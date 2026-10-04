import Foundation
import Observation
import SwiftUI

struct ActiveMission: Identifiable, Equatable {
    let id = UUID()
    var mission: MissionKind
    var target: Int
    var sound: AlarmSound
    var startedAt: Date = .now
    /// Started by the player from the app rather than by a ringing alarm.
    var isPractice: Bool
    var sourceAlarmID: UUID? = nil
}

enum BuildStatus: Equatable {
    case built
    case available
    case needsLevel(Int)
    case needsCoins(Int)
    case needsPlus
    case needsFestival
}

@Observable
@MainActor
final class AppModel {
    var state: GameState { didSet { scheduleSave() } }
    let env = EnvironmentService()
    let purchases = PurchaseService()

    var activeMission: ActiveMission?
    var reward: WakeReward? {
        didSet {
            // An alarm that fired while the reward was up is waiting: start it once the reward closes.
            if oldValue != nil && reward == nil && pendingReward == nil { checkInbox() }
        }
    }
    var showPaywall = false
    var paywallReason: String?
    /// Set when an item was just built so the world can play its construction animation.
    var lastBuilt: String?
    /// Set when an island was just bought so the world can raise it into view.
    var lastIsle: Int?
    /// Increments every time the player pets the sprout (world reacts).
    var petTick = 0
    /// Increments to play the morning commute cutscene; the reward shows when it finishes.
    var commuteTick = 0
    var pendingReward: WakeReward?
    /// Plots (index, crop) harvested in this morning's shift, for the cutscene.
    var commuteHarvest: [(Int, String)] = []
    var feedTick = 0

    static let freeAlarmLimit = 2
    private var saveTask: Task<Void, Never>?

    private static var saveURL: URL {
        let dir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir.appendingPathComponent("riser-state.json")
    }

    init() {
        if let data = try? Data(contentsOf: Self.saveURL),
           var saved = try? JSONDecoder().decode(GameState.self, from: data) {
            // Goals saved under older rules (e.g. Item Hunt used to allow several items).
            for i in saved.alarms.indices {
                if saved.alarms[i].mission == .steps {
                    saved.alarms[i].mission = .pushups
                    saved.alarms[i].target = MissionKind.pushups.defaultTarget
                }
                saved.alarms[i].target = saved.alarms[i].mission.clamped(saved.alarms[i].target)
            }
            state = saved
        } else {
            var s = GameState()
            s.alarms = [AlarmItem()]
            state = s
        }
        UserDefaults.standard.set(state.escapeProof, forKey: MissionInbox.escapeProofKey)
        SoundService.shared.musicEnabled = state.islandMusicOn
        SoundService.shared.ambienceEnabled = state.ambienceOn
        SoundService.shared.effectsEnabled = state.sfxOn
    }

    var isPlus: Bool { purchases.isPlus }

    /// Riser is free for a 3-day trial, then needs Riser+. Builds without purchases configured stay open.
    var hasAccess: Bool {
        #if DEBUG
        if UserDefaults.standard.bool(forKey: "forcePaywall") { return isPlus }
        // Screenshot/demo launches skip the paywall.
        if UserDefaults.standard.bool(forKey: "demoHome") { return true }
        #endif
        return isPlus || !purchases.isConfigured
    }

    // MARK: Persistence

    private func scheduleSave() {
        saveTask?.cancel()
        saveTask = Task { [state] in
            try? await Task.sleep(for: .milliseconds(300))
            guard !Task.isCancelled else { return }
            if let data = try? JSONEncoder().encode(state) {
                try? data.write(to: Self.saveURL, options: .atomic)
            }
        }
    }

    // MARK: Missions

    /// Called on launch / foreground / when an alarm intent fires.
    func checkInbox() {
        // A real alarm replaces a practice run (otherwise finishing the practice would swallow the alarm).
        guard activeMission?.isPractice ?? true, reward == nil, let pending = MissionInbox.pending else { return }
        let saved = state.alarms.first { $0.id.uuidString == pending.sourceAlarmID }
        let alarm = saved ?? state.alarms.first ?? AlarmItem()
        // The sound the alarm actually rang with (a test of an unsaved alarm isn't in the list yet).
        let sound = saved?.sound ?? UUID(uuidString: pending.sourceAlarmID).map(MissionInbox.sound(for:)) ?? alarm.sound
        let (mission, rawTarget) = MissionInbox.mission(for: pending.sourceAlarmID) ?? (alarm.mission, alarm.target)
        let target = mission.clamped(rawTarget)
        // The app takes over the ringing so the mission screen controls the sound,
        // and pending re-rings wait while the player is actually doing the mission.
        AlarmService.stopRinging()
        AlarmService.cancelNags()
        activeMission = ActiveMission(mission: mission, target: target, sound: sound, isPractice: false,
                                      sourceAlarmID: UUID(uuidString: pending.sourceAlarmID) ?? alarm.id)
        startMissionGuard()
    }

    private var guardTask: Task<Void, Never>?

