import SwiftUI

struct JournalView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss
    @State private var editingName = false
    @State private var nameDraft = ""
    @State private var labHours: Double = 0
    @State private var labOpen = false
    @State private var showLetters = false
    @State private var showTravel = false
    @State private var showSettings = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    companionCard
                    HStack(spacing: 12) {
                        HStack(spacing: 14) {
                            StreakLabel(streak: model.state.streak, size: 18)
                            CoinLabel(amount: model.state.coins, size: 18)
                        }
                        .padding(.horizontal, 16)
                        .frame(height: 52)
                        .glassCard(cornerRadius: 22)
                        Button { showLetters = true } label: {
                            Label(model.state.unreadLetters.isEmpty ? "Mailbox" : "Mailbox (\(model.state.unreadLetters.count))",
                                  systemImage: model.state.unreadLetters.isEmpty ? "envelope.fill" : "envelope.badge.fill")
                                .font(.rounded(15, .semibold))
                                .frame(maxWidth: .infinity)
                                .frame(height: 52)
                                .contentShape(.rect(cornerRadius: 22))
                        }
                        .buttonStyle(.plain)
                        .glassCard(cornerRadius: 22, interactive: true)
                    }
                    statsGrid
                    MorningCalendar(history: model.state.history)
                    if HarvestFestival.isActive() || model.state.festivalChests > 0 {
                        FestivalCard()
                    }
                    Button { showTravel = true } label: {
                        Label("Plan a vacation", systemImage: "suitcase.rolling.fill")
                            .font(.rounded(17, .bold))
                            .frame(maxWidth: .infinity)
                            .frame(height: 54)
                    }
                    .buttonStyle(.glassProminent)
                    .tint(Theme.leaf)
                    LogbookSection()
                    CareerCard()
                    AchievementsCard()
                    #if DEBUG
                    // Developer tool for scrubbing the day/weather cycle; not in App Store builds.
                    skyLab
                    #endif
                }
                .padding(.horizontal, 16)
                .padding(.bottom, 30)
            }
            .navigationTitle("Journal")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Settings", systemImage: "gearshape.fill") { showSettings = true }
                }
                ToolbarItem(placement: .topBarLeading) {
                    Button("Done", systemImage: "xmark") {
                        model.env.timeOverride = nil
                        model.env.weatherOverride = nil
                        dismiss()
                    }
                }
            }
            .sheet(isPresented: $showLetters) { LettersView().environment(model) }
            .sheet(isPresented: $showTravel) { TravelView().environment(model) }
            .sheet(isPresented: $showSettings) { SettingsView().environment(model) }
            .alert("Rename your sprout", isPresented: $editingName) {
                TextField("Name", text: $nameDraft)
                Button("Save") {
                    let n = nameDraft.trimmingCharacters(in: .whitespacesAndNewlines)
                    if !n.isEmpty { model.state.companionName = String(n.prefix(16)) }
                }
                Button("Cancel", role: .cancel) {}
            }
        }
        .presentationDetents([.medium, .large])
        .presentationBackgroundInteraction(.enabled(upThrough: .medium))
    }

    private var companionCard: some View {
        HStack(spacing: 16) {
            LevelBadge(level: model.state.level, progress: model.state.levelProgress, size: 64)
            VStack(alignment: .leading, spacing: 6) {
                Button {
                    nameDraft = model.state.companionName
                    editingName = true
                } label: {
                    HStack(spacing: 6) {
                        Text(model.state.companionName).font(.rounded(24, .heavy))
                        Image(systemName: "pencil").font(.system(size: 14, weight: .bold)).foregroundStyle(.secondary)
                    }
                }
                .buttonStyle(.plain)
                Text("\(model.state.sproutStage.title) · \(model.state.xpIntoLevel)/\(model.state.xpForLevel) XP to level \(model.state.level + 1)")
                    .font(.rounded(14, .medium))
                    .foregroundStyle(.secondary)
                GlowBar(progress: model.state.levelProgress, height: 10)
            }
        }
        .padding(18)
        .glassCard(cornerRadius: 28)
    }

    private var statsGrid: some View {
        let s = model.state
        return LazyVGrid(columns: [GridItem(.flexible(), spacing: 12), GridItem(.flexible(), spacing: 12)], spacing: 12) {
            StatTile(value: "\(s.streak)", label: "Day streak", symbol: "flame.fill", tint: .orange)
            StatTile(value: "\(s.bestStreak)", label: "Best streak", symbol: "trophy.fill", tint: .yellow)
            StatTile(value: "\(s.totalWakeUps)", label: "Total wins", symbol: "sunrise.fill", tint: Theme.sun)
            StatTile(value: "\(s.total(of: .pushups) + s.total(of: .squats))", label: "Reps done", symbol: "figure.strengthtraining.functional", tint: Theme.leaf)
            StatTile(value: "\(s.total(of: .hunt))", label: "Items found", symbol: "magnifyingglass", tint: Theme.sky)
            StatTile(value: "\(s.cropsHarvested)", label: "Crops harvested", symbol: "basket.fill", tint: Theme.leafLight)
            StatTile(value: "\(s.coinsEarned)", label: "Coins earned", symbol: "dollarsign.circle.fill", tint: .yellow)
            StatTile(value: "\(s.streakFreezes)", label: "Streak freezes", symbol: "snowflake", tint: .cyan)
        }
    }

    private var skyLab: some View {
        VStack(alignment: .leading, spacing: 12) {
            Button {
                withAnimation(.snappy) { labOpen.toggle() }
                if !labOpen { model.env.timeOverride = nil; model.env.weatherOverride = nil; labHours = 0 }
            } label: {
                HStack {
                    Label("Sky Lab", systemImage: "sparkles")
                        .font(.rounded(19, .bold))
                    Spacer()
                    Text(labOpen ? "Back to live" : "Explore")
                        .font(.rounded(14, .semibold))
                        .foregroundStyle(Theme.sun)
                }
            }
            .buttonStyle(.plain)
            Text("Your island's sky is live: the real sun, moon phase and weather where you are. Scrub through a day to see it all.")
                .font(.rounded(14, .medium))
                .foregroundStyle(.secondary)
            if labOpen {
                VStack(alignment: .leading, spacing: 6) {
                    let date = Date.now.addingTimeInterval(labHours * 3600)
                    HStack {
                        Text(date.formatted(date: .omitted, time: .shortened))
                            .font(.rounded(17, .bold)).monospacedDigit()
                        Spacer()
                        Text(Astronomy.moonPhaseName(Astronomy.moonPhase(date: date)))
                            .font(.rounded(13, .medium)).foregroundStyle(.secondary)
                    }
                    Slider(value: $labHours, in: 0...24, step: 0.1)
                        .tint(Theme.sun)
                        .onChange(of: labHours) { _, h in
                            model.env.timeOverride = h == 0 ? nil : Date.now.addingTimeInterval(h * 3600)
                        }
                }
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        chip("Live", symbol: "location.fill", selected: model.env.weatherOverride == nil) {
                            model.env.weatherOverride = nil
                        }
                        ForEach(WeatherKind.allCases) { kind in
                            chip(kind.title, symbol: kind.symbol(isDay: true), selected: model.env.weatherOverride == kind) {
                                model.env.weatherOverride = kind
                            }
                        }
                    }
                }
            }
        }
        .padding(18)
        .glassCard(cornerRadius: 28)
    }

    private func chip(_ title: String, symbol: String, selected: Bool, action: @escaping () -> Void) -> some View {
        Button {
            Haptics.select()
            action()
        } label: {
            Label(title, systemImage: symbol)
                .font(.rounded(13, .semibold))
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .foregroundStyle(selected ? Theme.ink : .primary)
                .background(selected ? AnyShapeStyle(Theme.sunGradient) : AnyShapeStyle(.quaternary), in: .capsule)
        }
        .buttonStyle(.plain)
    }

    private var plusCard: some View {
        Button {
            if !model.isPlus { model.paywallReason = nil; model.showPaywall = true }
        } label: {
            HStack(spacing: 14) {
                Image(systemName: "sparkles")
                    .font(.system(size: 24, weight: .bold))
                    .foregroundStyle(.white)
                    .frame(width: 48, height: 48)
                    .background(LinearGradient(colors: [Theme.berry, Theme.sun], startPoint: .topLeading, endPoint: .bottomTrailing), in: .rect(cornerRadius: 14))
                VStack(alignment: .leading, spacing: 2) {
                    Text(model.isPlus ? "You're a Riser+ member" : "Riser+")
                        .font(.rounded(18, .bold))
                    Text(model.isPlus ? "Thanks for supporting an indie maker ☀️" : "Premium decor, +50% coins, streak freezes & more")
                        .font(.rounded(13, .medium))
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.leading)
                }
                Spacer()
                if !model.isPlus { Image(systemName: "chevron.right").foregroundStyle(.tertiary) }
            }
            .padding(16)
            .contentShape(.rect(cornerRadius: 26))
        }
        .buttonStyle(.plain)
        .glassCard(cornerRadius: 26, interactive: true)
    }

    private var settings: some View {
        VStack(spacing: 0) {
            toggleRow("Island music", symbol: "music.note", isOn: Binding(get: { model.state.islandMusicOn }, set: { model.setMusic($0) }))
            Divider().padding(.leading, 52)
            toggleRow("Nature sounds", symbol: "leaf.fill", isOn: Binding(get: { model.state.ambienceOn }, set: { model.setAmbience($0) }))
            Divider().padding(.leading, 52)
            toggleRow("Sound effects", symbol: "speaker.wave.2.fill", isOn: Binding(get: { model.state.sfxOn }, set: { model.setEffects($0) }))
            Divider().padding(.leading, 52)
            toggleRow("Escape-proof alarms", symbol: "lock.fill", isOn: Binding(get: { model.state.escapeProof }, set: { model.setEscapeProof($0) }))
            if model.env.locationStatus != .authorizedWhenInUse && model.env.locationStatus != .authorizedAlways {
                Divider().padding(.leading, 52)
                Button {
                    model.env.requestLocation()
                } label: {
                    HStack(spacing: 14) {
                        Image(systemName: "location.fill").foregroundStyle(Theme.sky).frame(width: 24)
                        Text("Match my real sky").font(.rounded(16, .semibold))
                        Spacer()
                        Image(systemName: "chevron.right").foregroundStyle(.tertiary)
                    }
                    .padding(.vertical, 14)
                    .padding(.horizontal, 16)
                    .contentShape(.rect)
                }
                .buttonStyle(.plain)
            }
            Divider().padding(.leading, 52)
            Button {
                Task { await model.purchases.restore() }
            } label: {
                HStack(spacing: 14) {
                    Image(systemName: "arrow.clockwise").foregroundStyle(.secondary).frame(width: 24)
                    Text("Restore purchases").font(.rounded(16, .semibold))
                    Spacer()
                }
                .padding(.vertical, 14)
                .padding(.horizontal, 16)
                .contentShape(.rect)
            }
            .buttonStyle(.plain)
            #if DEBUG
            Divider().padding(.leading, 52)
            Button("Debug: toggle Riser+ / +200 coins / +300 XP") {
                model.purchases.debugTogglePlus()
                model.state.coins += 200
                model.state.xp += 300
            }
            .font(.footnote)
            .padding(14)
            #endif
        }
        .glassCard(cornerRadius: 26)
    }

    private func toggleRow(_ title: String, symbol: String, isOn: Binding<Bool>) -> some View {
        Toggle(isOn: isOn) {
            HStack(spacing: 14) {
                Image(systemName: symbol).foregroundStyle(Theme.sun).frame(width: 24)
                Text(title).font(.rounded(16, .semibold))
            }
        }
        .tint(Theme.sun)
        .padding(.vertical, 10)
        .padding(.horizontal, 16)
    }

    private var about: some View {
        VStack(spacing: 6) {
            Text("Riser · made with ☀️ for early birds and night owls alike")
            HStack(spacing: 14) {
                Link("Privacy", destination: Config.privacyURL)
                Link("Terms", destination: Config.termsURL)
                Link("Weather data sources", destination: model.env.attribution?.legalPageURL
                     ?? URL(string: "https://weatherkit.apple.com/legal-attribution.html")!)
            }
        }
        .font(.rounded(12, .medium))
        .foregroundStyle(.secondary)
        .padding(.top, 6)
    }
}

