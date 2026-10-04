import SwiftUI

struct HomeView: View {
    #if DEBUG
    /// Filming: hide every on-screen control so only the world shows (launch video b-roll).
    static let cinema = UserDefaults.standard.bool(forKey: "demoCinema")
    #else
    static let cinema = false
    #endif
    @Environment(AppModel.self) private var model
    @State private var sheet: HomeSheet?
    @State private var buildSelection: String?
    @State private var celebrateTick = 0
    @State private var greeting: String?
    @State private var clockY: CGFloat?
    @State private var postcard: AdventureTrip?
    @State private var viewingFarm = false
    @State private var commuting = false
    @State private var skipTick = 0
    @State private var fedEmoji = "🍎"
    @State private var insideView = false
    @State private var viewingTrip = false
    @State private var tripArrivalTick = 0
    @State private var arrivalShown: Date?
    /// Choosing a spot for something (new or moved), and which expansion isle the camera is on.
    @State private var draft: PlacementDraft?
    @State private var viewingIsle: Int?

    enum HomeSheet: String, Identifiable {
        case alarms, build, journal, settings, letters, travel, streak
        var id: String { rawValue }
    }

    var body: some View {
        let sky = model.env.sky
        ZStack {
            WorldView(
                sky: sky,
                built: model.state.built,
                stage: model.state.sproutStage,
                lastBuilt: model.lastBuilt,
                petTick: model.petTick,
                celebrateTick: celebrateTick,
                buildMarkers: [],
                highlightedSlot: sheet == .build ? buildSelection : nil,
                // Menus other than Build cover the island: stop rendering it entirely so they scroll smoothly.
                paused: model.activeMission != nil || model.reward != nil || model.showPaywall
                    || (sheet != nil && sheet != .build),
                throttled: sheet != nil && sheet != .build,
                clockY: commuting || Self.cinema ? nil : clockY,
                hat: model.state.equippedHat,
                sproutAway: model.state.trip != nil && !model.tripReturned,
                plots: model.state.plots,
                atWork: model.isAtWork,
                focusFarm: viewingFarm,
                mood: model.state.moodTier,
                hungry: model.state.isHungry,
                feedTick: model.feedTick,
                feedEmoji: fedEmoji,
                gloom: model.state.gloom,
                dusty: model.inDebt,
                sick: model.state.sick,
                home: model.state.built.contains("cottage") ? "cottage" : "tent",
                viewInside: insideView || model.state.ranAway,
                occupant: occupant,
                decor: model.state.currentDecor,
                tripDestination: onVacation ? model.state.trip?.destination : nil,
                tripVisible: viewingTrip && onVacation,
                tripActivity: tripActivity,
                tripArrivalTick: tripArrivalTick,
                commuteTick: model.commuteTick,
                skipTick: skipTick,
                commuteHarvest: model.commuteHarvest,
                placements: model.resolvedPlacements,
                isles: model.state.isles,
                newIsle: model.lastIsle,
                focusIsle: draft?.placement.island ?? viewingIsle,
                ghostID: draft?.id,
                ghostPlacement: draft?.placement,
                canPlace: { [id = draft?.id] p in id.map { model.canPlace($0, at: p) } ?? true },
                onGhostMoved: { p in draft?.placement = p },
                onCommuteFinished: { endCommuteNow() },
                onPetSprout: pet,
                onPokeBusySprout: pokeBusy,
                onTapMarker: { id in
                    buildSelection = id
                    Haptics.select()
                },
                onTapItem: { id in
                    // Tap something you built to see it (and move it) in the build menu.
                    guard sheet == nil, draft == nil, !commuting, BuildCatalog.isMovable(id) else { return }
                    Haptics.select()
                    buildSelection = id
                    sheet = .build
                }
            )
            .ignoresSafeArea()
            .accessibilityLabel("Your island. \(model.state.companionName) is here.")

            if commuting && !Self.cinema {
                CommuteOverlay(name: model.state.companionName) {
                    skipTick += 1
                    // Skip always works, even if the flight never got going.
                    endCommuteNow()
                }
                    .transition(.opacity)
            }

            VStack(spacing: 0) {
                topBar
                ClockHeader(sky: sky, placeName: model.env.placeName, cloudClockY: $clockY,
                            liveWeather: model.env.weather.fetchedAt != nil || model.env.weatherOverride != nil)
                    .padding(.top, 8)
                Group {
                    if model.state.ranAway {
                        StatusPill(symbol: "bed.double.fill", tint: .green,
                                   text: "\(model.state.companionName) is sick in bed · wake up together to help") {
                            sheet = .letters
                        }
                    } else if model.state.sick {
                        StatusPill(symbol: "thermometer.medium", tint: .orange,
                                   text: "\(model.state.companionName) has a cold · wake up together to help") { sheet = .letters }
                    } else if model.inDebt {
                        StatusPill(symbol: "exclamationmark.triangle.fill", tint: .orange,
                                   text: "In debt: \(model.state.debt) coins · shops closed") { sheet = .letters }
                    } else if occupant == .sleeping {
                        StatusPill(symbol: "moon.zzz.fill", tint: .indigo,
                                   text: "\(model.state.companionName) is asleep. You should be too 😴") {
                            withAnimation { insideView = true }
                        }
                    } else if let m = model.minutesToBedtime, model.state.trip == nil {
                        StatusPill(symbol: "bed.double.fill", tint: .indigo,
                                   text: "\(model.state.companionName) is getting sleepy · bedtime in \(m) min") {}
                    } else if model.isAtWork && model.state.trip == nil {
                        WorkPill(name: model.state.companionName, until: model.state.workUntil) {
                            withAnimation { viewingFarm = true }
                        }
                    } else if onVacation, let trip = model.state.trip, let dest = AdventureCatalog.destination(trip.destination) {
                        StatusPill(symbol: "balloon.fill", tint: Theme.leaf,
                                   text: viewingTrip
                                       ? "\(VacationCatalog.info(for: dest.id)?.activities[tripActivity] ?? "Exploring") · \(dest.name)"
                                       : "On vacation at \(dest.name) · home \(trip.returns.formatted(date: .omitted, time: .shortened))") {
                            withAnimation(.snappy) { viewingTrip = true; insideView = false; viewingFarm = false }
                        }
                    } else if let booked = model.state.bookedTrip, let dest = AdventureCatalog.destination(booked.destination) {
                        StatusPill(symbol: "calendar.badge.checkmark", tint: Theme.sun,
                                   text: "Vacation booked: \(dest.name) · \(Calendar.current.isDateInToday(booked.day) ? "today" : booked.day.formatted(.dateTime.weekday(.wide)))") {
                            sheet = .travel
                        }
                    } else if model.state.trip == nil && model.canBookVacation && model.isDayOff(model.env.now)
                                && Calendar.current.component(.hour, from: model.env.now) < 15 && !model.isSleepTime {
                        StatusPill(symbol: "suitcase.rolling.fill", tint: Theme.leaf,
                                   text: "Day off! Plan a vacation for \(model.state.companionName)") { sheet = .travel }
                    } else if model.state.trip != nil {
                        AdventurePill { postcard = model.state.trip }
                    } else if let letter = model.state.unreadLetters.first {
                        StatusPill(symbol: "envelope.badge.fill", tint: Theme.berry,
                                   text: "New letter: \(letter.title)") { sheet = .letters }
                    }
                }
                .padding(.top, 10)
                .transition(.scale.combined(with: .opacity))
                if let greeting {
                    SpeechBubble(text: greeting)
                        .padding(.top, 14)
                        .transition(.scale(scale: 0.6, anchor: .top).combined(with: .opacity))
                }
                Spacer()
                if draft != nil {
                    PlacementBar(draft: $draft) { island in
                        // Stay looking at the isle you just built on.
                        withAnimation { viewingIsle = island == 0 ? nil : island }
                        celebrateTick += 1
                    }
                    .transition(.move(edge: .bottom).combined(with: .opacity))
                } else if sheet == nil && !commuting {
                    bottomPanel
                        .transition(.move(edge: .bottom).combined(with: .opacity))
                }
            }
            .padding(.horizontal, 16)
            .opacity(commuting || Self.cinema ? 0 : 1)
        }
        .animation(.spring(response: 0.45, dampingFraction: 0.85), value: sheet)
        .animation(.easeInOut(duration: 0.4), value: commuting)
        .onChange(of: model.commuteTick) { _, tick in
            sheet = nil
            commuting = true
            // Safety net: the longest flight and harvest takes about 12 s, so never keep the bars up past 16 s.
            Task {
                try? await Task.sleep(for: .seconds(16))
                if commuting && model.commuteTick == tick {
                    skipTick += 1
                    endCommuteNow()
                }
            }
            // Reduce Motion: skip the flying cutscene and go straight to the shift report.
            if UIAccessibility.isReduceMotionEnabled {
                Task { try? await Task.sleep(for: .milliseconds(300)); skipTick += 1 }
            }
        }
        .animation(.spring(response: 0.4, dampingFraction: 0.7), value: greeting)
        .sheet(item: $sheet) { which in
            switch which {
            case .alarms:
                AlarmListView().environment(model)
            case .build:
                BuildSheet(selection: $buildSelection, insideView: $insideView,
                           onPlace: { startPlacing($0, isMove: false) },
                           onMove: { startPlacing($0, isMove: true) },
                           onVisitIsle: { id in
                               viewingFarm = false
                               viewingTrip = false
                               insideView = false
                               withAnimation { viewingIsle = id }
                           })
                    .environment(model)
            case .journal:
                JournalView().environment(model).environment(\.flatCards, true)
            case .settings:
                SettingsView().environment(model).environment(\.flatCards, true)
            case .letters:
                LettersView().environment(model).environment(\.flatCards, true)
            case .travel:
                TravelView().environment(model).environment(\.flatCards, true)
            case .streak:
                StreakSheet().environment(model).environment(\.flatCards, true)
            }
        }
        .sheet(item: $postcard) { trip in
            PostcardView(trip: trip).environment(model)
        }
        .onChange(of: model.reward) { old, new in
            if old != nil && new == nil {
                celebrateTick += 1
                // After the shift report, linger on the farm a moment, then fly home.
                Task {
                    try? await Task.sleep(for: .seconds(2.5))
                    withAnimation { viewingFarm = false }
                }
            }
        }
        .onChange(of: model.state.built) { _, _ in celebrateTick += 1 }
        .onAppear {
            updateAudio(sky)
            SoundService.shared.startMusic()
            #if DEBUG
            switch UserDefaults.standard.string(forKey: "demoScreen") {
            case "build": sheet = .build; buildSelection = "pond"
            case "isles": sheet = .build
            case "place": startPlacing(UserDefaults.standard.string(forKey: "placeItem") ?? "fountain", isMove: false)
            case "isle": viewingIsle = UserDefaults.standard.integer(forKey: "isleID") == 0 ? 1 : UserDefaults.standard.integer(forKey: "isleID")
            case "alarms": sheet = .alarms
            case "journal": sheet = .journal
            case "paywall": model.showPaywall = true
            case "mission": model.activeMission = ActiveMission(mission: .pushups, target: 10, sound: .sunrise, isPractice: false)
            case "math": model.activeMission = ActiveMission(mission: .math, target: 3, sound: .sunrise, isPractice: false)
            case "hunt": model.activeMission = ActiveMission(mission: .hunt, target: 3, sound: .sunrise, isPractice: true)
            case "reward":
                model.reward = WakeReward(mission: .pushups, amount: 10, seconds: 74, baseXP: 40, effortXP: 40, speedXP: 20,
                                          streakXP: 15, coins: 204, bonusCoins: 0, newStreak: 3, previousLevel: 2,
                                          newLevel: 3, previousProgress: 0.7, newProgress: 0.2, isPractice: false,
                                          shift: ShiftReport(harvest: [HarvestLine(crop: "carrot", count: 3, coins: 72),
                                                                       HarvestLine(crop: "strawberry", count: 2, coins: 76)],
                                                             wage: 22, moodMultiplier: 1.2, total: 204, watered: 2))
            case "adventure":
                model.state.trip = nil
                model.state.lastAdventureDay = nil
                model.state.canAdventureDay = .now
                model.reward = WakeReward(mission: .squats, amount: 15, seconds: 95, baseXP: 40, effortXP: 40, speedXP: 10,
                                          streakXP: 20, coins: 23, bonusCoins: 0, newStreak: 4, previousLevel: 5,
                                          newLevel: 5, previousProgress: 0.3, newProgress: 0.6, isPractice: false,
                                          festivalChest: 3, festivalReward: .hat("pumpkin"), canAdventure: true)
            case "postcard":
                model.state.trip = AdventureTrip(destination: "woods", discovery: "woods3", souvenir: "pinecone", hatFound: "explorer",
                                                 coins: 27, departed: .now.addingTimeInterval(-4 * 3600), returns: .now.addingTimeInterval(-60))
                postcard = model.state.trip
            case "exploring":
                model.state.trip = AdventureTrip(destination: "beach", discovery: "beach1", souvenir: "shell", hatFound: nil,
                                                 coins: 27, departed: .now, returns: .now.addingTimeInterval(3 * 3600))
            case "depart":
                model.state.trip = nil
                model.state.lastAdventureDay = nil
                model.state.canAdventureDay = .now
                Task {
                    try? await Task.sleep(for: .seconds(4))
                    model.startAdventure(to: AdventureCatalog.destinations[0], morningXP: 120)
                }
            case "return":
                model.state.trip = AdventureTrip(destination: "meadow", discovery: "meadow2", souvenir: "clover", hatFound: nil,
                                                 coins: 20, departed: .now.addingTimeInterval(-3600), returns: .now.addingTimeInterval(5))
            case "market", "wardrobe", "home":
                sheet = .build
            case "letters":
                sheet = .letters
            case "inside":
                insideView = true
            case "travel":
                sheet = .travel
            case "vacation":
                model.state.trip = nil
                model.state.bookedTrip = nil
                model.state.coins += 300
                if let d = AdventureCatalog.destination(UserDefaults.standard.string(forKey: "demoTrip") ?? "beach") {
                    model.startAdventure(to: d, morningXP: 100, force: true)
                }
                viewingTrip = true
            case "settings":
                sheet = .settings
            case "streak":
                // A realistic run-up for the calendar (on top of -demoBuilt's 12 won days): an earlier
                // 14-day run, a freeze covering the first sleep-in, then missed mornings before today's streak.
                // (After the app-level demo setup, which replaces the history.)
                Task {
                    try? await Task.sleep(for: .milliseconds(300))
                    let cal = Calendar.current
                    let today = cal.startOfDay(for: .now)
                    let day = { (d: Int) in cal.date(byAdding: .day, value: -d, to: today)! }
                    let won = model.state.wonDays
                    for d in 20...33 where !won.contains(day(d)) {
                        model.state.history.append(WakeRecord(date: day(d).addingTimeInterval(7 * 3600), mission: .pushups, amount: 10,
                                                              secondsToComplete: 80, xp: 110, coins: 35))
                    }
                    model.state.history.sort { $0.date < $1.date }
                    model.state.frozenDays = [day(19)]
                    model.state.bestStreak = max(model.state.bestStreak, 14)
                    if !model.state.alarms.isEmpty { model.state.alarms[0].createdAt = day(40) }
                    sheet = .streak
                }
            case "farmview":
                viewingFarm = true
            case "shift":
                model.state.plots = [PlotState(crop: "carrot", growth: 1), PlotState(crop: "turnip"), PlotState(crop: "corn", growth: 1),
                                     PlotState(crop: "strawberry", growth: 1)]
                model.state.lastWakeDay = nil
                Task {
                    try? await Task.sleep(for: .seconds(2.5))
                    model.completeMission(ActiveMission(mission: .pushups, target: 10, sound: .sunrise, isPractice: false), amount: 10)
                }
            case "pet":
                Task { try? await Task.sleep(for: .seconds(3)); pet() }
            default: break
            }
            #endif
        }
        .onChange(of: Calendar.current.component(.minute, from: model.env.now)) { _, _ in
            model.startBookedTripIfDue()
        }
        .onChange(of: onVacation) { _, on in if !on { viewingTrip = false } }
        .onChange(of: viewingTrip) { _, on in
            // First look just after they set off: watch the balloon land.
            guard on, let trip = model.state.trip, arrivalShown != trip.departed,
                  Date.now.timeIntervalSince(trip.departed) < 15 * 60 else { return }
            arrivalShown = trip.departed
            tripArrivalTick += 1
        }
        .onChange(of: sky.isDay) { _, _ in updateAudio(sky) }
        .onChange(of: sky.weather.kind) { _, _ in updateAudio(sky) }
    }

