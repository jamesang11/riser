import Foundation

/// A crop the sprout can grow on the Farm Island. Crops grow one stage per won morning.
struct Crop: Identifiable, Hashable, Sendable {
    let id: String
    let name: String
    let emoji: String
    let seedCost: Int
    let mornings: Int
    let sellPrice: Int
    let level: Int
    let premium: Bool

    var model: String { "crop_\(id)" }
}

struct Food: Identifiable, Hashable, Sendable {
    let id: String
    let name: String
    let emoji: String
    let cost: Int
    let hunger: Int
    let mood: Int

    var model: String { "food_\(id)" }
}

enum FarmCatalog {
    static let crops: [Crop] = [
        Crop(id: "turnip", name: "Turnip", emoji: "🥔", seedCost: 5, mornings: 1, sellPrice: 12, level: 1, premium: false),
        Crop(id: "carrot", name: "Carrot", emoji: "🥕", seedCost: 8, mornings: 2, sellPrice: 24, level: 1, premium: false),
        Crop(id: "strawberry", name: "Strawberry", emoji: "🍓", seedCost: 15, mornings: 2, sellPrice: 38, level: 2, premium: false),
        Crop(id: "corn", name: "Corn", emoji: "🌽", seedCost: 20, mornings: 3, sellPrice: 60, level: 3, premium: false),
        Crop(id: "pumpkin", name: "Pumpkin", emoji: "🎃", seedCost: 30, mornings: 4, sellPrice: 100, level: 4, premium: false),
        Crop(id: "sunflower", name: "Golden Sunflower", emoji: "🌻", seedCost: 40, mornings: 3, sellPrice: 120, level: 1, premium: true),
    ]

    static let foods: [Food] = [
        Food(id: "apple", name: "Apple", emoji: "🍎", cost: 5, hunger: 20, mood: 0),
        Food(id: "soup", name: "Veggie Soup", emoji: "🥣", cost: 12, hunger: 50, mood: 0),
        Food(id: "cake", name: "Honey Cake", emoji: "🍰", cost: 30, hunger: 100, mood: 15),
    ]

    static func crop(_ id: String) -> Crop? { crops.first { $0.id == id } }
    static func food(_ id: String) -> Food? { foods.first { $0.id == id } }

    static let startingPlots = 4
    static let maxPlots = 6
    static func plotPrice(forPlot n: Int) -> Int { n == 5 ? 120 : 250 }
}

/// One farm plot. `growth` counts won mornings since planting.
struct PlotState: Codable, Hashable, Sendable {
    var crop: String? = nil
    var growth: Int = 0
    var wilted: Bool = false
    var dead: Bool = false

    var isEmpty: Bool { crop == nil }

    /// 0 = just planted, 1 = sprouting, 2 = leafy, 3 = ripe.
    var visualStage: Int {
        guard let crop, let c = FarmCatalog.crop(crop) else { return 0 }
        if growth >= c.mornings { return 3 }
        return growth * 2 >= c.mornings ? 2 : 1
    }

    var morningsLeft: Int? {
        guard let crop, let c = FarmCatalog.crop(crop), !dead else { return nil }
        return max(0, c.mornings - growth)
    }
}

extension Crop {
    /// "Carrots", "Strawberries", "Corn".
    var plural: String {
        switch id {
        case "corn": name
        case "strawberry": "Strawberries"
        case "sunflower": "Golden Sunflowers"
        default: name + "s"
        }
    }
}

struct HarvestLine: Codable, Hashable, Sendable {
    var crop: String
    var count: Int
    var coins: Int
}

enum MoodTier: String, Sendable {
    case happy, okay, sad

    init(mood: Int) {
        self = mood >= 70 ? .happy : mood < 35 ? .sad : .okay
    }

    var payMultiplier: Double {
        switch self {
        case .happy: 1.2
        case .okay: 1.0
        case .sad: 0.7
        }
    }
}

