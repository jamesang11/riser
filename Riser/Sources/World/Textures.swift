import UIKit
import simd

/// Procedurally drawn textures for the sky and particles.
@MainActor
enum Textures {
    private static var cache: [String: UIImage] = [:]

    private static func cached(_ key: String, _ make: () -> UIImage) -> UIImage {
        if let img = cache[key] { return img }
        let img = make()
        cache[key] = img
        return img
    }

    private static func render(_ size: CGSize, opaque: Bool = false, _ draw: (CGContext) -> Void) -> UIImage {
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        format.opaque = opaque
        return UIGraphicsImageRenderer(size: size, format: format).image { draw($0.cgContext) }
    }

    /// Vertical sky gradient in screen space: zenith at the top, glowing horizon band, softer sky below the island.
    static func skyGradient(_ p: SkyState.Palette, horizonY: CGFloat, sunGlow: SIMD3<Double>, glowAmount: Double) -> UIImage {
        render(CGSize(width: 4, height: 512), opaque: true) { ctx in
            let horizon = simd_mix(p.horizon, sunGlow, SIMD3(repeating: glowAmount * 0.45))
            let colors = [p.zenith, simd_mix(p.zenith, horizon, SIMD3(repeating: 0.55)), horizon,
                          simd_mix(horizon, p.below, SIMD3(repeating: 0.5)), p.below]
                .map { $0.uiColor.cgColor } as CFArray
            let locs: [CGFloat] = [0, horizonY * 0.55, horizonY, min(1, horizonY + 0.25), 1]
            let g = CGGradient(colorsSpace: CGColorSpaceCreateDeviceRGB(), colors: colors, locations: locs)!
            ctx.drawLinearGradient(g, start: .zero, end: CGPoint(x: 0, y: 512), options: [])
        }
    }

    /// Equirectangular environment used for soft image-based lighting.
    static func environment(_ p: SkyState.Palette, ground: SIMD3<Double>) -> UIImage {
        render(CGSize(width: 64, height: 32), opaque: true) { ctx in
            let colors = [p.zenith, p.horizon, simd_mix(p.horizon, ground, SIMD3(repeating: 0.6)), ground]
                .map { $0.uiColor.cgColor } as CFArray
            let g = CGGradient(colorsSpace: CGColorSpaceCreateDeviceRGB(), colors: colors, locations: [0, 0.48, 0.56, 1])!
            ctx.drawLinearGradient(g, start: .zero, end: CGPoint(x: 0, y: 32), options: [])
        }
    }

    static var sun: UIImage {
        cached("sun") {
            render(CGSize(width: 256, height: 256)) { ctx in
                let c = CGPoint(x: 128, y: 128)
                let halo = CGGradient(colorsSpace: CGColorSpaceCreateDeviceRGB(), colors: [
                    UIColor(red: 1, green: 0.93, blue: 0.75, alpha: 0.55).cgColor,
                    UIColor(red: 1, green: 0.8, blue: 0.5, alpha: 0.18).cgColor,
                    UIColor(red: 1, green: 0.7, blue: 0.4, alpha: 0).cgColor,
                ] as CFArray, locations: [0, 0.35, 1])!
                ctx.drawRadialGradient(halo, startCenter: c, startRadius: 0, endCenter: c, endRadius: 128, options: [])
                let core = CGGradient(colorsSpace: CGColorSpaceCreateDeviceRGB(), colors: [
                    UIColor(red: 1, green: 1, blue: 0.97, alpha: 1).cgColor,
                    UIColor(red: 1, green: 0.97, blue: 0.85, alpha: 1).cgColor,
                    UIColor(red: 1, green: 0.9, blue: 0.7, alpha: 0).cgColor,
                ] as CFArray, locations: [0, 0.8, 1])!
                ctx.drawRadialGradient(core, startCenter: c, startRadius: 0, endCenter: c, endRadius: 30, options: [])
            }
        }
    }

