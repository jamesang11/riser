import AlarmKit
import Foundation

/// Travels with every scheduled alarm so the Live Activity can describe the mission.
struct RiserAlarmMetadata: AlarmMetadata {
    var mission: MissionKind
    var target: Int
    var isNag: Bool
}
