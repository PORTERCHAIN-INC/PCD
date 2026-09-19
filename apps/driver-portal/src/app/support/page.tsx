"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  BookOpen,
  FileWarning,
  LifeBuoy,
  MessageSquare,
  Phone,
  RefreshCw,
  Siren,
} from "lucide-react";
import DriverShell from "@/components/DriverShell";
import { useDriverSupport } from "@/hooks/useDriverSupport";
import { hasDriverSession } from "@/lib/api";
import { formatSupportDate, incidentLabel, priorityStyle, statusStyle } from "@/lib/support";
import { cn } from "@/lib/utils";

export default function SupportPage() {
  const router = useRouter();
  const {
    data,
    error,
    loading,
    refreshing,
    actionPending,
    refresh,
    createTicket,
    reportIncident,
    updateEmergencyContact,
    triggerSos,
    openClaim,
  } = useDriverSupport();

  useEffect(() => {
    hasDriverSession().then((ok) => {
      if (!ok) router.replace("/login");
    });
  }, [router]);

  if (loading && !data) {
    return (
      <DriverShell>
        <div className="animate-pulse space-y-4">
          <div className="h-10 w-48 rounded-xl bg-white" />
          <div className="h-32 rounded-2xl bg-white" />
        </div>
      </DriverShell>
    );
  }

  const snap = data!;

  return (
    <DriverShell>
      <header className="flex flex-col gap-3 border-b border-[var(--primary)]/8 pb-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Support</h1>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Tickets, claims, incidents, and help — synced with Porterchain Support
          </p>
        </div>
        <button
          type="button"
          onClick={refresh}
          disabled={refreshing}
          className="inline-flex items-center gap-2 rounded-xl border border-[var(--primary)]/10 bg-white px-4 py-2 text-sm font-medium"
        >
          <RefreshCw className={cn("h-4 w-4", refreshing && "animate-spin")} />
          {refreshing ? "Syncing…" : "Sync now"}
        </button>
      </header>

      {error && <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}

      <section className="mt-6 rounded-2xl border-2 border-red-200 bg-red-50 p-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <Siren className="h-8 w-8 text-red-600" />
            <div>
              <h2 className="text-lg font-bold text-red-900">SOS — Emergency</h2>
              <p className="text-sm text-red-800">
                Immediate alert to Porterchain operations with your GPS location
              </p>
            </div>
          </div>
          <button
            type="button"
            disabled={actionPending === "sos"}
            onClick={() => {
              if (!navigator.geolocation) {
                void triggerSos();
                return;
              }
              navigator.geolocation.getCurrentPosition(
                (pos) =>
                  void triggerSos({
                    lat: pos.coords.latitude,
                    lng: pos.coords.longitude,
                  }),
                () => void triggerSos()
              );
            }}
            className="rounded-xl bg-red-600 px-6 py-3 text-sm font-bold text-white shadow-md disabled:opacity-50"
          >
            {actionPending === "sos" ? "Sending…" : "SOS BUTTON"}
          </button>
        </div>
      </section>

      <section className="mt-6 grid gap-4 lg:grid-cols-2">
        <EmergencyContactCard
          contact={snap.emergency_contact}
          pending={actionPending === "contact"}
          onSave={updateEmergencyContact}
        />
        <ChatPlaceholder chat={snap.chat} />
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-bold">Report Incident</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Delivery issues auto-file claims when an order is linked
        </p>
        <IncidentForm
          types={snap.incident_types}
          pending={actionPending === "incident"}
          onSubmit={reportIncident}
        />
      </section>

      <section className="mt-8 rounded-2xl bg-white p-5 shadow-sm">
        <div className="flex items-center gap-2">
          <LifeBuoy className="h-5 w-5 text-[var(--secondary)]" />
          <h2 className="text-lg font-bold">Support Tickets</h2>
        </div>
        <TicketForm pending={actionPending === "ticket"} onSubmit={createTicket} />
        <ul className="mt-4 space-y-2">
          {snap.tickets.length === 0 ? (
            <li className="text-sm text-[var(--muted)]">No tickets yet</li>
          ) : (
            snap.tickets.map((t) => (
              <li key={t.id} className="rounded-xl bg-[var(--gray-bg)] px-4 py-3 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-semibold">{t.subject}</p>
                  <div className="flex gap-2">
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-xs font-semibold capitalize",
                        statusStyle(t.status)
                      )}
                    >
                      {t.status}
                    </span>
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-xs font-semibold capitalize",
                        priorityStyle(t.priority)
                      )}
                    >
                      {t.priority}
                    </span>
                  </div>
                </div>
                <p className="mt-1 text-xs text-[var(--muted)]">
                  {t.ticket_number} · {formatSupportDate(t.created_at)}
                </p>
              </li>
            ))
          )}
        </ul>
      </section>

      <section className="mt-8 rounded-2xl bg-white p-5 shadow-sm">
        <div className="flex items-center gap-2">
          <FileWarning className="h-5 w-5 text-[var(--secondary)]" />
          <h2 className="text-lg font-bold">Claims</h2>
        </div>
        <ClaimForm pending={actionPending === "claim"} onSubmit={(body) => openClaim(body)} />
        <ul className="mt-4 space-y-2">
          {snap.claims.length === 0 ? (
            <li className="text-sm text-[var(--muted)]">No claims filed</li>
          ) : (
            snap.claims.map((c) => (
              <li key={c.id} className="rounded-xl bg-[var(--gray-bg)] px-4 py-3 text-sm">
                <div className="flex justify-between gap-2">
                  <p className="font-semibold capitalize">{c.claim_type.replace(/_/g, " ")}</p>
                  <span
                    className={cn(
                      "rounded-full px-2 py-0.5 text-xs font-semibold capitalize",
                      statusStyle(c.status)
                    )}
                  >
                    {c.status}
                  </span>
                </div>
                <p className="mt-1 text-xs text-[var(--muted)]">
                  {c.claim_number} · Order {c.order_number ?? c.order_id.slice(0, 8)}
                </p>
              </li>
            ))
          )}
        </ul>
      </section>

      <section className="mt-8 rounded-2xl bg-white p-5 shadow-sm">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-[var(--secondary)]" />
          <h2 className="text-lg font-bold">Incident Log</h2>
        </div>
        <ul className="mt-4 space-y-2">
          {snap.incidents.length === 0 ? (
            <li className="text-sm text-[var(--muted)]">No incidents reported</li>
          ) : (
            snap.incidents.map((i) => (
              <li key={i.id} className="rounded-xl bg-[var(--gray-bg)] px-4 py-3 text-sm">
                <p className="font-semibold">
                  {incidentLabel(i.incident_type, snap.incident_types)}
                </p>
                <p className="mt-1 text-[var(--muted)]">{i.description}</p>
                <p className="mt-1 text-xs text-[var(--muted)]">
                  {formatSupportDate(i.created_at)}
                  {i.claim_id ? ` · Claim linked` : ""}
                </p>
              </li>
            ))
          )}
        </ul>
      </section>

      <section className="mt-8 rounded-2xl bg-white p-5 shadow-sm">
        <div className="flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-[var(--secondary)]" />
          <h2 className="text-lg font-bold">Knowledge Base</h2>
        </div>
        {snap.knowledge_base.articles.length === 0 && snap.knowledge_base.faq.length === 0 ? (
          <p className="mt-4 text-sm text-[var(--muted)]">No articles published yet</p>
        ) : (
          <div className="mt-4 space-y-4">
            {snap.knowledge_base.articles.map((a) => (
              <article key={a.id} className="rounded-xl bg-[var(--gray-bg)] p-4">
                <h3 className="font-semibold">{a.title}</h3>
                <p className="mt-2 text-sm text-[var(--muted)]">{a.body}</p>
              </article>
            ))}
            {snap.knowledge_base.faq.map((f, idx) => (
              <article key={idx} className="rounded-xl bg-[var(--gray-bg)] p-4">
                <h3 className="font-semibold">{f.question}</h3>
                <p className="mt-2 text-sm text-[var(--muted)]">{f.answer}</p>
              </article>
            ))}
          </div>
        )}
      </section>

      <p className="mt-6 text-xs text-[var(--muted)]">
        Last synced {new Date(snap.last_updated).toLocaleString()}
      </p>
    </DriverShell>
  );
}

