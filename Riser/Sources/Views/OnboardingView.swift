import Charts
import UserNotifications
import SwiftUI

/// A short, results-first onboarding: the problem, their own numbers, why Riser works,
/// what their island can become, then the sprout, the alarm and a commitment.
struct OnboardingView: View {
    @Environment(AppModel.self) private var model

    enum Step: Int, CaseIterable {
        case hook, snooze, costs, times, plan, why, tryIt, showcase, name, alarm, sky, building, commit
    }

    @State private var step: Step = .hook
    @State private var name = ""
    @State private var snooze: Int?
    @State private var costs: Set<String> = []
    @State private var wakeNow = Calendar.current.date(bySettingHour: 8, minute: 0, second: 0, of: .now) ?? .now
    @State private var wakeGoal = Calendar.current.date(bySettingHour: 6, minute: 30, second: 0, of: .now) ?? .now
    @State private var mission: MissionKind = .pushups
    /// Chosen on the alarm step: stopping without the mission makes the alarm ring again.
    @State private var escapeProof = true
    @State private var petTick = 0
    @State private var milestone = 3
    @State private var showcaseBuilt = Showcase.milestones[3].built
    @State private var showcaseLast: String?
    @State private var showcaseTask: Task<Void, Never>?
    @State private var holdProgress: Double = 0
    @State private var committed = false
    @State private var demo: PoseRepCounter?
    @State private var demoExercise: MissionKind = .pushups
    @State private var demoStarted = Date.now
    @State private var demoSeconds: Int?
    @State private var buildProgress = 0
    /// Where the sprout's head is on screen, so his speech bubble points at him.
    @State private var sproutAnchor = ScreenAnchor()
    /// Where the cloud "RISER" logo sits on screen (reported by the hook title's layout).
    @State private var logoY: CGFloat?
    @FocusState private var nameFocused: Bool

    /// Up to the showcase we show what's possible; from naming on, the real start (a tent and a seedling).
    private var isShowcasing: Bool { step.rawValue <= Step.showcase.rawValue }

    var body: some View {
        ZStack {
            WorldView(sky: morningSky,
                      built: isShowcasing ? showcaseBuilt : model.state.built,
                      stage: isShowcasing ? Showcase.milestones[milestone].stage : .seedling,
                      lastBuilt: showcaseLast,
                      petTick: petTick, celebrateTick: committed ? 1 : 0, buildMarkers: [], highlightedSlot: nil,
                      paused: step == .tryIt && demo?.cameraAvailable == true,
                      clockY: step == .hook ? logoY : nil,
                      clockText: "RISER",
                      hat: isShowcasing ? Showcase.milestones[milestone].hat : nil,
                      onPetSprout: {
                          petTick += 1
                          SoundService.shared.play(.pet)
                          Haptics.soft()
                      },
                      companionFocus: step != .hook && step != .showcase && !(step == .tryIt && demo != nil),
                      onSproutScreen: { [anchor = sproutAnchor] p in anchor.point = p })
                .ignoresSafeArea()
            if step == .tryIt, let demo, demo.cameraAvailable {
                CameraPreview(session: demo.session)
                    .ignoresSafeArea()
                    .transition(.opacity)
                SkeletonOverlay(joints: demo.joints, frameSize: demo.frameSize, keyJoint: demo.keyJoint,
                                keyAngle: demo.keyAngle, isDown: demo.isDown)
                    .ignoresSafeArea()
            }
            LinearGradient(colors: [.black.opacity(dimsWorld ? 0.3 : 0.15), .clear, Theme.night.opacity(0.55)],
                           startPoint: .top, endPoint: .bottom)
                .ignoresSafeArea()
                .allowsHitTesting(false)

            if let line = sproutLine {
                SpeechAnchorLayer(anchor: sproutAnchor, text: line)
                    .ignoresSafeArea()
                    .allowsHitTesting(false)
            }

            VStack(spacing: 0) {
                topBar
                if step == .hook { hookTitle.padding(.top, 20) }
                Spacer(minLength: 12)
                card
                    .padding(22)
                    .glassCard(cornerRadius: 34)
                    .id(step)
                    .transition(.asymmetric(insertion: .move(edge: .trailing).combined(with: .opacity),
                                            removal: .move(edge: .leading).combined(with: .opacity)))
            }
            .padding(.horizontal, 18)
            .padding(.bottom, 10)
        }
        .animation(.spring(response: 0.5, dampingFraction: 0.86), value: step)
        .animation(.spring(response: 0.4, dampingFraction: 0.7), value: sproutLine)
        .onAppear {
            SoundService.shared.startMusic()
            #if DEBUG
            if let n = Step(rawValue: UserDefaults.standard.integer(forKey: "onboardStep")), n != .hook {
                snooze = 2
                costs = [Self.costOptions[0], Self.costOptions[1]]
                name = "Mochi"
                step = n
                if n == .showcase { playShowcase() }
            }
            #endif
        }
        .onChange(of: step) { _, s in
            if s == .showcase { playShowcase() } else { showcaseTask?.cancel() }
            if s != .tryIt { stopDemo() }
            if s == .building { runBuilding() }
            // The sprout pops up to say hello when it's time to name him.
            if s == .name { petTick += 1 }
        }
    }

    /// Question pages blur the island so the card is easy to read.
    private var dimsWorld: Bool {
        [.snooze, .costs, .times, .plan, .why, .tryIt].contains(step)
    }

