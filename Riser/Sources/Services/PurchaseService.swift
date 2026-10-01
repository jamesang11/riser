import Foundation
import Observation
import RevenueCat

enum Config {
    /// RevenueCat public SDK keys (Project settings › API keys).
    /// Development builds use the Test Store key; App Store builds must use the App Store key ("appl_"):
    /// RevenueCat deliberately crashes release builds configured with a Test Store key.
    #if DEBUG
    static let revenueCatAPIKey = "test_REPLACE_WITH_YOUR_TEST_STORE_KEY"
    #else
    static let revenueCatAPIKey = "appl_REPLACE_WITH_YOUR_APPLE_KEY"
    #endif
    /// Entitlement identifier configured in RevenueCat.
    static let plusEntitlement = "riser_pro"

    /// Public website hosting the privacy policy, terms and support pages (the `site/` folder).
    static let siteBase = "https://withriser.com"
    static let privacyURL = URL(string: "\(siteBase)/privacy.html")!
    static let termsURL = URL(string: "\(siteBase)/terms.html")!
    static let supportURL = URL(string: "\(siteBase)/support.html")!
    /// Apple's standard EULA (our Terms of Use build on it).
    static let appleEULA = URL(string: "https://www.apple.com/legal/internet-services/itunes/dev/stdeula/")!

    static var hasRevenueCatKey: Bool { !revenueCatAPIKey.contains("REPLACE") }
}

/// Riser+ subscription state, powered by RevenueCat.
@Observable
@MainActor
final class PurchaseService: NSObject, PurchasesDelegate {
    /// Seeded from the last known state so Riser+ perks don't flicker off before RevenueCat answers.
    private(set) var isPlus = PurchaseService.initialPlus {
        didSet { UserDefaults.standard.set(isPlus, forKey: "riser.isPlusCache") }
    }
    private static var initialPlus: Bool {
        #if DEBUG
        if UserDefaults.standard.bool(forKey: "demoPlus") { return true }
        #endif
        return UserDefaults.standard.bool(forKey: "riser.isPlusCache")
    }
    private(set) var offering: Offering?
    /// Products whose free trial this Apple ID has already used (Apple allows one per subscription group).
    private(set) var trialUsed: Set<String> = []
    private(set) var isLoading = false
    var lastError: String?

    var isConfigured: Bool { Config.hasRevenueCatKey && Purchases.isConfigured }

    func configure() {
        guard Config.hasRevenueCatKey else { return }
        #if DEBUG
        Purchases.logLevel = .info
        #else
        Purchases.logLevel = .warn
        #endif
        Purchases.configure(withAPIKey: Config.revenueCatAPIKey)
        Purchases.shared.delegate = self
        Task { await refresh() }
    }

    func refresh() async {
        guard isConfigured else { return }
        if let info = try? await Purchases.shared.customerInfo() {
            apply(info)
        }
        if let offerings = try? await Purchases.shared.offerings() {
            offering = offerings.current
        }
        await checkTrialEligibility()
    }

    /// Only promise a free trial the App Store will actually give this Apple ID.
    func checkTrialEligibility() async {
        guard let packages = offering?.availablePackages, !packages.isEmpty else { return }
        let result = await Purchases.shared.checkTrialOrIntroDiscountEligibility(packages: packages)
        trialUsed = Set(result.compactMap { $0.value.status == .ineligible ? $0.key.storeProduct.productIdentifier : nil })
    }

    /// Returns true when the purchase unlocked Riser+.
    func purchase(_ package: Package) async -> Bool {
        isLoading = true
        defer { isLoading = false }
        do {
            let result = try await Purchases.shared.purchase(package: package)
            apply(result.customerInfo)
            return !result.userCancelled && isPlus
        } catch ErrorCode.purchaseCancelledError {
            return false
        } catch {
            lastError = error.localizedDescription
            return false
        }
    }

    func restore() async {
        guard isConfigured else {
            lastError = "The App Store can't be reached right now. Please try again later."
            return
        }
        isLoading = true
        defer { isLoading = false }
        do {
            apply(try await Purchases.shared.restorePurchases())
            if !isPlus { lastError = "No previous Riser+ purchase was found for this Apple Account." }
        } catch {
            lastError = error.localizedDescription
        }
    }

    private func apply(_ info: CustomerInfo) {
        isPlus = info.entitlements[Config.plusEntitlement]?.isActive == true
        #if DEBUG
        // Screen recordings of a subscriber's view (never in App Store builds).
        if UserDefaults.standard.bool(forKey: "demoPlus") { isPlus = true }
        #endif
    }

    nonisolated func purchases(_ purchases: Purchases, receivedUpdated customerInfo: CustomerInfo) {
        Task { @MainActor in self.apply(customerInfo) }
    }

    #if DEBUG
    /// Lets the simulator preview premium content without a store.
    func debugTogglePlus() { isPlus.toggle() }
    #endif
}
