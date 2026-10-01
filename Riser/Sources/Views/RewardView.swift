import SwiftUI

struct RewardView: View {
    @Environment(AppModel.self) private var model
    let reward: WakeReward

    @State private var step = 0
    @State private var barProgress: Double = 0
    @State private var shownXP = 0
    @State private var shownSun = 0
    @State private var level = 1
    @State private var confetti = 0

    var body: some View {
        let sky = model.env.sky
        ZStack {
            WorldView(sky: sky, built: model.state.built, stage: model.state.sproutStage, lastBuilt: nil,
                      petTick: 0, celebrateTick: confetti, buildMarkers: [], highlightedSlot: nil, interactive: false, hat: model.state.equippedHat)
                .ignoresSafeArea()
            LinearGradient(colors: [.black.opacity(0.2), .clear, .black.opacity(0.6)], startPoint: .top, endPoint: .bottom)
                .ignoresSafeArea()

            VStack(spacing: 18) {
                Spacer(minLength: 20)
                VStack(spacing: 6) {
                    Text(reward.isPractice ? "Bonus round!" : headline(sky))
                        .font(.system(size: 40, weight: .heavy, design: .rounded))
                        .multilineTextAlignment(.center)
                    Text(subline)
                        .font(.rounded(16, .semibold))
                        .opacity(0.9)
                        .multilineTextAlignment(.center)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .worldText()
                .scaleEffect(step >= 1 ? 1 : 0.7)
                .opacity(step >= 1 ? 1 : 0)

                Spacer()

                VStack(spacing: 14) {
                    if let shift = reward.shift {
                        HStack {
                            Label("Today's shift", systemImage: "leaf.fill")
                                .font(.rounded(15, .heavy))
                                .foregroundStyle(Theme.leafLight)
                            Spacer()
                            Text("\(reward.mission.goalText(reward.amount)) · \(reward.newStreak)🔥")
                                .font(.rounded(13, .semibold))
                                .opacity(0.8)
                        }
                        .opacity(step >= 2 ? 1 : 0)
                        if shift.harvest.isEmpty {
                            rewardRow(shift.watered > 0 ? "Watered \(shift.watered) crop\(shift.watered == 1 ? "" : "s")" : "Nothing planted yet",
                                      value: "", symbol: "drop.fill", show: step >= 2)
                        }
                        ForEach(shift.harvest, id: \.crop) { line in
                            let crop = FarmCatalog.crop(line.crop)
                            rewardRow("\(crop?.emoji ?? "") \(line.count) \(crop.map { line.count > 1 ? $0.plural : $0.name } ?? line.crop) sold",
                                      value: "+\(line.coins)", symbol: "basket.fill", show: step >= 3)
                        }
                        rewardRow("Daily wage", value: "+\(shift.wage)", symbol: "banknote.fill", show: step >= 3)
                        if shift.moodMultiplier != 1 {
                            rewardRow(shift.moodMultiplier > 1 ? "Happy worker bonus" : "Sad & sluggish",
                                      value: "×\(String(format: "%.1f", shift.moodMultiplier))",
                                      symbol: shift.moodMultiplier > 1 ? "heart.fill" : "heart.slash.fill", show: step >= 4)
                        }
                    } else {
                        rewardRow(reward.isPractice ? "Extra round" : "Woke up", value: "+\(reward.baseXP) XP",
                                  symbol: reward.isPractice ? "sparkles" : "sunrise.fill", show: step >= 2)
                        rewardRow("\(reward.mission.goalText(reward.amount))", value: "+\(reward.effortXP) XP", symbol: reward.mission.symbol, show: step >= 3)
                    }
                    Divider().overlay(.white.opacity(0.3))
                    HStack {
                        LevelBadge(level: level, progress: barProgress, size: 46)
                        VStack(alignment: .leading, spacing: 6) {
                            HStack {
                                Text("Level \(level)")
                                    .font(.rounded(17, .bold))
                                    .contentTransition(.numericText(value: Double(level)))
                                Spacer()
                                Text("+\(shownXP) XP")
                                    .font(.rounded(17, .heavy))
                                    .monospacedDigit()
                                    .foregroundStyle(Theme.leafLight)
                                    .contentTransition(.numericText(value: Double(shownXP)))
                            }
                            GlowBar(progress: barProgress)
                        }
                    }
                    HStack {
                        Text(reward.shift == nil ? "Coins earned" : "Shift pay")
                            .font(.rounded(16, .semibold))
                        Spacer()
                        CoinLabel(amount: shownSun, size: 20)
                        if reward.bonusCoins > 0 {
                            Text("Riser+ bonus")
                                .font(.rounded(11, .bold))
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(Theme.sunGradient, in: .capsule)
                                .foregroundStyle(Theme.ink)
                        }
                    }
                }
                .padding(20)
                .foregroundStyle(.white)
                .glassCard(cornerRadius: 32)

                if step >= 5 {
                    VStack(spacing: 10) {
                        ForEach(banners, id: \.title) { b in
                            RewardBanner(symbol: b.symbol, title: b.title, subtitle: b.subtitle, tint: b.tint)
                        }
                    }
                    .transition(.scale(scale: 0.7).combined(with: .opacity))
                }

                if let chest = reward.festivalChest, let r = reward.festivalReward, step >= 5 {
                    FestivalChestBanner(chest: chest, reward: r)
                        .transition(.scale(scale: 0.6).combined(with: .opacity))
                }

                if reward.leveledUp && step >= 6 {
                    LevelUpBanner(level: reward.newLevel, stage: SproutStage(level: reward.newLevel),
                                  grew: SproutStage(level: reward.newLevel) > SproutStage(level: reward.previousLevel))
                        .transition(.scale(scale: 0.5).combined(with: .opacity))
                }

                Button {
                    Haptics.tap()
                    // Nobody chose? The sprout picks its own adventure.
                    if reward.canAdventure && model.canStartAdventure, let first = model.adventureOptions().first {
                        model.startAdventure(to: first, morningXP: reward.totalXP)
                    }
                    model.reward = nil
                } label: {
                    Text("Back to the island")
                        .font(.rounded(19, .bold))
                        .frame(maxWidth: .infinity)
                        .frame(height: 58)
                }
                .buttonStyle(.glassProminent)
                .tint(Theme.leaf)
                .opacity(step >= 5 ? 1 : 0)
                .padding(.bottom, 8)
            }
            .padding(.horizontal, 20)
        }
        .task { await play() }
    }

    private struct Banner { var symbol: String; var title: String; var subtitle: String; var tint: Color }

    private var banners: [Banner] {
        var b: [Banner] = []
        let name = model.state.companionName
        if reward.cameHome {
            b.append(Banner(symbol: "cross.case.fill", title: "\(name) is out of bed!", subtitle: "You nursed him back to health. He's easing back into work today.", tint: Theme.leaf))
        }
        if let r = reward.promotedTo {
            let rank = Career.ranks[r]
            b.append(Banner(symbol: "arrow.up.circle.fill", title: "Promoted: \(rank.title) \(rank.emoji)", subtitle: "Wage is now \(rank.wage) coins a shift", tint: .yellow))
        }
        if reward.recoveryShift {
            b.append(Banner(symbol: "bandage.fill", title: "Recovery shift", subtitle: "\(name) worked through a cold at reduced pay, and feels better now", tint: .orange))
        }
        if let p = reward.perfectWeekBonus {
            b.append(Banner(symbol: "calendar.badge.checkmark", title: "Perfect week!", subtitle: "Every alarm morning won. +\(p) coins", tint: Theme.sun))
        }
        for id in reward.achievements {
            if let a = AchievementCatalog.all.first(where: { $0.id == id }) {
                b.append(Banner(symbol: a.symbol, title: "Achievement: \(a.title)", subtitle: "\(a.detail) · +\(a.reward) coins", tint: .yellow))
            }
        }
        if reward.debtPaid > 0 {
            b.append(Banner(symbol: "banknote.fill", title: "\(reward.debtPaid) coins went to your debt",
                            subtitle: model.state.debt > 0 ? "\(model.state.debt) still owed" : "Debt cleared!", tint: .orange))
        }
        return b
    }

    private func headline(_ sky: SkyState) -> String {
        let hour = Calendar.current.component(.hour, from: sky.date)
        if hour < 5 { return "Up before the sun!" }
        if hour < 12 { return "Good morning!" }
        return "You're up!"
    }

    private var subline: String {
        let m = reward.seconds / 60, s = reward.seconds % 60
        let time = m > 0 ? "\(m)m \(s)s" : "\(s)s"
        return reward.isPractice ? "Extra practice makes \(model.state.companionName) proud" : "Mission done in \(time). \(model.state.companionName) is so proud of you."
    }

    private func rewardRow(_ title: String, value: String, symbol: String, show: Bool) -> some View {
        HStack(spacing: 12) {
            Image(systemName: symbol)
                .font(.system(size: 17, weight: .semibold))
                .foregroundStyle(Theme.sunGradient)
                .frame(width: 30)
            Text(title).font(.rounded(16, .semibold))
            Spacer()
            Text(value).font(.rounded(16, .bold)).monospacedDigit()
        }
        .opacity(show ? 1 : 0)
        .offset(x: show ? 0 : 30)
    }

    private func play() async {
        level = reward.previousLevel
        barProgress = reward.previousProgress
        let spring = Animation.spring(response: 0.45, dampingFraction: 0.75)
        for s in 1...5 {
            try? await Task.sleep(for: .milliseconds(s == 1 ? 250 : 380))
            withAnimation(spring) { step = s }
            if s >= 2 { SoundService.shared.play(.tap, volume: 0.5, rate: 1 + Float(s) * 0.08); Haptics.tap() }
        }
        // Count up XP and fill the bar (through level-ups).
        let steps = 24
        for i in 1...steps {
            try? await Task.sleep(for: .milliseconds(35))
            withAnimation(.linear(duration: 0.035)) { shownXP = reward.totalXP * i / steps }
        }
        if reward.leveledUp {
            withAnimation(.easeIn(duration: 0.5)) { barProgress = 1 }
            try? await Task.sleep(for: .milliseconds(550))
            level = reward.newLevel
            barProgress = 0
            SoundService.shared.play(.levelUp)
            Haptics.success()
            confetti += 1
            withAnimation(.spring(response: 0.5, dampingFraction: 0.6)) { step = 6 }
        }
        withAnimation(.easeOut(duration: 0.8)) { barProgress = reward.newProgress }
        let totalSun = reward.coins + reward.bonusCoins
        for i in 1...max(1, min(totalSun, 20)) {
            try? await Task.sleep(for: .milliseconds(45))
            withAnimation(.snappy) { shownSun = totalSun * i / max(1, min(totalSun, 20)) }
            if i % 3 == 0 { SoundService.shared.play(.coin, volume: 0.45, rate: 1 + Float(i) * 0.02) }
        }
        if !reward.leveledUp { confetti += 1 }
    }
}

struct RewardBanner: View {
    var symbol: String
    var title: String
    var subtitle: String
    var tint: Color

