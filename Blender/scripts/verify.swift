// Usage: swift verify.swift file.usdz [more.usdz ...]
// Loads each USDZ in SceneKit, prints the node tree (names, geometry tris, materials)
// and the overall bounding box in scene (Y-up) space.
import SceneKit
import Foundation

func fmt(_ v: SCNVector3) -> String { String(format: "(%.2f, %.2f, %.2f)", v.x, v.y, v.z) }

for path in CommandLine.arguments.dropFirst() {
    print("=== \(URL(fileURLWithPath: path).lastPathComponent)")
    do {
        let scene = try SCNScene(url: URL(fileURLWithPath: path), options: nil)
        var tris = 0
        var mn = SCNVector3(Float.greatestFiniteMagnitude, Float.greatestFiniteMagnitude, Float.greatestFiniteMagnitude)
        var mx = SCNVector3(-Float.greatestFiniteMagnitude, -Float.greatestFiniteMagnitude, -Float.greatestFiniteMagnitude)
        var mats = Set<String>()
        func walk(_ n: SCNNode, _ d: Int) {
            var line = String(repeating: "  ", count: d) + (n.name ?? "<unnamed>")
            if let g = n.geometry {
                let t = g.elements.reduce(0) { $0 + $1.primitiveCount }
                tris += t
                let ms = g.materials.map { $0.name ?? "?" }
                ms.forEach { mats.insert($0) }
                line += "  [mesh \(t) tris]"
                let (a, b) = n.boundingBox
                for x in [a.x, b.x] { for y in [a.y, b.y] { for z in [a.z, b.z] {
                    let p = n.convertPosition(SCNVector3(x, y, z), to: scene.rootNode)
                    mn = SCNVector3(min(mn.x, p.x), min(mn.y, p.y), min(mn.z, p.z))
                    mx = SCNVector3(max(mx.x, p.x), max(mx.y, p.y), max(mx.z, p.z))
                }}}
            } else if d > 0 {
                let p = n.convertPosition(SCNVector3(0, 0, 0), to: scene.rootNode)
                line += "  @world\(fmt(p))"
            }
            if n.eulerAngles.x != 0 || n.eulerAngles.y != 0 || n.eulerAngles.z != 0 {
                line += String(format: "  rot(%.1f,%.1f,%.1f)", n.eulerAngles.x * 57.3, n.eulerAngles.y * 57.3, n.eulerAngles.z * 57.3)
            }
            print(line)
            for c in n.childNodes { walk(c, d + 1) }
        }
        walk(scene.rootNode, 0)
        print("materials: \(mats.sorted().joined(separator: ", "))")
        print("total tris: \(tris)")
        print("bbox min \(fmt(mn)) max \(fmt(mx)) size \(fmt(SCNVector3(mx.x - mn.x, mx.y - mn.y, mx.z - mn.z)))")
    } catch {
        print("LOAD FAILED: \(error)")
    }
}
