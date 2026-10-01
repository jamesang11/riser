import AVFoundation
import Observation
import SwiftUI
import Vision

/// Counts push-ups and squats from the front camera using Vision body-pose detection.
/// Frames are analysed in memory on-device; nothing is recorded or stored.
@Observable
@MainActor
final class PoseRepCounter: NSObject, RepCounter {
    enum Exercise { case pushup, squat }
    typealias Joint = VNHumanBodyPoseObservation.JointName

    let exercise: Exercise
    private(set) var count = 0
    private(set) var phase: Double = 0
    private(set) var statusText = "Setting up the camera…"
    /// Joint positions, normalized to the upright mirrored frame (0,0 = top-left).
    private(set) var joints: [Joint: CGPoint] = [:]
    /// Smoothed joints for drawing only (counting uses the raw ones), so the skeleton glides instead of jittering.
    private(set) var displayJoints: [Joint: CGPoint] = [:]
    private var missingFrames: [Joint: Int] = [:]
    /// The joint whose angle drives counting (elbow or knee), and that angle in degrees.
    private(set) var keyJoint: Joint?
    private(set) var keyAngle: Double?
    private(set) var isDown = false
    /// Size of the analysed frames (upright), used to map joints onto the preview.
    private(set) var frameSize = CGSize(width: 720, height: 1280)
    private(set) var cameraAvailable = true
    var onRep: (() -> Void)?

    let session = AVCaptureSession()
    private let output = AVCaptureVideoDataOutput()
    private let queue = DispatchQueue(label: "riser.pose", qos: .userInitiated)
    private let analyzer = PoseAnalyzer()
    private var smoothedAngle: Double?
    private var lastRepTime = Date.distantPast
    private var lastSeen = Date.distantPast
    /// Facing-the-camera push-ups: the shoulder-to-hands height (in shoulder widths) at the top of a rep.
    private var frontTop: Double = 0
    private var stopped = false
    /// Vision's confidence per joint for the latest frame (used to pick the side facing the camera).
    private var confidence: [Joint: Float] = [:]

    init(exercise: Exercise) {
        self.exercise = exercise
        super.init()
    }

    func start() {
        #if DEBUG
        // Screenshots: run the real pose detection on a still photo instead of the camera.
        if let path = UserDefaults.standard.string(forKey: "demoPoseImage"), let image = UIImage(contentsOfFile: path) {
            debugUseStill(image, reps: UserDefaults.standard.object(forKey: "demoPoseCount") as? Int
                          ?? Int(UserDefaults.standard.string(forKey: "demoPoseCount") ?? "") ?? 6)
            return
        }
        #endif
        stopped = false
        AVCaptureDevice.requestAccess(for: .video) { granted in
            Task { @MainActor in
                // The mission may have ended while the permission prompt was up: don't turn the camera on.
                guard !self.stopped else { return }
                if granted { self.configure() } else {
                    self.cameraAvailable = false
                    self.statusText = "Camera access is off"
                }
            }
        }
    }

