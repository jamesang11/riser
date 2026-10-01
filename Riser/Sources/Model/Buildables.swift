import Foundation
import simd

/// Something the player can build on their island with coins.
struct Buildable: Identifiable, Hashable, Sendable {
    let id: String
    let name: String
    let blurb: String
    let model: String          // usdz file name (without extension)
    let symbol: String         // SF Symbol for the build menu
    let cost: Int
    let level: Int             // level required
    let premium: Bool
    /// Position on the island top, in SceneKit space (x, z). Blender (x, y) -> SceneKit (x, -y).
    let slot: SIMD2<Float>
    let rotation: Float        // yaw in radians
    let scale: Float

}

extension SIMD2 where Scalar == Float {
    /// Blender (x, y) on the island top → SceneKit (x, z).
    static func blender(_ x: Float, _ y: Float) -> SIMD2<Float> { SIMD2(x, -y) }
}

enum BuildCatalog {
    static let all: [Buildable] = [
        Buildable(id: "tent", name: "Camp Tent", blurb: "Where every journey starts.",
                  model: "tent", symbol: "tent.fill", cost: 0, level: 1, premium: false,
                  slot: .blender(0, 0.6), rotation: 0, scale: 1),
        Buildable(id: "cottage", name: "Cozy Cottage", blurb: "A real home, with glowing windows at night.",
                  model: "cottage", symbol: "house.fill", cost: 140, level: 3, premium: false,
                  slot: .blender(0, 0.6), rotation: 0, scale: 1),
        Buildable(id: "campfire", name: "Campfire", blurb: "Crackles to life after sunset.",
                  model: "campfire", symbol: "flame.fill", cost: 30, level: 1, premium: false,
                  slot: .blender(1.8, -1.6), rotation: 0.4, scale: 1),
        Buildable(id: "flowers", name: "Wildflowers", blurb: "A burst of colour by the path.",
                  model: "flowers", symbol: "camera.macro", cost: 25, level: 1, premium: false,
                  slot: .blender(-3.5, -2.1), rotation: 0, scale: 1),
        Buildable(id: "lamppost", name: "Lamppost", blurb: "Lights the way on dark mornings.",
                  model: "lamppost", symbol: "lamp.table.fill", cost: 40, level: 1, premium: false,
                  slot: .blender(-1.4, -2.4), rotation: 0, scale: 1),
        Buildable(id: "treeRound", name: "Apple Tree", blurb: "Sways in the real wind.",
                  model: "tree_round", symbol: "tree.fill", cost: 50, level: 2, premium: false,
                  slot: .blender(-3.2, 1.2), rotation: 0.8, scale: 1),
        Buildable(id: "bench", name: "Bench", blurb: "Sit and watch the sunrise.",
                  model: "bench", symbol: "chair.lounge.fill", cost: 45, level: 2, premium: false,
                  slot: .blender(0.2, -2.9), rotation: 0, scale: 1),
        Buildable(id: "mailbox", name: "Mailbox", blurb: "Your sprout checks it every morning.",
                  model: "mailbox", symbol: "envelope.fill", cost: 35, level: 2, premium: false,
                  slot: .blender(1.2, -3.4), rotation: -0.3, scale: 1),
        Buildable(id: "garden", name: "Veggie Patch", blurb: "Grows a little every day you wake up.",
                  model: "garden", symbol: "carrot.fill", cost: 60, level: 2, premium: false,
                  slot: .blender(-2.6, -0.8), rotation: 0.3, scale: 1),
        Buildable(id: "pine", name: "Pine Tree", blurb: "Evergreen, like your streak.",
                  model: "pine", symbol: "tree", cost: 60, level: 3, premium: false,
                  slot: .blender(1.8, 3.4), rotation: 0, scale: 1),
        Buildable(id: "pond", name: "Lily Pond", blurb: "Ripples when it rains.",
                  model: "pond", symbol: "drop.fill", cost: 90, level: 3, premium: false,
                  slot: .blender(2.6, -0.2), rotation: 0, scale: 1),
        Buildable(id: "lanterns", name: "String Lanterns", blurb: "Warm lights for night owls turned early birds.",
                  model: "lanterns", symbol: "light.cylindrical.ceiling.fill", cost: 70, level: 3, premium: true,
                  slot: .blender(0.0, 2.9), rotation: 0, scale: 1),
        Buildable(id: "treeBlossom", name: "Cherry Blossom", blurb: "Drops petals on spring mornings.",
                  model: "tree_blossom", symbol: "camera.macro.circle.fill", cost: 80, level: 4, premium: true,
                  slot: .blender(3.2, 1.6), rotation: 0, scale: 1),
        Buildable(id: "telescope", name: "Telescope", blurb: "For stargazing before bed.",
                  model: "telescope", symbol: "moon.stars.fill", cost: 110, level: 4, premium: true,
                  slot: .blender(3.3, -2.3), rotation: 0.6, scale: 1),
        Buildable(id: "windmill", name: "Windmill", blurb: "Spins with your real local wind speed.",
                  model: "windmill", symbol: "wind", cost: 150, level: 5, premium: true,
                  slot: .blender(-1.6, 3.2), rotation: 0.35, scale: 1),
        Buildable(id: "pumpkins", name: "Pumpkin Patch", blurb: "Harvest Festival exclusive.",
                  model: "pumpkins", symbol: "leaf.fill", cost: 0, level: 1, premium: false,
                  slot: .blender(-2.3, -3.6), rotation: 0.2, scale: 1),
        Buildable(id: "scarecrow", name: "Scarecrow", blurb: "Harvest Festival exclusive. Very friendly.",
                  model: "scarecrow", symbol: "figure.stand", cost: 0, level: 1, premium: false,
                  slot: .blender(-4.0, -0.2), rotation: 0.5, scale: 1),
        Buildable(id: "maple", name: "Maple Tree", blurb: "Harvest Festival exclusive. Glows orange at sunset.",
                  model: "maple", symbol: "leaf.fill", cost: 0, level: 1, premium: false,
                  slot: .blender(2.4, -3.9), rotation: 0.3, scale: 1),
        // Free-placement decor: no classic slot, the player chooses where they go.
        Buildable(id: "bushes", name: "Flower Bushes", blurb: "Round hedges dotted with blossoms.",
                  model: "bushes", symbol: "camera.macro", cost: 25, level: 1, premium: false,
                  slot: .zero, rotation: 0, scale: 1),
        Buildable(id: "boulders", name: "Mossy Boulders", blurb: "Old stones with soft green caps.",
                  model: "boulders", symbol: "mountain.2.fill", cost: 30, level: 1, premium: false,
                  slot: .zero, rotation: 0, scale: 1),
        Buildable(id: "signpost", name: "Signpost", blurb: "Points the way to every island you own.",
                  model: "signpost", symbol: "signpost.right.and.left.fill", cost: 35, level: 2, premium: false,
                  slot: .zero, rotation: 0, scale: 1),
        Buildable(id: "beehive", name: "Beehives", blurb: "Busy bees make the flowers bloom.",
                  model: "beehive", symbol: "hexagon.fill", cost: 60, level: 2, premium: false,
                  slot: .zero, rotation: 0, scale: 1),
        Buildable(id: "picnic", name: "Picnic Table", blurb: "Breakfast outside on sunny mornings.",
                  model: "picnic", symbol: "basket.fill", cost: 80, level: 3, premium: false,
                  slot: .zero, rotation: 0, scale: 1),
        Buildable(id: "well", name: "Wishing Well", blurb: "Toss in a coin and wish for an early night.",
                  model: "well", symbol: "drop.fill", cost: 90, level: 3, premium: false,
                  slot: .zero, rotation: 0, scale: 1),
        Buildable(id: "swing", name: "Swing", blurb: "Sways in the real wind.",
                  model: "swing", symbol: "figure.play", cost: 100, level: 3, premium: false,
                  slot: .zero, rotation: 0, scale: 1),
        Buildable(id: "archway", name: "Flower Arch", blurb: "A doorway made of blossoms.",
                  model: "archway", symbol: "laurel.leading", cost: 110, level: 4, premium: false,
                  slot: .zero, rotation: 0, scale: 1),
        Buildable(id: "hammock", name: "Hammock", blurb: "For lazy days off.",
                  model: "hammock", symbol: "bed.double.fill", cost: 120, level: 4, premium: false,
                  slot: .zero, rotation: 0, scale: 1),
        Buildable(id: "fountain", name: "Fountain", blurb: "Splashes and sparkles in the sun.",
                  model: "fountain", symbol: "humidity.fill", cost: 180, level: 5, premium: false,
                  slot: .zero, rotation: 0, scale: 1),
        Buildable(id: "gazebo", name: "Gazebo", blurb: "A shady spot to watch the rain.",
                  model: "gazebo", symbol: "house.lodge.fill", cost: 220, level: 6, premium: false,
                  slot: .zero, rotation: 0, scale: 1),
        Buildable(id: "lighthouse", name: "Lighthouse", blurb: "Its lamp glows all night long.",
                  model: "lighthouse", symbol: "light.beacon.max.fill", cost: 260, level: 7, premium: false,
                  slot: .zero, rotation: 0, scale: 1),
    ]

    /// Decor earned from seasonal event chests rather than bought.
    static let eventItems: Set<String> = ["pumpkins", "scarecrow", "maple"]

    static func item(_ id: String) -> Buildable? { all.first { $0.id == id } }

    /// Items that share a slot replace each other (the tent becomes a cottage).
    static func replaces(_ item: Buildable) -> [String] {
        item.id == "cottage" ? ["tent"] : []
    }
}
