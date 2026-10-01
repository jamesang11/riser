import AlarmKit
import AppIntents
import Foundation
import SwiftUI

/// Mailbox between the alarm intents (which may run before the UI exists) and the app.
enum MissionInbox {
    struct Pending: Codable, Equatable {
        var sourceAlarmID: String
        var date: Date
    }

    private static let pendingKey = "riser.pendingMission"
    private static let nagKey = "riser.nagAlarms"
    private static let nagCountKey = "riser.nagCount"
    private static let testKey = "riser.testAlarms"
    private static let missionKey = "riser.alarmMissions"
    private static let soundKey = "riser.alarmSounds"
    private static let sourceKey = "riser.alarmSources"
    static let escapeProofKey = "riser.escapeProof"
    static let didChange = Notification.Name("riser.missionInboxChanged")

    static func post(sourceAlarmID: String) {
        let pending = Pending(sourceAlarmID: sourceAlarmID, date: .now)
        if let data = try? JSONEncoder().encode(pending) {
            UserDefaults.standard.set(data, forKey: pendingKey)
        }
        NotificationCenter.default.post(name: didChange, object: nil)
    }

    /// A pending mission from the last two hours, if any.
    static var pending: Pending? {
        guard let data = UserDefaults.standard.data(forKey: pendingKey),
              let p = try? JSONDecoder().decode(Pending.self, from: data),
              Date.now.timeIntervalSince(p.date) < 2 * 3600 else { return nil }
        return p
    }

    static func clear() {
        UserDefaults.standard.removeObject(forKey: pendingKey)
    }

    /// The guard alarm kept just ahead of an open escape-proof mission (see `AlarmService.armGuard`).
    static var guardID: UUID? {
        get { UserDefaults.standard.string(forKey: "riser.guardID").flatMap(UUID.init) }
        set { UserDefaults.standard.set(newValue?.uuidString, forKey: "riser.guardID") }
    }

    static var nagIDs: [UUID] {
        get { (UserDefaults.standard.stringArray(forKey: nagKey) ?? []).compactMap(UUID.init) }
        set { UserDefaults.standard.set(newValue.map(\.uuidString), forKey: nagKey) }
    }

    /// Re-rings so far this morning (resets once the last one is a few hours old).
    static var nagCount: Int {
        get {
            if let last = UserDefaults.standard.object(forKey: nagCountKey + ".date") as? Date,
               Date.now.timeIntervalSince(last) > 3 * 3600 { return 0 }
            return UserDefaults.standard.integer(forKey: nagCountKey)
        }
        set {
            UserDefaults.standard.set(newValue, forKey: nagCountKey)
            UserDefaults.standard.set(Date.now, forKey: nagCountKey + ".date")
        }
    }

    /// Escape-proof is opt-in.
    static var escapeProof: Bool {
        UserDefaults.standard.object(forKey: escapeProofKey) as? Bool ?? false
    }

    /// How long after Stop an escape-proof alarm rings again (seconds).
    static let nagIntervals: [TimeInterval] = [10, 30, 60, 300]
    static var nagInterval: TimeInterval {
        get {
            let v = UserDefaults.standard.double(forKey: "riser.nagInterval")
            return nagIntervals.contains(v) ? v : 10
        }
        set { UserDefaults.standard.set(newValue, forKey: "riser.nagInterval") }
    }

    /// "10 seconds", "1 minute", "5 minutes".
    static func intervalText(_ seconds: TimeInterval) -> String {
        seconds < 60 ? "\(Int(seconds)) seconds" : seconds == 60 ? "1 minute" : "\(Int(seconds / 60)) minutes"
    }

    /// One-off test alarms (kept when the regular alarm list re-syncs).
    static var testIDs: [UUID] {
        get { (UserDefaults.standard.stringArray(forKey: testKey) ?? []).compactMap(UUID.init) }
        set { UserDefaults.standard.set(newValue.suffix(10).map(\.uuidString), forKey: testKey) }
    }

    /// Mission + target for each source alarm id (so tests of unsaved alarms and nags start the right mission).
    static func remember(_ id: UUID, mission: MissionKind, target: Int) {
        var map = UserDefaults.standard.dictionary(forKey: missionKey) as? [String: String] ?? [:]
        map[id.uuidString] = "\(mission.rawValue):\(target)"
        UserDefaults.standard.set(map, forKey: missionKey)
    }

