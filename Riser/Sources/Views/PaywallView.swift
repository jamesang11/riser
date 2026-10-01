import RevenueCat
import SwiftUI

struct PaywallView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss
    var reason: String?
    @State private var selected: Package?
    @State private var appeared = false

    private var packages: [Package] {
        guard let offering = model.purchases.offering else { return [] }
        let order: [PackageType] = [.annual, .weekly, .monthly, .lifetime]
        return offering.availablePackages.sorted {
            (order.firstIndex(of: $0.packageType) ?? 9) < (order.firstIndex(of: $1.packageType) ?? 9)
        }
    }

    var body: some View {
        ScrollView {
            VStack(spacing: 0) {
                hero
                VStack(spacing: 22) {
                    VStack(spacing: 8) {
                        Text("Riser+")
                            .font(.system(size: 44, weight: .heavy, design: .rounded))
                            .foregroundStyle(LinearGradient(colors: [Theme.sunLight, Theme.sun, Theme.berry], startPoint: .leading, endPoint: .trailing))
                        Text(reason ?? "Grow a more magical island, every morning.")
                            .font(.rounded(17, .semibold))
                            .foregroundStyle(.secondary)
                            .multilineTextAlignment(.center)
                    }
                    features
                    packageList
                    purchaseButton
                    footer
                }
                .padding(.horizontal, 22)
                .padding(.bottom, 30)
            }
        }
        .scrollBounceBehavior(.basedOnSize)
        .background(Color(red: 0.06, green: 0.07, blue: 0.16).ignoresSafeArea())
        .overlay(alignment: .topTrailing) {
            Button("Close", systemImage: "xmark") { dismiss() }
                .labelStyle(.iconOnly)
                .buttonStyle(.glass)
                .buttonBorderShape(.circle)
                .padding(16)
        }
        .task {
            await model.purchases.refresh()
            selected = packages.first
            withAnimation(.spring(response: 0.6, dampingFraction: 0.8).delay(0.1)) { appeared = true }
        }
        .onChange(of: model.purchases.isPlus) { _, plus in
            if plus {
                Haptics.success()
                SoundService.shared.play(.levelUp)
                dismiss()
            }
        }
        .alert("Something went wrong", isPresented: Binding(get: { model.purchases.lastError != nil }, set: { if !$0 { model.purchases.lastError = nil } })) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(model.purchases.lastError ?? "")
        }
    }

    private var hero: some View {
        ZStack(alignment: .bottom) {
            if let img = UIImage(named: "paywall_hero.jpg") {
                Image(uiImage: img)
                    .resizable()
                    .scaledToFill()
                    .frame(height: 300)
                    .clipped()
                    .scaleEffect(appeared ? 1 : 1.08)
            } else {
                LinearGradient(colors: [Theme.sky, Theme.sun.opacity(0.8)], startPoint: .top, endPoint: .bottom)
                    .frame(height: 300)
            }
            LinearGradient(colors: [.clear, Color(red: 0.06, green: 0.07, blue: 0.16)], startPoint: .center, endPoint: .bottom)
                .frame(height: 300)
        }
        .frame(height: 300)
        .accessibilityHidden(true)
    }

    private var features: some View {
        VStack(alignment: .leading, spacing: 16) {
            feature("tree.fill", Theme.berry, "Premium decor & outfits", "Cherry blossom, windmill, telescope, lanterns, an aquarium, a record player and royal hats")
            feature("dollarsign.circle.fill", Theme.sun, "+50% daily wage", "\(model.state.companionName) earns more coins every shift")
            feature("snowflake", .cyan, "Weekly streak freeze", "Life happens. Your streak survives one missed morning a week")
            feature("alarm.fill", Theme.leaf, "Unlimited alarms + all sounds", "Weekday, weekend, nap alarms and the Meadow sound")
        }
        .padding(20)
        .glassCard(cornerRadius: 28)
        .opacity(appeared ? 1 : 0)
        .offset(y: appeared ? 0 : 20)
    }

    private func feature(_ symbol: String, _ tint: Color, _ title: String, _ detail: String) -> some View {
        HStack(alignment: .top, spacing: 14) {
            Image(systemName: symbol)
                .font(.system(size: 18, weight: .bold))
                .foregroundStyle(tint)
                .frame(width: 30, height: 30)
            VStack(alignment: .leading, spacing: 2) {
                Text(title).font(.rounded(16, .bold))
                Text(detail).font(.rounded(14, .medium)).foregroundStyle(.secondary)
            }
        }
        .accessibilityElement(children: .combine)
    }

    @ViewBuilder
    private var packageList: some View {
        if packages.isEmpty {
            VStack(spacing: 8) {
                if model.purchases.isConfigured {
                    ProgressView()
                    Text("Loading plans…").font(.footnote).foregroundStyle(.secondary)
                } else {
                    Text("Purchases aren't set up in this build yet.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 20)
        } else {
            VStack(spacing: 10) {
                ForEach(packages, id: \.identifier) { package in
                    PackageRow(package: package, selected: selected?.identifier == package.identifier,
                               badge: badge(for: package)) {
                        selected = package
                        Haptics.select()
                    }
                }
            }
        }
    }

    private func badge(for package: Package) -> String? {
        switch package.packageType {
        case .annual:
            // Compare against paying weekly (or monthly) for a whole year.
            let yearly = NSDecimalNumber(decimal: package.storeProduct.price as Decimal).doubleValue
            var alternative: Double?
            if let w = packages.first(where: { $0.packageType == .weekly }) {
                alternative = NSDecimalNumber(decimal: w.storeProduct.price as Decimal).doubleValue * 52
            } else if let m = packages.first(where: { $0.packageType == .monthly }) {
                alternative = NSDecimalNumber(decimal: m.storeProduct.price as Decimal).doubleValue * 12
            }
            if let alternative, alternative > 0 {
                let saving = 1 - yearly / alternative
                if saving > 0.05 { return "Save \(Int((saving * 100).rounded()))%" }
            }
            return "Best value"
        case .lifetime: return "One time"
        default: return nil
        }
    }

    private var purchaseButton: some View {
        Button {
            guard let selected else { return }
            Task { _ = await model.purchases.purchase(selected) }
        } label: {
            Group {
                if model.purchases.isLoading {
                    ProgressView().tint(Theme.ink)
                } else {
                    Text(ctaTitle)
                }
            }
            .font(.rounded(19, .bold))
            .frame(maxWidth: .infinity)
            .frame(height: 58)
        }
        .buttonStyle(.glassProminent)
        .tint(Theme.sun)
        .disabled(selected == nil || model.purchases.isLoading)
    }

    private var ctaTitle: String {
        guard let selected else { return "Continue" }
        if let intro = selected.storeProduct.introductoryDiscount, intro.paymentMode == .freeTrial {
            return "Start \(intro.subscriptionPeriod.durationText) free trial"
        }
        return selected.packageType == .lifetime ? "Unlock forever" : "Continue"
    }

    private var footer: some View {
        VStack(spacing: 10) {
            if let selected, let period = selected.storeProduct.subscriptionPeriod {
                let trial = selected.storeProduct.introductoryDiscount.flatMap { $0.paymentMode == .freeTrial ? $0 : nil }
                    .map { "Free for \($0.subscriptionPeriod.durationText.replacingOccurrences(of: "1-", with: "1 ")), then " } ?? ""
                Text("\(trial)\(selected.storeProduct.localizedPriceString) per \(period.unitText), billed to your Apple Account. Renews automatically unless cancelled at least 24 hours before the period ends. Manage or cancel in Settings › Apple Account › Subscriptions.")
                    .multilineTextAlignment(.center)
            } else if selected?.packageType == .lifetime {
                Text("One-time purchase. No subscription.")
            }
            HStack(spacing: 18) {
                Button("Restore") { Task { await model.purchases.restore() } }
                Link("Terms of Use (EULA)", destination: Config.termsURL)
                Link("Privacy Policy", destination: Config.privacyURL)
            }
            .font(.rounded(13, .semibold))
        }
        .font(.rounded(13, .medium))
        .foregroundStyle(.secondary)
    }
}

struct PackageRow: View {
    var package: Package
    var selected: Bool
    var badge: String?
    var action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 14) {
                Image(systemName: selected ? "checkmark.circle.fill" : "circle")
                    .font(.system(size: 22, weight: .semibold))
                    .foregroundStyle(selected ? Theme.sun : .secondary)
                VStack(alignment: .leading, spacing: 2) {
                    Text(title).font(.rounded(17, .bold))
                    if let sub = subtitle {
                        Text(sub).font(.rounded(13, .medium)).foregroundStyle(.secondary)
                    }
                }
                Spacer()
                if let badge {
                    Text(badge)
                        .font(.rounded(11, .heavy))
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Theme.sunGradient, in: .capsule)
                        .foregroundStyle(Theme.ink)
                }
                Text(package.storeProduct.localizedPriceString)
                    .font(.rounded(17, .bold))
            }
            .padding(16)
            .background {
                RoundedRectangle(cornerRadius: 22, style: .continuous)
                    .fill(.white.opacity(selected ? 0.1 : 0.04))
                    .strokeBorder(selected ? Theme.sun : .white.opacity(0.1), lineWidth: selected ? 2 : 1)
            }
        }
        .buttonStyle(.plain)
        .accessibilityAddTraits(selected ? .isSelected : [])
    }

    private var title: String {
        switch package.packageType {
        case .annual: "Yearly"
        case .weekly: "Weekly"
        case .monthly: "Monthly"
        case .lifetime: "Lifetime"
        default: package.storeProduct.localizedTitle
        }
    }

    private var subtitle: String? {
        if let intro = package.storeProduct.introductoryDiscount, intro.paymentMode == .freeTrial {
            return "\(intro.subscriptionPeriod.durationText) free trial"
        }
        return nil
    }
}

extension SubscriptionPeriod {
    var durationText: String {
        let unitName: String
        switch unit {
        case .day: unitName = value == 7 ? "week" : "day"
        case .week: unitName = "week"
        case .month: unitName = "month"
        case .year: unitName = "year"
        @unknown default: unitName = "period"
        }
        if unit == .day && value == 7 { return "1-week" }
        return "\(value)-\(unitName)"
    }

    var unitText: String {
        switch unit {
        case .day: value == 7 ? "week" : "day"
        case .week: "week"
        case .month: value == 1 ? "month" : "\(value) months"
        case .year: "year"
        @unknown default: "period"
        }
    }
}