    /// Onboarding shows a bright morning; the real sky arrives with the "Your sky" page.
    private var morningSky: SkyState {
        if step.rawValue >= Step.sky.rawValue { return model.env.sky }
        let morning = Calendar.current.date(bySettingHour: 8, minute: 10, second: 0, of: .now) ?? .now
        return SkyState.compute(date: morning, lat: model.env.latitude, lon: model.env.longitude, weather: WeatherNow())
    }

    // MARK: Chrome

    private var topBar: some View {
        HStack(spacing: 12) {
            if step != .hook {
                Button("Back", systemImage: "chevron.left") { back() }
                    .labelStyle(.iconOnly)
                    .buttonStyle(.glass)
                    .buttonBorderShape(.circle)
                GeometryReader { geo in
                    ZStack(alignment: .leading) {
                        Capsule().fill(.white.opacity(0.22))
                        Capsule().fill(Theme.sunGradient)
                            .frame(width: geo.size.width * Double(step.rawValue) / Double(Step.allCases.count - 1))
                    }
                }
                .frame(height: 7)
                .accessibilityElement()
                .accessibilityLabel("Step \(step.rawValue) of \(Step.allCases.count - 1)")
            }
        }
        .frame(height: 44)
        .padding(.top, 6)
        .animation(.spring(response: 0.5, dampingFraction: 0.9), value: step)
    }

    private var hookTitle: some View {
        VStack(spacing: 10) {
            // The world draws "RISER" in puffy 3D cloud letters right here.
            Color.clear
                .frame(height: 70)
                .onGeometryChange(for: CGFloat.self) { $0.frame(in: .global).midY } action: { logoY = $0 }
                .accessibilityElement()
                .accessibilityLabel("Riser")
            Text("Become a morning person\nwith your wake-up buddy.")
                .font(.rounded(28, .heavy))
                .multilineTextAlignment(.center)
                .lineSpacing(2)
        }
        .worldText()
        .frame(maxWidth: .infinity)
    }

    @ViewBuilder
    private var card: some View {
        switch step {
        case .hook: hook
        case .snooze: snoozeQuestion
        case .costs: costsQuestion
        case .times: timesQuestion
        case .plan: plan
        case .why: why
        case .tryIt: tryIt
        case .showcase: showcase
        case .name: namePage
        case .alarm: alarmPage
        case .sky: skyPage
        case .building: buildingPage
        case .commit: commitPage
        }
    }

    private func next() {
        Haptics.tap()
        SoundService.shared.play(.tap, volume: 0.5)
        nameFocused = false
        if let n = Step(rawValue: step.rawValue + 1) { step = n }
    }

    private func back() {
        Haptics.tap()
        nameFocused = false
        if let p = Step(rawValue: step.rawValue - 1) { step = p }
    }

    // MARK: The sprout's voice

    private var displayName: String {
        let n = name.trimmingCharacters(in: .whitespaces)
        return n.isEmpty ? model.state.companionName : n
    }

    /// What the little sprout says on each step (he reacts to your answers).
    private var sproutLine: String? {
        switch step {
        case .hook: return nil
        case .snooze:
            guard let snooze else { return "Hi! I'm a tiny sprout. Can I ask you something? 🌱" }
            return ["A natural! Let's make mornings feel good too.", "Just a couple? We can beat that together.",
                    "Oof. Those snoozes add up fast.", "Say no more. I've got you. 💪"][snooze]
        case .costs: return costs.isEmpty ? "Mornings shouldn't feel like that." : "Noted. Let's fix every one of those."
        case .times: return "When should we wake up together?"
        case .plan: return "Look at all that extra morning! ☀️"
        case .why: return "Here's the secret…"
        case .tryIt: return demoSeconds != nil ? "You did it!! 🎉" : "Your turn! Show me 3 reps."
        case .showcase: return "Look what we could build together!"
        case .name: return "What will you call me?"
        case .alarm: return "\(displayName) here! When do we get up?"
        case .sky: return "I love a real sky. 🌙"
        case .building: return buildProgress < 4 ? "Making our plan…" : "This is going to be great."
        case .commit: return "Pinky promise? 🤙"
        }
    }

    // MARK: 1 · Hook

    private var hook: some View {
        VStack(alignment: .leading, spacing: 16) {
            proof("lock.fill", Theme.berry, "No escaping it", "Hit stop without doing your mission and the alarm rings again, until you're up.")
            proof("figure.core.training", Theme.sun, "Push-ups your camera counts", "Or squats, an item hunt or quick math.")
            proof("leaf.fill", Theme.leaf, "A little friend who needs you", "Your buddy only goes to work when you get up.")
            primary("Fix my mornings", action: next)
        }
    }

    // MARK: 2 · Questions

    private static let snoozeOptions: [(String, String)] = [
        ("😇", "Rarely, I'm just groggy"),
        ("😴", "Once or twice"),
        ("🥱", "3 to 5 times"),
        ("🫠", "I've lost count"),
    ]

