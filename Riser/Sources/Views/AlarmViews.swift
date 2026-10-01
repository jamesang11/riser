import AlarmKit
import SwiftUI

struct AlarmListView: View {
    @AppStorage("riser.nagInterval") private var nagInterval: Double = 10
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss
    @State private var editing: AlarmItem?
    @State private var authState = AlarmService.authorizationState

    var body: some View {
        NavigationStack {
            List {
                if authState != .authorized {
                    Section {
                        PermissionCallout(
                            symbol: "alarm.waves.left.and.right.fill",
                            title: authState == .denied ? "Alarms are turned off" : "Allow Riser to ring",
                            message: authState == .denied
                                ? "Turn on Alarms for Riser in Settings so your wake-up missions can ring through Silent mode and Focus."
                                : "Riser uses real system alarms, so they ring even in Silent mode or a Focus.",
                            button: authState == .denied ? "Open Settings" : "Allow Alarms"
                        ) {
                            if authState == .denied {
                                if let url = URL(string: UIApplication.openSettingsURLString) { UIApplication.shared.open(url) }
                            } else {
                                Task {
                                    await AlarmService.requestAuthorization()
                                    authState = AlarmService.authorizationState
                                    model.syncAlarms()
                                }
                            }
                        }
                    }
                    .listRowBackground(Color.clear)
                    .listRowInsets(EdgeInsets())
                }

                Section {
                    ForEach(model.state.alarms) { alarm in
                        AlarmRow(alarm: alarm) { on in
                            var a = alarm
                            a.isEnabled = on
                            model.upsert(a)
                        }
                        .contentShape(.rect)
                        .onTapGesture { editing = alarm }
                        .swipeActions {
                            Button(role: .destructive) { model.delete(alarm) } label: {
                                Label("Delete", systemImage: "trash")
                            }
                        }
                    }
                } footer: {
                    if !model.isPlus {
                        Text("Free plan: up to \(AppModel.freeAlarmLimit) alarms. Riser+ unlocks unlimited alarms.")
                    }
                }

                Section {
                    Toggle(isOn: Binding(get: { model.state.escapeProof }, set: { model.setEscapeProof($0) })) {
                        Label {
                            VStack(alignment: .leading, spacing: 2) {
                                Text("Escape-proof")
                                Text("If you stop the alarm without finishing your mission, it keeps ringing again for up to an hour.")
                                    .font(.footnote)
                                    .foregroundStyle(.secondary)
                            }
                        } icon: {
                            Image(systemName: "lock.fill").foregroundStyle(Theme.sun)
                        }
                    }
                    .tint(Theme.sun)
                    Picker(selection: $nagInterval) {
                        ForEach(MissionInbox.nagIntervals, id: \.self) { Text(MissionInbox.intervalText($0)).tag($0) }
                    } label: {
                        Label("Rings again after", systemImage: "arrow.clockwise")
                    }
                    .disabled(!model.state.escapeProof)
                    .opacity(model.state.escapeProof ? 1 : 0.5)
                }

                Section("Try a mission now") {
                    ForEach(MissionKind.available) { m in
                        Button {
                            dismiss()
                            DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) {
                                model.startPractice(m, target: min(m.defaultTarget, 5))
                            }
                        } label: {
                            Label(m.title, systemImage: m.symbol)
                        }
                    }
                }
            }
            .scrollContentBackground(.hidden)
            .navigationTitle("Alarms")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Done", systemImage: "xmark") { dismiss() }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Add Alarm", systemImage: "plus") {
                        if model.canAddAlarm {
                            editing = AlarmItem(weekdays: [])
                        } else {
                            model.requirePlus("Unlimited alarms are part of Riser+")
                        }
                    }
                }
            }
            .sheet(item: $editing) { alarm in
                AlarmEditor(alarm: alarm, isNew: !model.state.alarms.contains { $0.id == alarm.id })
                    .environment(model)
            }
        }
        .presentationDetents([.large])
        .presentationBackground(.thinMaterial)
    }
}