    private var onVacation: Bool { model.state.trip != nil && !model.tripReturned }

    /// Which activity he's doing right now: 0 at his stay, then A/B/C, cycling every minute while you watch.
    private var tripActivity: Int {
        Int(model.env.now.timeIntervalSince1970 / 60) % 4
    }

    /// Opens the see-through preview for a new item (on the isle you're looking at) or a built one.
    private func startPlacing(_ id: String, isMove: Bool) {
        let island = isMove ? model.placement(of: id).island : (viewingIsle ?? 0)
        // New things go on the isle you're looking at, or the first island that still has room.
        let order = [island] + ([0] + model.state.isles).filter { $0 != island }
        let start = isMove ? model.placement(of: id)
            : (order.lazy.compactMap { model.freeSpot(for: id, on: $0) }.first
               ?? ItemPlacement(island: island, x: 0, z: 2.4, rotation: 0))
        insideView = false
        viewingFarm = false
        viewingTrip = false
        withAnimation(.spring(response: 0.45, dampingFraction: 0.85)) {
            draft = PlacementDraft(id: id, placement: start, isMove: isMove)
        }
    }

    private var occupant: WorldScene.Occupant {
        if model.state.ranAway { return .sick }
        if model.isSleepTime && !model.isAtWork && model.state.trip == nil { return .sleeping }
        return .none
    }