    /// Escape-proof: keeps the guard alarm a few seconds ahead for as long as this mission is open on screen.
    func startMissionGuard() {
        guard state.escapeProof, let m = activeMission, !m.isPractice, let source = m.sourceAlarmID else { return }
        guardTask?.cancel()
        guardTask = Task { @MainActor [weak self] in
            while !Task.isCancelled, let self, let now = self.activeMission, !now.isPractice, now.sourceAlarmID == source {
                await AlarmService.armGuard(sourceID: source)
                try? await Task.sleep(for: .seconds(8))
            }
        }
    }

    /// Stops pushing the guard back. It stays booked, so it rings unless the mission is finished.
    private func pauseMissionGuard() {
        guardTask?.cancel()
        guardTask = nil
    }

    /// Back in the app mid-mission: the re-ring armed when the player left isn't needed any more.
    func missionResumed() {
        guard let m = activeMission, !m.isPractice else { return }
        AlarmService.stopRinging()
        AlarmService.cancelNags()
        startMissionGuard()
    }

    /// The app went to the background mid-mission: with escape-proof on, the alarm comes back.
    func missionBackgrounded() {
        guard state.escapeProof, let m = activeMission, !m.isPractice, let source = m.sourceAlarmID else { return }
        pauseMissionGuard()
        MissionInbox.post(sourceAlarmID: source.uuidString)
        // Belt and braces: the guard is already booked, but also queue a normal re-ring if iOS gives us time.
        let task = UIApplication.shared.beginBackgroundTask(withName: "riser.nag")
        Task {
            await AlarmService.scheduleNag(sourceID: source)
            UIApplication.shared.endBackgroundTask(task)
        }
    }

    func startPractice(_ mission: MissionKind, target: Int) {
        activeMission = ActiveMission(mission: mission, target: mission.clamped(target), sound: .sunrise, isPractice: true)
    }