struct StatTile: View {
    var value: String
    var label: String
    var symbol: String
    var tint: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Image(systemName: symbol)
                .font(.system(size: 18, weight: .bold))
                .foregroundStyle(tint)
            Text(value)
                .font(.rounded(28, .heavy))
                .monospacedDigit()
            Text(label)
                .font(.rounded(13, .semibold))
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .glassCard(cornerRadius: 24)
        .accessibilityElement(children: .combine)
    }
}

/// Five weeks of mornings: a sun for every mission won.
struct MorningCalendar: View {
    var history: [WakeRecord]

    var body: some View {
        let cal = Calendar.current
        let today = cal.startOfDay(for: .now)
        let wonDays = Set(history.filter(\.isWin).map { cal.startOfDay(for: $0.date) })
        let days = (0..<35).reversed().compactMap { cal.date(byAdding: .day, value: -$0, to: today) }
        VStack(alignment: .leading, spacing: 12) {
            Text("Mornings")
                .font(.rounded(19, .bold))
            LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 6), count: 7), spacing: 6) {
                ForEach(days, id: \.self) { day in
                    let won = wonDays.contains(day)
                    ZStack {
                        RoundedRectangle(cornerRadius: 10, style: .continuous)
                            .fill(won ? AnyShapeStyle(Theme.sunGradient) : AnyShapeStyle(.white.opacity(0.06)))
                        if won {
                            Image(systemName: "sun.max.fill").font(.system(size: 14, weight: .bold)).foregroundStyle(.white)
                        } else {
                            Text("\(cal.component(.day, from: day))")
                                .font(.rounded(12, .semibold))
                                .foregroundStyle(cal.isDateInToday(day) ? .primary : .tertiary)
                        }
                    }
                    .aspectRatio(1, contentMode: .fit)
                    .accessibilityLabel("\(day.formatted(date: .abbreviated, time: .omitted)), \(won ? "won" : "no mission")")
                }
            }
        }
        .padding(18)
        .glassCard(cornerRadius: 28)
    }
}

