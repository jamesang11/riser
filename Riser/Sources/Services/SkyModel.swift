import Foundation
import WeatherKit
import SwiftUI
import simd

/// Astronomy for the island sky: where the sun and moon really are for the player right now.
enum Astronomy {
    private static let rad = Double.pi / 180

    private static func julianDay(_ date: Date) -> Double {
        date.timeIntervalSince1970 / 86400 + 2440587.5
    }

    /// Converts equatorial coordinates to horizon azimuth (from north, clockwise) and elevation, degrees.
    private static func horizon(ra: Double, dec: Double, date: Date, lat: Double, lon: Double) -> (az: Double, el: Double) {
        let n = julianDay(date) - 2451545.0
        let gmst = (18.697374558 + 24.06570982441908 * n).truncatingRemainder(dividingBy: 24)
        let lst = gmst + lon / 15
        let ha = (lst * 15 - ra) * rad
        let latR = lat * rad
        let decR = dec * rad
        let sinEl = sin(latR) * sin(decR) + cos(latR) * cos(decR) * cos(ha)
        let el = asin(max(-1, min(1, sinEl)))
        var az = atan2(-sin(ha), tan(decR) * cos(latR) - sin(latR) * cos(ha)) / rad
        if az < 0 { az += 360 }
        return (az, el / rad)
    }

    private static func equatorial(eclipticLon lambda: Double, eclipticLat beta: Double, n: Double) -> (ra: Double, dec: Double) {
        let eps = (23.439 - 0.0000004 * n) * rad
        let l = lambda * rad
        let b = beta * rad
        let ra = atan2(sin(l) * cos(eps) - tan(b) * sin(eps), cos(l)) / rad
        let dec = asin(sin(b) * cos(eps) + cos(b) * sin(eps) * sin(l)) / rad
        return ((ra + 360).truncatingRemainder(dividingBy: 360), dec)
    }

    static func sun(date: Date, lat: Double, lon: Double) -> (az: Double, el: Double) {
        let n = julianDay(date) - 2451545.0
        let L = (280.460 + 0.9856474 * n).truncatingRemainder(dividingBy: 360)
        let g = ((357.528 + 0.9856003 * n).truncatingRemainder(dividingBy: 360)) * rad
        let lambda = L + 1.915 * sin(g) + 0.020 * sin(2 * g)
        let eq = equatorial(eclipticLon: lambda, eclipticLat: 0, n: n)
        return horizon(ra: eq.ra, dec: eq.dec, date: date, lat: lat, lon: lon)
    }

    static func moon(date: Date, lat: Double, lon: Double) -> (az: Double, el: Double) {
        let n = julianDay(date) - 2451545.0
        let L = 218.316 + 13.176396 * n
        let M = (134.963 + 13.064993 * n) * rad
        let F = (93.272 + 13.229350 * n) * rad
        let lambda = L + 6.289 * sin(M)
        let beta = 5.128 * sin(F)
        let eq = equatorial(eclipticLon: lambda, eclipticLat: beta, n: n)
        return horizon(ra: eq.ra, dec: eq.dec, date: date, lat: lat, lon: lon)
    }

    /// 0 = new moon, 0.5 = full moon, 1 = new again.
    static func moonPhase(date: Date) -> Double {
        let synodic = 29.530588853
        let age = (julianDay(date) - 2451550.1) / synodic
        return age - floor(age)
    }

    static func moonPhaseName(_ phase: Double) -> String {
        switch phase {
        case ..<0.03, 0.97...: "New Moon"
        case ..<0.22: "Waxing Crescent"
        case ..<0.28: "First Quarter"
        case ..<0.47: "Waxing Gibbous"
        case ..<0.53: "Full Moon"
        case ..<0.72: "Waning Gibbous"
        case ..<0.78: "Last Quarter"
        default: "Waning Crescent"
        }
    }
}

enum WeatherKind: String, Codable, CaseIterable, Identifiable, Sendable {
    case clear, partlyCloudy, cloudy, fog, drizzle, rain, snow, thunder

    var id: String { rawValue }

    /// Maps Apple WeatherKit's conditions onto the island's weather looks.
    init(condition: WeatherCondition) {
        switch condition {
        case .clear, .mostlyClear, .hot, .frigid, .breezy, .windy: self = .clear
        case .partlyCloudy, .sunShowers, .sunFlurries: self = .partlyCloudy
        case .cloudy, .mostlyCloudy, .smoky, .haze, .blowingDust: self = .cloudy
        case .foggy: self = .fog
        case .drizzle, .freezingDrizzle: self = .drizzle
        case .rain, .heavyRain, .freezingRain, .sleet, .hail, .wintryMix: self = .rain
        case .snow, .heavySnow, .flurries, .blowingSnow, .blizzard: self = .snow
        case .thunderstorms, .isolatedThunderstorms, .scatteredThunderstorms, .strongStorms, .tropicalStorm, .hurricane: self = .thunder
        @unknown default: self = .clear
        }
    }

