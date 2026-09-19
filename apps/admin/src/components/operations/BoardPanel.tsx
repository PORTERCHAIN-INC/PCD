"use client";

import { useState } from "react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { ops, type OpsOrder } from "@/lib/operations";
import { DispatchBoard } from "@/components/operations/DispatchBoard";
import { AssignDriverModal } from "@/components/orders/AssignDriverModal";
import {
  ExceptionReasonModal,
  isExceptionColumn,
  type ExceptionColumn,
} from "@/components/orders/ExceptionReasonModal";
import { Spinner } from "@/components/crm/primitives";

export function BoardPanel({
  tick,
  onMoved,
  onOpenOrder,
}: {
  tick: number;
  onMoved: () => void;
  onOpenOrder: (id: string) => void;
}) {
  const { getApiToken } = useAdminAuth();
  const { data, refetch } = useApiData((t) => ops.board(t), [tick], { key: "ops-board" });
  const [error, setError] = useState<string | null>(null);
  const [assignOrder, setAssignOrder] = useState<OpsOrder | null>(null);
  const [exceptionTarget, setExceptionTarget] = useState<{
    order: OpsOrder;
    column: ExceptionColumn;
  } | null>(null);

  async function move(order: OpsOrder, toColumn: string, reason?: string) {
    setError(null);
    try {
      const token = await getApiToken();
      await ops.moveBoardOrder(token, order.id, toColumn, reason);
      onMoved();
      await refetch();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not move order — invalid transition path.");
      throw e;
    }
  }

  function requestMove(order: OpsOrder, toColumn: string) {
    setError(null);
    if (toColumn === "assigned") {
      setAssignOrder(order);
      return;
    }
    if (isExceptionColumn(toColumn)) {
      setExceptionTarget({ order, column: toColumn });
      return;
    }
    setError(
      "Execution columns (accept → delivered) advance in Fleetbase / the driver app. Use Assign for drivers, or Order 360 for exceptions."
    );
  }

  if (!data) return <Spinner label="Loading board…" />;

  return (
    <div className="space-y-3">
      <p className="text-xs text-muted">
        Click a card to open Order 360. Drop on <strong>Assigned</strong> to pick a driver, or on
        Failed / Returned / Lost / Damaged to enter a reason. Accept → Deliver stays in Fleetbase.
      </p>
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {error}
        </div>
      )}
      <DispatchBoard
        columns={data}
        onMove={(o, col) => move(o, col)}
        onRequestMove={requestMove}
        onOpenOrder={(o) => onOpenOrder(o.id)}
      />
      <AssignDriverModal
        open={!!assignOrder}
        orderId={assignOrder?.id ?? null}
        trackingNumber={assignOrder?.tracking_number}
        currentDriverName={assignOrder?.driver}
        onClose={() => setAssignOrder(null)}
        onAssigned={() => {
          onMoved();
          void refetch();
        }}
      />
      <ExceptionReasonModal
        open={!!exceptionTarget}
        trackingNumber={exceptionTarget?.order.tracking_number}
        initialColumn={exceptionTarget?.column ?? ""}
        allowColumnChange={false}
        onClose={() => setExceptionTarget(null)}
        onConfirm={async (column, reason) => {
          if (!exceptionTarget) return;
          await move(exceptionTarget.order, column, reason);
        }}
      />
    </div>
  );
}
