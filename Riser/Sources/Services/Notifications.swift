import Foundation
import UserNotifications

/// Gentle local notifications (the sprout coming home from an adventure).
enum Notifications {
    static func scheduleReturn(name: String, place: String, at date: Date) {
        #if DEBUG
        if UserDefaults.standard.bool(forKey: "demoQuiet") { return }  // filming: no permission popup
        #endif
        let center = UNUserNotificationCenter.current()
        center.requestAuthorization(options: [.alert, .sound, .badge]) { granted, _ in
            guard granted else { return }
            let content = UNMutableNotificationContent()
            content.title = "\(name) is back! 🎈"
            content.body = "Home from \(place) with a postcard and a souvenir for you."
            content.sound = .default
            let interval = max(5, date.timeIntervalSinceNow)
            let request = UNNotificationRequest(identifier: "riser.trip",
                                                content: content,
                                                trigger: UNTimeIntervalNotificationTrigger(timeInterval: interval, repeats: false))
            center.removePendingNotificationRequests(withIdentifiers: ["riser.trip"])
            center.add(request)
        }
    }

    /// The day before a free trial converts: an honest heads-up, as promised on the paywall.
    static func scheduleTrialReminder(trialDays: Int, price: String) {
        guard trialDays > 1 else { return }
        let center = UNUserNotificationCenter.current()
        let c = UNMutableNotificationContent()
        c.title = "Your Riser trial ends tomorrow"
        c.body = "After that it's \(price). Keep your streak going, or cancel any time in Settings › Apple Account › Subscriptions."
        c.sound = .default
        let interval = TimeInterval(trialDays - 1) * 86400
        center.removePendingNotificationRequests(withIdentifiers: ["riser.trial"])
        center.add(UNNotificationRequest(identifier: "riser.trial", content: c,
                                         trigger: UNTimeIntervalNotificationTrigger(timeInterval: interval, repeats: false)))
    }

    /// Wind-down + bedtime nudges for the coming nights, so the player gets 5 full sleep cycles.
    static func scheduleSleep(name: String, plans: [(bedtime: Date, wake: Date)]) {
        let center = UNUserNotificationCenter.current()
        center.getPendingNotificationRequests { pending in
            let old = pending.map(\.identifier).filter { $0.hasPrefix("riser.sleep.") }
            center.removePendingNotificationRequests(withIdentifiers: old)
            center.getNotificationSettings { settings in
                guard settings.authorizationStatus == .authorized else { return }
                for (i, plan) in plans.enumerated() {
                    let wakeText = plan.wake.formatted(date: .omitted, time: .shortened)
                    let bedText = plan.bedtime.formatted(date: .omitted, time: .shortened)
                    let windDown = plan.bedtime.addingTimeInterval(-30 * 60)
                    if windDown > .now {
                        let c = UNMutableNotificationContent()
                        c.title = "\(name) is getting sleepy 🥱"
                        c.body = "Time to start winding down. Bedtime is \(bedText) so you both get 5 full sleep cycles before your \(wakeText) alarm."
                        c.sound = .default
                        center.add(UNNotificationRequest(identifier: "riser.sleep.wind.\(i)", content: c,
                                                         trigger: UNTimeIntervalNotificationTrigger(timeInterval: windDown.timeIntervalSinceNow, repeats: false)))
                    }
                    if plan.bedtime > .now {
                        let c = UNMutableNotificationContent()
                        c.title = "\(name) is going to sleep 🌙"
                        c.body = "…and so should you! Sleep now for 8 hours (5 full sleep cycles) and you'll wake up refreshed at \(wakeText) tomorrow."
                        c.sound = .default
                        center.add(UNNotificationRequest(identifier: "riser.sleep.bed.\(i)", content: c,
                                                         trigger: UNTimeIntervalNotificationTrigger(timeInterval: plan.bedtime.timeIntervalSinceNow, repeats: false)))
                    }
                }
            }
        }
    }
}