    private func configure() {
        guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .front),
              let input = try? AVCaptureDeviceInput(device: device) else {
            cameraAvailable = false
            statusText = "No camera available"
            return
        }
        session.beginConfiguration()
        session.sessionPreset = .hd1280x720
        if session.canAddInput(input) { session.addInput(input) }
        output.alwaysDiscardsLateVideoFrames = true
        output.videoSettings = [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_420YpCbCr8BiPlanarFullRange]
        output.setSampleBufferDelegate(analyzer, queue: queue)
        if session.canAddOutput(output) { session.addOutput(output) }
        if let connection = output.connection(with: .video) {
            if connection.isVideoRotationAngleSupported(90) { connection.videoRotationAngle = 90 }
            if connection.isVideoMirroringSupported {
                connection.automaticallyAdjustsVideoMirroring = false
                connection.isVideoMirrored = true
            }
        }
        session.commitConfiguration()
        analyzer.onResult = { [weak self] points, confidence, size in
            Task { @MainActor in self?.ingest(points, confidence: confidence, frame: size) }
        }
        let s = session
        queue.async { s.startRunning() }
        statusText = exercise == .squat
            ? "Prop your phone up about 2 m away, facing you"
            : "Set your phone down in front of you or to your side"
    }

    func stop() {
        stopped = true
        let s = session
        queue.async { if s.isRunning { s.stopRunning() } }
    }

    // MARK: Analysis

    private func ingest(_ points: [Joint: CGPoint], confidence: [Joint: Float], frame: CGSize) {
        guard !stopped else { return }
        frameSize = frame
        joints = points
        smoothDisplay(points)
        self.confidence = confidence
        guard !points.isEmpty else {
            if Date.now.timeIntervalSince(lastSeen) > 1.5 {
                statusText = exercise == .squat ? "Step into view so I can see your whole body" : "Get into view of the camera"
                keyJoint = nil
                keyAngle = nil
            }
            return
        }
        lastSeen = .now
        switch exercise {
        case .squat: evaluateSquat(points)
        case .pushup: evaluatePushup(points)
        }
    }

    private func smoothDisplay(_ points: [Joint: CGPoint]) {
        var out: [Joint: CGPoint] = [:]
        for (j, p) in points {
            if let old = displayJoints[j] {
                // Ease towards the new position; catch up faster on big moves so it never trails behind.
                let k: CGFloat = hypot(p.x - old.x, p.y - old.y) > 0.12 ? 0.7 : 0.35
                out[j] = CGPoint(x: old.x + (p.x - old.x) * k, y: old.y + (p.y - old.y) * k)
            } else {
                out[j] = p
            }
            missingFrames[j] = 0
        }
        // A joint Vision loses for a moment stays put for a few frames instead of blinking.
        for (j, old) in displayJoints where points[j] == nil {
            let n = (missingFrames[j] ?? 0) + 1
            missingFrames[j] = n
            if n <= 4 { out[j] = old }
        }
        displayJoints = out
    }

    /// Picks the side (left/right) with the most visible chain of joints: side-on, the far limb is
    /// often "found" at low confidence in the wrong place, so prefer the chain Vision is surest about.
    private func bestChain(_ p: [Joint: CGPoint], _ chains: [(Joint, Joint, Joint)]) -> (Joint, Joint, Joint)? {
        chains.filter { p[$0.0] != nil && p[$0.1] != nil && p[$0.2] != nil }
            .max { score($0) < score($1) }
    }

    private func score(_ c: (Joint, Joint, Joint)) -> Float {
        min(confidence[c.0] ?? 0, confidence[c.1] ?? 0, confidence[c.2] ?? 0)
    }

    private func angle(_ a: CGPoint, _ b: CGPoint, _ c: CGPoint) -> Double {
        // Account for the frame aspect so angles are measured in real pixel space.
        let s = frameSize
        let v1 = CGVector(dx: (a.x - b.x) * s.width, dy: (a.y - b.y) * s.height)
        let v2 = CGVector(dx: (c.x - b.x) * s.width, dy: (c.y - b.y) * s.height)
        let dot = v1.dx * v2.dx + v1.dy * v2.dy
        let m = sqrt(v1.dx * v1.dx + v1.dy * v1.dy) * sqrt(v2.dx * v2.dx + v2.dy * v2.dy)
        guard m > 0 else { return 180 }
        return Double(acos(max(-1, min(1, Double(dot / m))))) * 180 / .pi
    }

    private func smooth(_ value: Double) -> Double {
        let s = (smoothedAngle ?? value) * 0.45 + value * 0.55
        smoothedAngle = s
        return s
    }

    private func evaluateSquat(_ p: [Joint: CGPoint]) {
        let chains: [(Joint, Joint, Joint)] = [(.leftHip, .leftKnee, .leftAnkle), (.rightHip, .rightKnee, .rightAnkle)]
        guard let (hip, knee, ankle) = bestChain(p, chains) else {
            statusText = "Step back so I can see your knees and feet"
            keyJoint = nil
            return
        }
        let a = smooth(angle(p[hip]!, p[knee]!, p[ankle]!))
        keyJoint = knee
        keyAngle = a
        // Facing the camera the thigh is foreshortened, so the 2D knee angle barely drops below ~130°
        // even in a deep squat. Also measure how far the hip has dropped toward the knee, relative to
        // the shin (≈1 standing, ≈0 at parallel); that works from the front and from the side.
        let shin = (p[ankle]!.y - p[knee]!.y) * frameSize.height
        let thigh = (p[knee]!.y - p[hip]!.y) * frameSize.height
        let drop = shin > 8 ? max(0, min(1.5, thigh / shin)) : 1
        let depth = max((170 - a) / 80, (1 - drop) / 0.55)
        phase = max(0, min(1, depth))
        // Express both as one "angle" so the same hysteresis applies: down past 115° or hip ≈ 0.5 shin,
        // up only once the leg is straight again (above 155° and hip back up).
        let effective = drop < 0.5 ? min(a, 110) : (drop < 0.7 ? min(a, 150) : a)
        step(angle: effective, downBelow: 115, upAbove: 155,
             downText: "Now stand up tall!", upText: "Squat down, hips back")
    }

    private func evaluatePushup(_ p: [Joint: CGPoint]) {
        if evaluateFrontPushup(p) { return }
        let chains: [(Joint, Joint, Joint)] = [(.leftShoulder, .leftElbow, .leftWrist), (.rightShoulder, .rightElbow, .rightWrist)]
        guard let (shoulder, elbow, wrist) = bestChain(p, chains) else {
            statusText = "Keep your arms in view of the camera"
            keyJoint = nil
            return
        }
        // Push-ups happen close to horizontal: the back can tilt (knee push-ups count too), but not stand up.
        let hip = p[shoulder == .leftShoulder ? .leftHip : .rightHip]
        if let hip {
            let dx = abs(hip.x - p[shoulder]!.x) * frameSize.width
            let dy = abs(hip.y - p[shoulder]!.y) * frameSize.height
            if dy > dx * 1.5 {
                statusText = "Get into a plank (knees down is fine)"
                keyJoint = elbow
                keyAngle = nil
                return
            }
        }
        let a = smooth(angle(p[shoulder]!, p[elbow]!, p[wrist]!))
        keyJoint = elbow
        keyAngle = a
        phase = max(0, min(1, (165 - a) / 55))
        // A bend to 110° is a real rep for knee push-ups too; full push-ups go well past it.
        step(angle: a, downBelow: 110, upAbove: 145,
             downText: "Push up!", upText: "Lower your chest")
    }

    /// Phone in front of the player (both shoulders visible side by side). Elbow angles are hard to read
    /// head-on, so a rep is counted from how far the shoulders drop towards the hands and back up.
    /// Returns false when the player isn't facing the camera, so the side-on logic takes over.
    private func evaluateFrontPushup(_ p: [Joint: CGPoint]) -> Bool {
        let w = frameSize.width, h = frameSize.height
        guard let ls = p[.leftShoulder], let rs = p[.rightShoulder] else { return false }
        let shoulderWidth = abs(ls.x - rs.x) * w
        guard shoulderWidth > 0.12 * w else { return false }
        let wrists = [p[.leftWrist], p[.rightWrist]].compactMap { $0 }
        guard !wrists.isEmpty else {
            statusText = "Keep your hands in view of the camera"
            keyJoint = nil
            keyAngle = nil
            return true
        }
        let shoulderY = (ls.y + rs.y) / 2 * h
        let wristY = wrists.map(\.y).reduce(0, +) / CGFloat(wrists.count) * h
        // Standing up: the hips sit far below the shoulders. In a plank (knees down or not) they're foreshortened.
        let hips = [p[.leftHip], p[.rightHip]].compactMap { $0 }
        if !hips.isEmpty {
            let hipY = hips.map(\.y).reduce(0, +) / CGFloat(hips.count) * h
            if hipY - shoulderY > shoulderWidth * 1.2 {
                statusText = "Get into a plank (knees down is fine)"
                keyJoint = nil
                keyAngle = nil
                return true
            }
        }
        let r = Double(max(0, wristY - shoulderY) / shoulderWidth)
        // Remember the top of the rep, forgetting it only slowly so a pause at the bottom never counts.
        frontTop = max(r, frontTop * 0.999)
        guard frontTop > 0.4 else { return true }
        // Express it like an elbow angle (straight arms = 180°) so the usual rep thresholds apply.
        let a = smooth(180 * r / frontTop)
        keyJoint = wrists.count == 2 ? nil : (p[.leftWrist] != nil ? .leftElbow : .rightElbow)
        keyAngle = a
        phase = max(0, min(1, (165 - a) / 55))
        step(angle: a, downBelow: 110, upAbove: 145, downText: "Push up!", upText: "Lower your chest")
        return true
    }

    private func step(angle a: Double, downBelow: Double, upAbove: Double, downText: String, upText: String) {
        if !isDown && a < downBelow {
            isDown = true
            statusText = downText
        } else if isDown && a > upAbove {
            isDown = false
            // Ignore jitter: a real rep takes at least ~0.5 s.
            if Date.now.timeIntervalSince(lastRepTime) > 0.5 {
                lastRepTime = .now
                count += 1
                onRep?()
            }
            statusText = upText
        } else if !isDown && ["Step", "Turn", "Prop", "Set", "Get", "Keep", "Camera"].contains(where: { statusText.hasPrefix($0) }) {
            statusText = upText
        }
    }

    #if DEBUG
    func debugRep() { count += 1; onRep?() }

    /// The still photo standing in for the camera (screenshots only).
    private(set) var stillImage: UIImage?

    func debugUseStill(_ image: UIImage, reps: Int) {
        stillImage = image
        cameraAvailable = true
        guard let cg = image.cgImage else { return }
        let request = VNDetectHumanBodyPoseRequest()
        try? VNImageRequestHandler(cgImage: cg, orientation: .up).perform([request])
        var points: [Joint: CGPoint] = [:]
        if let body = request.results?.max(by: { $0.confidence < $1.confidence }),
           let all = try? body.recognizedPoints(.all) {
            for (name, p) in all where p.confidence > 0.3 {
                points[name] = CGPoint(x: p.location.x, y: 1 - p.location.y)
            }
        }
        // The simulator can't run body-pose detection: use joints Vision found on a Mac for the same photo.
        if points.isEmpty, let path = UserDefaults.standard.string(forKey: "demoPoseJoints"),
           let data = FileManager.default.contents(atPath: path),
           let json = try? JSONSerialization.jsonObject(with: data) as? [String: [Double]] {
            for (key, v) in json where v.count >= 2 {
                points[Joint(rawValue: VNRecognizedPointKey(rawValue: key))] = CGPoint(x: v[0], y: v[1])
            }
        }
        frameSize = CGSize(width: cg.width, height: cg.height)
        joints = points
        displayJoints = points
        // Mark the working elbow like a live rep would.
        if let elbow: Joint = [.rightElbow, .leftElbow].first(where: { points[$0] != nil }),
           let s = points[elbow == .rightElbow ? .rightShoulder : .leftShoulder],
           let w = points[elbow == .rightElbow ? .rightWrist : .leftWrist], let e = points[elbow] {
            keyJoint = elbow
            keyAngle = angle(s, e, w)
        }
        count = reps
        phase = 0.35
        statusText = "Lower your chest"
        // Filming: count reps on a beat so the mission plays out without a person in front of the camera.
        let tick = UserDefaults.standard.double(forKey: "demoPoseTick")
        if tick > 0 {
            Task { @MainActor in
                try? await Task.sleep(for: .seconds(1.2))
                while !stopped {
                    statusText = "Push up!"
                    phase = 0.9
                    try? await Task.sleep(for: .seconds(tick * 0.5))
                    guard !stopped else { break }
                    count += 1
                    phase = 0.1
                    statusText = "Lower your chest"
                    onRep?()
                    try? await Task.sleep(for: .seconds(tick * 0.5))
                }
            }
        }
        print("🦴 pose joints detected: \(points.count)")
    }
    #endif
}

