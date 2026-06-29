"use client";

import { useMemo, useState } from "react";
import { Plus, Info, Search, X, Users, Target, Layers } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { crm, type Company, type Deal, type Lead, type PipelineCard } from "@/lib/crm";
import { KanbanBoard } from "@/components/crm/KanbanBoard";
import { ActivityTimeline } from "@/components/crm/ActivityTimeline";
import { LeadDetailModal } from "@/components/crm/LeadDetailModal";
import { Dropdown } from "@/components/crm/filters";
import { Badge, Button, Drawer, Field, Input, Select, Spinner } from "@/components/crm/primitives";
import { STAGE_LABELS, STATUS_TONE, money, shortDate, titleCase } from "@/lib/crmFormat";

const STAGES = [
  "prospecting",
  "qualified",
  "meeting_scheduled",
  "quote_sent",
  "negotiation",
  "contract_review",
  "won",
  "lost",
  "hold",
];

// Dropping a lead into one of these columns simply updates its status (no deal yet).
const LEAD_STATUS_STAGES: Record<string, string> = {
  prospecting: "contacted",
  qualified: "qualified",
  lost: "unqualified",
};

const blank = (): Partial<Deal> => ({
  name: "",
  stage: "prospecting",
  expected_revenue_cents: 0,
  probability: 10,
});