    private var snoozeQuestion: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top) {
                question("How often do you hit snooze?", "Be honest. No judgement.")
                Spacer()
                Button("Skip") { next() }
                    .font(.rounded(15, .semibold))
                    .foregroundStyle(.secondary)
            }
            ForEach(Self.snoozeOptions.indices, id: \.self) { i in
                option(Self.snoozeOptions[i].0, Self.snoozeOptions[i].1, selected: snooze == i) {
                    snooze = i
                    Task {
                        try? await Task.sleep(for: .milliseconds(280))
                        next()
                    }
                }
            }
        }
    }

    private static let costOptions = ["🏃 Running late", "🌫️ Groggy for hours", "💪 No time to work out",
                                      "📱 Scrolling in bed", "😮‍💨 Behind all day"]

    private var costsQuestion: some View {
        VStack(alignment: .leading, spacing: 12) {
            question("What do rough mornings cost you?", "Pick all that apply.")
            FlowChips(items: Self.costOptions, selected: $costs)
            primary(costs.isEmpty ? "Skip" : "Continue", action: next)
        }
    }

    private var timesQuestion: some View {
        VStack(alignment: .leading, spacing: 12) {
            question("Let's set your goal", "When do you get up now, and when do you want to?")
            timeRow("bed.double.fill", "I usually get up at", $wakeNow, tint: .white.opacity(0.75))
            timeRow("sunrise.fill", "I want to get up at", $wakeGoal, tint: Theme.sun)
            primary("See my plan", action: next)
        }
    }

    private func timeRow(_ symbol: String, _ title: String, _ date: Binding<Date>, tint: Color) -> some View {
        HStack(spacing: 12) {
            Image(systemName: symbol)
                .font(.system(size: 18, weight: .bold))
                .foregroundStyle(tint)
                .frame(width: 28)
            Text(title)
                .font(.rounded(17, .semibold))
            Spacer(minLength: 8)
            DatePicker(title, selection: date, displayedComponents: .hourAndMinute)
                .labelsHidden()
        }
        .padding(.horizontal, 16)
        .frame(minHeight: 60)
        .background(.white.opacity(0.07), in: .rect(cornerRadius: 18))
    }

    // MARK: 3 · Their results

    private var planNumbers: OnboardingPlan {
        OnboardingPlan(now: wakeNow, goal: wakeGoal, snoozeLevel: snooze ?? 1)
    }

    private var plan: some View {
        let p = planNumbers
        return VStack(alignment: .leading, spacing: 14) {
            question("Your new mornings", "Up at \(wakeGoal.formatted(date: .omitted, time: .shortened)), every weekday.")
            WakeChart(plan: p)
                .frame(height: 150)
            HStack(spacing: 10) {
                stat(p.weeklyText, "more morning\nevery week", Theme.sun)
                stat(p.yearDays, "full days back\nevery year", Theme.leaf)
                stat("200+", "push-ups a\nmonth, done", Theme.berry)
            }
            primary("How does it work?", action: next)
        }
    }

    private func stat(_ value: String, _ label: String, _ tint: Color) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(value)
                .font(.rounded(24, .heavy))
                .foregroundStyle(tint)
                .minimumScaleFactor(0.6)
                .lineLimit(1)
            Text(label)
                .font(.rounded(12, .semibold))
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(.white.opacity(0.07), in: .rect(cornerRadius: 16))
        .accessibilityElement(children: .combine)
    }

    // MARK: 4 · Why it works

    private var why: some View {
        VStack(alignment: .leading, spacing: 16) {
            question("Why Riser works", "Three small things that change mornings.")
            proof("figure.run", Theme.sun, "You can't snooze a push-up",
                  "The alarm only stays off once your mission is done. Escape-proof mode rings again soon after you hit stop, 10 seconds to 5 minutes, your choice.")
            proof("heart.fill", Theme.berry, "Someone's counting on you",
                  "Your sprout goes to work when you get up. Sleep in and he gets sad, then sick.")
            proof("moon.zzz.fill", .indigo, "A bedtime that fits your alarm",
                  "Riser counts back 8 hours from your alarm (five 90-minute sleep cycles plus time to fall asleep) and nudges you to wind down.")
            primary("Try it now", action: next)
        }
    }

    // MARK: 5 · Feel it: three reps, counted by the camera

    private var demoTarget: Int { 3 }

    @ViewBuilder
    private var tryIt: some View {
        if let seconds = demoSeconds {
            VStack(alignment: .leading, spacing: 12) {
                Text("🎉 Alarm off!")
                    .font(.rounded(30, .heavy))
                Text("\(demoTarget) \(demoExercise.unit) in \(seconds) seconds. That's every morning with Riser: heart rate up, grogginess gone, and no snooze button to hide behind.")
                    .font(.rounded(16, .medium))
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
                primary("Show me what I'll build", action: next)
            }
        } else if let demo {
            VStack(spacing: 12) {
                ZStack {
                    Circle().stroke(.white.opacity(0.15), lineWidth: 10)
                    Circle()
                        .trim(from: 0, to: Double(demo.count) / Double(demoTarget))
                        .stroke(Theme.sunGradient, style: StrokeStyle(lineWidth: 10, lineCap: .round))
                        .rotationEffect(.degrees(-90))
                        .animation(.spring, value: demo.count)
                    VStack(spacing: 0) {
                        Text("\(min(demo.count, demoTarget))")
                            .font(.system(size: 44, weight: .heavy, design: .rounded))
                            .contentTransition(.numericText())
                        Text("of \(demoTarget)").font(.rounded(13, .semibold)).foregroundStyle(.secondary)
                    }
                }
                .frame(width: 110, height: 110)
                .accessibilityElement()
                .accessibilityLabel("\(demo.count) of \(demoTarget) reps")
                Text(demo.cameraAvailable ? demo.statusText : "No camera here, so we'll skip the demo. You'll still love the real thing.")
                    .font(.rounded(15, .semibold))
                    .multilineTextAlignment(.center)
                    .frame(minHeight: 40)
                    .animation(.easeInOut, value: demo.statusText)
                #if DEBUG
                Button("Debug: count one") { demo.debugRep() }
                    .font(.caption)
                #endif
                Button(demo.cameraAvailable ? "Skip for now" : "Continue") { skipDemo() }
                    .font(.rounded(15, .semibold))
                    .foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity)
        } else {
            VStack(alignment: .leading, spacing: 14) {
                question("Try it right now", "Do \(demoTarget) reps and feel how the alarm switches off.")
                HStack(spacing: 10) {
                    ForEach([MissionKind.pushups, .squats]) { m in
                        MissionChoice(mission: m, selected: demoExercise == m) {
                            demoExercise = m
                            Haptics.select()
                        }
                    }
                    Spacer(minLength: 0)
                }
                Label(demoExercise.instruction, systemImage: "iphone.gen3")
                    .font(.rounded(14, .medium))
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
                Label("Video stays on your iPhone. Nothing is recorded.", systemImage: "lock.fill")
                    .font(.rounded(13, .semibold))
                    .foregroundStyle(Theme.leaf)
                Label("Only do movements you're comfortable with.", systemImage: "heart.text.square")
                    .font(.rounded(13, .medium))
                    .foregroundStyle(.secondary)
                primary("Continue", action: startDemo)
            }
        }
    }

    private func startDemo() {
        Haptics.tap()
        let counter = PoseRepCounter(exercise: demoExercise == .pushups ? .pushup : .squat)
        counter.onRep = {
            SoundService.shared.play(.rep, rate: 1 + Float(counter.count) * 0.05)
            Haptics.rep()
            if counter.count >= demoTarget && demoSeconds == nil {
                demoSeconds = max(1, Int(Date.now.timeIntervalSince(demoStarted)))
                SoundService.shared.play(.complete)
                Haptics.success()
                petTick += 1
                stopDemo(keepResult: true)
            }
        }
        demoStarted = .now
        withAnimation { demo = counter }
        counter.start()
    }

    private func skipDemo() {
        stopDemo()
        next()
    }

    private func stopDemo(keepResult: Bool = false) {
        demo?.stop()
        withAnimation { demo = nil }
        if !keepResult && step != .tryIt { demoSeconds = nil }
    }

    // MARK: 6 · What's possible

    private var showcase: some View {
        let m = Showcase.milestones[milestone]
        return VStack(alignment: .leading, spacing: 14) {
            HStack(spacing: 6) {
                ForEach(Showcase.milestones.indices, id: \.self) { i in
                    Button {
                        showcaseTask?.cancel()
                        showcaseTask = Task { @MainActor in await build(to: i) }
                    } label: {
                        Text(Showcase.milestones[i].label)
                            .font(.rounded(13, .bold))
                            .lineLimit(1)
                            .frame(maxWidth: .infinity)
                            .frame(height: 34)
                            .background(i == milestone ? AnyShapeStyle(Theme.sunGradient) : AnyShapeStyle(.white.opacity(0.08)), in: .capsule)
                            .foregroundStyle(i == milestone ? Theme.ink : .primary)
                            .contentShape(.capsule)
                    }
                    .buttonStyle(.plain)
                    .accessibilityAddTraits(i == milestone ? .isSelected : [])
                }
            }
            VStack(alignment: .leading, spacing: 4) {
                Text(m.title)
                    .font(.rounded(24, .heavy))
                Text(m.detail)
                    .font(.rounded(15, .medium))
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .id(milestone)
            .transition(.opacity)
            .animation(.easeInOut, value: milestone)
            primary("I want this", action: next)
        }
    }

    private func playShowcase() {
        showcaseTask?.cancel()
        milestone = 0
        showcaseBuilt = Showcase.milestones[0].built
        showcaseLast = nil
        showcaseTask = Task { @MainActor in
            try? await Task.sleep(for: .seconds(1.4))
            for i in 1..<Showcase.milestones.count {
                guard !Task.isCancelled else { return }
                await build(to: i)
                try? await Task.sleep(for: .seconds(1.8))
            }
        }
    }

    /// Pops the milestone's buildings in one by one, like the island growing over the months.
    private func build(to i: Int) async {
        let target = Showcase.milestones[i].built
        milestone = i
        showcaseBuilt = showcaseBuilt.filter { target.contains($0) }
        for id in target where !showcaseBuilt.contains(id) {
            guard !Task.isCancelled else { return }
            showcaseLast = id
            showcaseBuilt.append(id)
            SoundService.shared.play(.build, volume: 0.35)
            Haptics.soft()
            try? await Task.sleep(for: .milliseconds(260))
        }
    }

    // MARK: 6 · Their sprout

    private var namePage: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Everyone starts\nwith a tent.")
                .font(.rounded(30, .heavy))
            Text("And a tiny sprout who just found your island. What should we call it?")
                .font(.rounded(16, .medium))
                .foregroundStyle(.secondary)
            HStack(spacing: 10) {
                TextField("Name your sprout", text: $name)
                    .font(.rounded(22, .bold))
                    .padding(.horizontal, 18)
                    .frame(height: 56)
                    .background(.white.opacity(0.08), in: .rect(cornerRadius: 18))
                    .focused($nameFocused)
                    .submitLabel(.done)
                    .textInputAutocapitalization(.words)
                    .onSubmit { nameFocused = false }
                Button {
                    name = ["Sprig", "Mochi", "Pip", "Bean", "Dewey", "Clover", "Sunny", "Tater", "Basil", "Nori", "Fern", "Biscuit"]
                        .filter { $0 != name }.randomElement()!
                    Haptics.select()
                    petTick += 1
                } label: {
                    Image(systemName: "dice.fill")
                        .font(.system(size: 22, weight: .semibold))
                        .frame(width: 56, height: 56)
                }
                .buttonStyle(.glass)
                .accessibilityLabel("Suggest a name")
            }
            primary(name.isEmpty ? "Give your sprout a name" : "Say hi to \(name)", action: {
                model.state.companionName = String(name.trimmingCharacters(in: .whitespaces).prefix(16))
                petTick += 1
                next()
            })
            .disabled(name.trimmingCharacters(in: .whitespaces).isEmpty)
            .onAppear {
                Task { try? await Task.sleep(for: .seconds(0.6)); nameFocused = true }
            }
        }
    }

    // MARK: 7 · First alarm

    private var bedtime: Date { wakeGoal.addingTimeInterval(-AppModel.sleepDuration) }

    private var alarmPage: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Your first alarm")
                .font(.rounded(30, .heavy))
            HStack(spacing: 10) {
                DatePicker("Wake time", selection: $wakeGoal, displayedComponents: .hourAndMinute)
                    .labelsHidden()
                Text("Mon to Fri")
                    .font(.rounded(15, .semibold))
                    .foregroundStyle(.secondary)
                Spacer()
            }
            Label("Bedtime \(bedtime.formatted(date: .omitted, time: .shortened)) for five full sleep cycles",
                  systemImage: "moon.zzz.fill")
                .font(.rounded(14, .semibold))
                .foregroundStyle(Color.indigo.mix(with: .white, by: 0.45))
            Text("To stop it, I'll…")
                .font(.rounded(16, .bold))
                .padding(.top, 4)
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 10) {
                    ForEach(MissionKind.available) { m in
                        MissionChoice(mission: m, selected: mission == m) {
                            mission = m
                            Haptics.select()
                        }
                    }
                }
            }
            Toggle(isOn: $escapeProof.animation()) {
                VStack(alignment: .leading, spacing: 2) {
                    Label("Escape-proof", systemImage: "lock.fill")
                        .font(.rounded(16, .bold))
                    Text(escapeProof
                         ? "Hit stop without your mission and it rings again, as soon as 10 seconds later, until you're up."
                         : "Stopping the alarm switches it off. You can turn this on later in Settings.")
                        .font(.rounded(13, .medium))
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            .tint(Theme.sun)
            .padding(14)
            .background(.white.opacity(0.07), in: .rect(cornerRadius: 18))
            primary("Continue", action: next)
        }
    }

    // MARK: 8 · Real sky

    private var skyPage: some View {
        VStack(alignment: .leading, spacing: 14) {
            Image(systemName: "sun.horizon.fill")
                .font(.system(size: 40, weight: .semibold))
                .symbolRenderingMode(.multicolor)
            Text("Your sky, for real.")
                .font(.rounded(30, .heavy))
            Text("The sun, the moon's phase and the weather on \(model.state.companionName)'s island match the sky outside your window.")
                .font(.rounded(16, .medium))
                .foregroundStyle(.secondary)
            VStack(alignment: .leading, spacing: 10) {
                privacyPoint("location.fill", "Approximate location only, rounded to about 1 km, and only while you use Riser.")
                privacyPoint("cloud.sun.fill", "Weather comes from Apple Weather. Only those rounded coordinates are sent to Apple, and they aren't linked to you.")
                privacyPoint("lock.fill", "Never stored on our servers, never shared or sold. No account needed.")
                privacyPoint("hand.raised.fill", "Optional: say no and Riser estimates your sky from your time zone.")
            }
            primary("Continue", action: {
                model.env.requestLocation()
                next()
            })
        }
    }

    private func privacyPoint(_ symbol: String, _ text: String) -> some View {
        Label {
            Text(text).fixedSize(horizontal: false, vertical: true)
        } icon: {
            Image(systemName: symbol).foregroundStyle(Theme.leaf)
        }
        .font(.rounded(13, .medium))
        .foregroundStyle(.secondary)
    }

    // MARK: 9 · Their plan

    private var buildingSteps: [(String, String)] {
        [("alarm.fill", "Setting your \(wakeGoal.formatted(date: .omitted, time: .shortened)) alarm"),
         ("moon.zzz.fill", "Counting back five sleep cycles"),
         (mission.symbol, "Choosing \(mission.goalText(mission.defaultTarget)) to stop it"),
         ("leaf.fill", "Getting \(displayName) ready for work")]
    }

    private func runBuilding() {
        buildProgress = 0
        Task { @MainActor in
            for i in 1...4 {
                try? await Task.sleep(for: .milliseconds(750))
                guard step == .building else { return }
                withAnimation(.spring(response: 0.4, dampingFraction: 0.8)) { buildProgress = i }
                Haptics.soft()
            }
            SoundService.shared.play(.complete, volume: 0.5)
            Haptics.success()
            petTick += 1
        }
    }

    @ViewBuilder
    private var buildingPage: some View {
        if buildProgress < 4 {
            VStack(alignment: .leading, spacing: 14) {
                question("Building your plan", "Just a moment…")
                ForEach(buildingSteps.indices, id: \.self) { i in
                    HStack(spacing: 12) {
                        ZStack {
                            if i < buildProgress {
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundStyle(Theme.leaf)
                                    .transition(.scale.combined(with: .opacity))
                            } else if i == buildProgress {
                                ProgressView().tint(Theme.sun)
                            } else {
                                Image(systemName: "circle").foregroundStyle(.white.opacity(0.25))
                            }
                        }
                        .font(.system(size: 22))
                        .frame(width: 28)
                        Label(buildingSteps[i].1, systemImage: buildingSteps[i].0)
                            .font(.rounded(16, .semibold))
                            .opacity(i <= buildProgress ? 1 : 0.45)
                    }
                }
            }
        } else {
            let p = OnboardingPlan(now: wakeNow, goal: wakeGoal, snoozeLevel: snooze ?? 1)
            VStack(alignment: .leading, spacing: 12) {
                question("Your plan is ready", "Made for you and \(displayName).")
                VStack(spacing: 0) {
                    planRow("sunrise.fill", Theme.sun, "Wake up", "\(wakeGoal.formatted(date: .omitted, time: .shortened)), Mon to Fri")
                    planRow("moon.zzz.fill", .indigo, "Bedtime", "\(bedtime.formatted(date: .omitted, time: .shortened)) for 5 full sleep cycles")
                    planRow(mission.symbol, Theme.berry, "To stop the alarm", mission.goalText(mission.defaultTarget).capitalizedFirst)
                    planRow("leaf.fill", Theme.leaf, "\(displayName)'s first shift", "Tomorrow, the moment you're up")
                    planRow("chart.line.uptrend.xyaxis", Theme.sunLight, "You gain", "\(p.weeklyText) of morning every week", last: true)
                }
                .background(.white.opacity(0.06), in: .rect(cornerRadius: 20))
                primary("Looks perfect", action: next)
            }
        }
    }

    private func planRow(_ symbol: String, _ tint: Color, _ title: String, _ value: String, last: Bool = false) -> some View {
        VStack(spacing: 0) {
            HStack(spacing: 12) {
                Image(systemName: symbol)
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(tint)
                    .frame(width: 24)
                Text(title).font(.rounded(15, .semibold)).foregroundStyle(.secondary)
                Spacer(minLength: 8)
                Text(value).font(.rounded(15, .bold)).multilineTextAlignment(.trailing)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 11)
            if !last { Divider().opacity(0.4).padding(.leading, 50) }
        }
        .accessibilityElement(children: .combine)
    }

    // MARK: 10 · Commitment

    private var commitPage: some View {
        VStack(spacing: 16) {
            Text("Make it official")
                .font(.rounded(30, .heavy))
            Text("I'll get up at **\(wakeGoal.formatted(date: .omitted, time: .shortened))** on weekdays, for me and for \(model.state.companionName).")
                .font(.rounded(18, .medium))
                .multilineTextAlignment(.center)
            ZStack {
                Circle().stroke(.white.opacity(0.15), lineWidth: 8)
                Circle()
                    .trim(from: 0, to: holdProgress)
                    .stroke(Theme.sunGradient, style: StrokeStyle(lineWidth: 8, lineCap: .round))
                    .rotationEffect(.degrees(-90))
                Image(systemName: committed ? "checkmark" : "hand.thumbsup.fill")
                    .font(.system(size: 38, weight: .bold))
                    .foregroundStyle(committed ? Theme.leaf : Theme.sun)
                    .contentTransition(.symbolEffect(.replace))
            }
            .frame(width: 118, height: 118)
            .contentShape(.circle)
            .onLongPressGesture(minimumDuration: 1.2, maximumDistance: 40) {
                commit()
            } onPressingChanged: { pressing in
                guard !committed else { return }
                if pressing { Haptics.soft() }
                withAnimation(pressing ? .linear(duration: 1.2) : .spring(response: 0.3)) {
                    holdProgress = pressing ? 1 : 0
                }
            }
            .accessibilityElement()
            .accessibilityLabel("Hold to commit")
            .accessibilityAddTraits(.isButton)
            .accessibilityAction { commit() }
            Text(committed ? "Let's do this." : "Press and hold to commit")
                .font(.rounded(14, .semibold))
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
    }

    private func commit() {
        guard !committed else { return }
        committed = true
        holdProgress = 1
        Haptics.success()
        SoundService.shared.play(.complete, volume: 0.6)
        Task {
            try? await Task.sleep(for: .seconds(0.7))
            finish()
        }
    }

    private func finish() {
        let c = Calendar.current.dateComponents([.hour, .minute], from: wakeGoal)
        var alarm = model.state.alarms.first ?? AlarmItem()
        alarm.hour = c.hour ?? 7
        alarm.minute = c.minute ?? 0
        alarm.mission = mission
        alarm.target = mission.defaultTarget
        alarm.weekdays = [2, 3, 4, 5, 6]
        alarm.isEnabled = true
        alarm.createdAt = .now
        model.setEscapeProof(escapeProof)
        Task {
            await AlarmService.requestAuthorization()
            _ = try? await UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge])
            model.upsert(alarm)
            model.sendWelcomeLetters()
            withAnimation(.spring(response: 0.6, dampingFraction: 0.85)) {
                model.state.hasOnboarded = true
            }
        }
    }

    // MARK: Building blocks

    private func question(_ title: String, _ subtitle: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title).font(.rounded(26, .heavy))
            Text(subtitle).font(.rounded(15, .medium)).foregroundStyle(.secondary)
        }
        .padding(.bottom, 2)
    }

    private func option(_ emoji: String, _ title: String, selected: Bool, action: @escaping () -> Void) -> some View {
        Button {
            Haptics.select()
            action()
        } label: {
            HStack(spacing: 12) {
                Text(emoji).font(.system(size: 24))
                Text(title).font(.rounded(17, .semibold))
                Spacer()
                Image(systemName: selected ? "checkmark.circle.fill" : "circle")
                    .foregroundStyle(selected ? Theme.sun : .secondary)
            }
            .padding(.horizontal, 16)
            .frame(minHeight: 54)
            .background(.white.opacity(selected ? 0.14 : 0.06), in: .rect(cornerRadius: 18))
            .overlay(RoundedRectangle(cornerRadius: 18).strokeBorder(selected ? Theme.sun : .clear, lineWidth: 2))
            .contentShape(.rect)
        }
        .buttonStyle(.plain)
        .accessibilityAddTraits(selected ? .isSelected : [])
    }

    private func proof(_ symbol: String, _ tint: Color, _ title: String, _ detail: String) -> some View {
        HStack(alignment: .top, spacing: 14) {
            Image(systemName: symbol)
                .font(.system(size: 18, weight: .bold))
                .foregroundStyle(.white)
                .frame(width: 40, height: 40)
                .background(tint.gradient, in: .rect(cornerRadius: 12))
            VStack(alignment: .leading, spacing: 2) {
                Text(title).font(.rounded(17, .bold))
                Text(detail).font(.rounded(14, .medium)).foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .accessibilityElement(children: .combine)
    }

    private func primary(_ title: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(title)
                .font(.rounded(19, .bold))
                .frame(maxWidth: .infinity)
                .frame(height: 56)
        }
        .buttonStyle(.glassProminent)
        .tint(Theme.sun)
        .padding(.top, 6)
    }
}

