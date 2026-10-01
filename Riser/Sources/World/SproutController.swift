import SceneKit
import UIKit
import simd

/// Brings the companion to life: breathing, blinking, hopping around, little emotes that react to the
/// time of day and weather, sleeping in a nightcap, and delighted reactions when petted.
@MainActor
final class SproutController {
    let root = SCNNode()              // position + facing
    private let bouncer = SCNNode()   // hop height + squash
    private var model = SCNNode()

    // Parts (all optional so the controller works with any version of the model).
    private var eyes: [SCNNode] = []
    private var eyeBase: [SIMD3<Float>] = []
    private var happyEyes: [SCNNode] = []
    private var sleepEyes: [SCNNode] = []
    private var mouth: SCNNode?
    private var mouthOpen: SCNNode?
    private var arms: [SCNNode] = []
    private var armBase: [SIMD3<Float>] = []
    private var nightcap: SCNNode?
    private var stem: SCNNode?
    private var leaves: [SCNNode] = []
    private var leafBase: [SIMD3<Float>] = []
    private var bud: SCNNode?
    private var flower: SCNNode?
    private var hatNode: SCNNode?
    private var sadEyes: [SCNNode] = []
    private var sadMouth: SCNNode?
    private var nextTear: TimeInterval = 0
    private var nextRumble: TimeInterval = 0
    private var rumbleUntil: TimeInterval = 0
    /// Companion needs, fed from the game state.
    var moodTier: MoodTier = .okay
    var hungry = false
    var sick = false { didSet { if sick != oldValue { nightcap?.isHidden = !sick && mode != .sleeping; hatNode?.isHidden = sick; applyTint() } } }
    /// Two or more missed mornings: a gloomy little rain cloud follows Sprig around.
    var gloomy = false { didSet { if gloomy != oldValue { updateHeadCloud() } } }
    private(set) var bedridden = false
    private(set) var bedSick = false
    private var awayFlag = false
    /// Inside the house/tent (hidden on the island).
    private(set) var indoors = false
    /// The camera is inside the home; hide the island sprout unless it's in bed.
    var viewingInside = false { didSet { refreshVisibility() } }
    private var enteringHome = false
    private var doorSpot = SIMD2<Float>(0, 0.9)
    /// Extra height above the island surface (e.g. lying on a mattress).
    private(set) var liftY: Float = 0
    private var headCloud: SCNNode?
    private var swirls: SCNNode?
    private var bodyMaterials: [SCNMaterial] = []
    private var nextSneeze: TimeInterval = 0
    private var hatID: String?

    enum Face { case normal, happy, sleepy, surprised, sad }
    private enum Emote { case wave, stretch, dance, shiver, lookAround }
    private enum Mode: Equatable {
        case idle, walking, sleeping, celebrating
        case emote(Int)
    }
    private let emotes: [Emote] = [.wave, .stretch, .dance, .shiver, .lookAround]

    private var mode: Mode = .idle
    private var modeStart: TimeInterval = 0
    private var modeUntil: TimeInterval = 0
    private var face: Face = .normal
    private var target: SIMD2<Float>?
    private var nextDecision: TimeInterval = 0
    private var nextBlink: TimeInterval = 1
    private var blinkUntil: TimeInterval = 0
    private var hopPhase: Float = 0
    private var yaw: Float = 0
    private var desiredYaw: Float = 0
    private var reactUntil: TimeInterval = 0
    private var sleepEmitter: SCNNode?
    private var squash: Float = 0
    private var lastT: TimeInterval = 0
    private var stageScale: Float = 1

    /// Areas the sprout should not walk through (built items), in island x/z.
    var obstacles: [(SIMD2<Float>, Float)] = [] { didSet { nav.rebuild(obstacles: obstacles) } }
    /// Walkable grid; Sprig routes around everything built on the island.
    private var nav = NavGrid()
    private var waypoints: [SIMD2<Float>] = []

    /// Plans a route around obstacles and starts walking it. Returns false if there's no way there.
    @discardableResult
    private func goTo(_ goal: SIMD2<Float>) -> Bool {
        guard let route = nav.path(from: position, to: goal), !route.isEmpty else { return false }
        waypoints = Array(route.dropFirst())
        target = route[0]
        mode = .walking
        return true
    }
    /// Where the sprout curls up at night.
    var bedSpot = SIMD2<Float>(0.75, 0.95)
    var cameraYaw: Float = 0
    /// Sprig now sleeps indoors at bedtime (see walkIndoors), never out on the grass.
    var sleepsOutdoors = false
    var wind: Float = 0.3
    var weather: WeatherKind = .clear
    var goldenHour: Double = 0

