import QuartzCore
import UIKit
import SceneKit

/// Frame-timing logger for on-device tuning. Off unless launched with `-perfLog YES`; prints a line every
/// 3 s: main-thread frame rate and hitches (display link), 3D render rate, and CPU time spent in our frame loop.
final class PerfProbe: NSObject, SCNSceneRendererDelegate, @unchecked Sendable {
    static let enabled = UserDefaults.standard.bool(forKey: "perfLog")

    /// Times a block and logs it when it takes longer than `threshold` ms (only with `-perfLog YES`).
    @discardableResult
    static func measure<T>(_ label: String, threshold: Double = 4, _ body: () -> T) -> T {
        guard enabled else { return body() }
        let start = CACurrentMediaTime()
        let result = body()
        let ms = (CACurrentMediaTime() - start) * 1000
        if ms > threshold { fputs(String(format: "[slow] %@ %.1f ms\n", label, ms), stderr) }
        return result
    }

    private let lock = NSLock()
    private var renders = 0
    private var mainFrames = 0
    private var hitches = 0
    private var worstGap: CFTimeInterval = 0
    private var loopTime: CFTimeInterval = 0
    private var lastMain: CFTimeInterval = 0
    private var windowStart = CACurrentMediaTime()
    private let maxFPS = MainActor.assumeIsolated { UIScreen.main.maximumFramesPerSecond }
    private var sections: [String: CFTimeInterval] = [:]
    private var mark: CFTimeInterval = 0

    /// Split timing inside the frame loop: `lap(nil)` starts, `lap("name")` books the time since the last lap.
    func lap(_ name: String?) {
        let now = CACurrentMediaTime()
        if let name { lock.lock(); sections[name, default: 0] += now - mark; lock.unlock() }
        mark = now
    }

    func renderer(_ renderer: any SCNSceneRenderer, didRenderScene scene: SCNScene, atTime time: TimeInterval) {
        lock.lock(); renders += 1; lock.unlock()
    }

    /// Call at the top of the main-thread frame loop; `work` is how long the previous loop body took.
    func mainFrame(at t: CFTimeInterval, work: CFTimeInterval) {
        lock.lock(); defer { lock.unlock() }
        if lastMain > 0 {
            let gap = t - lastMain
            worstGap = max(worstGap, gap)
            if gap > 1.0 / 40 { hitches += 1 }
        }
        lastMain = t
        mainFrames += 1
        loopTime += work
        let span = t - windowStart
        guard span >= 3 else { return }
        let line = String(format: "[perf] main %.0f fps, hitches %d, worst %.0f ms | render %.0f fps | loop %.2f ms/frame | thermal %d | lowPower %d | screen max %d",
                          Double(mainFrames) / span, hitches, worstGap * 1000, Double(renders) / span,
                          mainFrames > 0 ? loopTime / Double(mainFrames) * 1000 : 0,
                          ProcessInfo.processInfo.thermalState.rawValue, ProcessInfo.processInfo.isLowPowerModeEnabled ? 1 : 0,
                          maxFPS)
        fputs(line + "\n", stderr)
        if !sections.isEmpty, mainFrames > 0 {
            let parts = sections.sorted { $0.value > $1.value }.map { String(format: "%@ %.2f", $0.key, $0.value / Double(mainFrames) * 1000) }
            fputs("[perf]   ms/frame: " + parts.joined(separator: " | ") + "\n", stderr)
            sections = [:]
        }
        renders = 0; mainFrames = 0; hitches = 0; worstGap = 0; loopTime = 0; windowStart = t
    }
}