    private func updateAudio(_ sky: SkyState) {
        let name: String
        switch sky.weather.kind {
        case .rain, .drizzle, .thunder: name = "amb_rain"
        default: name = sky.isDay ? "amb_day" : "amb_night"
        }
        SoundService.shared.setAmbience(name)
    }

    /// Tapping the sprout mid-shift or mid-vacation: a little busy, a little annoyed, still cute.
    private func pokeBusy(_ atWork: Bool) {
        SoundService.shared.play(.pet, rate: Float.random(in: 1.05...1.25))
        Haptics.soft()
        let work = ["Shh, I'm on the clock! ⏰", "Can't talk, carrots won't pull themselves 🥕", "Boss is watching… act natural 👀",
                    "Five more rows, then snacks!", "Hi! Bye! Busy! 🌱", "You woke up, so I'm working. Deal's a deal!",
                    "Do NOT tell the scarecrow I stopped", "Watering… watering… still watering 💧",
                    "Is it 5 o'clock yet?", "I'm basically a farming legend now"]
        let trip = ["Excuse me, I'm on VACATION 🏝️", "Out of office! Leave a message 📮", "Wish you were here! (Not really, it's quiet) 😌",
                    "Do not disturb, I'm relaxing", "Sending you a postcard, hold on!", "Five more minutes of sunshine… ☀️",
                    "I earned this. You earned this. We earned this!", "No work talk, please 🙅"]
        greeting = (atWork ? work : trip).randomElement()
        let current = greeting
        Task {
            try? await Task.sleep(for: .seconds(3))
            if greeting == current { greeting = nil }
        }
    }