    init() {
        root.name = "SproutRoot"
        root.addChildNode(bouncer)
        model = ModelLibrary.node("sprout") ?? Self.fallbackModel()
        bouncer.addChildNode(model)

        eyes = ["EyeL", "EyeR"].compactMap { model.part($0) }
        eyeBase = eyes.map(\.simdScale)
        happyEyes = ["EyeHappyL", "EyeHappyR"].compactMap { model.part($0) }
        sleepEyes = ["EyeSleepL", "EyeSleepR"].compactMap { model.part($0) }
        mouth = model.part("Mouth")
        mouthOpen = model.part("MouthOpen")
        arms = ["ArmL", "ArmR"].compactMap { model.part($0) }
        armBase = arms.map(\.simdEulerAngles)
        nightcap = model.part("Nightcap")
        sadEyes = ["EyeSadL", "EyeSadR"].compactMap { model.part($0) }
        sadMouth = model.part("MouthSad")
        sadEyes.forEach { $0.isHidden = true }
        sadMouth?.isHidden = true
        model.enumerateHierarchy { n, _ in
            for m in n.geometry?.materials ?? [] where m.name == "SproutBody" || m.name == "SproutCheek" {
                if !bodyMaterials.contains(where: { $0 === m }) { bodyMaterials.append(m) }
            }
        }
        stem = model.part("Stem")
        leaves = ["LeafL", "LeafR"].compactMap { model.part($0) }
        leafBase = leaves.map(\.simdEulerAngles)
        bud = model.part("Bud")
        flower = model.part("Flower")
        nightcap?.isHidden = true
        setFace(.normal)
        addOutline()

        root.simdPosition = SIMD3(0.4, 0, 1.4)
        root.simdScale = SIMD3(repeating: 2.1)
        // Generous invisible tap target so the little sprout is easy to pet.
        let hitGeo = SCNSphere(radius: 0.42)
        let hitMat = SCNMaterial()
        hitMat.colorBufferWriteMask = []
        hitMat.writesToDepthBuffer = false
        hitGeo.firstMaterial = hitMat
        let hit = SCNNode(geometry: hitGeo)
        hit.simdPosition = SIMD3(0, 0.3, 0)
        hit.castsShadow = false
        root.addChildNode(hit)
    }

    var position: SIMD2<Float> { SIMD2(root.simdPosition.x, root.simdPosition.z) }
    var isSleeping: Bool { mode == .sleeping }

    func setStage(_ stage: SproutStage) {
        bud?.isHidden = stage != .bud
        flower?.isHidden = stage != .bloom
        stageScale = [0.75, 1.0, 1.08, 1.15][stage.rawValue]
        for leaf in leaves { leaf.simdScale = SIMD3(repeating: stageScale) }
        stem?.simdScale = SIMD3(1, 0.8 + 0.2 * stageScale, 1)
    }

    // MARK: Hats & travel

    func setHat(_ id: String?) {
        guard id != hatID else { return }
        hatID = id
        hatNode?.removeFromParentNode()
        hatNode = nil
        guard let id, let node = ModelLibrary.node("hat_\(id)") else { return }
        model.addChildNode(node)
        hatNode = node
        node.isHidden = mode == .sleeping
        node.scale = SCNVector3(0.01, 0.01, 0.01)
        let pop = SCNAction.scale(to: 1.15, duration: 0.2)
        pop.timingMode = .easeOut
        node.runAction(.sequence([pop, .scale(to: 1, duration: 0.12)]))
    }

    /// A lightweight copy of the sprout (with its hat) to ride in the balloon.
    func passenger() -> SCNNode {
        let copy = model.clone()
        copy.childNodes.filter { $0.name == "outline" }.forEach { $0.removeFromParentNode() }
        return copy
    }

    /// Hides the sprout while it's away; drops it back at `spot` on return.
    func setAway(_ away: Bool, landingAt spot: SIMD2<Float>? = nil) {
        awayFlag = away
        refreshVisibility()
        if !away {
            if let spot { root.simdPosition = SIMD3(spot.x, root.simdPosition.y, spot.y) }
            mode = .idle
            target = nil
            waypoints = []
            nightcap?.isHidden = true
            sleepEmitter?.removeFromParentNode()
            sleepEmitter = nil
            setFace(.normal)
        }
    }

    private func refreshVisibility() {
        root.isHidden = bedridden ? false : (awayFlag || indoors || viewingInside)
    }

    /// Bedtime: hop over to the front door and go inside.
    func walkIndoors(door: SIMD2<Float>) {
        doorSpot = door
        guard !indoors else { return }
        if awayFlag || root.isHidden {
            indoors = true
            refreshVisibility()
            return
        }
        enteringHome = true
        if !goTo(door) {
            // Boxed in somehow: just pop inside.
            enteringHome = false
            indoors = true
            refreshVisibility()
        }
    }

