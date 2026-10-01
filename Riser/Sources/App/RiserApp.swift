import Combine
import SwiftUI

@main
struct RiserApp: App {
    @State private var model = AppModel()
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(model)
                .preferredColorScheme(.dark)
                .task {
                    #if DEBUG
                    let args = UserDefaults.standard
                    if args.bool(forKey: "demoHome") { model.state.hasOnboarded = true }
                    if let n = args.string(forKey: "demoName") { model.state.companionName = n }
                    if let h = args.object(forKey: "skyHour") as? Double ?? Double(args.string(forKey: "skyHour") ?? "") {
                        let start = Calendar.current.startOfDay(for: .now)
                        model.env.timeOverride = start.addingTimeInterval(h * 3600)
                    }
                    if let w = args.string(forKey: "skyWeather") { model.env.weatherOverride = WeatherKind(rawValue: w) }
                    if args.bool(forKey: "demoBuilt") {
                        model.state.built = ["cottage", "campfire", "flowers", "lamppost", "treeRound", "bench", "mailbox", "garden", "pine", "pond", "lanterns", "treeBlossom", "telescope", "windmill"]
                        model.state.xp = 900
                        model.state.streak = 12
                        model.state.bestStreak = 12
                        model.state.coins = 245
                        model.state.ownedHats = Wardrobe.hats.map(\.id)
                        model.state.unlockedDecor = ["pumpkins", "scarecrow", "maple"]
                        model.state.built += ["pumpkins", "scarecrow", "maple"]
                        // A lived-in history: the last 12 days all won.
                        let cal = Calendar.current
                        model.state.history = (1...12).reversed().compactMap { d in
                            cal.date(byAdding: .day, value: -d, to: cal.date(bySettingHour: 6, minute: 58, second: 0, of: .now)!)
                                .map { WakeRecord(date: $0, mission: d % 3 == 0 ? .squats : .pushups, amount: 12, secondsToComplete: 70, xp: 120, coins: 40) }
                        }
                        model.state.lastWakeDay = cal.date(byAdding: .day, value: -1, to: .now)
                        model.state.lastEvaluatedDay = cal.date(byAdding: .day, value: -1, to: .now)
                        for i in model.state.letters.indices { model.state.letters[i].read = true }
                        model.state.claimedAchievements = AchievementCatalog.all.map(\.id)
                    }
                    if args.bool(forKey: "demoNoTrip") { model.state.trip = nil }
                    if args.bool(forKey: "demoIsles") {
                        model.state.isles = [1, 2]
                        model.state.coins = max(model.state.coins, 900)
                        if args.bool(forKey: "demoIsleDecor") {
                            let plan: [(String, Int)] = [("gazebo", 1), ("fountain", 1), ("bushes", 1), ("archway", 1), ("beehive", 1),
                                                         ("swing", 1), ("lighthouse", 2), ("hammock", 2), ("picnic", 2), ("boulders", 2),
                                                         ("signpost", 0), ("well", 2)]
                            for (id, island) in plan where !model.state.built.contains(id) {
                                if let spot = model.freeSpot(for: id, on: island) {
                                    model.state.built.append(id)
                                    model.state.placements[id] = spot
                                }
                            }
                        }
                    }
                    if args.bool(forKey: "demoFresh") { model.state.hasOnboarded = false }
                    if args.bool(forKey: "demoDecor") {
                        model.state.ownedFurniture = InteriorCatalog.furniture.map(\.id)
                        model.state.layouts = [
                            "cottage": ["SlotFloor1": "armchair", "SlotFloor2": "plant", "SlotFloor3": "aquarium", "SlotWall1": "garland", "SlotWall2": "poster_sun"],
                            "tent": ["SlotFloor1": "beanbag", "SlotFloor2": "teddy", "SlotFloor3": "floorlamp", "SlotWall1": "garland", "SlotWall2": "clock"],
                        ]
                        model.state.roomStyles = ["cottage": ["wall": "wall.mint", "floor": "floor.cherry"], "tent": ["canvas": "canvas.teal"]]
                    }
                    if args.bool(forKey: "demoTent") {
                        model.state.built.removeAll { $0 == "cottage" }
                        if !model.state.built.contains("tent") { model.state.built.append("tent") }
                    }
                    if args.object(forKey: "demoMiss") != nil {
                        model.debugResetNeglect()
                        for _ in 0..<args.integer(forKey: "demoMiss") { model.debugMiss() }
                    }
                    if args.object(forKey: "demoDebt") != nil { model.state.debt = args.integer(forKey: "demoDebt") }
                    let failures = FarmEngine.selfTest()
                    print(failures.isEmpty ? "✅ FarmEngine self-test passed" : "❌ FarmEngine self-test: \(failures)")
                    if let m = args.string(forKey: "demoMood") { model.state.mood = m == "sad" ? 20 : m == "happy" ? 90 : 50 }
                    if args.object(forKey: "demoMissed") != nil {
                        let n = args.integer(forKey: "demoMissed")
                        model.state.plots = [PlotState(crop: "carrot", growth: 1), PlotState(crop: "corn", growth: 2),
                                             PlotState(crop: "strawberry"), PlotState()]
                        for i in 1...max(1, n) {
                            model.state.plots = FarmEngine.missedMorning(model.state.plots, consecutive: i)
                        }
                    }
                    if args.bool(forKey: "demoCrops") {
                        model.state.plots = [PlotState(crop: "carrot", growth: 2), PlotState(crop: "pumpkin", growth: 3),
                                             PlotState(crop: "strawberry", growth: 1), PlotState(crop: "corn", growth: 2)]
                    }
                    if args.bool(forKey: "demoAtWork") {
                        let hour = args.object(forKey: "demoWorkUntil") != nil ? args.integer(forKey: "demoWorkUntil") : 23
                        model.state.workUntil = Calendar.current.date(bySettingHour: hour, minute: hour == 23 ? 50 : 0, second: 0, of: .now)
                    }
                    if args.bool(forKey: "demoNotWorking") { model.state.workUntil = nil }
                    if let hat = args.string(forKey: "demoHat") {
                        model.state.equippedHat = hat == "none" ? nil : hat
                    }
                    // Launch video: the island grows piece by piece with the real construction animation.
                    if args.bool(forKey: "demoGrow") {
                        let order = ["campfire", "flowers", "treeRound", "bench", "lamppost", "mailbox", "garden", "pine", "cottage",
                                     "pond", "lanterns", "treeBlossom", "windmill", "telescope", "maple", "pumpkins", "scarecrow"]
                        model.state.built = ["tent"]
                        model.state.unlockedDecor = ["pumpkins", "scarecrow", "maple"]
                        let delay = args.double(forKey: "growDelay") > 0 ? args.double(forKey: "growDelay") : 3
                        let step = args.double(forKey: "growStep") > 0 ? args.double(forKey: "growStep") : 0.9
                        Task { @MainActor in
                            try? await Task.sleep(for: .seconds(delay))
                            for id in order {
                                if id == "cottage" { model.state.built.removeAll { $0 == "tent" } }
                                model.lastBuilt = id
                                model.state.built.append(id)
                                try? await Task.sleep(for: .seconds(step))
                            }
                        }
                    }
                    // Launch video: run the sky clock fast (hours of sky per real second).
                    let lapse = args.double(forKey: "skyTimelapse")
                    if lapse > 0 {
                        Task { @MainActor in
                            try? await Task.sleep(for: .seconds(args.double(forKey: "lapseDelay")))
                            while true {
                                try? await Task.sleep(for: .milliseconds(33))
                                if let t = model.env.timeOverride { model.env.timeOverride = t.addingTimeInterval(lapse * 3600 * 0.033) }
                            }
                        }
                    }
                    #endif
                    model.purchases.configure()
                    model.env.start()
                    model.evaluateMissedDays()
                    model.state.plots = model.autoPlanted(model.state.plots)
                    model.checkAchievements()
                    model.autoAdventureIfNeeded()
                    SoundService.shared.configureForIsland()
                    model.checkInbox()
                    await watchAlarms()
                }
                .onReceive(NotificationCenter.default.publisher(for: MissionInbox.didChange).receive(on: DispatchQueue.main)) { _ in
                    model.checkInbox()
                }
                .onChange(of: scenePhase) { _, phase in
                    switch phase {
                    case .active:
                        model.missionResumed()
                        model.scheduleBedtimeReminder()
                        model.evaluateMissedDays()
                        model.autoAdventureIfNeeded()
                        model.checkInbox()
                        Task {
                            await model.purchases.refresh()
                            model.grantWeeklyFreezeIfNeeded()
                        }
                    case .background:
                        // Leaving mid-mission doesn't get you out of it.
                        model.missionBackgrounded()
                    default: break
                    }
                }
        }
    }

    /// If an alarm starts ringing while the app is open, jump straight into the mission.
    @MainActor
    private func watchAlarms() async {
        #if DEBUG
        if UserDefaults.standard.bool(forKey: "demoQuiet") { return }  // filming: no permission popup
        #endif
        for await alarms in AlarmService.manager.alarmUpdates {
            if let ringing = alarms.first(where: { $0.state == .alerting }), model.activeMission?.isPractice ?? true {
                // Test alarms and re-rings have their own ids: map them back to the alarm they belong to.
                let source = model.state.alarms.first { $0.id == ringing.id }?.id.uuidString
                    ?? MissionInbox.source(for: ringing.id)?.uuidString
                    ?? model.state.alarms.first?.id.uuidString ?? ""
                MissionInbox.post(sourceAlarmID: source)
            }
        }
    }
}

struct RootView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        @Bindable var model = model
        ZStack {
            if !model.state.hasOnboarded {
                OnboardingView()
            } else if model.hasAccess {
                HomeView()
            } else {
                TrialPaywallView()
                    .transition(.opacity)
            }
        }
        .animation(.easeInOut(duration: 0.5), value: model.hasAccess)
        .onChange(of: model.hasAccess) { _, access in
            // Without access the alarm can always be stopped normally.
            if !access && model.state.escapeProof { model.setEscapeProof(false) }
        }
        .fullScreenCover(isPresented: Binding(
            get: { model.activeMission != nil || model.reward != nil },
            set: { if !$0 { model.reward = nil } }
        )) {
            ZStack {
                if let mission = model.activeMission {
                    MissionView(active: mission)
                        .id(mission.id)
                        .transition(.opacity)
                } else if let reward = model.reward {
                    RewardView(reward: reward)
                        .transition(.opacity.combined(with: .scale(scale: 1.04)))
                }
            }
            .animation(.easeInOut(duration: 0.5), value: model.activeMission?.id)
            .environment(model)
        }
        .sheet(isPresented: $model.showPaywall) {
            PaywallView(reason: model.paywallReason)
                .environment(model)
        }
    }
}
