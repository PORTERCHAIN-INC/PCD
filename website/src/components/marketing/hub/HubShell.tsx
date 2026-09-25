import { cn } from "@/lib/utils";

type Props = {
  children: React.ReactNode;
  className?: string;
};

/** Light advanced-UI canvas for Merchants / Drivers hubs. */
export default function HubShell({ children, className }: Props) {
  return (
    <div className={cn("relative bg-[#F4F6FA] text-primary", className)}>
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.4]"
        aria-hidden
        style={{
          backgroundImage:
            "radial-gradient(circle at 1px 1px, rgba(15,23,42,0.06) 1px, transparent 0)",
          backgroundSize: "24px 24px",
        }}
      />
      <div className="relative z-10">{children}</div>
    </div>
  );
}