    /// Put Sprig inside immediately (no walk), parked by the door.
    func setIndoorsNow(door: SIMD2<Float>) {
        doorSpot = door
        indoors = true
        enteringHome = false
        target = nil
        waypoints = []
        mode = .idle
        root.simdPosition = SIMD3(door.x, root.simdPosition.y, door.y)
        refreshVisibility()
    }

    /// Morning (or you let him out): pop back out of the front door.
    func comeOutdoors(door: SIMD2<Float>) {
        if enteringHome {
            // Still on his way to the door: just turn around.
            enteringHome = false
            target = nil
            waypoints = []
            mode = .idle
            return
        }
        guard indoors else { return }
        indoors = false
        enteringHome = false
        root.simdPosition = SIMD3(door.x, root.simdPosition.y, door.y)
        mode = .idle
        setFace(.normal)
        nightcap?.isHidden = !sick
        refreshVisibility()
    }

    // MARK: Look

    /// A soft warm ink outline (inverted hull) so the sprout pops like a cartoon character.
    private func addOutline() {
        let ink = SCNMaterial()
        ink.lightingModel = .constant
        ink.diffuse.contents = UIColor(red: 0.33, green: 0.24, blue: 0.2, alpha: 1)
        ink.cullMode = .front
        ink.shaderModifiers = [.geometry: "_geometry.position.xyz += _geometry.normal * 0.0085;"]
        let names = ["Body", "FootL", "FootR", "ArmL", "ArmR", "Stem", "LeafL", "LeafR", "Nightcap", "Bud", "Flower"]
        for name in names {
            guard let part = model.part(name) else { continue }
            let targets = [part]
            for n in targets where n.geometry != nil {
                guard let copy = n.geometry?.copy() as? SCNGeometry else { continue }
                copy.materials = [ink]
                let hull = SCNNode(geometry: copy)
                hull.name = "outline"
                hull.castsShadow = false
                n.addChildNode(hull)
            }
        }
    }

    private func setFace(_ f: Face) {
        face = f
        let hasHappy = !happyEyes.isEmpty, hasSleep = !sleepEyes.isEmpty
        switch f {
        case .normal:
            eyes.forEach { $0.isHidden = false }
            happyEyes.forEach { $0.isHidden = true }
            sleepEyes.forEach { $0.isHidden = true }
            setEyeOpen(1)
        case .happy:
            eyes.forEach { $0.isHidden = hasHappy }
            happyEyes.forEach { $0.isHidden = false }
            sleepEyes.forEach { $0.isHidden = true }
            if !hasHappy { setEyeOpen(0.45) }
        case .sleepy:
            eyes.forEach { $0.isHidden = hasSleep }
            sleepEyes.forEach { $0.isHidden = false }
            happyEyes.forEach { $0.isHidden = true }
            if !hasSleep { setEyeOpen(0.08) }
        case .surprised:
            eyes.forEach { $0.isHidden = false }
            happyEyes.forEach { $0.isHidden = true }
            sleepEyes.forEach { $0.isHidden = true }
            setEyeOpen(1.15)
        case .sad:
            break   // handled below
        }
        let open = (f == .happy || f == .surprised) && mouthOpen != nil
        let sad = f == .sad
        sadEyes.forEach { $0.isHidden = !sad }
        if sad {
            eyes.forEach { $0.isHidden = !sadEyes.isEmpty }
            happyEyes.forEach { $0.isHidden = true }
            sleepEyes.forEach { $0.isHidden = true }
            if sadEyes.isEmpty { setEyeOpen(0.7) }
        }
        sadMouth?.isHidden = !sad
        mouthOpen?.isHidden = !open
        mouth?.isHidden = open || (sad && sadMouth != nil)
    }

    private func setEyeOpen(_ open: Float) {
        for (e, base) in zip(eyes, eyeBase) { e.simdScale = SIMD3(base.x, base.y * open, base.z) }
    }

    // MARK: Reactions

    func pet(at t: TimeInterval) {
        if bedridden {
            // Just a sleepy stir.
            squash = -0.08
            thought(Textures.emoji(bedSick ? "🤒" : "💤"))
            return
        }
        if mode == .sleeping { wake() }
        reactUntil = t + 1.2
        squash = -0.35
        desiredYaw = cameraYaw
        setFace(.happy)
        burst(image: Textures.symbol("heart.fill", color: UIColor(red: 1, green: 0.45, blue: 0.55, alpha: 1)),
              count: 8, size: 0.09, color: .white, spread: 50)
    }

    func celebrate(at t: TimeInterval) {
        guard !bedridden else { return }
        if sleepEmitter != nil { wake() }
        begin(.celebrating, at: t, duration: 3.2)
        desiredYaw = cameraYaw
        setFace(.happy)
        burst(image: Textures.sparkle, count: 24, size: 0.08, color: UIColor(red: 1, green: 0.85, blue: 0.4, alpha: 1), spread: 70)
    }

