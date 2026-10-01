import SwiftUI

/// Postcard illustration for a destination (Blender render, or a painted fallback).
struct PostcardArt: View {
    var destination: Destination
    var cornerRadius: CGFloat = 20

    var body: some View {
        // Clear base sizes to the frame the caller gives; the art fills and is clipped to it.
        Color.clear
            .overlay {
                if let img = UIImage(named: "postcard_\(destination.id).jpg") {
                    Image(uiImage: img).resizable().scaledToFill()
                } else {
                    ZStack {
                        LinearGradient(colors: destination.colors.map { Color(hex: $0) }, startPoint: .top, endPoint: .bottom)
                        Image(systemName: destination.symbol)
                            .font(.system(size: 54, weight: .semibold))
                            .foregroundStyle(.white.opacity(0.85))
                    }
                }
            }
            .clipShape(.rect(cornerRadius: cornerRadius))
            .contentShape(.rect(cornerRadius: cornerRadius))
            .accessibilityHidden(true)
    }
}

/// Home screen status: exploring, or back with a postcard.
struct AdventurePill: View {
    @Environment(AppModel.self) private var model
    var onOpenPostcard: () -> Void

    var body: some View {
        if let trip = model.state.trip, let dest = AdventureCatalog.destination(trip.destination) {
            let back = model.tripReturned
            Button {
                if back { onOpenPostcard() }
            } label: {
                HStack(spacing: 8) {
                    Image(systemName: back ? "envelope.open.fill" : "balloon.fill")
                        .foregroundStyle(back ? AnyShapeStyle(Theme.sunGradient) : AnyShapeStyle(Theme.leafGradient))
                        .symbolEffect(.bounce, options: .repeat(.periodic(delay: 2)), isActive: back)
                    if back {
                        Text("\(model.state.companionName) is back with a postcard!")
                    } else {
                        Text("Exploring \(dest.name) · back \(trip.returns.formatted(date: .omitted, time: .shortened))")
                    }
                }
                .font(.rounded(14, .semibold))
                .foregroundStyle(.white)
                .padding(.horizontal, 14)
                .padding(.vertical, 9)
                .contentShape(.capsule)
            }
            .buttonStyle(.plain)
            .glassEffect(back ? .regular.tint(Theme.sun.opacity(0.35)).interactive() : .regular, in: .capsule)
            .accessibilityHint(back ? "Opens the postcard" : "")
        }
    }
}

