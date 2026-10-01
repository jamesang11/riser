import Foundation
import SwiftUI

/// A place the sprout can fly to after a won morning.
struct Destination: Identifiable, Hashable {
    let id: String
    let name: String
    let blurb: String
    let symbol: String
    let level: Int
    let colors: [UInt32]          // postcard fallback gradient
    let souvenirs: [Souvenir]
    let discoveries: [Discovery]
    /// A hat that can only be found here (rare).
    let exclusiveHat: String?
}

struct Souvenir: Identifiable, Hashable {
    let id: String
    let name: String
    let symbol: String
    let tint: UInt32
}

struct Discovery: Identifiable, Hashable {
    let id: String
    let title: String
    /// Told in the sprout's voice. `{you}` is replaced by nothing personal: the story is addressed to the player.
    let story: String
    let replies: [String]
    let reactions: [String]
}

extension Color {
    init(hex: UInt32) {
        self.init(red: Double((hex >> 16) & 0xFF) / 255, green: Double((hex >> 8) & 0xFF) / 255, blue: Double(hex & 0xFF) / 255)
    }
}

enum AdventureCatalog {
    static let destinations: [Destination] = [
        Destination(
            id: "meadow", name: "Dewdrop Meadow", blurb: "Rolling hills that sparkle at sunrise.", symbol: "sun.horizon.fill",
            level: 1, colors: [0x9FE0A0, 0xFFE3A3],
            souvenirs: [
                .init(id: "dewdrop", name: "Bottled Dewdrop", symbol: "drop.fill", tint: 0x6EC8E6),
                .init(id: "clover", name: "Four-Leaf Clover", symbol: "leaf.fill", tint: 0x6CC265),
                .init(id: "dandelion", name: "Dandelion Wish", symbol: "aqi.medium", tint: 0xFFF3C4),
            ],
            discoveries: [
                .init(id: "meadow1", title: "A Dew Rainbow", story: "Every blade of grass had a dewdrop on it, and when the sun came up the whole meadow turned into a tiny rainbow. I tried to count the colors and lost track at nine.", replies: ["Nine colors?!", "Did you drink one?"], reactions: ["Maybe ten. I'm counting again tomorrow!", "Just one. It tasted like morning."]),
                .init(id: "meadow2", title: "The Sleepy Bumblebee", story: "I found a bumblebee asleep inside a clover flower. I didn't want to wake it, so I hummed very quietly until it buzzed off on its own.", replies: ["You're so gentle", "Bees hum back?"], reactions: ["It waved at me. I think.", "A little! We harmonized."]),
                .init(id: "meadow3", title: "Hill Rolling Contest", story: "Some rabbits challenged me to roll down the biggest hill. I'm very round, so I won. By a lot. They want a rematch.", replies: ["Champion!", "Did you get dizzy?"], reactions: ["Round is my superpower.", "The sky spun for a whole minute."]),
                .init(id: "meadow4", title: "Cloud Shapes", story: "I lay in the grass and watched the clouds. One looked exactly like you doing push-ups this morning. It was very inspiring.", replies: ["Haha, really?", "Was I good at them?"], reactions: ["Even the clouds are proud of you.", "The best cloud push-ups ever."]),
                .init(id: "meadow5", title: "A Wish on the Wind", story: "I blew on a dandelion and made a wish. I can't tell you what it was, but it's about tomorrow morning.", replies: ["Tell me!", "I hope it comes true"], reactions: ["Nope! But you'll see.", "If we wake up together, it will."]),
                .init(id: "meadow6", title: "The Oldest Oak", story: "In the middle of the meadow there's an oak older than anyone remembers. It told me it has watched ten thousand sunrises. I've only watched a few, but they're my favorites.", replies: ["Trees can talk?", "Let's watch more"], reactions: ["Very, very slowly.", "Every single morning."]),
            ],
            exclusiveHat: "flowercrown"
        ),
        Destination(
            id: "woods", name: "Whispering Woods", blurb: "Tall pines, mossy logs and secrets.", symbol: "tree.fill",
            level: 2, colors: [0x4E8C5A, 0xB9D88A],
            souvenirs: [
                .init(id: "pinecone", name: "Perfect Pinecone", symbol: "tree", tint: 0xA9774F),
                .init(id: "feather", name: "Owl Feather", symbol: "leaf", tint: 0xD9C8A9),
                .init(id: "moss", name: "Soft Moss Pillow", symbol: "cloud.fill", tint: 0x7FB069),
            ],
            discoveries: [
                .init(id: "woods1", title: "Whispers in the Pines", story: "The trees really do whisper here. Mostly about the weather. One of them said you're doing great, but that might have been the wind.", replies: ["Aw, the trees!", "It was the wind"], reactions: ["I choose to believe the trees.", "The wind is nice too."]),
                .init(id: "woods2", title: "Owl Office Hours", story: "An owl who is usually asleep during the day made an exception to chat with me. We agreed that mornings are underrated.", replies: ["An owl said that?", "Mornings rule"], reactions: ["She's trying something new. Like us!", "Morning people unite!"]),
                .init(id: "woods3", title: "The Mushroom Ring", story: "I found a circle of tiny mushrooms. I stepped inside and felt about 3% more magical. I stepped out and it wore off.", replies: ["Only 3%?", "Go back in!"], reactions: ["Magic is expensive.", "Tomorrow. I promise."]),
                .init(id: "woods4", title: "Deer Crossing", story: "A family of deer crossed right in front of me. The smallest one had spots like a sprinkled cookie. We stared at each other for a very long, very polite time.", replies: ["So polite", "Cookie deer!"], reactions: ["Forest manners are important.", "I miss cookie deer already."]),
                .init(id: "woods5", title: "Sunbeam Hopscotch", story: "Sunlight came through the leaves in long golden stripes, and I hopped from one to the next without touching the shade. Personal record: forty hops.", replies: ["Forty!", "Show me sometime"], reactions: ["Next goal: fifty.", "On our island. After breakfast."]),
                .init(id: "woods6", title: "The Lost Explorer's Hat", story: "Hanging on a branch was a tiny explorer's hat with a note: 'For whoever wakes up early enough to find this.' That's us!", replies: ["We earned it!", "Try it on!"], reactions: ["Early risers get the best hats.", "It fits perfectly."]),
            ],
            exclusiveHat: "explorer"
        ),
        Destination(
            id: "beach", name: "Pebble Beach", blurb: "Turquoise waves and smooth stones.", symbol: "water.waves",
            level: 3, colors: [0x5CC8E0, 0xF6E3B4],
            souvenirs: [
                .init(id: "shell", name: "Spiral Shell", symbol: "hurricane", tint: 0xF7B7C9),
                .init(id: "seaglass", name: "Sea Glass", symbol: "diamond.fill", tint: 0x7FD1C7),
                .init(id: "pebble", name: "Skipping Stone", symbol: "circle.fill", tint: 0xB8B2A7),
            ],
            discoveries: [
                .init(id: "beach1", title: "Seven Skips", story: "I skipped a pebble seven times! A crab clapped. At least, I think it was clapping. Crabs are hard to read.", replies: ["Seven!!", "Crab fan club"], reactions: ["New island record.", "My first fan!"]),
                .init(id: "beach2", title: "Sandcastle Kingdom", story: "I built a sandcastle with a moat, a tower and a little flag made of seaweed. The tide took it, but the tide was nice about it.", replies: ["Sad but beautiful", "Build another!"], reactions: ["Everything's a sunrise and a sunset.", "Tomorrow: two towers."]),
                .init(id: "beach3", title: "Message in a Bottle", story: "A bottle washed up with a note inside. It said: 'Whoever finds this, drink some water today.' Good advice from a stranger.", replies: ["Wise bottle", "Did you?"], reactions: ["The ocean looks out for us.", "Three sips. You too!"]),
                .init(id: "beach4", title: "Tidepool Town", story: "There's a whole town in the tidepools: starfish mayors, snail postmen, tiny fish commuting to work. Everybody gets up with the tide.", replies: ["Snail postmen!", "Early risers too"], reactions: ["Mail takes a while there.", "The tide is their alarm clock."]),
                .init(id: "beach5", title: "Dolphin Hello", story: "Far out in the water a dolphin jumped three times. I jumped three times back. We had a whole conversation.", replies: ["What did it say?", "You speak dolphin?"], reactions: ["'Good morning!' Obviously.", "Only the greetings."]),
                .init(id: "beach6", title: "The Warmest Rock", story: "I found the warmest rock on the whole beach and sat on it until my bottom was toasty. 10/10 would sit again.", replies: ["Toasty!", "Rating: accurate"], reactions: ["Like a hug from the sun.", "I'm a rock critic now."]),
            ],
            exclusiveHat: "straw"
        ),
        Destination(
            id: "mushroom", name: "Mushroom Hollow", blurb: "Giant toadstools and glowing spores.", symbol: "sparkles",
            level: 4, colors: [0xC45A5A, 0xF3D9B1],
            souvenirs: [
                .init(id: "spore", name: "Glow Spore", symbol: "sparkle", tint: 0xD6F28A),
                .init(id: "cap", name: "Tiny Toadstool", symbol: "umbrella.fill", tint: 0xE0674F),
                .init(id: "acorn", name: "Painted Acorn", symbol: "oval.portrait.fill", tint: 0xB07A4A),
            ],
            discoveries: [
                .init(id: "mush1", title: "Umbrella Mushrooms", story: "It started drizzling, so I stood under a mushroom as big as our cottage. A beetle and a frog joined me. We waited it out together and told jokes.", replies: ["Best joke?", "Cozy shelter"], reactions: ["Why did the mushroom party? He's a fungi.", "Rain is nicer with friends."]),
                .init(id: "mush2", title: "Spore Lights", story: "When I hopped, the mushrooms puffed out little glowing spores. I hopped a LOT. It looked like fireworks made of sleep.", replies: ["Fireworks!", "Sleep fireworks?"], reactions: ["Very quiet fireworks.", "Like dreams, but outside."]),
                .init(id: "mush3", title: "The Snail Race", story: "I was the judge of a snail race. It lasted all afternoon. Everyone won, because nobody finished.", replies: ["Fair judging", "Who was fastest?"], reactions: ["Everyone gets a medal.", "Gary. By a whisker."]),
                .init(id: "mush4", title: "Moss Bed Nap", story: "I found the softest moss bed in the world and I did NOT nap on it, because I'm an early riser now. I just rested my eyes. Briefly.", replies: ["Proud of you", "Suspicious…"], reactions: ["Discipline!", "Okay, maybe five minutes."]),
                .init(id: "mush5", title: "Fairy Door", story: "At the bottom of a mushroom stem there was a teeny door. I knocked. Someone inside said 'too early!' Even fairies need an alarm clock.", replies: ["Lend them ours!", "Ha, lazy fairies"], reactions: ["I'll suggest push-ups.", "Everyone starts somewhere."]),
                .init(id: "mush6", title: "The Hollow Choir", story: "At dusk the frogs sang in harmony, low notes from the pond, high notes from the leaves. I hummed along and they let me join the chorus.", replies: ["You're in a choir!", "Sing it for me"], reactions: ["Soprano, obviously.", "Hmm hm hmmm ♪"]),
            ],
            exclusiveHat: "frog"
        ),
        Destination(
            id: "harbor", name: "Cloud Harbor", blurb: "Sky docks where balloons come to rest.", symbol: "cloud.sun.fill",
            level: 5, colors: [0x8EC5F4, 0xFFFFFF],
            souvenirs: [
                .init(id: "ticket", name: "Sky Ferry Ticket", symbol: "ticket.fill", tint: 0xF2B45A),
                .init(id: "cloudpuff", name: "Jar of Cloud", symbol: "cloud.fill", tint: 0xE8F2FF),
                .init(id: "compass", name: "Wind Compass", symbol: "safari.fill", tint: 0x4FA3A5),
            ],
            discoveries: [
                .init(id: "harbor1", title: "Balloon Traffic", story: "There were so many balloons at the harbor that there was a traffic jam. In the sky! A seagull directed traffic with its wings.", replies: ["Sky traffic!", "Good seagull"], reactions: ["We honked. Politely.", "Employee of the month."]),
                .init(id: "harbor2", title: "The Cloud Baker", story: "A baker there makes bread from clouds. It's very fluffy and weighs nothing. I ate four loaves and I'm still hungry.", replies: ["Cloud bread!", "Save me one"], reactions: ["Tastes like vanilla air.", "It floated away. Sorry!"]),
                .init(id: "harbor3", title: "Lighthouse of the Sky", story: "There's a lighthouse that guides balloons home through fog. The keeper wakes up at 4am every day. She says the quiet is worth it.", replies: ["4am!", "Worth it?"], reactions: ["Goals.", "She says the stars wave goodbye."]),
                .init(id: "harbor4", title: "Island Spotting", story: "From the harbor's telescope I could see our island! It looked so small and cozy. I waved. Did you see me?", replies: ["I saw you!", "Wave again!"], reactions: ["I knew it!", "*waving intensifies*"]),
                .init(id: "harbor5", title: "Paper Boat Regatta", story: "Everyone raced paper boats on a river of clouds. Mine was folded out of a to-do list. It was very motivated.", replies: ["Did it win?", "Productive boat"], reactions: ["Second! Checked every box.", "It completed its goals."]),
                .init(id: "harbor6", title: "The Wind Map", story: "An old sailor showed me a map of all the winds in the world. There's one called the Morning Breeze that only blows for people who get up early.", replies: ["That's us!", "Let's catch it"], reactions: ["Every morning!", "Balloon's ready."]),
            ],
            exclusiveHat: "party"
        ),
        Destination(
            id: "caves", name: "Crystal Caves", blurb: "Glittering tunnels of pastel crystal.", symbol: "diamond.fill",
            level: 6, colors: [0x7A6BD1, 0x9FE3F0],
            souvenirs: [
                .init(id: "crystal", name: "Pocket Crystal", symbol: "diamond.fill", tint: 0xB9A6FF),
                .init(id: "geode", name: "Tiny Geode", symbol: "circle.hexagongrid.fill", tint: 0x9FE3F0),
                .init(id: "echo", name: "Bottled Echo", symbol: "waveform", tint: 0xF7B7C9),
            ],
            discoveries: [
                .init(id: "caves1", title: "The Echo Chamber", story: "I said 'good morning' in the big cave and it said 'good morning' back eleven times. That's the most good mornings I've ever gotten.", replies: ["Eleven!", "Good morning!"], reactions: ["Twelve with yours!", "Good morning! good morning! good mor…"]),
                .init(id: "caves2", title: "Crystal Music", story: "When water drips on the crystals they ring like little bells. I stayed for a whole song. It was about patience, I think.", replies: ["Beautiful", "Hum it"], reactions: ["It was. Drip by drip.", "Ting… ting… tiiing."]),
                .init(id: "caves3", title: "Glowworm Galaxy", story: "The ceiling was covered in glowworms, like a sky full of stars underground. I lay down and made new constellations. One is shaped like our cottage.", replies: ["A cottage star!", "Name one after me"], reactions: ["Very cozy constellation.", "Done. It's the brightest."]),
                .init(id: "caves4", title: "The Crystal Gardener", story: "A mole takes care of the crystals like a garden. She says they grow one millimeter per year, so you have to be very consistent.", replies: ["Consistency!", "Like our streak"], reactions: ["Small every day, big over time.", "Exactly like our streak."]),
                .init(id: "caves5", title: "Rainbow Pool", story: "Light bounced through the crystals into a pool and made rainbow ripples. I dipped one foot in. It was cold. I had to hop around for a while.", replies: ["Brr!", "Worth it?"], reactions: ["Very brr.", "Always worth it."]),
                .init(id: "caves6", title: "The Wishing Crystal", story: "Deep in the cave there's a crystal that shows you your future. Mine showed me waking up tomorrow feeling proud. It's never wrong.", replies: ["Love that", "Show me mine"], reactions: ["See you at sunrise!", "It showed you smiling."]),
            ],
            exclusiveHat: "headphones"
        ),
        Destination(
            id: "peaks", name: "Aurora Peaks", blurb: "Snowy summits under dancing lights.", symbol: "mountain.2.fill",
            level: 8, colors: [0x2E4A8A, 0x7FF0C8],
            souvenirs: [
                .init(id: "snowflake", name: "Unmelting Snowflake", symbol: "snowflake", tint: 0xD6ECFF),
                .init(id: "aurora", name: "Ribbon of Aurora", symbol: "wind", tint: 0x7FF0C8),
                .init(id: "summit", name: "Summit Flag", symbol: "flag.fill", tint: 0xE0674F),
            ],
            discoveries: [
                .init(id: "peaks1", title: "Summit Sunrise", story: "I climbed all the way to the top before dawn. Watching the sun rise over the clouds from up there was the best thing I've ever seen. I thought of you.", replies: ["That's beautiful", "You climbed?!"], reactions: ["It was our sunrise.", "Tiny legs, big mountain."]),
                .init(id: "peaks2", title: "Dancing Lights", story: "At night the sky did a dance in green and pink. The mountain goats say it's the sky celebrating everyone who kept their promises that day.", replies: ["We kept ours!", "Sky party!"], reactions: ["The green part was for us.", "Invitation-only."]),
                .init(id: "peaks3", title: "Snow Sprout", story: "I built a snow version of me! Same round shape, same leaf. It's still up there, guarding the mountain.", replies: ["Snow twin!", "What's its name?"], reactions: ["It's very chill.", "Frosty Sprig, obviously."]),
                .init(id: "peaks4", title: "The Hot Spring", story: "Halfway down there's a steaming hot spring. The snow monkeys let me sit in it. We didn't talk. We didn't need to.", replies: ["Relaxing", "Snow monkeys!"], reactions: ["Zen level: maximum.", "Very good listeners."]),
                .init(id: "peaks5", title: "Avalanche of Snowballs", story: "A little snowball rolled down, then got bigger, then bigger. By the bottom it was huge! Just like how small mornings add up.", replies: ["Deep, Sprig", "How big?!"], reactions: ["I've been thinking a lot.", "Cottage-sized."]),
                .init(id: "peaks6", title: "The Star Keeper", story: "At the highest peak an old yak keeps a lantern lit so the stars can find their way back each night. He says the sun does the same for us each morning.", replies: ["Lovely", "Thank you, sun"], reactions: ["The sky takes care of us.", "The sun says you're welcome."]),
            ],
            exclusiveHat: "beanie"
        ),
        Destination(
            id: "moon", name: "Moon Garden", blurb: "Silver flowers that bloom only at night.", symbol: "moon.stars.fill",
            level: 10, colors: [0x1B2450, 0xC9C3FF],
            souvenirs: [
                .init(id: "moonflower", name: "Moonflower", symbol: "camera.macro", tint: 0xE6E0FF),
                .init(id: "stardust", name: "Pinch of Stardust", symbol: "sparkles", tint: 0xFFD58A),
                .init(id: "moonstone", name: "Moonstone", symbol: "moon.fill", tint: 0xC9C3FF),
            ],
            discoveries: [
                .init(id: "moon1", title: "Night Bloom", story: "The moonflowers open only when it's dark and close at sunrise, right when I wake up. So we take turns being awake. I think that's lovely.", replies: ["Taking turns", "So lovely"], reactions: ["Night shift and day shift.", "I'm glad I'm day shift."]),
                .init(id: "moon2", title: "The Sleepy Gardener", story: "The gardener here sleeps all day and gardens all night. When I told her about our mornings she said, 'Different flowers, different hours.' Wise.", replies: ["Very wise", "We're morning flowers"], reactions: ["Everyone has their hour.", "Sunflowers, basically."]),
                .init(id: "moon3", title: "Reflection Pond", story: "The pond reflected the moon so clearly I couldn't tell which one was real. I waved at both, just to be safe.", replies: ["Smart", "Which was real?"], reactions: ["Always wave at both moons.", "Both, maybe."]),
                .init(id: "moon4", title: "Firefly Lanterns", story: "Fireflies carried little lanterns and showed me around the garden. They're closing early this week because it's the harvest season.", replies: ["Tiny tour guides", "Harvest season?"], reactions: ["Five-star tour.", "Pumpkins everywhere soon!"]),
                .init(id: "moon5", title: "A Wish for You", story: "There's a well where you can wish for someone else. I wished that you'd feel as proud of yourself as I am of you.", replies: ["Sprig…", "I do!"], reactions: ["I mean it.", "Then it worked!"]),
                .init(id: "moon6", title: "The Moon's Secret", story: "The moon told me a secret: it's been rising and setting every single day for four billion years, and it still thinks every night is worth showing up for.", replies: ["Consistency king", "Worth showing up"], reactions: ["The ultimate streak.", "Like our mornings."]),
            ],
            exclusiveHat: "wizard"
        ),
    ]