    /// Say hello when the player opens the app.
    func greet(at t: TimeInterval) {
        guard !bedridden else { return }
        guard mode != .sleeping else { return }
        target = nil
        waypoints = []
        begin(.emote(0), at: t + 0.6, duration: 2.2)
        desiredYaw = cameraYaw
    }

    private func begin(_ m: Mode, at t: TimeInterval, duration: TimeInterval) {
        mode = m
        modeStart = t
        modeUntil = t + duration
    }

    private func wake() {
        sleepEmitter?.removeFromParentNode()
        sleepEmitter = nil
        nightcap?.isHidden = !sick
        hatNode?.isHidden = sick
        mode = .idle
        setFace(.normal)
    }

    // MARK: Frame update

    func update(t: TimeInterval, daylight: Double) {
        let dt = Float(lastT == 0 ? 1.0 / 60 : min(0.1, t - lastT))
        lastT = t
        if bedridden {
            // Lying on its back under the quilt, breathing slowly, the odd cough and sneeze.
            let breathe = sin(Float(t) * 1.3) * 0.04
            bouncer.simdEulerAngles = SIMD3(-0.62, 0, 0)
            bouncer.simdPosition = .zero
            bouncer.simdScale = SIMD3(1 + breathe * 0.5, 1, 1 + breathe)
            root.simdEulerAngles = SIMD3(0, yaw, 0)
            if bedSick && t > nextSneeze {
                nextSneeze = t + Double.random(in: 4...7)
                thought(Textures.emoji(["🤒", "🤧", "🌡️"].randomElement()!))
            }
            return
        }

        // Night → head to bed; morning → wake with a big stretch.
        if sleepsOutdoors && daylight < 0.1 && mode != .sleeping && mode != .celebrating {
            if simd_distance(position, bedSpot) > 0.1 {
                target = bedSpot
                mode = .walking
            } else {
                fallAsleep()
            }
        } else if sleepsOutdoors && daylight >= 0.1 && mode == .sleeping && t > reactUntil {
            wake()
            begin(.emote(1), at: t, duration: 2.6)   // stretch
        }

        var armAngles: (Float, Float) = (0, 0)
        var jitter: Float = 0

        switch mode {
        case .idle:
            if t > nextDecision {
                nextDecision = t + Double.random(in: 4...9)
                decide(t: t)
            }
            armAngles = (sin(Float(t) * 1.3) * 0.05, -sin(Float(t) * 1.3) * 0.05)
        case .walking:
            if let target {
                let d = target - position
                let dist = simd_length(d)
                if dist < 0.06, !waypoints.isEmpty {
                    self.target = waypoints.removeFirst()
                } else if dist < 0.06 {
                    self.target = nil
                    if enteringHome {
                        enteringHome = false
                        indoors = true
                        mode = .idle
                        refreshVisibility()
                    } else if false { fallAsleep() } else {
                        mode = .idle
                        desiredYaw = cameraYaw + Float.random(in: -0.4...0.4)
                        nextDecision = t + Double.random(in: 2...5)
                    }
                } else {
                    desiredYaw = atan2(d.x, d.y)
                    let step = d / dist * min(dist, 0.75 * dt)
                    root.simdPosition += SIMD3(step.x, 0, step.y)
                    let before = hopPhase
                    hopPhase += dt * 9
                    if Int(before / .pi) != Int(hopPhase / .pi) { squash = 0.22 }
                    let swing = sin(hopPhase) * 0.45
                    armAngles = (swing, swing)
                }
            } else {
                mode = .idle
            }
        case .celebrating:
            let before = hopPhase
            hopPhase += dt * 11
            if Int(before / .pi) != Int(hopPhase / .pi) { squash = 0.3 }
            desiredYaw += dt * 5
            let up = 2.3 + sin(Float(t) * 14) * 0.25
            armAngles = (-up, up)
            if t > modeUntil { finishEmote(t) }
        case .emote(let i):
            let k = Float((t - modeStart) / max(0.01, modeUntil - modeStart))
            guard t >= modeStart else { break }
            switch emotes[i] {
            case .wave:
                if face != .happy { setFace(.happy) }
                armAngles = (0.1, 1.9 + sin(Float(t) * 13) * 0.45)
                desiredYaw = cameraYaw
            case .stretch:
                if face != .sleepy && k < 0.7 { setFace(.sleepy) }
                if k >= 0.7 && face != .happy { setFace(.happy) }
                let reach = sin(min(1, k * 1.4) * .pi)
                armAngles = (-2.4 * reach, 2.4 * reach)
                squash = -0.18 * reach
            case .dance:
                if face != .happy { setFace(.happy) }
                let before = hopPhase
                hopPhase += dt * 8
                if Int(before / .pi) != Int(hopPhase / .pi) { squash = 0.2 }
                desiredYaw = cameraYaw + sin(Float(t) * 4) * 0.6
                armAngles = (-1.2 + sin(Float(t) * 8) * 0.6, 1.2 + sin(Float(t) * 8) * 0.6)
            case .shiver:
                if face != .surprised { setFace(.surprised) }
                jitter = sin(Float(t) * 70) * 0.012
                armAngles = (0.5, -0.5)
            case .lookAround:
                desiredYaw = cameraYaw + sin(k * .pi * 2) * 1.1
            }
            if t > modeUntil { finishEmote(t) }
        case .sleeping:
            armAngles = (0.25, -0.25)
        }

        // Needs: a sad sprout droops and cries a little; a hungry one's tummy rumbles.
        let feelsSad = moodTier == .sad || sick
        if mode == .idle && t > reactUntil {
            if feelsSad && face == .normal { setFace(.sad) }
            if !feelsSad && face == .sad { setFace(.normal) }
        }
        if sick && mode != .sleeping && t > nextSneeze {
            nextSneeze = t + Double.random(in: 5...8)
            squash = -0.3
            thought(Textures.emoji("🤧"))
            burst(image: Textures.softDot, count: 10, size: 0.04, color: UIColor(white: 1, alpha: 0.8), spread: 30)
        }
        if feelsSad && mode != .sleeping && t > nextTear {
            nextTear = t + Double.random(in: 4...7)
            tear()
        }
        if hungry && mode != .sleeping && t > nextRumble {
            nextRumble = t + Double.random(in: 5...8)
            rumbleUntil = t + 0.5
            thought(Textures.emoji(["🍎", "🥕", "🍰"].randomElement()!))
        }
        if t < rumbleUntil { jitter += sin(Float(t) * 55) * 0.015 }

        // Hop height.
        var height: Float = 0
        if mode == .walking {
            height = abs(sin(hopPhase)) * 0.12
        } else if mode == .celebrating {
            height = abs(sin(hopPhase)) * 0.35
        } else if case .emote(let i) = mode, emotes[i] == .dance {
            height = abs(sin(hopPhase)) * 0.14
        } else if t < reactUntil {
            let k = Float((reactUntil - t) / 1.2)
            height = sin(k * .pi) * 0.3
            armAngles = (-2.0, 2.0)
        } else if face == .happy, mode == .idle {
            setFace(.normal)
        }

        // Turn smoothly.
        var dy = desiredYaw - yaw
        while dy > .pi { dy -= 2 * .pi }
        while dy < -.pi { dy += 2 * .pi }
        yaw += dy * min(1, dt * 7)
        root.simdEulerAngles = SIMD3(0, yaw, 0)

        // Squash & stretch with a spring back to the breathing pose.
        squash += (0 - squash) * min(1, dt * 9)
        let breathe = mode == .sleeping || feelsSad ? sin(Float(t) * 1.4) * 0.05 : sin(Float(t) * 2.3) * 0.025
        let s = squash + breathe
        bouncer.simdScale = SIMD3(1 + s * 0.6, 1 - s, 1 + s * 0.6)
        bouncer.simdPosition = SIMD3(jitter, height, 0)

        // Arms ease toward their pose.
        for (i, arm) in arms.enumerated() {
            let base = armBase[i]
            let goal = base.z + (i == 0 ? armAngles.0 : armAngles.1)
            var e = arm.simdEulerAngles
            e.z += (goal - e.z) * min(1, dt * 14)
            arm.simdEulerAngles = e
        }

        // Leaves sway in the wind.
        let sway = sin(Float(t) * (1.6 + wind)) * (0.06 + 0.12 * wind)
        let droop: Float = feelsSad ? 0.45 : hungry ? 0.2 : 0
        stem?.simdEulerAngles = SIMD3(sway * 0.4 + droop, 0, sway)
        for (i, leaf) in leaves.enumerated() {
            let base = leafBase[i]
            leaf.simdEulerAngles = SIMD3(base.x, base.y, base.z + (i == 0 ? 1 : -1) * sin(Float(t) * 2.1 + Float(i)) * 0.08)
        }
        nightcap.map { cap in cap.simdEulerAngles.z = sin(Float(t) * 1.4) * 0.05 }

        // Blink.
        if face == .normal {
            if t > nextBlink {
                nextBlink = t + Double.random(in: 2...5.5)
                blinkUntil = t + 0.16
            }
            if t < blinkUntil {
                let p = Float((blinkUntil - t) / 0.16)
                setEyeOpen(max(0.08, abs(1 - 2 * p)))
            } else {
                setEyeOpen(1)
            }
        }
    }