    private func pet() {
        model.petTick += 1
        model.petted()
        SoundService.shared.play(.pet, rate: Float.random(in: 0.92...1.12))
        Haptics.soft()
        var lines = Self.petLines(name: model.state.companionName, sky: model.env.sky, woke: model.state.woke)
        if occupant == .sleeping { lines = ["Zzz…", "Five more minutes…", "Mmm… carrots… zzz", "Shh, it's bedtime 🌙"] }
        else if model.state.moodTier == .sad { lines = ["I missed you this morning…", "Will we wake up together tomorrow?", "The crops are thirsty…"] }
        greeting = lines.randomElement()
        let current = greeting
        Task {
            try? await Task.sleep(for: .seconds(3))
            if greeting == current { greeting = nil }
        }
    }

    static func petLines(name: String, sky: SkyState, woke: Bool) -> [String] {
        var lines = ["Hehe, that tickles!", "Hi hi hi!", "☀️ ✨ 🌱"]
        if sky.isDay {
            lines += woke ? ["We did it today!", "Look how bright it is!"] : ["Is it morning yet?", "Let's rise and shine together!"]
        } else {
            lines += ["So sleepy…", "The stars are out ✨", "Wake me at sunrise?"]
        }
        switch sky.weather.kind {
        case .rain, .drizzle: lines.append("Pitter patter…")
        case .snow: lines.append("Snow!! ❄️")
        case .thunder: lines.append("Eep! Thunder!")
        default: break
        }
        return lines
    }