export default function DealsPage() {
  const { getApiToken } = useAdminAuth();
  const [version, setVersion] = useState(0);

  // Advanced search (server-side, reaches the full lead+deal dataset)
  const [search, setSearch] = useState("");
  const [cardType, setCardType] = useState("");
  const [minValue, setMinValue] = useState("");

  const { data: board, error } = useApiData(
    (t) =>
      crm.pipeline(t, {
        search: search || undefined,
        card_type: cardType || undefined,
        min_value_cents: minValue || undefined,
      }),
    [search, cardType, minValue, version]
  );
  const { data: companies } = useApiData((t) => crm.companies(t), []);

  const totals = useMemo(() => {
    const cols = board ?? [];
    return {
      cards: cols.reduce((s, c) => s + c.count, 0),
      leads: cols.reduce((s, c) => s + c.lead_count, 0),
      deals: cols.reduce((s, c) => s + c.deal_count, 0),
      value: cols.reduce((s, c) => s + c.value_cents, 0),
    };
  }, [board]);

  const hasFilters = Boolean(search || cardType || minValue);
  const clearSearch = () => {
    setSearch("");
    setCardType("");
    setMinValue("");
  };

  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<Partial<Deal>>(blank());
  const [selectedDeal, setSelectedDeal] = useState<Deal | null>(null);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const refresh = () => setVersion((v) => v + 1);

  async function move(card: PipelineCard, toStage: string, position: number) {
    const token = await getApiToken();
    if (card.type === "deal") {
      await crm.moveDeal(token, card.id, toStage, position);
    } else if (LEAD_STATUS_STAGES[toStage]) {
      await crm.updateLead(token, card.id, { status: LEAD_STATUS_STAGES[toStage] });
    } else {
      await crm.convertLead(token, card.id, { create_deal: true, target_stage: toStage });
      setToast(`"${card.title}" converted into a deal at ${STAGE_LABELS[toStage] ?? toStage}.`);
    }
    refresh();
  }

  async function openCard(card: PipelineCard) {
    const token = await getApiToken();
    if (card.type === "deal") {
      setSelectedDeal(await crm.deal(token, card.id));
    } else {
      setSelectedLead(await crm.lead(token, card.id));
    }
  }

  async function submitCreate() {
    if (!form.name) return;
    setBusy(true);
    try {
      const token = await getApiToken();
      await crm.createDeal(token, {
        ...form,
        expected_revenue_cents: Number(form.expected_revenue_cents) || 0,
      });
      setCreating(false);
      setForm(blank());
      refresh();
    } finally {
      setBusy(false);
    }
  }

  async function changeStage(stage: string) {
    if (!selectedDeal) return;
    setBusy(true);
    try {
      const token = await getApiToken();
      const updated = await crm.updateDeal(token, selectedDeal.id, { stage });
      setSelectedDeal(updated);
      refresh();
    } finally {
      setBusy(false);
    }
  }

  async function convertLead(lead: Lead) {
    setBusy(true);
    try {
      const token = await getApiToken();
      await crm.convertLead(token, lead.id, { create_deal: true });
      setSelectedLead(await crm.lead(token, lead.id));
      refresh();
    } finally {
      setBusy(false);
    }
  }

  if (error) return <p className="text-red-600">{error}</p>;

  return (
    <div className="space-y-4">
      {toast && (
        <div className="rounded-xl border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-700">
          {toast}
        </div>
      )}
      <div className="space-y-3 rounded-2xl border border-primary/10 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-[220px] flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search the whole pipeline — company, city, deal name…"
              className="w-full rounded-xl border border-primary/15 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:border-secondary focus:ring-2 focus:ring-secondary/20"
            />
          </div>
          <Dropdown
            label="Type"
            icon={<Layers className="h-4 w-4" />}
            value={cardType}
            onChange={setCardType}
            allLabel="Leads & deals"
            options={[
              { value: "lead", label: "Leads only" },
              { value: "deal", label: "Deals only" },
            ]}
          />
          <Dropdown
            label="Min value"
            icon={<Target className="h-4 w-4" />}
            value={minValue}
            onChange={setMinValue}
            allLabel="Any value"
            options={[
              { value: "100000", label: "$1k+" },
              { value: "1000000", label: "$10k+" },
              { value: "5000000", label: "$50k+" },
            ]}
          />
          {hasFilters && (
            <Button variant="ghost" onClick={clearSearch} className="text-xs">
              <X className="h-4 w-4" />
              Clear
            </Button>
          )}
          <Button onClick={() => setCreating(true)} className="ml-auto">
            <Plus className="h-4 w-4" />
            New Deal
          </Button>
        </div>
        <div className="flex flex-wrap items-center gap-3 border-t border-primary/5 pt-2 text-xs text-muted">
          <span className="inline-flex items-center gap-1.5">
            <Users className="h-3.5 w-3.5 text-amber-500" />
            {totals.leads.toLocaleString()} leads
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Target className="h-3.5 w-3.5 text-secondary" />
            {totals.deals.toLocaleString()} deals
          </span>
          <span>· Pipeline value {money(totals.value)}</span>
          <span className="ml-auto inline-flex items-center gap-1.5">
            <Info className="h-3.5 w-3.5 text-secondary" />
            Drag a lead forward to qualify or convert it into a deal
          </span>
        </div>
      </div>

      {!board ? (
        <Spinner label="Loading pipeline…" />
      ) : (
        <KanbanBoard columns={board} onMove={move} onCardClick={openCard} />
      )}

      {/* Create deal */}
      <Drawer
        open={creating}
        onClose={() => setCreating(false)}
        title="New deal"
        footer={
          <>
            <Button variant="outline" onClick={() => setCreating(false)}>
              Cancel
            </Button>
            <Button onClick={submitCreate} disabled={busy || !form.name}>
              Create deal
            </Button>
          </>
        }
      >
        <div className="grid grid-cols-2 gap-4">
          <Field label="Deal name *" className="col-span-2">
            <Input
              value={form.name ?? ""}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </Field>
          <Field label="Company" className="col-span-2">
            <Select
              value={form.company_id ?? ""}
              onChange={(e) => setForm({ ...form, company_id: e.target.value })}
            >
              <option value="">— None —</option>
              {(companies ?? []).map((c: Company) => (
                <option key={c.id} value={c.id}>
                  {c.operating_name || c.legal_name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Stage">
            <Select
              value={form.stage ?? "prospecting"}
              onChange={(e) => setForm({ ...form, stage: e.target.value })}
            >
              {STAGES.map((s) => (
                <option key={s} value={s}>
                  {STAGE_LABELS[s] ?? titleCase(s)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Expected revenue (cents)">
            <Input
              type="number"
              value={(form.expected_revenue_cents as number) ?? 0}
              onChange={(e) => setForm({ ...form, expected_revenue_cents: Number(e.target.value) })}
            />
          </Field>
        </div>
      </Drawer>

      {/* Deal detail */}
      <Drawer
        open={!!selectedDeal}
        onClose={() => setSelectedDeal(null)}
        title={selectedDeal?.name ?? "Deal"}
      >
        {selectedDeal && (
          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={STATUS_TONE[selectedDeal.stage]}>
                {STAGE_LABELS[selectedDeal.stage] ?? titleCase(selectedDeal.stage)}
              </Badge>
              <Badge tone="sky">{selectedDeal.probability}% win</Badge>
              <span className="text-lg font-bold text-secondary">
                {money(selectedDeal.expected_revenue_cents)}
              </span>
            </div>
            <Field label="Move to stage">
              <Select
                value={selectedDeal.stage}
                onChange={(e) => changeStage(e.target.value)}
                disabled={busy}
              >
                {STAGES.map((s) => (
                  <option key={s} value={s}>
                    {STAGE_LABELS[s] ?? titleCase(s)}
                  </option>
                ))}
              </Select>
            </Field>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <Detail label="Company" value={selectedDeal.company_name} />
              <Detail label="Expected close" value={shortDate(selectedDeal.expected_close_date)} />
              <Detail label="Competitor" value={selectedDeal.competitor} />
              <Detail label="Created" value={shortDate(selectedDeal.created_at)} />
            </dl>
            <ActivityTimeline entityType="deal" entityId={selectedDeal.id} />
          </div>
        )}
      </Drawer>

      {/* Lead detail (tabbed) */}
      <LeadDetailModal
        lead={selectedLead}
        onClose={() => setSelectedLead(null)}
        onConvert={convertLead}
        busy={busy}
        onChanged={refresh}
      />
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="text-primary">{value || "—"}</dd>
    </div>
  );
}
