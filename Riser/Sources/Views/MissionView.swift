import SwiftUI

struct MissionView: View {
    @Environment(AppModel.self) private var model
    let active: ActiveMission

    @State private var started = false
    @State private var count = 0
    @State private var phase: Double = 0
    @State private var status = ""
    @State private var counter: (any RepCounter)?
    @State private var pose: PoseRepCounter?
    @State private var hunt: ItemHuntCounter?
    @State private var pollTask: Task<Void, Never>?
    @State private var lastProgress = Date.now
    @State private var celebrateTick = 0
    @State private var finished = false
    @State private var pulse = false
    /// The camera or sensors couldn't be used: the mission became a short Brain Warm-up instead.
    @State private var fallbackMath = false
    @State private var offerSwitch = false
    @State private var appeared = false

    /// What the player actually has to do (a fallback swaps in 3 math problems).
    private var goal: Int { fallbackMath ? 3 : active.mission.clamped(active.target) }
    private var progress: Double { min(1, Double(count) / Double(max(1, goal))) }

    var body: some View {
        ZStack {
            if let hunt, started, hunt.cameraAvailable, !fallbackMath {
                CameraPreview(session: hunt.session, mirrored: false)
                    .ignoresSafeArea()
            } else if let pose, started, pose.cameraAvailable {
                #if DEBUG
                if let still = pose.stillImage {
                    GeometryReader { geo in
                        Image(uiImage: still).resizable().scaledToFill()
                            .frame(width: geo.size.width, height: geo.size.height).clipped()
                    }
                    .ignoresSafeArea()
                } else {
                    CameraPreview(session: pose.session)
                        .ignoresSafeArea()
                }
                #else
                CameraPreview(session: pose.session)
                    .ignoresSafeArea()
                #endif
                SkeletonOverlay(joints: pose.displayJoints, frameSize: pose.frameSize, keyJoint: pose.keyJoint,
                                keyAngle: pose.keyAngle, isDown: pose.isDown)
                    .ignoresSafeArea()
            } else {
                WorldView(sky: model.env.sky, built: model.state.built, stage: model.state.sproutStage,
                          lastBuilt: nil, petTick: 0, celebrateTick: celebrateTick,
                          buildMarkers: [], highlightedSlot: nil, interactive: false, hat: model.state.equippedHat)
                    .ignoresSafeArea()
                    .blur(radius: started ? 6 : 0)
            }
            LinearGradient(colors: [.black.opacity(0.45), .clear, .clear, .black.opacity(0.65)], startPoint: .top, endPoint: .bottom)
                .ignoresSafeArea()
                .allowsHitTesting(false)

            VStack(spacing: 0) {
                header
                Spacer()
                if started {
                    if active.mission == .math || fallbackMath {
                        MathMission(target: goal) { solved in
                            count = solved
                            registerProgress()
                        }
                        .transition(.move(edge: .bottom).combined(with: .opacity))
                    } else if let hunt, !fallbackMath {
                        HuntPanel(hunt: hunt)
                            .transition(.move(edge: .bottom).combined(with: .opacity))
                        Spacer()
                        #if DEBUG
                        Button("Debug: found it") { hunt.debugRep() }
                            .font(.caption)
                            .buttonStyle(.glass)
                        #endif
                    } else {
                        ProgressRing(progress: progress, count: count, target: goal, unit: active.mission.unit,
                                     symbol: active.mission.symbol, phase: phase)
                            .scaleEffect(pose?.cameraAvailable == true ? 0.62 : 1)
                            .frame(height: pose?.cameraAvailable == true ? 180 : 280)
                            .transition(.scale.combined(with: .opacity))
                        Text(status)
                            .font(.rounded(19, .semibold))
                            .worldText()
                            .multilineTextAlignment(.center)
                            .padding(.top, 24)
                            .contentTransition(.opacity)
                            .animation(.easeInOut(duration: 0.2), value: status)
                            .accessibilityAddTraits(.updatesFrequently)
                        Spacer()
                        #if DEBUG
                        if !UserDefaults.standard.bool(forKey: "demoAutoStart") {
                            Button("Debug: count one") { counter?.debugRep() }
                                .font(.caption)
                                .buttonStyle(.glass)
                        }
                        #endif
                    }
                } else {
                    briefing
                }
                Spacer()
                if offerSwitch && !fallbackMath && !finished {
                    Button {
                        switchToMath(reason: "Let's warm up your brain instead")
                    } label: {
                        Label("Having trouble? Do 3 math problems", systemImage: "brain.head.profile")
                            .font(.rounded(15, .semibold))
                    }
                    .buttonStyle(.glass)
                    .padding(.bottom, 8)
                    .transition(.opacity)
                }
                if active.isPractice && !finished {
                    Button("End practice") { finishPractice() }
                        .font(.rounded(15, .semibold))
                        .buttonStyle(.glass)
                        .padding(.bottom, 8)
                }
            }
            .padding(.horizontal, 20)
        }
        .animation(.spring(response: 0.5, dampingFraction: 0.85), value: started)
        .statusBarHidden()
        .persistentSystemOverlays(.hidden)
        .onAppear {
            UIApplication.shared.isIdleTimerDisabled = true
            // SwiftUI can briefly disappear/re-appear the cover's content while it's being presented
            // (e.g. straight after the Alarms sheet closes for a practice run): only set up once.
            guard !appeared else { return }
            appeared = true
            #if DEBUG
            if UserDefaults.standard.bool(forKey: "demoAutoStart") {
                Task { try? await Task.sleep(for: .milliseconds(600)); start() }
            }
            #endif
            SoundService.shared.startAlarmLoop(active.sound)
            status = active.mission.instruction
        }
        .onDisappear {
            UIApplication.shared.isIdleTimerDisabled = false
            // Only tear down once the mission has really ended. A spurious disappear used to mark the
            // mission finished before it started, so completing it never registered (practice runs
            // counted "4 of 3" forever and End practice vanished).
            guard model.activeMission?.id != active.id else { return }
            finished = true
            counter?.stop()
            hunt?.stop()
            pose?.stop()
            pollTask?.cancel()
        }
    }

