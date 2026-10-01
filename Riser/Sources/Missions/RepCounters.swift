import AVFoundation
import CoreMotion
import Foundation
import Observation
import UIKit

/// Common interface for sensor-driven missions.
@MainActor
protocol RepCounter: AnyObject {
    var count: Int { get }
    /// 0...1 how far through the current movement the player is (drives the sprout mirror animation).
    var phase: Double { get }
    var statusText: String { get }
    var onRep: (() -> Void)? { get set }
    /// The sensor can't be used (unsupported or permission denied): the mission should fall back.
    var isUnavailable: Bool { get }
    func start()
    func stop()
    #if DEBUG
    func debugRep()
    #endif
}

extension RepCounter {
    var isUnavailable: Bool { false }
}

// MARK: - Push-ups (TrueDepth camera, falling back to the proximity sensor)

/// Phone lies flat on the floor, screen up, under the player's face.
/// The front TrueDepth camera measures the distance to the player's face/chest: close → down, far → up.
/// It works in a dark bedroom because TrueDepth uses infrared. No images are stored or displayed.
@Observable
@MainActor
final class PushupCounter: NSObject, RepCounter {
    private(set) var count = 0
    private(set) var phase: Double = 0
    private(set) var statusText = "Get into position"
    private(set) var distance: Double? = nil
    private(set) var usingProximity = false
    var onRep: (() -> Void)?

    private let session = AVCaptureSession()
    private let depthOutput = AVCaptureDepthDataOutput()
    private let queue = DispatchQueue(label: "riser.depth")
    private var isDown = false
    private var smoothed: Double?
    private var stopped = false

    // Hysteresis thresholds in metres.
    private let downThreshold = 0.26
    private let upThreshold = 0.38

    func start() {
        guard let device = AVCaptureDevice.default(.builtInTrueDepthCamera, for: .depthData, position: .front) else {
            startProximity()
            return
        }
        AVCaptureDevice.requestAccess(for: .video) { granted in
            Task { @MainActor in
                guard !self.stopped else { return }
                granted ? self.startDepth(device) : self.startProximity()
            }
        }
    }

    private func startDepth(_ device: AVCaptureDevice) {
        do {
            session.beginConfiguration()
            session.sessionPreset = .vga640x480
            let input = try AVCaptureDeviceInput(device: device)
            if session.canAddInput(input) { session.addInput(input) }
            if session.canAddOutput(depthOutput) { session.addOutput(depthOutput) }
            depthOutput.isFilteringEnabled = true
            depthOutput.setDelegate(self, callbackQueue: queue)
            if let format = device.activeFormat.supportedDepthDataFormats
                .filter({ CMFormatDescriptionGetMediaSubType($0.formatDescription) == kCVPixelFormatType_DepthFloat16 })
                .max(by: { CMVideoFormatDescriptionGetDimensions($0.formatDescription).width < CMVideoFormatDescriptionGetDimensions($1.formatDescription).width }) {
                try device.lockForConfiguration()
                device.activeDepthDataFormat = format
                device.unlockForConfiguration()
            }
            session.commitConfiguration()
            let s = session
            queue.async { s.startRunning() }
            statusText = "Lower your chest toward the phone"
        } catch {
            startProximity()
        }
    }

    private func startProximity() {
        usingProximity = true
        UIDevice.current.isProximityMonitoringEnabled = true
        NotificationCenter.default.addObserver(self, selector: #selector(proximityChanged),
                                               name: UIDevice.proximityStateDidChangeNotification, object: nil)
        statusText = "Touch your nose to the screen on each rep"
    }

    @objc private func proximityChanged() {
        let near = UIDevice.current.proximityState
        phase = near ? 1 : 0
        if near { isDown = true } else if isDown { isDown = false; registerRep() }
    }

    func stop() {
        stopped = true
        let s = session
        queue.async { if s.isRunning { s.stopRunning() } }
        if usingProximity {
            UIDevice.current.isProximityMonitoringEnabled = false
            NotificationCenter.default.removeObserver(self)
        }
    }

    private func registerRep() {
        count += 1
        onRep?()
    }

    fileprivate func ingest(_ d: Double?) {
        guard let d else {
            // No valid depth: when the player was already close this means "very close" (below minimum range).
            if let s = smoothed, s < upThreshold { process(0.15) } else { statusText = "Can't see you. Lean over the phone" }
            return
        }
        process(d)
    }