function ClaimForm({
  pending,
  onSubmit,
}: {
  pending: boolean;
  onSubmit: (body: { order_id: string; claim_type: string; description?: string }) => Promise<void>;
}) {
  const [orderId, setOrderId] = useState("");
  const [claimType, setClaimType] = useState("damaged_parcel");
  const [description, setDescription] = useState("");

  return (
    <form
      className="mt-4 grid gap-3 border-b border-[var(--primary)]/10 pb-4 lg:grid-cols-2"
      onSubmit={async (e) => {
        e.preventDefault();
        if (!orderId.trim()) return;
        await onSubmit({
          order_id: orderId.trim(),
          claim_type: claimType,
          description: description.trim() || undefined,
        });
        setDescription("");
      }}
    >
      <input
        value={orderId}
        onChange={(e) => setOrderId(e.target.value)}
        placeholder="Order ID"
        required
        className="rounded-xl border border-[var(--primary)]/10 px-3 py-2 text-sm"
      />
      <select
        value={claimType}
        onChange={(e) => setClaimType(e.target.value)}
        className="rounded-xl border border-[var(--primary)]/10 px-3 py-2 text-sm"
      >
        <option value="damaged_parcel">Damaged parcel</option>
        <option value="lost_parcel">Lost parcel</option>
        <option value="delivery_failed">Delivery failed</option>
        <option value="vehicle_damage">Vehicle damage</option>
        <option value="driver_complaint">Driver complaint</option>
      </select>
      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Description (optional)"
        rows={2}
        className="rounded-xl border border-[var(--primary)]/10 px-3 py-2 text-sm lg:col-span-2"
      />
      <button
        type="submit"
        disabled={pending}
        className="rounded-xl bg-[var(--primary)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50 lg:col-span-2"
      >
        {pending ? "Filing…" : "Open claim"}
      </button>
    </form>
  );
}

