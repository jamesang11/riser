import Foundation

struct AlarmItem: Codable, Identifiable, Hashable, Sendable {
    var id: UUID = UUID()
    var hour: Int = 7
    var minute: Int = 0
    /// Calendar weekday numbers (1 = Sunday … 7 = Saturday). Empty = one-off.
    var weekdays: Set<Int> = [2, 3, 4, 5, 6]
    var isEnabled: Bool = true
    var mission: MissionKind = .pushups
    var target: Int = MissionKind.pushups.defaultTarget
    var sound: AlarmSound = .classic
    var label: String = ""
    /// When the alarm was created (misses only count after this).
    var createdAt: Date? = .now

    var timeText: String {
        var comps = DateComponents()
        comps.hour = hour
        comps.minute = minute
        let date = Calendar.current.date(from: comps) ?? .now
        return date.formatted(date: .omitted, time: .shortened)
    }

    var repeatText: String {
        if weekdays.isEmpty { return "Once" }
        if weekdays == [2, 3, 4, 5, 6] { return "Weekdays" }
        if weekdays == [1, 7] { return "Weekends" }
        if weekdays.count == 7 { return "Every day" }
        let symbols = Calendar.current.shortWeekdaySymbols
        return weekdays.sorted().map { symbols[$0 - 1] }.joined(separator: " ")
    }

    /// Next date this alarm will ring, used for the countdown pill.
    func nextFireDate(after now: Date = .now) -> Date? {
        let cal = Calendar.current
        var comps = DateComponents()
        comps.hour = hour
        comps.minute = minute
        comps.second = 0
        if weekdays.isEmpty {
            return cal.nextDate(after: now, matching: comps, matchingPolicy: .nextTime)
        }
        return weekdays.compactMap { day -> Date? in
            var c = comps
            c.weekday = day
            return cal.nextDate(after: now, matching: c, matchingPolicy: .nextTime)
        }.min()
    }
}
