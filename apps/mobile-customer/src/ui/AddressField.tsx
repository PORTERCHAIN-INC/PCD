import { useEffect, useState } from "react";
import { Pressable, Text, TextInput, StyleSheet } from "react-native";
import { colors, radius, spacing, touchTargetMin, typography } from "@porterchain/mobile-theme";
import type { Address } from "../api";
import { googleMapsApiKey } from "../config";

type Suggestion = { placeId: string; description: string };

type Props = {
  label: string;
  value: Address;
  onChange: (next: Address) => void;
  accessoryId?: string;
  /** True when a typed address may be quoted because Google returned nothing. */
  onManualOk?: (ok: boolean) => void;
};

export function AddressField({ label, value, onChange, accessoryId, onManualOk }: Props) {
  const [query, setQuery] = useState(value.formatted);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [hint, setHint] = useState<string | null>(null);

  useEffect(() => {
    setQuery(value.formatted);
  }, [value.formatted]);

  useEffect(() => {
    if (!googleMapsApiKey || query.trim().length < 3) {
      setSuggestions([]);
      return;
    }
    if (query === value.formatted && value.place_id) {
      setSuggestions([]);
      return;
    }
    onManualOk?.(false);
    let cancelled = false;
    const timer = setTimeout(() => {
      void fetch("https://places.googleapis.com/v1/places:autocomplete", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Goog-Api-Key": googleMapsApiKey,
        },
        body: JSON.stringify({
          input: query,
          includedRegionCodes: ["ca"],
        }),
      })
        .then(async (res) => {
          if (!res.ok) throw new Error("places_unavailable");
          return res.json() as Promise<{
            suggestions?: Array<{
              placePrediction?: { placeId?: string; text?: { text?: string } };
            }>;
          }>;
        })
        .then((body) => {
          if (cancelled) return;
          const rows = (body.suggestions ?? [])
            .map((row) => ({
              placeId: row.placePrediction?.placeId ?? "",
              description: row.placePrediction?.text?.text ?? "",
            }))
            .filter((row) => row.placeId && row.description)
            .slice(0, 5);
          setSuggestions(rows);
          const none = rows.length === 0;
          setHint(none ? "No matching Canadian address. You can keep what you typed." : null);
          onManualOk?.(none);
        })
        .catch(() => {
          if (cancelled) return;
          setSuggestions([]);
          setHint(
            "Google address search is unavailable. Type the full street, city, and postal code."
          );
          onManualOk?.(true);
        });
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query, value.formatted, onManualOk]);

  useEffect(() => {
    if (!googleMapsApiKey) {
      onManualOk?.(true);
      return;
    }
    if (value.place_id || query.trim().length < 3) onManualOk?.(false);
  }, [query, value.place_id, onManualOk]);

  async function choose(item: Suggestion) {
    setSuggestions([]);
    setHint(null);
    setQuery(item.description);
    try {
      const res = await fetch(
        `https://places.googleapis.com/v1/places/${encodeURIComponent(item.placeId)}`,
        {
          headers: {
            "X-Goog-Api-Key": googleMapsApiKey,
            "X-Goog-FieldMask": "formattedAddress,location,addressComponents",
          },
        }
      );
      if (!res.ok) throw new Error("place_details_unavailable");
      const body = (await res.json()) as {
        formattedAddress?: string;
        location?: { latitude?: number; longitude?: number };
        addressComponents?: Array<{ longText?: string; types?: string[] }>;
      };
      const postal = body.addressComponents?.find((part) =>
        part.types?.includes("postal_code")
      )?.longText;
      const formatted = body.formattedAddress || item.description;
      const lat = body.location?.latitude;
      const lng = body.location?.longitude;
      if (lat == null || lng == null) throw new Error("place_without_point");
      setQuery(formatted);
      onChange({
        formatted,
        place_id: item.placeId,
        lat,
        lng,
        postal,
      });
    } catch {
      setHint("Could not load that place. Choose another suggestion.");
      onChange({ formatted: item.description });
    }
  }

  return (
    <>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        accessibilityLabel={label}
        autoCorrect={false}
        placeholder={googleMapsApiKey ? "Search a Canadian address" : "Street, city, postal code"}
        placeholderTextColor={colors.muted}
        style={styles.input}
        value={query}
        inputAccessoryViewID={accessoryId}
        onChangeText={(text) => {
          setQuery(text);
          setHint(null);
          onChange({ formatted: text });
        }}
      />
      {value.place_id ? (
        <Text style={styles.hint}>
          {value.postal ? `Google · ${value.postal}` : "Selected from Google"}
        </Text>
      ) : null}
      {hint ? <Text style={styles.hint}>{hint}</Text> : null}
      {suggestions.map((item) => (
        <Pressable key={item.placeId} onPress={() => void choose(item)} style={styles.suggestion}>
          <Text style={styles.suggestionText}>{item.description}</Text>
        </Pressable>
      ))}
    </>
  );
}

const styles = StyleSheet.create({
  label: { ...typography.caption, color: colors.muted },
  hint: { ...typography.caption, color: colors.muted },
  input: {
    minHeight: touchTargetMin,
    borderWidth: 1,
    borderColor: `${colors.primary}26`,
    borderRadius: radius.lg,
    paddingHorizontal: spacing.md,
    backgroundColor: colors.white,
    color: colors.primary,
    fontSize: typography.body.fontSize,
  },
  suggestion: {
    minHeight: touchTargetMin,
    justifyContent: "center",
    paddingHorizontal: spacing.md,
    backgroundColor: colors.white,
    borderRadius: radius.md,
  },
  suggestionText: { ...typography.caption, color: colors.primary },
});