    var title: String {
        switch self {
        case .clear: "Clear"
        case .partlyCloudy: "Partly Cloudy"
        case .cloudy: "Cloudy"
        case .fog: "Foggy"
        case .drizzle: "Drizzle"
        case .rain: "Rain"
        case .snow: "Snow"
        case .thunder: "Thunderstorm"
        }
    }

    func symbol(isDay: Bool) -> String {
        switch self {
        case .clear: isDay ? "sun.max.fill" : "moon.stars.fill"
        case .partlyCloudy: isDay ? "cloud.sun.fill" : "cloud.moon.fill"
        case .cloudy: "cloud.fill"
        case .fog: "cloud.fog.fill"
        case .drizzle: "cloud.drizzle.fill"
        case .rain: "cloud.rain.fill"
        case .snow: "cloud.snow.fill"
        case .thunder: "cloud.bolt.rain.fill"
        }
    }

    /// 0...1 how grey the sky gets.
    var overcast: Double {
        switch self {
        case .clear: 0
        case .partlyCloudy: 0.15
        case .cloudy: 0.55
        case .fog: 0.6
        case .drizzle: 0.55
        case .rain: 0.7
        case .snow: 0.55
        case .thunder: 0.85
        }
    }

    var cloudCount: Int {
        switch self {
        case .clear: 3
        case .partlyCloudy: 6
        case .cloudy, .fog: 10
        case .drizzle, .snow: 9
        case .rain: 11
        case .thunder: 12
        }
    }

    var precipitation: Double {
        switch self {
        case .drizzle: 0.35
        case .rain: 1
        case .thunder: 1.3
        case .snow: 0.8
        default: 0
        }
    }
}

struct WeatherNow: Equatable, Sendable {
    var kind: WeatherKind = .clear
    var temperatureC: Double = 18
    var windKmh: Double = 8
    var cloudCover: Double = 0.1
    var fetchedAt: Date? = nil

    var temperatureText: String {
        let m = Measurement(value: temperatureC, unit: UnitTemperature.celsius)
        return m.formatted(.measurement(width: .narrow, usage: .weather, numberFormatStyle: .number.precision(.fractionLength(0))))
    }
}

/// Everything the renderer needs to paint the sky for one moment.
struct SkyState: Equatable {
    var date: Date
    var sunAzimuth: Double
    var sunElevation: Double
    var moonAzimuth: Double
    var moonElevation: Double
    var moonPhase: Double
    var weather: WeatherNow
    var southernHemisphere: Bool

    var isDay: Bool { sunElevation > -4 }
    /// 0 at night, 1 in full day, smooth through twilight.
    var daylight: Double { smoothstep(-10, 8, sunElevation) }
    /// Peaks at sunrise/sunset.
    var goldenHour: Double {
        let e = sunElevation
        return max(0, 1 - abs(e - 2) / 12)
    }

    static func compute(date: Date, lat: Double, lon: Double, weather: WeatherNow) -> SkyState {
        let sun = Astronomy.sun(date: date, lat: lat, lon: lon)
        let moon = Astronomy.moon(date: date, lat: lat, lon: lon)
        return SkyState(
            date: date,
            sunAzimuth: sun.az, sunElevation: sun.el,
            moonAzimuth: moon.az, moonElevation: moon.el,
            moonPhase: Astronomy.moonPhase(date: date),
            weather: weather,
            southernHemisphere: lat < 0
        )
    }

    // MARK: Palette

    struct Palette {
        var zenith: SIMD3<Double>
        var horizon: SIMD3<Double>
        var below: SIMD3<Double>
        var sunLight: SIMD3<Double>
        var sunIntensity: Double
        var ambient: SIMD3<Double>
        var ambientIntensity: Double
        var cloudTint: SIMD3<Double>
        var fog: SIMD3<Double>
    }