    private func process(_ d: Double) {
        let s = (smoothed ?? d) * 0.55 + d * 0.45
        smoothed = s
        distance = s
        phase = max(0, min(1, (0.55 - s) / (0.55 - 0.18)))
        if !isDown && s < downThreshold {
            isDown = true
            statusText = "Now push up!"
        } else if isDown && s > upThreshold {
            isDown = false
            statusText = "Nice! Keep going"
            registerRep()
        } else if !isDown && s > 0.9 {
            statusText = "Get closer. Phone under your face"
        }
    }

    #if DEBUG
    func debugRep() { registerRep() }
    #endif
}

extension PushupCounter: AVCaptureDepthDataOutputDelegate {
    nonisolated func depthDataOutput(_ output: AVCaptureDepthDataOutput, didOutput depthData: AVDepthData,
                                     timestamp: CMTime, connection: AVCaptureConnection) {
        let converted = depthData.depthDataType == kCVPixelFormatType_DepthFloat32
            ? depthData : depthData.converting(toDepthDataType: kCVPixelFormatType_DepthFloat32)
        let map = converted.depthDataMap
        CVPixelBufferLockBaseAddress(map, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(map, .readOnly) }
        let w = CVPixelBufferGetWidth(map)
        let h = CVPixelBufferGetHeight(map)
        let rowBytes = CVPixelBufferGetBytesPerRow(map)
        guard let base = CVPixelBufferGetBaseAddress(map) else { return }
        // Sample the central 40% of the frame and take a low percentile (closest body part).
        var samples: [Float] = []
        samples.reserveCapacity(400)
        let x0 = Int(Double(w) * 0.3), x1 = Int(Double(w) * 0.7)
        let y0 = Int(Double(h) * 0.3), y1 = Int(Double(h) * 0.7)
        let step = max(1, (x1 - x0) / 20)
        for y in stride(from: y0, to: y1, by: step) {
            let row = base.advanced(by: y * rowBytes).assumingMemoryBound(to: Float32.self)
            for x in stride(from: x0, to: x1, by: step) {
                let v = row[x]
                if v.isFinite && v > 0.05 && v < 3 { samples.append(v) }
            }
        }
        let value: Double?
        if samples.count < 25 {
            value = nil
        } else {
            samples.sort()
            value = Double(samples[samples.count / 4])
        }
        Task { @MainActor [weak self] in self?.ingest(value) }
    }
}

// MARK: - Squats (device motion)

/// Phone held against the chest. Vertical velocity from the accelerometer: a descent followed by an ascent is one squat.
@Observable
@MainActor
final class SquatCounter: RepCounter {
    private(set) var count = 0
    private(set) var phase: Double = 0
    private(set) var statusText = "Hold your phone to your chest"
    private(set) var isUnavailable = false
    var onRep: (() -> Void)?

    private let motion = CMMotionManager()
    private var velocity = 0.0
    private var position = 0.0
    private var sawDescent = false
    private var descentTime: TimeInterval = 0
    private var lastRep: TimeInterval = 0

    func start() {
        guard motion.isDeviceMotionAvailable else {
            statusText = "Motion sensors unavailable"
            isUnavailable = true
            return
        }
        motion.deviceMotionUpdateInterval = 1.0 / 60
        motion.startDeviceMotionUpdates(to: .main) { [weak self] data, _ in
            guard let self, let data else { return }
            MainActor.assumeIsolated { self.ingest(data) }
        }
    }

    func stop() { motion.stopDeviceMotionUpdates() }

    private func ingest(_ m: CMDeviceMotion) {
        let g = m.gravity
        let a = m.userAcceleration
        // Acceleration along "up" (opposite gravity), in m/s².
        let up = -(a.x * g.x + a.y * g.y + a.z * g.z) * 9.81
        let dt = 1.0 / 60
        velocity = velocity * 0.975 + up * dt
        position = position * 0.985 + velocity * dt
        phase = max(0, min(1, -position / 0.25))
        let t = m.timestamp
        if velocity < -0.32 && !sawDescent {
            sawDescent = true
            descentTime = t
            statusText = "Down…"
        } else if sawDescent && velocity > 0.30 {
            sawDescent = false
            if t - lastRep > 0.9 && t - descentTime < 3.5 {
                lastRep = t
                count += 1
                statusText = "Up! Great squat"
                onRep?()
            }
        } else if sawDescent && t - descentTime > 3.5 {
            sawDescent = false
        }
    }

    #if DEBUG
    func debugRep() { count += 1; onRep?() }
    #endif
}

// MARK: - Math (the mission view draws its own keypad; nothing to sense)

@Observable
@MainActor
final class MathPlaceholderCounter: RepCounter {
    private(set) var count = 0
    private(set) var phase: Double = 0
    private(set) var statusText = ""
    var onRep: (() -> Void)?

    func start() {}
    func stop() {}
    #if DEBUG
    func debugRep() {}
    #endif
}