    /// The sound each source alarm rings with, so re-rings and the escape guard sound the same.
    static func rememberSound(_ id: UUID, sound: AlarmSound) {
        var map = UserDefaults.standard.dictionary(forKey: soundKey) as? [String: String] ?? [:]
        map[id.uuidString] = sound.rawValue
        UserDefaults.standard.set(map, forKey: soundKey)
    }

    static func sound(for id: UUID) -> AlarmSound {
        (UserDefaults.standard.dictionary(forKey: soundKey) as? [String: String])?[id.uuidString]
            .flatMap(AlarmSound.init(rawValue:)) ?? .classic
    }

    /// Which saved alarm a test alarm or re-ring belongs to (their AlarmKit ids differ from it).
    static func rememberSource(_ id: UUID, source: UUID) {
        guard id != source else { return }
        let list = (UserDefaults.standard.stringArray(forKey: sourceKey) ?? []) + ["\(id.uuidString):\(source.uuidString)"]
        UserDefaults.standard.set(Array(list.suffix(30)), forKey: sourceKey)
    }

    static func source(for id: UUID) -> UUID? {
        let prefix = id.uuidString + ":"
        guard let entry = (UserDefaults.standard.stringArray(forKey: sourceKey) ?? []).last(where: { $0.hasPrefix(prefix) }) else { return nil }
        return UUID(uuidString: String(entry.dropFirst(prefix.count)))
    }

    static func mission(for id: String) -> (MissionKind, Int)? {
        guard let raw = (UserDefaults.standard.dictionary(forKey: missionKey) as? [String: String])?[id] else { return nil }
        let parts = raw.split(separator: ":")
        guard parts.count == 2, let m = MissionKind(rawValue: String(parts[0])), let t = Int(parts[1]) else { return nil }
        return (m, t)
    }
}

enum AlarmService {
    static var manager: AlarmManager { AlarmManager.shared }
    /// Escape-proof keeps re-ringing for up to an hour, then gives up (nobody gets an alarm they can never silence).
    static let nagWindow: TimeInterval = 3600
    static var maxNags: Int { max(10, Int(nagWindow / MissionInbox.nagInterval)) }

    static var isAuthorized: Bool { manager.authorizationState == .authorized }
    static var authorizationState: AlarmManager.AuthorizationState { manager.authorizationState }

    @discardableResult
    static func requestAuthorization() async -> Bool {
        switch manager.authorizationState {
        case .authorized: return true
        case .denied: return false
        case .notDetermined:
            return (try? await manager.requestAuthorization()) == .authorized
        @unknown default: return false
        }
    }

    /// Makes the system's scheduled alarms mirror the app's alarm list.
    static func sync(_ alarms: [AlarmItem]) async {
        #if DEBUG
        if UserDefaults.standard.bool(forKey: "demoQuiet") { return }  // filming: no permission popup
        #endif
        guard isAuthorized else { return }
        let keep = Set(MissionInbox.nagIDs + MissionInbox.testIDs + [MissionInbox.guardID].compactMap { $0 })
        let existing = (try? manager.alarms) ?? []
        for alarm in existing where !keep.contains(alarm.id) {
            try? manager.cancel(id: alarm.id)
        }
        for item in alarms where item.isEnabled {
            try? await schedule(item)
        }
    }

    static func schedule(_ item: AlarmItem) async throws {
        let time = Alarm.Schedule.Relative.Time(hour: item.hour, minute: item.minute)
        let recurrence: Alarm.Schedule.Relative.Recurrence =
            item.weekdays.isEmpty ? .never : .weekly(item.weekdays.sorted().compactMap(weekday(from:)))
        let alarmSchedule = Alarm.Schedule.relative(.init(time: time, repeats: recurrence))
        let target = item.mission.clamped(item.target)
        let title: LocalizedStringResource = item.label.isEmpty
            ? "Rise & shine! \(item.mission.amountText(target)) to go"
            : "\(item.label)"
        MissionInbox.remember(item.id, mission: item.mission, target: target)
        MissionInbox.rememberSound(item.id, sound: item.sound)
        try await schedule(
            id: item.id,
            sourceID: item.id,
            schedule: alarmSchedule,
            title: title,
            metadata: RiserAlarmMetadata(mission: item.mission, target: target, isNag: false),
            sound: item.sound
        )
    }