    func completeMission(_ active: ActiveMission, amount: Int) {
        let seconds = Int(Date.now.timeIntervalSince(active.startedAt))
        let firstOfDay = !state.woke && !active.isPractice
        if firstOfDay { evaluateMissedDays() }
        let before = GameState.levelInfo(xp: state.xp)

        var newStreak = state.streak
        if firstOfDay {
            newStreak = nextStreak()
        }

        let base = firstOfDay ? 40 : 8
        let effort = firstOfDay ? active.mission.effortXP(target: amount) : active.mission.effortXP(target: amount) / 5
        let speed = firstOfDay ? (seconds < 90 ? 20 : seconds < 240 ? 10 : 0) : 0
        let streakXP = firstOfDay ? min(newStreak * 5, 50) : 0
        let total = base + effort + speed + streakXP

        // The shift: every won morning, Sprig works the farm (unless he's run away).
        var shift: ShiftReport?
        var sun = 3
        let bonus = 0
        var promotedTo: Int?
        var comeback: Int?
        var cameHome = false
        var recovery = false
        var perfectWeek: Int?
        var masteryUp: [String] = []
        var debtPaid = 0
        if firstOfDay {
            state.consecutiveMisses = 0
            state.mood = min(100, state.mood + 20)
            if state.ranAway {
                // One morning up with him and he's out of bed (a gentle recovery shift follows).
                state.ranAway = false
                state.comebackProgress = 0
                state.sick = true
                cameHome = true
                comeback = 1
                state.mood = max(state.mood, 55)
                sendLetter(from: "\(state.companionName) 🌱", title: "I'm feeling better!",
                           body: "You woke up and came to check on me. I'm out of bed and heading back to the farm. I'll take it easy today. Thank you for looking after me.")
            }
            do {
                // Sprig runs the farm himself: he replants any empty or withered plots.
                state.plots = autoPlanted(state.plots)
                let before = state.plots
                let r = FarmEngine.wonMorning(before)
                let harvested = r.harvest.reduce(0) { $0 + $1.count }
                let growing = r.plots.filter { $0.crop != nil && !$0.dead }.count
                let rankBefore = state.rank
                state.careerPoints += 1
                if state.rank > rankBefore {
                    promotedTo = state.rank
                    let rk = state.rankInfo
                    sendLetter(from: "Farmer Figg 🧑‍🌾", title: "Promotion: \(rk.title)!",
                               body: "\(state.companionName) has shown up bright and early day after day. Effective immediately, you're promoted to \(rk.title) \(rk.emoji). Your daily wage is now \(rk.wage) coins. Keep it up!")
                }
                var wage = FarmEngine.wage(streak: newStreak, plus: isPlus, rank: state.rank)
                if state.sick {
                    recovery = true
                    wage /= 2
                    state.sick = false
                }
                var pay = FarmEngine.pay(harvest: r.harvest, wage: wage, mood: state.mood - 20)
                if recovery { pay = pay * 2 / 3 }
                shift = ShiftReport(harvest: r.harvest, wage: wage, moodMultiplier: MoodTier(mood: state.mood - 20).payMultiplier,
                                    total: pay, watered: growing)
                commuteHarvest = before.enumerated().compactMap { i, p in
                    guard let c = p.crop, !p.dead, let crop = FarmCatalog.crop(c), p.growth + 1 >= crop.mornings else { return nil }
                    return (i, c)
                }
                for line in r.harvest {
                    let before = Career.stars(harvested: state.mastery[line.crop] ?? 0)
                    state.mastery[line.crop, default: 0] += line.count
                    if Career.stars(harvested: state.mastery[line.crop] ?? 0) > before { masteryUp.append(line.crop) }
                }
                state.plots = r.plots
                state.cropsHarvested += harvested
                state.coinsEarned += pay
                state.lastShift = shift
                let cal = Calendar.current
                let fivePM = cal.date(bySettingHour: 17, minute: 0, second: 0, of: .now) ?? .now
                state.workUntil = max(fivePM, Date.now.addingTimeInterval(8 * 3600))
                sun = pay
                // Perfect week: every alarm morning this week won.
                if let bonusCoins = checkPerfectWeek() {
                    perfectWeek = bonusCoins
                    sun += bonusCoins
                }
            }
            // Wages pay off debt first.
            if state.debt > 0 && sun > 0 {
                debtPaid = min(state.debt, sun)
                state.debt -= debtPaid
                sun -= debtPaid
                if state.debt == 0 {
                    sendLetter(from: "Island Council 🏛️", title: "Debt cleared",
                               body: "Thank you! Your island upkeep is fully paid. The shops are open to you again.")
                }
            }
        }

        state.xp += total
        state.coins += sun + bonus
        if firstOfDay {
            state.streak = newStreak
            state.bestStreak = max(state.bestStreak, newStreak)
            state.lastWakeDay = .now
        }
        state.history.append(WakeRecord(date: .now, mission: active.mission, amount: amount,
                                        secondsToComplete: seconds, xp: total, coins: sun + bonus,
                                        isPractice: active.isPractice))
        // A one-off alarm is done once it has been answered.
        if let src = active.sourceAlarmID, let i = state.alarms.firstIndex(where: { $0.id == src }),
           state.alarms[i].weekdays.isEmpty, state.alarms[i].isEnabled {
            state.alarms[i].isEnabled = false
        }
        let after = GameState.levelInfo(xp: state.xp)

        // Seasonal event chest: one per festival morning.
        var chest: Int?
        var festivalReward: HarvestFestival.Reward?
        let cal = Calendar.current
        if firstOfDay && HarvestFestival.isActive() && !(state.lastFestivalDay.map(cal.isDateInToday) ?? false) {
            state.festivalChests += 1
            state.lastFestivalDay = .now
            let n = state.festivalChests
            chest = n
            let r = HarvestFestival.reward(forChest: n)
            festivalReward = r
            switch r {
            case .decor(let id): if !state.unlockedDecor.contains(id) { state.unlockedDecor.append(id) }
            case .hat(let id): if !state.ownedHats.contains(id) { state.ownedHats.append(id) }
            case .coins(let n): state.coins += n
            }
        }
        let canAdventure = false

        let newAchievements = checkAchievements()
        if !active.isPractice {
            // Stop re-booking the guard first, so a booking can't land after it's been cancelled.
            pauseMissionGuard()
            AlarmService.missionCompleted(keeping: Set(state.alarms.map(\.id)))
            MissionInbox.clear()
        }
        SoundService.shared.stopAlarmLoop()

        reward = WakeReward(
            mission: active.mission, amount: amount, seconds: seconds,
            baseXP: base, effortXP: effort, speedXP: speed, streakXP: streakXP,
            coins: sun, bonusCoins: bonus, newStreak: state.streak,
            previousLevel: before.level, newLevel: after.level,
            previousProgress: before.progress, newProgress: after.progress,
            isPractice: !firstOfDay,
            festivalChest: chest,
            festivalReward: festivalReward,
            canAdventure: canAdventure,
            shift: shift,
            promotedTo: promotedTo,
            comeback: comeback,
            cameHome: cameHome,
            recoveryShift: recovery,
            perfectWeekBonus: perfectWeek,
            masteryUp: masteryUp,
            debtPaid: debtPaid,
            achievements: newAchievements
        )
        activeMission = nil
        // Play the commute to work first; the shift report follows.
        if shift != nil {
            pendingReward = reward
            reward = nil
            commuteTick += 1
        }
    }

    func abandonPractice() {
        guard let m = activeMission, m.isPractice else { return }
        SoundService.shared.stopAlarmLoop()
        activeMission = nil
    }

    /// The streak counts alarm mornings: days off in between don't break it, and a missed alarm
    /// morning only survives if a streak freeze covered it (see `evaluateMissedDays`).
    private func nextStreak() -> Int {
        let cal = Calendar.current
        guard let last = state.lastWakeDay else { return 1 }
        if cal.isDateInToday(last) { return state.streak }
        let frozen = Set(state.frozenDays.map { cal.startOfDay(for: $0) })
        var day = cal.date(byAdding: .day, value: 1, to: cal.startOfDay(for: last))!
        let today = cal.startOfDay(for: .now)
        while day < today {
            if isMissableAlarmDay(day) && !frozen.contains(day) { return 1 }
            day = cal.date(byAdding: .day, value: 1, to: day)!
        }
        return state.streak + 1
    }

    /// Riser+ members get one streak freeze a week.
    func grantWeeklyFreezeIfNeeded() {
        guard isPlus else { return }
        if let last = state.lastFreezeGrant, Date.now.timeIntervalSince(last) < 7 * 86400 { return }
        state.streakFreezes = min(state.streakFreezes + 1, 2)
        state.lastFreezeGrant = .now
    }

