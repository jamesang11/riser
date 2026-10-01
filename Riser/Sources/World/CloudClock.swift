import SceneKit
import UIKit
import simd

/// The home screen clock, built from puffy 3D cloud numerals that float in the island's sky
/// and are lit by the real sun and moon. Changing digits pop like soft marshmallows.
@MainActor
final class CloudClock {
    let node = SCNNode()
    private var glyphs: [SCNNode] = []
    private var characters: [Character] = []
    private var materials: [SCNMaterial] = []
    private static var templates: [String: SCNNode] = [:]

    /// Cap height of the main digits as a fraction of the screen height.
    var screenFraction: CGFloat = 0.05
    private let smallScale: Float = 0.42

    init() {
        node.name = "CloudClock"
        node.renderingOrder = 10
    }

    // MARK: Glyph library

    private static func key(for c: Character) -> String? {
        switch c {
        case "0"..."9": String(c)
        case ":": "colon"
        case "A", "a": "A"
        case "P", "p": "P"
        case "M", "m": "M"
        case "R", "r": "R"
        case "I", "i": "I"
        case "S", "s": "S"
        case "E", "e": "E"
        default: nil
        }
    }

    private func makeGlyph(_ c: Character) -> SCNNode {
        let holder = SCNNode()
        let inner: SCNNode
        if let key = Self.key(for: c), let template = Self.template(key) {
            inner = template.clone()
        } else {
            inner = Self.textGlyph(c)
        }
        holder.addChildNode(inner)
        inner.enumerateHierarchy { n, _ in
            n.castsShadow = false
            n.geometry?.materials.forEach { m in
                if !materials.contains(where: { $0 === m }) { materials.append(m) }
            }
        }
        return holder
    }

    private static func template(_ key: String) -> SCNNode? {
        if let t = templates[key] { return t }
        guard let url = Bundle.main.url(forResource: "glyph_\(key)", withExtension: "usdz"),
              let scene = try? SCNScene(url: url) else { return nil }
        let root = SCNNode()
        scene.rootNode.childNodes.forEach { root.addChildNode($0) }
        root.enumerateHierarchy { n, _ in
            n.geometry?.materials = [cloudMaterial]
        }
        templates[key] = root
        return root
    }

    private static let cloudMaterial: SCNMaterial = {
        let m = SCNMaterial()
        m.lightingModel = .physicallyBased
        m.diffuse.contents = UIColor.white
        m.roughness.contents = 1.0
        m.metalness.contents = 0.0
        m.emission.contents = UIColor.white
        m.emission.intensity = 0.12
        m.shaderModifiers = [.surface: ModelLibrary.rimShader]
        m.setValue(NSValue(scnVector3: SCNVector3(0.3, 0.3, 0.35)), forKey: "rimColor")
        return m
    }()

    /// Fallback: chunky rounded 3D text, used until the cloud glyphs are bundled (or for other scripts).
    private static func textGeometry(_ c: Character) -> SCNText {
        let text = SCNText(string: String(c), extrusionDepth: 0.3)
        let base = UIFont.systemFont(ofSize: 1.38, weight: .heavy)
        text.font = base.fontDescriptor.withDesign(.rounded).map { UIFont(descriptor: $0, size: 1.38) } ?? base
        text.chamferRadius = 0.07
        text.flatness = 0.02
        text.materials = [cloudMaterial]
        return text
    }

    /// Baseline and cap height measured from "0", shared by every fallback glyph.
    private static let referenceMetrics: (baseline: Float, height: Float) = {
        let (minB, maxB) = SCNNode(geometry: textGeometry("0")).boundingBox
        return (minB.y, max(0.3, maxB.y - minB.y))
    }()

    private static func textGlyph(_ c: Character) -> SCNNode {
        let n = SCNNode(geometry: textGeometry(c))
        let (minB, maxB) = n.boundingBox
        let ref = referenceMetrics
        n.pivot = SCNMatrix4MakeTranslation((minB.x + maxB.x) / 2, ref.baseline, (minB.z + maxB.z) / 2)
        let wrapper = SCNNode()
        wrapper.addChildNode(n)
        n.scale = SCNVector3(1 / ref.height, 1 / ref.height, 1 / ref.height)
        return wrapper
    }

    // MARK: Layout