    var palette: Palette {
        // Keyframes along sun elevation (degrees).
        let keys: [(Double, Palette)] = [
            (-18, Palette(zenith: hex(0x070B1F), horizon: hex(0x16204A), below: hex(0x0B1233),
                          sunLight: hex(0x9DB4FF), sunIntensity: 0, ambient: hex(0x5A6CB8), ambientIntensity: 560,
                          cloudTint: hex(0x39427A), fog: hex(0x121A40))),
            (-8, Palette(zenith: hex(0x131C4A), horizon: hex(0x4B3F7E), below: hex(0x1D2458),
                         sunLight: hex(0xB9A6FF), sunIntensity: 60, ambient: hex(0x7470B8), ambientIntensity: 600,
                         cloudTint: hex(0x6B5E9E), fog: hex(0x2E2C63))),
            (-2, Palette(zenith: hex(0x3B4E9C), horizon: hex(0xFF8C7A), below: hex(0x9A6FB0),
                         sunLight: hex(0xFF9A6A), sunIntensity: 420, ambient: hex(0xB08ABF), ambientIntensity: 520,
                         cloudTint: hex(0xF4A3A0), fog: hex(0x9A7AA8))),
            (6, Palette(zenith: hex(0x6A92DE), horizon: hex(0xFFBE8C), below: hex(0xF2B8C6),
                        sunLight: hex(0xFFC27A), sunIntensity: 1300, ambient: hex(0xE6C6C0), ambientIntensity: 720,
                        cloudTint: hex(0xFFE0C2), fog: hex(0xE8C9B8))),
            (18, Palette(zenith: hex(0x4B9BEB), horizon: hex(0xBFE5FF), below: hex(0xA9D4F5),
                         sunLight: hex(0xFFF1D6), sunIntensity: 1900, ambient: hex(0xCFE6FF), ambientIntensity: 820,
                         cloudTint: hex(0xFFFFFF), fog: hex(0xC5E3FA))),
            (60, Palette(zenith: hex(0x3E8FE6), horizon: hex(0xB4E0FF), below: hex(0x9FD0F7),
                         sunLight: hex(0xFFFAEE), sunIntensity: 2100, ambient: hex(0xD6EAFF), ambientIntensity: 860,
                         cloudTint: hex(0xFFFFFF), fog: hex(0xBCDDF8))),
        ]
        let e = sunElevation
        var p = keys.first!.1
        if e >= keys.last!.0 {
            p = keys.last!.1
        } else if e > keys.first!.0 {
            for i in 0..<(keys.count - 1) where e >= keys[i].0 && e < keys[i + 1].0 {
                let t = (e - keys[i].0) / (keys[i + 1].0 - keys[i].0)
                p = mixPalette(keys[i].1, keys[i + 1].1, smooth(t))
            }
        }
        // Weather greys things out.
        let o = weather.kind.overcast
        if o > 0 {
            let lum = { (c: SIMD3<Double>) in SIMD3(repeating: simd_dot(c, SIMD3(0.3, 0.55, 0.15))) }
            let grey = SIMD3<Double>(0.62, 0.66, 0.72)
            func g(_ c: SIMD3<Double>) -> SIMD3<Double> {
                let l = lum(c).x
                return simd_mix(c, grey * (0.25 + l * 0.7), SIMD3(repeating: o))
            }
            p.zenith = g(p.zenith)
            p.horizon = g(p.horizon)
            p.below = g(p.below)
            p.cloudTint = simd_mix(p.cloudTint, lum(p.cloudTint) * SIMD3(0.8, 0.83, 0.9), SIMD3(repeating: o))
            p.fog = g(p.fog)
            p.sunIntensity *= (1 - o * 0.7)
            p.ambientIntensity *= (1 - o * 0.15)
        }
        return p
    }
}

// MARK: - Small math helpers

func hex(_ v: UInt32) -> SIMD3<Double> {
    SIMD3(Double((v >> 16) & 0xFF) / 255, Double((v >> 8) & 0xFF) / 255, Double(v & 0xFF) / 255)
}

func smooth(_ t: Double) -> Double { t * t * (3 - 2 * t) }

func smoothstep(_ a: Double, _ b: Double, _ x: Double) -> Double {
    let t = max(0, min(1, (x - a) / (b - a)))
    return smooth(t)
}

private func mixPalette(_ a: SkyState.Palette, _ b: SkyState.Palette, _ t: Double) -> SkyState.Palette {
    func m(_ x: SIMD3<Double>, _ y: SIMD3<Double>) -> SIMD3<Double> { simd_mix(x, y, SIMD3(repeating: t)) }
    func f(_ x: Double, _ y: Double) -> Double { x + (y - x) * t }
    return SkyState.Palette(
        zenith: m(a.zenith, b.zenith), horizon: m(a.horizon, b.horizon), below: m(a.below, b.below),
        sunLight: m(a.sunLight, b.sunLight), sunIntensity: f(a.sunIntensity, b.sunIntensity),
        ambient: m(a.ambient, b.ambient), ambientIntensity: f(a.ambientIntensity, b.ambientIntensity),
        cloudTint: m(a.cloudTint, b.cloudTint), fog: m(a.fog, b.fog)
    )
}

extension SIMD3 where Scalar == Double {
    var color: Color { Color(red: x, green: y, blue: z) }
    var uiColor: UIColor { UIColor(red: x, green: y, blue: z, alpha: 1) }
}