    // MARK: Adventures

    var tripReturned: Bool {
        guard let trip = state.trip else { return false }
        return env.now >= trip.returns
    }

    /// Adventures happen on days off (no alarm today), once per day.
    var canStartAdventure: Bool {
        guard state.trip == nil, !isAtWork, !state.ranAway, !state.sick else { return false }
        return isDayOff(.now) && !(state.lastAdventureDay.map(Calendar.current.isDateInToday) ?? false)
    }

    func isAlarmDay(_ date: Date) -> Bool {
        let weekday = Calendar.current.component(.weekday, from: date)
        return state.alarms.contains { $0.isEnabled && $0.weekdays.contains(weekday) }
    }

    func isDayOff(_ date: Date) -> Bool { !isAlarmDay(date) }

    /// An alarm day whose alarm existed when it rang (a new alarm can't cause a miss the same morning).
    func isMissableAlarmDay(_ day: Date) -> Bool {
        let cal = Calendar.current
        let weekday = cal.component(.weekday, from: day)
        return state.alarms.contains { a in
            guard a.isEnabled, a.weekdays.contains(weekday) else { return false }
            guard let created = a.createdAt,
                  let rang = cal.date(bySettingHour: a.hour, minute: a.minute, second: 0, of: day) else { return true }
            return rang > created
        }
    }

    var isAtWork: Bool {
        guard !state.ranAway, let until = state.workUntil else { return false }
        return env.now < until && Calendar.current.isDateInToday(until)
    }

    /// Finishes the commute cutscene and reveals the shift report.
    func finishCommute() {
        if let r = pendingReward {
            pendingReward = nil
            reward = r
        }
        commuteHarvest = []
    }

    // MARK: Farm

    /// Sprig tends the farm on his own: empty or withered plots get fresh seeds.
    func autoPlanted(_ plots: [PlotState]) -> [PlotState] {
        var out = plots
        while out.count < FarmCatalog.maxPlots { out.append(PlotState()) }
        let crops = FarmCatalog.crops.filter { !$0.premium || isPlus }.filter { state.level >= $0.level }
        for i in out.indices where out[i].isEmpty || out[i].dead {
            out[i] = PlotState(crop: (crops.randomElement() ?? FarmCatalog.crops[0]).id)
        }
        return out
    }

    // MARK: Vacations

    /// The next day with no alarm (today counts if it's still before 3 PM).
    func nextDayOff(from now: Date = .now) -> Date? {
        let cal = Calendar.current
        let today = cal.startOfDay(for: now)
        for i in 0..<14 {
            guard let day = cal.date(byAdding: .day, value: i, to: today) else { continue }
            if i == 0 && cal.component(.hour, from: now) >= 15 { continue }
            if isDayOff(day) { return day }
        }
        return nil
    }

    var canBookVacation: Bool {
        state.bookedTrip == nil && state.trip == nil && !state.ranAway
    }

    /// Pays for a vacation. Sprig leaves right away on a day off, otherwise on the next day off.
    @discardableResult
    func bookVacation(_ dest: Destination) -> Bool {
        guard canBookVacation, let info = VacationCatalog.info(for: dest.id), state.level >= dest.level else { return false }
        guard guardDebt() else { return false }
        guard state.coins >= info.price else {
            SoundService.shared.play(.nope)
            Haptics.warning()
            return false
        }
        guard let day = nextDayOff() else { return false }
        state.coins -= info.price
        state.bookedTrip = BookedTrip(destination: dest.id, day: day)
        SoundService.shared.play(.build)
        Haptics.success()
        startBookedTripIfDue()
        if state.trip == nil {
            sendLetter(from: "\(state.companionName) 🌱", title: "Vacation booked! 🎈",
                       body: "We're going to \(dest.name) on \(day.formatted(.dateTime.weekday(.wide))) and staying at the \(info.stay). I'm already packing!")
        }
        return true
    }

    /// Starts a booked vacation when its day off arrives (from 9 AM).
    func startBookedTripIfDue() {
        guard let booked = state.bookedTrip, state.trip == nil, !state.ranAway, !isAtWork,
              let dest = AdventureCatalog.destination(booked.destination) else { return }
        let cal = Calendar.current
        let now = env.now
        let today = cal.startOfDay(for: now)
        guard booked.day <= today else { return }
        // Today's trip leaves from 6 AM; an overdue one (he was sick or working) leaves as soon as he's free.
        if booked.day == today && cal.component(.hour, from: now) < 6 { return }
        state.bookedTrip = nil
        startAdventure(to: dest, morningXP: 100, force: true)
    }

    /// (Adventures are now booked vacations.)
    func autoAdventureIfNeeded() { startBookedTripIfDue() }

    func petted() {
        let cal = Calendar.current
        if !(state.lastPetDay.map(cal.isDateInToday) ?? false) {
            state.petsToday = 0
            state.lastPetDay = .now
        }
        if state.petsToday < 5 {
            state.petsToday += 1
            state.mood = min(100, state.mood + 1)
        }
    }

    // MARK: Needs & missed mornings

