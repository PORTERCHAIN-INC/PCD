/**
 * Documents the merchant/customer attached for this stop (e.g. a warehouse pickup
 * authorization). Images are kept on the phone so they open with no signal inside a
 * warehouse; PDFs open full-screen in the phone's own viewer via a 5-minute link.
 */
import { File, Paths } from "expo-file-system";
import * as ImagePicker from "expo-image-picker";
import { useKeepAwake } from "expo-keep-awake";
import * as WebBrowser from "expo-web-browser";
import { useCallback, useEffect, useState } from "react";
import { Image, Modal, Pressable, StyleSheet, Text, View } from "react-native";
import {
  downloadStopDocument,
  fetchStopDocuments,
  markStopDocumentShown,
  stopDocumentLink,
  type StopDocument,
} from "../../api";
import { Body, Button, Card, Label, Muted } from "../kit";
import { toast } from "../toast";

const isImage = (d: StopDocument) => d.content_type.startsWith("image/");
const localFile = (d: StopDocument) => new File(Paths.cache, `stopdoc-${d.id}`);

async function cache(d: StopDocument): Promise<string | null> {
  if (!isImage(d)) return null;
  const f = localFile(d);
  if (f.exists) return f.uri;
  const bytes = await downloadStopDocument(d.id);
  f.create({ overwrite: true });
  f.write(new Uint8Array(bytes));
  return f.uri;
}

function ShowToStaff({ doc, uri, onClose, onShown }: { doc: StopDocument; uri: string; onClose: () => void; onShown: () => void }) {
  useKeepAwake();
  const [busy, setBusy] = useState(false);
  async function shown(withPhoto: boolean) {
    setBusy(true);
    try {
      let proof: string | null = null;
      if (withPhoto) {
        const perm = await ImagePicker.requestCameraPermissionsAsync();
        if (perm.status !== "granted") throw new Error("camera");
        const r = await ImagePicker.launchCameraAsync({ mediaTypes: ["images"], quality: 0.6, exif: false });
        if (r.canceled || !r.assets?.[0]) return;
        proof = r.assets[0].uri;
      }
      await markStopDocumentShown(doc.id, proof);
      toast.show("success", "Marked as shown to staff");
      onShown();
    } catch {
      toast.show("danger", "Couldn't save. Try again when you have signal.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal visible animationType="slide" onRequestClose={onClose} testID="show-to-staff">
      <View style={st.full}>
        <View style={st.bar}>
          <Text style={st.barTitle}>{doc.kind_label}</Text>
          <Pressable accessibilityRole="button" accessibilityLabel="Close" onPress={onClose} hitSlop={16}>
            <Text style={st.close}>✕</Text>
          </Pressable>
        </View>
        <Image source={{ uri }} style={st.img} resizeMode="contain" />
        <View style={st.actions}>
          <Button label="Photo of signed copy" onPress={() => void shown(true)} busy={busy} />
          <Button label="Shown to staff" tone="primary" onPress={() => void shown(false)} busy={busy} />
        </View>
      </View>
    </Modal>
  );
}

export function StopDocumentsCard({ orderId }: { orderId: string }) {
  const [docs, setDocs] = useState<StopDocument[]>([]);
  const [showing, setShowing] = useState<{ doc: StopDocument; uri: string } | null>(null);

  const load = useCallback(async () => {
    if (!orderId) return;
    try {
      const r = await fetchStopDocuments(orderId);
      setDocs(r.items);
      r.items.forEach((d) => void cache(d).catch(() => undefined)); // pre-fetch for the warehouse
    } catch {
      /* offline: keep last list */
    }
  }, [orderId]);
  useEffect(() => {
    void load();
  }, [load]);

  async function open(d: StopDocument) {
    try {
      if (isImage(d)) {
        const uri = await cache(d);
        if (uri) setShowing({ doc: d, uri });
        return;
      }
      await WebBrowser.openBrowserAsync(await stopDocumentLink(d.id), {
        presentationStyle: WebBrowser.WebBrowserPresentationStyle.FULL_SCREEN,
      });
      // Back from the viewer: ask to confirm.
      await markShownPrompt(d);
    } catch {
      toast.show("danger", "Couldn't open the document. Check your signal.");
    }
  }

  async function markShownPrompt(d: StopDocument) {
    if (!d.required_at_stop || d.shown_at) return;
    setShowing(null);
    setConfirming(d);
  }
  const [confirming, setConfirming] = useState<StopDocument | null>(null);

  if (docs.length === 0) return null;
  return (
    <Card testID="stop-documents">
      <Label>Documents for this stop</Label>
      {docs.map((d) => (
        <View key={d.id} style={st.row}>
          <Body>{d.kind_label}</Body>
          <Muted>
            {d.filename}
            {d.note ? ` · ${d.note}` : ""}
          </Muted>
          {d.required_at_stop && d.stop === "pickup" ? (
            <Muted>{d.shown_at ? "✓ Shown to warehouse staff" : "Required: show to warehouse staff before Picked up"}</Muted>
          ) : null}
          <Button label="Show to staff" tone="primary" onPress={() => void open(d)} testID={`show-doc-${d.id}`} />
          {confirming?.id === d.id ? (
            <View style={st.actions}>
              <Button
                label="Shown to staff"
                tone="primary"
                onPress={() =>
                  void markStopDocumentShown(d.id)
                    .then(() => {
                      setConfirming(null);
                      void load();
                    })
                    .catch(() => toast.show("danger", "Couldn't save. Try again."))
                }
              />
            </View>
          ) : null}
        </View>
      ))}
      {showing ? (
        <ShowToStaff
          doc={showing.doc}
          uri={showing.uri}
          onClose={() => setShowing(null)}
          onShown={() => {
            setShowing(null);
            void load();
          }}
        />
      ) : null}
    </Card>
  );
}

const st = StyleSheet.create({
  row: { marginTop: 12, gap: 6 },
  full: { flex: 1, backgroundColor: "#ffffff" },
  bar: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", padding: 16, paddingTop: 56 },
  barTitle: { fontSize: 22, fontWeight: "700", color: "#000" },
  close: { fontSize: 28, color: "#000" },
  img: { flex: 1, width: "100%" },
  actions: { padding: 16, gap: 10 },
});