    /// While set, the sprout walks to this open spot and stays there (e.g. talking to the player in onboarding).
    var stageSpot: SIMD2<Float>? {
        didSet {
            guard let spot = stageSpot, stageSpot != oldValue else { return }
            // Walk there if there's a route; otherwise just pop over (e.g. if boxed in by new props).
            if !goTo(spot) {
                root.simdPosition = SIMD3(spot.x, root.simdPosition.y, spot.y)
                target = nil
                waypoints = []
                mode = .idle
            }
        }
    }

    private func decide(t: TimeInterval) {
        if let spot = stageSpot {
            if simd_distance(position, spot) > 0.35 { _ = goTo(spot) } else { begin(.emote(4), at: t, duration: 3) }
            return
        }
        let roll = Double.random(in: 0...1)
        // Weather and time of day shape what the sprout feels like doing.
        if weather == .snow && roll < 0.35 {
            begin(.emote(3), at: t, duration: 1.8)
        } else if (weather == .rain || weather == .drizzle) && roll < 0.35 {
            begin(.emote(2), at: t, duration: 3.2)
        } else if goldenHour > 0.5 && roll < 0.25 {
            begin(.emote(1), at: t, duration: 2.6)
        } else if roll < (sick ? 0.05 : moodTier == .sad ? 0.25 : 0.62), let p = randomSpot(), goTo(p) {
            // walking along the planned route
        } else if roll < 0.78 {
            begin(.emote(4), at: t, duration: 3)
        } else if roll < 0.88 {
            begin(.emote(0), at: t, duration: 2)
        } else if roll < 0.95 {
            begin(.emote(2), at: t, duration: 2.6)
        } else {
            desiredYaw = cameraYaw + Float.random(in: -0.6...0.6)
        }
    }

