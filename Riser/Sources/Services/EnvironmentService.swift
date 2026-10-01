import CoreLocation
import Foundation
import Observation
import WeatherKit

/// Location, live weather and the clock that drive the island's sky.
@Observable
@MainActor
final class EnvironmentService: NSObject, CLLocationManagerDelegate {
    private(set) var latitude: Double
    private(set) var longitude: Double
    private(set) var placeName: String?
    private(set) var weather = WeatherNow()
    /// Apple Weather mark + legal link, shown wherever the live weather appears (WeatherKit requirement).
    private(set) var attribution: WeatherAttribution?
    private(set) var now = Date.now
    private(set) var hasLocation = false
    var locationStatus: CLAuthorizationStatus = .notDetermined

    /// Sky Lab overrides (for exploring the day/weather cycle).
    var timeOverride: Date? = nil
    var weatherOverride: WeatherKind? = nil

    private let locationManager = CLLocationManager()
    private var timer: Timer?
    private var lastFetch: Date?

    override init() {
        // Until we have a location, estimate longitude from the time zone so the sun is roughly right.
        let offsetHours = Double(TimeZone.current.secondsFromGMT()) / 3600
        longitude = offsetHours * 15
        latitude = 38
        super.init()
        locationManager.delegate = self
        locationManager.desiredAccuracy = kCLLocationAccuracyReduced
        locationStatus = locationManager.authorizationStatus
        if let saved = UserDefaults.standard.array(forKey: "riser.lastLocation") as? [Double], saved.count == 2 {
            latitude = saved[0]
            longitude = saved[1]
            hasLocation = true
        }
    }

    var effectiveDate: Date { timeOverride ?? now }

    var effectiveWeather: WeatherNow {
        guard let kind = weatherOverride else { return weather }
        var w = weather
        w.kind = kind
        w.cloudCover = kind.overcast
        if kind == .thunder || kind == .rain { w.windKmh = max(w.windKmh, 22) }
        return w
    }

    var sky: SkyState {
        SkyState.compute(date: effectiveDate, lat: latitude, lon: longitude, weather: effectiveWeather)
    }

    func start() {
        timer?.invalidate()
        timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.tick() }
        }
        if locationStatus == .authorizedWhenInUse || locationStatus == .authorizedAlways {
            locationManager.requestLocation()
        }
        Task { await refreshWeather() }
    }

    func requestLocation() {
        switch locationManager.authorizationStatus {
        case .notDetermined: locationManager.requestWhenInUseAuthorization()
        case .authorizedAlways, .authorizedWhenInUse: locationManager.requestLocation()
        default: break
        }
    }

    private func tick() {
        // Publish once a minute: every change re-renders the home screen and re-applies the 3D sky.
        let current = Date.now
        if Int(current.timeIntervalSince1970 / 60) != Int(now.timeIntervalSince1970 / 60) { now = current }
        if let last = lastFetch, now.timeIntervalSince(last) > 20 * 60 {
            Task { await refreshWeather() }
        }
    }

    /// Live weather from Apple WeatherKit, only once we know roughly where the player is.
    func refreshWeather() async {
        guard hasLocation else { return }
        lastFetch = .now
        // Rounded to ~1 km: the sky only needs an approximate position.
        let location = CLLocation(latitude: (latitude * 100).rounded() / 100, longitude: (longitude * 100).rounded() / 100)
        do {
            let current = try await WeatherService.shared.weather(for: location, including: .current)
            weather = WeatherNow(
                kind: WeatherKind(condition: current.condition),
                temperatureC: current.temperature.converted(to: .celsius).value,
                windKmh: current.wind.speed.converted(to: .kilometersPerHour).value,
                cloudCover: current.cloudCover,
                fetchedAt: .now
            )
            if attribution == nil { attribution = try? await WeatherService.shared.attribution }
        } catch {
            // Offline (or WeatherKit unavailable) is fine: the island keeps its last known weather.
        }
    }

    // MARK: CLLocationManagerDelegate

    nonisolated func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        let status = manager.authorizationStatus
        Task { @MainActor in
            self.locationStatus = status
            if status == .authorizedWhenInUse || status == .authorizedAlways {
                self.locationManager.requestLocation()
            }
        }
    }

    nonisolated func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let loc = locations.last else { return }
        Task { @MainActor in
            self.latitude = loc.coordinate.latitude
            self.longitude = loc.coordinate.longitude
            self.hasLocation = true
            UserDefaults.standard.set([self.latitude, self.longitude], forKey: "riser.lastLocation")
            await self.refreshWeather()
            if let place = try? await CLGeocoder().reverseGeocodeLocation(loc).first {
                self.placeName = place.locality ?? place.administrativeArea
            }
        }
    }

    nonisolated func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {}
}
