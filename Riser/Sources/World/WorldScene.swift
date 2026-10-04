import SceneKit
import UIKit
import simd

/// The living diorama: a floating island whose sky, light and weather follow the real world.
@MainActor
final class WorldScene: NSObject {
    let scene = SCNScene()

    // Camera rig
    private let orbit = SCNNode()
    private let pitch = SCNNode()
    let cameraNode = SCNNode()
    private(set) var yaw: Float = 0
    var yawVelocity: Float = 0
    var isInteracting = false
    private(set) var distance: Float = 23
    var targetDistance: Float = 23
    #if DEBUG
    /// Filming: pull the camera back (landscape launch-video shots). 1 = normal.
    let cinemaZoom: Float = { let z = UserDefaults.standard.float(forKey: "cinemaZoom"); return z > 0 ? z : 1 }()
    #else
    let cinemaZoom: Float = 1
    #endif
    private let horizontalFOV: CGFloat = 34
    private var aspect: CGFloat = 0.46

    // Sky
    private let skyRoot = SCNNode()
    private let skyPlane = SCNNode()
    private let starsNode = SCNNode()
    private let sunNode = SCNNode()
    private let moonNode = SCNNode()
    private let skyDepth: Float = 200
    private var skyVisibleSize = CGSize(width: 130, height: 282)

    // Lights
    private let sunLightNode = SCNNode()
    private let fillLightNode = SCNNode()
    private let ambientNode = SCNNode()
    private var flashUntil: CFTimeInterval = 0
    private var nextLightning: CFTimeInterval = 0

    // World content
    private let islandRoot = SCNNode()
    private var islandModel: SCNNode?
    private let itemsRoot = SCNNode()
    private(set) var items: [String: SCNNode] = [:]
    let sprout = SproutController()
    private let cloudRing = SCNNode()
    private var clouds: [SCNNode] = []
    private var cloudMaterials: [SCNMaterial] = []
    private var floatRocks: [(SCNNode, SIMD3<Float>)] = []
    private let weatherRoot = SCNNode()
    private var rain: SCNParticleSystem?
    private var snow: SCNParticleSystem?
    private var mist: SCNParticleSystem?
    private var fireflies: SCNParticleSystem?
    private var motes: SCNParticleSystem?
    private var markersRoot = SCNNode()
    private var markers: [String: SCNNode] = [:]
    private var lights: [(SCNLight, CGFloat)] = []   // night lights and their full intensity
    private var fires: [SCNNode] = []

    private(set) var sky: SkyState?
    private var lastEnvironmentUpdate: CFTimeInterval = 0
    private var lastPalette: SkyState.Palette?
    private var displayLink: CADisplayLink?
    /// On-device frame timing (only with `-perfLog YES`).
    let perf: PerfProbe? = PerfProbe.enabled ? PerfProbe() : nil
    private var lastFrame: CFTimeInterval = 0
    private var southern = false
    private var appliedCloudCount = -1
    private var idleSway: Float = 0
    /// Resting heights of the home and farm islands; the float offset is added each frame.
    private var islandBaseY: Float = 0
    private var farmBaseY: Float = 0
    /// Where the home island is right now (kept here so the loop never has to ask the renderer).
    private var islandY: Float = 0

    /// Eased up-and-down float for both islands (same motion the old actions made).
    private func floatIslands(_ t: CFTimeInterval) {
        islandY = islandBaseY + 0.06 * (1 - cos(Float(t) * .pi / 3.2))
        islandRoot.simdPosition.y = islandY
        farmRoot.simdPosition.y = farmBaseY + 0.09 * (1 - cos(Float(t) * .pi / 3.8))
    }
    /// Moving parts of island items, looked up once instead of searched every frame.
    private var animatedParts: [String: SCNNode?] = [:]

    /// Global exposure balance for the palette's physical light values.
    private let lightScale = (sun: CGFloat(0.55), ambient: CGFloat(0.3))

    override init() {
        super.init()
        buildCamera()
        buildSky()
        buildLights()
        buildIsland()
        buildWeather()
        buildFarm()
        scene.rootNode.addChildNode(itemsRoot)
        scene.rootNode.addChildNode(sprout.root)
        scene.rootNode.addChildNode(markersRoot)
        start()
    }

