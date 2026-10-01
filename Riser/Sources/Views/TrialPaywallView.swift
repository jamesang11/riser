import RevenueCat
import SwiftUI

/// The paywall at the end of onboarding: 3 days free, then Riser+.
/// Shows exactly when you'll be charged, and reminds you the day before.
struct TrialPaywallView: View {
    @Environment(AppModel.self) private var model
    @State private var selectedID: String?
    @State private var appeared = false
    @State private var restoreMessage: String?

    struct PlanOption: Identifiable, Equatable {
        var id: String
        var type: PackageType
        var title: String
        var price: String
        /// "year", "week"… (nil for lifetime).
        var period: String?
        var note: String?
        var trialDays: Int
        var package: Package?

        static func == (a: PlanOption, b: PlanOption) -> Bool { a.id == b.id }

        init(id: String, type: PackageType, title: String, price: String, period: String?, note: String?, trialDays: Int, package: Package? = nil) {
            self.id = id
            self.type = type
            self.title = title
            self.price = price
            self.period = period
            self.note = note
            self.trialDays = trialDays
            self.package = package
        }

        init(_ p: Package) {
            let product = p.storeProduct
            var days = 0
            if let intro = product.introductoryDiscount, intro.paymentMode == .freeTrial {
                let v = intro.subscriptionPeriod.value
                switch intro.subscriptionPeriod.unit {
                case .day: days = v
                case .week: days = v * 7
                case .month: days = v * 30
                case .year: days = v * 365
                @unknown default: days = 0
                }
            }
            let title: String
            var note: String?
            switch p.packageType {
            case .annual:
                title = "Yearly"
                note = nil
            case .weekly: title = "Weekly"
            case .monthly: title = "Monthly"
            case .lifetime:
                title = "Lifetime"
                note = "Pay once, keep it forever"
            default: title = product.localizedTitle
            }
            self.init(id: p.identifier, type: p.packageType, title: title, price: product.localizedPriceString,
                      period: product.subscriptionPeriod?.unitText, note: note, trialDays: days, package: p)
        }
    }

    private var options: [PlanOption] {
        let order: [PackageType] = [.annual, .monthly, .weekly, .lifetime]
        let packages = (model.purchases.offering?.availablePackages ?? [])
            .sorted { (order.firstIndex(of: $0.packageType) ?? 9) < (order.firstIndex(of: $1.packageType) ?? 9) }
        var real = packages.map(PlanOption.init)
        // No trial on offer if this Apple ID already used it: the App Store would charge straight away.
        for i in real.indices where real[i].package.map({ model.purchases.trialUsed.contains($0.storeProduct.productIdentifier) }) == true {
            real[i].trialDays = 0
        }
        // "Save 50%": the yearly price against twelve months of the monthly plan.
        if let yearly = packages.first(where: { $0.packageType == .annual }),
           let monthly = packages.first(where: { $0.packageType == .monthly }),
           let i = real.firstIndex(where: { $0.type == .annual }) {
            let y = NSDecimalNumber(decimal: yearly.storeProduct.price as Decimal).doubleValue
            let m = NSDecimalNumber(decimal: monthly.storeProduct.price as Decimal).doubleValue * 12
            if m > 0, y < m {
                let save = Int(((1 - y / m) * 100).rounded())
                // No per-month breakdown of the yearly price: App Review flags it as misleading.
                real[i].note = "Save \(save)% vs Monthly"
            }
        }
        #if DEBUG
        if real.isEmpty {
            return [
                PlanOption(id: "y", type: .annual, title: "Yearly", price: "$29.99", period: "year", note: "Save 50% vs Monthly", trialDays: 3),
                PlanOption(id: "m", type: .monthly, title: "Monthly", price: "$4.99", period: "month", note: nil, trialDays: 0),
                PlanOption(id: "l", type: .lifetime, title: "Lifetime", price: "$59.99", period: nil, note: "Pay once, keep it forever", trialDays: 0),
            ]
        }
        #endif
        return real
    }

    private var selected: PlanOption? { options.first { $0.id == selectedID } ?? options.first }
    private var name: String { model.state.companionName }
    private var alarmText: String {
        model.state.alarms.first(where: \.isEnabled)?.timeText ?? "sunrise"
    }