    /// Shows a new time string, animating only the characters that changed.
    func show(_ date: Date) {
        let raw = date.formatted(date: .omitted, time: .shortened)
        show(text: raw.replacingOccurrences(of: "\u{202F}", with: " ").replacingOccurrences(of: "\u{00A0}", with: " "))
    }

    /// Spells any text in cloud letters (e.g. the "RISER" logo in onboarding).
    func show(text: String) {
        let chars = Array(text)
        guard chars != characters else { return }
        let old = characters
        characters = chars

        var newGlyphs: [SCNNode] = []
        var reused = glyphs
        for (i, c) in chars.enumerated() {
            if c == " " { newGlyphs.append(SCNNode()); continue }
            if i < old.count, old[i] == c, i < reused.count {
                newGlyphs.append(reused[i])
                reused[i] = SCNNode()   // mark as kept
            } else {
                let g = makeGlyph(c)
                node.addChildNode(g)
                if !old.isEmpty { pop(g) }
                newGlyphs.append(g)
            }
        }
        // Remove glyphs that were replaced, with a little puff out.
        for g in reused where g.parent != nil {
            let out = SCNAction.group([.scale(to: 0.01, duration: 0.18), .fadeOut(duration: 0.18)])
            out.timingMode = .easeIn
            g.runAction(.sequence([out, .removeFromParentNode()]))
        }
        glyphs = newGlyphs
        layout()
    }

    private func pop(_ g: SCNNode) {
        g.scale = SCNVector3(0.01, 0.01, 0.01)
        let a = SCNAction.scale(to: 1.18, duration: 0.22)
        a.timingMode = .easeOut
        let b = SCNAction.scale(to: 0.95, duration: 0.12)
        let c = SCNAction.scale(to: 1.0, duration: 0.12)
        g.runAction(.sequence([.wait(duration: 0.1), a, b, c]))
    }

    private func layout() {
        // Main run = everything up to the first space; the AM/PM suffix is set smaller.
        var x: Float = 0
        var positions: [(SCNNode, Float, Float)] = []   // node, x, scale
        var small = false
        for (i, c) in characters.enumerated() {
            if c == " " {
                small = true
                x += 0.16
                continue
            }
            let g = glyphs[i]
            let s: Float = small ? smallScale : 1
            let w = width(of: g) * s
            positions.append((g, x + w / 2, s))
            x += w + (c == ":" || (i + 1 < characters.count && characters[i + 1] == ":") ? 0.03 : 0.07) * s
        }
        let total = x
        for (g, px, s) in positions {
            g.simdPosition = SIMD3(px - total / 2, 0, 0)
            g.childNodes.first?.simdScale = SIMD3(repeating: s)
        }
    }

    private func width(of g: SCNNode) -> Float {
        guard let inner = g.childNodes.first else { return 0.6 }
        let (minB, maxB) = inner.boundingBox
        let w = maxB.x - minB.x
        return w > 0.01 ? w : 0.6
    }

    // MARK: Per-frame

    /// Places the clock in camera space so it sits at a given screen height, at the focus depth.
    func update(t: CFTimeInterval, depth: Float, verticalFOV: Float, screenY: CGFloat, night: Double) {
        let visibleH = 2 * depth * tan(verticalFOV / 2)
        let capHeight = visibleH * Float(screenFraction)
        let y = (0.5 - Float(screenY)) * visibleH
        node.simdPosition = SIMD3(0, y - capHeight / 2, -depth)
        node.simdScale = SIMD3(repeating: capHeight)
        for (i, g) in glyphs.enumerated() where g.childNodes.first != nil {
            g.simdPosition.y = sin(Float(t) * 1.3 + Float(i) * 0.8) * 0.035
            g.simdEulerAngles = SIMD3(sin(Float(t) * 0.9 + Float(i)) * 0.06, sin(Float(t) * 0.7 + Float(i) * 1.7) * 0.1, 0)
        }
        let m = Self.cloudMaterial
        m.emission.intensity = CGFloat(0.5 + night * 0.1)
        m.emission.contents = night > 0.5 ? UIColor(red: 0.78, green: 0.82, blue: 1, alpha: 1) : UIColor(red: 1, green: 0.98, blue: 0.95, alpha: 1)
    }
}