    // MARK: Top bar

    /// Closes the commute cutscene and shows the shift report (safe to call more than once).
    private func endCommuteNow() {
        guard commuting else { return }
        withAnimation(.easeInOut(duration: 0.4)) { commuting = false }
        model.finishCommute()
    }

    private var topBar: some View {
        HStack {
            // Settings, mirroring the streak pill (same height and glass).
            Button {
                SoundService.shared.play(.tap, volume: 0.5)
                Haptics.tap()
                sheet = .settings
            } label: {
                Image(systemName: "gearshape.fill")
                    .font(.system(size: 17, weight: .semibold))
                    .foregroundStyle(.white)
                    .frame(width: 38, height: 38)
                    .contentShape(.circle)
            }
            .buttonStyle(.plain)
            .glassEffect(.regular.interactive(), in: .circle)
            .accessibilityLabel("Settings")
            Spacer()
            Button {
                SoundService.shared.play(.tap, volume: 0.5)
                Haptics.tap()
                sheet = .streak
            } label: {
                StreakWeek()
            }
            .buttonStyle(.plain)
            .glassEffect(.regular.interactive(), in: .capsule)
            .accessibilityLabel("\(model.state.streak) day streak")
            .accessibilityHint("Opens your streak calendar")
        }
        .padding(.top, 2)
    }

    // MARK: Bottom

    private var bottomPanel: some View {
        VStack(spacing: 10) {
            if !model.state.ranAway {
                PlaceSwitcher(place: Binding(
                    get: {
                        insideView ? .inside : viewingFarm ? .farm : (viewingTrip && onVacation) ? .trip
                            : viewingIsle.map { .isle($0) } ?? .island
                    },
                    set: { p in
                        insideView = p == .inside
                        viewingFarm = p == .farm
                        viewingTrip = p == .trip
                        if case .isle(let n) = p { viewingIsle = n } else { viewingIsle = nil }
                    }
                ), tent: !model.state.built.contains("cottage"), showTrip: onVacation, isles: model.state.isles)
            }
            GlassEffectContainer(spacing: 8) {
                HStack(spacing: 8) {
                    Button {
                        SoundService.shared.play(.tap, volume: 0.5)
                        Haptics.tap()
                        sheet = .alarms
                    } label: { AlarmChip() }
                        .buttonStyle(.plain)
                        .glassEffect(.regular.interactive(), in: .capsule)
                    barButton("Build", symbol: "hammer.fill", prominent: true) {
                        buildSelection = nil
                        viewingFarm = false
                        sheet = .build
                    }
                    barButton("Journal", symbol: "book.closed.fill") { sheet = .journal }
                }
            }
        }
        .padding(.bottom, 6)
    }