    /// A one-off alarm a minute from now, great for trying the whole loop.
    static func scheduleTest(for item: AlarmItem, in seconds: TimeInterval = 60) async throws -> Date {
        let fire = Date.now.addingTimeInterval(seconds)
        let testID = UUID()
        MissionInbox.testIDs.append(testID)
        let target = item.mission.clamped(item.target)
        MissionInbox.remember(item.id, mission: item.mission, target: target)
        MissionInbox.rememberSound(item.id, sound: item.sound)
        try await schedule(
            id: testID,
            sourceID: item.id,
            schedule: .fixed(fire),
            title: "Test wake-up! \(item.mission.amountText(target))",
            metadata: RiserAlarmMetadata(mission: item.mission, target: target, isNag: false),
            sound: item.sound
        )
        return fire
    }

    /// Re-arms the alarm if the player tries to escape without finishing their mission.
    static func scheduleNag(sourceID: UUID, in seconds: TimeInterval = MissionInbox.nagInterval) async {
        guard isAuthorized, MissionInbox.nagCount < maxNags else { return }
        MissionInbox.nagCount += 1
        let id = UUID()
        MissionInbox.nagIDs.append(id)
        let lines: [LocalizedStringResource] = [
            "Nice try! Your sprout is still waiting",
            "Still in bed? Your mission awaits",
            "The sun's up. Are you?",
            "Your streak is counting on you",
        ]
        let title = lines[(MissionInbox.nagCount - 1) % lines.count]
        let (mission, target) = MissionInbox.mission(for: sourceID.uuidString) ?? (.pushups, MissionKind.pushups.defaultTarget)
        try? await schedule(
            id: id,
            sourceID: sourceID,
            schedule: .fixed(Date.now.addingTimeInterval(seconds)),
            title: title,
            metadata: RiserAlarmMetadata(mission: mission, target: target, isNag: true),
            sound: MissionInbox.sound(for: sourceID)
        )
    }

    /// Called when a mission is finished: silence everything that was chasing the player.
    static func missionCompleted() {
        disarmGuard()
        for id in MissionInbox.nagIDs {
            try? manager.cancel(id: id)
        }
        for alarm in (try? manager.alarms) ?? [] where alarm.state == .alerting {
            try? manager.stop(id: alarm.id)
        }
        MissionInbox.nagIDs = []
        MissionInbox.nagCount = 0
        MissionInbox.clear()
    }

    /// Cancels pending re-rings (the player is doing the mission now).
    /// How far ahead the guard waits: the player's re-ring delay, never less than 20 s, plus a little slack.
    static var guardDelay: TimeInterval { max(MissionInbox.nagInterval, 20) + 10 }

    /// While an escape-proof mission is on screen, a guard alarm waits just ahead and the app keeps pushing it
    /// back. Leave, close or force-quit the app and the pushing stops, so the guard rings. Nothing has to run
    /// after the player leaves, which is what makes it impossible to wriggle out of.
    static func armGuard(sourceID: UUID) async {
        guard isAuthorized else { return }
        let old = MissionInbox.guardID
        let id = UUID()
        let (mission, target) = MissionInbox.mission(for: sourceID.uuidString) ?? (.pushups, MissionKind.pushups.defaultTarget)
        do {
            // The new guard is booked before the old one is cancelled, so there's never a gap.
            try await schedule(
                id: id,
                sourceID: sourceID,
                schedule: .fixed(Date.now.addingTimeInterval(guardDelay)),
                title: "Back to your mission!",
                metadata: RiserAlarmMetadata(mission: mission, target: target, isNag: true),
                sound: MissionInbox.sound(for: sourceID)
            )
            MissionInbox.guardID = id
            if let old { try? manager.cancel(id: old) }
        } catch {}
    }

    static func disarmGuard() {
        if let id = MissionInbox.guardID { try? manager.cancel(id: id) }
        MissionInbox.guardID = nil
    }

    static func cancelNags() {
        for id in MissionInbox.nagIDs { try? manager.cancel(id: id) }
        MissionInbox.nagIDs = []
        MissionInbox.nagCount = 0
    }

