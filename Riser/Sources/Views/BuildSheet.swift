import SwiftUI

struct BuildSheet: View {
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss
    @Binding var selection: String?
    @Binding var insideView: Bool
    /// Start choosing a spot for a new item, or for moving a built one.
    var onPlace: (String) -> Void = { _ in }
    var onMove: (String) -> Void = { _ in }
    var onVisitIsle: (Int) -> Void = { _ in }

    private var items: [Buildable] {
        BuildCatalog.all.filter { item in
            // Hide the tent once upgraded, and the cottage until the tent is the only home.
            !(item.id == "tent" && model.state.built.contains("cottage")) &&
                (!BuildCatalog.eventItems.contains(item.id) || HarvestFestival.isActive() || model.state.unlockedDecor.contains(item.id))
        }
        .sorted { a, b in
            let ra = rank(model.status(of: a)), rb = rank(model.status(of: b))
            return ra != rb ? ra < rb : a.cost < b.cost
        }
    }

    private func rank(_ s: BuildStatus) -> Int {
        switch s {
        case .available: 0
        case .needsCoins: 1
        case .needsLevel: 2
        case .needsPlus: 3
        case .needsFestival: 4
        case .built: 5
        }
    }

    enum Tab: String, CaseIterable, Identifiable {
        case build = "Build", isles = "Isles", market = "Market", wardrobe = "Hats", home = "Home"
        var id: String { rawValue }
    }
    @State private var tab: Tab = .build

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Picker("Section", selection: $tab) {
                    ForEach(Tab.allCases) { Text($0.rawValue).tag($0) }
                }
                .pickerStyle(.segmented)
                .frame(maxWidth: 330)
                Spacer()
                CoinLabel(amount: model.state.coins, size: 18)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                    .glassEffect(.regular, in: .capsule)
            }
            .padding(.horizontal, 20)
            .padding(.top, 22)
            switch tab {
            case .build: buildTab
            case .isles: IslesTab(onVisit: { id in onVisitIsle(id); dismiss() })
            case .market: MarketTab()
            case .wardrobe: WardrobeTab()
            case .home: HomeDecorTab()
            }
        }
        .animation(.snappy, value: selection)
        .animation(.snappy, value: tab)
        .onChange(of: tab) { _, t in
            // Decorating and furniture shopping happen inside; everything else happens on the island.
            withAnimation(.snappy) { insideView = (t == .home || t == .market) }
        }
        .onDisappear { if tab == .home || tab == .market { insideView = false } }
        #if DEBUG
        .onAppear {
            switch UserDefaults.standard.string(forKey: "demoScreen") {
            case "market": tab = .market
            case "wardrobe": tab = .wardrobe
            case "home": tab = .home
            case "isles": tab = .isles
            default: break
            }
        }
        #endif
        .presentationDetents([.height(390)])
        .presentationBackgroundInteraction(.enabled(upThrough: .height(390)))
        .presentationDragIndicator(.visible)
    }

    @ViewBuilder
    private var buildTab: some View {

            ScrollViewReader { proxy in
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 12) {
                        ForEach(items) { item in
                            BuildCard(item: item, status: model.status(of: item), selected: selection == item.id) {
                                if selection == item.id {
                                    attemptBuild(item)
                                } else {
                                    selection = item.id
                                    Haptics.select()
                                }
                            }
                            .id(item.id)
                        }
                    }
                    .padding(.horizontal, 20)
                    .padding(.vertical, 4)
                }
                .onChange(of: selection) { _, id in
                    if let id { withAnimation { proxy.scrollTo(id, anchor: .center) } }
                }
            }

            if let id = selection, let item = BuildCatalog.item(id) {
                detail(item)
                    .padding(.horizontal, 20)
                    .transition(.move(edge: .bottom).combined(with: .opacity))
            } else {
                Text("Pick something, then drag it anywhere on your island.")
                    .font(.rounded(14, .medium))
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, 20)
            }
            Spacer(minLength: 0)
    }

    @ViewBuilder
    private func detail(_ item: Buildable) -> some View {
        let status = model.status(of: item)
        HStack(alignment: .center, spacing: 14) {
            VStack(alignment: .leading, spacing: 4) {
                Text(item.name).font(.rounded(19, .bold))
                Text(item.blurb).font(.rounded(14, .medium)).foregroundStyle(.secondary)
            }
            Spacer()
            if status == .built && BuildCatalog.isMovable(item.id) {
                Button {
                    onMove(item.id)
                    dismiss()
                } label: {
                    Label("Move", systemImage: "arrow.up.and.down.and.arrow.left.and.right")
                        .font(.rounded(15, .bold))
                        .padding(.horizontal, 6)
                        .frame(height: 40)
                }
                .buttonStyle(.glassProminent)
                .tint(Theme.sun)
            } else {
            Button {
                attemptBuild(item)
            } label: {
                Group {
                    switch status {
                    case .built: Label("Built", systemImage: "checkmark")
                    case .available: Label(item.cost == 0 ? "Place" : "Build · \(item.cost)", systemImage: "hammer.fill")
                    case .needsCoins(let n): Label("Need \(n) more", systemImage: "sun.max")
                    case .needsLevel(let l): Label("Level \(l)", systemImage: "lock.fill")
                    case .needsPlus: Label("Riser+", systemImage: "sparkles")
                    case .needsFestival: Label("Festival", systemImage: "leaf.fill")
                    }
                }
                .font(.rounded(15, .bold))
                .padding(.horizontal, 6)
                .frame(height: 40)
            }
            .buttonStyle(.glassProminent)
            .tint(status == .available ? Theme.sun : status == .needsPlus ? Theme.berry : .gray)
            .disabled(status == .built)
            }
        }
    }

    private func attemptBuild(_ item: Buildable) {
        // Anything that can go anywhere: pick the spot first, pay on "Build here".
        if model.status(of: item) == .available && BuildCatalog.isMovable(item.id) && !model.inDebt {
            onPlace(item.id)
            dismiss()
            return
        }
        if model.build(item) {
            selection = nil
            Task {
                try? await Task.sleep(for: .seconds(1.6))
                if model.state.built.count > 3 { dismiss() }
            }
        }
    }
}