/// Pure farm rules: easy to reason about and to self-test.
enum FarmEngine {
    /// A won morning: every living crop grows a stage, wilted crops recover, ripe crops are harvested.
    static func wonMorning(_ plots: [PlotState], mastery: [String: Int] = [:]) -> (plots: [PlotState], harvest: [HarvestLine]) {
        var out = plots
        var counts: [String: Int] = [:]
        for i in out.indices {
            guard let crop = out[i].crop, !out[i].dead, let c = FarmCatalog.crop(crop) else { continue }
            out[i].wilted = false
            out[i].growth += 1
            if out[i].growth >= c.mornings {
                counts[crop, default: 0] += 1
                out[i] = PlotState()
            }
        }
        let harvest = counts.keys.sorted().map { id in
            let stars = Career.stars(harvested: mastery[id] ?? 0)
            let price = Double(FarmCatalog.crop(id)?.sellPrice ?? 0) * (1 + 0.1 * Double(stars))
            return HarvestLine(crop: id, count: counts[id]!, coins: Int((Double(counts[id]!) * price).rounded()))
        }
        return (out, harvest)
    }

    /// A missed alarm morning: first miss wilts, a second consecutive miss kills wilted crops.
    static func missedMorning(_ plots: [PlotState], consecutive: Int) -> [PlotState] {
        plots.map { p in
            var p = p
            guard p.crop != nil, !p.dead else { return p }
            if consecutive >= 2 && p.wilted {
                p.dead = true
                p.wilted = false
            } else {
                p.wilted = true
            }
            return p
        }
    }

    static func wage(streak: Int, plus: Bool, rank: Int = 0) -> Int {
        let base = Career.ranks[max(0, min(rank, Career.ranks.count - 1))].wage + min(streak * 2, 20)
        return plus ? base * 3 / 2 : base
    }

    static func pay(harvest: [HarvestLine], wage: Int, mood: Int) -> Int {
        let gross = harvest.reduce(wage) { $0 + $1.coins }
        return Int((Double(gross) * MoodTier(mood: mood).payMultiplier).rounded())
    }

    #if DEBUG
    /// Sanity checks for the rules above (logged at launch in debug builds).
    static func selfTest() -> [String] {
        var failures: [String] = []
        func check(_ ok: Bool, _ msg: String) { if !ok { failures.append(msg) } }
        var plots = [PlotState(crop: "carrot"), PlotState(crop: "turnip"), PlotState()]
        var r = wonMorning(plots)
        check(r.harvest == [HarvestLine(crop: "turnip", count: 1, coins: 12)], "turnip ripe after 1 morning")
        check(r.plots[0].growth == 1 && r.plots[1].isEmpty, "carrot grows, turnip plot cleared")
        plots = missedMorning(r.plots, consecutive: 1)
        check(plots[0].wilted && !plots[0].dead, "first miss wilts")
        r = wonMorning(plots)
        check(!r.plots[0].wilted, "won morning revives")
        check(r.harvest.first?.crop == "carrot", "carrot harvested after 2 won mornings")
        plots = [PlotState(crop: "corn")]
        plots = missedMorning(plots, consecutive: 1)
        plots = missedMorning(plots, consecutive: 2)
        check(plots[0].dead, "second consecutive miss kills")
        r = wonMorning(plots)
        check(r.plots[0].dead && r.harvest.isEmpty, "dead crops don't grow")
        check(pay(harvest: [HarvestLine(crop: "x", count: 1, coins: 50)], wage: 10, mood: 80) == 72, "happy pay x1.2")
        check(pay(harvest: [], wage: 10, mood: 20) == 7, "sad pay x0.7")
        return failures
    }
    #endif
}

/// What happened at work this morning (shown on the shift report).
struct ShiftReport: Codable, Hashable, Sendable {
    var harvest: [HarvestLine]
    var wage: Int
    var moodMultiplier: Double
    var total: Int
    var watered: Int
}
