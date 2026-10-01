import simd

/// A walkability grid over the island top so Sprig walks *around* buildings, trees and props.
struct NavGrid {
    let cell: Float = 0.25
    let radius: Float = 4.3
    /// Sprig is roughly a metre wide at his in-game scale; obstacles are padded by this.
    let bodyRadius: Float = 0.42
    private let n: Int
    private var blocked: [Bool]

    init() {
        n = Int((radius * 2) / cell) + 1
        blocked = Array(repeating: false, count: n * n)
        rebuild(obstacles: [])
    }

    private func index(_ i: Int, _ j: Int) -> Int { j * n + i }

    private func cellOf(_ p: SIMD2<Float>) -> (Int, Int) {
        (Int(((p.x + radius) / cell).rounded()), Int(((p.y + radius) / cell).rounded()))
    }

    private func centre(_ i: Int, _ j: Int) -> SIMD2<Float> {
        SIMD2(Float(i) * cell - radius, Float(j) * cell - radius)
    }

    private func inBounds(_ i: Int, _ j: Int) -> Bool { i >= 0 && j >= 0 && i < n && j < n }

    mutating func rebuild(obstacles: [(SIMD2<Float>, Float)]) {
        for j in 0..<n {
            for i in 0..<n {
                let c = centre(i, j)
                var b = simd_length(c) > radius - bodyRadius * 0.5
                if !b {
                    for (o, r) in obstacles where simd_distance(c, o) < r + bodyRadius {
                        b = true
                        break
                    }
                }
                blocked[index(i, j)] = b
            }
        }
    }

    func isFree(_ p: SIMD2<Float>) -> Bool {
        let (i, j) = cellOf(p)
        return inBounds(i, j) && !blocked[index(i, j)]
    }

    /// Nearest walkable cell to `p` (for starts/goals that sit inside an obstacle, like a doorstep).
    func nearestFree(_ p: SIMD2<Float>) -> SIMD2<Float>? {
        let (ci, cj) = cellOf(p)
        for r in 0..<n {
            var best: (SIMD2<Float>, Float)?
            for dj in -r...r {
                for di in -r...r where abs(di) == r || abs(dj) == r {
                    let i = ci + di, j = cj + dj
                    guard inBounds(i, j), !blocked[index(i, j)] else { continue }
                    let c = centre(i, j)
                    let d = simd_distance(c, p)
                    if best == nil || d < best!.1 { best = (c, d) }
                }
            }
            if let best { return best.0 }
        }
        return nil
    }

    /// Straight line clear of obstacles?
    func lineOfSight(_ a: SIMD2<Float>, _ b: SIMD2<Float>) -> Bool {
        let steps = max(1, Int(simd_distance(a, b) / (cell * 0.5)))
        for s in 0...steps {
            if !isFree(simd_mix(a, b, SIMD2(repeating: Float(s) / Float(steps)))) { return false }
        }
        return true
    }

    /// A* over 8-connected cells, then smoothed into as few straight segments as possible.
    func path(from start: SIMD2<Float>, to goal: SIMD2<Float>) -> [SIMD2<Float>]? {
        guard let s = isFree(start) ? start : nearestFree(start),
              let g = isFree(goal) ? goal : nearestFree(goal) else { return nil }
        if lineOfSight(s, g) { return [g] }
        let (si, sj) = cellOf(s), (gi, gj) = cellOf(g)
        let startIdx = index(si, sj), goalIdx = index(gi, gj)
        var open: Set<Int> = [startIdx]
        var came: [Int: Int] = [:]
        var gScore: [Int: Float] = [startIdx: 0]
        var fScore: [Int: Float] = [startIdx: simd_distance(s, g)]
        var iterations = 0
        while let current = open.min(by: { (fScore[$0] ?? .infinity) < (fScore[$1] ?? .infinity) }) {
            iterations += 1
            if iterations > 4000 { return nil }
            if current == goalIdx {
                var cells = [current]
                var c = current
                while let p = came[c] { cells.append(p); c = p }
                let raw = cells.reversed().map { centre($0 % n, $0 / n) } + [g]
                return smooth(from: s, raw)
            }
            open.remove(current)
            let ci = current % n, cj = current / n
            for dj in -1...1 {
                for di in -1...1 where di != 0 || dj != 0 {
                    let i = ci + di, j = cj + dj
                    guard inBounds(i, j), !blocked[index(i, j)] else { continue }
                    // No cutting diagonally between two blocked cells.
                    if di != 0 && dj != 0 && (blocked[index(ci + di, cj)] || blocked[index(ci, cj + dj)]) { continue }
                    let nb = index(i, j)
                    let step: Float = (di != 0 && dj != 0) ? 1.414 : 1
                    let tentative = (gScore[current] ?? .infinity) + step * cell
                    if tentative < (gScore[nb] ?? .infinity) {
                        came[nb] = current
                        gScore[nb] = tentative
                        fScore[nb] = tentative + simd_distance(centre(i, j), g)
                        open.insert(nb)
                    }
                }
            }
        }
        return nil
    }

    private func smooth(from start: SIMD2<Float>, _ pts: [SIMD2<Float>]) -> [SIMD2<Float>] {
        var out: [SIMD2<Float>] = []
        var anchor = start
        var i = 0
        while i < pts.count {
            var j = pts.count - 1
            while j > i && !lineOfSight(anchor, pts[j]) { j -= 1 }
            out.append(pts[j])
            anchor = pts[j]
            i = j + 1
        }
        return out
    }
}