/// The sprout's little speech bubble, with a tail pointing down at him.
/// Screen position of something in the 3D world (updated by the world, read by one small view).
@Observable
final class ScreenAnchor {
    var point: CGPoint?
}

/// The sprout's speech bubble, floating just above his head wherever he is.
struct SpeechAnchorLayer: View {
    var anchor: ScreenAnchor
    var text: String

    var body: some View {
        GeometryReader { geo in
            if let p = anchor.point, p.x > -50, p.x < geo.size.width + 50, p.y > 40 {
                let half: CGFloat = 160
                let x = min(max(p.x, half + 12), geo.size.width - half - 12)
                SproutSays(text: text, tailOffset: max(-half + 28, min(half - 28, p.x - x)))
                    .frame(width: half * 2, height: 240, alignment: .bottom)
                    .position(x: x, y: max(130, p.y) - 120)
                    .id(text)
                    .transition(.scale(scale: 0.7, anchor: .bottom).combined(with: .opacity))
                    .animation(.interactiveSpring(response: 0.35, dampingFraction: 0.9), value: p)
            }
        }
    }
}

struct SproutSays: View {
    var text: String
    /// Horizontal shift of the tail so it points at the sprout even when the bubble is kept on screen.
    var tailOffset: CGFloat = 0

    var body: some View {
        VStack(spacing: 0) {
            Text(text)
                .font(.rounded(16, .bold))
                .foregroundStyle(Theme.ink)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 18)
                .padding(.vertical, 11)
                .background(Theme.cream, in: .rect(cornerRadius: 20))
            Triangle()
                .fill(Theme.cream)
                .frame(width: 18, height: 10)
                .offset(x: tailOffset)
        }
        .shadow(color: .black.opacity(0.18), radius: 12, y: 5)
        .frame(maxWidth: 320)
        .accessibilityLabel(text)
    }

    private struct Triangle: Shape {
        func path(in r: CGRect) -> Path {
            Path { p in
                p.move(to: CGPoint(x: r.minX, y: r.minY))
                p.addLine(to: CGPoint(x: r.maxX, y: r.minY))
                p.addLine(to: CGPoint(x: r.midX, y: r.maxY))
                p.closeSubpath()
            }
        }
    }
}