    var body: some View {
        ScrollView {
            VStack(spacing: 0) {
                hero
                VStack(spacing: 20) {
                    header
                    if let s = selected, s.trialDays > 0 { timeline(s) } else { perks }
                    plans
                    valueStack
                    footer
                }
                .padding(.horizontal, 22)
                .padding(.bottom, 20)
            }
        }
        .defaultScrollAnchor(.top)
        .overlay(alignment: .top) {
            // Keep the status bar readable over scrolled content.
            LinearGradient(colors: [Color(red: 0.06, green: 0.07, blue: 0.16), .clear], startPoint: .top, endPoint: .bottom)
                .frame(height: 64)
                .ignoresSafeArea(edges: .top)
                .allowsHitTesting(false)
        }
        .scrollBounceBehavior(.basedOnSize)
        .safeAreaInset(edge: .bottom) {
            VStack(spacing: 10) {
                cta
                legalLinks
            }
                .padding(.horizontal, 22)
                .padding(.top, 12)
                .padding(.bottom, 4)
                .background {
                    LinearGradient(colors: [Color(red: 0.06, green: 0.07, blue: 0.16).opacity(0), Color(red: 0.06, green: 0.07, blue: 0.16)],
                                   startPoint: .top, endPoint: .init(x: 0.5, y: 0.3))
                        .ignoresSafeArea()
                }
        }
        .background(Color(red: 0.06, green: 0.07, blue: 0.16).ignoresSafeArea())
        .ignoresSafeArea(edges: .top)
        .task {
            await model.purchases.refresh()
            if selectedID == nil { selectedID = options.first?.id }
            withAnimation(.spring(response: 0.6, dampingFraction: 0.8).delay(0.1)) { appeared = true }
        }
        .alert("Something went wrong", isPresented: Binding(get: { model.purchases.lastError != nil },
                                                             set: { if !$0 { model.purchases.lastError = nil } })) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(model.purchases.lastError ?? "")
        }
        .alert("Restore purchases", isPresented: Binding(get: { restoreMessage != nil }, set: { if !$0 { restoreMessage = nil } })) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(restoreMessage ?? "")
        }
    }

    // MARK: Sections

    private var hero: some View {
        ZStack(alignment: .bottom) {
            WorldView(sky: model.env.sky.isDay ? model.env.sky : morningSky,
                      built: Showcase.milestones[3].built, stage: .bloom, lastBuilt: nil,
                      petTick: 0, celebrateTick: appeared ? 1 : 0, buildMarkers: [], highlightedSlot: nil,
                      interactive: false, hat: "crown")
                .frame(height: 260)
            LinearGradient(colors: [.clear, Color(red: 0.06, green: 0.07, blue: 0.16)], startPoint: .center, endPoint: .bottom)
                .frame(height: 260)
                .allowsHitTesting(false)
        }
        .frame(height: 260)
        .accessibilityHidden(true)
    }

    private var morningSky: SkyState {
        let morning = Calendar.current.date(bySettingHour: 8, minute: 10, second: 0, of: .now) ?? .now
        return SkyState.compute(date: morning, lat: model.env.latitude, lon: model.env.longitude, weather: WeatherNow())
    }

    private var header: some View {
        VStack(spacing: 8) {
            Text("Wake up with \(name)")
                .font(.rounded(32, .heavy))
                .multilineTextAlignment(.center)
            Text("Your first alarm is set for \(alarmText). Unlock every mission, your island and \(name)'s whole world.")
                .font(.rounded(17, .semibold))
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding(.top, -20)
        .opacity(appeared ? 1 : 0)
        .offset(y: appeared ? 0 : 12)
    }

    /// Clear about exactly what happens and when.
    private func timeline(_ plan: PlanOption) -> some View {
        let end = Calendar.current.date(byAdding: .day, value: plan.trialDays, to: .now) ?? .now
        return VStack(alignment: .leading, spacing: 0) {
            timelineRow("lock.open.fill", Theme.leaf, "Today", "Full access: every mission, your island, \(name)'s job and vacations.", last: false)
            timelineRow("bell.fill", Theme.sun, "Day \(max(1, plan.trialDays - 1))", "We'll send you a reminder that your trial is ending.", last: false)
            timelineRow("star.fill", Theme.berry, end.formatted(.dateTime.month(.abbreviated).day()),
                        "You're charged \(plan.price)/\(plan.period ?? "year"). Cancel any time before and pay nothing.", last: true)
        }
        .padding(18)
        .glassCard(cornerRadius: 26)
    }

    private func timelineRow(_ symbol: String, _ tint: Color, _ title: String, _ detail: String, last: Bool) -> some View {
        HStack(alignment: .top, spacing: 14) {
            VStack(spacing: 0) {
                Image(systemName: symbol)
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(.white)
                    .frame(width: 34, height: 34)
                    .background(tint.gradient, in: .circle)
                if !last {
                    Rectangle()
                        .fill(.white.opacity(0.15))
                        .frame(width: 3)
                        .frame(minHeight: 22)
                }
            }
            VStack(alignment: .leading, spacing: 2) {
                Text(title).font(.rounded(16, .bold))
                Text(detail).font(.rounded(14, .medium)).foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .padding(.bottom, last ? 0 : 14)
        }
        .accessibilityElement(children: .combine)
    }

    /// Everything they get, and an honest line on why it costs money.
    private var valueStack: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Everything in Riser")
                .font(.rounded(20, .heavy))
            value("figure.core.training", Theme.sun, "4 wake-up missions", "Camera-counted push-ups and squats, item hunts and brain warm-ups")
            value("leaf.fill", Theme.leaf, "A companion with a real job", "\(name) works, earns, gets promoted, and really misses you when you sleep in")
            value("map.fill", Theme.berry, "3 islands, 30+ things to build", "Plus furniture, hats and 8 vacation spots to send \(name) to")
            value("moon.zzz.fill", .indigo, "A bedtime coach", "Sleep-cycle bedtimes and gentle wind-down nudges")
            value("sun.horizon.fill", Theme.sunLight, "Your real sky", "Live sun, moon phase and weather over your island")
            Divider().opacity(0.4)
            Label {
                Text("**Why it costs money:** Riser has no ads and never sells your data. Your subscription keeps it that way, and pays for new islands, missions and seasonal events.")
                    .font(.rounded(14, .medium))
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            } icon: {
                Image(systemName: "heart.fill").foregroundStyle(Theme.berry)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(18)
        .glassCard(cornerRadius: 26)
    }

    private func value(_ symbol: String, _ tint: Color, _ title: String, _ detail: String) -> some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: symbol)
                .font(.system(size: 15, weight: .bold))
                .foregroundStyle(.white)
                .frame(width: 32, height: 32)
                .background(tint.gradient, in: .rect(cornerRadius: 9))
            VStack(alignment: .leading, spacing: 1) {
                Text(title).font(.rounded(15, .bold))
                Text(detail).font(.rounded(13, .medium)).foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .accessibilityElement(children: .combine)
    }

    private var perks: some View {
        VStack(alignment: .leading, spacing: 12) {
            perk("alarm.fill", Theme.sun, "Wake-up missions your camera counts")
            perk("leaf.fill", Theme.leaf, "\(name), his job and your whole island")
            perk("house.fill", Theme.berry, "Every decoration, hat and vacation")
            perk("moon.zzz.fill", .indigo, "Bedtime nudges and a real sky")
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(18)
        .glassCard(cornerRadius: 26)
    }

    private func perk(_ symbol: String, _ tint: Color, _ text: String) -> some View {
        Label {
            Text(text).font(.rounded(15, .semibold))
        } icon: {
            Image(systemName: symbol).foregroundStyle(tint)
        }
    }

    @ViewBuilder
    private var plans: some View {
        if options.isEmpty {
            VStack(spacing: 8) {
                ProgressView()
                Text("Loading plans…").font(.footnote).foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 20)
        } else {
            VStack(spacing: 10) {
                ForEach(options) { option in
                    planRow(option)
                }
            }
        }
    }

    private func planRow(_ o: PlanOption) -> some View {
        let on = selected?.id == o.id
        return Button {
            selectedID = o.id
            Haptics.select()
        } label: {
            HStack(spacing: 14) {
                Image(systemName: on ? "checkmark.circle.fill" : "circle")
                    .font(.system(size: 22, weight: .semibold))
                    .foregroundStyle(on ? Theme.sun : .secondary)
                VStack(alignment: .leading, spacing: 2) {
                    HStack(spacing: 6) {
                        Text(o.title).font(.rounded(17, .bold))
                        if o.trialDays > 0 {
                            Text("\(o.trialDays) DAYS FREE")
                                .font(.rounded(10, .heavy))
                                .padding(.horizontal, 7)
                                .padding(.vertical, 3)
                                .background(Theme.sunGradient, in: .capsule)
                                .foregroundStyle(Theme.ink)
                        }
                    }
                    if let note = o.note {
                        Text(note).font(.rounded(13, .medium)).foregroundStyle(.secondary)
                    }
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 0) {
                    Text(o.price).font(.rounded(22, .heavy))
                    Text(o.period.map { "per \($0)" } ?? "once")
                        .font(.rounded(12, .semibold))
                        .foregroundStyle(.secondary)
                }
            }
            .padding(16)
            .background {
                RoundedRectangle(cornerRadius: 22, style: .continuous)
                    .fill(.white.opacity(on ? 0.1 : 0.04))
                    .strokeBorder(on ? Theme.sun : .white.opacity(0.1), lineWidth: on ? 2 : 1)
            }
            .contentShape(.rect)
        }
        .buttonStyle(.plain)
        .accessibilityAddTraits(on ? .isSelected : [])
    }

    private var ctaTitle: String {
        guard let s = selected else { return "Continue" }
        if s.trialDays > 0 { return "Start my free trial" }
        return s.type == .lifetime ? "Unlock forever" : "Continue"
    }

    private var cta: some View {
        VStack(spacing: 8) {
            Button(action: buy) {
                Group {
                    if model.purchases.isLoading {
                        ProgressView().tint(Theme.ink)
                    } else {
                        Text(ctaTitle)
                    }
                }
                .font(.rounded(20, .bold))
                .frame(maxWidth: .infinity)
                .frame(height: 60)
            }
            .buttonStyle(.glassProminent)
            .tint(Theme.sun)
            .disabled(selected == nil || model.purchases.isLoading)
            // The billed amount, right at the button (App Review 3.1.2).
            if let s = selected {
                Text(s.trialDays > 0
                     ? "\(s.trialDays) days free, then \(s.price)/\(s.period ?? "year")"
                     : s.period.map { "\(s.price)/\($0), renews automatically" } ?? "\(s.price), one-time purchase")
                    .font(.rounded(15, .bold))
                if s.trialDays > 0 {
                    Label("No payment due now · Cancel anytime", systemImage: "checkmark.shield.fill")
                        .font(.rounded(13, .semibold))
                        .foregroundStyle(Theme.leaf)
                }
            }
        }
    }

    private func buy() {
        guard let s = selected else { return }
        Haptics.tap()
        Task {
            var ok = false
            if let package = s.package {
                ok = await model.purchases.purchase(package)
            } else {
                #if DEBUG
                model.purchases.debugTogglePlus()
                ok = true
                #endif
            }
            if ok {
                Haptics.success()
                SoundService.shared.play(.levelUp)
                if s.trialDays > 0 {
                    Notifications.scheduleTrialReminder(trialDays: s.trialDays, price: "\(s.price)/\(s.period ?? "year")")
                }
            }
        }
    }

    /// Restore, Terms (EULA) and Privacy: pinned under the button so they're always on screen.
    private var legalLinks: some View {
        HStack(spacing: 16) {
            Button("Restore") {
                Task {
                    await model.purchases.restore()
                    if model.purchases.lastError == nil && !model.isPlus {
                        restoreMessage = "No previous purchase was found for this Apple Account."
                    }
                }
            }
            Link("Terms of Use (EULA)", destination: Config.termsURL)
            Link("Privacy Policy", destination: Config.privacyURL)
        }
        .font(.rounded(13, .semibold))
        .foregroundStyle(.secondary)
    }

    private var footer: some View {
        VStack(spacing: 10) {
            if let s = selected {
                Group {
                    if let period = s.period {
                        Text(s.trialDays > 0
                             ? "Free for \(s.trialDays) days, then \(s.price) per \(period), billed to your Apple Account. "
                             : "\(s.price) per \(period), billed to your Apple Account. ")
                        + Text("Renews automatically unless cancelled at least 24 hours before the end of the period. Manage or cancel in Settings › Apple Account › Subscriptions.")
                    } else {
                        Text("\(s.price) one-time purchase. No subscription.")
                    }
                }
                .multilineTextAlignment(.center)
            }
            #if DEBUG
            Button("Debug: skip paywall") { model.purchases.debugTogglePlus() }
                .font(.caption)
            #endif
        }
        .font(.rounded(12, .medium))
        .foregroundStyle(.secondary)
    }
}