    /// (Hunger was removed; kept as a no-op so callers stay simple.)
    func updateNeeds(now: Date = .now) {}

    /// Walks every day since the last check. Each missed alarm morning climbs the neglect ladder:
    /// 1 wilt · 2 crops die + demotion + storm cloud · 3 sick · 5 Sprig runs away.
    func evaluateMissedDays(now: Date = .now) {
        let cal = Calendar.current
        let today = cal.startOfDay(for: now)
        chargeUpkeepIfNeeded(now: now)
        guard let last = state.lastEvaluatedDay else {
            state.lastEvaluatedDay = cal.date(byAdding: .day, value: -1, to: today)
            return
        }
        var day = cal.date(byAdding: .day, value: 1, to: cal.startOfDay(for: last))!
        let wonDays = state.wonDays
        while day < today {
            if isMissableAlarmDay(day) {
                if wonDays.contains(day) {
                    state.consecutiveMisses = 0
                } else if state.streakFreezes > 0 && state.consecutiveMisses == 0 {
                    state.streakFreezes -= 1
                    state.frozenDays = (state.frozenDays + [day]).suffix(20)
                    sendLetter(from: "\(state.companionName) 🌱", title: "Streak freeze used ❄️",
                               body: "You slept in, but your streak freeze kept the farm watered. Phew! Let's get up together tomorrow.")
                } else {
                    applyMiss()
                }
            }
            day = cal.date(byAdding: .day, value: 1, to: day)!
        }
        state.lastEvaluatedDay = cal.date(byAdding: .day, value: -1, to: today)
    }

    private func applyMiss() {
        state.consecutiveMisses += 1
        let n = state.consecutiveMisses
        state.streak = 0
        state.plots = FarmEngine.missedMorning(state.plots, consecutive: n)
        state.mood = max(0, state.mood - 30)
        let name = state.companionName
        switch n {
        case 1:
            sendLetter(from: "Farmer Figg 🧑‍🌾", title: "Where was \(name)?",
                       body: "\(name) didn't show up for work this morning. The crops are thirsty and starting to wilt. One more missed morning and they won't make it.")
        case 2:
            let old = state.rank
            if old > 0 { state.careerPoints = Career.ranks[old - 1].points }
            sendLetter(from: "Farmer Figg 🧑‍🌾", title: old > 0 ? "Demoted to \(Career.ranks[old - 1].title)" : "Final warning",
                       body: "Two mornings in a row without \(name). The wilted crops have withered, and I've had to \(old > 0 ? "move \(name) down to \(Career.ranks[old - 1].title)" : "put \(name) on a final warning"). A gloomy little rain cloud has started following \(name) around.")
        case 3:
            state.sick = true
            sendLetter(from: "\(name) 🌱", title: "Achoo…",
                       body: "That little rain cloud has been following me around and now I've caught a cold. I feel all green and wobbly. My next shift will be slow. Please wake up with me tomorrow?")
        case Career.runawayAfter:
            state.ranAway = true
            state.sick = true
            state.comebackProgress = 0
            state.workUntil = nil
            sendLetter(from: "\(name) 🌱", title: "Too sick to get out of bed",
                       body: "You haven't woken up with me in \(n) mornings. I've been waiting in the rain under my little cloud and now I'm really sick. I'm stuck in bed with a thermometer. Please wake up tomorrow morning and come make me feel better?")
        default:
            break
        }
    }

    /// Weekly island upkeep, charged each new week. Unpaid bills become debt.
    private func chargeUpkeepIfNeeded(now: Date) {
        let cal = Calendar.current
        let week = cal.component(.yearForWeekOfYear, from: now) * 100 + cal.component(.weekOfYear, from: now)
        guard let last = state.lastUpkeepWeek else {
            state.lastUpkeepWeek = week
            return
        }
        guard week > last else { return }
        state.lastUpkeepWeek = week
        // Weekly recap of last week's mornings.
        if let lastWeek = cal.date(byAdding: .weekOfYear, value: -1, to: now),
           let interval = cal.dateInterval(of: .weekOfYear, for: lastWeek) {
            let won = Set(state.history.filter { $0.isWin && interval.contains($0.date) }.map { cal.startOfDay(for: $0.date) })
            var alarmDays = 0
            var d = interval.start
            while d < interval.end {
                if isAlarmDay(d) { alarmDays += 1 }
                d = cal.date(byAdding: .day, value: 1, to: d)!
            }
            if alarmDays > 0 {
                let line = won.count >= alarmDays ? "A perfect week. \(state.companionName) is beaming!" :
                    won.count == 0 ? "No mornings won. \(state.companionName) missed you. This week's a fresh start." :
                    "Every morning counts. Let's aim for \(min(alarmDays, won.count + 1)) this week!"
                sendLetter(from: "\(state.companionName) 🌱", title: "Our week: \(won.count) of \(alarmDays) mornings",
                           body: "We woke up together \(won.count) of \(alarmDays) alarm mornings last week. \(line)")
            }
        }
        let buildings = state.built.filter { $0 != "tent" }.count
        let bill = Career.upkeep(buildings: buildings)
        if state.coins >= bill {
            state.coins -= bill
            sendLetter(from: "Island Council 🏛️", title: "Weekly upkeep: \(bill) coins",
                       body: "Thanks for keeping your \(buildings) building\(buildings == 1 ? "" : "s") in good repair. \(bill) coins were paid from your savings.")
        } else {
            state.debt += bill - state.coins
            state.coins = 0
            sendLetter(from: "Island Council 🏛️", title: "Unpaid upkeep: \(state.debt) coins owed",
                       body: "Your island's upkeep couldn't be paid. Until the debt is cleared the island will look run-down and the shops are closed to you. \(state.companionName)'s wages will go toward the debt first.")
        }
    }

