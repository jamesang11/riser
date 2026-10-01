import Foundation
import simd

/// Where the player put something: which island, where on its top (SceneKit x/z), and which way it faces.
struct ItemPlacement: Codable, Hashable, Sendable {
    var island: Int = 0
    var x: Float
    var z: Float
    var rotation: Float = 0

    var point: SIMD2<Float> { SIMD2(x, z) }

    func moved(to p: SIMD2<Float>) -> ItemPlacement {
        var m = self
        m.x = p.x
        m.z = p.y
        return m
    }
}

/// Extra floating islands the player can buy, joined to home by a rope bridge.
struct Isle: Identifiable, Hashable, Sendable {
    let id: Int
    let name: String
    let blurb: String
    let model: String
    let symbol: String
    let price: Int
    let level: Int
    /// Centre relative to the home island (SceneKit space).
    let position: SIMD3<Float>
    let buildRadius: Float
}

enum IsleCatalog {
    /// How far from the centre an item's middle can go on the home island. The flat grass ends ~4.7 m out at the
    /// narrowest point and the grassy rim runs to ~5.3 m (Blender `a_island.R`), so 5.0 stays on the green.
    static let homeBuildRadius: Float = 5.0

    static let all: [Isle] = [
        Isle(id: 1, name: "Meadow Isle", blurb: "A quiet green isle across a rope bridge, with room for a whole garden.",
             model: "isle_meadow", symbol: "leaf.circle.fill", price: 500, level: 4,
             position: SIMD3(-10.8, -0.9, -4.2), buildRadius: 3.2),
        Isle(id: 2, name: "Sandy Isle", blurb: "A sunny isle with a sandy shore. Perfect for a lighthouse and a hammock.",
             model: "isle_beach", symbol: "beach.umbrella.fill", price: 1000, level: 7,
             position: SIMD3(10.6, 0.5, -6.0), buildRadius: 3.2),
    ]

    static func isle(_ id: Int) -> Isle? { all.first { $0.id == id } }

    static func buildRadius(_ island: Int) -> Float {
        island == 0 ? homeBuildRadius : (isle(island)?.buildRadius ?? 3)
    }

    static func name(_ island: Int) -> String {
        island == 0 ? "Home Isle" : (isle(island)?.name ?? "Isle")
    }

    static func symbol(_ island: Int) -> String {
        island == 0 ? "tree.fill" : (isle(island)?.symbol ?? "circle")
    }
}

extension BuildCatalog {
    /// Homes stay where they are (the door and the path lead to them).
    static func isMovable(_ id: String) -> Bool { id != "tent" && id != "cottage" }

    /// Ground circle an item needs, for packing items without overlaps.
    static func radius(_ id: String) -> Float {
        switch id {
        case "cottage": 1.45
        case "tent": 1.15
        case "windmill": 1.0
        case "pond": 1.05
        case "garden": 0.8
        case "campfire": 0.75
        case "bench": 0.6
        case "flowers": 0.55
        case "pumpkins": 0.65
        case "telescope": 0.45
        case "treeRound", "treeBlossom", "maple": 0.55
        case "pine": 0.55
        case "lanterns": 1.25
        case "mailbox", "lamppost", "scarecrow": 0.3
        case "well": 0.6
        case "fountain": 0.8
        case "gazebo": 1.1
        case "beehive": 0.5
        case "swing": 0.7
        case "lighthouse": 0.6
        case "bushes": 0.7
        case "boulders": 0.6
        case "signpost": 0.3
        case "picnic": 0.8
        case "archway": 0.7
        case "hammock": 0.9
        default: 0.6
        }
    }
}

extension AppModel {
    /// Where an item is (or would be): the player's placement, or its original spot on the home island.
    func placement(of id: String) -> ItemPlacement {
        if let p = state.placements[id] { return p }
        let item = BuildCatalog.item(id)
        return ItemPlacement(island: 0, x: item?.slot.x ?? 0, z: item?.slot.y ?? 0, rotation: item?.rotation ?? 0)
    }

    /// Every built item's placement, for the world.
    var resolvedPlacements: [String: ItemPlacement] {
        Dictionary(uniqueKeysWithValues: state.built.map { ($0, placement(of: $0)) })
    }

