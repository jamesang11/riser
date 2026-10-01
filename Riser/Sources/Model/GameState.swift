import Foundation

/// One completed (or escaped) morning.
struct WakeRecord: Codable, Hashable, Identifiable, Sendable {
    var id: UUID = UUID()
    var date: Date
    var mission: MissionKind
    var amount: Int
    var secondsToComplete: Int
    var xp: Int
    var coins: Int
    var escaped: Bool = false
    var isPractice: Bool = false

    init(date: Date, mission: MissionKind, amount: Int, secondsToComplete: Int, xp: Int, coins: Int, isPractice: Bool = false) {
        self.date = date
        self.mission = mission
        self.amount = amount
        self.secondsToComplete = secondsToComplete
        self.xp = xp
        self.coins = coins
        self.isPractice = isPractice
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = (try? c.decode(UUID.self, forKey: .id)) ?? UUID()
        date = try c.decode(Date.self, forKey: .date)
        mission = (try? c.decode(MissionKind.self, forKey: .mission)) ?? .pushups
        amount = (try? c.decode(Int.self, forKey: .amount)) ?? 0
        secondsToComplete = (try? c.decode(Int.self, forKey: .secondsToComplete)) ?? 0
        xp = (try? c.decode(Int.self, forKey: .xp)) ?? 0
        coins = (try? c.decode(Int.self, forKey: .coins)) ?? 0
        escaped = (try? c.decode(Bool.self, forKey: .escaped)) ?? false
        isPractice = (try? c.decode(Bool.self, forKey: .isPractice)) ?? false
    }

    /// A real, won alarm morning (not a practice run or an escape).
    var isWin: Bool { !escaped && !isPractice }
}

/// The sprout's current trip.
struct AdventureTrip: Codable, Hashable, Sendable, Identifiable {
    var id: Date { departed }
    var destination: String
    var discovery: String
    var souvenir: String
    var hatFound: String?
    var coins: Int
    var departed: Date
    var returns: Date
}

struct LogEntry: Codable, Hashable, Sendable {
    var discovery: String
    var date: Date
    var reply: Int
}

/// Everything the player owns and has achieved. Persisted as JSON.
struct GameState: Codable, Sendable {
    var companionName: String = "Sprig"
    var hasOnboarded: Bool = false
    var xp: Int = 0
    var coins: Int = 60
    var streak: Int = 0
    var bestStreak: Int = 0
    var lastWakeDay: Date? = nil
    var built: [String] = ["tent"]
    var history: [WakeRecord] = []
    var alarms: [AlarmItem] = []
    var escapeProof: Bool = false
    /// Island music is off until the player turns it on (renamed so older saves start quiet too).
    var islandMusicOn: Bool = false
    var ambienceOn: Bool = true
    var sfxOn: Bool = true
    var streakFreezes: Int = 0
    var lastFreezeGrant: Date? = nil
    // Adventures
    var trip: AdventureTrip? = nil
    var bookedTrip: BookedTrip? = nil
    /// Set when a morning is won: the sprout may head out today.
    var canAdventureDay: Date? = nil
    var lastAdventureDay: Date? = nil
    var logbook: [LogEntry] = []
    var souvenirs: [String: Int] = [:]
    // Wardrobe
    var ownedHats: [String] = []
    var equippedHat: String? = nil
    // Events
    var festivalChests: Int = 0
    var lastFestivalDay: Date? = nil
    var unlockedDecor: [String] = []
    // Farm & companion needs
    var plots: [PlotState] = Array(repeating: PlotState(), count: FarmCatalog.maxPlots)
    var hunger: Int = 80
    var mood: Int = 70
    var lastNeedsUpdate: Date? = nil
    var lastEvaluatedDay: Date? = nil
    var consecutiveMisses: Int = 0
    var workUntil: Date? = nil
    var lastShift: ShiftReport? = nil
    var cropsHarvested: Int = 0
    var coinsEarned: Int = 0
    var petsToday: Int = 0
    var lastPetDay: Date? = nil
    // Career, consequences, economy
    var careerPoints: Int = 0
    var sick: Bool = false
    var ranAway: Bool = false
    var comebackProgress: Int = 0
    var debt: Int = 0
    var lastUpkeepWeek: Int? = nil
    var mastery: [String: Int] = [:]
    var lastPerfectWeek: Int? = nil
    var letters: [Letter] = []
    // Interior decor
    var ownedFurniture: [String] = []
    var ownedStyles: [String] = []
    /// home ("tent"/"cottage") → slot → furniture id
    var layouts: [String: [String: String]] = [:]
    /// home → surface → style id
    var roomStyles: [String: [String: String]] = [:]
    var claimedAchievements: [String] = []
    /// Alarm days covered by a streak freeze (not counted as misses).
    var frozenDays: [Date] = []
    /// Where the player put each built item (missing = its original spot on the home island).
    var placements: [String: ItemPlacement] = [:]
    /// Expansion islands bought (see IsleCatalog).
    var isles: [Int] = []