    static func destination(_ id: String) -> Destination? { destinations.first { $0.id == id } }

    static func discovery(_ id: String) -> (Destination, Discovery)? {
        for d in destinations {
            if let disc = d.discoveries.first(where: { $0.id == id }) { return (d, disc) }
        }
        return nil
    }

    static var totalDiscoveries: Int { destinations.reduce(0) { $0 + $1.discoveries.count } }
}

// MARK: - Wardrobe

struct Hat: Identifiable, Hashable {
    enum Source: Hashable { case market, adventure(String), festival }
    let id: String
    let name: String
    let symbol: String
    let price: Int
    let premium: Bool
    let source: Source

    var model: String { "hat_\(id)" }
}

enum Wardrobe {
    static let hats: [Hat] = [
        Hat(id: "bow", name: "Big Bow", symbol: "gift.fill", price: 50, premium: false, source: .market),
        Hat(id: "party", name: "Party Hat", symbol: "party.popper.fill", price: 45, premium: false, source: .market),
        Hat(id: "straw", name: "Straw Sun Hat", symbol: "sun.max.fill", price: 60, premium: false, source: .market),
        Hat(id: "beanie", name: "Cozy Beanie", symbol: "snowflake", price: 70, premium: false, source: .market),
        Hat(id: "flowercrown", name: "Flower Crown", symbol: "camera.macro", price: 80, premium: false, source: .market),
        Hat(id: "frog", name: "Frog Hat", symbol: "tortoise.fill", price: 90, premium: false, source: .market),
        Hat(id: "headphones", name: "Headphones", symbol: "headphones", price: 110, premium: false, source: .market),
        Hat(id: "wizard", name: "Wizard Hat", symbol: "wand.and.stars", price: 150, premium: true, source: .market),
        Hat(id: "crown", name: "Little Crown", symbol: "crown.fill", price: 220, premium: true, source: .market),
        Hat(id: "explorer", name: "Explorer's Hat", symbol: "binoculars.fill", price: 0, premium: false, source: .adventure("woods")),
        Hat(id: "pumpkin", name: "Pumpkin Cap", symbol: "leaf.fill", price: 0, premium: false, source: .festival),
        Hat(id: "maple", name: "Maple Crown", symbol: "leaf.fill", price: 0, premium: false, source: .festival),
    ]