/// Buy more floating islands, each joined to home by a rope bridge.
struct IslesTab: View {
    @Environment(AppModel.self) private var model
    var onVisit: (Int) -> Void

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 12) {
                ForEach(IsleCatalog.all) { isle in
                    card(isle)
                }
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 4)
        }
        Spacer(minLength: 0)
    }

    private func card(_ isle: Isle) -> some View {
        let status = model.status(of: isle)
        let count = model.state.built.filter { model.placement(of: $0).island == isle.id }.count
        return VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: isle.symbol)
                    .font(.system(size: 22, weight: .bold))
                    .foregroundStyle(Theme.leafGradient)
                Spacer()
                switch status {
                case .owned: Label("Yours", systemImage: "checkmark.circle.fill").foregroundStyle(Theme.leafLight)
                case .needsLevel(let l): Label("Lv \(l)", systemImage: "lock.fill").foregroundStyle(.secondary)
                default: CoinLabel(amount: isle.price, size: 14)
                }
            }
            .font(.rounded(13, .bold))
            Text(isle.name).font(.rounded(18, .heavy))
            Text(status == .owned ? "\(count) thing\(count == 1 ? "" : "s") built here" : isle.blurb)
                .font(.rounded(13, .medium))
                .foregroundStyle(.secondary)
                .lineLimit(3)
                .fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 0)
            Button {
                if status == .owned {
                    onVisit(isle.id)
                } else if model.buyIsle(isle) {
                    onVisit(isle.id)
                }
            } label: {
                Group {
                    switch status {
                    case .owned: Label("Visit", systemImage: "arrow.right")
                    case .available: Label("Buy · \(isle.price)", systemImage: "hammer.fill")
                    case .needsCoins(let n): Label("Need \(n) more", systemImage: "dollarsign.circle")
                    case .needsLevel(let l): Label("Level \(l)", systemImage: "lock.fill")
                    }
                }
                .font(.rounded(15, .bold))
                .frame(maxWidth: .infinity)
                .frame(height: 40)
            }
            .buttonStyle(.glassProminent)
            .tint(status == .available || status == .owned ? Theme.sun : .gray)
            .disabled(!(status == .available || status == .owned))
        }
        .padding(16)
        .frame(width: 250, height: 230)
        .background(.white.opacity(0.07), in: .rect(cornerRadius: 24))
        .accessibilityElement(children: .contain)
    }
}