/// The sprout's postcard: a story from its trip, your reply, and the souvenirs it brought home.
struct PostcardView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss
    let trip: AdventureTrip
    @State private var reply: Int?
    @State private var revealed = false

    var body: some View {
        let pair = AdventureCatalog.discovery(trip.discovery)
        ScrollView {
            if let (dest, disc) = pair {
                VStack(alignment: .leading, spacing: 18) {
                    PostcardArt(destination: dest, cornerRadius: 26)
                        .frame(height: 230)
                        .overlay(alignment: .topTrailing) {
                            // A little postage stamp.
                            VStack(spacing: 2) {
                                Image(systemName: dest.symbol).font(.system(size: 18, weight: .bold))
                                Text(trip.departed.formatted(.dateTime.month(.abbreviated).day()))
                                    .font(.rounded(9, .bold))
                            }
                            .foregroundStyle(Color(hex: dest.colors[0]))
                            .frame(width: 58, height: 66)
                            .background(Theme.cream, in: .rect(cornerRadius: 6))
                            .rotationEffect(.degrees(6))
                            .padding(14)
                            .shadow(radius: 4, y: 2)
                        }
                    VStack(alignment: .leading, spacing: 6) {
                        Text("Postcard from \(dest.name)")
                            .font(.rounded(14, .semibold))
                            .foregroundStyle(.secondary)
                        Text(disc.title)
                            .font(.rounded(28, .heavy))
                    }
                    Text(disc.story)
                        .font(.system(size: 19, weight: .medium, design: .serif))
                        .italic()
                        .lineSpacing(4)
                    Text("With love, \(model.state.companionName) 🌱")
                        .font(.rounded(15, .semibold))
                        .foregroundStyle(.secondary)

                    if let reply {
                        SpeechBubble(text: disc.reactions[reply])
                            .transition(.scale(scale: 0.7, anchor: .leading).combined(with: .opacity))
                        rewards(dest)
                            .transition(.move(edge: .bottom).combined(with: .opacity))
                        Button {
                            model.finishTrip(reply: reply)
                            dismiss()
                        } label: {
                            Text("Add to logbook")
                                .font(.rounded(18, .bold))
                                .frame(maxWidth: .infinity)
                                .frame(height: 54)
                        }
                        .buttonStyle(.glassProminent)
                        .tint(Theme.leaf)
                    } else {
                        Text("Write back:")
                            .font(.rounded(15, .semibold))
                            .foregroundStyle(.secondary)
                        ForEach(disc.replies.indices, id: \.self) { i in
                            Button {
                                Haptics.tap()
                                SoundService.shared.play(.pet)
                                withAnimation(.spring(response: 0.45, dampingFraction: 0.8)) { reply = i }
                            } label: {
                                Text(disc.replies[i])
                                    .font(.rounded(17, .semibold))
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .padding(16)
                                    .contentShape(.rect(cornerRadius: 20))
                            }
                            .buttonStyle(.plain)
                            .glassCard(cornerRadius: 20, interactive: true)
                        }
                    }
                }
                .padding(20)
            }
        }
        .presentationDetents([.large])
        .presentationDragIndicator(.visible)
    }

    private func rewards(_ dest: Destination) -> some View {
        let souvenir = dest.souvenirs.first { $0.id == trip.souvenir }
        return VStack(alignment: .leading, spacing: 12) {
            Text("Brought home")
                .font(.rounded(15, .bold))
                .foregroundStyle(.secondary)
            HStack(spacing: 10) {
                if let souvenir {
                    chip(souvenir.name, symbol: souvenir.symbol, tint: Color(hex: souvenir.tint))
                }
                chip("+\(trip.coins)", symbol: "sun.max.fill", tint: Theme.sun)
            }
            if let hat = trip.hatFound.flatMap(Wardrobe.hat) {
                chip("Rare find: \(hat.name)!", symbol: hat.symbol, tint: Theme.berry)
            }
        }
    }

    private func chip(_ text: String, symbol: String, tint: Color) -> some View {
        Label(text, systemImage: symbol)
            .font(.rounded(15, .bold))
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .background(tint.opacity(0.25), in: .capsule)
            .overlay(Capsule().strokeBorder(tint.opacity(0.6), lineWidth: 1))
    }
}

/// Journal section: every destination and how much of it has been discovered.
struct LogbookSection: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        let found = model.state.discoveredIDs
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Adventure Logbook")
                    .font(.rounded(19, .bold))
                Spacer()
                Text("\(found.count)/\(AdventureCatalog.totalDiscoveries)")
                    .font(.rounded(15, .bold))
                    .foregroundStyle(.secondary)
            }
            LazyVGrid(columns: [GridItem(.flexible(), spacing: 10), GridItem(.flexible(), spacing: 10)], spacing: 10) {
                ForEach(AdventureCatalog.destinations) { dest in
                    let unlocked = model.state.level >= dest.level
                    let n = dest.discoveries.filter { found.contains($0.id) }.count
                    NavigationLink {
                        DestinationDetail(destination: dest)
                    } label: {
                        VStack(alignment: .leading, spacing: 6) {
                            PostcardArt(destination: dest, cornerRadius: 14)
                                .frame(height: 76)
                                .saturation(unlocked ? 1 : 0)
                                .overlay {
                                    if !unlocked {
                                        Label("Level \(dest.level)", systemImage: "lock.fill")
                                            .font(.rounded(12, .bold))
                                            .padding(.horizontal, 10).padding(.vertical, 6)
                                            .background(.ultraThinMaterial, in: .capsule)
                                    }
                                }
                            Text(dest.name).font(.rounded(14, .bold)).lineLimit(1)
                            GlowBar(progress: Double(n) / Double(dest.discoveries.count), height: 6)
                        }
                    }
                    .buttonStyle(.plain)
                    .disabled(!unlocked)
                }
            }
            if !model.state.souvenirs.isEmpty {
                Text("Souvenir shelf")
                    .font(.rounded(15, .bold))
                    .padding(.top, 6)
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 10) {
                        ForEach(AdventureCatalog.destinations.flatMap(\.souvenirs).filter { model.state.souvenirs[$0.id] != nil }) { s in
                            VStack(spacing: 4) {
                                Image(systemName: s.symbol)
                                    .font(.system(size: 22, weight: .semibold))
                                    .foregroundStyle(Color(hex: s.tint))
                                    .frame(width: 50, height: 50)
                                    .background(.white.opacity(0.08), in: .circle)
                                Text(s.name).font(.rounded(10, .semibold)).lineLimit(1).frame(width: 72)
                                if let c = model.state.souvenirs[s.id], c > 1 {
                                    Text("×\(c)").font(.rounded(10, .bold)).foregroundStyle(.secondary)
                                }
                            }
                        }
                    }
                }
            }
        }
        .padding(18)
        .glassCard(cornerRadius: 28)
    }
}

