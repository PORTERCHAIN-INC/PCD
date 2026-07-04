"use client";

import { forwardRef } from "react";
import { TextInput, View, type TextInputProps } from "react-native";
import { useTheme } from "@porterchain/mobile-theme";
import { Input, type InputProps } from "./input";

export type SearchInputProps = Omit<InputProps, "label"> & {
  onClear?: () => void;
};

export const SearchInput = forwardRef<TextInput, SearchInputProps>(function SearchInput(
  { placeholder = "Search…", style, ...props },
  ref
) {
  const { theme } = useTheme();

  return (
    <View style={{ position: "relative" }}>
      <View
        pointerEvents="none"
        style={{
          position: "absolute",
          left: theme.spacing.lg,
          top: 0,
          bottom: 0,
          justifyContent: "center",
          zIndex: 1,
        }}
      >
        <View
          style={{
            width: 16,
            height: 16,
            borderRadius: 8,
            borderWidth: 2,
            borderColor: theme.colors.textMuted,
          }}
        />
      </View>
      <Input
        ref={ref}
        placeholder={placeholder}
        returnKeyType="search"
        clearButtonMode="while-editing"
        style={[{ paddingLeft: theme.spacing["4xl"] }, style]}
        containerStyle={{ marginBottom: 0 }}
        {...(props as TextInputProps)}
      />
    </View>
  );
});