struct PermissionCallout: View {
    var symbol: String
    var title: String
    var message: String
    var button: String
    var action: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Image(systemName: symbol)
                .font(.system(size: 28, weight: .semibold))
                .foregroundStyle(Theme.sunGradient)
                .symbolEffect(.wiggle, options: .repeat(.periodic(delay: 2)))
            Text(title).font(.rounded(19, .bold))
            Text(message).font(.subheadline).foregroundStyle(.secondary)
            Button(button, action: action)
                .buttonStyle(.glassProminent)
                .tint(Theme.sun)
                .padding(.top, 4)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(18)
        .glassCard(cornerRadius: 24, tint: Theme.sun.opacity(0.15))
    }
}

struct AlarmRow: View {
    var alarm: AlarmItem
    var onToggle: (Bool) -> Void

    var body: some View {
        HStack(spacing: 14) {
            VStack(alignment: .leading, spacing: 4) {
                Text(alarm.timeText)
                    .font(.system(size: 44, weight: .semibold, design: .rounded))
                    .monospacedDigit()
                    .foregroundStyle(alarm.isEnabled ? .primary : .tertiary)
                HStack(spacing: 6) {
                    Image(systemName: alarm.mission.symbol)
                    Text("\(alarm.mission.amountText(alarm.target)) · \(alarm.repeatText)")
                    if !alarm.label.isEmpty { Text("· \(alarm.label)") }
                }
                .font(.rounded(14, .medium))
                .foregroundStyle(.secondary)
            }
            Spacer()
            Toggle("Enabled", isOn: Binding(get: { alarm.isEnabled }, set: onToggle))
                .labelsHidden()
                .tint(Theme.sun)
        }
        .padding(.vertical, 6)
        .accessibilityElement(children: .combine)
    }
}

struct AlarmEditor: View {
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss
    @State var alarm: AlarmItem
    var isNew: Bool
    @State private var time = Date.now
    @State private var testScheduled: Date?
    @State private var errorText: String?

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    DatePicker("Time", selection: $time, displayedComponents: .hourAndMinute)
                        .datePickerStyle(.wheel)
                        .labelsHidden()
                        .frame(maxWidth: .infinity)
                }
                .listRowBackground(Color.clear)

                Section("Repeat") {
                    WeekdayPicker(selection: $alarm.weekdays)
                        .listRowInsets(EdgeInsets(top: 12, leading: 12, bottom: 12, trailing: 12))
                }

                Section("Wake-up mission") {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 10) {
                            ForEach(MissionKind.available) { m in
                                MissionChoice(mission: m, selected: alarm.mission == m) {
                                    withAnimation(.snappy) {
                                        alarm.mission = m
                                        alarm.target = m.defaultTarget
                                    }
                                    Haptics.select()
                                }
                            }
                        }
                        .padding(.vertical, 4)
                    }
                    .listRowInsets(EdgeInsets(top: 8, leading: 12, bottom: 8, trailing: 12))
                    Text(alarm.mission.blurb)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                    if alarm.mission.targetRange.count > 1 {
                        Stepper(value: $alarm.target, in: alarm.mission.targetRange, step: alarm.mission.targetStep) {
                            HStack {
                                Text("Goal")
                                Spacer()
                                Text(alarm.mission.amountText(alarm.target))
                                    .font(.rounded(17, .bold))
                                    .monospacedDigit()
                                    .contentTransition(.numericText(value: Double(alarm.target)))
                            }
                        }
                    } else {
                        HStack {
                            Text("Goal")
                            Spacer()
                            Text(alarm.mission.amountText(alarm.target))
                                .font(.rounded(17, .bold))
                        }
                    }
                }

                Section("Sound") {
                    ForEach(AlarmSound.allCases) { s in
                        Button {
                            if s.isPremium && !model.isPlus {
                                model.requirePlus("The \(s.title) alarm sound is part of Riser+")
                            } else {
                                alarm.sound = s
                                Haptics.select()
                            }
                        } label: {
                            HStack {
                                VStack(alignment: .leading) {
                                    Text(s.title).foregroundStyle(.primary)
                                    Text(s.subtitle).font(.footnote).foregroundStyle(.secondary)
                                }
                                Spacer()
                                if s.isPremium && !model.isPlus {
                                    Image(systemName: "lock.fill").foregroundStyle(.secondary)
                                } else if alarm.sound == s {
                                    Image(systemName: "checkmark").foregroundStyle(Theme.sun).fontWeight(.bold)
                                }
                            }
                        }
                    }
                }

                Section {
                    TextField("Label (optional)", text: $alarm.label)
                }

                Section {
                    Button {
                        Task { await scheduleTest() }
                    } label: {
                        Label(testScheduled == nil ? "Test the full alarm in 1 minute" : "Test alarm set, lock your phone!",
                              systemImage: testScheduled == nil ? "bell.badge.waveform.fill" : "checkmark.circle.fill")
                    }
                    .disabled(testScheduled != nil)
                    if let errorText {
                        Text(errorText).font(.footnote).foregroundStyle(.red)
                    }
                } footer: {
                    Text("Rings like the real thing so you can see exactly how your mornings will go.")
                }

                if !isNew {
                    Section {
                        Button("Delete Alarm", role: .destructive) {
                            model.delete(alarm)
                            dismiss()
                        }
                    }
                }
            }
            .navigationTitle(isNew ? "New Alarm" : "Edit Alarm")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel", systemImage: "xmark") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save", systemImage: "checkmark") { save() }
                        .buttonStyle(.glassProminent)
                        .tint(Theme.sun)
                }
            }
            .onAppear {
                var c = DateComponents()
                c.hour = alarm.hour
                c.minute = alarm.minute
                time = Calendar.current.date(from: c) ?? .now
            }
        }
    }

    private func applyTime() {
        let c = Calendar.current.dateComponents([.hour, .minute], from: time)
        alarm.hour = c.hour ?? 7
        alarm.minute = c.minute ?? 0
    }

    private func save() {
        applyTime()
        alarm.isEnabled = true
        Task {
            await AlarmService.requestAuthorization()
            model.upsert(alarm)
        }
        Haptics.success()
        dismiss()
    }

    private func scheduleTest() async {
        applyTime()
        guard await AlarmService.requestAuthorization() else {
            errorText = "Allow alarms for Riser in Settings first."
            return
        }
        do {
            testScheduled = try await AlarmService.scheduleTest(for: alarm)
            Haptics.success()
        } catch {
            errorText = error.localizedDescription
        }
    }
}