    var body: some View {
        HStack(spacing: 14) {
            Image(systemName: symbol)
                .font(.system(size: 24, weight: .bold))
                .foregroundStyle(tint)
                .frame(width: 32)
            VStack(alignment: .leading, spacing: 2) {
                Text(title).font(.rounded(17, .heavy))
                Text(subtitle).font(.rounded(13, .semibold)).opacity(0.85)
            }
            Spacer()
        }
        .foregroundStyle(.white)
        .padding(14)
        .glassCard(cornerRadius: 22, tint: tint.opacity(0.25))
    }
}

struct FestivalChestBanner: View {
    var chest: Int
    var reward: HarvestFestival.Reward

    var body: some View {
        HStack(spacing: 14) {
            Image(systemName: "shippingbox.fill")
                .font(.system(size: 26, weight: .bold))
                .foregroundStyle(LinearGradient(colors: [.orange, .red], startPoint: .top, endPoint: .bottom))
                .symbolEffect(.bounce, options: .repeat(2))
            VStack(alignment: .leading, spacing: 2) {
                Text("Harvest chest #\(chest)")
                    .font(.rounded(18, .heavy))
                Text(text)
                    .font(.rounded(14, .semibold))
                    .opacity(0.85)
            }
            Spacer()
        }
        .foregroundStyle(.white)
        .padding(16)
        .glassCard(cornerRadius: 24, tint: .orange.opacity(0.3))
    }

    private var text: String {
        switch reward {
        case .decor(let id): "Unlocked: \(BuildCatalog.item(id)?.name ?? id). Place it from Build!"
        case .hat(let id): "New hat: \(Wardrobe.hat(id)?.name ?? id)!"
        case .coins(let n): "+\(n) coins"
        }
    }
}

struct LevelUpBanner: View {
    var level: Int
    var stage: SproutStage
    var grew: Bool

    var body: some View {
        HStack(spacing: 14) {
            Image(systemName: grew ? "leaf.fill" : "star.fill")
                .font(.system(size: 28, weight: .bold))
                .foregroundStyle(Theme.leafGradient)
                .symbolEffect(.bounce, options: .repeat(3))
            VStack(alignment: .leading, spacing: 2) {
                Text("Level \(level)!")
                    .font(.rounded(20, .heavy))
                Text(grew ? "Your sprout grew: \(stage.title)" : "New things to build are unlocking")
                    .font(.rounded(14, .semibold))
                    .opacity(0.85)
            }
            Spacer()
        }
        .foregroundStyle(.white)
        .padding(16)
        .glassCard(cornerRadius: 24, tint: Theme.leaf.opacity(0.35))
    }
}