    // MARK: Header

    private var header: some View {
        VStack(spacing: 4) {
            Text(active.isPractice ? "Practice mission" : "Good morning, \(model.state.companionName) is waiting!")
                .font(.rounded(17, .semibold))
                .opacity(0.9)
            TimelineView(.periodic(from: .now, by: 1)) { ctx in
                Text((model.env.timeOverride ?? ctx.date).formatted(date: .omitted, time: .shortened))
                    .font(.system(size: started ? 40 : 64, weight: .semibold, design: .rounded))
                    .monospacedDigit()
                    .contentTransition(.numericText())
            }
        }
        .worldText()
        .padding(.top, 20)
    }

    // MARK: Briefing

    private var briefing: some View {
        VStack(spacing: 18) {
            Image(systemName: active.mission.symbol)
                .font(.system(size: 54, weight: .semibold))
                .foregroundStyle(Theme.sunGradient)
                .symbolEffect(.bounce, options: .repeat(.periodic(delay: 1.2)))
                .frame(width: 100, height: 100)
                .glassEffect(.regular, in: .circle)
            VStack(spacing: 6) {
                Text(active.mission.goalText(goal).prefix(1).uppercased() + active.mission.goalText(goal).dropFirst())
                    .font(.rounded(32, .heavy))
                Text("to silence the alarm")
                    .font(.rounded(18, .semibold))
                    .opacity(0.85)
            }
            .worldText()
            Text(active.mission.instruction)
                .font(.rounded(16, .medium))
                .multilineTextAlignment(.center)
                .worldText()
                .opacity(0.9)
                .padding(.horizontal, 12)
            if active.mission == .pushups || active.mission == .squats {
                Text("Only do movements you're comfortable with.")
                    .font(.rounded(13, .medium))
                    .worldText()
                    .opacity(0.7)
            }

            Button(action: start) {
                Label("I'm up. Let's go!", systemImage: "sun.max.fill")
                    .font(.rounded(20, .bold))
                    .frame(maxWidth: .infinity)
                    .frame(height: 60)
            }
            .buttonStyle(.glassProminent)
            .tint(Theme.sun)
            .scaleEffect(pulse ? 1.03 : 1)
            .animation(.easeInOut(duration: 0.9).repeatForever(autoreverses: true), value: pulse)
            .onAppear { pulse = true }
            .padding(.top, 10)
        }
        .padding(24)
        .glassCard(cornerRadius: 34)
    }

