import Foundation
import UIKit

/// Furniture and styles for the inside of Sprig's home (tent or cottage).
struct FurnitureItem: Identifiable, Hashable, Sendable {
    enum Kind: String, Sendable { case floor, wall }
    let id: String
    let name: String
    let symbol: String
    let price: Int
    let kind: Kind
    let premium: Bool

    var model: String { "furn_\(id)" }
}

/// A recolour of the room's surfaces (wallpaper, floor or tent canvas).
struct RoomStyle: Identifiable, Hashable, Sendable {
    enum Surface: String, Sendable { case wall, floor, canvas, groundsheet }
    let id: String
    let name: String
    let surface: Surface
    let price: Int
    /// Material name → colour (hex). Empty = the model's original look.
    let colors: [String: UInt32]
}

enum InteriorCatalog {
    static let furniture: [FurnitureItem] = [
        FurnitureItem(id: "plant", name: "Monstera", symbol: "leaf.fill", price: 45, kind: .floor, premium: false),
        FurnitureItem(id: "beanbag", name: "Beanbag", symbol: "circle.fill", price: 55, kind: .floor, premium: false),
        FurnitureItem(id: "teddy", name: "Big Teddy", symbol: "teddybear.fill", price: 60, kind: .floor, premium: false),
        FurnitureItem(id: "floorlamp", name: "Floor Lamp", symbol: "lamp.floor.fill", price: 65, kind: .floor, premium: false),
        FurnitureItem(id: "toychest", name: "Toy Chest", symbol: "shippingbox.fill", price: 70, kind: .floor, premium: false),
        FurnitureItem(id: "armchair", name: "Armchair", symbol: "sofa.fill", price: 90, kind: .floor, premium: false),
        FurnitureItem(id: "rocker", name: "Rocking Chair", symbol: "chair.fill", price: 95, kind: .floor, premium: false),
        FurnitureItem(id: "desk", name: "Writing Desk", symbol: "pencil.and.ruler.fill", price: 110, kind: .floor, premium: false),
        FurnitureItem(id: "recordplayer", name: "Record Player", symbol: "opticaldisc.fill", price: 130, kind: .floor, premium: true),
        FurnitureItem(id: "aquarium", name: "Aquarium", symbol: "fish.fill", price: 160, kind: .floor, premium: true),
        FurnitureItem(id: "poster_sun", name: "Sunrise Poster", symbol: "sunrise.fill", price: 30, kind: .wall, premium: false),
        FurnitureItem(id: "clock", name: "Wall Clock", symbol: "clock.fill", price: 40, kind: .wall, premium: false),
        FurnitureItem(id: "shelf", name: "Plant Shelf", symbol: "books.vertical.fill", price: 50, kind: .wall, premium: false),
        FurnitureItem(id: "garland", name: "Fairy Lights", symbol: "sparkles", price: 75, kind: .wall, premium: false),
    ]