    /// The moon drawn with its real current phase (0 new → 0.5 full → 1 new).
    static func moon(phase: Double) -> UIImage {
        let key = "moon\(Int(phase * 48))"
        return cached(key) {
            render(CGSize(width: 256, height: 256)) { ctx in
                let c = CGPoint(x: 128, y: 128)
                let halo = CGGradient(colorsSpace: CGColorSpaceCreateDeviceRGB(), colors: [
                    UIColor(red: 0.85, green: 0.9, blue: 1, alpha: 0.28).cgColor,
                    UIColor(red: 0.7, green: 0.8, blue: 1, alpha: 0).cgColor,
                ] as CFArray, locations: [0, 1])!
                ctx.drawRadialGradient(halo, startCenter: c, startRadius: 20, endCenter: c, endRadius: 128, options: [])
                let r: CGFloat = 34
                let disc = CGRect(x: c.x - r, y: c.y - r, width: 2 * r, height: 2 * r)
                // Dark side (faintly visible earthshine).
                ctx.setFillColor(UIColor(red: 0.3, green: 0.35, blue: 0.55, alpha: 0.35).cgColor)
                ctx.fillEllipse(in: disc)
                // Lit side: half disc + terminator ellipse.
                let illum = phase <= 0.5 ? phase * 2 : (1 - phase) * 2   // 0...1
                let waxing = phase <= 0.5
                let path = CGMutablePath()
                let steps = 64
                for i in 0...steps {
                    let a = -Double.pi / 2 + Double.pi * Double(i) / Double(steps)
                    let x = CGFloat(cos(a)) * r * (waxing ? 1 : -1)
                    let y = CGFloat(sin(a)) * r
                    i == 0 ? path.move(to: CGPoint(x: c.x + x, y: c.y + y)) : path.addLine(to: CGPoint(x: c.x + x, y: c.y + y))
                }
                let k = CGFloat(1 - 2 * illum)   // 1 = new (terminator on lit edge), -1 = full
                for i in 0...steps {
                    let a = Double.pi / 2 - Double.pi * Double(i) / Double(steps)
                    let x = CGFloat(cos(a)) * r * k * (waxing ? 1 : -1)
                    let y = CGFloat(sin(a)) * r
                    path.addLine(to: CGPoint(x: c.x + x, y: c.y + y))
                }
                path.closeSubpath()
                ctx.addPath(path)
                ctx.setFillColor(UIColor(red: 1, green: 0.98, blue: 0.9, alpha: 1).cgColor)
                ctx.fillPath()
                // Craters.
                ctx.setFillColor(UIColor(red: 0.85, green: 0.84, blue: 0.8, alpha: 0.35).cgColor)
                for (dx, dy, cr) in [(-10.0, -8.0, 7.0), (9.0, 10.0, 5.0), (12.0, -12.0, 4.0), (-6.0, 14.0, 3.5)] {
                    ctx.fillEllipse(in: CGRect(x: c.x + dx - cr, y: c.y + dy - cr, width: 2 * cr, height: 2 * cr))
                }
            }
        }
    }

    /// Portrait star field that thins out toward the horizon.
    static var stars: UIImage {
        cached("stars") {
            render(CGSize(width: 600, height: 1300)) { ctx in
                var rng = SeededRandom(seed: 42)
                for _ in 0..<420 {
                    let x = CGFloat(rng.next()) * 600
                    let fy = pow(rng.next(), 1.6)            // denser near the top
                    let y = CGFloat(fy) * 1300 * 0.62
                    let fade = CGFloat(max(0, 1 - fy * 1.1))
                    let big = rng.next() > 0.93
                    let r = CGFloat(big ? 1.4 + rng.next() * 1.2 : 0.5 + rng.next() * 0.8)
                    let a = CGFloat(0.35 + rng.next() * 0.65) * fade
                    let warm = rng.next()
                    ctx.setFillColor(UIColor(red: 1, green: 0.92 + 0.08 * warm, blue: 0.8 + 0.2 * warm, alpha: a).cgColor)
                    ctx.fillEllipse(in: CGRect(x: x - r, y: y - r, width: 2 * r, height: 2 * r))
                    if big {
                        ctx.setFillColor(UIColor(white: 1, alpha: a * 0.18).cgColor)
                        ctx.fillEllipse(in: CGRect(x: x - r * 3, y: y - r * 3, width: r * 6, height: r * 6))
                    }
                }
            }
        }
    }

    static var softDot: UIImage {
        cached("dot") {
            render(CGSize(width: 64, height: 64)) { ctx in
                let g = CGGradient(colorsSpace: CGColorSpaceCreateDeviceRGB(), colors: [
                    UIColor.white.cgColor, UIColor(white: 1, alpha: 0.5).cgColor, UIColor(white: 1, alpha: 0).cgColor,
                ] as CFArray, locations: [0, 0.35, 1])!
                ctx.drawRadialGradient(g, startCenter: CGPoint(x: 32, y: 32), startRadius: 0,
                                       endCenter: CGPoint(x: 32, y: 32), endRadius: 32, options: [])
            }
        }
    }

    static var puff: UIImage {
        cached("puff") {
            render(CGSize(width: 128, height: 128)) { ctx in
                let g = CGGradient(colorsSpace: CGColorSpaceCreateDeviceRGB(), colors: [
                    UIColor(white: 1, alpha: 0.9).cgColor, UIColor(white: 1, alpha: 0.55).cgColor, UIColor(white: 1, alpha: 0).cgColor,
                ] as CFArray, locations: [0, 0.55, 1])!
                ctx.drawRadialGradient(g, startCenter: CGPoint(x: 64, y: 64), startRadius: 0,
                                       endCenter: CGPoint(x: 64, y: 64), endRadius: 64, options: [])
            }
        }
    }

