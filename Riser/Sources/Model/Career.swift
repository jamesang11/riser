import Foundation

/// Sprig's job on the farm. Showing up promotes him; missing work gets him demoted.
enum Career {
    struct Rank: Hashable {
        let title: String
        let emoji: String
        /// Total shifts (career points) needed to reach this rank.
        let points: Int
        let wage: Int
    }

    static let ranks: [Rank] = [
        Rank(title: "Farmhand", emoji: "🧺", points: 0, wage: 10),
        Rank(title: "Sprout Grower", emoji: "🌱", points: 5, wage: 14),
        Rank(title: "Harvester", emoji: "🥕", points: 12, wage: 19),
        Rank(title: "Foreman", emoji: "📋", points: 25, wage: 26),
        Rank(title: "Head Farmer", emoji: "🧑‍🌾", points: 45, wage: 34),
        Rank(title: "Farm Owner", emoji: "🏡", points: 75, wage: 45),
    ]

    static func rank(for points: Int) -> Int {
        ranks.lastIndex { points >= $0.points } ?? 0
    }

    /// Progress (0...1) toward the next rank.
    static func progress(points: Int) -> Double {
        let r = rank(for: points)
        guard r + 1 < ranks.count else { return 1 }
        let lo = ranks[r].points, hi = ranks[r + 1].points
        return Double(points - lo) / Double(hi - lo)
    }

    /// Crop mastery: harvest counts that earn stars (+10% sale price each).
    static let masteryThresholds = [10, 25, 50]

    static func stars(harvested: Int) -> Int {
        masteryThresholds.filter { harvested >= $0 }.count
    }

    /// Weekly island upkeep: every building needs looking after.
    static func upkeep(buildings: Int) -> Int { 5 + 3 * buildings }

    /// Consecutive missed mornings before Sprig is too sick to get out of bed.
    static let runawayAfter = 5
    /// Won mornings needed to nurse him back to health.
    static let comebackMornings = 1
}

/// A letter in Sprig's mailbox: warnings from the boss, bills, notes from Sprig.
struct Letter: Codable, Hashable, Identifiable, Sendable {
    var id = UUID()
    var date: Date = .now
    var from: String
    var title: String
    var body: String
    var read = false
}
