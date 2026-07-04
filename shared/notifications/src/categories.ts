import * as Notifications from "expo-notifications";

export async function setupNotificationCategories(mode: "driver" | "customer"): Promise<void> {
  const common = [
    {
      identifier: "porterchain_open",
      actions: [{ identifier: "open", buttonTitle: "Open", options: { opensAppToForeground: true } }],
    },
    {
      identifier: "porterchain_archive",
      actions: [
        { identifier: "open", buttonTitle: "Open", options: { opensAppToForeground: true } },
        {
          identifier: "archive",
          buttonTitle: "Archive",
          options: { opensAppToForeground: false },
        },
      ],
    },
  ];

  const driver = [
    {
      identifier: "driver_assignment",
      actions: [
        { identifier: "accept", buttonTitle: "Accept", options: { opensAppToForeground: true } },
        { identifier: "reject", buttonTitle: "Reject", options: { opensAppToForeground: false } },
      ],
    },
    {
      identifier: "driver_emergency",
      actions: [
        { identifier: "open", buttonTitle: "View SOS", options: { opensAppToForeground: true } },
      ],
    },
  ];

  const categories = mode === "driver" ? [...common, ...driver] : common;
  for (const category of categories) {
    await Notifications.setNotificationCategoryAsync(category.identifier, category.actions);
  }
}

export function categoryForItem(group?: string, priority?: string): string {
  if (priority === "critical") return "driver_emergency";
  if (group === "assignment") return "driver_assignment";
  return "porterchain_archive";
}
