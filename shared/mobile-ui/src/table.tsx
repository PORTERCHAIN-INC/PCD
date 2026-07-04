"use client";

import type { ReactElement, ReactNode } from "react";
import { ScrollView, View } from "react-native";
import { useTheme } from "@porterchain/mobile-theme";
import { Caption, Label, Text } from "./typography";

export type TableColumn<T> = {
  key: string;
  header: string;
  width?: number | `${number}%`;
  align?: "left" | "center" | "right";
  render: (row: T) => ReactElement | string | number | null;
};

export type DataTableProps<T> = {
  columns: TableColumn<T>[];
  data: T[];
  keyExtractor: (row: T, index: number) => string;
  emptyMessage?: string;
};

export function DataTable<T>({ columns, data, keyExtractor, emptyMessage = "No rows" }: DataTableProps<T>) {
  const { theme } = useTheme();

  if (data.length === 0) {
    return (
      <View style={{ padding: theme.spacing.xl, alignItems: "center" }}>
        <Caption>{emptyMessage}</Caption>
      </View>
    );
  }

  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false}>
      <View style={{ minWidth: "100%" }}>
        <View
          style={{
            flexDirection: "row",
            backgroundColor: theme.colors.surfaceMuted,
            borderBottomWidth: 1,
            borderColor: theme.colors.border,
          }}
        >
          {columns.map((col) => (
            <View
              key={col.key}
              style={{
                flex: col.width ? undefined : 1,
                width: typeof col.width === "number" ? col.width : col.width,
                paddingVertical: theme.spacing.sm,
                paddingHorizontal: theme.spacing.md,
              }}
            >
              <Label style={{ textAlign: col.align ?? "left" }}>{col.header}</Label>
            </View>
          ))}
        </View>
        {data.map((row, index) => (
          <View
            key={keyExtractor(row, index)}
            style={{
              flexDirection: "row",
              borderBottomWidth: index < data.length - 1 ? 1 : 0,
              borderColor: theme.colors.border,
              backgroundColor: theme.colors.surface,
            }}
          >
            {columns.map((col) => {
              const cell = col.render(row);
              return (
                <View
                  key={col.key}
                  style={{
                    flex: col.width ? undefined : 1,
                    width: typeof col.width === "number" ? col.width : col.width,
                    paddingVertical: theme.spacing.md,
                    paddingHorizontal: theme.spacing.md,
                    justifyContent: "center",
                  }}
                >
                  {typeof cell === "string" || typeof cell === "number" ? (
                    <Text variant="body" style={{ textAlign: col.align ?? "left" }}>
                      {String(cell)}
                    </Text>
                  ) : (
                    cell
                  )}
                </View>
              );
            })}
          </View>
        ))}
      </View>
    </ScrollView>
  );
}