// MARK: - Streak

/// Opened from the streak pill: the streak, freezes, and a month-by-month calendar of alarm mornings.
struct StreakSheet: View {
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss
    /// First day of the month on screen.
    @State private var month = Calendar.current.dateInterval(of: .month, for: .now)?.start ?? .now
    @State private var forward = true

    var body: some View {
        let s = model.state
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    hero
                    HStack(spacing: 10) {
                        StatTile(value: "\(s.bestStreak)", label: "Best streak", symbol: "trophy.fill", tint: .yellow)
                        StatTile(value: "\(s.totalWakeUps)", label: "Total wins", symbol: "sunrise.fill", tint: Theme.sun)
                        StatTile(value: "\(s.streakFreezes)", label: s.streakFreezes == 1 ? "Freeze" : "Freezes", symbol: "snowflake", tint: .cyan)
                    }
                    calendarCard
                    Label {
                        Text(model.isPlus
                             ? "A streak freeze covers one missed alarm morning automatically. Riser+ tops you up each week (up to 2)."
                             : "A streak freeze covers one missed alarm morning automatically. Riser+ members get one every week.")
                    } icon: {
                        Image(systemName: "snowflake").foregroundStyle(.cyan)
                    }
                    .font(.rounded(13, .medium))
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, 4)
                }
                .padding(.horizontal, 16)
                .padding(.bottom, 30)
            }
            .navigationTitle("Streak")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Done", systemImage: "xmark") { dismiss() }
                }
            }
        }
        .presentationDetents([.large])
    }

    // MARK: Hero

    private var hero: some View {
        let streak = model.state.streak
        return VStack(spacing: 6) {
            Image(systemName: "flame.fill")
                .font(.system(size: 40, weight: .bold))
                .foregroundStyle(LinearGradient(colors: [.yellow, .orange, .red], startPoint: .top, endPoint: .bottom))
                .symbolEffect(.bounce, options: .repeat(.periodic(delay: 2.5)))
                .frame(width: 76, height: 76)
                .glassEffect(.regular.tint(Theme.sun.opacity(0.25)), in: .circle)
                .padding(.bottom, 4)
            Text(streak, format: .number)
                .font(.system(size: 56, weight: .heavy, design: .rounded))
                .monospacedDigit()
                .contentTransition(.numericText(value: Double(streak)))
            Text(streak == 1 ? "morning in a row" : "mornings in a row")
                .font(.rounded(17, .semibold))
                .foregroundStyle(.secondary)
            Text(todayLine)
                .font(.rounded(14, .semibold))
                .foregroundStyle(Theme.sunLight)
                .multilineTextAlignment(.center)
                .padding(.top, 6)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 18)
        .padding(.horizontal, 16)
        .glassCard(cornerRadius: 30, tint: Theme.sun.opacity(0.12))
        .accessibilityElement(children: .combine)
    }

    private var todayLine: String {
        let now = model.env.effectiveDate
        if model.state.woke { return "Today's won. See you tomorrow! ☀️" }
        if model.isAlarmDay(now) { return "Win today's mission to keep it growing" }
        return "Day off today. Your streak is safe 🌿"
    }

    // MARK: Calendar

    enum DayKind { case won, frozen, missed, off, today, future }

    private var calendarCard: some View {
        let cal = Calendar.current
        let today = cal.startOfDay(for: model.env.effectiveDate)
        let thisMonth = cal.dateInterval(of: .month, for: today)?.start ?? today
        let first = firstMonth
        let days = monthDays(month)
        let kinds = days.map { $0.map { kind($0, today: today) } }
        let counts = (won: kinds.filter { $0 == .won }.count, missed: kinds.filter { $0 == .missed }.count,
                      frozen: kinds.filter { $0 == .frozen }.count)
        return VStack(spacing: 14) {
            HStack {
                pageButton("chevron.left", "Previous month", enabled: month > first) { page(-1) }
                Spacer()
                VStack(spacing: 2) {
                    Text(month.formatted(.dateTime.month(.wide).year()))
                        .font(.rounded(19, .bold))
                        .contentTransition(.opacity)
                    Text(summary(counts))
                        .font(.rounded(12, .semibold))
                        .foregroundStyle(.secondary)
                        .contentTransition(.opacity)
                }
                Spacer()
                pageButton("chevron.right", "Next month", enabled: month < thisMonth) { page(1) }
            }
            HStack(spacing: 6) {
                ForEach(Array(weekdaySymbols.enumerated()), id: \.offset) { _, d in
                    Text(d)
                        .font(.rounded(11, .bold))
                        .foregroundStyle(.tertiary)
                        .frame(maxWidth: .infinity)
                }
            }
            LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 6), count: 7), spacing: 6) {
                ForEach(Array(days.enumerated()), id: \.offset) { i, day in
                    if let day, let k = kinds[i] {
                        DayCell(day: cal.component(.day, from: day), kind: k, isToday: day == today)
                            .accessibilityLabel("\(day.formatted(date: .complete, time: .omitted)), \(label(k))")
                    } else {
                        Color.clear.aspectRatio(1, contentMode: .fit)
                    }
                }
            }
            .id(month)
            .transition(.push(from: forward ? .trailing : .leading))
            legend
        }
        .padding(18)
        .glassCard(cornerRadius: 28)
        .clipped()
        // Simultaneous, so a vertical drag that starts on the calendar still scrolls the sheet.
        .simultaneousGesture(
            DragGesture(minimumDistance: 24)
                .onEnded { v in
                    guard abs(v.translation.width) > abs(v.translation.height) else { return }
                    if v.translation.width < -40, month < thisMonth { page(1) }
                    if v.translation.width > 40, month > first { page(-1) }
                }
        )
    }

    private var legend: some View {
        HStack(spacing: 12) {
            legendItem("Won", symbol: "sun.max.fill", tint: Theme.sun)
            legendItem("Frozen", symbol: "snowflake", tint: .cyan)
            legendItem("Missed", symbol: "moon.zzz.fill", tint: Theme.berry)
            legendItem("Day off", symbol: "leaf.fill", tint: .secondary.opacity(0.8))
        }
        .font(.rounded(11, .semibold))
        .foregroundStyle(.secondary)
        .frame(maxWidth: .infinity)
    }

    private func legendItem(_ title: String, symbol: String, tint: Color) -> some View {
        HStack(spacing: 4) {
            Image(systemName: symbol).foregroundStyle(tint)
            Text(title)
        }
        .lineLimit(1)
    }

    private func pageButton(_ symbol: String, _ label: String, enabled: Bool, action: @escaping () -> Void) -> some View {
        Button {
            Haptics.select()
            action()
        } label: {
            Image(systemName: symbol)
                .font(.system(size: 15, weight: .bold))
                .frame(width: 38, height: 38)
                .contentShape(.circle)
        }
        .buttonStyle(.plain)
        .glassEffect(.regular.interactive(), in: .circle)
        .disabled(!enabled)
        .opacity(enabled ? 1 : 0.3)
        .accessibilityLabel(label)
    }

    private func page(_ by: Int) {
        guard let next = Calendar.current.date(byAdding: .month, value: by, to: month) else { return }
        forward = by > 0
        withAnimation(.snappy(duration: 0.3)) { month = next }
    }

    private func summary(_ c: (won: Int, missed: Int, frozen: Int)) -> String {
        var parts = ["\(c.won) won"]
        if c.missed > 0 { parts.append("\(c.missed) missed") }
        if c.frozen > 0 { parts.append("\(c.frozen) frozen") }
        return parts.joined(separator: " · ")
    }

    private func label(_ k: DayKind) -> String {
        switch k {
        case .won: "mission won"
        case .frozen: "covered by a streak freeze"
        case .missed: "missed alarm"
        case .off: "no alarm"
        case .today: "today"
        case .future: "upcoming"
        }
    }

    /// Weekday initials in the calendar's own order (Sunday- or Monday-first).
    private var weekdaySymbols: [String] {
        let cal = Calendar.current
        let symbols = cal.veryShortStandaloneWeekdaySymbols
        return (0..<7).map { symbols[(cal.firstWeekday - 1 + $0) % 7] }
    }

    /// The month as a grid: leading blanks, then each day.
    private func monthDays(_ start: Date) -> [Date?] {
        let cal = Calendar.current
        guard let range = cal.range(of: .day, in: .month, for: start) else { return [] }
        let lead = (cal.component(.weekday, from: start) - cal.firstWeekday + 7) % 7
        return Array(repeating: nil, count: lead) + range.compactMap { cal.date(byAdding: .day, value: $0 - 1, to: start) }
    }

    /// The first day Riser knows about: nothing before it can have been missed.
    private var firstDay: Date {
        let cal = Calendar.current
        let dates = model.state.history.map(\.date) + model.state.frozenDays + model.state.alarms.compactMap(\.createdAt)
        return cal.startOfDay(for: dates.min() ?? model.env.effectiveDate)
    }

    private var firstMonth: Date {
        Calendar.current.dateInterval(of: .month, for: firstDay)?.start ?? month
    }

    private func kind(_ day: Date, today: Date) -> DayKind {
        let cal = Calendar.current
        if model.state.wonDays.contains(day) { return .won }
        if day > today { return .future }
        if model.state.frozenDays.contains(where: { cal.isDate($0, inSameDayAs: day) }) { return .frozen }
        if day == today { return .today }
        if day >= firstDay && model.isMissableAlarmDay(day) { return .missed }
        return .off
    }
}

