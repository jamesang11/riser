import SwiftUI
import WeatherKit

/// Everything configurable, in one place: sound, alarms, the sprout, the sky, Riser+.
struct SettingsView: View {
    @AppStorage("riser.nagInterval") private var nagInterval: Double = 10
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss
    @State private var nameDraft = ""
    @State private var showManage = false
    @State private var restoreMessage: String?

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    HStack {
                        Label("Name", systemImage: "leaf.fill")
                        TextField("Name", text: $nameDraft)
                            .multilineTextAlignment(.trailing)
                            .submitLabel(.done)
                            .onSubmit(saveName)
                    }
                } header: {
                    Text("Your sprout")
                }

                Section {
                    Toggle(isOn: Binding(get: { model.state.islandMusicOn }, set: { model.setMusic($0) })) {
                        Label("Island music", systemImage: "music.note")
                    }
                    Toggle(isOn: Binding(get: { model.state.ambienceOn }, set: { model.setAmbience($0) })) {
                        Label("Nature sounds", systemImage: "leaf")
                    }
                    Toggle(isOn: Binding(get: { model.state.sfxOn }, set: { model.setEffects($0) })) {
                        Label("Sound effects", systemImage: "hand.tap.fill")
                    }
                } header: {
                    Text("Sound")
                } footer: {
                    Text("Alarms always ring at full volume so you still wake up.")
                }

                Section {
                    Toggle(isOn: Binding(get: { model.state.escapeProof }, set: { model.setEscapeProof($0) })) {
                        Label("Escape-proof", systemImage: "lock.fill")
                    }
                    Picker(selection: $nagInterval) {
                        ForEach(MissionInbox.nagIntervals, id: \.self) { Text(MissionInbox.intervalText($0)).tag($0) }
                    } label: {
                        Label("Rings again after", systemImage: "arrow.clockwise")
                    }
                    .disabled(!model.state.escapeProof)
                    .opacity(model.state.escapeProof ? 1 : 0.5)
                } header: {
                    Text("Alarms")
                } footer: {
                    Text("If you press Stop instead of finishing your mission, the alarm rings again after \(MissionInbox.intervalText(nagInterval)), and keeps coming back for up to an hour.")
                }

                if model.env.locationStatus != .authorizedWhenInUse && model.env.locationStatus != .authorizedAlways {
                    Section("Sky") {
                        Button {
                            model.env.requestLocation()
                        } label: {
                            Label("Match my real sky", systemImage: "location.fill")
                        }
                    }
                }

                Section("Riser+") {
                    Button {
                        model.paywallReason = nil
                        model.showPaywall = true
                    } label: {
                        Label(model.isPlus ? "You're a Riser+ member" : "Get Riser+", systemImage: "sparkles")
                    }
                    .disabled(model.isPlus)
                    Button {
                        Task {
                            await model.purchases.restore()
                            restoreMessage = model.purchases.lastError ?? "Riser+ is restored. Welcome back!"
                            model.purchases.lastError = nil
                        }
                    } label: {
                        Label("Restore purchases", systemImage: "arrow.clockwise")
                    }
                    if model.isPlus {
                        Button {
                            showManage = true
                        } label: {
                            Label("Manage subscription", systemImage: "creditcard")
                        }
                    }
                }

                Section("Help") {
                    Link(destination: Config.supportURL) { Label("Help & Support", systemImage: "questionmark.circle.fill") }
                }

                Section("About") {
                    Link(destination: Config.privacyURL) { Label("Privacy Policy", systemImage: "hand.raised.fill") }
                    Link(destination: Config.termsURL) { Label("Terms of Use", systemImage: "doc.text") }
                    Link(destination: Config.appleEULA) { Label("Apple Standard EULA", systemImage: "doc.plaintext") }
                    WeatherAttributionRow(attribution: model.env.attribution)
                }

                #if DEBUG
                Section("Debug") {
                    Button("Toggle Riser+ / +200 coins / +300 XP") {
                        model.purchases.debugTogglePlus()
                        model.state.coins += 200
                        model.state.xp += 300
                    }
                    Button("Simulate a missed morning") {
                        model.debugMiss()
                    }
                    Button("Reset neglect") { model.debugResetNeglect() }
                }
                #endif
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done", systemImage: "checkmark") {
                        saveName()
                        dismiss()
                    }
                }
            }
            .onAppear { nameDraft = model.state.companionName }
            .manageSubscriptionsSheet(isPresented: $showManage)
            .alert("Restore purchases", isPresented: Binding(get: { restoreMessage != nil }, set: { if !$0 { restoreMessage = nil } })) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(restoreMessage ?? "")
            }
        }
    }

    private func saveName() {
        let n = nameDraft.trimmingCharacters(in: .whitespacesAndNewlines)
        if !n.isEmpty { model.state.companionName = String(n.prefix(16)) }
    }
}