extension String {
    var capitalizedFirst: String { prefix(1).uppercased() + dropFirst() }
}

// MARK: - The island over time

enum Showcase {
    struct Milestone {
        var label: String
        var title: String
        var detail: String
        var built: [String]
        var stage: SproutStage
        var hat: String?
    }

    static let milestones: [Milestone] = [
        Milestone(label: "Day 1", title: "A tent and a seedling",
                  detail: "Everyone starts here. Win your first morning and he heads off to his first shift.",
                  built: ["tent"], stage: .seedling, hat: nil),
        Milestone(label: "Week 1", title: "A campfire and a promotion",
                  detail: "Flowers, a lamppost, a bench for sunrises, and his first straw hat.",
                  built: ["tent", "campfire", "flowers", "lamppost", "bench"], stage: .sprout, hat: "straw"),
        Milestone(label: "Month 1", title: "A cozy cottage",
                  detail: "Go inside and decorate his room with furniture from the daily market.",
                  built: ["cottage", "campfire", "flowers", "lamppost", "bench", "treeRound", "mailbox", "garden", "pine"],
                  stage: .bud, hat: "beanie"),
        Milestone(label: "Month 3", title: "Your dream island",
                  detail: "A windmill, cherry blossoms, a telescope for stargazing, and vacations from the beach to the moon.",
                  built: ["cottage", "campfire", "flowers", "lamppost", "bench", "treeRound", "mailbox", "garden", "pine",
                          "pond", "lanterns", "treeBlossom", "telescope", "windmill"],
                  stage: .bloom, hat: "crown"),
    ]
}

