import SceneKit
import simd

/// Butterflies that flutter around the island by day, and little birds that fly past now and then.
@MainActor
final class CritterSystem {
    private struct Butterfly {
        let node: SCNNode
        let wings: [SCNNode]
        let center: SIMD3<Float>
        let radius: Float
        let speed: Float
        let phase: Float
    }

    private struct Bird {
        let node: SCNNode
        let wings: [SCNNode]
        let start: SIMD3<Float>
        let end: SIMD3<Float>
        let born: CFTimeInterval
        let duration: CFTimeInterval
        let flapOffset: Float
    }

    private let root = SCNNode()
    private var butterflies: [Butterfly] = []
    private var birds: [Bird] = []
    private var butterfliesOn = false
    private var birdsOn = false
    private var nextFlock: CFTimeInterval = 0

    init(parent: SCNNode) {
        root.name = "Critters"
        parent.addChildNode(root)
    }

    func setActive(butterflies b: Bool, birds br: Bool) {
        if b != butterfliesOn {
            butterfliesOn = b
            b ? spawnButterflies() : clearButterflies()
        }
        birdsOn = br
    }

    private func spawnButterflies() {
        guard ModelLibrary.exists("butterfly") else { return }
        let spots: [SIMD3<Float>] = [SIMD3(-3.2, 0.6, 2.0), SIMD3(-2.4, 0.7, 0.6), SIMD3(2.2, 0.8, 1.9)]
        let tints: [UIColor] = [
            UIColor(red: 1, green: 0.93, blue: 0.6, alpha: 1),
            UIColor(red: 1, green: 0.78, blue: 0.86, alpha: 1),
            UIColor(red: 0.8, green: 0.9, blue: 1, alpha: 1),
        ]
        for (i, c) in spots.enumerated() {
            guard let node = ModelLibrary.node("butterfly") else { continue }
            node.simdScale = SIMD3(repeating: 1.4)
            node.enumerateHierarchy { n, _ in
                n.castsShadow = false
                if n.name?.hasPrefix("Wing") == true, let g = n.geometry {
                    g.materials = g.materials.map { m in
                        let copy = m.copy() as! SCNMaterial
                        copy.multiply.contents = tints[i % tints.count]
                        return copy
                    }
                }
            }
            let wings = ["WingL", "WingR"].compactMap { node.part($0) }
            root.addChildNode(node)
            butterflies.append(Butterfly(node: node, wings: wings, center: c, radius: Float.random(in: 0.5...0.9),
                                         speed: Float.random(in: 0.6...0.9), phase: Float.random(in: 0...6)))
        }
    }

    private func clearButterflies() {
        butterflies.forEach { $0.node.removeFromParentNode() }
        butterflies.removeAll()
    }

    private func spawnFlock(at t: CFTimeInterval) {
        guard ModelLibrary.exists("bird") else { return }
        let side: Float = Bool.random() ? 1 : -1
        let height = Float.random(in: 2.5...4.5)
        let depth = Float.random(in: -2...3)
        for i in 0..<Int.random(in: 1...3) {
            guard let node = ModelLibrary.node("bird") else { continue }
            node.enumerateHierarchy { n, _ in n.castsShadow = false }
            let offset = SIMD3<Float>(Float(i) * 0.7 * side, Float(i) * 0.25, Float(i) * 0.5)
            let start = SIMD3<Float>(-14 * side, height, depth) - offset
            let end = SIMD3<Float>(14 * side, height + Float.random(in: -1...1.5), depth - 2) - offset
            node.simdPosition = start
            node.simdScale = SIMD3(repeating: 1.5)
            root.addChildNode(node)
            let wings = ["WingL", "WingR"].compactMap { node.part($0) }
            birds.append(Bird(node: node, wings: wings, start: start, end: end, born: t,
                              duration: Double.random(in: 7...10), flapOffset: Float(i)))
        }
    }

    func update(t: CFTimeInterval, dt: Float) {
        let ft = Float(t)
        for b in butterflies {
            let a = ft * b.speed + b.phase
            let p = b.center + SIMD3(cos(a) * b.radius, sin(a * 2.3) * 0.18 + sin(a * 0.7) * 0.1, sin(a * 1.3) * b.radius * 0.8)
            let ahead = b.center + SIMD3(cos(a + 0.1) * b.radius, 0, sin((a + 0.1) * 1.3) * b.radius * 0.8)
            b.node.simdPosition = p
            let d = ahead - p
            b.node.simdEulerAngles.y = atan2(d.x, d.z)
            let flap = sin(ft * 22 + b.phase) * 0.9
            if b.wings.count == 2 {
                b.wings[0].simdEulerAngles.z = flap
                b.wings[1].simdEulerAngles.z = -flap
            }
        }

        if birdsOn {
            if nextFlock == 0 { nextFlock = t + Double.random(in: 4...10) }
            if t > nextFlock {
                spawnFlock(at: t)
                nextFlock = t + Double.random(in: 18...40)
            }
        }
        birds.removeAll { bird in
            let k = Float((t - bird.born) / bird.duration)
            if k >= 1 {
                bird.node.removeFromParentNode()
                return true
            }
            var p = simd_mix(bird.start, bird.end, SIMD3(repeating: k))
            p.y += sin(k * .pi * 3) * 0.3
            bird.node.simdPosition = p
            let d = bird.end - bird.start
            bird.node.simdEulerAngles = SIMD3(0, atan2(d.x, d.z), 0)
            // Flap, then glide.
            let cycle = (ft * 1.2 + bird.flapOffset).truncatingRemainder(dividingBy: 2)
            let flap = cycle < 1.2 ? sin(ft * 20 + bird.flapOffset) * 0.8 : 0.15
            if bird.wings.count == 2 {
                bird.wings[0].simdEulerAngles.z = flap
                bird.wings[1].simdEulerAngles.z = -flap
            }
            return false
        }
    }
}
