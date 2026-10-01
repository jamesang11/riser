import AVFoundation
import Observation
import SwiftUI
import Vision

/// Something to find around the home. `labels` are Vision classifier identifiers that count as a match.
struct HuntTarget: Identifiable, Hashable, Sendable {
    let id: String
    let name: String
    let emoji: String
    let labels: [String]
}

enum HuntCatalog {
    /// Everyday things that are usually *out of bed's reach*.
    static let targets: [HuntTarget] = [
        HuntTarget(id: "cup", name: "a cup or mug", emoji: "☕️", labels: ["cup", "mug", "coffee"]),
        HuntTarget(id: "shoes", name: "your shoes", emoji: "👟", labels: ["shoes", "sneaker", "footwear", "boot", "sandal"]),
        HuntTarget(id: "book", name: "a book", emoji: "📚", labels: ["book", "bookshelf"]),
        HuntTarget(id: "plant", name: "a plant", emoji: "🪴", labels: ["plant", "decorative_plant", "flower"]),
        HuntTarget(id: "fridge", name: "the fridge", emoji: "🧊", labels: ["refrigerator"]),
        HuntTarget(id: "sink", name: "the kitchen sink", emoji: "🚰", labels: ["kitchen_sink", "kitchen_faucet"]),
        HuntTarget(id: "bottle", name: "a bottle", emoji: "🧴", labels: ["bottle", "wine_bottle"]),
        HuntTarget(id: "spoon", name: "a spoon or fork", emoji: "🥄", labels: ["spoon", "fork", "utensil"]),
        HuntTarget(id: "lamp", name: "a lamp", emoji: "💡", labels: ["lamp"]),
        HuntTarget(id: "door", name: "a door", emoji: "🚪", labels: ["door"]),
        HuntTarget(id: "clock", name: "a clock", emoji: "🕰️", labels: ["clock"]),
        HuntTarget(id: "kettle", name: "a kettle or teapot", emoji: "🫖", labels: ["kettle", "teapot"]),
        HuntTarget(id: "chair", name: "a chair", emoji: "🪑", labels: ["chair", "armchair", "swivel_chair", "folding_chair", "chair_other"]),
        HuntTarget(id: "window", name: "a window", emoji: "🪟", labels: ["window"]),
    ]

    static func pick(_ n: Int) -> [HuntTarget] {
        Array(targets.shuffled().prefix(max(1, min(n, targets.count))))
    }
}

/// Finds objects with the back camera using on-device image classification.
@Observable
@MainActor
final class ItemHuntCounter: NSObject, RepCounter {
    private(set) var targets: [HuntTarget]
    private(set) var count = 0
    private(set) var phase: Double = 0
    private(set) var statusText = "Point your camera around your home"
    /// What the camera thinks it's looking at right now (for fun feedback).
    private(set) var seeing: String?
    private(set) var justFound: HuntTarget?
    private(set) var cameraAvailable = true
    var onRep: (() -> Void)?

    let session = AVCaptureSession()
    private let output = AVCaptureVideoDataOutput()
    private let queue = DispatchQueue(label: "riser.hunt", qos: .userInitiated)
    private let classifier = HuntClassifier()
    private var streak = 0
    private var stopped = false
    /// Items recently swapped away, so "Try another item" doesn't bounce straight back to them.
    private var recentlySkipped: [String] = []

    var current: HuntTarget? { count < targets.count ? targets[count] : nil }

    init(count n: Int) {
        targets = HuntCatalog.pick(n)
        super.init()
    }

    func start() {
        stopped = false
        AVCaptureDevice.requestAccess(for: .video) { granted in
            Task { @MainActor in
                // The mission may have ended while the permission prompt was up: don't turn the camera on.
                guard !self.stopped else { return }
                granted ? self.configure() : self.unavailable("Camera access is off")
            }
        }
    }

    /// Swaps the current item for a different random one (never the same item straight back).
    func tryAnother() {
        guard let old = current else { return }
        recentlySkipped = Array((recentlySkipped + [old.id]).suffix(2))
        let taken = Set(targets.map(\.id) + recentlySkipped)
        let pool = HuntCatalog.targets.filter { !taken.contains($0.id) }
        guard let next = pool.randomElement() ?? HuntCatalog.targets.filter({ $0.id != old.id }).randomElement() else { return }
        targets[count] = next
        streak = 0
        phase = 0
        seeing = nil
        statusText = "Find \(next.name) \(next.emoji)"
    }

    private func unavailable(_ text: String) {
        cameraAvailable = false
        statusText = text
    }

    private func configure() {
        guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back),
              let input = try? AVCaptureDeviceInput(device: device) else {
            unavailable("No camera available")
            return
        }
        session.beginConfiguration()
        session.sessionPreset = .hd1280x720
        if session.canAddInput(input) { session.addInput(input) }
        output.alwaysDiscardsLateVideoFrames = true
        output.setSampleBufferDelegate(classifier, queue: queue)
        if session.canAddOutput(output) { session.addOutput(output) }
        if let c = output.connection(with: .video), c.isVideoRotationAngleSupported(90) { c.videoRotationAngle = 90 }
        session.commitConfiguration()
        classifier.onResult = { [weak self] results in
            Task { @MainActor in self?.ingest(results) }
        }
        let s = session
        queue.async { s.startRunning() }
    }

    func stop() {
        stopped = true
        let s = session
        queue.async { if s.isRunning { s.stopRunning() } }
    }

    private func ingest(_ results: [(String, Float)]) {
        guard !stopped, let target = current else { return }
        if let top = results.first, top.1 > 0.25 {
            seeing = top.0.replacingOccurrences(of: "_", with: " ")
        }
        let hit = results.contains { target.labels.contains($0.0) && $0.1 > 0.22 }
        streak = hit ? streak + 1 : max(0, streak - 1)
        phase = min(1, Double(streak) / 3)
        statusText = hit ? "That looks like it… hold steady!" : "Find \(target.name) \(target.emoji)"
        if streak >= 3 {
            streak = 0
            phase = 0
            justFound = target
            count += 1
            onRep?()
            statusText = current.map { "Found it! Next: \($0.name) \($0.emoji)" } ?? "Found everything!"
        }
    }

    #if DEBUG
    func debugRep() {
        guard current != nil else { return }
        justFound = current
        count += 1
        onRep?()
    }
    #endif
}

private final class HuntClassifier: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate, @unchecked Sendable {
    var onResult: (([(String, Float)]) -> Void)?
    private let request = VNClassifyImageRequest()
    private var last = Date.distantPast

    func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer, from connection: AVCaptureConnection) {
        // A few classifications per second is plenty and keeps the phone cool.
        guard Date.now.timeIntervalSince(last) > 0.25, let pixels = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        last = .now
        let handler = VNImageRequestHandler(cvPixelBuffer: pixels, orientation: .up)
        guard (try? handler.perform([request])) != nil, let obs = request.results else { return }
        let top = obs.prefix(25).map { ($0.identifier, $0.confidence) }
        onResult?(Array(top))
    }
}