// MARK: - Their numbers

struct OnboardingPlan {
    var now: Date
    var goal: Date
    var snoozeLevel: Int

    private static func minutes(_ d: Date) -> Int {
        let c = Calendar.current.dateComponents([.hour, .minute], from: d)
        return (c.hour ?? 0) * 60 + (c.minute ?? 0)
    }

    var nowMinutes: Int { Self.minutes(now) }
    var goalMinutes: Int { Self.minutes(goal) }
    /// Typical minutes lost to snoozing each morning (9-minute snoozes).
    var snoozeMinutes: Int { [5, 14, 36, 54][min(max(snoozeLevel, 0), 3)] }
    /// Extra morning each weekday: the earlier start plus the snoozes you no longer hit.
    var dailyGain: Int { max(0, nowMinutes - goalMinutes) + snoozeMinutes }
    var weeklyMinutes: Int { dailyGain * 5 }

    var weeklyText: String {
        let h = weeklyMinutes / 60, m = weeklyMinutes % 60
        if h == 0 { return "\(m)m" }
        return m == 0 ? "\(h)h" : "\(h)h \(m)m"
    }

    var yearDays: String {
        let days = Double(weeklyMinutes * 52) / 60 / 24
        return days >= 10 ? "\(Int(days.rounded()))" : days.formatted(.number.precision(.fractionLength(0...1)))
    }
}