struct BuildCard: View {
    var item: Buildable
    var status: BuildStatus
    var selected: Bool
    var action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(spacing: 6) {
                ZStack(alignment: .topTrailing) {
                    Group {
                        if let img = Thumbnailer.image(for: item.model) {
                            Image(uiImage: img).resizable().scaledToFit()
                        } else {
                            Image(systemName: item.symbol)
                                .font(.system(size: 36, weight: .semibold))
                                .foregroundStyle(Theme.sunGradient)
                        }
                    }
                    .frame(width: 96, height: 96)
                    .saturation(status == .needsLevel(0) || isLocked ? 0.2 : 1)
                    .opacity(isLocked ? 0.6 : 1)

                    if item.premium {
                        Image(systemName: "sparkles")
                            .font(.system(size: 11, weight: .bold))
                            .padding(5)
                            .background(Theme.berry, in: .circle)
                            .foregroundStyle(.white)
                    }
                }
                Text(item.name)
                    .font(.rounded(13, .bold))
                    .lineLimit(1)
                    .minimumScaleFactor(0.8)
                footer
                    .font(.rounded(12, .semibold))
            }
            .frame(width: 118, height: 162)
            .background {
                RoundedRectangle(cornerRadius: 24, style: .continuous)
                    .fill(selected ? AnyShapeStyle(Theme.sun.opacity(0.28)) : AnyShapeStyle(.white.opacity(0.07)))
                    .strokeBorder(selected ? Theme.sunLight : .clear, lineWidth: 2)
            }
            .scaleEffect(selected ? 1.04 : 1)
        }
        .buttonStyle(.plain)
        .accessibilityLabel("\(item.name). \(accessibilityStatus)")
    }

    private var isLocked: Bool {
        switch status {
        case .needsLevel, .needsPlus, .needsFestival: true
        default: false
        }
    }

    @ViewBuilder
    private var footer: some View {
        switch status {
        case .built:
            Label("Built", systemImage: "checkmark.circle.fill").foregroundStyle(Theme.leafLight)
        case .available, .needsCoins:
            CoinLabel(amount: item.cost, size: 13)
                .foregroundStyle(status == .available ? .primary : .secondary)
        case .needsLevel(let l):
            Label("Lv \(l)", systemImage: "lock.fill").foregroundStyle(.secondary)
        case .needsPlus:
            Text("Riser+").foregroundStyle(Theme.berry)
        case .needsFestival:
            Label("Festival", systemImage: "leaf.fill").foregroundStyle(.orange)
        }
    }

    private var accessibilityStatus: String {
        switch status {
        case .built: "Built"
        case .available: "Costs \(item.cost) coins"
        case .needsCoins(let n): "Needs \(n) more coins"
        case .needsLevel(let l): "Unlocks at level \(l)"
        case .needsPlus: "Part of Riser plus"
        case .needsFestival: "Earned from Harvest Festival chests"
        }
    }
}


/// Today's hat market: new stock every midnight.
struct MarketTab: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        let stock = Wardrobe.market(on: model.env.now, plus: model.isPlus)
        let furniture = InteriorCatalog.market(on: model.env.now, plus: model.isPlus)
        VStack(alignment: .leading, spacing: 10) {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 12) {
                    ForEach(furniture) { item in
                        let owned = model.state.ownedFurniture.contains(item.id)
                        Button {
                            if !owned { _ = model.buyFurniture(item) }
                        } label: {
                            FurnitureCard(item: item, footer: owned ? "Owned" : (item.premium && !model.isPlus ? "Riser+" : "For your home"),
                                          price: owned ? nil : item.price, selected: false)
                        }
                        .buttonStyle(.plain)
                    }
                    ForEach(stock) { hat in
                        let owned = model.state.ownedHats.contains(hat.id)
                        Button {
                            if !owned { _ = model.buyHat(hat) }
                        } label: {
                            HatCard(hat: hat, footer: owned ? "Owned" : (hat.premium && !model.isPlus ? "Riser+" : nil),
                                    price: owned ? nil : hat.price, dim: false)
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.horizontal, 20)
            }
        }
    }
}