    static func stopRinging() {
        for alarm in (try? manager.alarms) ?? [] where alarm.state == .alerting {
            try? manager.stop(id: alarm.id)
        }
    }

    // MARK: - Private

    private static func schedule(
        id: UUID,
        sourceID: UUID,
        schedule: Alarm.Schedule,
        title: LocalizedStringResource,
        metadata: RiserAlarmMetadata,
        sound: AlarmSound
    ) async throws {
        let start = AlarmButton(text: "Start Mission", textColor: .white, systemImageName: "sun.max.fill")
        let alert: AlarmPresentation.Alert
        if #available(iOS 26.1, *) {
            alert = AlarmPresentation.Alert(title: title, secondaryButton: start, secondaryButtonBehavior: .custom)
        } else {
            let stop = AlarmButton(text: "Stop", textColor: .white, systemImageName: "xmark")
            alert = AlarmPresentation.Alert(title: title, stopButton: stop, secondaryButton: start, secondaryButtonBehavior: .custom)
        }
        let attributes = AlarmAttributes<RiserAlarmMetadata>(
            presentation: AlarmPresentation(alert: alert),
            metadata: metadata,
            tintColor: Color(red: 0.98, green: 0.65, blue: 0.26)
        )
        let configuration = AlarmManager.AlarmConfiguration<RiserAlarmMetadata>(
            schedule: schedule,
            attributes: attributes,
            stopIntent: EscapeAlarmIntent(alarmID: id, sourceID: sourceID),
            secondaryIntent: StartMissionIntent(alarmID: id, sourceID: sourceID),
            sound: sound == .classic ? .default : .named(sound.fileName)
        )
        MissionInbox.rememberSource(id, source: sourceID)
        _ = try await manager.schedule(id: id, configuration: configuration)
    }

    private static func weekday(from calendarWeekday: Int) -> Locale.Weekday? {
        switch calendarWeekday {
        case 1: .sunday
        case 2: .monday
        case 3: .tuesday
        case 4: .wednesday
        case 5: .thursday
        case 6: .friday
        case 7: .saturday
        default: nil
        }
    }
}

// MARK: - Intents

/// "Start Mission" on the alarm: silences the system alert and opens straight into the mission.
struct StartMissionIntent: LiveActivityIntent {
    static var title: LocalizedStringResource = "Start Wake-up Mission"
    static var openAppWhenRun: Bool = true
    static var isDiscoverable: Bool = false

    @Parameter(title: "Alarm ID") var alarmID: String
    @Parameter(title: "Source Alarm ID") var sourceID: String

    init() {
        alarmID = ""
        sourceID = ""
    }

    init(alarmID: UUID, sourceID: UUID) {
        self.alarmID = alarmID.uuidString
        self.sourceID = sourceID.uuidString
    }

    func perform() async throws -> some IntentResult {
        if let id = UUID(uuidString: alarmID) {
            try? AlarmManager.shared.stop(id: id)
        }
        MissionInbox.post(sourceAlarmID: sourceID)
        return .result()
    }
}

/// The system Stop control. Escape-proof mode re-arms the alarm after the chosen delay (10 s to 5 min).
struct EscapeAlarmIntent: LiveActivityIntent {
    static var title: LocalizedStringResource = "Stop Alarm"
    static var isDiscoverable: Bool = false

    @Parameter(title: "Alarm ID") var alarmID: String
    @Parameter(title: "Source Alarm ID") var sourceID: String

    init() {
        alarmID = ""
        sourceID = ""
    }

    init(alarmID: UUID, sourceID: UUID) {
        self.alarmID = alarmID.uuidString
        self.sourceID = sourceID.uuidString
    }

    func perform() async throws -> some IntentResult {
        if let id = UUID(uuidString: alarmID) {
            try? AlarmManager.shared.stop(id: id)
        }
        // Escape-proof (opt-in): the mission stays pending and the alarm re-rings after the chosen delay.
        if MissionInbox.escapeProof, let source = UUID(uuidString: sourceID) {
            MissionInbox.post(sourceAlarmID: sourceID)
            await AlarmService.scheduleNag(sourceID: source)
        }
        return .result()
    }
}