/// One day on the streak calendar.
private struct DayCell: View {
    var day: Int
    var kind: StreakSheet.DayKind
    var isToday: Bool

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 11, style: .continuous)
                .fill(fill)
            VStack(spacing: 1) {
                if let symbol {
                    Image(systemName: symbol)
                        .font(.system(size: 11, weight: .bold))
                        .foregroundStyle(symbolStyle)
                }
                Text("\(day)")
                    .font(.rounded(13, kind == .won || isToday ? .heavy : .semibold))
                    .monospacedDigit()
                    .foregroundStyle(textStyle)
            }
        }
        .overlay {
            if isToday {
                RoundedRectangle(cornerRadius: 11, style: .continuous)
                    .strokeBorder(.white, lineWidth: 2)
            }
        }
        .shadow(color: kind == .won ? Theme.sun.opacity(0.35) : .clear, radius: 6, y: 2)
        .aspectRatio(1, contentMode: .fit)
    }

    private var fill: AnyShapeStyle {
        switch kind {
        case .won: AnyShapeStyle(Theme.sunGradient)
        case .frozen: AnyShapeStyle(Color.cyan.opacity(0.28))
        case .missed: AnyShapeStyle(Theme.berry.opacity(0.16))
        case .today: AnyShapeStyle(Color.white.opacity(0.14))
        case .off, .future: AnyShapeStyle(Color.white.opacity(0.05))
        }
    }

    private var symbol: String? {
        switch kind {
        case .won: "sun.max.fill"
        case .frozen: "snowflake"
        case .missed: "moon.zzz.fill"
        default: nil
        }
    }

    private var symbolStyle: AnyShapeStyle {
        switch kind {
        case .won: AnyShapeStyle(Color.white)
        case .frozen: AnyShapeStyle(Color.cyan)
        default: AnyShapeStyle(Theme.berry)
        }
    }

    private var textStyle: AnyShapeStyle {
        switch kind {
        case .won: AnyShapeStyle(Theme.ink)
        case .today, .frozen: AnyShapeStyle(Color.white)
        case .missed: AnyShapeStyle(Color.white.opacity(0.6))
        case .off: AnyShapeStyle(Color.white.opacity(0.4))
        case .future: AnyShapeStyle(Color.white.opacity(0.25))
        }
    }
}
