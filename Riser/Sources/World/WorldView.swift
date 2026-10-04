import SceneKit
import SwiftUI

/// SwiftUI wrapper around the SceneKit island.
struct WorldView: UIViewRepresentable {
    var sky: SkyState
    var built: [String]
    var stage: SproutStage
    var lastBuilt: String?
    var petTick: Int
    var celebrateTick: Int
    var buildMarkers: [String]
    var highlightedSlot: String?
    var interactive: Bool = true
    /// Stops rendering while something covers the world (saves battery during missions).
    var paused: Bool = false
    /// Drop to 30 fps while a menu covers the world, so the menu itself animates smoothly.
    var throttled: Bool = false
    /// Where to float the 3D cloud clock, in view points from the top (nil = no clock).
    var clockY: CGFloat? = nil
    /// Cloud letters to show instead of the time.
    var clockText: String? = nil
    var hat: String? = nil
    var sproutAway: Bool = false
    var plots: [PlotState] = []
    var atWork: Bool = false
    var focusFarm: Bool = false
    var mood: MoodTier = .okay
    var hungry: Bool = false
    var feedTick: Int = 0
    var feedEmoji: String = "🍎"
    var gloom: Int = 0
    var dusty: Bool = false
    var sick: Bool = false
    var home: String = "tent"
    var viewInside: Bool = false
    var occupant: WorldScene.Occupant = .none
    var decor: InteriorDecor = InteriorDecor()
    var tripDestination: String? = nil
    var tripVisible: Bool = false
    var tripActivity: Int = 0
    var tripArrivalTick: Int = 0
    var commuteTick: Int = 0
    var skipTick: Int = 0
    var commuteHarvest: [(Int, String)] = []
    /// Where each built item is (island + spot); missing items use their classic slot.
    var placements: [String: ItemPlacement] = [:]
    /// Expansion isles owned, and one that was just bought (it rises into view).
    var isles: [Int] = []
    var newIsle: Int? = nil
    /// Point the camera at an expansion isle.
    var focusIsle: Int? = nil
    /// The item being placed (see-through preview), its spot, and a validity check for the ring colour.
    var ghostID: String? = nil
    var ghostPlacement: ItemPlacement? = nil
    var canPlace: (ItemPlacement) -> Bool = { _ in true }
    var onGhostMoved: (ItemPlacement) -> Void = { _ in }
    var onCommuteFinished: () -> Void = {}
    var onPetSprout: () -> Void = {}
    /// Tapped the sprout while it's busy at the farm (true) or on vacation (false).
    var onPokeBusySprout: (Bool) -> Void = { _ in }
    var onTapMarker: (String) -> Void = { _ in }
    var onTapItem: (String) -> Void = { _ in }
    /// Onboarding: frame the sprout and report where his head is on screen.
    var companionFocus: Bool = false
    var onSproutScreen: ((CGPoint) -> Void)? = nil

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIView(context: Context) -> SCNView {
        let world = context.coordinator.world
        let view = SCNView(frame: .zero)
        view.scene = world.scene
        view.pointOfView = world.cameraNode
        view.antialiasingMode = .multisampling4X
        // Render the 3D world at 2× (the UI on top stays at full resolution): a big GPU saving on 3× phones.
        view.contentScaleFactor = min(UIScreen.main.scale, 2)
        world.view = view
        if let perf = world.perf { view.delegate = perf }
        // Full ProMotion rate (120 Hz on Pro iPhones): at 60 the island feels sluggish next to iOS itself.
        view.preferredFramesPerSecond = UIScreen.main.maximumFramesPerSecond
        view.rendersContinuously = true
        // Sky-coloured while the island builds, instead of a black flash.
        view.backgroundColor = sky.palette.horizon.uiColor
        view.isJitteringEnabled = false
        let pan = UIPanGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.pan(_:)))
        let pinch = UIPinchGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.pinch(_:)))
        let tap = UITapGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.tap(_:)))
        view.gestureRecognizers = [pan, pinch, tap]
        context.coordinator.view = view
        world.setIsles(isles, animate: nil)
        world.setBuilt(built, placements: placements, animate: nil)
        world.sprout.setStage(stage)
        world.apply(sky: sky, force: true)
        if interactive { world.sprout.greet(at: CACurrentMediaTime()) }
        context.coordinator.feedTick = feedTick
        context.coordinator.commuteTick = commuteTick
        return view
    }

    func updateUIView(_ view: SCNView, context: Context) {
        PerfProbe.measure("updateUIView") { update(view, context: context) }
    }

    private func update(_ view: SCNView, context: Context) {
        let c = context.coordinator
        let world = c.world
        c.parent = self
        view.gestureRecognizers?.forEach { $0.isEnabled = interactive }
        if c.throttled != throttled {
            c.throttled = throttled
            view.preferredFramesPerSecond = throttled ? 30 : UIScreen.main.maximumFramesPerSecond
            world.setThrottled(throttled)
        }
        if c.paused != paused {
            c.paused = paused
            view.rendersContinuously = !paused
            view.isPlaying = !paused
            paused ? world.stop() : world.start()
        }
        world.clockPointY = clockY
        world.clockText = clockText
        if view.bounds.height > 0 { world.setAspect(view.bounds.width / view.bounds.height) }
        world.apply(sky: sky)
        if c.isles != isles {
            c.isles = isles
            world.setIsles(isles, animate: newIsle)
        }
        if c.built != built || c.placements != placements {
            c.built = built
            c.placements = placements
            world.setBuilt(built, placements: placements, animate: lastBuilt)
        }
        world.ghostValidator = canPlace
        world.companionFocus = companionFocus
        world.onSproutScreen = onSproutScreen
        if !c.draggingGhost {
            world.setGhost(id: ghostID, placement: ghostPlacement)
        }
        world.sprout.setHat(hat)
        world.sprout.moodTier = mood
        world.sprout.hungry = hungry
        world.sprout.sick = sick
        world.setGloom(gloom)
        world.setInterior(home: home, visible: viewInside, occupant: occupant, decor: decor)
        world.setTrip(destination: tripDestination, visible: tripVisible, activity: tripActivity)
        if c.tripArrivalTick != tripArrivalTick {
            c.tripArrivalTick = tripArrivalTick
            world.playTripArrival()
        }
        world.setDusty(dusty)
        world.focus = focusFarm || world.isCommuting ? .farm : (focusIsle.map { $0 == 0 ? .home : .isle($0) } ?? .home)
        if c.commuteTick != commuteTick {
            let first = c.commuteTick == -1
            c.commuteTick = commuteTick
            if !first {
                let done = onCommuteFinished
                world.playCommute(harvest: commuteHarvest, plots: plots) { done() }
            }
        }
        if !world.isCommuting {
            if c.plots != plots {
                c.plots = plots
                world.setPlots(plots)
            }
            if c.atWork != atWork {
                world.setAtWork(atWork, animated: c.atWork != nil)
                c.atWork = atWork
            }
        } else {
            c.plots = plots
            c.atWork = atWork
            world.setAtWork(atWork, animated: false)
        }
        if c.skipTick != skipTick {
            c.skipTick = skipTick
            world.skipCommute()
        }
        if c.feedTick != feedTick {
            c.feedTick = feedTick
            world.sprout.eat(feedEmoji, at: CACurrentMediaTime())
        }
        if c.away != sproutAway {
            world.setSproutAway(sproutAway, animated: c.away != nil)
            c.away = sproutAway
        }
        if c.stage != stage {
            c.stage = stage
            world.sprout.setStage(stage)
        }
        if c.petTick != petTick {
            c.petTick = petTick
            world.sprout.pet(at: CACurrentMediaTime())
            world.closeUpOnSprout()
        }
        if c.celebrateTick != celebrateTick {
            c.celebrateTick = celebrateTick
            world.sprout.celebrate(at: CACurrentMediaTime())
        }
        if c.markers != buildMarkers || c.highlight != highlightedSlot {
            c.markers = buildMarkers
            if c.highlight != highlightedSlot, let id = highlightedSlot, let item = BuildCatalog.item(id) {
                let p = placements[id]
                if p == nil || p?.island == 0 { world.focus(on: p?.point ?? item.slot) }
            }
            c.highlight = highlightedSlot
            world.setBuildMarkers(buildMarkers, highlighted: highlightedSlot)
        }
    }

    static func dismantleUIView(_ view: SCNView, coordinator: Coordinator) {
        coordinator.world.stop()
    }

    @MainActor
    final class Coordinator: NSObject {
        let world = WorldScene()
        weak var view: SCNView?
        var parent: WorldView?
        var built: [String] = []
        var stage: SproutStage = .seedling
        var petTick = 0
        var celebrateTick = 0
        var markers: [String] = []
        var highlight: String?
        var paused = false
        var throttled = false
        var away: Bool?
        var commuteTick = -1
        var plots: [PlotState]?
        var atWork: Bool?
        var feedTick = 0
        var skipTick = 0
        var tripArrivalTick = 0
        var isles: [Int] = []
        var placements: [String: ItemPlacement] = [:]
        var draggingGhost = false

        @objc func pan(_ g: UIPanGestureRecognizer) {
            guard let view else { return }
            let w = Float(max(1, view.bounds.width))
            // While placing: a drag that starts on (or near) the preview moves it; anything else orbits.
            if let spot = world.ghostPlacement {
                let loc = g.location(in: view)
                if g.state == .began, let ground = world.groundPoint(at: loc, in: view, island: spot.island),
                   simd_distance(ground, spot.point) < max(1.1, BuildCatalog.radius(parent?.ghostID ?? "") + 0.7) {
                    draggingGhost = true
                }
                if draggingGhost {
                    switch g.state {
                    case .changed:
                        if let ground = world.groundPoint(at: loc, in: view, island: spot.island) {
                            world.moveGhost(to: spot.moved(to: clamp(ground, island: spot.island)))
                        }
                    case .ended, .cancelled:
                        draggingGhost = false
                        if let p = world.ghostPlacement { parent?.onGhostMoved(p) }
                    default: break
                    }
                    return
                }
            }
            switch g.state {
            case .began:
                world.isInteracting = true
                world.yawVelocity = 0
            case .changed:
                let dx = Float(g.translation(in: view).x)
                g.setTranslation(.zero, in: view)
                world.orbitBy(-dx / w * 2.6)
            case .ended, .cancelled:
                world.isInteracting = false
                world.yawVelocity = -Float(g.velocity(in: view).x) / w * 2.6
            default: break
            }
        }

        @objc func pinch(_ g: UIPinchGestureRecognizer) {
            world.zoom(by: Float(g.scale))
            g.scale = 1
        }

        /// Keeps a dragged item within reach of the island's edge.
        private func clamp(_ p: SIMD2<Float>, island: Int) -> SIMD2<Float> {
            let limit = IsleCatalog.buildRadius(island) + 0.4
            let len = simd_length(p)
            return len > limit ? p / len * limit : p
        }

        @objc func tap(_ g: UITapGestureRecognizer) {
            guard let view else { return }
            // While placing, tapping the ground moves the preview there.
            if let spot = world.ghostPlacement {
                if let ground = world.groundPoint(at: g.location(in: view), in: view, island: spot.island),
                   simd_length(ground) < IsleCatalog.buildRadius(spot.island) + 0.4 {
                    let p = spot.moved(to: ground)
                    world.moveGhost(to: p)
                    parent?.onGhostMoved(p)
                    Haptics.select()
                }
                return
            }
            if let atWork = world.busySproutNear(g.location(in: view), in: view) {
                parent?.onPokeBusySprout(atWork)
                return
            }
            let results = view.hitTest(g.location(in: view), options: [.searchMode: SCNHitTestSearchMode.all.rawValue])
            switch world.hit(results) {
            case .sprout: parent?.onPetSprout()
            case .busySprout(let atWork): parent?.onPokeBusySprout(atWork)
            case .marker(let id): parent?.onTapMarker(id)
            case .item(let id): parent?.onTapItem(id)
            default: break
            }
        }
    }
}
