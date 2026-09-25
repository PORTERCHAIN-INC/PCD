import type { OrderDetail } from "@/lib/orders";

export type Order360Actions = {
  onAssignDriver: () => void;
  onReassignDriver: () => void;
  /** Optional suggested exception column from assist (failed/returned/lost/damaged). */
  onMarkException: (suggested?: string) => void;
  onCancel: () => void;
  onDuplicate: () => void;
  onRebook: () => void;
  onCreateReturn: () => void;
  onGenerateInvoice: () => void;
  onResendReceipt: () => void;
  onRefund: () => void;
  onOpenClaim: () => void;
  onOpenSupport: () => void;
  onShareTracking: () => void;
  onPrintLabels: () => void;
  onPrintManifest: () => void;
  onDownloadRecord: () => void;
};

export type { OrderDetail };