    /// Returns a bonus if every alarm morning this week (so far through today) has been won, once per week.
    private func checkPerfectWeek(now: Date = .now) -> Int? {
        let cal = Calendar.current
        let week = cal.component(.yearForWeekOfYear, from: now) * 100 + cal.component(.weekOfYear, from: now)
        guard state.lastPerfectWeek != week,
              let interval = cal.dateInterval(of: .weekOfYear, for: now) else { return nil }
        let wonDays = state.wonDays
        var day = interval.start
        var alarmDays = 0
        var allWon = true
        while day < interval.end {
            if isAlarmDay(day) {
                alarmDays += 1
                if !(wonDays.contains(day) || cal.isDateInToday(day)) { allWon = false }
            }
            day = cal.date(byAdding: .day, value: 1, to: day)!
        }
        // Only award on the week's last alarm day.
        let remaining = (1...6).compactMap { cal.date(byAdding: .day, value: $0, to: cal.startOfDay(for: now)) }
            .filter { $0 < interval.end && isAlarmDay($0) }
        guard allWon, alarmDays >= 3, remaining.isEmpty else { return nil }
        state.lastPerfectWeek = week
        return 40 + alarmDays * 10
    }

    /// Pays out any newly reached achievements. Returns their ids.
    @discardableResult
    func checkAchievements(announce: Bool = true) -> [String] {
        var unlocked: [String] = []
        for a in AchievementCatalog.all where !state.claimedAchievements.contains(a.id) && a.progress(state) >= a.goal {
            state.claimedAchievements.append(a.id)
            state.coins += a.reward
            unlocked.append(a.id)
            if announce {
                sendLetter(from: "Island Council 🏛️", title: "Achievement: \(a.title)",
                           body: "\(a.detail) ✓. Here's \(a.reward) coins to celebrate!")
            }
        }
        return unlocked
    }

    /// The very first letters: Sprig's new job, bedtime and days off.
    func sendWelcomeLetters() {
        guard state.letters.isEmpty else { return }
        let name = state.companionName
        sendLetter(from: "Farmer Figg 🧑‍🌾", title: "Welcome to the farm!",
                   body: "Morning! I hear \(name) is looking for work. Here's the deal: every morning you both get up on time, \(name) flies over to my Farm Island, works a shift and earns coins. Show up and you'll be promoted. Sleep through the alarm and, well… the crops won't be happy. Neither will I.")
        sendLetter(from: "\(name) 🌱", title: "Hi! It's me!",
                   body: "I'll go to bed at the time Riser works out from your alarm, so we both get proper sleep. On days without an alarm we can go on vacation! Let's build the coziest island ever.")
    }

    func sendLetter(from: String, title: String, body: String) {
        state.letters.insert(Letter(from: from, title: title, body: body), at: 0)
        if state.letters.count > 40 { state.letters.removeLast(state.letters.count - 40) }
    }

    func markLettersRead() {
        for i in state.letters.indices { state.letters[i].read = true }
    }

    var inDebt: Bool { state.debt > 0 }

    #if DEBUG
    func debugMiss() {
        applyMiss()
    }

    func debugResetNeglect() {
        state.consecutiveMisses = 0
        state.sick = false
        state.ranAway = false
        state.debt = 0
        state.mood = 80
    }
    #endif

    /// Blocks spending while in debt.
    private func guardDebt() -> Bool {
        if inDebt {
            SoundService.shared.play(.nope)
            Haptics.warning()
            return false
        }
        return true
    }

    /// Three destinations to choose from today (Riser+ sees every unlocked one).
    func adventureOptions(on date: Date = .now) -> [Destination] {
        let unlocked = AdventureCatalog.destinations.filter { state.level >= $0.level }
        if isPlus || unlocked.count <= 3 { return unlocked }
        let day = Calendar.current.ordinality(of: .day, in: .era, for: date) ?? 0
        var rng = SeededRandom(seed: UInt64(day) &* 40503)
        var pool = unlocked
        var picks: [Destination] = []
        // Always offer the newest unlocked place so progress feels fresh.
        if let newest = pool.max(by: { $0.level < $1.level }) {
            picks.append(newest)
            pool.removeAll { $0.id == newest.id }
        }
        while picks.count < 3 && !pool.isEmpty {
            picks.append(pool.remove(at: Int(rng.next() * Double(pool.count)) % pool.count))
        }
        return picks
    }