/// Everything the sprout can wear. Tap to put it on.
struct WardrobeTab: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 12) {
                Button { model.equip(nil) } label: {
                    VStack(spacing: 8) {
                        Image(systemName: "circle.slash")
                            .font(.system(size: 34, weight: .medium))
                            .frame(width: 96, height: 96)
                        Text("No hat").font(.rounded(13, .bold))
                    }
                    .frame(width: 118, height: 162)
                    .background(RoundedRectangle(cornerRadius: 24, style: .continuous)
                        .fill(model.state.equippedHat == nil ? AnyShapeStyle(Theme.sun.opacity(0.28)) : AnyShapeStyle(.white.opacity(0.07))))
                }
                .buttonStyle(.plain)
                ForEach(Wardrobe.hats) { hat in
                    let owned = model.state.ownedHats.contains(hat.id)
                    Button {
                        if owned { model.equip(hat.id) } else { Haptics.warning() }
                    } label: {
                        HatCard(hat: hat, footer: owned ? (model.state.equippedHat == hat.id ? "Wearing" : "Wear") : source(hat),
                                price: nil, dim: !owned, selected: model.state.equippedHat == hat.id)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 20)
        }
    }

    private func source(_ hat: Hat) -> String {
        switch hat.source {
        case .market: "Market"
        case .adventure(let d): "Found in \(AdventureCatalog.destination(d)?.name ?? "the wild")"
        case .festival: "Harvest Festival"
        }
    }
}

struct HatCard: View {
    var hat: Hat
    var footer: String?
    var price: Int?
    var dim: Bool
    var selected: Bool = false

    var body: some View {
        VStack(spacing: 6) {
            Group {
                if let img = Thumbnailer.image(for: hat.model) {
                    Image(uiImage: img).resizable().scaledToFit()
                } else {
                    Image(systemName: hat.symbol)
                        .font(.system(size: 34, weight: .semibold))
                        .foregroundStyle(Theme.sunGradient)
                }
            }
            .frame(width: 96, height: 96)
            .saturation(dim ? 0.1 : 1)
            .opacity(dim ? 0.55 : 1)
            Text(hat.name).font(.rounded(13, .bold)).lineLimit(1).minimumScaleFactor(0.8)
            if let price {
                CoinLabel(amount: price, size: 13)
            }
            if let footer {
                Text(footer).font(.rounded(11, .semibold)).foregroundStyle(.secondary).lineLimit(2)
                    .multilineTextAlignment(.center)
            }
        }
        .padding(.horizontal, 6)
        .frame(width: 118, height: 162)
        .background {
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .fill(selected ? AnyShapeStyle(Theme.sun.opacity(0.28)) : AnyShapeStyle(.white.opacity(0.07)))
                .strokeBorder(selected ? Theme.sunLight : .clear, lineWidth: 2)
        }
        .accessibilityElement(children: .combine)
    }
}


struct FurnitureCard: View {
    var item: FurnitureItem
    var footer: String?
    var price: Int?
    var selected: Bool

    var body: some View {
        VStack(spacing: 6) {
            Group {
                if let img = Thumbnailer.image(for: item.model) {
                    Image(uiImage: img).resizable().scaledToFit()
                } else {
                    Image(systemName: item.symbol)
                        .font(.system(size: 34, weight: .semibold))
                        .foregroundStyle(Theme.sunGradient)
                }
            }
            .frame(width: 96, height: 96)
            Text(item.name).font(.rounded(13, .bold)).lineLimit(1).minimumScaleFactor(0.8)
            if let price { CoinLabel(amount: price, size: 13) }
            if let footer {
                Text(footer).font(.rounded(11, .semibold)).foregroundStyle(.secondary).lineLimit(1)
            }
        }
        .padding(.horizontal, 6)
        .frame(width: 118, height: 162)
        .background {
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .fill(selected ? AnyShapeStyle(Theme.sun.opacity(0.28)) : AnyShapeStyle(.white.opacity(0.07)))
                .strokeBorder(selected ? Theme.sunLight : .clear, lineWidth: 2)
        }
        .accessibilityElement(children: .combine)
    }
}

/// Arrange furniture in the tent/cottage and restyle its walls and floor.
struct HomeDecorTab: View {
    @Environment(AppModel.self) private var model
    @State private var slot: String = InteriorCatalog.floorSlots[0]