/// Runs Vision on camera frames off the main thread.
private final class PoseAnalyzer: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate, @unchecked Sendable {
    var onResult: (([VNHumanBodyPoseObservation.JointName: CGPoint], [VNHumanBodyPoseObservation.JointName: Float], CGSize) -> Void)?
    private let request = VNDetectHumanBodyPoseRequest()

    func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer, from connection: AVCaptureConnection) {
        guard let pixels = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        let size = CGSize(width: CVPixelBufferGetWidth(pixels), height: CVPixelBufferGetHeight(pixels))
        let handler = VNImageRequestHandler(cvPixelBuffer: pixels, orientation: .up)
        var points: [VNHumanBodyPoseObservation.JointName: CGPoint] = [:]
        var confidence: [VNHumanBodyPoseObservation.JointName: Float] = [:]
        if (try? handler.perform([request])) != nil,
           let body = request.results?.max(by: { $0.confidence < $1.confidence }),
           let all = try? body.recognizedPoints(.all) {
            for (name, p) in all where p.confidence > 0.3 {
                // Vision's origin is bottom-left; flip to top-left.
                points[name] = CGPoint(x: p.location.x, y: 1 - p.location.y)
                confidence[name] = p.confidence
            }
        }
        onResult?(points, confidence, size)
    }
}