    private func barButton(_ title: String, symbol: String, prominent: Bool = false, action: @escaping () -> Void) -> some View {
        Button {
            SoundService.shared.play(.tap, volume: 0.5)
            Haptics.tap()
            action()
        } label: {
            Image(systemName: symbol)
                .font(.system(size: 20, weight: .semibold))
                .foregroundStyle(prominent ? Theme.ink : .white)
                .frame(width: 58, height: 58)
                .contentShape(.circle)
        }
        .buttonStyle(.plain)
        .glassEffect(prominent ? .regular.tint(Theme.sunLight).interactive() : .regular.interactive(), in: .circle)
        .accessibilityLabel(title)
    }

}

/// Date, time and weather over the sky. With `cloudClockY` the time itself is drawn in 3D by the world
/// (puffy cloud numerals), and this view just reserves the space and reports where it is.
struct ClockHeader: View {
    var sky: SkyState
    var placeName: String?
    var cloudClockY: Binding<CGFloat?>? = nil
    /// Only show a temperature once real weather has arrived.
    var liveWeather: Bool = true

    var body: some View {
        VStack(spacing: 6) {
            if let cloudClockY {
                Color.clear
                    .frame(height: 62)
                    .onGeometryChange(for: CGFloat.self) { $0.frame(in: .global).midY } action: { cloudClockY.wrappedValue = $0 }
                    .accessibilityElement()
                    .accessibilityLabel(sky.date.formatted(date: .omitted, time: .shortened))
            } else {
                Text(sky.date.formatted(date: .omitted, time: .shortened))
                    .font(.system(size: 58, weight: .semibold, design: .rounded))
                    .monospacedDigit()
                    .contentTransition(.numericText())
                    .minimumScaleFactor(0.6)
                    .lineLimit(1)
            }
            HStack(spacing: 6) {
                Text(sky.date.formatted(.dateTime.weekday(.wide).month(.abbreviated).day()))
                if liveWeather {
                    Text("·").opacity(0.6)
                    Image(systemName: sky.weather.kind.symbol(isDay: sky.isDay))
                        .symbolRenderingMode(.multicolor)
                    Text(sky.weather.temperatureText)
                }
            }
            .font(.rounded(15, .semibold))
            .opacity(0.9)
            .accessibilityLabel("\(sky.date.formatted(date: .complete, time: .omitted)), \(sky.weather.temperatureText), \(sky.weather.kind.title)")
        }
        .worldText()
        .accessibilityElement(children: .combine)
    }
}

struct SpeechBubble: View {
    var text: String

    var body: some View {
        Text(text)
            .font(.rounded(16, .semibold))
            .foregroundStyle(Theme.ink)
            .padding(.horizontal, 18)
            .padding(.vertical, 10)
            .background(Theme.cream, in: .capsule)
            .shadow(color: .black.opacity(0.15), radius: 10, y: 4)
    }
}


struct WorkPill: View {
    var name: String
    var until: Date?
    var onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            HStack(spacing: 8) {
                Image(systemName: "leaf.fill").foregroundStyle(Theme.leafGradient)
                Text("\(name) is at work on the farm · home \(until?.formatted(date: .omitted, time: .shortened) ?? "tonight")")
            }
            .font(.rounded(14, .semibold))
            .foregroundStyle(.white)
            .padding(.horizontal, 14)
            .padding(.vertical, 9)
            .contentShape(.capsule)
        }
        .buttonStyle(.plain)
        .glassEffect(.regular.interactive(), in: .capsule)
    }
}

/// Letterbox bars + caption while the morning commute plays.
struct CommuteOverlay: View {
    var name: String
    var onSkip: () -> Void
    @State private var caption = 0

    private var captions: [String] {
        ["\(name) is off to work!", "Flying to the Farm Island…", "Harvest time!"]
    }

    var body: some View {
        VStack(spacing: 0) {
            Rectangle().fill(.black).frame(height: 110)
            Spacer()
            ZStack {
                Rectangle().fill(.black).frame(height: 150)
                HStack {
                    Text(captions[min(caption, captions.count - 1)])
                        .font(.rounded(20, .bold))
                        .foregroundStyle(.white)
                        .contentTransition(.opacity)
                    Spacer()
                    Button("Skip", action: onSkip)
                        .font(.rounded(15, .semibold))
                        .buttonStyle(.glass)
                }
                .padding(.horizontal, 22)
                .padding(.bottom, 30)
            }
        }
        .ignoresSafeArea()
        .task {
            for i in 1..<3 {
                try? await Task.sleep(for: .seconds(i == 1 ? 1.8 : 4.2))
                withAnimation { caption = i }
            }
        }
    }
}


struct StatusPill: View {
    var symbol: String
    var tint: Color
    var text: String
    var onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            HStack(spacing: 8) {
                Image(systemName: symbol).foregroundStyle(tint)
                Text(text).multilineTextAlignment(.leading)
            }
            .font(.rounded(13, .semibold))
            .foregroundStyle(.white)
            .lineLimit(1)
            .minimumScaleFactor(0.85)
            .padding(.horizontal, 14)
            .padding(.vertical, 8)
            .contentShape(.capsule)
        }
        .buttonStyle(.plain)
        .glassEffect(.regular.interactive(), in: .capsule)
    }
}