    static func hat(_ id: String) -> Hat? { hats.first { $0.id == id } }

    /// Today's market: a few hats, reshuffled every day at midnight.
    static func market(on date: Date, plus: Bool) -> [Hat] {
        let day = Calendar.current.ordinality(of: .day, in: .era, for: date) ?? 0
        var rng = SeededRandom(seed: UInt64(day) &* 2654435761)
        let pool = hats.filter { $0.source == .market }
        var picks: [Hat] = []
        var candidates = pool
        while picks.count < (plus ? 6 : 4) && !candidates.isEmpty {
            let i = Int(rng.next() * Double(candidates.count)) % candidates.count
            picks.append(candidates.remove(at: i))
        }
        return picks
    }
}

// MARK: - Seasonal event

enum HarvestFestival {
    static let name = "Harvest Festival"

    static func isActive(on date: Date = .now) -> Bool {
        Calendar.current.component(.month, from: date) == 10
    }

    /// Chest rewards by the number of festival mornings won (1-based).
    enum Reward: Equatable {
        case decor(String)
        case hat(String)
        case coins(Int)
    }

    static func reward(forChest n: Int) -> Reward {
        switch n {
        case 1: .decor("pumpkins")
        case 3: .hat("pumpkin")
        case 5: .decor("scarecrow")
        case 7: .decor("maple")
        case 10: .hat("maple")
        default: .coins(20 + min(n, 20))
        }
    }