/// "Before" (drifting, snooze-late) vs "with Riser" (settling onto the goal) over three weeks of weekdays.
struct WakeChart: View {
    var plan: OnboardingPlan

    private struct Point: Identifiable {
        var id: String { "\(series)\(day)" }
        var series: String
        var day: Int
        var minutes: Int
    }

    private var points: [Point] {
        let wobble = [0.9, 1.3, 0.6, 1.1, 1.5, 0.8, 1.2, 1.0, 1.4, 0.7, 1.1, 1.3, 0.9, 1.2, 1.0]
        let before = wobble.enumerated().map { i, w in
            Point(series: "Before", day: i + 1, minutes: plan.nowMinutes + Int(Double(plan.snoozeMinutes) * w))
        }
        let start = plan.nowMinutes
        let with = (0..<15).map { i in
            let t = min(1, Double(i) / 4)
            let eased = 1 - pow(1 - t, 2)
            return Point(series: "With Riser", day: i + 1,
                         minutes: Int(Double(start) + Double(plan.goalMinutes - start) * eased))
        }
        return before + with
    }

    private func label(_ minutes: Int) -> String {
        let m = ((minutes % 1440) + 1440) % 1440
        let d = Calendar.current.date(bySettingHour: m / 60, minute: m % 60, second: 0, of: .now) ?? .now
        return d.formatted(date: .omitted, time: .shortened)
    }