struct DestinationDetail: View {
    @Environment(AppModel.self) private var model
    let destination: Destination

    var body: some View {
        let found = model.state.discoveredIDs
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                PostcardArt(destination: destination, cornerRadius: 24)
                    .frame(height: 200)
                Text(destination.blurb)
                    .font(.rounded(16, .medium))
                    .foregroundStyle(.secondary)
                ForEach(destination.discoveries) { d in
                    let entry = model.state.logbook.first { $0.discovery == d.id }
                    VStack(alignment: .leading, spacing: 6) {
                        Text(entry == nil ? "???" : d.title)
                            .font(.rounded(17, .bold))
                        if let entry {
                            Text(d.story)
                                .font(.system(size: 15, design: .serif))
                                .italic()
                            Text("You wrote back: “\(d.replies[entry.reply])”")
                                .font(.rounded(13, .semibold))
                                .foregroundStyle(.secondary)
                        } else {
                            Text("Not discovered yet. Keep exploring!")
                                .font(.rounded(14, .medium))
                                .foregroundStyle(.tertiary)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(16)
                    .glassCard(cornerRadius: 20)
                    .opacity(found.contains(d.id) ? 1 : 0.7)
                }
            }
            .padding(16)
        }
        .navigationTitle(destination.name)
    }
}

/// Journal card for the seasonal event.
struct FestivalCard: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        let n = model.state.festivalChests
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "leaf.fill").foregroundStyle(.orange)
                Text(HarvestFestival.name).font(.rounded(19, .bold))
                Spacer()
                Text("October").font(.rounded(13, .semibold)).foregroundStyle(.secondary)
            }
            Text("Every morning you win this month opens a festival chest.")
                .font(.rounded(14, .medium))
                .foregroundStyle(.secondary)
            HStack(spacing: 0) {
                ForEach(HarvestFestival.milestones, id: \.self) { m in
                    VStack(spacing: 4) {
                        ZStack {
                            Circle().fill(n >= m ? AnyShapeStyle(LinearGradient(colors: [.orange, .red], startPoint: .top, endPoint: .bottom)) : AnyShapeStyle(.white.opacity(0.08)))
                            Image(systemName: icon(for: m)).font(.system(size: 15, weight: .bold))
                                .foregroundStyle(n >= m ? .white : .secondary)
                        }
                        .frame(width: 40, height: 40)
                        Text("Day \(m)").font(.rounded(10, .semibold)).foregroundStyle(.secondary)
                    }
                    .frame(maxWidth: .infinity)
                }
            }
        }
        .padding(18)
        .glassCard(cornerRadius: 28, tint: .orange.opacity(0.15))
    }

    private func icon(for m: Int) -> String {
        switch HarvestFestival.reward(forChest: m) {
        case .decor: "house.fill"
        case .hat: "crown.fill"
        case .coins: "sun.max.fill"
        }
    }
}

