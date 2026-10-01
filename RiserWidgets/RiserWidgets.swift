import ActivityKit
import AlarmKit
import SwiftUI
import WidgetKit

@main
struct RiserWidgetsBundle: WidgetBundle {
    var body: some Widget {
        AlarmLiveActivity()
    }
}

private let sun = Color(red: 0.98, green: 0.65, blue: 0.26)

/// Lock Screen + Dynamic Island presentation for Riser alarms.
struct AlarmLiveActivity: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: AlarmAttributes<RiserAlarmMetadata>.self) { context in
            LockScreenAlarmView(attributes: context.attributes, state: context.state)
                .activityBackgroundTint(Color(red: 0.09, green: 0.12, blue: 0.27))
                .activitySystemActionForegroundColor(sun)
        } dynamicIsland: { context in
            DynamicIsland {
                DynamicIslandExpandedRegion(.leading) {
                    Image(systemName: "sun.max.fill")
                        .font(.title2)
                        .foregroundStyle(sun)
                }
                DynamicIslandExpandedRegion(.trailing) {
                    if let m = context.attributes.metadata {
                        Label("\(m.target)", systemImage: m.mission.symbol)
                            .font(.headline)
                    }
                }
                DynamicIslandExpandedRegion(.bottom) {
                    Text(context.attributes.presentation.alert.title)
                        .font(.system(.headline, design: .rounded))
                }
            } compactLeading: {
                Image(systemName: "sun.max.fill").foregroundStyle(sun)
            } compactTrailing: {
                if let m = context.attributes.metadata {
                    Image(systemName: m.mission.symbol).foregroundStyle(sun)
                }
            } minimal: {
                Image(systemName: "sun.max.fill").foregroundStyle(sun)
            }
            .keylineTint(sun)
        }
    }
}

struct LockScreenAlarmView: View {
    var attributes: AlarmAttributes<RiserAlarmMetadata>
    var state: AlarmPresentationState

    var body: some View {
        HStack(spacing: 14) {
            ZStack {
                Circle().fill(LinearGradient(colors: [Color(red: 1, green: 0.82, blue: 0.4), sun],
                                             startPoint: .top, endPoint: .bottom))
                Image(systemName: attributes.metadata?.mission.symbol ?? "sun.max.fill")
                    .font(.system(size: 20, weight: .bold))
                    .foregroundStyle(.white)
            }
            .frame(width: 46, height: 46)
            VStack(alignment: .leading, spacing: 2) {
                Text(attributes.presentation.alert.title)
                    .font(.system(.headline, design: .rounded))
                if let m = attributes.metadata, !m.isNag {
                    Text("\(m.mission.goalText(m.target).prefix(1).uppercased() + m.mission.goalText(m.target).dropFirst()) to wake your sprout")
                        .font(.system(.subheadline, design: .rounded))
                        .foregroundStyle(.secondary)
                } else {
                    Text("Your sprout is still waiting 🌱")
                        .font(.system(.subheadline, design: .rounded))
                        .foregroundStyle(.secondary)
                }
            }
            Spacer()
        }
        .padding(16)
        .foregroundStyle(.white)
    }
}