function EmergencyContactCard({
  contact,
  pending,
  onSave,
}: {
  contact: {
    name?: string | null;
    phone?: string | null;
    relationship?: string | null;
    ops_hotline: string;
    ops_email: string;
  };
  pending: boolean;
  onSave: (body: { name: string; phone: string; relationship?: string }) => Promise<void>;
}) {
  const [name, setName] = useState(contact.name ?? "");
  const [phone, setPhone] = useState(contact.phone ?? "");
  const [relationship, setRelationship] = useState(contact.relationship ?? "");

  useEffect(() => {
    setName(contact.name ?? "");
    setPhone(contact.phone ?? "");
    setRelationship(contact.relationship ?? "");
  }, [contact]);

  return (
    <div className="rounded-2xl bg-white p-5 shadow-sm">
      <div className="flex items-center gap-2">
        <Phone className="h-5 w-5 text-[var(--secondary)]" />
        <h2 className="text-lg font-bold">Emergency Contact</h2>
      </div>
      <dl className="mt-4 space-y-2 text-sm">
        <div className="flex justify-between">
          <dt className="text-[var(--muted)]">Ops hotline</dt>
          <dd className="font-semibold">{contact.ops_hotline}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-[var(--muted)]">Ops email</dt>
          <dd className="font-semibold">{contact.ops_email}</dd>
        </div>
      </dl>
      <form
        className="mt-4 space-y-2 border-t border-[var(--primary)]/10 pt-4"
        onSubmit={async (e) => {
          e.preventDefault();
          await onSave({ name, phone, relationship: relationship || undefined });
        }}
      >
        <p className="text-xs font-semibold uppercase text-[var(--muted)]">
          Your emergency contact
        </p>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Name"
          required
          className="w-full rounded-xl border border-[var(--primary)]/10 px-3 py-2 text-sm"
        />
        <input
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          placeholder="Phone"
          required
          className="w-full rounded-xl border border-[var(--primary)]/10 px-3 py-2 text-sm"
        />
        <input
          value={relationship}
          onChange={(e) => setRelationship(e.target.value)}
          placeholder="Relationship (optional)"
          className="w-full rounded-xl border border-[var(--primary)]/10 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={pending}
          className="rounded-xl bg-[var(--primary)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
        >
          {pending ? "Saving…" : "Save contact"}
        </button>
      </form>
    </div>
  );
}

