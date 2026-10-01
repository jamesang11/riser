import AVFoundation
import UIKit

enum SFX: String {
    case rep = "sfx_rep"
    case complete = "sfx_complete"
    case coin = "sfx_coin"
    case build = "sfx_build"
    case levelUp = "sfx_levelup"
    case tap = "sfx_tap"
    case pet = "sfx_pet"
    case nope = "sfx_nope"
}

/// Plays the in-app alarm loop during missions, UI sound effects, ambience and music.
@MainActor
final class SoundService {
    static let shared = SoundService()

    private var sfxPlayers: [String: [AVAudioPlayer]] = [:]
    private var alarmPlayer: AVAudioPlayer?
    private var ambientPlayer: AVAudioPlayer?
    private var ambientName: String?
    private var musicPlayer: AVAudioPlayer?
    private var fadeTimers: [ObjectIdentifier: Timer] = [:]

    var musicEnabled = false { didSet { musicEnabled ? startMusic() : stopMusic() } }
    var ambienceEnabled = true { didSet { if !ambienceEnabled { setAmbience(nil) } else if let n = pendingAmbience { setAmbience(n) } } }
    var effectsEnabled = true
    private var pendingAmbience: String?

    private init() {}

    private func url(_ name: String) -> URL? {
        Bundle.main.url(forResource: name, withExtension: "caf")
            ?? Bundle.main.url(forResource: name, withExtension: "wav")
    }

    func configureForIsland() {
        let session = AVAudioSession.sharedInstance()
        try? session.setCategory(.ambient, mode: .default, options: [.mixWithOthers])
        try? session.setActive(true)
    }

    func configureForAlarm() {
        let session = AVAudioSession.sharedInstance()
        try? session.setCategory(.playback, mode: .default, options: [])
        try? session.setActive(true)
    }

    // MARK: SFX

    func play(_ sfx: SFX, volume: Float = 0.8, rate: Float = 1) {
        guard effectsEnabled else { return }
        let key = sfx.rawValue
        var pool = sfxPlayers[key] ?? []
        var player = pool.first { !$0.isPlaying }
        if player == nil, let u = url(key), let p = try? AVAudioPlayer(contentsOf: u) {
            p.enableRate = true
            p.prepareToPlay()
            pool.append(p)
            sfxPlayers[key] = pool
            player = p
        }
        guard let player else { return }
        player.volume = volume
        player.rate = rate
        player.currentTime = 0
        player.play()
    }

    // MARK: Alarm loop (during missions)

    func startAlarmLoop(_ sound: AlarmSound) {
        // Never leave an earlier loop playing underneath (e.g. a real alarm replacing a practice run).
        alarmPlayer?.stop()
        alarmPlayer = nil
        configureForAlarm()
        stopMusic()
        setAmbience(nil)
        guard let u = url(sound.loopName), let p = try? AVAudioPlayer(contentsOf: u) else { return }
        p.numberOfLoops = -1
        p.volume = 0.2
        p.play()
        alarmPlayer = p
        fade(p, to: 1, duration: 4)
    }

    /// While the player is actively working, the alarm steps back so reps are audible.
    func duckAlarm(_ ducked: Bool) {
        guard let p = alarmPlayer else { return }
        fade(p, to: ducked ? 0.18 : 1, duration: ducked ? 0.6 : 2.5)
    }

    func stopAlarmLoop() {
        guard let p = alarmPlayer else { return }
        alarmPlayer = nil
        fade(p, to: 0, duration: 0.8) { p.stop() }
        configureForIsland()
        // Back to the island's own soundscape.
        startMusic()
        if let pendingAmbience { setAmbience(pendingAmbience) }
    }

    // MARK: Ambience + music

    func setAmbience(_ name: String?) {
        if name != nil { pendingAmbience = name }
        guard ambienceEnabled || name == nil else { return }
        guard name != ambientName else { return }
        ambientName = name
        if let old = ambientPlayer {
            fade(old, to: 0, duration: 2) { old.stop() }
        }
        guard let name, let u = url(name), let p = try? AVAudioPlayer(contentsOf: u) else {
            ambientPlayer = nil
            return
        }
        p.numberOfLoops = -1
        p.volume = 0
        p.play()
        ambientPlayer = p
        fade(p, to: 0.16, duration: 3)
    }

    func startMusic() {
        guard musicEnabled, alarmPlayer == nil, musicPlayer == nil,
              let u = url("music_island"), let p = try? AVAudioPlayer(contentsOf: u) else { return }
        p.numberOfLoops = -1
        p.volume = 0
        p.play()
        musicPlayer = p
        fade(p, to: 0.2, duration: 4)
    }

    func stopMusic() {
        guard let p = musicPlayer else { return }
        musicPlayer = nil
        fade(p, to: 0, duration: 1.2) { p.stop() }
    }

    // MARK: Fading

    private func fade(_ player: AVAudioPlayer, to target: Float, duration: TimeInterval, completion: (() -> Void)? = nil) {
        let id = ObjectIdentifier(player)
        fadeTimers[id]?.invalidate()
        let start = player.volume
        let steps = max(1, Int(duration * 30))
        var i = 0
        let timer = Timer(timeInterval: duration / Double(steps), repeats: true) { [weak self] t in
            MainActor.assumeIsolated {
                i += 1
                let f = Float(i) / Float(steps)
                player.volume = start + (target - start) * f
                if i >= steps {
                    t.invalidate()
                    self?.fadeTimers[id] = nil
                    completion?()
                }
            }
        }
        RunLoop.main.add(timer, forMode: .common)
        fadeTimers[id] = timer
    }
}

enum Haptics {
    @MainActor static func tap() { UIImpactFeedbackGenerator(style: .light).impactOccurred() }
    @MainActor static func soft() { UIImpactFeedbackGenerator(style: .soft).impactOccurred() }
    @MainActor static func rep() { UIImpactFeedbackGenerator(style: .rigid).impactOccurred(intensity: 0.9) }
    @MainActor static func heavy() { UIImpactFeedbackGenerator(style: .heavy).impactOccurred() }
    @MainActor static func success() { UINotificationFeedbackGenerator().notificationOccurred(.success) }
    @MainActor static func warning() { UINotificationFeedbackGenerator().notificationOccurred(.warning) }
    @MainActor static func select() { UISelectionFeedbackGenerator().selectionChanged() }
}