    // MARK: Flow

    private func start() {
        Haptics.heavy()
        started = true
        SoundService.shared.duckAlarm(true)
        lastProgress = .now
        guard active.mission != .math else {
            startIdleWatch()
            return
        }
        let c: any RepCounter
        switch active.mission {
        case .pushups, .squats:
            let p = PoseRepCounter(exercise: active.mission == .pushups ? .pushup : .squat)
            pose = p
            c = p
        case .steps, .math: c = MathPlaceholderCounter()
        case .hunt:
            let h = ItemHuntCounter(count: goal)
            hunt = h
            c = h
        }
        c.onRep = { registerProgress() }
        c.start()
        counter = c
        // The mission must always be finishable: no camera (or access denied) falls back to the
        // phone's own sensors for reps, or to math for Item Hunt; long silence offers a switch.
        Task { @MainActor in
            while !finished && !fallbackMath {
                try? await Task.sleep(for: .milliseconds(500))
                if let p = pose, !p.cameraAvailable {
                    p.stop()
                    pose = nil
                    let fallback: any RepCounter = active.mission == .pushups ? PushupCounter() : SquatCounter()
                    fallback.onRep = { registerProgress() }
                    fallback.start()
                    counter = fallback
                }
                if let h = hunt, !h.cameraAvailable {
                    switchToMath(reason: "No camera, so it's a Brain Warm-up today")
                } else if let c = counter, c.isUnavailable {
                    switchToMath(reason: "No motion sensors, so it's a Brain Warm-up today")
                }
                // Stuck part-way counts too (e.g. the camera loses you after a few reps).
                if Date.now.timeIntervalSince(lastProgress) > 40 && !offerSwitch && !fallbackMath {
                    withAnimation { offerSwitch = true }
                }
            }
        }
        // Mirror counter state into the view.
        pollTask = Task { @MainActor in
            var statusShownAt = Date.distantPast
            while !Task.isCancelled {
                if let counter {
                    if counter.count != count { count = counter.count }
                    phase = counter.phase
                    // Hold each tip for a moment so it doesn't flicker between two messages.
                    if !counter.statusText.isEmpty, count < goal, counter.statusText != status,
                       Date.now.timeIntervalSince(statusShownAt) > 1.2 {
                        status = counter.statusText
                        statusShownAt = .now
                    }
                }
                try? await Task.sleep(for: .milliseconds(50))
            }
        }
        startIdleWatch()
    }

    private func switchToMath(reason: String) {
        counter?.stop()
        counter = nil
        hunt?.stop()
        hunt = nil
        pose?.stop()
        pose = nil
        count = 0
        status = reason
        lastProgress = .now
        withAnimation { fallbackMath = true }
    }

    /// If the player stops moving, the alarm swells back up.
    private func startIdleWatch() {
        Task { @MainActor in
            var ducked = true
            while !finished {
                try? await Task.sleep(for: .seconds(1))
                let idle = Date.now.timeIntervalSince(lastProgress) > 25
                if idle && ducked {
                    ducked = false
                    SoundService.shared.duckAlarm(false)
                    status = "Don't fall back asleep!"
                } else if !idle && !ducked {
                    ducked = true
                    SoundService.shared.duckAlarm(true)
                }
            }
        }
    }

    private func registerProgress() {
        lastProgress = .now
        if let c = counter { count = c.count }
        SoundService.shared.play(.rep, rate: 1 + Float(min(count, 20)) * 0.025)
        Haptics.rep()
        if count >= goal && !finished {
            complete()
        } else {
            let left = goal - count
            if active.mission != .math && !fallbackMath {
                status = left <= 3 ? "Only \(left) to go!" : ["Nice!", "Great form!", "Keep it up!", "You've got this!"].randomElement()!
            }
        }
    }

    private func complete() {
        finished = true
        counter?.stop()
        pollTask?.cancel()
        celebrateTick += 1
        SoundService.shared.stopAlarmLoop()
        SoundService.shared.play(.complete)
        Haptics.success()
        status = "Mission complete!"
        Task {
            try? await Task.sleep(for: .seconds(1.1))
            // A real alarm may have replaced this practice run in the meantime: don't end that one.
            guard model.activeMission?.id == active.id else { return }
            var done = active
            if fallbackMath {
                done.mission = .math
                done.target = goal
            }
            model.completeMission(done, amount: max(count, goal))
        }
    }