    func startAdventure(to destination: Destination, morningXP: Int, force: Bool = false) {
        guard force || canStartAdventure else { return }
        let found = state.discoveredIDs
        let fresh = destination.discoveries.filter { !found.contains($0.id) }
        let discovery = (fresh.isEmpty ? destination.discoveries : fresh).randomElement()!
        let souvenir = destination.souvenirs.randomElement()!
        var hat: String?
        if let h = destination.exclusiveHat, !state.ownedHats.contains(h),
           discovery.id.hasSuffix("6") || Double.random(in: 0...1) < 0.2 {
            hat = h
        }
        var hours = min(6, max(2, 6 - Double(morningXP - 80) / 60))
        if isPlus { hours *= 0.75 }
        #if DEBUG
        if let m = UserDefaults.standard.object(forKey: "adventureMinutes") as? Double
            ?? Double(UserDefaults.standard.string(forKey: "adventureMinutes") ?? "") {
            hours = m / 60
        }
        #endif
        var returns = Date.now.addingTimeInterval(hours * 3600)
        if force {
            // A vacation lasts until early evening (at least 3 hours).
            let evening = Calendar.current.date(bySettingHour: 18, minute: 0, second: 0, of: .now) ?? returns
            returns = max(evening, Date.now.addingTimeInterval(3 * 3600))
            #if DEBUG
            if let m = UserDefaults.standard.object(forKey: "adventureMinutes") as? Double
                ?? Double(UserDefaults.standard.string(forKey: "adventureMinutes") ?? "") {
                returns = Date.now.addingTimeInterval(m * 60)
            }
            #endif
        }
        state.trip = AdventureTrip(destination: destination.id, discovery: discovery.id, souvenir: souvenir.id,
                                   hatFound: hat, coins: 15 + state.level * 2, departed: .now, returns: returns)
        state.lastAdventureDay = .now
        state.canAdventureDay = nil
        Notifications.scheduleReturn(name: state.companionName, place: destination.name, at: returns)
    }

    /// Opens the postcard: files the discovery and hands over the souvenirs.
    func finishTrip(reply: Int) {
        guard let trip = state.trip else { return }
        state.logbook.append(LogEntry(discovery: trip.discovery, date: .now, reply: reply))
        state.souvenirs[trip.souvenir, default: 0] += 1
        state.coins += trip.coins
        if let h = trip.hatFound, !state.ownedHats.contains(h) { state.ownedHats.append(h) }
        state.trip = nil
        checkAchievements()
        SoundService.shared.play(.coin)
        Haptics.success()
    }

    // MARK: Wardrobe

    func buyHat(_ hat: Hat) -> Bool {
        guard !state.ownedHats.contains(hat.id) else { return false }
        if hat.premium && !isPlus {
            requirePlus("The \(hat.name) is part of Riser+")
            return false
        }
        guard state.coins >= hat.price else {
            SoundService.shared.play(.nope)
            Haptics.warning()
            return false
        }
        guard guardDebt() else { return false }
        state.coins -= hat.price
        state.ownedHats.append(hat.id)
        state.equippedHat = hat.id
        SoundService.shared.play(.build)
        Haptics.success()
        return true
    }

    func equip(_ hat: String?) {
        state.equippedHat = hat
        petTick += 1
        SoundService.shared.play(.pet)
        Haptics.select()
    }

    // MARK: Interior decor

    func buyFurniture(_ item: FurnitureItem) -> Bool {
        guard !state.ownedFurniture.contains(item.id) else { return false }
        if item.premium && !isPlus {
            requirePlus("The \(item.name) is part of Riser+")
            return false
        }
        guard guardDebt() else { return false }
        guard state.coins >= item.price else {
            SoundService.shared.play(.nope)
            Haptics.warning()
            return false
        }
        state.coins -= item.price
        state.ownedFurniture.append(item.id)
        // Auto-place it in the first free matching spot.
        let home = state.homeKind
        let slots = item.kind == .floor ? InteriorCatalog.floorSlots : InteriorCatalog.wallSlots
        var layout = state.layouts[home] ?? [:]
        if let free = slots.first(where: { layout[$0] == nil }) {
            layout[free] = item.id
            state.layouts[home] = layout
        }
        SoundService.shared.play(.build)
        Haptics.success()
        return true
    }

    func place(_ itemID: String?, in slot: String) {
        let home = state.homeKind
        var layout = state.layouts[home] ?? [:]
        if let itemID {
            // An item lives in one spot at a time.
            for (k, v) in layout where v == itemID { layout[k] = nil }
        }
        layout[slot] = itemID
        state.layouts[home] = layout
        checkAchievements()
        SoundService.shared.play(.tap)
        Haptics.select()
    }

    func applyStyle(_ style: RoomStyle) {
        let owned = style.price == 0 || state.ownedStyles.contains(style.id)
        if !owned {
            guard guardDebt() else { return }
            guard state.coins >= style.price else {
                SoundService.shared.play(.nope)
                Haptics.warning()
                return
            }
            state.coins -= style.price
            state.ownedStyles.append(style.id)
            SoundService.shared.play(.build)
        } else {
            SoundService.shared.play(.tap)
        }
        let home = state.homeKind
        var styles = state.roomStyles[home] ?? [:]
        styles[style.surface.rawValue] = style.id
        state.roomStyles[home] = styles
        Haptics.success()
    }

    // MARK: Building

