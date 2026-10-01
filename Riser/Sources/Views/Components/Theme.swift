import UIKit
import SwiftUI

enum Theme {
    static let sun = Color(red: 0.98, green: 0.65, blue: 0.26)
    static let sunLight = Color(red: 1.0, green: 0.84, blue: 0.45)
    static let leaf = Color(red: 0.42, green: 0.76, blue: 0.40)
    static let leafLight = Color(red: 0.62, green: 0.86, blue: 0.52)
    static let berry = Color(red: 0.97, green: 0.47, blue: 0.52)
    static let sky = Color(red: 0.36, green: 0.62, blue: 0.93)
    static let night = Color(red: 0.09, green: 0.12, blue: 0.27)
    static let cream = Color(red: 1.0, green: 0.97, blue: 0.9)
    static let ink = Color(red: 0.16, green: 0.14, blue: 0.2)

    static let sunGradient = LinearGradient(colors: [Color(red: 1, green: 0.8, blue: 0.35), sun, Color(red: 0.96, green: 0.45, blue: 0.3)],
                                            startPoint: .topLeading, endPoint: .bottomTrailing)
    static let coinGradient = LinearGradient(colors: [Color(red: 1, green: 0.88, blue: 0.4), Color(red: 0.95, green: 0.68, blue: 0.18)],
                                             startPoint: .top, endPoint: .bottom)
    static let leafGradient = LinearGradient(colors: [leafLight, leaf], startPoint: .top, endPoint: .bottom)
}

extension Font {
    /// SF Rounded that follows the user's Dynamic Type setting (capped so the diorama layout holds).
    static func rounded(_ size: CGFloat, _ weight: Font.Weight = .semibold) -> Font {
        let scaled = UIFontMetrics.default.scaledValue(for: size)
        return .system(size: min(max(scaled, size * 0.9), size * 1.3), weight: weight, design: .rounded)
    }
}

/// The coin currency glyph + amount.
struct CoinLabel: View {
    var amount: Int
    var size: CGFloat = 17

    var body: some View {
        HStack(spacing: 5) {
            Image(systemName: "dollarsign.circle.fill")
                .symbolRenderingMode(.palette)
                .foregroundStyle(Theme.ink.opacity(0.75), Theme.coinGradient)
                .font(.system(size: size * 0.95, weight: .bold))
            Text(amount, format: .number)
                .font(.rounded(size, .bold))
                .monospacedDigit()
                .contentTransition(.numericText(value: Double(amount)))
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(amount) coins")
    }
}

struct StreakLabel: View {
    var streak: Int
    var size: CGFloat = 17

    var body: some View {
        HStack(spacing: 5) {
            Image(systemName: "flame.fill")
                .foregroundStyle(LinearGradient(colors: [.yellow, .orange, .red], startPoint: .top, endPoint: .bottom))
                .font(.system(size: size * 0.95, weight: .bold))
                .symbolEffect(.bounce, value: streak)
            Text(streak, format: .number)
                .font(.rounded(size, .bold))
                .monospacedDigit()
                .contentTransition(.numericText(value: Double(streak)))
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(streak) day streak")
    }
}

/// A circular level badge with progress ring.
struct LevelBadge: View {
    var level: Int
    var progress: Double
    var size: CGFloat = 40

    var body: some View {
        ZStack {
            Circle().stroke(.white.opacity(0.25), lineWidth: 4)
            Circle()
                .trim(from: 0, to: max(0.02, progress))
                .stroke(Theme.leafGradient, style: StrokeStyle(lineWidth: 4, lineCap: .round))
                .rotationEffect(.degrees(-90))
            Text("\(level)")
                .font(.rounded(size * 0.42, .heavy))
                .contentTransition(.numericText(value: Double(level)))
        }
        .frame(width: size, height: size)
        .accessibilityElement()
        .accessibilityLabel("Level \(level), \(Int(progress * 100)) percent to next level")
    }
}

/// A horizontal XP/progress bar with a glowing fill.
struct GlowBar: View {
    var progress: Double
    var gradient: LinearGradient = Theme.leafGradient
    var height: CGFloat = 12

    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                Capsule().fill(.white.opacity(0.18))
                Capsule()
                    .fill(gradient)
                    .frame(width: max(height, geo.size.width * min(1, max(0, progress))))
                    .shadow(color: Theme.leafLight.opacity(0.6), radius: 6)
                    .overlay(alignment: .top) {
                        Capsule().fill(.white.opacity(0.35)).frame(height: height * 0.3).padding(.horizontal, 4).padding(.top, 2)
                    }
            }
        }
        .frame(height: height)
    }
}

extension EnvironmentValues {
    /// Inside full sheets (Journal, Settings…) cards are flat: dozens of live glass layers made scrolling stutter.
    @Entry var flatCards = false
}

private struct CardSurface: ViewModifier {
    @Environment(\.flatCards) private var flat
    var cornerRadius: CGFloat
    var tint: Color?
    var interactive: Bool

    private var glass: Glass {
        var g = Glass.regular
        if let tint { g = g.tint(tint) }
        if interactive { g = g.interactive() }
        return g
    }

    @ViewBuilder
    func body(content: Content) -> some View {
        if flat {
            content.background {
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .fill((tint ?? .white).opacity(tint == nil ? 0.08 : 0.2))
                    .overlay(RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                        .strokeBorder(.white.opacity(0.08), lineWidth: 0.5))
            }
        } else {
            content.glassEffect(glass, in: .rect(cornerRadius: cornerRadius))
        }
    }
}

extension View {
    /// Liquid Glass card surface (a flat card inside full sheets, see `flatCards`).
    func glassCard(cornerRadius: CGFloat = 28, tint: Color? = nil, interactive: Bool = false) -> some View {
        modifier(CardSurface(cornerRadius: cornerRadius, tint: tint, interactive: interactive))
    }

    /// Legible white text over the 3D world.
    func worldText() -> some View {
        foregroundStyle(.white)
            .shadow(color: .black.opacity(0.25), radius: 8, y: 2)
    }
}