    /// Front of the house, kept clear so the sprout can always get in and out.
    private static let doorClearance = (point: SIMD2<Float>(0.2, 1.35), radius: Float(0.55))

    /// Whether `id` fits at `p`: on the island, not overlapping anything, not blocking the door.
    func canPlace(_ id: String, at p: ItemPlacement) -> Bool { placementProblem(id, at: p) == nil }

    /// Why `id` can't go at `p` (nil if it fits).
    func placementProblem(_ id: String, at p: ItemPlacement) -> String? {
        let r = BuildCatalog.radius(id)
        if p.island != 0 && !state.isles.contains(p.island) { return "You don't own that island yet" }
        // Generous: the item's middle has to be on the grass; a little overhang at the rim is fine.
        if simd_length(p.point) + r * 0.35 > IsleCatalog.buildRadius(p.island) { return "Too close to the edge" }
        let replaced = BuildCatalog.item(id).map(BuildCatalog.replaces) ?? []
        for other in state.built where other != id && !replaced.contains(other) {
            let q = placement(of: other)
            guard q.island == p.island else { continue }
            // Footprints are drawn generously, so things may nestle in about 30% closer than their full radii.
            if simd_distance(p.point, q.point) < (r + BuildCatalog.radius(other)) * 0.7 {
                return "Bumps into the \(BuildCatalog.item(other)?.name.lowercased() ?? "something")"
            }
        }
        if p.island == 0 && BuildCatalog.isMovable(id),
           simd_distance(p.point, Self.doorClearance.point) < r + Self.doorClearance.radius {
            return "Keep the front door clear"
        }
        return nil
    }

    /// A good free spot for a new item on `island`: its classic slot if free, else the nearest open ground.
    func freeSpot(for id: String, on island: Int) -> ItemPlacement? {
        let item = BuildCatalog.item(id)
        let rotation = item?.rotation ?? 0
        if island == 0, let item, item.slot != .zero {
            let classic = ItemPlacement(island: 0, x: item.slot.x, z: item.slot.y, rotation: rotation)
            if canPlace(id, at: classic) { return classic }
        }
        let maxR = IsleCatalog.buildRadius(island) - BuildCatalog.radius(id) * 0.35
        var ring: Float = 0
        while ring <= maxR {
            let steps = max(1, Int((2 * .pi * ring) / 0.45))
            for k in 0..<steps {
                // Start at the front (towards the camera) and work round.
                let a = Float(k) / Float(steps) * 2 * .pi
                let p = ItemPlacement(island: island, x: sin(a) * ring, z: cos(a) * ring, rotation: rotation)
                if canPlace(id, at: p) { return p }
            }
            ring += 0.35
        }
        return nil
    }

    // MARK: Islands

    enum IsleStatus: Equatable { case owned, available, needsLevel(Int), needsCoins(Int) }

    func status(of isle: Isle) -> IsleStatus {
        if state.isles.contains(isle.id) { return .owned }
        if state.level < isle.level { return .needsLevel(isle.level) }
        if state.coins < isle.price { return .needsCoins(isle.price - state.coins) }
        return .available
    }

    @discardableResult
    func buyIsle(_ isle: Isle) -> Bool {
        guard status(of: isle) == .available, !inDebt else {
            SoundService.shared.play(.nope)
            Haptics.warning()
            return false
        }
        state.coins -= isle.price
        state.isles.append(isle.id)
        lastIsle = isle.id
        SoundService.shared.play(.levelUp)
        Haptics.success()
        sendLetter(from: "Island Council 🏛️", title: "Welcome to \(isle.name)!",
                   body: "The rope bridge is up and \(isle.name) is yours. Build anything you like there: open Build, pick something, and drag it onto the new isle.")
        checkAchievements()
        return true
    }

    /// Moves something that's already built.
    func move(_ id: String, to p: ItemPlacement) -> Bool {
        guard state.built.contains(id), BuildCatalog.isMovable(id), canPlace(id, at: p) else {
            SoundService.shared.play(.nope)
            Haptics.warning()
            return false
        }
        state.placements[id] = p
        SoundService.shared.play(.build, volume: 0.5)
        Haptics.success()
        return true
    }
}