    func status(of item: Buildable) -> BuildStatus {
        if state.built.contains(item.id) { return .built }
        if BuildCatalog.eventItems.contains(item.id) {
            return state.unlockedDecor.contains(item.id) ? .available : .needsFestival
        }
        if item.premium && !isPlus { return .needsPlus }
        if state.level < item.level { return .needsLevel(item.level) }
        if state.coins < item.cost { return .needsCoins(item.cost - state.coins) }
        return .available
    }

    @discardableResult
    func build(_ item: Buildable, at spot: ItemPlacement? = nil) -> Bool {
        guard status(of: item) == .available else {
            if status(of: item) == .needsPlus {
                paywallReason = "\(item.name) is part of Riser+"
                showPaywall = true
            } else {
                SoundService.shared.play(.nope)
                Haptics.warning()
            }
            return false
        }
        guard guardDebt() else { return false }
        state.coins -= item.cost
        let replaced = BuildCatalog.replaces(item)
        state.built.removeAll { replaced.contains($0) }
        state.built.append(item.id)
        if let spot, BuildCatalog.isMovable(item.id) { state.placements[item.id] = spot }
        lastBuilt = item.id
        checkAchievements()
        SoundService.shared.play(.build)
        Haptics.success()
        return true
    }

    // MARK: Alarms

    var canAddAlarm: Bool { isPlus || state.alarms.count < Self.freeAlarmLimit }

    func upsert(_ alarm: AlarmItem) {
        if let i = state.alarms.firstIndex(where: { $0.id == alarm.id }) {
            state.alarms[i] = alarm
        } else {
            state.alarms.append(alarm)
        }
        syncAlarms()
    }

    func delete(_ alarm: AlarmItem) {
        state.alarms.removeAll { $0.id == alarm.id }
        syncAlarms()
    }

    func syncAlarms() {
        let alarms = state.alarms
        Task { await AlarmService.sync(alarms) }
        scheduleBedtimeReminder()
    }

    // MARK: Sleep

    /// 5 full 90-minute sleep cycles plus 30 minutes to drift off: 8 hours before the alarm.
    static let sleepCycles = 5
    static let fallAsleepMinutes = 30
    static var sleepDuration: TimeInterval { TimeInterval(sleepCycles * 90 + fallAsleepMinutes) * 60 }

    /// Tonight's bedtime and the wake-up it's planned around (the next alarm, or 7:00 without one).
    func sleepPlan(at now: Date) -> (bedtime: Date, wake: Date) {
        let wake = state.alarms.filter(\.isEnabled)
            .compactMap { $0.nextFireDate(after: now) }
            .min() ?? Calendar.current.nextDate(after: now, matching: DateComponents(hour: 7, minute: 0), matchingPolicy: .nextTime) ?? now
        return (wake.addingTimeInterval(-Self.sleepDuration), wake)
    }

    /// Between bedtime and the alarm, Sprig is tucked up in bed.
    var isSleepTime: Bool {
        let now = env.effectiveDate
        let plan = sleepPlan(at: now)
        return now >= plan.bedtime && now < plan.wake
    }

    /// Minutes until bedtime when it's getting close (within 45 min), else nil.
    var minutesToBedtime: Int? {
        let now = env.effectiveDate
        let m = Int(sleepPlan(at: now).bedtime.timeIntervalSince(now) / 60)
        return (0...45).contains(m) ? m : nil
    }

    /// Schedules wind-down + bedtime notifications for the next week of alarm mornings.
    func scheduleBedtimeReminder() {
        var plans: [(bedtime: Date, wake: Date)] = []
        var cursor = Date.now
        let enabled = state.alarms.filter(\.isEnabled)
        guard !enabled.isEmpty else {
            Notifications.scheduleSleep(name: state.companionName, plans: [])
            return
        }
        for _ in 0..<7 {
            guard let wake = enabled.compactMap({ $0.nextFireDate(after: cursor) }).min() else { break }
            plans.append((wake.addingTimeInterval(-Self.sleepDuration), wake))
            cursor = wake.addingTimeInterval(60)
        }
        Notifications.scheduleSleep(name: state.companionName, plans: plans)
    }

    var nextAlarm: (AlarmItem, Date)? {
        state.alarms.filter(\.isEnabled)
            .compactMap { a in a.nextFireDate().map { (a, $0) } }
            .min { $0.1 < $1.1 }
    }

    func setEscapeProof(_ on: Bool) {
        state.escapeProof = on
        UserDefaults.standard.set(on, forKey: MissionInbox.escapeProofKey)
    }

    // MARK: Sound settings

    func setMusic(_ on: Bool) {
        state.islandMusicOn = on
        SoundService.shared.musicEnabled = on
    }

    func setAmbience(_ on: Bool) {
        state.ambienceOn = on
        SoundService.shared.ambienceEnabled = on
    }

    func setEffects(_ on: Bool) {
        state.sfxOn = on
        SoundService.shared.effectsEnabled = on
    }

    var allSoundOff: Bool { !state.islandMusicOn && !state.ambienceOn && !state.sfxOn }

    func requirePlus(_ reason: String) {
        paywallReason = reason
        showPaywall = true
    }
}