/// Island · House · Farm (· Trip): icons, with the selected place's name. Every segment has a full
/// 44 pt tap target so it's easy to hit even while the selection animates.
struct PlaceSwitcher: View {
    enum Place: Hashable { case island, inside, farm, trip, isle(Int) }
    @Binding var place: Place
    var tent: Bool
    var showTrip: Bool = false
    var isles: [Int] = []

    var body: some View {
        HStack(spacing: 0) {
            item(.island, "Island", "tree.fill")
            item(.inside, tent ? "Tent" : "House", tent ? "tent.fill" : "house.fill")
            ForEach(isles, id: \.self) { n in
                item(.isle(n), IsleCatalog.isle(n)?.name.replacingOccurrences(of: " Isle", with: "") ?? "Isle", IsleCatalog.symbol(n))
            }
            item(.farm, "Farm", "leaf.fill")
            if showTrip { item(.trip, "Trip", "airplane") }
        }
        .padding(3)
        .glassEffect(.regular, in: .capsule)
    }

    private func item(_ p: Place, _ title: String, _ symbol: String) -> some View {
        Button {
            Haptics.select()
            SoundService.shared.play(.tap, volume: 0.4)
            withAnimation(.snappy(duration: 0.25)) { place = p }
        } label: {
            Label(title, systemImage: symbol)
                .font(.rounded(14, .semibold))
                .labelStyle(PlaceLabelStyle(showTitle: place == p))
                .padding(.horizontal, 14)
                .frame(minWidth: 48, minHeight: 44)
                .foregroundStyle(place == p ? Theme.ink : .white)
                .background(place == p ? AnyShapeStyle(Theme.sunLight) : AnyShapeStyle(.clear), in: .capsule)
                .contentShape(.rect)
        }
        .buttonStyle(.plain)
        .accessibilityLabel(title)
        .accessibilityAddTraits(place == p ? .isSelected : [])
    }
}

/// Icon only, plus the title for the selected place.
struct PlaceLabelStyle: LabelStyle {
    var showTitle: Bool
    func makeBody(configuration: Configuration) -> some View {
        HStack(spacing: 5) {
            configuration.icon
            if showTitle { configuration.title }
        }
    }
}



/// Top-right: the streak flame plus this week as seven tiny dots (sun = won, faint = missed/upcoming).
struct StreakWeek: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        let cal = Calendar.current
        let now = model.env.effectiveDate
        let start = cal.dateInterval(of: .weekOfYear, for: now)?.start ?? cal.startOfDay(for: now)
        let days = (0..<7).compactMap { cal.date(byAdding: .day, value: $0, to: start) }
        let won = Set(model.state.history.filter(\.isWin).map { cal.startOfDay(for: $0.date) })
        let today = cal.startOfDay(for: now)
        HStack(spacing: 8) {
            StreakLabel(streak: model.state.streak, size: 15)
            HStack(spacing: 4) {
                ForEach(days, id: \.self) { day in
                    let isWon = won.contains(day)
                    let missed = day < today && model.isAlarmDay(day) && !isWon
                    Circle()
                        .fill(isWon ? AnyShapeStyle(Theme.sunGradient)
                              : missed ? AnyShapeStyle(Color.white.opacity(0.18)) : AnyShapeStyle(Color.white.opacity(0.35)))
                        .frame(width: 7, height: 7)
                        .overlay(Circle().strokeBorder(day == today ? Color.white : .clear, lineWidth: 1.2).padding(-2.5))
                }
            }
        }
        .padding(.horizontal, 12)
        .frame(height: 38)
        .contentShape(.capsule)
    }
}

/// The next alarm, compact: bell + time + mission, bedtime underneath.
struct AlarmChip: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: model.state.woke ? "checkmark.circle.fill" : "alarm.fill")
                .font(.system(size: 20, weight: .semibold))
                .foregroundStyle(Theme.sunGradient)
            if let (alarm, _) = model.nextAlarm {
                VStack(alignment: .leading, spacing: 0) {
                    Text(alarm.timeText)
                        .font(.rounded(17, .bold))
                        .monospacedDigit()
                    Text("\(alarm.mission.goalText(alarm.target)) · bed \(model.sleepPlan(at: model.env.now).bedtime.formatted(date: .omitted, time: .shortened))")
                        .font(.rounded(11, .medium))
                        .foregroundStyle(.secondary)
                }
                .lineLimit(1)
                .minimumScaleFactor(0.75)
            } else {
                Text("Set an alarm").font(.rounded(16, .bold))
            }
            Spacer(minLength: 0)
        }
        .foregroundStyle(.white)
        .padding(.horizontal, 16)
        .frame(maxWidth: .infinity, minHeight: 58)
        .contentShape(.capsule)
        .accessibilityElement(children: .combine)
        .accessibilityHint("Opens alarms")
    }
}