    var body: some View {
        let all = points.map(\.minutes)
        let lo = (all.min() ?? 0) - 15, hi = (all.max() ?? 0) + 15
        Chart(points) { p in
            LineMark(x: .value("Weekday", p.day), y: .value("Up at", p.minutes))
                .foregroundStyle(by: .value("Series", p.series))
                .interpolationMethod(.catmullRom)
                .lineStyle(StrokeStyle(lineWidth: p.series == "Before" ? 2.5 : 4, lineCap: .round,
                                       dash: p.series == "Before" ? [5, 5] : []))
        }
        .chartForegroundStyleScale(["Before": Color.white.opacity(0.45), "With Riser": Theme.sun])
        .chartYScale(domain: [hi, lo])
        .chartYAxis {
            AxisMarks(position: .leading, values: .automatic(desiredCount: 3)) { v in
                AxisGridLine().foregroundStyle(.white.opacity(0.1))
                AxisValueLabel {
                    if let m = v.as(Int.self) { Text(label(m)).font(.rounded(11, .semibold)) }
                }
            }
        }
        .chartXAxis {
            AxisMarks(values: [1, 6, 11, 15]) { v in
                AxisValueLabel {
                    if let d = v.as(Int.self) { Text(d == 1 ? "Today" : "Week \((d + 4) / 5)").font(.rounded(11, .semibold)) }
                }
            }
        }
        .chartLegend(position: .top, alignment: .leading)
        .accessibilityElement()
        .accessibilityLabel("Wake-up time. Before: around \(label(plan.nowMinutes + plan.snoozeMinutes)). With Riser: \(label(plan.goalMinutes)).")
    }
}

/// Wrapping multi-select chips.
struct FlowChips: View {
    var items: [String]
    @Binding var selected: Set<String>

    var body: some View {
        FlowLayout(spacing: 8) {
            ForEach(items, id: \.self) { item in
                let on = selected.contains(item)
                Button {
                    Haptics.select()
                    if on { selected.remove(item) } else { selected.insert(item) }
                } label: {
                    Text(item)
                        .font(.rounded(16, .semibold))
                        .padding(.horizontal, 14)
                        .frame(minHeight: 44)
                        .background(.white.opacity(on ? 0.16 : 0.06), in: .capsule)
                        .overlay(Capsule().strokeBorder(on ? Theme.sun : .clear, lineWidth: 2))
                        .contentShape(.capsule)
                }
                .buttonStyle(.plain)
                .accessibilityAddTraits(on ? .isSelected : [])
            }
        }
    }
}

struct FlowLayout: Layout {
    var spacing: CGFloat = 8

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let width = proposal.width ?? 320
        var x: CGFloat = 0, y: CGFloat = 0, row: CGFloat = 0
        for s in subviews {
            let size = s.sizeThatFits(.unspecified)
            if x + size.width > width, x > 0 {
                x = 0
                y += row + spacing
                row = 0
            }
            x += size.width + spacing
            row = max(row, size.height)
        }
        return CGSize(width: width, height: y + row)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var x = bounds.minX, y = bounds.minY, row: CGFloat = 0
        for s in subviews {
            let size = s.sizeThatFits(.unspecified)
            if x + size.width > bounds.maxX, x > bounds.minX {
                x = bounds.minX
                y += row + spacing
                row = 0
            }
            s.place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(size))
            x += size.width + spacing
            row = max(row, size.height)
        }
    }
}