    static var raindrop: UIImage {
        cached("rain") {
            render(CGSize(width: 8, height: 64)) { ctx in
                let g = CGGradient(colorsSpace: CGColorSpaceCreateDeviceRGB(), colors: [
                    UIColor(white: 1, alpha: 0).cgColor, UIColor(white: 1, alpha: 0.9).cgColor,
                ] as CFArray, locations: [0, 1])!
                ctx.addPath(UIBezierPath(roundedRect: CGRect(x: 2, y: 0, width: 4, height: 64), cornerRadius: 2).cgPath)
                ctx.clip()
                ctx.drawLinearGradient(g, start: .zero, end: CGPoint(x: 0, y: 64), options: [])
            }
        }
    }

    static var sparkle: UIImage {
        cached("sparkle") {
            render(CGSize(width: 64, height: 64)) { ctx in
                let c = CGPoint(x: 32, y: 32)
                let p = UIBezierPath()
                p.move(to: CGPoint(x: 32, y: 2))
                p.addQuadCurve(to: CGPoint(x: 62, y: 32), controlPoint: c)
                p.addQuadCurve(to: CGPoint(x: 32, y: 62), controlPoint: c)
                p.addQuadCurve(to: CGPoint(x: 2, y: 32), controlPoint: c)
                p.addQuadCurve(to: CGPoint(x: 32, y: 2), controlPoint: c)
                ctx.addPath(p.cgPath)
                ctx.setFillColor(UIColor.white.cgColor)
                ctx.fillPath()
            }
        }
    }

    static func symbol(_ name: String, color: UIColor, size: CGFloat = 96) -> UIImage {
        cached("sym-\(name)-\(color.description)") {
            let cfg = UIImage.SymbolConfiguration(pointSize: size * 0.7, weight: .bold)
            let img = UIImage(systemName: name, withConfiguration: cfg)?.withTintColor(color, renderingMode: .alwaysOriginal)
            return render(CGSize(width: size, height: size)) { _ in
                guard let img else { return }
                let s = img.size
                img.draw(in: CGRect(x: (size - s.width) / 2, y: (size - s.height) / 2, width: s.width, height: s.height))
            }
        }
    }

    static func emoji(_ e: String, size: CGFloat = 72) -> UIImage {
        cached("emoji-\(e)") {
            render(CGSize(width: size, height: size)) { _ in
                let attrs: [NSAttributedString.Key: Any] = [.font: UIFont.systemFont(ofSize: size * 0.8)]
                let str = e as NSString
                let sz = str.size(withAttributes: attrs)
                str.draw(at: CGPoint(x: (size - sz.width) / 2, y: (size - sz.height) / 2), withAttributes: attrs)
            }
        }
    }

    /// A green cartoon "feeling sick" squiggle.
    static var sickSwirl: UIImage {
        cached("swirl") {
            render(CGSize(width: 128, height: 128)) { ctx in
                let c = CGPoint(x: 64, y: 64)
                let path = CGMutablePath()
                let turns = 2.4
                let steps = 140
                for i in 0...steps {
                    let t = Double(i) / Double(steps)
                    let a = t * turns * 2 * .pi
                    let r = 6 + 48 * t
                    let p = CGPoint(x: c.x + CGFloat(cos(a) * r), y: c.y + CGFloat(sin(a) * r))
                    i == 0 ? path.move(to: p) : path.addLine(to: p)
                }
                ctx.addPath(path)
                ctx.setLineCap(.round)
                ctx.setLineJoin(.round)
                ctx.setStrokeColor(UIColor(red: 0.2, green: 0.45, blue: 0.1, alpha: 0.55).cgColor)
                ctx.setLineWidth(13)
                ctx.strokePath()
                ctx.addPath(path)
                ctx.setStrokeColor(UIColor(red: 0.55, green: 0.9, blue: 0.3, alpha: 1).cgColor)
                ctx.setLineWidth(8)
                ctx.strokePath()
            }
        }
    }

    static var sleepyZ: UIImage {
        cached("zzz") {
            render(CGSize(width: 64, height: 64)) { _ in
                let attrs: [NSAttributedString.Key: Any] = [
                    .font: UIFont.systemFont(ofSize: 44, weight: .heavy).rounded,
                    .foregroundColor: UIColor.white,
                ]
                ("z" as NSString).draw(at: CGPoint(x: 18, y: 2), withAttributes: attrs)
            }
        }
    }
}

struct SeededRandom {
    private var state: UInt64
    init(seed: UInt64) { state = seed &* 6364136223846793005 &+ 1442695040888963407 }
    mutating func next() -> Double {
        state = state &* 6364136223846793005 &+ 1442695040888963407
        return Double((state >> 33) & 0xFFFFFF) / Double(0xFFFFFF)
    }
}

extension UIFont {
    var rounded: UIFont {
        guard let d = fontDescriptor.withDesign(.rounded) else { return self }
        return UIFont(descriptor: d, size: pointSize)
    }
}