// MARK: - Preview + skeleton

/// Live mirrored camera preview.
struct CameraPreview: UIViewRepresentable {
    let session: AVCaptureSession
    var mirrored: Bool = true

    final class PreviewView: UIView {
        override class var layerClass: AnyClass { AVCaptureVideoPreviewLayer.self }
        var previewLayer: AVCaptureVideoPreviewLayer { layer as! AVCaptureVideoPreviewLayer }
    }

    func makeUIView(context: Context) -> PreviewView {
        let v = PreviewView()
        v.previewLayer.session = session
        v.previewLayer.videoGravity = .resizeAspectFill
        v.backgroundColor = .black
        return v
    }

    func updateUIView(_ v: PreviewView, context: Context) {
        if let c = v.previewLayer.connection {
            if c.isVideoRotationAngleSupported(90) { c.videoRotationAngle = 90 }
            if c.isVideoMirroringSupported {
                c.automaticallyAdjustsVideoMirroring = false
                c.isVideoMirrored = mirrored
            }
        }
    }
}

/// Glowing stick-figure drawn over the camera, matching the aspect-fill preview.
struct SkeletonOverlay: View {
    var joints: [VNHumanBodyPoseObservation.JointName: CGPoint]
    var frameSize: CGSize
    var keyJoint: VNHumanBodyPoseObservation.JointName?
    var keyAngle: Double?
    var isDown: Bool

