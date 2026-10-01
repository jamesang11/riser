import Foundation

/// Long-term milestones. Progress is computed from the game state; each pays out coins once.
struct Achievement: Identifiable, Hashable, Sendable {
    let id: String
    let title: String
    let detail: String
    let symbol: String
    let reward: Int
    let goal: Int
    let progress: @Sendable (GameState) -> Int

    static func == (a: Achievement, b: Achievement) -> Bool { a.id == b.id }
    func hash(into h: inout Hasher) { h.combine(id) }
}

enum AchievementCatalog {
    static let all: [Achievement] = [
        Achievement(id: "first", title: "First Light", detail: "Win your first morning", symbol: "sunrise.fill", reward: 25, goal: 1) { $0.totalWakeUps },
        Achievement(id: "streak3", title: "Early Bird", detail: "Reach a 3-day streak", symbol: "flame.fill", reward: 40, goal: 3) { $0.bestStreak },
        Achievement(id: "streak7", title: "Week of Sunrises", detail: "Reach a 7-day streak", symbol: "flame.circle.fill", reward: 80, goal: 7) { $0.bestStreak },
        Achievement(id: "streak30", title: "Sunrise Legend", detail: "Reach a 30-day streak", symbol: "crown.fill", reward: 250, goal: 30) { $0.bestStreak },
        Achievement(id: "speedy", title: "Speedy Riser", detail: "Finish a mission in under a minute", symbol: "hare.fill", reward: 40, goal: 1) { s in
            s.history.filter { $0.isWin && $0.secondsToComplete < 60 }.isEmpty ? 0 : 1
        },
        Achievement(id: "pushups", title: "Push-up Pro", detail: "Do 100 push-ups", symbol: "figure.core.training", reward: 80, goal: 100) { $0.total(of: .pushups) },
        Achievement(id: "squats", title: "Squat Squad", detail: "Do 100 squats", symbol: "figure.strengthtraining.functional", reward: 80, goal: 100) { $0.total(of: .squats) },
        Achievement(id: "math", title: "Bright Brain", detail: "Solve 50 problems", symbol: "brain.head.profile", reward: 60, goal: 50) { $0.total(of: .math) },
        Achievement(id: "hunt", title: "Treasure Hunter", detail: "Find 25 items", symbol: "magnifyingglass", reward: 60, goal: 25) { $0.total(of: .hunt) },
        Achievement(id: "foreman", title: "Climbing the Ladder", detail: "Get promoted to Foreman", symbol: "arrow.up.circle.fill", reward: 100, goal: Career.ranks[3].points) { $0.careerPoints },
        Achievement(id: "owner", title: "Farm Owner", detail: "Reach the top of the career ladder", symbol: "house.lodge.fill", reward: 300, goal: Career.ranks[5].points) { $0.careerPoints },
        Achievement(id: "builder", title: "Island Builder", detail: "Build 8 things on your island", symbol: "hammer.fill", reward: 100, goal: 8) { s in s.built.filter { $0 != "tent" }.count },
        Achievement(id: "decorator", title: "Home Sweet Home", detail: "Place 5 pieces of furniture", symbol: "sofa.fill", reward: 80, goal: 5) { s in
            s.layouts[s.homeKind]?.count ?? 0
        },
        Achievement(id: "traveler", title: "Globetrotter", detail: "Vacation in 4 different places", symbol: "airplane", reward: 120, goal: 4) { s in
            Set(s.logbook.compactMap { AdventureCatalog.discovery($0.discovery)?.0.id }).count
        },
        Achievement(id: "isle", title: "Island Hopper", detail: "Buy a second island", symbol: "map.fill", reward: 100, goal: 1) { $0.isles.count },
        Achievement(id: "archipelago", title: "Archipelago", detail: "Own every island", symbol: "globe.asia.australia.fill", reward: 300, goal: IsleCatalog.all.count) { $0.isles.count },
        Achievement(id: "stories", title: "Storyteller", detail: "Collect 24 postcards", symbol: "envelope.open.fill", reward: 200, goal: 24) { $0.logbook.count },
    ]
}
