import Foundation

/// A wake-up mission the player must finish before the alarm lets go.
enum MissionKind: String, Codable, CaseIterable, Identifiable, Sendable {
    case pushups
    case squats
    case steps
    case math
    case hunt

    var id: String { rawValue }

    var title: String {
        switch self {
        case .pushups: "Push-ups"
        case .squats: "Squats"
        case .steps: "Morning Walk"
        case .math: "Brain Warm-up"
        case .hunt: "Item Hunt"
        }
    }

    /// "10 push-ups", "find 3 items", …
    func goalText(_ target: Int) -> String {
        switch self {
        case .hunt: "find \(target) item\(target == 1 ? "" : "s")"
        case .math: "\(target) math problem\(target == 1 ? "" : "s")"
        case .steps: "walk \(target) step\(target == 1 ? "" : "s")"
        default: "\(target) \(title.lowercased())"
        }
    }

    /// "10 reps", "1 item", "50 steps" (singular when the goal is one).
    func amountText(_ target: Int) -> String {
        target == 1 && unit.hasSuffix("s") ? "1 \(unit.dropLast())" : "\(target) \(unit)"
    }

    /// A goal forced into this mission's allowed range (older saved alarms may be outside it).
    func clamped(_ target: Int) -> Int {
        min(max(target, targetRange.lowerBound), targetRange.upperBound)
    }

    var symbol: String {
        switch self {
        case .pushups: "figure.core.training"
        case .squats: "figure.strengthtraining.functional"
        case .steps: "figure.walk"
        case .math: "brain.head.profile"
        case .hunt: "magnifyingglass"
        }
    }

    var blurb: String {
        switch self {
        case .pushups: "Set your phone down in front of you or to your side. The camera counts every rep."
        case .squats: "Prop your phone up facing you. The camera watches your knees and counts every squat."
        case .steps: "Get out of bed and walk. Kitchen, window, anywhere."
        case .math: "Quick sums to switch your brain on."
        case .hunt: "Get up and find one everyday thing around your home, like a mug or your shoes. The camera recognises it."
        }
    }

    /// Short instruction shown during the mission.
    var instruction: String {
        switch self {
        case .pushups: "Lean your phone against something on the floor about 1.5 m away, in front of you or to your side, and get into a plank. Knee push-ups count too."
        case .squats: "Lean your phone against something about 2 m away, facing you, so your whole body is in view."
        case .steps: "Start walking. Every step counts."
        case .math: "Solve each one to continue."
        case .hunt: "Walk to it and point your camera at it until it's ticked off. Can't find it? Try another item."
        }
    }

    var unit: String {
        switch self {
        case .pushups: "reps"
        case .squats: "reps"
        case .steps: "steps"
        case .math: "problems"
        case .hunt: "items"
        }
    }

    var targetRange: ClosedRange<Int> {
        switch self {
        case .pushups: 3...50
        case .squats: 5...60
        case .steps: 20...300
        case .math: 1...10
        case .hunt: 1...1
        }
    }

    var targetStep: Int {
        switch self {
        case .steps: 10
        default: 1
        }
    }

    var defaultTarget: Int {
        switch self {
        case .pushups: 10
        case .squats: 15
        case .steps: 50
        case .math: 3
        case .hunt: 1
        }
    }

    /// Relative effort used for XP. Roughly normalised so a default mission ~ 40 XP.
    func effortXP(target: Int) -> Int {
        switch self {
        case .pushups: target * 4
        case .squats: Int(Double(target) * 2.7)
        case .steps: Int(Double(target) * 0.8)
        case .math: target * 12
        case .hunt: target * 40
        }
    }
}

enum AlarmSound: String, Codable, CaseIterable, Identifiable, Sendable {
    /// The iPhone's own alarm sound (AlarmKit's system default).
    case classic
    case sunrise
    case meadow
    case bells

    var id: String { rawValue }

    var title: String {
        switch self {
        case .classic: "iPhone Alarm"
        case .sunrise: "Sunrise"
        case .meadow: "Meadow"
        case .bells: "Heavy Sleeper"
        }
    }

    var subtitle: String {
        switch self {
        case .classic: "The standard iPhone alarm sound"
        case .sunrise: "Bright kalimba melody"
        case .meadow: "Chimes & birdsong"
        case .bells: "Insistent hand-bells"
        }
    }

    var fileName: String { "alarm_\(rawValue).caf" }

    /// What plays inside the app during a mission (the system alarm sound can't be played by apps).
    var loopName: String { self == .classic ? "alarm_bells" : "alarm_\(rawValue)" }

    var isPremium: Bool { self == .meadow }
}