    func start() {
        guard displayLink == nil else { return }
        let link = CADisplayLink(target: self, selector: #selector(frame(_:)))
        let maxFPS = Float(UIScreen.main.maximumFramesPerSecond)
        link.preferredFrameRateRange = CAFrameRateRange(minimum: 30, maximum: maxFPS, preferred: maxFPS)
        link.add(to: .main, forMode: .common)
        displayLink = link
    }

    /// Caps the frame loop at 30 fps (menus open) or restores the screen's full rate.
    func setThrottled(_ on: Bool) {
        let maxFPS = on ? 30 : Float(UIScreen.main.maximumFramesPerSecond)
        displayLink?.preferredFrameRateRange = CAFrameRateRange(minimum: 30, maximum: maxFPS, preferred: maxFPS)
    }

    func stop() {
        displayLink?.invalidate()
        displayLink = nil
    }

    // MARK: - Setup

    private func buildCamera() {
        let cam = SCNCamera()
        cam.projectionDirection = .horizontal
        cam.fieldOfView = horizontalFOV
        cam.zNear = 0.5
        cam.zFar = 600
        cam.wantsHDR = true
        cam.wantsExposureAdaptation = false
        cam.exposureOffset = -0.15
        cam.minimumExposure = -1
        cam.maximumExposure = 1
        cam.bloomIntensity = 0.4
        cam.bloomThreshold = 1.1
        cam.bloomBlurRadius = 12
        // No screen-space ambient occlusion: it was the single most expensive pass on phones.
        cam.wantsDepthOfField = false  // switched on only for close-ups (see frame)
        cam.focusDistance = CGFloat(distance)
        cam.fStop = 2.2
        cam.focalBlurSampleCount = 10
        cam.apertureBladeCount = 6
        cam.vignettingIntensity = 0.35
        cam.vignettingPower = 0.9
        cam.saturation = 1.0
        cam.contrast = 0.04
        cameraNode.camera = cam
        cameraNode.simdPosition = SIMD3(0, 0, distance)
        pitch.simdEulerAngles = SIMD3(-0.52, 0, 0)
        orbit.simdPosition = SIMD3(0, -0.6, 0)
        pitch.addChildNode(cameraNode)
        orbit.addChildNode(pitch)
        scene.rootNode.addChildNode(orbit)
    }

    private func constantMaterial(_ contents: Any, additive: Bool = false) -> SCNMaterial {
        let m = SCNMaterial()
        m.lightingModel = .constant
        m.diffuse.contents = contents
        m.writesToDepthBuffer = false
        m.readsFromDepthBuffer = false
        m.isDoubleSided = true
        if additive { m.blendMode = .add }
        return m
    }

    private func buildSky() {
        skyRoot.simdPosition = SIMD3(0, 0, -skyDepth)
        cameraNode.addChildNode(skyRoot)

        skyPlane.geometry = SCNPlane(width: 1, height: 1)
        skyPlane.geometry?.firstMaterial = constantMaterial(UIColor.systemTeal)
        skyPlane.renderingOrder = -100
        skyRoot.addChildNode(skyPlane)

        starsNode.geometry = SCNPlane(width: 1, height: 1)
        let starMat = constantMaterial(Textures.stars, additive: true)
        starMat.diffuse.wrapS = .repeat
        starMat.diffuse.wrapT = .repeat
        starsNode.geometry?.firstMaterial = starMat
        starsNode.renderingOrder = -99
        starsNode.simdPosition = SIMD3(0, 0, 0.5)
        skyRoot.addChildNode(starsNode)
        starsNode.runAction(.repeatForever(.sequence([
            .fadeOpacity(to: 0.8, duration: 2.3), .fadeOpacity(to: 1, duration: 1.9),
        ])))

        let sunPlane = SCNPlane(width: 34, height: 34)
        sunPlane.firstMaterial = constantMaterial(Textures.sun, additive: true)
        sunPlane.firstMaterial?.diffuse.intensity = 2.4
        sunNode.geometry = sunPlane
        sunNode.renderingOrder = -98
        skyRoot.addChildNode(sunNode)

        let moonPlane = SCNPlane(width: 30, height: 30)
        let moonMat = constantMaterial(Textures.moon(phase: 0.5))
        moonMat.blendMode = .alpha
        moonPlane.firstMaterial = moonMat
        moonNode.geometry = moonPlane
        moonNode.renderingOrder = -97
        skyRoot.addChildNode(moonNode)
        layoutSky()
    }

    private func layoutSky() {
        let vfovHalf = atan(tan(horizontalFOV * .pi / 360) / aspect)
        let h = 2 * CGFloat(skyDepth) * tan(vfovHalf)
        let w = h * aspect
        skyVisibleSize = CGSize(width: w, height: h)
        if let plane = skyPlane.geometry as? SCNPlane {
            plane.width = w * 1.15
            plane.height = h * 1.15
        }
        if let plane = starsNode.geometry as? SCNPlane {
            plane.width = w * 1.15
            plane.height = h * 1.15
            let m = starsNode.geometry?.firstMaterial
            m?.diffuse.contentsTransform = SCNMatrix4Identity
        }
        let sunSize = w * 0.36
        (sunNode.geometry as? SCNPlane)?.width = sunSize
        (sunNode.geometry as? SCNPlane)?.height = sunSize
        (moonNode.geometry as? SCNPlane)?.width = w * 0.3
        (moonNode.geometry as? SCNPlane)?.height = w * 0.3
    }

    func setAspect(_ a: CGFloat) {
        guard a > 0, abs(a - aspect) > 0.001 else { return }
        aspect = a
        layoutSky()
        if let sky { positionCelestials(sky) }
    }

    private func buildLights() {
        let sun = SCNLight()
        sun.type = .directional
        sun.castsShadow = true
        sun.shadowMapSize = CGSize(width: 2048, height: 2048)
        sun.shadowSampleCount = 6
        sun.shadowRadius = 3.5
        sun.shadowMode = .forward
        sun.orthographicScale = 9
        sun.zNear = 1
        sun.zFar = 90
        sun.shadowBias = 0.02
        sun.shadowColor = UIColor(red: 0.05, green: 0.05, blue: 0.2, alpha: 0.45)
        sunLightNode.light = sun
        scene.rootNode.addChildNode(sunLightNode)

        let fill = SCNLight()
        fill.type = .directional
        fill.intensity = 350
        fill.castsShadow = false
        fillLightNode.light = fill
        fillLightNode.simdPosition = SIMD3(-8, 12, 20)
        fillLightNode.simdLook(at: .zero)
        orbit.addChildNode(fillLightNode)

        let ambient = SCNLight()
        ambient.type = .ambient
        ambient.intensity = 600
        ambientNode.light = ambient
        scene.rootNode.addChildNode(ambientNode)

        scene.lightingEnvironment.intensity = 1.0
    }

    private func buildIsland() {
        scene.rootNode.addChildNode(islandRoot)
        let model = ModelLibrary.node("island") ?? Self.fallbackIsland()
        islandModel = model
        islandRoot.addChildNode(model)
        for i in 1...3 {
            if let rock = model.part("FloatRock\(i)") {
                floatRocks.append((rock, rock.simdPosition))
            }
        }
        // The island's gentle float is computed in the frame loop (see `floatIslands`), not run as an action:
        // reading an action-driven position back each frame made the main thread wait on the renderer.
        islandBaseY = islandRoot.simdPosition.y
        islandRoot.addChildNode(cloudRing)
        cloudRing.runAction(.repeatForever(.rotateBy(x: 0, y: .pi * 2, z: 0, duration: 1100)))
        // Items and sprout ride along with the island's float.
        islandRoot.addChildNode(itemsRoot)
    }

    private func buildWeather() {
        weatherRoot.simdPosition = SIMD3(0, 13, 0)
        scene.rootNode.addChildNode(weatherRoot)

        let r = SCNParticleSystem()
        r.particleImage = Textures.raindrop
        r.birthRate = 0
        r.emitterShape = SCNBox(width: 22, height: 0.1, length: 22, chamferRadius: 0)
        r.birthLocation = .volume
        r.particleLifeSpan = 1.4
        r.particleVelocity = 16
        r.particleVelocityVariation = 3
        r.emittingDirection = SCNVector3(0.12, -1, 0.05)
        r.spreadingAngle = 3
        r.particleSize = 0.055
        r.stretchFactor = 0.11
        r.particleColor = UIColor(red: 0.85, green: 0.92, blue: 1, alpha: 0.55)
        r.isLightingEnabled = false
        r.blendMode = .alpha
        r.sortingMode = .none
        weatherRoot.addParticleSystem(r)
        rain = r

        let s = SCNParticleSystem()
        s.particleImage = Textures.softDot
        s.birthRate = 0
        s.emitterShape = SCNBox(width: 24, height: 0.1, length: 24, chamferRadius: 0)
        s.birthLocation = .volume
        s.particleLifeSpan = 9
        s.particleVelocity = 1.4
        s.particleVelocityVariation = 0.5
        s.emittingDirection = SCNVector3(0.1, -1, 0)
        s.spreadingAngle = 25
        s.particleSize = 0.12
        s.particleSizeVariation = 0.06
        s.particleColor = .white
        s.isLightingEnabled = false
        s.blendMode = .alpha
        s.isAffectedByPhysicsFields = true
        weatherRoot.addParticleSystem(s)
        snow = s
        let turbulence = SCNPhysicsField.turbulenceField(smoothness: 1.5, animationSpeed: 0.8)
        turbulence.strength = 0.7
        let fieldNode = SCNNode()
        fieldNode.physicsField = turbulence
        weatherRoot.addChildNode(fieldNode)

        let m = SCNParticleSystem()
        m.particleImage = Textures.puff
        m.birthRate = 0
        m.emitterShape = SCNTorus(ringRadius: 7, pipeRadius: 2.5)
        m.birthLocation = .volume
        m.particleLifeSpan = 14
        m.particleVelocity = 0.25
        m.particleSize = 3.2
        m.particleSizeVariation = 1.2
        m.particleColor = UIColor(white: 1, alpha: 0.16)
        m.isLightingEnabled = false
        m.blendMode = .alpha
        let mistFade = SCNParticlePropertyController(animation: {
            let a = CAKeyframeAnimation()
            a.values = [0, 1, 1, 0]
            a.keyTimes = [0, 0.25, 0.75, 1]
            return a
        }())
        m.propertyControllers = [.opacity: mistFade]
        let mistNode = SCNNode()
        mistNode.simdPosition = SIMD3(0, 0.2, 0)
        mistNode.addParticleSystem(m)
        islandRoot.addChildNode(mistNode)
        mist = m

        // Fireflies at night, drifting light motes by day.
        let ff = SCNParticleSystem()
        ff.particleImage = Textures.softDot
        ff.birthRate = 0
        ff.emitterShape = SCNCylinder(radius: 4.5, height: 1.6)
        ff.birthLocation = .volume
        ff.particleLifeSpan = 5
        ff.particleLifeSpanVariation = 2
        ff.particleVelocity = 0.15
        ff.spreadingAngle = 180
        ff.particleSize = 0.06
        ff.particleColor = UIColor(red: 0.85, green: 1, blue: 0.45, alpha: 1)
        ff.isLightingEnabled = false
        ff.blendMode = .additive
        ff.isAffectedByPhysicsFields = true
        let blink = SCNParticlePropertyController(animation: {
            let a = CAKeyframeAnimation()
            a.values = [0, 1, 0.3, 1, 0]
            a.keyTimes = [0, 0.2, 0.5, 0.75, 1]
            return a
        }())
        ff.propertyControllers = [.opacity: blink]
        let ffNode = SCNNode()
        ffNode.simdPosition = SIMD3(0, 0.9, 0)
        ffNode.addParticleSystem(ff)
        islandRoot.addChildNode(ffNode)
        fireflies = ff
        let wander = SCNPhysicsField.noiseField(smoothness: 1, animationSpeed: 0.4)
        wander.strength = 0.25
        let wanderNode = SCNNode()
        wanderNode.physicsField = wander
        ffNode.addChildNode(wanderNode)

        let motes = SCNParticleSystem()
        motes.particleImage = Textures.softDot
        motes.birthRate = 0
        motes.emitterShape = SCNCylinder(radius: 6, height: 3)
        motes.birthLocation = .volume
        motes.particleLifeSpan = 7
        motes.particleVelocity = 0.12
        motes.spreadingAngle = 180
        motes.particleSize = 0.035
        motes.particleColor = UIColor(red: 1, green: 0.95, blue: 0.8, alpha: 0.7)
        motes.isLightingEnabled = false
        motes.blendMode = .additive
        motes.propertyControllers = [.opacity: blink]
        let motesNode = SCNNode()
        motesNode.simdPosition = SIMD3(0, 1.5, 0)
        motesNode.addParticleSystem(motes)
        islandRoot.addChildNode(motesNode)
        self.motes = motes
    }

    // MARK: - Clouds

    private func rebuildClouds(count: Int) {
        guard count != appliedCloudCount else { return }
        appliedCloudCount = count
        clouds.forEach { $0.removeFromParentNode() }
        clouds.removeAll()
        var rng = SeededRandom(seed: 7)
        for i in 0..<count {
            let node = ModelLibrary.node(i % 2 == 0 ? "cloud_a" : "cloud_b") ?? Self.fallbackCloud()
            node.enumerateHierarchy { n, _ in n.castsShadow = false }
            let angle = Float(rng.next()) * 2 * .pi
            let radius = 10 + Float(rng.next()) * 14
            let y = -7 + Float(rng.next()) * 12
            let s = 0.8 + Float(rng.next()) * 1.4
            node.simdPosition = SIMD3(cos(angle) * radius, y, sin(angle) * radius)
            node.simdScale = SIMD3(repeating: s)
            node.simdEulerAngles = SIMD3(0, Float(rng.next()) * 6.28, 0)
            let bob = Double(1.5 + rng.next() * 2)
            node.runAction(.repeatForever(.sequence([
                .moveBy(x: 0, y: 0.35, z: 0, duration: 4 * bob),
                .moveBy(x: 0, y: -0.35, z: 0, duration: 4 * bob),
            ])))
            cloudRing.addChildNode(node)
            clouds.append(node)
        }
        cloudMaterials = clouds.flatMap { c -> [SCNMaterial] in
            var mats: [SCNMaterial] = []
            c.enumerateHierarchy { n, _ in mats += n.geometry?.materials ?? [] }
            return mats
        }
        for m in cloudMaterials {
            m.lightingModel = .physicallyBased
            m.roughness.contents = 1.0
        }
        if let palette = lastPalette { tintClouds(palette) }
    }

    private func tintClouds(_ p: SkyState.Palette) {
        let tint = p.cloudTint.uiColor
        for m in cloudMaterials {
            m.multiply.contents = tint
            m.emission.contents = UIColor(red: p.cloudTint.x * 0.22, green: p.cloudTint.y * 0.22, blue: p.cloudTint.z * 0.26, alpha: 1)
        }
    }

    // MARK: - Sky & lighting

    func apply(sky newSky: SkyState, force: Bool = false) {
        PerfProbe.measure("apply(sky)") { applySky(newSky, force: force) }
    }

    private func applySky(_ newSky: SkyState, force: Bool) {
        let first = sky == nil
        sky = newSky
        southern = newSky.southernHemisphere
        let p = newSky.palette
        let now = CACurrentMediaTime()
        let paletteChanged = lastPalette.map { !$0.isClose(to: p) } ?? true

        if paletteChanged || force {
            lastPalette = p
            // Textures are the expensive part: rebuild them only when the sky's colours actually change,
            // not when a view switch (e.g. going inside) forces the lights to refresh.
            if paletteChanged || first {
                let glowColor = newSky.isDay ? SIMD3(1.0, 0.72, 0.45) : SIMD3(0.5, 0.45, 0.8)
                skyPlane.geometry?.firstMaterial?.diffuse.contents =
                    Textures.skyGradient(p, horizonY: 0.44, sunGlow: glowColor, glowAmount: newSky.goldenHour)
                tintClouds(p)
            }

            let ambient = ambientNode.light!
            ambient.color = bedridden ? UIColor(red: 1, green: 0.86, blue: 0.72, alpha: 1) : p.ambient.uiColor
            ambient.intensity = bedridden ? 210 : CGFloat(p.ambientIntensity) * lightScale.ambient

            let night = 1 - newSky.daylight
            for m in ModelLibrary.glowMaterials {
                m.emission.intensity = CGFloat(0.1 + night * 1.3)
            }
            let rim = simd_mix(p.horizon, p.sunLight, SIMD3(repeating: 0.5)) * (0.18 + newSky.goldenHour * 0.25)
            for m in ModelLibrary.rimMaterials {
                m.setValue(NSValue(scnVector3: SCNVector3(Float(rim.x), Float(rim.y), Float(rim.z))), forKey: "rimColor")
            }
            for (light, full) in lights {
                light.intensity = full * CGFloat(max(0, night * 1.1 - 0.1))
            }
            // Indoors: the window shows the sky softly, the lamp glows gently.
            for m in roomWindowMaterials {
                m.emission.contents = newSky.isDay ? UIColor(red: 0.75, green: 0.88, blue: 1, alpha: 1) : UIColor(red: 0.2, green: 0.25, blue: 0.5, alpha: 1)
                m.emission.intensity = 0.35
            }
            for m in roomLampMaterials { m.emission.intensity = 0.12 }
            cameraNode.camera?.bloomIntensity = bedridden ? 0.12 : 0.4
            let fill = fillLightNode.light!
            fill.color = simd_mix(p.ambient, SIMD3(1, 1, 1), SIMD3(repeating: 0.4)).uiColor
            fill.intensity = bedridden ? 60 : CGFloat(90 + newSky.daylight * 160)
            (starsNode.geometry?.firstMaterial)?.transparency = CGFloat(max(0, night - 0.1) * (1 - newSky.weather.kind.overcast * 0.9))

            if first || (paletteChanged && now - lastEnvironmentUpdate > 3) {
                lastEnvironmentUpdate = now
                let ground = SIMD3(0.35, 0.5, 0.3) * (0.3 + 0.7 * newSky.daylight)
                scene.lightingEnvironment.contents = Textures.environment(p, ground: ground)
                scene.lightingEnvironment.intensity = CGFloat(0.2 + 0.45 * newSky.daylight)
            }
        }

        positionCelestials(newSky)
        applyWeather(newSky)
        let moon = Textures.moon(phase: newSky.moonPhase)
        if let m = moonNode.geometry?.firstMaterial, m.diffuse.contents as? UIImage !== moon { m.diffuse.contents = moon }
    }

    /// World direction toward a point in the sky (azimuth from north, elevation), in island space.
    private func direction(az: Double, el: Double) -> SIMD3<Float> {
        let a = (az + (southern ? 180 : 0)) * .pi / 180
        let e = el * .pi / 180
        return SIMD3(Float(-sin(a) * cos(e)), Float(sin(e)), Float(cos(a) * cos(e)))
    }

    private func positionCelestials(_ s: SkyState) {
        let p = lastPalette ?? s.palette
        // Sky sprites: horizontal position follows azimuth relative to where the camera looks.
        let facing = (southern ? 0.0 : 180.0) - Double(yaw) * 180 / .pi
        func screen(az: Double, el: Double) -> (SIMD3<Float>, Float) {
            var rel = az - facing
            while rel > 180 { rel -= 360 }
            while rel < -180 { rel += 360 }
            let sx = 0.5 + rel / 190
            let horizon = 0.47
            let sy = el >= 0 ? horizon - (horizon - 0.1) * pow(min(el, 75) / 75, 0.6) : horizon - el * 0.012
            let x = Float((sx - 0.5) * Double(skyVisibleSize.width))
            let y = Float((0.5 - sy) * Double(skyVisibleSize.height))
            let fade = Float(max(0, min(1, (el + 5) / 7)))
            return (SIMD3(x, y, 1), fade)
        }
        let (sunPos, sunFade) = screen(az: s.sunAzimuth, el: s.sunElevation)
        sunNode.simdPosition = sunPos
        sunNode.opacity = CGFloat(sunFade) * CGFloat(1 - s.weather.kind.overcast * 0.85)
        let (moonPos, moonFade) = screen(az: s.moonAzimuth, el: s.moonElevation)
        moonNode.simdPosition = moonPos + SIMD3(0, 0, 0.5)
        moonNode.opacity = CGFloat(moonFade) * CGFloat(1 - s.daylight * 0.65) * CGFloat(1 - s.weather.kind.overcast * 0.8)

        // Stars drift as you orbit.
        if let m = starsNode.geometry?.firstMaterial {
            m.diffuse.contentsTransform = SCNMatrix4MakeTranslation(-yaw / (2 * .pi) * 1.5, 0, 0)
        }

        // Key light: the sun by day, the moon by night.
        let light = sunLightNode.light!
        let daylight = s.daylight
        let dir: SIMD3<Float>
        if daylight > 0.25 {
            dir = direction(az: s.sunAzimuth, el: max(s.sunElevation, 14))
            light.color = p.sunLight.uiColor
            light.intensity = CGFloat(p.sunIntensity) * lightScale.sun * CGFloat(1 - 0.18 * Double(gloom)) * (bedridden ? 0.22 : 1)
        } else {
            let moonUp = s.moonElevation > 0
            dir = moonUp ? direction(az: s.moonAzimuth, el: max(s.moonElevation, 25)) : SIMD3(0.3, 0.9, 0.3)
            let phaseLight = 1 - abs(s.moonPhase - 0.5) * 1.6
            light.color = UIColor(red: 0.62, green: 0.72, blue: 1, alpha: 1)
            light.intensity = CGFloat(max(p.sunIntensity * 0.55, 120 + 200 * phaseLight * (moonUp ? 1 : 0.4))) * (bedridden ? 0.25 : 1)
        }
        lightDirection = simd_normalize(dir)
        sunLightNode.simdPosition = orbit.simdPosition + lightDirection * 40
        sunLightNode.simdLook(at: orbit.simdPosition)
    }

    private func applyWeather(_ s: SkyState) {
        let kind = s.weather.kind
        rebuildClouds(count: kind.cloudCount)
        let wind = Float(min(1, s.weather.windKmh / 35))
        sprout.wind = wind
        sprout.weather = kind
        sprout.goldenHour = s.goldenHour
        for m in ModelLibrary.windMaterials { m.setValue(NSNumber(value: wind), forKey: "windAmount") }
        let critterWeather = kind.precipitation == 0 && s.daylight > 0.45
        critters.setActive(butterflies: critterWeather && kind != .cloudy, birds: critterWeather)
        let precip = kind.precipitation
        rain?.birthRate = kind == .snow ? 0 : CGFloat(700 * precip)
        rain?.emittingDirection = SCNVector3(0.1 + wind * 0.3, -1, 0.05)
        snow?.birthRate = kind == .snow ? 260 : 0
        mist?.birthRate = kind == .fog ? 2.2 : (kind == .cloudy || kind == .drizzle ? 0.35 : 0)
        let night = 1 - s.daylight
        fireflies?.birthRate = precip > 0 ? 0 : CGFloat(max(0, night - 0.3) * 9)
        motes?.birthRate = precip > 0 || night > 0.5 ? 0 : CGFloat(3 + s.goldenHour * 6)
        if kind != .thunder { nextLightning = 0 }
    }

    // MARK: - Items

    private var appliedPlacements: [String: ItemPlacement] = [:]

    /// Shows the built items wherever the player placed them (home island or an expansion isle).
    func setBuilt(_ ids: [String], placements: [String: ItemPlacement] = [:], animate newID: String?) {
        let wanted = Set(ids)
        for (id, node) in items where !wanted.contains(id) {
            node.removeFromParentNode()
            items[id] = nil
            animatedParts[id] = nil
            appliedPlacements[id] = nil
        }
        func spot(_ item: Buildable) -> ItemPlacement {
            placements[item.id] ?? ItemPlacement(island: 0, x: item.slot.x, z: item.slot.y, rotation: item.rotation)
        }
        for id in ids {
            guard let item = BuildCatalog.item(id) else { continue }
            let p = spot(item)
            let parent = itemRoot(for: p.island)
            if let holder = items[id] {
                guard appliedPlacements[id] != p else { continue }
                if holder.parent !== parent {
                    holder.removeFromParentNode()
                    parent.addChildNode(holder)
                }
                holder.simdPosition = SIMD3(p.x, 0, p.z)
                holder.simdEulerAngles = SIMD3(0, p.rotation, 0)
                if appliedPlacements[id] != nil { playConstruction(holder, scale: item.scale) }
            } else {
                let node = ModelLibrary.node(item.model) ?? Self.fallbackItem(item)
                let holder = SCNNode()
                holder.name = "item:\(id)"
                holder.addChildNode(node)
                holder.simdPosition = SIMD3(p.x, 0, p.z)
                holder.simdEulerAngles = SIMD3(0, p.rotation, 0)
                holder.simdScale = SIMD3(repeating: item.scale)
                decorate(id: id, node: holder)
                parent.addChildNode(holder)
                items[id] = holder
                animatedParts[id] = nil
                if id == newID { playConstruction(holder, scale: item.scale) }
            }
            appliedPlacements[id] = p
        }
        // The sprout lives on the home island: only what's there gets in his way.
        sprout.obstacles = ids.compactMap { BuildCatalog.item($0) }.flatMap { item -> [(SIMD2<Float>, Float)] in
            let p = spot(item)
            return p.island == 0 ? Self.footprint(item, at: p.point, rotation: p.rotation) : []
        }
        if let sky { apply(sky: sky, force: true) }
    }

    private func itemRoot(for island: Int) -> SCNNode {
        island == 0 ? itemsRoot : (isleItemRoots[island] ?? itemsRoot)
    }

    // MARK: - Expansion isles

    private var isleRoots: [Int: SCNNode] = [:]
    private var isleItemRoots: [Int: SCNNode] = [:]

    /// Adds bought isles (floating with the home island) and their rope bridges. `newIsle` rises into view.
    func setIsles(_ owned: [Int], animate newIsle: Int?) {
        for id in owned where isleRoots[id] == nil {
            guard let isle = IsleCatalog.isle(id) else { continue }
            let root = SCNNode()
            root.name = "isle:\(id)"
            root.addChildNode(ModelLibrary.node(isle.model) ?? Self.fallbackIsle(radius: isle.buildRadius + 0.6))
            let itemsNode = SCNNode()
            root.addChildNode(itemsNode)
            root.simdPosition = isle.position
            islandRoot.addChildNode(root)
            isleRoots[id] = root
            isleItemRoots[id] = itemsNode
            let bridge = makeBridge(to: isle)
            islandRoot.addChildNode(bridge)
            if id == newIsle {
                root.simdPosition.y = isle.position.y - 9
                root.opacity = 0
                let rise = SCNAction.move(to: SCNVector3(isle.position), duration: 2.4)
                rise.timingMode = .easeOut
                root.runAction(.group([rise, .fadeIn(duration: 0.9)]))
                bridge.opacity = 0
                bridge.runAction(.sequence([.wait(duration: 2.2), .fadeIn(duration: 0.8)]))
            }
        }
        if let sky { apply(sky: sky, force: true) }
    }

    /// A rope bridge from the home island's edge to the isle's edge (the model spans 6 m along +Z).
    private func makeBridge(to isle: Isle) -> SCNNode {
        let dir = simd_normalize(SIMD2(isle.position.x, isle.position.z))
        let start = SIMD3(dir.x * 4.25, 0, dir.y * 4.25)
        let endXZ = SIMD2(isle.position.x, isle.position.z) - dir * (isle.buildRadius + 0.5)
        let v = SIMD3(endXZ.x, isle.position.y, endXZ.y) - start
        let horizontal = simd_length(SIMD2(v.x, v.z))
        let yawNode = SCNNode()
        yawNode.simdPosition = start
        yawNode.simdEulerAngles = SIMD3(0, atan2(v.x, v.z), 0)
        let pitchNode = SCNNode()
        pitchNode.simdEulerAngles = SIMD3(-atan2(v.y, horizontal), 0, 0)
        let model = ModelLibrary.node("bridge") ?? Self.fallbackBridge()
        model.simdScale = SIMD3(1, 1, simd_length(v) / 6)
        pitchNode.addChildNode(model)
        yawNode.addChildNode(pitchNode)
        return yawNode
    }

    // MARK: - Placing things

    private var ghost: SCNNode?
    private var ghostRing: SCNMaterial?
    private var ghostID: String?
    private(set) var ghostPlacement: ItemPlacement?
    /// Tells the world whether a spot is free (green ring) or not (red ring).
    var ghostValidator: ((ItemPlacement) -> Bool)?

    /// A see-through preview of `id` at `placement` while the player chooses a spot; nil clears it.
    func setGhost(id: String?, placement: ItemPlacement?) {
        guard let id, let placement, let item = BuildCatalog.item(id) else {
            ghost?.removeFromParentNode()
            ghost = nil
            ghostID = nil
            ghostPlacement = nil
            for (_, n) in items where n.opacity < 1 { n.opacity = 1 }
            return
        }
        if ghostID != id || ghost == nil {
            ghost?.removeFromParentNode()
            let g = SCNNode()
            let model = ModelLibrary.node(item.model) ?? Self.fallbackItem(item)
            model.simdScale = SIMD3(repeating: item.scale)
            model.opacity = 0.82
            let bob = SCNAction.moveBy(x: 0, y: 0.12, z: 0, duration: 0.55)
            bob.timingMode = .easeInEaseOut
            model.runAction(.repeatForever(.sequence([bob, bob.reversed()])))
            g.addChildNode(model)
            // A soft disc plus a bright rim, just above the grass.
            let r = CGFloat(BuildCatalog.radius(id))
            let m = SCNMaterial()
            m.lightingModel = .constant
            m.writesToDepthBuffer = false
            let disc = SCNCylinder(radius: r, height: 0.01)
            disc.firstMaterial = m
            let discNode = SCNNode(geometry: disc)
            discNode.opacity = 0.35
            discNode.renderingOrder = 10
            let rim = SCNTorus(ringRadius: r, pipeRadius: 0.045)
            rim.firstMaterial = m
            let rimNode = SCNNode(geometry: rim)
            rimNode.renderingOrder = 11
            let ring = SCNNode()
            ring.simdPosition = SIMD3(0, 0.1, 0)
            ring.addChildNode(discNode)
            ring.addChildNode(rimNode)
            g.addChildNode(ring)
            ghost = g
            ghostRing = m
            ghostID = id
            for (other, n) in items { n.opacity = other == id ? 0.2 : 1 }
        }
        moveGhost(to: placement)
    }

    func moveGhost(to p: ItemPlacement) {
        guard let ghost else { return }
        let parent = itemRoot(for: p.island)
        if ghost.parent !== parent {
            ghost.removeFromParentNode()
            parent.addChildNode(ghost)
        }
        ghost.simdPosition = SIMD3(p.x, 0, p.z)
        ghost.simdEulerAngles = SIMD3(0, p.rotation, 0)
        ghostPlacement = p
        let ok = ghostValidator?(p) ?? true
        ghostRing?.diffuse.contents = ok ? UIColor(red: 0.45, green: 0.92, blue: 0.5, alpha: 1)
                                         : UIColor(red: 1, green: 0.38, blue: 0.33, alpha: 1)
    }

    /// Where a screen point lands on an island's top (island-local x/z), for dragging things around.
    func groundPoint(at pt: CGPoint, in view: SCNView, island: Int) -> SIMD2<Float>? {
        let root = itemRoot(for: island).presentation
        let a = SIMD3<Float>(view.unprojectPoint(SCNVector3(Float(pt.x), Float(pt.y), 0)))
        let b = SIMD3<Float>(view.unprojectPoint(SCNVector3(Float(pt.x), Float(pt.y), 1)))
        let la = root.simdConvertPosition(a, from: nil)
        let d = root.simdConvertPosition(b, from: nil) - la
        guard abs(d.y) > 1e-5 else { return nil }
        let t = -la.y / d.y
        guard t > 0 else { return nil }
        let p = la + d * t
        return SIMD2(p.x, p.z)
    }

    /// Solid areas (island x/z centre, radius) an item occupies. Trees only block at the trunk,
    /// the lantern string only at its two poles, so Sprig can wander under canopies and lights.
    static func footprint(_ item: Buildable, at c: SIMD2<Float>, rotation: Float) -> [(SIMD2<Float>, Float)] {
        switch item.id {
        case "cottage": return [(c, 1.45)]
        case "tent": return [(c + SIMD2(0, 0.3), 1.1)]
        case "windmill": return [(c, 1.0)]
        case "pond": return [(c, 1.05)]
        case "garden": return [(c, 0.8)]
        case "campfire": return [(c, 0.75)]
        case "bench": return [(c, 0.6)]
        case "flowers": return [(c, 0.55)]
        case "pumpkins": return [(c, 0.65)]
        case "telescope": return [(c, 0.45)]
        case "treeRound", "treeBlossom", "maple": return [(c, 0.4)]
        case "pine": return [(c, 0.55)]
        case "lanterns":
            let dx = SIMD2<Float>(cos(rotation), -sin(rotation)) * 1.2
            return [(c + dx, 0.18), (c - dx, 0.18)]
        case "mailbox", "lamppost", "scarecrow": return [(c, 0.25)]
        default: return [(c, BuildCatalog.radius(item.id))]
        }
    }

    /// Adds per-item life: fire, smoke, lamps, windmill spin, tree sway.
    private func decorate(id: String, node: SCNNode) {
        switch id {
        case "campfire":
            let point = node.part("FirePoint") ?? { let n = SCNNode(); n.simdPosition = SIMD3(0, 0.2, 0); node.addChildNode(n); return n }()
            point.addParticleSystem(Self.fire())
            let light = SCNLight()
            light.type = .omni
            light.color = UIColor(red: 1, green: 0.62, blue: 0.3, alpha: 1)
            light.attenuationStartDistance = 0.6
            light.attenuationEndDistance = 3.2
            let ln = SCNNode()
            ln.light = light
            ln.simdPosition = SIMD3(0, 0.5, 0)
            point.addChildNode(ln)
            lights.append((light, 14))
            ln.runAction(.repeatForever(.customAction(duration: 1) { n, _ in
                n.simdPosition.y = 0.5 + Float.random(in: -0.04...0.04)
            }))
            fires.append(ln)
        case "cottage":
            if let smoke = node.part("SmokePoint") {
                smoke.addParticleSystem(Self.smoke())
            }
        case "lamppost", "lanterns", "lighthouse", "gazebo":
            let point = node.part("LightPoint") ?? { let n = SCNNode(); n.simdPosition = SIMD3(0, 1.5, 0); node.addChildNode(n); return n }()
            let light = SCNLight()
            light.type = .omni
            light.color = UIColor(red: 1, green: 0.8, blue: 0.5, alpha: 1)
            light.attenuationStartDistance = 0.1
            light.attenuationEndDistance = 2.6
            point.light = light
            lights.append((light, 12))
        default:
            break
        }
    }

    private func playConstruction(_ node: SCNNode, scale: Float) {
        node.simdScale = SIMD3(repeating: 0.01)
        let up = SCNAction.scale(to: CGFloat(scale * 1.18), duration: 0.35)
        up.timingMode = .easeOut
        let down = SCNAction.scale(to: CGFloat(scale * 0.94), duration: 0.14)
        down.timingMode = .easeInEaseOut
        let settle = SCNAction.scale(to: CGFloat(scale), duration: 0.18)
        settle.timingMode = .easeInEaseOut
        node.runAction(.sequence([.wait(duration: 0.15), up, down, settle]))

        let dust = SCNParticleSystem()
        dust.particleImage = Textures.puff
        dust.birthRate = 400
        dust.emissionDuration = 0.08
        dust.loops = false
        dust.emitterShape = SCNTorus(ringRadius: 0.8, pipeRadius: 0.1)
        dust.birthLocation = .surface
        dust.particleLifeSpan = 1.1
        dust.particleVelocity = 1.2
        dust.emittingDirection = SCNVector3(0, 0.3, 0)
        dust.spreadingAngle = 80
        dust.particleSize = 0.35
        dust.particleColor = UIColor(red: 1, green: 0.97, blue: 0.9, alpha: 0.8)
        dust.dampingFactor = 2.5
        dust.isLightingEnabled = false
        let fade = SCNParticlePropertyController(animation: {
            let a = CAKeyframeAnimation()
            a.values = [0.9, 0]
            return a
        }())
        dust.propertyControllers = [.opacity: fade]

        let sparkle = SCNParticleSystem()
        sparkle.particleImage = Textures.sparkle
        sparkle.birthRate = 160
        sparkle.emissionDuration = 0.25
        sparkle.loops = false
        sparkle.emitterShape = SCNCylinder(radius: 0.9, height: 1.5)
        sparkle.birthLocation = .volume
        sparkle.particleLifeSpan = 1.2
        sparkle.particleVelocity = 0.8
        sparkle.emittingDirection = SCNVector3(0, 1, 0)
        sparkle.spreadingAngle = 30
        sparkle.particleSize = 0.09
        sparkle.particleColor = UIColor(red: 1, green: 0.86, blue: 0.45, alpha: 1)
        sparkle.blendMode = .additive
        sparkle.isLightingEnabled = false
        sparkle.propertyControllers = [.opacity: fade]

        let fx = SCNNode()
        fx.simdPosition = node.simdPosition + SIMD3(0, 0.1, 0)
        itemsRoot.addChildNode(fx)
        fx.addParticleSystem(dust)
        fx.addParticleSystem(sparkle)
        fx.runAction(.sequence([.wait(duration: 2.5), .removeFromParentNode()]))
    }

    // MARK: - Build markers

    func setBuildMarkers(_ ids: [String], highlighted: String?) {
        for (id, node) in markers where !ids.contains(id) {
            node.removeFromParentNode()
            markers[id] = nil
        }
        for id in ids where markers[id] == nil {
            guard let item = BuildCatalog.item(id) else { continue }
            let ring = SCNTorus(ringRadius: 0.55, pipeRadius: 0.035)
            let m = SCNMaterial()
            m.lightingModel = .constant
            m.diffuse.contents = UIColor(red: 1, green: 0.9, blue: 0.6, alpha: 1)
            m.emission.contents = UIColor(red: 1, green: 0.8, blue: 0.4, alpha: 1)
            ring.firstMaterial = m
            let node = SCNNode(geometry: ring)
            node.simdPosition = SIMD3(item.slot.x, 0.06, item.slot.y)
            node.runAction(.repeatForever(.sequence([
                .scale(to: 1.12, duration: 0.8), .scale(to: 0.92, duration: 0.8),
            ])))
            markersRoot.addChildNode(node)
            markers[id] = node
        }
        for (id, node) in markers {
            node.opacity = highlighted == nil || highlighted == id ? 1 : 0.35
        }
        markersRoot.simdPosition = islandRoot.simdPosition
    }

    /// Spins the camera so a slot faces the viewer.
    func focus(on slot: SIMD2<Float>) {
        let angle = atan2(slot.x, slot.y)
        var target = angle
        while target - yaw > .pi { target -= 2 * .pi }
        while target - yaw < -.pi { target += 2 * .pi }
        focusYaw = target
    }

    private var focusYaw: Float?
    private var closeUpUntil: CFTimeInterval = 0
    /// Onboarding: keep the camera on the sprout so he can "talk" to the player.
    var companionFocus = false {
        didSet {
            guard companionFocus != oldValue else { return }
            // Step into the open at the front of the island, in view and clear of props.
            sprout.stageSpot = companionFocus ? SIMD2(-0.7, 3.7) : nil
        }
    }
    /// Reports where the sprout's head is on screen (for speech bubbles).
    weak var view: SCNView?
    var onSproutScreen: ((CGPoint) -> Void)?
    private var lastSproutScreen = CGPoint(x: -999, y: -999)
    private let clock = CloudClock()
    /// Shows this text in cloud letters instead of the time (onboarding logo).
    var clockText: String?
    /// Where the 3D clock's centre sits, in view points from the top (nil hides it). Resolved against the
    /// view's size every frame, so it's right from the first frame even if SwiftUI doesn't update again.
    var clockPointY: CGFloat?
    /// Screen-space centre of the 3D clock (0 = top, 1 = bottom), or nil to hide it.
    private var clockScreenY: CGFloat? {
        didSet { clock.node.isHidden = clockScreenY == nil }
    }
    private lazy var critters = CritterSystem(parent: islandRoot)

    // MARK: Adventures

    fileprivate(set) var sproutAway = false

    private func makeBalloon() -> SCNNode {
        if let b = ModelLibrary.node("balloon") {
            b.simdScale = SIMD3(repeating: 2.1)
            b.enumerateHierarchy { n, _ in n.castsShadow = true }
            return b
        }
        // Fallback balloon.
        let root = SCNNode()
        let env = SCNSphere(radius: 0.5)
        env.materials = [Self.pbr(UIColor(red: 0.48, green: 0.8, blue: 0.44, alpha: 1))]
        let e = SCNNode(geometry: env)
        e.simdPosition = SIMD3(0, 1.1, 0)
        e.simdScale = SIMD3(1, 1.15, 1)
        root.addChildNode(e)
        let basket = SCNNode(geometry: SCNBox(width: 0.4, height: 0.25, length: 0.4, chamferRadius: 0.05))
        basket.geometry?.materials = [Self.pbr(UIColor(red: 0.69, green: 0.48, blue: 0.29, alpha: 1))]
        basket.simdPosition = SIMD3(0, 0.12, 0)
        root.addChildNode(basket)
        let seat = SCNNode()
        seat.name = "SeatPoint"
        seat.simdPosition = SIMD3(0, 0.05, 0)
        root.addChildNode(seat)
        root.simdScale = SIMD3(repeating: 2.1)
        return root
    }

    /// Plays the sprout's departure or homecoming in its little balloon.
    func setSproutAway(_ away: Bool, animated: Bool) {
        guard away != sproutAway else { return }
        sproutAway = away
        guard animated else {
            sprout.setAway(away)
            return
        }
        let balloon = makeBalloon()
        let seat = balloon.part("SeatPoint") ?? balloon
        let rider = sprout.passenger()
        rider.simdScale = SIMD3(repeating: 0.8)
        seat.addChildNode(rider)
        itemsRoot.addChildNode(balloon)
        let ground = SIMD2<Float>(sprout.root.simdPosition.x, sprout.root.simdPosition.z)
        if away {
            balloon.simdPosition = SIMD3(ground.x, 0, ground.y)
            balloon.opacity = 0
            sprout.setAway(true)
            let rise = SCNAction.moveBy(x: 3, y: 16, z: -4, duration: 6)
            rise.timingMode = .easeIn
            balloon.runAction(.sequence([
                .fadeIn(duration: 0.3),
                .wait(duration: 0.8),
                .group([rise, .rotateBy(x: 0, y: 1.2, z: 0, duration: 6), .sequence([.wait(duration: 4.5), .fadeOut(duration: 1.5)])]),
                .removeFromParentNode(),
            ]))
        } else {
            let land = sprout.bedSpot + SIMD2(0.4, 0.5)
            balloon.simdPosition = SIMD3(land.x - 3, 16, land.y + 4)
            let descend = SCNAction.move(to: SCNVector3(land.x, 0, land.y), duration: 5)
            descend.timingMode = .easeOut
            balloon.runAction(.sequence([
                .group([descend, .rotateBy(x: 0, y: -1.2, z: 0, duration: 5)]),
                .run { [weak self] _ in
                    Task { @MainActor in
                        rider.removeFromParentNode()
                        self?.sprout.setAway(false, landingAt: land + SIMD2(0.6, 0.3))
                        self?.sprout.celebrate(at: CACurrentMediaTime())
                    }
                },
                .wait(duration: 1.2),
                .group([.moveBy(x: -2, y: 14, z: -3, duration: 5), .sequence([.wait(duration: 3.5), .fadeOut(duration: 1.5)])]),
                .removeFromParentNode(),
            ]))
        }
    }

    /// Swoops the camera in on the sprout for a few seconds (after a pet).
    func closeUpOnSprout(for seconds: CFTimeInterval = 5) {
        closeUpUntil = CACurrentMediaTime() + seconds
        focusYaw = nil
    }

    // MARK: - Frame loop

    @objc private func frame(_ link: CADisplayLink) {
        let t = link.timestamp
        let begin = CACurrentMediaTime()
        defer { perf?.mainFrame(at: t, work: CACurrentMediaTime() - begin) }
        perf?.lap(nil)
        let dt = Float(lastFrame == 0 ? 1.0 / 60 : min(0.1, t - lastFrame))
        lastFrame = t

        // Camera inertia + focus.
        if let f = focusYaw, !isInteracting {
            yaw += (f - yaw) * min(1, dt * 3)
            if abs(f - yaw) < 0.002 { focusYaw = nil }
        } else if !isInteracting {
            yaw += yawVelocity * dt
            yawVelocity *= pow(0.04, dt)
        }
        if isInteracting { focusYaw = nil }
        idleSway = UIAccessibility.isReduceMotionEnabled ? 0 : sin(Float(t) * 0.25) * 0.03
        orbit.simdEulerAngles = SIMD3(0, yaw + idleSway, 0)
        let closeUp = t < closeUpUntil && !bedridden
        let onTrip = tripVisible && !bedridden && !closeUp
        let onFarm = focus == .farm && !closeUp && !bedridden && !onTrip
        var onIsle: SCNNode?
        if case .isle(let n) = focus, !closeUp, !bedridden, !onTrip { onIsle = isleRoots[n] }
        let companion = companionFocus && !bedridden && !onTrip && !closeUp
        let wantDistance = bedridden ? min(targetDistance, 8.5) : closeUp ? Float(10) : companion ? Float(12) : onTrip ? min(targetDistance, 18)
            : onIsle != nil ? min(targetDistance, 14) : (onFarm ? min(targetDistance, 17) : targetDistance)
        distance += (wantDistance * cinemaZoom - distance) * min(1, dt * (closeUp ? 2.5 : 1.8))
        cameraNode.simdPosition = SIMD3(0, 0, distance)
        floatIslands(t)
        let focusPoint = bedridden ? roomCenter : onTrip ? tripRoot.presentation.simdConvertPosition(tripCenter, to: nil) : closeUp ? SIMD3(sprout.root.simdPosition.x, islandY + 0.2, sprout.root.simdPosition.z)
            // Look a little below him so he sits in the upper part of the screen, above the cards.
            : companion ? SIMD3(sprout.root.simdPosition.x, islandY - 2.2, sprout.root.simdPosition.z)
            : onFarm ? farmRoot.simdPosition + SIMD3(0, -0.4, 0)
            : onIsle.map { $0.simdWorldPosition + SIMD3(0, -0.5, 0) } ?? SIMD3<Float>(0, -0.6, 0)
        sunLightNode.simdPosition = orbit.simdPosition + lightDirection * 40
        sunLightNode.simdLook(at: orbit.simdPosition)
        weatherRoot.simdPosition = SIMD3(orbit.simdPosition.x, 13, orbit.simdPosition.z)
        orbit.simdPosition += (focusPoint - orbit.simdPosition) * min(1, dt * 2.2)
        cameraNode.camera?.focusDistance = CGFloat(distance)
        cameraNode.camera?.fStop = closeUp ? 1.4 : 2.2
        if cameraNode.camera?.wantsDepthOfField != closeUp { cameraNode.camera?.wantsDepthOfField = closeUp }
        perf?.lap("camera")
        PerfProbe.measure("critters", threshold: 2) { critters.update(t: t, dt: dt) }
        perf?.lap("critters")
        if let view, view.bounds.height > 0 {
            setAspect(view.bounds.width / view.bounds.height)
            let y = clockPointY.map { $0 / view.bounds.height }
            if y != clockScreenY { clockScreenY = y }
        }
        if let clockY = clockScreenY, let sky {
            if clock.node.parent == nil { cameraNode.addChildNode(clock.node) }
            if let clockText { clock.show(text: clockText) } else { clock.show(sky.date) }
            let vfov = 2 * atan(tan(Float(horizontalFOV) * .pi / 360) / Float(aspect))
            clock.update(t: t, depth: distance, verticalFOV: vfov, screenY: clockY, night: 1 - sky.daylight)
        }
        perf?.lap("clock")
        sprout.cameraYaw = yaw
        if let sky, abs(yawVelocity) > 0.0001 || isInteracting || focusYaw != nil {
            positionCelestials(sky)
        }

        perf?.lap("celestials")
        // Float rocks.
        for (i, (rock, base)) in floatRocks.enumerated() {
            rock.simdPosition = base + SIMD3(0, sin(Float(t) * 0.7 + Float(i) * 2) * 0.25, 0)
            rock.simdEulerAngles.y = Float(t) * 0.05 * Float(i + 1)
        }

        // Wind-driven life.
        let wind = sprout.wind
        for (id, node) in items {
            let partName: String
            switch id {
            case "treeRound", "treeBlossom", "pine": partName = "Canopy"
            case "windmill": partName = "Blades"
            case "swing": partName = "Seat"
            case "mailbox": partName = "Flag"
            default: continue
            }
            if animatedParts[id] == nil { animatedParts[id] = .some(node.part(partName)) }
            guard let part = animatedParts[id] ?? nil else { continue }
            switch id {
            case "treeRound", "treeBlossom", "pine":
                let k: Float = id == "pine" ? 0.5 : 1
                part.simdEulerAngles = SIMD3(sin(Float(t) * 1.1 + Float(id.count)) * 0.012 * (1 + wind * 3) * k,
                                             0, sin(Float(t) * (0.9 + wind)) * (0.02 + 0.05 * wind) * k)
            case "windmill":
                part.simdEulerAngles.z -= dt * (0.4 + wind * 3.2)
            case "swing":
                part.simdEulerAngles.x = sin(Float(t) * 1.7) * (0.05 + wind * 0.25)
            default:
                part.simdEulerAngles.x = sin(Float(t) * 3) * 0.05 * wind
            }
        }

        perf?.lap("rocks+items")
        // Lightning.
        if let sky, sky.weather.kind == .thunder {
            if nextLightning == 0 { nextLightning = t + Double.random(in: 3...8) }
            if t > nextLightning {
                nextLightning = t + Double.random(in: 5...13)
                flashUntil = t + 0.35
            }
            let ambient = ambientNode.light!
            if t < flashUntil {
                let k = (flashUntil - t) / 0.35
                ambient.intensity = CGFloat(sky.palette.ambientIntensity) * lightScale.ambient + CGFloat(1800 * (k > 0.5 ? 1 : k * 0.6))
            } else {
                ambient.intensity = CGFloat(lastPalette?.ambientIntensity ?? 600) * lightScale.ambient
            }
        }

        perf?.lap("lightning")
        PerfProbe.measure("sprout", threshold: 2) { sprout.update(t: t, daylight: sky?.daylight ?? 1) }
        perf?.lap("sprout")
        if let onSproutScreen, let view, !sprout.root.isHidden {
            let head = sprout.root.simdWorldPosition + SIMD3(0, 1.25, 0)
            let p = view.projectPoint(SCNVector3(head))
            let pt = CGPoint(x: CGFloat(p.x), y: CGFloat(p.y))
            if abs(pt.x - lastSproutScreen.x) + abs(pt.y - lastSproutScreen.y) > 1.5 {
                lastSproutScreen = pt
                onSproutScreen(pt)
            }
        }
        markersRoot.simdPosition = islandRoot.simdPosition
        if bedridden && sprout.bedridden {
            sprout.root.simdPosition = roomSproutPosition
        } else {
            sprout.root.simdPosition.y = islandY + sprout.liftY
        }
        perf?.lap("tail")
    }


    // MARK: - Neglect visuals

    private(set) var gloom = 0
    private var dusty = false

    /// 2+ missed mornings: the light dims and a gloomy little cloud follows Sprig.
    func setGloom(_ level: Int) {
        guard level != gloom else { return }
        gloom = level
        sprout.gloomy = level >= 2
        if let sky { apply(sky: sky, force: true) }
    }

    // MARK: Home interior (tent or cottage bedroom)

    enum Occupant: Equatable { case none, sleeping, sick }

    private var room: SCNNode?
    private var roomHome: String?
    /// The camera is inside Sprig's home.
    private(set) var bedridden = false
    private var occupant: Occupant = .none
    private var roomSproutPosition = SIMD3<Float>(0, 0, 0)
    private var roomWindowMaterials: [SCNMaterial] = []
    private var roomLampMaterials: [SCNMaterial] = []
    private var roomCenter = SIMD3<Float>(0, 1, 0)
    static let roomPosition = SIMD3<Float>(-140, 0, 0)
    private var appliedDecor = InteriorDecor()
    private var decorNodes: [SCNNode] = []
    private var originalColors: [ObjectIdentifier: Any] = [:]
    private var roomMaterials: [SCNMaterial] = []

    /// Places bought furniture into the room's slots and applies wall/floor/canvas styles.
    private func applyDecor() {
        guard let r = room else { return }
        decorNodes.forEach { $0.removeFromParentNode() }
        decorNodes = []
        for (slot, itemID) in appliedDecor.layout {
            guard let anchor = r.part(slot), let item = InteriorCatalog.item(itemID) else { continue }
            let node = ModelLibrary.node(item.model) ?? Self.fallbackFurniture(item)
            anchor.addChildNode(node)
            decorNodes.append(node)
            if let lampPart = node.part("LightPoint") ?? (item.id == "floorlamp" ? node : nil), item.id == "floorlamp" {
                let l = SCNLight()
                l.type = .omni
                l.color = UIColor(red: 1, green: 0.8, blue: 0.55, alpha: 1)
                l.intensity = 8
                l.attenuationEndDistance = 2.2
                let ln = SCNNode()
                ln.light = l
                ln.simdPosition = SIMD3(0, 1.4, 0)
                lampPart.addChildNode(ln)
            }
        }
        // Surface styles: recolour named materials (restoring originals for default styles).
        var targets: [String: UInt32] = [:]
        for id in appliedDecor.styles {
            if let st = InteriorCatalog.style(id) { targets.merge(st.colors) { $1 } }
        }
        let styled = Set(InteriorCatalog.styles.flatMap { $0.colors.keys })
        for m in roomMaterials {
            guard let name = m.name, styled.contains(name) else { continue }
            let key = ObjectIdentifier(m)
            if originalColors[key] == nil { originalColors[key] = m.diffuse.contents }
            if let hex = targets[name] {
                m.diffuse.contents = UIColor(red: CGFloat((hex >> 16) & 0xFF) / 255, green: CGFloat((hex >> 8) & 0xFF) / 255,
                                             blue: CGFloat(hex & 0xFF) / 255, alpha: 1)
            } else if let orig = originalColors[key] {
                m.diffuse.contents = orig
            }
        }
    }

    private static func fallbackFurniture(_ item: FurnitureItem) -> SCNNode {
        let root = SCNNode()
        let geo: SCNGeometry = item.kind == .wall
            ? SCNBox(width: 0.6, height: 0.5, length: 0.05, chamferRadius: 0.02)
            : SCNBox(width: 0.7, height: 0.7, length: 0.7, chamferRadius: 0.12)
        geo.materials = [pbr(UIColor(red: 0.9, green: 0.72, blue: 0.5, alpha: 1))]
        let n = SCNNode(geometry: geo)
        n.simdPosition = item.kind == .wall ? SIMD3(0, 0, 0.03) : SIMD3(0, 0.35, 0)
        root.addChildNode(n)
        return root
    }

    /// Front door on the island (where Sprig goes in and out).
    let homeDoor = SIMD2<Float>(0.2, 0.95)

    /// `home` is "tent" or "cottage"; `visible` puts the camera inside; `occupant` is who's in bed.
    func setInterior(home: String, visible: Bool, occupant newOccupant: Occupant, decor: InteriorDecor = InteriorDecor()) {
        let needsRoom = visible && (room == nil || roomHome != home)
        let decorChanged = decor != appliedDecor
        appliedDecor = decor
        if needsRoom { buildRoom(home) } else if decorChanged, room != nil { applyDecor() }
        // Built once, then just hidden: rebuilding the room on every visit caused a hitch.
        room?.isHidden = !visible
        let changedView = visible != bedridden
        bedridden = visible
        sprout.viewingInside = visible
        if changedView {
            setWorldHidden(visible)
            if visible {
                orbit.simdPosition = roomCenter
                distance = 8
                yaw = 0.45
            } else {
                orbit.simdPosition = SIMD3(0, -0.6, 0)
                distance = targetDistance
                yaw = 0
                yawVelocity = 0
            }
            if let sky { apply(sky: sky, force: true) }
        }

        // Who's where.
        let oldOccupant = occupant
        occupant = newOccupant
        switch newOccupant {
        case .none:
            if sprout.bedridden { sprout.setInBed(false, at: .zero, height: 0, yaw: 0) }
            if oldOccupant != .none { sprout.comeOutdoors(door: homeDoor) }
        case .sleeping, .sick:
            if visible {
                sprout.setInBed(true, sick: newOccupant == .sick, at: SIMD2(roomSproutPosition.x, roomSproutPosition.z), height: 0, yaw: 0)
            } else if sprout.bedridden {
                sprout.setInBed(false, at: .zero, height: 0, yaw: 0)
                sprout.setIndoorsNow(door: homeDoor)
            } else {
                sprout.walkIndoors(door: homeDoor)
            }
        }
    }

    private func buildRoom(_ home: String) {
        room?.removeFromParentNode()
        let r = ModelLibrary.node(home == "cottage" ? "bedroom" : "tent_interior")
            ?? ModelLibrary.node("bedroom") ?? Self.fallbackRoom()
        r.simdPosition = Self.roomPosition
        scene.rootNode.addChildNode(r)
        room = r
        roomHome = home
        let origin = r.part("SproutOrigin").map { $0.simdPosition } ?? SIMD3(-0.3, 0.47, -1.1)
        roomSproutPosition = r.simdConvertPosition(origin, to: nil)
        roomCenter = r.simdConvertPosition(r.part("RoomCenter")?.simdPosition ?? SIMD3(0, 1, -0.4), to: nil)
        roomWindowMaterials = []
        roomLampMaterials = []
        roomMaterials = []
        r.enumerateHierarchy { n, _ in
            for m in n.geometry?.materials ?? [] {
                if m.name == "GlowWindow" { roomWindowMaterials.append(m) }
                if m.name == "GlowLamp" { roomLampMaterials.append(m) }
                if !roomMaterials.contains(where: { $0 === m }) { roomMaterials.append(m) }
            }
        }
        decorNodes = []
        applyDecor()
        let lamp = SCNLight()
        lamp.type = .omni
        lamp.color = UIColor(red: 1, green: 0.8, blue: 0.58, alpha: 1)
        lamp.intensity = 9
        lamp.attenuationStartDistance = 0.1
        lamp.attenuationEndDistance = 2.6
        let lampNode = SCNNode()
        lampNode.light = lamp
        lampNode.simdPosition = r.part("LampLight")?.simdPosition ?? SIMD3(0.9, 1.1, -1.5)
        r.addChildNode(lampNode)
        if occupant != .none {
            sprout.setInBed(true, sick: occupant == .sick, at: SIMD2(roomSproutPosition.x, roomSproutPosition.z), height: 0, yaw: 0)
        }
    }

    private func setWorldHidden(_ hidden: Bool) {
        islandRoot.isHidden = hidden
        farmRoot.isHidden = hidden
        weatherRoot.isHidden = hidden
        markersRoot.isHidden = hidden
        skyPlane.isHidden = hidden
        starsNode.isHidden = hidden
        sunNode.isHidden = hidden
        moonNode.isHidden = hidden
        scene.background.contents = hidden ? UIColor(red: 0.2, green: 0.16, blue: 0.17, alpha: 1) : nil
    }

    private static func fallbackRoom() -> SCNNode {
        let root = SCNNode()
        let floor = SCNBox(width: 4.5, height: 0.1, length: 4.5, chamferRadius: 0.02)
        floor.materials = [pbr(UIColor(red: 0.72, green: 0.52, blue: 0.34, alpha: 1))]
        let f = SCNNode(geometry: floor)
        f.simdPosition = SIMD3(0, -0.05, 0)
        root.addChildNode(f)
        for (w, pos, rot) in [(SCNBox(width: 4.5, height: 2.8, length: 0.12, chamferRadius: 0), SIMD3<Float>(0, 1.4, -2.25), Float(0)),
                              (SCNBox(width: 4.5, height: 2.8, length: 0.12, chamferRadius: 0), SIMD3<Float>(-2.25, 1.4, 0), Float.pi / 2)] {
            w.materials = [pbr(UIColor(red: 0.96, green: 0.91, blue: 0.82, alpha: 1))]
            let n = SCNNode(geometry: w)
            n.simdPosition = pos
            n.simdEulerAngles = SIMD3(0, rot, 0)
            root.addChildNode(n)
        }
        if let bed = ModelLibrary.node("sickbed") {
            bed.simdPosition = SIMD3(-0.3, 0, -1.1)
            bed.part("Quilt")?.simdScale = SIMD3(1, 0.42, 1)
            root.addChildNode(bed)
            if let lie = bed.part("LiePoint") {
                let o = SCNNode()
                o.name = "SproutOrigin"
                o.simdPosition = bed.simdPosition + lie.simdPosition + SIMD3(0, 0.02, -0.5)
                root.addChildNode(o)
            }
        }
        return root
    }

    /// In debt: the island looks run-down (dusty, washed-out colours).
    func setDusty(_ on: Bool) {
        guard on != dusty else { return }
        dusty = on
        let tint = on ? UIColor(red: 0.74, green: 0.7, blue: 0.64, alpha: 1) : UIColor.white
        for m in ModelLibrary.rimMaterials { m.multiply.contents = tint }
    }

    // MARK: - Vacation view

    private let tripRoot = SCNNode()
    private var tripID: String?
    private var tripSprout: SCNNode?
    private var tripPoints: [SIMD3<Float>] = []
    private var tripYaws: [Float] = []
    private var tripCenter = SIMD3<Float>(0, 1, 0)
    private var tripActivity = -1
    private(set) var tripVisible = false
    static let tripPosition = SIMD3<Float>(-12, 3, 115)

    /// Shows Sprig's vacation destination far across the sky, with him doing activity `activity`
    /// (0 = at his stay, 1–3 = ActivityA/B/C).
    func setTrip(destination: String?, visible: Bool, activity: Int) {
        tripVisible = visible && destination != nil
        if destination != tripID {
            tripRoot.childNodes.forEach { $0.removeFromParentNode() }
            tripSprout = nil
            tripActivity = -1
            tripID = destination
            guard let destination else { tripRoot.removeFromParentNode(); return }
            let model = ModelLibrary.node("trip_\(destination)") ?? Self.fallbackFarm()
            tripRoot.addChildNode(model)
            tripRoot.simdPosition = Self.tripPosition
            if tripRoot.parent == nil {
                scene.rootNode.addChildNode(tripRoot)
                let bob = SCNAction.moveBy(x: 0, y: 0.2, z: 0, duration: 4.2)
                bob.timingMode = .easeInEaseOut
                tripRoot.runAction(.repeatForever(.sequence([bob, bob.reversed()])))
            }
            let names = ["StayPoint", "ActivityA", "ActivityB", "ActivityC"]
            tripPoints = names.enumerated().map { i, n in
                model.part(n).map { $0.simdConvertPosition(.zero, to: tripRoot) } ?? SIMD3(Float(i - 1) * 1.3, 0, 1.2)
            }
            tripYaws = names.map { n in
                guard let p = model.part(n) else { return 0 }
                let fwd = p.simdConvertVector(SIMD3(0, 0, 1), to: tripRoot)
                return atan2(fwd.x, fwd.z)
            }
            tripCenter = model.part("IslandCenter").map { $0.simdConvertPosition(.zero, to: tripRoot) } ?? SIMD3(0, 1, 0)
            let visitor = SCNNode()
            visitor.addChildNode(sprout.passenger())
            visitor.simdScale = SIMD3(repeating: 2.1)
            visitor.simdPosition = tripPoints[0]
            tripRoot.addChildNode(visitor)
            tripSprout = visitor
            let breathe = SCNAction.customAction(duration: 1.6) { n, t in
                let k = sin(Float(t) / 1.6 * 2 * .pi)
                n.childNodes.first?.simdScale = SIMD3(1 + k * 0.02, 1 - k * 0.03, 1 + k * 0.02)
            }
            visitor.runAction(.repeatForever(breathe), forKey: "breathe")
        }
        guard let visitor = tripSprout, !tripPoints.isEmpty else { return }
        let a = max(0, min(activity, tripPoints.count - 1))
        if a != tripActivity {
            let first = tripActivity == -1
            tripActivity = a
            let target = tripPoints[a]
            visitor.removeAction(forKey: "move")
            if first {
                visitor.simdPosition = target
                visitor.simdEulerAngles.y = tripYaws[a]
            } else {
                let yaw = tripYaws[a]
                visitor.runAction(.sequence([
                    hopMove(visitor, to: target, duration: 1.4),
                    .customAction(duration: 0.3) { n, t in n.simdEulerAngles.y += (yaw - n.simdEulerAngles.y) * Float(t / 0.3) },
                ]), forKey: "move")
            }
        }
    }

    /// The balloon touching down at the vacation spot: plays the first time you look in just after they set off.
    func playTripArrival() {
        guard let visitor = tripSprout, !tripPoints.isEmpty else { return }
        tripRoot.childNode(withName: "TripBalloon", recursively: false)?.removeFromParentNode()
        let balloon = makeBalloon()
        balloon.name = "TripBalloon"
        let seat = balloon.part("SeatPoint") ?? balloon
        let rider = sprout.passenger()
        rider.simdScale = SIMD3(repeating: 0.8)
        seat.addChildNode(rider)
        tripRoot.addChildNode(balloon)
        let land = tripPoints[0] + SIMD3<Float>(0.6, 0, 0.5)
        let a = max(0, min(tripActivity, tripPoints.count - 1))
        let settle = tripPoints[a]
        let yaw = tripYaws[a]
        visitor.removeAction(forKey: "move")
        visitor.opacity = 0
        balloon.simdPosition = land + SIMD3(-3, 14, 4)
        let descend = SCNAction.move(to: SCNVector3(land.x, land.y, land.z), duration: 4.5)
        descend.timingMode = .easeOut
        balloon.runAction(.sequence([
            .wait(duration: 1.0),   // let the camera get there first
            .group([descend, .rotateBy(x: 0, y: -1.2, z: 0, duration: 4.5)]),
            .run { [weak self] _ in
                Task { @MainActor in
                    guard let self else { return }
                    rider.removeFromParentNode()
                    visitor.simdPosition = land
                    visitor.opacity = 1
                    visitor.runAction(.sequence([
                        self.hopMove(visitor, to: settle, duration: 1.2),
                        .customAction(duration: 0.3) { n, t in n.simdEulerAngles.y += (yaw - n.simdEulerAngles.y) * Float(t / 0.3) },
                    ]), forKey: "move")
                }
            },
            .wait(duration: 1.2),
            .group([.moveBy(x: -2, y: 14, z: -3, duration: 5), .sequence([.wait(duration: 3.5), .fadeOut(duration: 1.5)])]),
            .removeFromParentNode(),
        ]))
    }

    // MARK: - Farm Island (Sprig's workplace)

    enum Focus: Equatable { case home, farm, isle(Int) }
    var focus: Focus = .home
    private var lightDirection = SIMD3<Float>(0.3, 0.8, 0.3)
    private let farmRoot = SCNNode()
    private var plotAnchors: [SCNNode] = []
    private var cropNodes: [Int: (key: String, node: SCNNode)] = [:]
    private var dockPoint = SIMD3<Float>(0, 0, 2.8)
    private var workSpot = SIMD3<Float>(1.2, 0, 1.2)
    private var farmWorker: SCNNode?
    private var parkedBalloon: SCNNode?
    private(set) var isCommuting = false
    private var commuteTask: Task<Void, Never>?
    private var commuteFinish: (() -> Void)?
    private var wantAtWork = false
    private var displayedPlots: [PlotState] = []
    static let farmPosition = SIMD3<Float>(15, 2.5, -36)

    private func buildFarm() {
        let model = ModelLibrary.node("farm_island") ?? Self.fallbackFarm()
        farmRoot.addChildNode(model)
        farmRoot.simdPosition = Self.farmPosition
        farmRoot.simdEulerAngles = SIMD3(0, -0.35, 0)
        scene.rootNode.addChildNode(farmRoot)
        farmBaseY = farmRoot.simdPosition.y
        plotAnchors = (1...6).compactMap { model.part("Plot\($0)") }
        if plotAnchors.count < 6 {
            plotAnchors = (0..<6).map { i in
                let n = SCNNode()
                n.simdPosition = SIMD3(Float(i % 3 - 1) * 1.2, 0.02, i < 3 ? 1.0 : -0.3)
                model.addChildNode(n)
                return n
            }
        }
        if let d = model.part("BalloonDock") { dockPoint = d.simdPosition }
        if let w = model.part("WorkSpot") { workSpot = w.simdPosition }
    }

    /// Shows each plot's crop at its growth stage (wilted crops droop; dead ones wither).
    func setPlots(_ plots: [PlotState], overrideRipe: [Int: String] = [:]) {
        displayedPlots = plots
        for i in 0..<plotAnchors.count {
            let anchor = plotAnchors[i]
            let plot = i < plots.count ? plots[i] : nil
            var cropID = plot?.crop
            var stage = plot?.visualStage ?? 0
            var dead = plot?.dead ?? false
            var wilted = plot?.wilted ?? false
            if let ripe = overrideRipe[i] {
                cropID = ripe
                stage = 3
                dead = false
                wilted = false
            }
            let key = cropID.map { "\($0)-\(stage)-\(dead)-\(wilted)" } ?? "empty"
            if cropNodes[i]?.key == key { continue }
            cropNodes[i]?.node.removeFromParentNode()
            cropNodes[i] = nil
            guard let cropID else { continue }
            let node = ModelLibrary.node("crop_\(cropID)") ?? Self.fallbackCrop()
            let parts = ["Stage1", "Stage2", "Ripe", "Withered"]
            let visible = dead ? "Withered" : stage >= 3 ? "Ripe" : stage == 2 ? "Stage2" : "Stage1"
            for name in parts { node.part(name)?.isHidden = name != visible }
            if node.part("Ripe") == nil {   // fallback geometry: scale by stage
                node.simdScale = SIMD3(repeating: dead ? 0.5 : 0.35 + Float(stage) * 0.22)
            }
            if wilted {
                node.simdScale.y *= 0.8
                node.simdEulerAngles.x = 0.18
            }
            anchor.addChildNode(node)
            cropNodes[i] = (key, node)
        }
    }

    /// Where Sprig is today: at the farm (worker visible there) or at home.
    func setAtWork(_ atWork: Bool, animated: Bool) {
        wantAtWork = atWork
        guard !isCommuting else { return }
        if atWork {
            placeWorker()
            sprout.setAway(true)
        } else if farmWorker != nil {
            farmWorker?.removeFromParentNode()
            farmWorker = nil
            parkedBalloon?.removeFromParentNode()
            parkedBalloon = nil
            if !sproutAway {
                if animated {
                    sproutAway = true
                    setSproutAway(false, animated: true)   // balloon homecoming
                } else {
                    sprout.setAway(false)
                }
            }
        }
    }

    private func placeWorker() {
        let farmModel = farmRoot.childNodes.first ?? farmRoot
        if parkedBalloon == nil {
            let b = makeBalloon()
            b.simdPosition = dockPoint
            farmModel.addChildNode(b)
            parkedBalloon = b
        }
        guard farmWorker == nil else { return }
        let worker = SCNNode()
        let body = sprout.passenger()
        worker.addChildNode(body)
        worker.simdScale = SIMD3(repeating: 2.1)
        worker.simdPosition = workSpot
        farmModel.addChildNode(worker)
        farmWorker = worker
        wanderWorker()
    }

    /// A gentle work loop: hop between plots, pause, look busy.
    private func wanderWorker() {
        guard let worker = farmWorker else { return }
        let targets = plotAnchors.map { $0.simdPosition + SIMD3(0.55, 0, 0.45) } + [workSpot]
        var steps: [SCNAction] = []
        for t in targets.shuffled().prefix(4) {
            steps.append(hopMove(worker, to: t))
            steps.append(.wait(duration: Double.random(in: 1.2...2.5)))
        }
        worker.runAction(.sequence(steps)) { [weak self] in
            Task { @MainActor in self?.wanderWorker() }
        }
    }

    private final class StartBox { var start: SIMD3<Float>? }

    private func hopMove(_ node: SCNNode, to target: SIMD3<Float>, duration: TimeInterval = 0.9) -> SCNAction {
        let box = StartBox()
        return .customAction(duration: duration) { n, elapsed in
            let start = box.start ?? n.simdPosition
            if box.start == nil { box.start = start }
            let k = Float(elapsed / duration)
            let p = simd_mix(start, target, SIMD3(repeating: k))
            let hop = abs(sin(k * .pi * 3)) * 0.12
            n.simdPosition = SIMD3(p.x, target.y + hop, p.z)
            let d = target - start
            if simd_length(SIMD2(d.x, d.z)) > 0.01 { n.simdEulerAngles.y = atan2(d.x, d.z) }
        }
    }

    /// The morning commute: balloon from home to the Farm Island, harvest pops, watering, then work.
    func playCommute(harvest: [(Int, String)], plots: [PlotState], completion: @escaping () -> Void) {
        commuteTask?.cancel()
        isCommuting = true
        commuteFinish = completion
        var ripe: [Int: String] = [:]
        for (i, c) in harvest { ripe[i] = c }
        setPlots(plots, overrideRipe: ripe)
        let finalPlots = plots
        commuteTask = Task { @MainActor [weak self] in
            guard let self else { return }
            let t0 = CACurrentMediaTime()
            self.sprout.celebrate(at: t0)
            try? await Task.sleep(for: .seconds(1.1))
            guard !Task.isCancelled else { return }
            // Take off from home.
            let balloon = self.makeBalloon()
            let seat = balloon.part("SeatPoint") ?? balloon
            let rider = self.sprout.passenger()
            rider.simdScale = SIMD3(repeating: 0.8)
            seat.addChildNode(rider)
            let startLocal = SIMD3(self.sprout.root.simdPosition.x, 0, self.sprout.root.simdPosition.z)
            let start = self.islandRoot.simdConvertPosition(startLocal, to: nil)
            balloon.simdPosition = start
            self.scene.rootNode.addChildNode(balloon)
            self.sprout.setAway(true)
            let farmModel = self.farmRoot.childNodes.first ?? self.farmRoot
            let flight: TimeInterval = 4.2
            balloon.runAction(.customAction(duration: flight) { n, elapsed in
                let end = farmModel.simdConvertPosition(self.dockPoint, to: nil)
                let k = Float(elapsed / flight)
                let e = k * k * (3 - 2 * k)
                let mid = (start + end) / 2 + SIMD3(0, 9, 0)
                let a = simd_mix(start, mid, SIMD3(repeating: e)), b = simd_mix(mid, end, SIMD3(repeating: e))
                n.simdPosition = simd_mix(a, b, SIMD3(repeating: e))
                n.simdEulerAngles.y = e * 1.4
            }, completionHandler: nil)
            try? await Task.sleep(for: .seconds(1.3))
            self.focus = .farm
            try? await Task.sleep(for: .seconds(flight - 1.1))
            guard !Task.isCancelled else { return }
            // Land: park the balloon, Sprig hops out and gets to work.
            balloon.removeFromParentNode()
            self.placeWorker()
            SoundService.shared.play(.tap)
            try? await Task.sleep(for: .seconds(0.4))
            for (i, _) in harvest {
                guard !Task.isCancelled, let worker = self.farmWorker, i < self.plotAnchors.count else { break }
                worker.removeAllActions()
                worker.runAction(self.hopMove(worker, to: self.plotAnchors[i].simdPosition + SIMD3(0.55, 0, 0.45), duration: 0.5), completionHandler: nil)
                try? await Task.sleep(for: .seconds(0.55))
                self.popCrop(at: i)
                try? await Task.sleep(for: .seconds(0.3))
            }
            // Water everything still growing.
            for (i, p) in finalPlots.enumerated() where p.crop != nil && !p.dead && i < self.plotAnchors.count {
                self.water(at: i)
            }
            if finalPlots.contains(where: { $0.crop != nil }) { SoundService.shared.play(.tap, rate: 1.3) }
            try? await Task.sleep(for: .seconds(1.2))
            guard !Task.isCancelled else { return }
            self.endCommute()
        }
    }

    /// Jumps to the end of the commute.
    func skipCommute() {
        guard isCommuting else { return }
        commuteTask?.cancel()
        endCommute()
    }

    private func endCommute() {
        isCommuting = false
        setPlots(displayedPlots)
        if wantAtWork { placeWorker(); sprout.setAway(true) }
        if let w = farmWorker, w.actionKeys.isEmpty { wanderWorker() }
        let done = commuteFinish
        commuteFinish = nil
        done?()
    }

    private func popCrop(at i: Int) {
        guard let entry = cropNodes[i] else { return }
        let node = entry.node
        cropNodes[i] = nil
        let up = SCNAction.group([.scale(by: 1.35, duration: 0.18), .moveBy(x: 0, y: 0.5, z: 0, duration: 0.18)])
        up.timingMode = .easeOut
        let fly = SCNAction.group([.moveBy(x: 0, y: 1.2, z: 0, duration: 0.4), .scale(to: 0.01, duration: 0.4), .fadeOut(duration: 0.4)])
        node.runAction(.sequence([up, fly, .removeFromParentNode()]))
        let fx = SCNNode()
        fx.simdPosition = SIMD3(0, 0.6, 0)
        plotAnchors[i].addChildNode(fx)
        fx.addParticleSystem(Self.coinBurst())
        fx.runAction(.sequence([.wait(duration: 2), .removeFromParentNode()]))
        SoundService.shared.play(.coin, rate: Float.random(in: 0.95...1.1))
    }

    private func water(at i: Int) {
        let ps = SCNParticleSystem()
        ps.particleImage = Textures.raindrop
        ps.birthRate = 120
        ps.emissionDuration = 0.35
        ps.loops = false
        ps.emitterShape = SCNBox(width: 0.8, height: 0.05, length: 0.8, chamferRadius: 0)
        ps.birthLocation = .volume
        ps.particleLifeSpan = 0.5
        ps.particleVelocity = 2
        ps.emittingDirection = SCNVector3(0, -1, 0)
        ps.particleSize = 0.04
        ps.stretchFactor = 0.06
        ps.particleColor = UIColor(red: 0.6, green: 0.85, blue: 1, alpha: 0.85)
        ps.isLightingEnabled = false
        let fx = SCNNode()
        fx.simdPosition = SIMD3(0, 1.1, 0)
        plotAnchors[i].addChildNode(fx)
        fx.addParticleSystem(ps)
        fx.runAction(.sequence([.wait(duration: 1.5), .removeFromParentNode()]))
    }

    private static func coinBurst() -> SCNParticleSystem {
        let ps = SCNParticleSystem()
        ps.particleImage = Textures.symbol("dollarsign.circle.fill", color: UIColor(red: 1, green: 0.8, blue: 0.25, alpha: 1))
        ps.birthRate = 90
        ps.emissionDuration = 0.12
        ps.loops = false
        ps.particleLifeSpan = 1.1
        ps.particleSize = 0.16
        ps.particleVelocity = 2.2
        ps.particleVelocityVariation = 0.6
        ps.emittingDirection = SCNVector3(0, 1, 0)
        ps.spreadingAngle = 35
        ps.acceleration = SCNVector3(0, -3.5, 0)
        ps.isLightingEnabled = false
        ps.blendMode = .alpha
        return ps
    }

    private static func fallbackFarm() -> SCNNode {
        let root = SCNNode()
        let top = SCNCylinder(radius: 4.5, height: 0.5)
        top.materials = [pbr(UIColor(red: 0.55, green: 0.78, blue: 0.4, alpha: 1))]
        let t = SCNNode(geometry: top)
        t.simdPosition = SIMD3(0, -0.25, 0)
        root.addChildNode(t)
        let cone = SCNCone(topRadius: 4.4, bottomRadius: 0.4, height: 4)
        cone.materials = [pbr(UIColor(red: 0.66, green: 0.47, blue: 0.31, alpha: 1))]
        let c = SCNNode(geometry: cone)
        c.simdPosition = SIMD3(0, -2.5, 0)
        root.addChildNode(c)
        for i in 0..<6 {
            let soil = SCNBox(width: 0.95, height: 0.08, length: 0.95, chamferRadius: 0.03)
            soil.materials = [pbr(UIColor(red: 0.4, green: 0.27, blue: 0.18, alpha: 1))]
            let n = SCNNode(geometry: soil)
            n.name = "Plot\(i + 1)"
            n.simdPosition = SIMD3(Float(i % 3 - 1) * 1.2, 0.02, i < 3 ? 1.0 : -0.3)
            root.addChildNode(n)
        }
        return root
    }

    private static func fallbackCrop() -> SCNNode {
        let root = SCNNode()
        let g = SCNCone(topRadius: 0, bottomRadius: 0.3, height: 0.6)
        g.materials = [pbr(UIColor(red: 0.42, green: 0.76, blue: 0.4, alpha: 1))]
        let n = SCNNode(geometry: g)
        n.simdPosition = SIMD3(0, 0.3, 0)
        root.addChildNode(n)
        return root
    }

    // MARK: - Hit testing

    enum Hit { case sprout, busySprout(atWork: Bool), marker(String), item(String), none }

    /// The busy sprout hops around, so a tap anywhere near it on screen counts (true = farm, false = trip).
    func busySproutNear(_ pt: CGPoint, in view: SCNView, radius: CGFloat = 60) -> Bool? {
        for (node, atWork) in [(farmWorker, true), (tripSprout, false)] {
            guard let node, !node.isHidden, node.parent != nil else { continue }
            let p = view.projectPoint(SCNVector3(node.presentation.simdWorldPosition + SIMD3(0, 0.6, 0)))
            guard p.z > 0, p.z < 1 else { continue }
            if hypot(CGFloat(p.x) - pt.x, CGFloat(p.y) - pt.y) < radius { return atWork }
        }
        return nil
    }

    func hit(_ results: [SCNHitTestResult]) -> Hit {
        for r in results {
            var n: SCNNode? = r.node
            while let node = n {
                if node === sprout.root { return .sprout }
                if let w = farmWorker, node === w { return .busySprout(atWork: true) }
                if let v = tripSprout, node === v { return .busySprout(atWork: false) }
                if let (id, _) = markers.first(where: { $0.value === node }) { return .marker(id) }
                if let name = node.name, name.hasPrefix("item:") { return .item(String(name.dropFirst(5))) }
                n = node.parent
            }
        }
        return .none
    }

    func orbitBy(_ delta: Float) {
        yaw += delta
    }

    func zoom(by factor: Float) {
        targetDistance = max(16, min(40, targetDistance / factor))
    }

    // MARK: - Particle recipes

    private static func fire() -> SCNParticleSystem {
        let f = SCNParticleSystem()
        f.particleImage = Textures.puff
        f.birthRate = 40
        f.emitterShape = SCNSphere(radius: 0.12)
        f.birthLocation = .volume
        f.particleLifeSpan = 0.7
        f.particleLifeSpanVariation = 0.2
        f.particleVelocity = 0.6
        f.particleVelocityVariation = 0.2
        f.emittingDirection = SCNVector3(0, 1, 0)
        f.spreadingAngle = 12
        f.particleSize = 0.2
        f.particleColor = UIColor(red: 1, green: 0.55, blue: 0.18, alpha: 1)
        f.blendMode = .additive
        f.isLightingEnabled = false
        let size = SCNParticlePropertyController(animation: {
            let a = CAKeyframeAnimation()
            a.values = [0.22, 0.14, 0.02]
            return a
        }())
        let color = SCNParticlePropertyController(animation: {
            let a = CAKeyframeAnimation()
            a.values = [UIColor(red: 1, green: 0.9, blue: 0.5, alpha: 1), UIColor(red: 1, green: 0.45, blue: 0.12, alpha: 0.9),
                        UIColor(red: 0.8, green: 0.2, blue: 0.1, alpha: 0)]
            return a
        }())
        f.propertyControllers = [.size: size, .color: color]
        return f
    }

    private static func smoke() -> SCNParticleSystem {
        let s = SCNParticleSystem()
        s.particleImage = Textures.puff
        s.birthRate = 2.2
        s.particleLifeSpan = 5
        s.particleVelocity = 0.35
        s.emittingDirection = SCNVector3(0.25, 1, 0)
        s.spreadingAngle = 10
        s.particleSize = 0.18
        s.particleColor = UIColor(white: 0.95, alpha: 0.55)
        s.isLightingEnabled = false
        s.blendMode = .alpha
        let grow = SCNParticlePropertyController(animation: {
            let a = CAKeyframeAnimation()
            a.values = [0.12, 0.6]
            return a
        }())
        let fade = SCNParticlePropertyController(animation: {
            let a = CAKeyframeAnimation()
            a.values = [0, 0.6, 0]
            a.keyTimes = [0, 0.15, 1]
            return a
        }())
        s.propertyControllers = [.size: grow, .opacity: fade]
        return s
    }

    // MARK: - Fallback geometry (before Blender assets are bundled)

    static func pbr(_ c: UIColor) -> SCNMaterial {
        let m = SCNMaterial()
        m.lightingModel = .physicallyBased
        m.diffuse.contents = c
        m.roughness.contents = 0.85
        return m
    }

    private static func fallbackIsland() -> SCNNode {
        let root = SCNNode()
        let top = SCNCylinder(radius: 6, height: 0.5)
        top.materials = [pbr(UIColor(red: 0.48, green: 0.79, blue: 0.44, alpha: 1))]
        let topNode = SCNNode(geometry: top)
        topNode.simdPosition = SIMD3(0, -0.25, 0)
        root.addChildNode(topNode)
        let bottom = SCNCone(topRadius: 5.9, bottomRadius: 0.6, height: 5)
        bottom.materials = [pbr(UIColor(red: 0.66, green: 0.47, blue: 0.31, alpha: 1))]
        let b = SCNNode(geometry: bottom)
        b.simdPosition = SIMD3(0, -3, 0)
        root.addChildNode(b)
        return root
    }

    static func fallbackCloud() -> SCNNode {
        let root = SCNNode()
        for (x, y, r) in [(-1.0, 0.0, 0.9), (0.0, 0.3, 1.2), (1.1, 0.0, 0.85), (0.4, -0.1, 0.9)] as [(Float, Float, CGFloat)] {
            let s = SCNSphere(radius: r)
            s.materials = [pbr(.white)]
            let n = SCNNode(geometry: s)
            n.simdPosition = SIMD3(x, y, 0)
            root.addChildNode(n)
        }
        return root
    }

    private static func fallbackIsle(radius: Float) -> SCNNode {
        let n = SCNNode()
        let top = SCNNode(geometry: SCNCylinder(radius: CGFloat(radius), height: 0.5))
        top.geometry?.firstMaterial = pbr(UIColor(red: 0.48, green: 0.79, blue: 0.44, alpha: 1))
        top.simdPosition = SIMD3(0, -0.25, 0)
        let under = SCNNode(geometry: SCNCone(topRadius: CGFloat(radius) * 0.95, bottomRadius: 0.3, height: 2.6))
        under.geometry?.firstMaterial = pbr(UIColor(red: 0.66, green: 0.47, blue: 0.31, alpha: 1))
        under.simdPosition = SIMD3(0, -1.8, 0)
        n.addChildNode(top)
        n.addChildNode(under)
        return n
    }

    private static func fallbackBridge() -> SCNNode {
        let n = SCNNode()
        let wood = pbr(UIColor(red: 0.69, green: 0.48, blue: 0.29, alpha: 1))
        for i in 0..<20 {
            let plank = SCNNode(geometry: SCNBox(width: 0.9, height: 0.06, length: 0.22, chamferRadius: 0.02))
            plank.geometry?.firstMaterial = wood
            let z = (Float(i) + 0.5) * 0.3
            plank.simdPosition = SIMD3(0, -0.2 * sin(z / 6 * .pi), z)
            n.addChildNode(plank)
        }
        return n
    }

    private static func fallbackItem(_ item: Buildable) -> SCNNode {
        let box = SCNBox(width: 0.9, height: 0.9, length: 0.9, chamferRadius: 0.2)
        box.materials = [pbr(UIColor(red: 0.95, green: 0.7, blue: 0.35, alpha: 1))]
        let n = SCNNode(geometry: box)
        n.simdPosition = SIMD3(0, 0.45, 0)
        let root = SCNNode()
        root.addChildNode(n)
        return root
    }
}

extension SkyState.Palette {
    func isClose(to o: SkyState.Palette) -> Bool {
        simd_distance(zenith, o.zenith) < 0.004 && simd_distance(horizon, o.horizon) < 0.004 &&
            abs(sunIntensity - o.sunIntensity) < 8 && simd_distance(cloudTint, o.cloudTint) < 0.004
    }
}