    private static let bones: [(VNHumanBodyPoseObservation.JointName, VNHumanBodyPoseObservation.JointName)] = [
        (.leftShoulder, .rightShoulder), (.leftHip, .rightHip),
        (.leftShoulder, .leftHip), (.rightShoulder, .rightHip),
        (.leftShoulder, .leftElbow), (.leftElbow, .leftWrist),
        (.rightShoulder, .rightElbow), (.rightElbow, .rightWrist),
        (.leftHip, .leftKnee), (.leftKnee, .leftAnkle),
        (.rightHip, .rightKnee), (.rightKnee, .rightAnkle),
        (.neck, .nose),
    ]

    var body: some View {
        Canvas { ctx, size in
            let scale = max(size.width / frameSize.width, size.height / frameSize.height)
            let w = frameSize.width * scale, h = frameSize.height * scale
            let ox = (size.width - w) / 2, oy = (size.height - h) / 2
            func pt(_ j: VNHumanBodyPoseObservation.JointName) -> CGPoint? {
                joints[j].map { CGPoint(x: ox + $0.x * w, y: oy + $0.y * h) }
            }
            let accent = isDown ? Color(red: 0.62, green: 0.86, blue: 0.52) : Color(red: 1, green: 0.8, blue: 0.4)
            for (a, b) in Self.bones {
                guard let p = pt(a), let q = pt(b) else { continue }
                var path = Path()
                path.move(to: p)
                path.addLine(to: q)
                ctx.stroke(path, with: .color(accent.opacity(0.35)), style: StrokeStyle(lineWidth: 14, lineCap: .round))
                ctx.stroke(path, with: .color(.white.opacity(0.95)), style: StrokeStyle(lineWidth: 4, lineCap: .round))
            }
            for (j, _) in joints {
                guard let p = pt(j) else { continue }
                let r: CGFloat = j == keyJoint ? 11 : 5
                ctx.fill(Path(ellipseIn: CGRect(x: p.x - r, y: p.y - r, width: 2 * r, height: 2 * r)),
                         with: .color(j == keyJoint ? accent : .white))
            }
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }
}
