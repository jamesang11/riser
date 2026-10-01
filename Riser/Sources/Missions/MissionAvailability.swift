extension MissionKind {
    /// Missions offered to the player. The Morning Walk was retired; its case stays so older saves still decode.
    static var available: [MissionKind] {
        allCases.filter { $0 != .steps }
    }
}