    private func finishPractice() {
        counter?.stop()
        pollTask?.cancel()
        if count > 0 {
            finished = true
            var done = active
            if fallbackMath {
                done.mission = .math
                done.target = goal
            }
            model.completeMission(done, amount: count)
        } else {
            model.abandonPractice()
        }
    }
}

/// Big circular counter. The inner sprout-dot rises and falls with the player's movement.
struct ProgressRing: View {
    var progress: Double
    var count: Int
    var target: Int
    var unit: String
    var symbol: String
    var phase: Double

    var body: some View {
        ZStack {
            Circle()
                .fill(.ultraThinMaterial)
                .glassEffect(.regular, in: .circle)
            Circle()
                .stroke(.white.opacity(0.15), lineWidth: 18)
                .padding(14)
            Circle()
                .trim(from: 0, to: max(0.001, progress))
                .stroke(Theme.sunGradient, style: StrokeStyle(lineWidth: 18, lineCap: .round))
                .rotationEffect(.degrees(-90))
                .padding(14)
                .shadow(color: Theme.sun.opacity(0.6), radius: 12)
                .animation(.spring(response: 0.5, dampingFraction: 0.7), value: progress)
            VStack(spacing: 0) {
                Image(systemName: symbol)
                    .font(.system(size: 26, weight: .semibold))
                    .offset(y: CGFloat(phase) * 10)
                    .animation(.easeOut(duration: 0.12), value: phase)
                    .opacity(0.8)
                Text("\(count)")
                    .font(.system(size: 96, weight: .heavy, design: .rounded))
                    .monospacedDigit()
                    .contentTransition(.numericText(value: Double(count)))
                    .animation(.spring(response: 0.3, dampingFraction: 0.6), value: count)
                Text("of \(target) \(unit)")
                    .font(.rounded(17, .semibold))
                    .opacity(0.8)
            }
            .foregroundStyle(.white)
        }
        .frame(width: 280, height: 280)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("\(count) of \(target) \(unit)")
    }
}

/// A quick arithmetic warm-up with a big friendly keypad.
struct MathMission: View {
    var target: Int
    var onSolved: (Int) -> Void

    @State private var problem = MathProblem.random(difficulty: 0)
    @State private var entry = ""
    @State private var solved = 0
    @State private var shake = 0

    var body: some View {
        VStack(spacing: 18) {
            Text(solved >= target ? "All done!" : "\(solved + 1) of \(target)")
                .font(.rounded(15, .semibold))
                .worldText()
                .opacity(0.85)
            VStack(spacing: 6) {
                Text(problem.text)
                    .font(.system(size: 52, weight: .heavy, design: .rounded))
                    .monospacedDigit()
                Text(entry.isEmpty ? "?" : entry)
                    .font(.system(size: 44, weight: .bold, design: .rounded))
                    .monospacedDigit()
                    .foregroundStyle(entry.isEmpty ? .white.opacity(0.4) : Theme.sunLight)
                    .contentTransition(.numericText())
            }
            .foregroundStyle(.white)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 22)
            .glassCard(cornerRadius: 30)
            .modifier(ShakeEffect(shakes: CGFloat(shake)))

            let keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "⌫", "0", "✓"]
            LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 10), count: 3), spacing: 10) {
                ForEach(keys, id: \.self) { key in
                    Button { press(key) } label: {
                        Group {
                            if key == "⌫" { Image(systemName: "delete.left.fill") }
                            else if key == "✓" { Image(systemName: "checkmark") }
                            else { Text(key) }
                        }
                        .font(.rounded(28, .bold))
                        .frame(maxWidth: .infinity)
                        .frame(height: 62)
                        .foregroundStyle(key == "✓" ? Theme.ink : .white)
                        // The whole key is tappable, not just the digit's glyph.
                        .contentShape(.rect(cornerRadius: 20))
                    }
                    .buttonStyle(.plain)
                    .glassEffect(key == "✓" ? .regular.tint(Theme.sun).interactive() : .regular.interactive(), in: .rect(cornerRadius: 20))
                    .accessibilityLabel(key == "⌫" ? "Delete" : key == "✓" ? "Submit" : key)
                }
            }
        }
    }

    private func press(_ key: String) {
        Haptics.tap()
        switch key {
        case "⌫": if !entry.isEmpty { entry.removeLast() }
        case "✓": submit()
        default: if entry.count < 4 { entry += key }
        }
    }

    private func submit() {
        guard solved < target, let v = Int(entry) else { return }
        if v == problem.answer {
            solved += 1
            onSolved(solved)
            // The last answer stays on screen while the mission wraps up (no stray "4 of 3").
            guard solved < target else { return }
            entry = ""
            problem = .random(difficulty: solved)
        } else {
            SoundService.shared.play(.nope)
            Haptics.warning()
            withAnimation(.default) { shake += 1 }
            entry = ""
        }
    }
}