    // MARK: Sickness

    private func applyTint() {
        let green = sick
        for m in bodyMaterials {
            m.multiply.contents = green ? UIColor(red: 0.74, green: 0.9, blue: 0.6, alpha: 1) : UIColor.white
        }
        updateSwirls(green)
    }

    /// Green nausea squiggles circling the sprout's head.
    private func updateSwirls(_ on: Bool) {
        if on, swirls == nil {
            let ring = SCNNode()
            ring.simdPosition = SIMD3(0, 0.62, 0)
            for i in 0..<3 {
                let plane = SCNPlane(width: 0.16, height: 0.16)
                let m = SCNMaterial()
                m.lightingModel = .constant
                m.diffuse.contents = Textures.sickSwirl
                m.isDoubleSided = true
                m.writesToDepthBuffer = false
                plane.firstMaterial = m
                let n = SCNNode(geometry: plane)
                let a = Float(i) / 3 * 2 * .pi
                n.simdPosition = SIMD3(cos(a) * 0.3, Float(i % 2) * 0.05, sin(a) * 0.3)
                n.constraints = [SCNBillboardConstraint()]
                n.castsShadow = false
                let spin = SCNAction.customAction(duration: 1.2) { node, t in
                    node.simdScale = SIMD3(repeating: 0.85 + 0.2 * sin(Float(t) / 1.2 * 2 * .pi + a))
                }
                n.runAction(.repeatForever(spin))
                ring.addChildNode(n)
            }
            ring.runAction(.repeatForever(.rotateBy(x: 0, y: 2 * .pi, z: 0, duration: 3.5)))
            bouncer.addChildNode(ring)
            swirls = ring
        } else if !on, let r = swirls {
            swirls = nil
            r.removeFromParentNode()
        }
    }

    private func updateHeadCloud() {
        if gloomy, headCloud == nil {
            let holder = SCNNode()
            holder.simdPosition = SIMD3(0, 0.98, 0)
            let cloud = ModelLibrary.node("cloud_a") ?? WorldScene.fallbackCloud()
            cloud.simdScale = SIMD3(repeating: 0.13)
            cloud.enumerateHierarchy { n, _ in
                n.castsShadow = false
                n.geometry?.materials = n.geometry?.materials.map { m in
                    let c = m.copy() as! SCNMaterial
                    c.multiply.contents = UIColor(red: 0.3, green: 0.32, blue: 0.4, alpha: 1)
                    c.emission.contents = UIColor.black
                    return c
                } ?? []
            }
            holder.addChildNode(cloud)
            let bob = SCNAction.moveBy(x: 0, y: 0.04, z: 0, duration: 1.4)
            bob.timingMode = .easeInEaseOut
            holder.runAction(.repeatForever(.sequence([bob, bob.reversed()])))
            holder.opacity = 0
            holder.runAction(.fadeIn(duration: 0.8))
            root.addChildNode(holder)
            headCloud = holder
        } else if !gloomy, let c = headCloud {
            headCloud = nil
            c.runAction(.sequence([.fadeOut(duration: 0.8), .removeFromParentNode()]))
        }
    }