    static let milestones = [1, 3, 5, 7, 10]
}

// MARK: - Vacations

/// Where Sprig stays and what he gets up to on a vacation.
struct VacationInfo: Sendable {
    let stay: String
    let price: Int
    /// What he's doing at StayPoint, ActivityA, ActivityB, ActivityC.
    let activities: [String]
}

struct BookedTrip: Codable, Hashable, Sendable {
    var destination: String
    /// Start of the day the trip happens.
    var day: Date
}

enum VacationCatalog {
    static let info: [String: VacationInfo] = [
        "meadow": VacationInfo(stay: "Dandelion B&B", price: 40,
                               activities: ["Checking in at the Dandelion B&B", "Having a picnic", "Flying a kite", "Smelling the giant daisies"]),
        "woods": VacationInfo(stay: "Treetop Cabin", price: 60,
                              activities: ["Climbing up to the Treetop Cabin", "Toasting marshmallows", "Crossing the log bridge", "Tiptoeing round the mushroom ring"]),
        "beach": VacationInfo(stay: "Seashell Bungalow", price: 80,
                              activities: ["Unpacking at the Seashell Bungalow", "Building a sandcastle", "Sunbathing under the parasol", "Fishing off the pier"]),
        "mushroom": VacationInfo(stay: "Toadstool Inn", price: 100,
                                 activities: ["Checking in at the Toadstool Inn", "Bouncing on mushroom caps", "Following the spore lanterns", "Sipping tea on a stump"]),
        "harbor": VacationInfo(stay: "Cloud Harbor Hotel", price: 130,
                               activities: ["Checking in at the Cloud Harbor Hotel", "Watching the balloons at the dock", "Climbing the lighthouse", "Eating cloud cake at the café"]),
        "caves": VacationInfo(stay: "Crystal Grotto Lodge", price: 160,
                              activities: ["Settling in at the Crystal Grotto Lodge", "Riding the mine cart", "Admiring the glowing crystals", "Dipping toes in the cave pool"]),
        "peaks": VacationInfo(stay: "Aurora Chalet", price: 200,
                              activities: ["Warming up at the Aurora Chalet", "Sledding down the slope", "Building a snowman", "Soaking in the hot spring"]),
        "moon": VacationInfo(stay: "Moonbeam Observatory", price: 260,
                             activities: ["Arriving at the Moonbeam Observatory", "Stargazing through the telescope", "Swinging in the hammock", "Gazing at the reflecting pool"]),
    ]

    static func info(for id: String) -> VacationInfo? { info[id] }
}