/// Plan a vacation: pick a destination and its stay, pay with coins.
struct TravelView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 14) {
                    status
                    ForEach(AdventureCatalog.destinations) { dest in
                        if let info = VacationCatalog.info(for: dest.id) {
                            destinationCard(dest, info)
                        }
                    }
                    Text("Vacations happen on days off (days with no alarm). \(model.state.companionName) leaves in the morning and flies home in the evening with a postcard.")
                        .font(.rounded(12, .medium))
                        .foregroundStyle(.secondary)
                        .padding(.horizontal, 4)
                }
                .padding(16)
            }
            .navigationTitle("Plan a vacation")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Close", systemImage: "xmark") { dismiss() }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    CoinLabel(amount: model.state.coins, size: 15)
                }
            }
        }
    }

    @ViewBuilder
    private var status: some View {
        if let trip = model.state.trip, let dest = AdventureCatalog.destination(trip.destination) {
            Label("\(model.state.companionName) is on vacation at \(dest.name)", systemImage: "balloon.fill")
                .font(.rounded(15, .semibold))
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(14)
                .glassCard(cornerRadius: 20, tint: Theme.leaf.opacity(0.25))
        } else if let booked = model.state.bookedTrip, let dest = AdventureCatalog.destination(booked.destination) {
            Label("Booked: \(dest.name) on \(booked.day.formatted(.dateTime.weekday(.wide)))", systemImage: "calendar.badge.checkmark")
                .font(.rounded(15, .semibold))
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(14)
                .glassCard(cornerRadius: 20, tint: Theme.sun.opacity(0.25))
        } else if let day = model.nextDayOff() {
            Label(Calendar.current.isDateInToday(day) ? "Today is a day off: he can leave right away!" : "Next day off: \(day.formatted(.dateTime.weekday(.wide)))",
                  systemImage: "sun.max.fill")
                .font(.rounded(15, .semibold))
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(14)
                .glassCard(cornerRadius: 20)
        } else {
            Label("Every day has an alarm. Turn one day off in Alarms to make time for a vacation.", systemImage: "calendar.badge.exclamationmark")
                .font(.rounded(14, .semibold))
                .padding(14)
                .glassCard(cornerRadius: 20)
        }
    }

    private func destinationCard(_ dest: Destination, _ info: VacationInfo) -> some View {
        let locked = model.state.level < dest.level
        let found = dest.discoveries.filter { model.state.discoveredIDs.contains($0.id) }.count
        return VStack(alignment: .leading, spacing: 10) {
            PostcardArt(destination: dest, cornerRadius: 18)
                .frame(height: 130)
                .saturation(locked ? 0 : 1)
                .overlay(alignment: .topLeading) {
                    Text(dest.name)
                        .font(.rounded(18, .heavy))
                        .foregroundStyle(.white)
                        .shadow(radius: 4)
                        .padding(12)
                }
            HStack(alignment: .center, spacing: 12) {
                VStack(alignment: .leading, spacing: 3) {
                    Label(info.stay, systemImage: "bed.double.fill")
                        .font(.rounded(15, .bold))
                    Text("\(found)/\(dest.discoveries.count) stories found · \(info.activities.dropFirst().joined(separator: ", ").lowercased())")
                        .font(.rounded(12, .medium))
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }
                Spacer()
                Button {
                    if model.bookVacation(dest) { dismiss() }
                } label: {
                    Group {
                        if locked {
                            Label("Lv \(dest.level)", systemImage: "lock.fill")
                        } else {
                            HStack(spacing: 4) {
                                Text("Book")
                                CoinLabel(amount: info.price, size: 13)
                            }
                            .fixedSize()
                        }
                    }
                    .font(.rounded(14, .bold))
                    .padding(.horizontal, 4)
                    .frame(height: 36)
                }
                .buttonStyle(.glassProminent)
                .tint(locked ? .gray : Theme.leaf)
                .disabled(locked || !model.canBookVacation)
            }
        }
        .padding(14)
        .glassCard(cornerRadius: 24)
    }
}