    /// In bed at `spot`: asleep at bedtime, or too sick to get up.
    func setInBed(_ on: Bool, sick isSick: Bool = false, at spot: SIMD2<Float>, height: Float, yaw bedYaw: Float) {
        if on && bedridden && bedSick == isSick { return }
        if !on && !bedridden { return }
        bedridden = on
        bedSick = on && isSick
        applyTint()
        sleepEmitter?.removeFromParentNode()
        sleepEmitter = nil
        if on {
            target = nil
            waypoints = []
            enteringHome = false
            mode = .sleeping
            root.simdPosition = SIMD3(spot.x, root.simdPosition.y, spot.y)
            liftY = height
            yaw = bedYaw
            desiredYaw = bedYaw
            nightcap?.isHidden = false
            hatNode?.isHidden = true
            setFace(isSick ? .sad : .sleepy)
            headCloud?.simdPosition = SIMD3(0, 0.75, -0.25)
            if !isSick { addSleepZs() }
        } else {
            liftY = 0
            bouncer.simdEulerAngles = .zero
            headCloud?.simdPosition = SIMD3(0, 0.98, 0)
            wake()
        }
        refreshVisibility()
    }

    private func addSleepZs() {
        let emitter = SCNNode()
        emitter.simdPosition = SIMD3(0.15, 0.62, -0.1)
        let ps = SCNParticleSystem()
        ps.particleImage = Textures.sleepyZ
        ps.birthRate = 0.8
        ps.particleLifeSpan = 3
        ps.particleSize = 0.09
        ps.particleVelocity = 0.18
        ps.emittingDirection = SCNVector3(0.3, 1, 0)
        ps.spreadingAngle = 15
        ps.particleColor = UIColor(white: 1, alpha: 0.9)
        ps.isLightingEnabled = false
        ps.blendMode = .alpha
        let fade = SCNParticlePropertyController(animation: {
            let a = CAKeyframeAnimation()
            a.values = [0, 1, 1, 0]
            a.keyTimes = [0, 0.15, 0.7, 1]
            return a
        }())
        ps.propertyControllers = [.opacity: fade]
        emitter.addParticleSystem(ps)
        root.addChildNode(emitter)
        sleepEmitter = emitter
    }

    /// Munch! A delighted reaction to being fed.
    func eat(_ emoji: String, at t: TimeInterval) {
        if bedridden {
            thought(Textures.emoji(emoji))
            return
        }
        if mode == .sleeping { wake() }
        reactUntil = t + 1.4
        squash = 0.3
        desiredYaw = cameraYaw
        setFace(.happy)
        burst(image: Textures.emoji(emoji), count: 6, size: 0.12, color: .white, spread: 40)
    }

    private func tear() {
        let ps = SCNParticleSystem()
        ps.particleImage = Textures.softDot
        ps.birthRate = 1 / 0.05
        ps.emissionDuration = 0.05
        ps.loops = false
        ps.particleLifeSpan = 0.9
        ps.particleSize = 0.035
        ps.particleVelocity = 0.05
        ps.acceleration = SCNVector3(0, -0.8, 0)
        ps.particleColor = UIColor(red: 0.55, green: 0.8, blue: 1, alpha: 0.95)
        ps.isLightingEnabled = false
        let n = SCNNode()
        n.simdPosition = SIMD3(0.09, 0.28, 0.2)
        bouncer.addChildNode(n)
        n.addParticleSystem(ps)
        n.runAction(.sequence([.wait(duration: 1.2), .removeFromParentNode()]))
    }

    private func thought(_ image: UIImage) {
        let ps = SCNParticleSystem()
        ps.particleImage = image
        ps.birthRate = 1 / 0.05
        ps.emissionDuration = 0.05
        ps.loops = false
        ps.particleLifeSpan = 2.2
        ps.particleSize = 0.1
        ps.particleVelocity = 0.12
        ps.emittingDirection = SCNVector3(0.2, 1, 0)
        ps.isLightingEnabled = false
        ps.blendMode = .alpha
        let fade = SCNParticlePropertyController(animation: {
            let a = CAKeyframeAnimation()
            a.values = [0, 1, 1, 0]
            a.keyTimes = [0, 0.15, 0.75, 1]
            return a
        }())
        ps.propertyControllers = [.opacity: fade]
        let n = SCNNode()
        n.simdPosition = SIMD3(0.18, 0.62, 0)
        root.addChildNode(n)
        n.addParticleSystem(ps)
        n.runAction(.sequence([.wait(duration: 2.5), .removeFromParentNode()]))
    }

    private func finishEmote(_ t: TimeInterval) {
        mode = .idle
        setFace(.normal)
        desiredYaw = cameraYaw
        nextDecision = t + Double.random(in: 2...5)
    }

