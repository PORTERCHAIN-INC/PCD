import { useEffect, useState } from "react";
import { Pressable, Text, TextInput, StyleSheet } from "react-native";
import { radius, spacing, touchTargetMin, typography } from "@porterchain/mobile-theme";
import { useThemed, type Palette } from "../theme";
import type { Address } from "../api";
import { apiBaseUrl } from "../config";

type Suggestion = { placeId: string; description: string };

type Props = {
  label: string;
  value: Address;
  onChange: (next: Address) => void;
  accessoryId?: string;
  /** True when a typed address may be quoted because search returned nothing. */
  onManualOk?: (ok: boolean) => void;
};

export function AddressField({ label, value, onChange, accessoryId, onManualOk }: Props) {
  const { colors, styles } = useThemed(makeStyles);
  const [query, setQuery] = useState(value.formatted);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [hint, setHint] = useState<string | null>(null);

  useEffect(() => {
    setQuery(value.formatted);
  }, [value.formatted]);

  useEffect(() => {
    if (query.trim().length < 3) {
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
      // PorterChain address search (self-hosted, GTA ±150 km). No Google key in the app.
      void fetch(`${apiBaseUrl}/v1/geo/autocomplete?q=${encodeURIComponent(query)}&limit=5`, {
        headers: { Accept: "application/json" },
      })
        .then(async (res) => {
          if (!res.ok) throw new Error("geo_unavailable");
          return res.json() as Promise<{
            results?: Array<{ id?: string; formatted?: string }>;
          }>;
        })
        .then((body) => {
          if (cancelled) return;
          const rows = (body.results ?? [])
            .map((row) => ({ placeId: row.id ?? "", description: row.formatted ?? "" }))
            .filter((row) => row.placeId && row.description)
            .slice(0, 5);
          setSuggestions(rows);
          const none = rows.length === 0;
          setHint(none ? "No matching address nearby. You can keep what you typed." : null);
          onManualOk?.(none);
        })
        .catch(() => {
          if (cancelled) return;
          setSuggestions([]);
          setHint("Address search is unavailable. Type the full street, city, and postal code.");
          onManualOk?.(true);
        });
    }, 400);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query, value.formatted, value.place_id, onManualOk]);

  useEffect(() => {
    if (value.place_id || query.trim().length < 3) onManualOk?.(false);
  }, [query, value.place_id, onManualOk]);

  async function choose(item: Suggestion) {
    setSuggestions([]);
    setHint(null);
    setQuery(item.description);
    try {
      const res = await fetch(`${apiBaseUrl}/v1/geo/place?id=${encodeURIComponent(item.placeId)}`, {
        headers: { Accept: "application/json" },
      });
      if (!res.ok) throw new Error("place_unavailable");
      const body = (await res.json()) as {
        formatted?: string;
        lat?: number;
        lng?: number;
        postal?: string | null;
      };
      const formatted = body.formatted || item.description;
      if (body.lat == null || body.lng == null) throw new Error("place_without_point");
      setQuery(formatted);
      onChange({
        formatted,
        // Server caps place_id at 255 chars; the search token can be longer, so store a
        // short stable id. Price and distance always come from lat/lng on the API.
        place_id: `osm:${body.lat.toFixed(5)},${body.lng.toFixed(5)}`,
        lat: body.lat,
        lng: body.lng,
        postal: body.postal ?? undefined,
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
        placeholder="Search an address"
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

const makeStyles = (colors: Palette) =>
  StyleSheet.create({
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