    init() {}

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        func v<T: Decodable>(_ k: CodingKeys, _ d: T) -> T { (try? c.decodeIfPresent(T.self, forKey: k)) ?? d }
        companionName = v(.companionName, "Sprig")
        hasOnboarded = v(.hasOnboarded, false)
        xp = v(.xp, 0)
        struct LegacyKey: CodingKey {
            var stringValue: String
            var intValue: Int? { nil }
            init(stringValue: String) { self.stringValue = stringValue }
            init?(intValue: Int) { nil }
        }
        let legacy = try? decoder.container(keyedBy: LegacyKey.self)
        let oldSunbeams = try? legacy?.decodeIfPresent(Int.self, forKey: LegacyKey(stringValue: "sunbeams"))
        coins = (try? c.decodeIfPresent(Int.self, forKey: .coins)) ?? oldSunbeams ?? 60
        streak = v(.streak, 0)
        bestStreak = v(.bestStreak, 0)
        lastWakeDay = v(.lastWakeDay, nil)
        built = v(.built, ["tent"])
        history = v(.history, [])
        alarms = v(.alarms, [])
        escapeProof = v(.escapeProof, false)
        islandMusicOn = v(.islandMusicOn, false)
        ambienceOn = v(.ambienceOn, true)
        sfxOn = v(.sfxOn, true)
        streakFreezes = v(.streakFreezes, 0)
        lastFreezeGrant = v(.lastFreezeGrant, nil)
        trip = v(.trip, nil)
        bookedTrip = v(.bookedTrip, nil)
        canAdventureDay = v(.canAdventureDay, nil)
        lastAdventureDay = v(.lastAdventureDay, nil)
        logbook = v(.logbook, [])
        souvenirs = v(.souvenirs, [:])
        ownedHats = v(.ownedHats, [])
        equippedHat = v(.equippedHat, nil)
        festivalChests = v(.festivalChests, 0)
        lastFestivalDay = v(.lastFestivalDay, nil)
        unlockedDecor = v(.unlockedDecor, [])
        plots = v(.plots, Array(repeating: PlotState(), count: FarmCatalog.startingPlots))
        hunger = v(.hunger, 80)
        mood = v(.mood, 70)
        lastNeedsUpdate = v(.lastNeedsUpdate, nil)
        lastEvaluatedDay = v(.lastEvaluatedDay, nil)
        consecutiveMisses = v(.consecutiveMisses, 0)
        workUntil = v(.workUntil, nil)
        lastShift = v(.lastShift, nil)
        cropsHarvested = v(.cropsHarvested, 0)
        coinsEarned = v(.coinsEarned, 0)
        petsToday = v(.petsToday, 0)
        lastPetDay = v(.lastPetDay, nil)
        careerPoints = v(.careerPoints, 0)
        sick = v(.sick, false)
        ranAway = v(.ranAway, false)
        comebackProgress = v(.comebackProgress, 0)
        debt = v(.debt, 0)
        lastUpkeepWeek = v(.lastUpkeepWeek, nil)
        mastery = v(.mastery, [:])
        lastPerfectWeek = v(.lastPerfectWeek, nil)
        letters = v(.letters, [])
        ownedFurniture = v(.ownedFurniture, [])
        ownedStyles = v(.ownedStyles, [])
        layouts = v(.layouts, [:])
        roomStyles = v(.roomStyles, [:])
        claimedAchievements = v(.claimedAchievements, [])
        frozenDays = v(.frozenDays, [])
        placements = v(.placements, [:])
        isles = v(.isles, [])
    }

    var homeKind: String { built.contains("cottage") ? "cottage" : "tent" }

    var currentDecor: InteriorDecor {
        let home = homeKind
        let styleIDs = InteriorCatalog.surfaces(for: home).map { roomStyles[home]?[$0.rawValue] ?? InteriorCatalog.defaultStyle($0) }
        return InteriorDecor(layout: layouts[home] ?? [:], styles: styleIDs)
    }

    var rank: Int { Career.rank(for: careerPoints) }
    var rankInfo: Career.Rank { Career.ranks[rank] }
    var unreadLetters: [Letter] { letters.filter { !$0.read } }
    /// Neglect level driving the island's gloom: 0 fine … 3 stormy.
    var gloom: Int { ranAway || sick ? 3 : min(consecutiveMisses, 3) }

    var moodTier: MoodTier { MoodTier(mood: mood) }
    var isHungry: Bool { false }

    var discoveredIDs: Set<String> { Set(logbook.map(\.discovery)) }

    // MARK: Levels

    /// XP needed to go from `level` to `level + 1`.
    static func xpToNext(level: Int) -> Int { 100 + (level - 1) * 60 }

    var level: Int { Self.levelInfo(xp: xp).level }
    var levelProgress: Double { Self.levelInfo(xp: xp).progress }
    var xpIntoLevel: Int { Self.levelInfo(xp: xp).into }
    var xpForLevel: Int { Self.xpToNext(level: level) }

    static func levelInfo(xp: Int) -> (level: Int, into: Int, progress: Double) {
        var level = 1
        var remaining = xp
        while remaining >= xpToNext(level: level) {
            remaining -= xpToNext(level: level)
            level += 1
        }
        return (level, remaining, Double(remaining) / Double(xpToNext(level: level)))
    }

    /// Growth stage of the sprout on the companion's head.
    var sproutStage: SproutStage { SproutStage(level: level) }

    var totalWakeUps: Int { history.filter(\.isWin).count }

    /// Start-of-day dates of every won alarm morning.
    var wonDays: Set<Date> { Set(history.filter(\.isWin).map { Calendar.current.startOfDay(for: $0.date) }) }

    func total(of mission: MissionKind) -> Int {
        history.filter { $0.mission == mission && $0.isWin }.reduce(0) { $0 + $1.amount }
    }

    var woke: Bool {
        guard let last = lastWakeDay else { return false }
        return Calendar.current.isDateInToday(last)
    }
}