    private func fallAsleep() {
        guard sleepEmitter == nil else { mode = .sleeping; return }
        mode = .sleeping
        target = nil
        waypoints = []
        desiredYaw = cameraYaw + 0.5
        setFace(.sleepy)
        nightcap?.isHidden = false
        hatNode?.isHidden = true
        let emitter = SCNNode()
        emitter.simdPosition = SIMD3(0.12, 0.6, 0)
        let ps = SCNParticleSystem()
        ps.particleImage = Textures.sleepyZ
        ps.birthRate = 0.7
        ps.particleLifeSpan = 3
        ps.particleSize = 0.09
        ps.particleVelocity = 0.18
        ps.emittingDirection = SCNVector3(0.3, 1, 0)
        ps.spreadingAngle = 15
        ps.particleColor = UIColor(white: 1, alpha: 0.9)
        ps.isLightingEnabled = false
        ps.blendMode = .alpha
        ps.sortingMode = .none
        let fade = SCNParticlePropertyController(animation: {
            let a = CAKeyframeAnimation()
            a.values = [0, 1, 1, 0]
            a.keyTimes = [0, 0.15, 0.7, 1]
            return a
        }())
        let grow = SCNParticlePropertyController(animation: {
            let a = CAKeyframeAnimation()
            a.values = [0.05, 0.12]
            return a
        }())
        ps.propertyControllers = [.opacity: fade, .size: grow]
        emitter.addParticleSystem(ps)
        root.addChildNode(emitter)
        sleepEmitter = emitter
    }

    private func randomSpot() -> SIMD2<Float>? {
        for _ in 0..<30 {
            // Stay in the half of the island facing the camera so the sprout is always easy to find.
            let a = cameraYaw + Float.random(in: -1.25...1.25)
            let r = 0.9 + sqrt(Float.random(in: 0...1)) * 2.9
            let p = SIMD2(sin(a) * r, cos(a) * r)
            if nav.isFree(p) && simd_distance(p, position) > 0.8 {
                return p
            }
        }
        return nil
    }

    private func burst(image: UIImage, count: Int, size: CGFloat, color: UIColor, spread: CGFloat) {
        let ps = SCNParticleSystem()
        ps.particleImage = image
        ps.birthRate = CGFloat(count) / 0.1
        ps.emissionDuration = 0.1
        ps.loops = false
        ps.particleLifeSpan = 1.1
        ps.particleLifeSpanVariation = 0.3
        ps.particleSize = size
        ps.particleSizeVariation = size * 0.4
        ps.particleVelocity = 1.1
        ps.particleVelocityVariation = 0.5
        ps.emittingDirection = SCNVector3(0, 1, 0)
        ps.spreadingAngle = spread
        ps.acceleration = SCNVector3(0, -0.9, 0)
        ps.particleColor = color
        ps.isLightingEnabled = false
        ps.blendMode = .alpha
        let fade = SCNParticlePropertyController(animation: {
            let a = CAKeyframeAnimation()
            a.values = [1, 1, 0]
            a.keyTimes = [0, 0.6, 1]
            return a
        }())
        ps.propertyControllers = [.opacity: fade]
        let n = SCNNode()
        n.simdPosition = SIMD3(0, 0.45, 0)
        root.addChildNode(n)
        n.addParticleSystem(ps)
        n.runAction(.sequence([.wait(duration: 2), .removeFromParentNode()]))
    }

    // MARK: Fallback (used until the Blender model is bundled)

    private static func fallbackModel() -> SCNNode {
        let root = SCNNode()
        root.name = "Sprout"
        func mat(_ c: UIColor, rough: CGFloat = 0.8) -> SCNMaterial {
            let m = SCNMaterial()
            m.lightingModel = .physicallyBased
            m.diffuse.contents = c
            m.roughness.contents = rough
            return m
        }
        let bodyGeo = SCNSphere(radius: 0.25)
        bodyGeo.segmentCount = 48
        bodyGeo.materials = [mat(UIColor(red: 0.95, green: 0.96, blue: 0.89, alpha: 1))]
        let body = SCNNode(geometry: bodyGeo)
        body.name = "Body"
        body.simdPosition = SIMD3(0, 0.22, 0)
        body.simdScale = SIMD3(1.08, 0.88, 1)
        root.addChildNode(body)
        for (name, x) in [("EyeL", Float(-0.085)), ("EyeR", Float(0.085))] {
            let g = SCNSphere(radius: 0.04)
            g.materials = [mat(UIColor(red: 0.17, green: 0.15, blue: 0.19, alpha: 1), rough: 0.2)]
            let e = SCNNode(geometry: g)
            e.name = name
            e.simdPosition = SIMD3(x, 0.24, 0.225)
            e.simdScale = SIMD3(0.85, 1.2, 0.6)
            root.addChildNode(e)
        }
        let stem = SCNNode()
        stem.name = "Stem"
        stem.simdPosition = SIMD3(0, 0.43, 0)
        root.addChildNode(stem)
        return root
    }
}
