import Metal
import SceneKit
import UIKit

/// Renders small, softly lit portraits of island models for the build menu.
@MainActor
enum Thumbnailer {
    private static var cache: [String: UIImage] = [:]
    private static let renderer: SCNRenderer? = {
        guard let device = MTLCreateSystemDefaultDevice() else { return nil }
        return SCNRenderer(device: device, options: nil)
    }()

    static func image(for model: String, size: CGFloat = 220) -> UIImage? {
        if let img = cache[model] { return img }
        guard let renderer, let node = ModelLibrary.node(model) else { return nil }

        let scene = SCNScene()
        scene.background.contents = UIColor.clear
        scene.rootNode.addChildNode(node)
        let (minB, maxB) = node.boundingBox
        let center = SIMD3<Float>((minB.x + maxB.x) / 2, (minB.y + maxB.y) / 2, (minB.z + maxB.z) / 2)
        let extent = max(maxB.x - minB.x, maxB.y - minB.y, maxB.z - minB.z)

        let cam = SCNCamera()
        cam.fieldOfView = 30
        cam.zNear = 0.05
        cam.zFar = 200
        let camNode = SCNNode()
        camNode.camera = cam
        let dist = extent / (2 * tan(15 * .pi / 180)) * 1.05
        let dir = simd_normalize(SIMD3<Float>(0.55, 0.45, 1))
        camNode.simdPosition = center + dir * dist
        camNode.simdLook(at: center)
        scene.rootNode.addChildNode(camNode)

        let key = SCNNode()
        key.light = SCNLight()
        key.light?.type = .directional
        key.light?.intensity = 1800
        key.light?.color = UIColor(red: 1, green: 0.95, blue: 0.86, alpha: 1)
        key.simdPosition = SIMD3(4, 8, 6)
        key.simdLook(at: .zero)
        scene.rootNode.addChildNode(key)
        let amb = SCNNode()
        amb.light = SCNLight()
        amb.light?.type = .ambient
        amb.light?.intensity = 900
        amb.light?.color = UIColor(red: 0.85, green: 0.9, blue: 1, alpha: 1)
        scene.rootNode.addChildNode(amb)
        scene.lightingEnvironment.contents = UIColor(red: 0.8, green: 0.88, blue: 1, alpha: 1)
        scene.lightingEnvironment.intensity = 1.2

        renderer.scene = scene
        renderer.pointOfView = camNode
        let img = renderer.snapshot(atTime: 0, with: CGSize(width: size, height: size), antialiasingMode: .multisampling4X)
        cache[model] = img
        return img
    }
}