struct MissionChoice: View {
    var mission: MissionKind
    var selected: Bool
    var action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(spacing: 8) {
                Image(systemName: mission.symbol)
                    .font(.system(size: 26, weight: .semibold))
                    .symbolEffect(.bounce, value: selected)
                    .frame(height: 30)
                Text(mission.title)
                    .font(.rounded(13, .bold))
                    .multilineTextAlignment(.center)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)
                    .frame(height: 34, alignment: .top)
            }
            .padding(.horizontal, 6)
            .frame(width: 96, height: 96)
            .foregroundStyle(selected ? Theme.ink : .primary)
            .background {
                RoundedRectangle(cornerRadius: 20, style: .continuous)
                    .fill(selected ? AnyShapeStyle(Theme.sunGradient) : AnyShapeStyle(.quaternary))
            }
        }
        .buttonStyle(.plain)
        .accessibilityAddTraits(selected ? .isSelected : [])
    }
}

struct WeekdayPicker: View {
    @Binding var selection: Set<Int>

    var body: some View {
        let symbols = Calendar.current.veryShortWeekdaySymbols
        let order = (0..<7).map { (Calendar.current.firstWeekday - 1 + $0) % 7 + 1 }
        HStack(spacing: 6) {
            ForEach(order, id: \.self) { day in
                let on = selection.contains(day)
                Button {
                    if on { selection.remove(day) } else { selection.insert(day) }
                    Haptics.select()
                } label: {
                    Text(symbols[day - 1])
                        .font(.rounded(15, .bold))
                        .frame(maxWidth: .infinity)
                        .frame(height: 40)
                        .foregroundStyle(on ? Theme.ink : .primary)
                        .background(Circle().fill(on ? AnyShapeStyle(Theme.sunGradient) : AnyShapeStyle(.quaternary)))
                }
                .buttonStyle(.plain)
                .accessibilityLabel(Calendar.current.weekdaySymbols[day - 1])
                .accessibilityAddTraits(on ? .isSelected : [])
            }
        }
    }
}