enum SproutStage: Int, Comparable, Sendable {
    case seedling = 0, sprout, bud, bloom

    init(level: Int) {
        switch level {
        case ..<3: self = .seedling
        case 3..<5: self = .sprout
        case 5..<8: self = .bud
        default: self = .bloom
        }
    }

    static func < (a: Self, b: Self) -> Bool { a.rawValue < b.rawValue }

    var title: String {
        switch self {
        case .seedling: "Seedling"
        case .sprout: "Sprout"
        case .bud: "Budding"
        case .bloom: "In Bloom"
        }
    }
}

/// The result of finishing a mission, shown on the reward screen.
struct WakeReward: Equatable, Sendable {
    var mission: MissionKind
    var amount: Int
    var seconds: Int
    var baseXP: Int
    var effortXP: Int
    var speedXP: Int
    var streakXP: Int
    var coins: Int
    var bonusCoins: Int
    var newStreak: Int
    var previousLevel: Int
    var newLevel: Int
    var previousProgress: Double
    var newProgress: Double
    var isPractice: Bool
    var festivalChest: Int? = nil
    var festivalReward: HarvestFestival.Reward? = nil
    /// The sprout can head out on today's adventure.
    var canAdventure: Bool = false
    var shift: ShiftReport? = nil
    var promotedTo: Int? = nil
    var comeback: Int? = nil
    var cameHome: Bool = false
    var recoveryShift: Bool = false
    var perfectWeekBonus: Int? = nil
    var masteryUp: [String] = []
    var debtPaid: Int = 0
    var achievements: [String] = []

    var totalXP: Int { baseXP + effortXP + speedXP + streakXP }
    var leveledUp: Bool { newLevel > previousLevel }
}