/// A thing being placed: which item, where, and whether it's already built (a move).
struct PlacementDraft: Equatable {
    var id: String
    var placement: ItemPlacement
    var isMove: Bool
}

/// Shown while placing: what it is, whether it fits, island choice, rotate, cancel and confirm.
struct PlacementBar: View {
    @Environment(AppModel.self) private var model
    @Binding var draft: PlacementDraft?
    var onPlaced: (Int) -> Void

    var body: some View {
        if let d = draft, let item = BuildCatalog.item(d.id) {
            let problem = model.placementProblem(d.id, at: d.placement) ?? (d.isMove ? nil : buyProblem(item))
            let ok = problem == nil
            VStack(spacing: 12) {
                HStack(spacing: 12) {
                    Image(systemName: item.symbol)
                        .font(.system(size: 18, weight: .bold))
                        .foregroundStyle(Theme.sun)
                        .frame(width: 40, height: 40)
                        .background(.white.opacity(0.1), in: .circle)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(d.isMove ? "Move \(item.name)" : item.name)
                            .font(.rounded(17, .bold))
                        Text(ok ? "Drag it around, or tap a spot"
                             : model.freeSpot(for: d.id, on: d.placement.island) == nil
                                ? (model.state.isles.count < IsleCatalog.all.count ? "This island is full. Buy a new isle in Build" : "This island is full. Try another isle")
                                : problem ?? "")
                            .font(.rounded(13, .semibold))
                            .foregroundStyle(ok ? AnyShapeStyle(.secondary) : AnyShapeStyle(Color.orange))
                            .contentTransition(.opacity)
                    }
                    Spacer()
                    if !d.isMove { CoinLabel(amount: item.cost, size: 16) }
                }
                if !model.state.isles.isEmpty {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 8) {
                            ForEach([0] + model.state.isles, id: \.self) { i in
                                let on = d.placement.island == i
                                Button {
                                    Haptics.select()
                                    moveTo(island: i)
                                } label: {
                                    Label(IsleCatalog.name(i), systemImage: IsleCatalog.symbol(i))
                                        .font(.rounded(13, .bold))
                                        .padding(.horizontal, 12)
                                        .frame(height: 34)
                                        .background(on ? AnyShapeStyle(Theme.sunLight) : AnyShapeStyle(.white.opacity(0.08)), in: .capsule)
                                        .foregroundStyle(on ? Theme.ink : .primary)
                                }
                                .buttonStyle(.plain)
                                .accessibilityAddTraits(on ? .isSelected : [])
                            }
                        }
                    }
                }
                HStack(spacing: 10) {
                    round("xmark", "Cancel") {
                        withAnimation { draft = nil }
                    }
                    round("arrow.clockwise", "Rotate") {
                        withAnimation(.snappy) { draft?.placement.rotation -= .pi / 4 }
                    }
                    Button(action: confirm) {
                        Label(d.isMove ? "Move here" : "Build here", systemImage: "checkmark")
                            .font(.rounded(17, .bold))
                            .frame(maxWidth: .infinity)
                            .frame(height: 50)
                    }
                    .buttonStyle(.glassProminent)
                    .tint(Theme.sun)
                    .disabled(!ok)
                }
            }
            .padding(16)
            .glassCard(cornerRadius: 30)
            .padding(.bottom, 6)
        }
    }

    private func round(_ symbol: String, _ label: String, action: @escaping () -> Void) -> some View {
        Button {
            Haptics.tap()
            action()
        } label: {
            Image(systemName: symbol)
                .font(.system(size: 18, weight: .bold))
                .frame(width: 50, height: 50)
                .contentShape(.circle)
        }
        .buttonStyle(.plain)
        .glassEffect(.regular.interactive(), in: .circle)
        .accessibilityLabel(label)
    }

    /// Can't afford it (any more) or not unlocked yet.
    private func buyProblem(_ item: Buildable) -> String? {
        switch model.status(of: item) {
        case .needsCoins(let n): "You need \(n) more coins"
        case .needsLevel(let l): "Unlocks at level \(l)"
        case .needsPlus: "Part of Riser+"
        default: model.inDebt ? "Pay off your debt first" : nil
        }
    }

    private func moveTo(island: Int) {
        guard let d = draft, d.placement.island != island else { return }
        var spot = model.freeSpot(for: d.id, on: island) ?? ItemPlacement(island: island, x: 0, z: 0)
        spot.rotation = d.placement.rotation
        withAnimation(.snappy) { draft?.placement = spot }
    }

    private func confirm() {
        guard let d = draft, let item = BuildCatalog.item(d.id) else { return }
        let done = d.isMove ? model.move(d.id, to: d.placement) : model.build(item, at: d.placement)
        if done {
            withAnimation(.spring(response: 0.45, dampingFraction: 0.85)) { draft = nil }
            onPlaced(d.placement.island)
        }
    }
}
