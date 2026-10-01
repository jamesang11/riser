import SceneKit
import UIKit

/// Loads Blender-made USDZ models and gives them the Riser look (soft PBR + rim light + night glow).
@MainActor
enum ModelLibrary {
    private static var cache: [String: SCNNode] = [:]
    /// Every material that should glow warmly at night (windows, lamps, lanterns, embers).
    private(set) static var glowMaterials: [SCNMaterial] = []
    /// Every material that receives the sky-tinted rim light.
    private(set) static var rimMaterials: [SCNMaterial] = []
    private(set) static var waterMaterials: [SCNMaterial] = []
    /// Grass and flower materials that sway in the wind.
    private(set) static var windMaterials: [SCNMaterial] = []

    static let windShader = """
    #pragma arguments
    float windAmount;
    #pragma body
    float h = clamp(_geometry.position.y * 3.0, 0.0, 1.0);
    float4 wp = scn_node.modelTransform * _geometry.position;
    float t = scn_frame.time;
    float s = sin(t * 2.3 + wp.x * 1.7 + wp.z * 1.1) + 0.5 * sin(t * 3.9 + wp.z * 2.3);
    _geometry.position.x += s * h * (0.012 + 0.035 * windAmount);
    _geometry.position.z += s * h * (0.008 + 0.022 * windAmount);
    """
    private static let swayingNodes: Set<String> = ["IslandDecor", "FlowerPatch", "GardenBed"]
    private static let swayingMaterials: Set<String> = [
        "GrassTuft", "GrassLight", "Leaf", "LeafDark", "Blossom", "BlossomDeep", "BlossomLight",
        "FlowerYellow", "Purple", "White", "Stem", "Apple",
    ]

    static let rimShader = """
    #pragma arguments
    float3 rimColor;
    #pragma body
    float rimF = 1.0 - saturate(dot(_surface.normal, _surface.view));
    _surface.emission.rgb += rimColor * (rimF * rimF * rimF);
    """

    static let waterShader = """
    #pragma body
    float t = scn_frame.time;
    float w = sin(t * 1.7 + _surface.position.x * 5.0) * sin(t * 1.3 + _surface.position.y * 6.0);
    _surface.diffuse.rgb += float3(0.06, 0.08, 0.09) * w;
    """

    static func exists(_ name: String) -> Bool {
        Bundle.main.url(forResource: name, withExtension: "usdz") != nil
    }

    /// Returns a fresh clone (geometry shared) of the named model, or nil if it isn't bundled yet.
    static func node(_ name: String) -> SCNNode? {
        if let cached = cache[name] { return cached.clone() }
        guard let url = Bundle.main.url(forResource: name, withExtension: "usdz"),
              let scene = try? SCNScene(url: url, options: [.checkConsistency: false]) else { return nil }
        let container = SCNNode()
        container.name = name
        for child in scene.rootNode.childNodes {
            container.addChildNode(child)
        }
        prepare(container, rim: !name.hasPrefix("cloud"))
        cache[name] = container
        return container.clone()
    }

    private static func prepare(_ root: SCNNode, rim: Bool) {
        root.enumerateHierarchy { node, _ in
            node.castsShadow = true
            guard let geometry = node.geometry else { return }
            let sways = swayingNodes.contains(node.name ?? "")
            if sways {
                geometry.materials = geometry.materials.map { $0.copy() as! SCNMaterial }
            }
            for material in geometry.materials {
                let name = material.name ?? ""
                material.lightingModel = .physicallyBased
                material.metalness.contents = 0.0
                material.roughness.contents = 0.82
                material.isDoubleSided = false
                if name.hasPrefix("Glow") {
                    material.emission.contents = UIColor(red: 1, green: 0.84, blue: 0.54, alpha: 1)
                    material.emission.intensity = 0
                    glowMaterials.append(material)
                } else if name == "Water" {
                    material.roughness.contents = 0.12
                    material.transparency = 0.88
                    material.shaderModifiers = [.surface: waterShader]
                    waterMaterials.append(material)
                    continue
                }
                if sways && swayingMaterials.contains(name) {
                    material.shaderModifiers = [.geometry: windShader, .surface: rimShader]
                    material.setValue(NSNumber(value: 0.3), forKey: "windAmount")
                    material.setValue(NSValue(scnVector3: SCNVector3(0, 0, 0)), forKey: "rimColor")
                    windMaterials.append(material)
                    rimMaterials.append(material)
                } else if rim {
                    material.shaderModifiers = [.surface: rimShader]
                    material.setValue(NSValue(scnVector3: SCNVector3(0, 0, 0)), forKey: "rimColor")
                    rimMaterials.append(material)
                }
            }
        }
    }
}

extension SCNNode {
    /// Finds a named descendant (Blender object name).
    func part(_ name: String) -> SCNNode? { childNode(withName: name, recursively: true) }
}