    static let styles: [RoomStyle] = [
        RoomStyle(id: "wall.cream", name: "Cream Stripe", surface: .wall, price: 0, colors: [:]),
        RoomStyle(id: "wall.mint", name: "Mint", surface: .wall, price: 60,
                  colors: ["Wallpaper": 0xCFEBD9, "WallpaperStripe": 0xB5DCC4, "Wainscot": 0x7FB69A]),
        RoomStyle(id: "wall.blush", name: "Blush", surface: .wall, price: 60,
                  colors: ["Wallpaper": 0xF7D9DE, "WallpaperStripe": 0xF0C2CB, "Wainscot": 0xD98FA0]),
        RoomStyle(id: "wall.sky", name: "Sky Blue", surface: .wall, price: 60,
                  colors: ["Wallpaper": 0xCFE3F7, "WallpaperStripe": 0xB6D2EE, "Wainscot": 0x6E97C7]),
        RoomStyle(id: "wall.night", name: "Starry Night", surface: .wall, price: 90,
                  colors: ["Wallpaper": 0x2E3566, "WallpaperStripe": 0x3A4278, "Wainscot": 0x1F2447]),
        RoomStyle(id: "floor.oak", name: "Oak", surface: .floor, price: 0, colors: [:]),
        RoomStyle(id: "floor.cherry", name: "Cherry", surface: .floor, price: 50,
                  colors: ["FloorA": 0x9C5A3C, "FloorB": 0x8A4E33, "FloorC": 0xA86846]),
        RoomStyle(id: "floor.birch", name: "Birch", surface: .floor, price: 50,
                  colors: ["FloorA": 0xE8D4B0, "FloorB": 0xDCC59E, "FloorC": 0xF0DFC0]),
        RoomStyle(id: "floor.walnut", name: "Walnut", surface: .floor, price: 50,
                  colors: ["FloorA": 0x5E4230, "FloorB": 0x523828, "FloorC": 0x6B4C37]),
        RoomStyle(id: "canvas.orange", name: "Sunset Stripe", surface: .canvas, price: 0, colors: [:]),
        RoomStyle(id: "canvas.teal", name: "Lagoon Stripe", surface: .canvas, price: 45,
                  colors: ["TentOrange": 0x4FA3A5, "TentCream": 0xE6F4F1]),
        RoomStyle(id: "canvas.pink", name: "Berry Stripe", surface: .canvas, price: 45,
                  colors: ["TentOrange": 0xE77A9A, "TentCream": 0xFBE7EC]),
        RoomStyle(id: "canvas.forest", name: "Forest Stripe", surface: .canvas, price: 45,
                  colors: ["TentOrange": 0x5C8A4E, "TentCream": 0xEEF0DC]),
        RoomStyle(id: "ground.weave", name: "Picnic Weave", surface: .groundsheet, price: 0, colors: [:]),
        RoomStyle(id: "ground.blue", name: "Blue Gingham", surface: .groundsheet, price: 35,
                  colors: ["WeaveA": 0x8FB6E0, "WeaveB": 0xE8F0FA, "WeaveBorder": 0x4E77A8]),
        RoomStyle(id: "ground.red", name: "Red Gingham", surface: .groundsheet, price: 35,
                  colors: ["WeaveA": 0xD9665E, "WeaveB": 0xFBEDE9, "WeaveBorder": 0x9C3B35]),
    ]

    static let floorSlots = ["SlotFloor1", "SlotFloor2", "SlotFloor3"]
    static let wallSlots = ["SlotWall1", "SlotWall2"]

    static func item(_ id: String) -> FurnitureItem? { furniture.first { $0.id == id } }
    static func style(_ id: String) -> RoomStyle? { styles.first { $0.id == id } }

    /// Which surfaces a home can restyle.
    static func surfaces(for home: String) -> [RoomStyle.Surface] {
        home == "cottage" ? [.wall, .floor] : [.canvas, .groundsheet]
    }

    static func defaultStyle(_ surface: RoomStyle.Surface) -> String {
        switch surface {
        case .wall: "wall.cream"
        case .floor: "floor.oak"
        case .canvas: "canvas.orange"
        case .groundsheet: "ground.weave"
        }
    }

    /// Today's furniture in the market (rotates daily).
    static func market(on date: Date, plus: Bool) -> [FurnitureItem] {
        let day = Calendar.current.ordinality(of: .day, in: .era, for: date) ?? 0
        var rng = SeededRandom(seed: UInt64(day) &* 97_531)
        var pool = furniture
        var picks: [FurnitureItem] = []
        while picks.count < (plus ? 5 : 3) && !pool.isEmpty {
            picks.append(pool.remove(at: Int(rng.next() * Double(pool.count)) % pool.count))
        }
        return picks
    }
}

/// The current home's decor, handed to the renderer.
struct InteriorDecor: Equatable {
    var layout: [String: String] = [:]      // slot → furniture id
    var styles: [String] = []                // style ids applied
}
