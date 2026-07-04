"use client";

import { forwardRef, useCallback, useMemo, type ReactNode } from "react";
import { View } from "react-native";
import BottomSheet, {
  BottomSheetBackdrop,
  BottomSheetModal,
  BottomSheetModalProvider,
  BottomSheetView,
  type BottomSheetBackdropProps,
  type BottomSheetModal as BottomSheetModalType,
} from "@gorhom/bottom-sheet";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { shadowForScheme, useTheme } from "@porterchain/mobile-theme";
import { Title } from "./typography";

export function MobileUiProvider({ children }: { children: ReactNode }) {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <BottomSheetModalProvider>{children}</BottomSheetModalProvider>
    </GestureHandlerRootView>
  );
}

function useSheetStyles() {
  const { theme } = useTheme();
  return useMemo(
    () => ({
      backgroundStyle: {
        backgroundColor: theme.colors.surface,
        borderTopLeftRadius: theme.radii["2xl"],
        borderTopRightRadius: theme.radii["2xl"],
        ...shadowForScheme("sheet", theme.scheme),
      },
      handleIndicatorStyle: {
        width: theme.layout.bottomSheetHandleWidth,
        backgroundColor: theme.colors.borderStrong,
      },
    }),
    [theme]
  );
}

export function AppBottomSheet({
  children,
  snapPoints = ["25%", "50%"],
}: {
  children: ReactNode;
  snapPoints?: (string | number)[];
}) {
  const styles = useSheetStyles();
  const points = useMemo(() => snapPoints, [snapPoints]);

  return (
    <BottomSheet snapPoints={points} backgroundStyle={styles.backgroundStyle} handleIndicatorStyle={styles.handleIndicatorStyle}>
      {children}
    </BottomSheet>
  );
}

export type SheetModalProps = {
  title?: string;
  children: ReactNode;
  snapPoints?: (string | number)[];
  onDismiss?: () => void;
};

export const SheetModal = forwardRef<BottomSheetModalType, SheetModalProps>(function SheetModal(
  { title, children, snapPoints = ["40%", "85%"], onDismiss },
  ref
) {
  const { theme } = useTheme();
  const styles = useSheetStyles();
  const points = useMemo(() => snapPoints, [snapPoints]);

  const renderBackdrop = useCallback(
    (props: BottomSheetBackdropProps) => (
      <BottomSheetBackdrop {...props} disappearsOnIndex={-1} appearsOnIndex={0} opacity={0.45} />
    ),
    []
  );

  return (
    <BottomSheetModal
      ref={ref}
      snapPoints={points}
      enablePanDownToClose
      backdropComponent={renderBackdrop}
      backgroundStyle={styles.backgroundStyle}
      handleIndicatorStyle={styles.handleIndicatorStyle}
      onDismiss={onDismiss}
    >
      <BottomSheetView style={{ padding: theme.spacing.lg, paddingBottom: theme.spacing["3xl"] }}>
        {title ? (
          <View style={{ marginBottom: theme.spacing.lg }}>
            <Title>{title}</Title>
          </View>
        ) : null}
        {children}
      </BottomSheetView>
    </BottomSheetModal>
  );
});