struct MathProblem {
    var text: String
    var answer: Int

    static func random(difficulty: Int) -> MathProblem {
        switch Int.random(in: 0...2) {
        case 0:
            let a = Int.random(in: 12...(40 + difficulty * 10)), b = Int.random(in: 11...49)
            return MathProblem(text: "\(a) + \(b)", answer: a + b)
        case 1:
            let a = Int.random(in: 3...9), b = Int.random(in: 4...12)
            return MathProblem(text: "\(a) × \(b)", answer: a * b)
        default:
            let a = Int.random(in: 40...99), b = Int.random(in: 11...(a - 5))
            return MathProblem(text: "\(a) − \(b)", answer: a - b)
        }
    }
}

struct ShakeEffect: GeometryEffect {
    var shakes: CGFloat
    var animatableData: CGFloat {
        get { shakes }
        set { shakes = newValue }
    }

    func effectValue(size: CGSize) -> ProjectionTransform {
        ProjectionTransform(CGAffineTransform(translationX: 10 * sin(shakes * .pi * 4), y: 0))
    }
}


/// Item Hunt: the current target, progress and a live "I see…" hint.
struct HuntPanel: View {
    let hunt: ItemHuntCounter

    var body: some View {
        VStack(spacing: 14) {
            if let target = hunt.current {
                VStack(spacing: 8) {
                    Text("Find")
                        .font(.rounded(15, .semibold))
                        .opacity(0.8)
                    Text(target.emoji)
                        .font(.system(size: 64))
                        .scaleEffect(1 + hunt.phase * 0.25)
                        .animation(.spring(response: 0.3, dampingFraction: 0.5), value: hunt.phase)
                    Text(target.name)
                        .font(.rounded(28, .heavy))
                        .multilineTextAlignment(.center)
                    GlowBar(progress: hunt.phase, gradient: Theme.leafGradient, height: 8)
                        .frame(width: 160)
                        .opacity(hunt.phase > 0 ? 1 : 0.3)
                }
                .foregroundStyle(.white)
                .padding(22)
                .frame(maxWidth: .infinity)
                .glassCard(cornerRadius: 30)
                .id(target.id)
                .transition(.scale(scale: 0.9).combined(with: .opacity))

                Button {
                    Haptics.tap()
                    withAnimation(.snappy) { hunt.tryAnother() }
                } label: {
                    Label("Try another item", systemImage: "shuffle")
                        .font(.rounded(16, .semibold))
                        .padding(.horizontal, 6)
                        .padding(.vertical, 4)
                }
                .buttonStyle(.glass)
                .accessibilityHint("Swaps \(target.name) for something else to find")
            }
            if hunt.targets.count > 1 {
                HStack(spacing: 10) {
                    ForEach(Array(hunt.targets.enumerated()), id: \.offset) { i, t in
                        Text(i < hunt.count ? "✅" : t.emoji)
                            .font(.system(size: 26))
                            .frame(width: 50, height: 50)
                            .background(.white.opacity(i == hunt.count ? 0.25 : 0.08), in: .circle)
                            .opacity(i > hunt.count ? 0.5 : 1)
                    }
                }
            }
            Text(hunt.seeing.map { "I see: \($0)" } ?? hunt.statusText)
                .font(.rounded(15, .semibold))
                .worldText()
                .contentTransition(.opacity)
                .animation(.easeInOut, value: hunt.seeing)
        }
    }
}