/// Journal: Sprig's job title, wage and progress to the next promotion.
struct CareerCard: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        let s = model.state
        let rank = s.rankInfo
        let next = s.rank + 1 < Career.ranks.count ? Career.ranks[s.rank + 1] : nil
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text(rank.emoji).font(.system(size: 34))
                VStack(alignment: .leading, spacing: 2) {
                    Text(rank.title).font(.rounded(20, .heavy))
                    Text("Wage \(rank.wage) coins a shift · \(s.careerPoints) shifts worked")
                        .font(.rounded(13, .medium))
                        .foregroundStyle(.secondary)
                }
                Spacer()
            }
            if let next {
                GlowBar(progress: Career.progress(points: s.careerPoints), height: 8)
                Text("\(next.points - s.careerPoints) more shifts to \(next.title) \(next.emoji). Missing 2 mornings in a row means demotion.")
                    .font(.rounded(12, .medium))
                    .foregroundStyle(.secondary)
            } else {
                Text("Top of the ladder. The farm is yours!").font(.rounded(13, .semibold)).foregroundStyle(.secondary)
            }
            if s.debt > 0 {
                Label("In debt: \(s.debt) coins. Wages pay it off first.", systemImage: "exclamationmark.triangle.fill")
                    .font(.rounded(13, .semibold))
                    .foregroundStyle(.orange)
            }
        }
        .padding(18)
        .glassCard(cornerRadius: 28)
    }
}

/// Sprig's mailbox.
struct LettersView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 14) {
                    if model.state.letters.isEmpty {
                        ContentUnavailableView("No letters yet", systemImage: "envelope", description: Text("Letters from the farm and from \(model.state.companionName) show up here."))
                    }
                    ForEach(model.state.letters) { letter in
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Text(letter.from).font(.rounded(13, .bold)).foregroundStyle(Theme.ink.opacity(0.6))
                                Spacer()
                                Text(letter.date.formatted(.relative(presentation: .named)))
                                    .font(.rounded(12, .medium)).foregroundStyle(Theme.ink.opacity(0.5))
                            }
                            Text(letter.title).font(.rounded(20, .heavy)).foregroundStyle(Theme.ink)
                            Text(letter.body)
                                .font(.system(size: 16, design: .serif))
                                .foregroundStyle(Theme.ink.opacity(0.85))
                                .lineSpacing(3)
                        }
                        .padding(18)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Theme.cream, in: .rect(cornerRadius: 20))
                        .overlay(alignment: .topTrailing) {
                            if !letter.read {
                                Circle().fill(Theme.berry).frame(width: 10, height: 10).padding(12)
                            }
                        }
                    }
                }
                .padding(16)
            }
            .navigationTitle("Mailbox")
            .navigationBarTitleDisplayMode(.inline)
        }
        .presentationDetents([.medium, .large])
        .onDisappear { model.markLettersRead() }
    }
}

/// Journal: long-term milestones with progress.
struct AchievementsCard: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        let done = model.state.claimedAchievements.count
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Achievements").font(.rounded(19, .bold))
                Spacer()
                Text("\(done)/\(AchievementCatalog.all.count)")
                    .font(.rounded(15, .bold))
                    .foregroundStyle(.secondary)
            }
            LazyVGrid(columns: [GridItem(.flexible(), spacing: 10), GridItem(.flexible(), spacing: 10)], spacing: 10) {
                ForEach(AchievementCatalog.all) { a in
                    let claimed = model.state.claimedAchievements.contains(a.id)
                    let p = min(a.progress(model.state), a.goal)
                    VStack(alignment: .leading, spacing: 6) {
                        HStack(spacing: 8) {
                            Image(systemName: a.symbol)
                                .font(.system(size: 16, weight: .bold))
                                .foregroundStyle(claimed ? AnyShapeStyle(Theme.sunGradient) : AnyShapeStyle(.secondary))
                                .frame(width: 30, height: 30)
                                .background(.white.opacity(claimed ? 0.15 : 0.06), in: .circle)
                            Text(a.title).font(.rounded(13, .bold)).lineLimit(2).minimumScaleFactor(0.85)
                        }
                        Text(a.detail).font(.rounded(11, .medium)).foregroundStyle(.secondary).lineLimit(2)
                        if claimed {
                            Label("+\(a.reward) coins", systemImage: "checkmark.seal.fill")
                                .font(.rounded(11, .bold))
                                .foregroundStyle(Theme.leafLight)
                        } else {
                            GlowBar(progress: Double(p) / Double(max(1, a.goal)), height: 6)
                            Text("\(p)/\(a.goal)").font(.rounded(10, .semibold)).foregroundStyle(.tertiary).monospacedDigit()
                        }
                    }
                    .padding(12)
                    .frame(maxWidth: .infinity, minHeight: 118, alignment: .topLeading)
                    .background(.white.opacity(0.05), in: .rect(cornerRadius: 18))
                    .opacity(claimed ? 1 : 0.85)
                    .accessibilityElement(children: .combine)
                }
            }
        }
        .padding(18)
        .glassCard(cornerRadius: 28)
    }
}


/// The Apple Weather mark and a link to its data sources (WeatherKit attribution requirement).
struct WeatherAttributionRow: View {
    var attribution: WeatherAttribution?
    @Environment(\.colorScheme) private var scheme

    var body: some View {
        Link(destination: attribution?.legalPageURL ?? URL(string: "https://weatherkit.apple.com/legal-attribution.html")!) {
            HStack {
                if let attribution {
                    AsyncImage(url: scheme == .dark ? attribution.combinedMarkDarkURL : attribution.combinedMarkLightURL) { image in
                        image.resizable().scaledToFit()
                    } placeholder: {
                        Text("Weather")
                    }
                    .frame(height: 16)
                } else {
                    Label("Weather", systemImage: "cloud.sun")
                }
                Spacer()
                Text("Data sources").font(.footnote).foregroundStyle(.secondary)
            }
        }
        .accessibilityLabel("Weather data by Apple Weather. Data sources.")
    }
}