    var body: some View {
        let home = model.state.homeKind
        let layout = model.state.layouts[home] ?? [:]
        let kind: FurnitureItem.Kind = InteriorCatalog.wallSlots.contains(slot) ? .wall : .floor
        let owned = InteriorCatalog.furniture.filter { model.state.ownedFurniture.contains($0.id) && $0.kind == kind }
        VStack(alignment: .leading, spacing: 10) {
            // Spots in the room.
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(InteriorCatalog.floorSlots + InteriorCatalog.wallSlots, id: \.self) { s in
                        let filled = layout[s].flatMap(InteriorCatalog.item)
                        Button {
                            slot = s
                            Haptics.select()
                        } label: {
                            Label(filled?.name ?? (InteriorCatalog.wallSlots.contains(s) ? "Wall spot" : "Floor spot"),
                                  systemImage: filled?.symbol ?? (InteriorCatalog.wallSlots.contains(s) ? "square.dashed" : "square.dashed.inset.filled"))
                                .font(.rounded(12, .semibold))
                                .padding(.horizontal, 10)
                                .padding(.vertical, 7)
                                .foregroundStyle(slot == s ? Theme.ink : .primary)
                                .background(slot == s ? AnyShapeStyle(Theme.sunGradient) : AnyShapeStyle(.quaternary), in: .capsule)
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.horizontal, 20)
            }
            // Owned items for the selected spot.
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 10) {
                    Button { model.place(nil, in: slot) } label: {
                        VStack(spacing: 6) {
                            Image(systemName: "circle.slash").font(.system(size: 26))
                            Text("Empty").font(.rounded(12, .bold))
                        }
                        .frame(width: 84, height: 96)
                        .background(.white.opacity(0.07), in: .rect(cornerRadius: 18))
                    }
                    .buttonStyle(.plain)
                    if owned.isEmpty {
                        Text("Buy \(kind == .wall ? "wall decor" : "furniture") in the Market. New pieces arrive every day.")
                            .font(.rounded(13, .medium))
                            .foregroundStyle(.secondary)
                            .frame(width: 220, alignment: .leading)
                    }
                    ForEach(owned) { item in
                        Button { model.place(item.id, in: slot) } label: {
                            VStack(spacing: 4) {
                                Group {
                                    if let img = Thumbnailer.image(for: item.model) {
                                        Image(uiImage: img).resizable().scaledToFit()
                                    } else {
                                        Image(systemName: item.symbol).font(.system(size: 26))
                                    }
                                }
                                .frame(width: 64, height: 64)
                                Text(item.name).font(.rounded(11, .bold)).lineLimit(1).minimumScaleFactor(0.7)
                            }
                            .frame(width: 84, height: 96)
                            .background {
                                RoundedRectangle(cornerRadius: 18)
                                    .fill(layout[slot] == item.id ? AnyShapeStyle(Theme.sun.opacity(0.3)) : AnyShapeStyle(.white.opacity(0.07)))
                            }
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.horizontal, 20)
            }
            // Styles.
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(InteriorCatalog.surfaces(for: home), id: \.self) { surface in
                        ForEach(InteriorCatalog.styles.filter { $0.surface == surface }) { style in
                            let current = (model.state.roomStyles[home]?[surface.rawValue] ?? InteriorCatalog.defaultStyle(surface)) == style.id
                            let owned = style.price == 0 || model.state.ownedStyles.contains(style.id)
                            Button { model.applyStyle(style) } label: {
                                HStack(spacing: 6) {
                                    Circle()
                                        .fill(swatch(style))
                                        .frame(width: 16, height: 16)
                                        .overlay(Circle().strokeBorder(.white.opacity(0.4), lineWidth: 1))
                                    Text(style.name).font(.rounded(12, .semibold))
                                    if !owned { CoinLabel(amount: style.price, size: 11) }
                                }
                                .padding(.horizontal, 10)
                                .padding(.vertical, 7)
                                .background(current ? AnyShapeStyle(Theme.sun.opacity(0.35)) : AnyShapeStyle(.quaternary), in: .capsule)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
                .padding(.horizontal, 20)
            }
        }
    }

    private func swatch(_ style: RoomStyle) -> Color {
        let defaults: [RoomStyle.Surface: UInt32] = [.wall: 0xF3E6CF, .floor: 0xB57F52, .canvas: 0xF2B45A, .groundsheet: 0xC9A66B]
        let hex = style.colors.values.first ?? defaults[style.surface] ?? 0xFFFFFF
        return Color(hex: hex)
    }
}