function ChatPlaceholder({
  chat,
}: {
  chat: { enabled: boolean; status: string; message: string };
}) {
  return (
    <div className="rounded-2xl bg-white p-5 shadow-sm">
      <div className="flex items-center gap-2">
        <MessageSquare className="h-5 w-5 text-[var(--secondary)]" />
        <h2 className="text-lg font-bold">Chat</h2>
        <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-semibold text-gray-600">
          Future
        </span>
      </div>
      <p className="mt-4 text-sm text-[var(--muted)]">{chat.message}</p>
      <button
        type="button"
        disabled
        className="mt-4 w-full cursor-not-allowed rounded-xl border border-dashed border-[var(--primary)]/20 px-4 py-3 text-sm text-[var(--muted)]"
      >
        Live chat — {chat.status.replace(/_/g, " ")}
      </button>
    </div>
  );
}

function IncidentForm({
  types,
  pending,
  onSubmit,
}: {
  types: Array<{ id: string; label: string }>;
  pending: boolean;
  onSubmit: (body: {
    incident_type: string;
    description: string;
    order_id?: string;
  }) => Promise<void>;
}) {
  const [incidentType, setIncidentType] = useState(types[0]?.id ?? "unable_to_deliver");
  const [orderId, setOrderId] = useState("");
  const [description, setDescription] = useState("");

  return (
    <form
      className="mt-4 grid gap-3 rounded-2xl bg-white p-5 shadow-sm lg:grid-cols-2"
      onSubmit={async (e) => {
        e.preventDefault();
        if (!description.trim()) return;
        await onSubmit({
          incident_type: incidentType,
          description: description.trim(),
          order_id: orderId.trim() || undefined,
        });
        setDescription("");
      }}
    >
      <select
        value={incidentType}
        onChange={(e) => setIncidentType(e.target.value)}
        className="rounded-xl border border-[var(--primary)]/10 px-3 py-2 text-sm"
      >
        {types.map((t) => (
          <option key={t.id} value={t.id}>
            {t.label}
          </option>
        ))}
      </select>
      <input
        value={orderId}
        onChange={(e) => setOrderId(e.target.value)}
        placeholder="Order ID (required for parcel claims)"
        className="rounded-xl border border-[var(--primary)]/10 px-3 py-2 text-sm"
      />
      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Describe what happened…"
        required
        rows={3}
        className="lg:col-span-2 rounded-xl border border-[var(--primary)]/10 px-3 py-2 text-sm"
      />
      <button
        type="submit"
        disabled={pending || !description.trim()}
        className="lg:col-span-2 rounded-xl bg-[var(--secondary)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
      >
        {pending ? "Submitting…" : "Submit incident report"}
      </button>
    </form>
  );
}

function TicketForm({
  pending,
  onSubmit,
}: {
  pending: boolean;
  onSubmit: (body: { subject: string; description?: string; order_id?: string }) => Promise<void>;
}) {
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [orderId, setOrderId] = useState("");

  return (
    <form
      className="mt-4 grid gap-2 sm:grid-cols-2"
      onSubmit={async (e) => {
        e.preventDefault();
        if (!subject.trim()) return;
        await onSubmit({
          subject: subject.trim(),
          description: description.trim() || undefined,
          order_id: orderId.trim() || undefined,
        });
        setSubject("");
        setDescription("");
        setOrderId("");
      }}
    >
      <input
        value={subject}
        onChange={(e) => setSubject(e.target.value)}
        placeholder="Subject"
        required
        className="sm:col-span-2 rounded-xl border border-[var(--primary)]/10 px-3 py-2 text-sm"
      />
      <input
        value={orderId}
        onChange={(e) => setOrderId(e.target.value)}
        placeholder="Order ID (optional)"
        className="rounded-xl border border-[var(--primary)]/10 px-3 py-2 text-sm"
      />
      <input
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Details"
        className="rounded-xl border border-[var(--primary)]/10 px-3 py-2 text-sm"
      />
      <button
        type="submit"
        disabled={pending || !subject.trim()}
        className="sm:col-span-2 rounded-xl border border-[var(--primary)]/10 bg-[var(--gray-bg)] px-4 py-2 text-sm font-semibold disabled:opacity-50"
      >
        {pending ? "Creating…" : "Open support ticket"}
      </button>
    </form>
  );
}
