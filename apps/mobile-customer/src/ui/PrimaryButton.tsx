import type { PressableProps } from "react-native";
import { Button } from "./kit";

type Props = PressableProps & {
  label: string;
  testID?: string;
  tone?: "solid" | "ghost";
  loading?: boolean;
};

/** Back-compat wrapper over the kit `Button` (keeps existing testIDs working). */
export function PrimaryButton({ tone = "solid", ...rest }: Props) {
  return <Button variant={tone} {...rest} />;
}
