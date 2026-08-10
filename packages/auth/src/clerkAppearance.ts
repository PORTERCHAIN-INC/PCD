/** Shared Porterchain Clerk appearance — portals + website. */

const baseElements = {
  rootBox: "w-full",
  cardBox: "w-full shadow-none",
  card: "shadow-none border-0 bg-transparent p-0 gap-5 w-full",
  header: "gap-1",
  headerTitle: "text-lg font-semibold text-primary tracking-tight hidden",
  headerSubtitle: "text-sm text-muted hidden",
  socialButtonsBlockButton:
    "h-11 border border-primary/10 bg-white text-primary font-medium hover:bg-gray-bg transition-colors",
  socialButtonsBlockButtonText: "font-medium text-sm",
  dividerLine: "bg-primary/8",
  dividerText: "text-muted text-xs uppercase tracking-wide",
  formFieldLabel: "text-sm font-medium text-primary",
  formFieldInput:
    "h-11 rounded-xl border-primary/10 bg-gray-bg text-primary shadow-none focus:ring-2 focus:ring-secondary/20",
  formButtonPrimary:
    "h-11 rounded-xl bg-secondary hover:bg-[#1d4ed8] text-sm font-semibold shadow-none transition-colors",
  identityPreview: "rounded-xl border border-primary/8 bg-gray-bg",
  formFieldInputShowPasswordButton: "text-muted hover:text-primary",
  alert: "rounded-xl border border-red-200 bg-red-50 text-red-800",
} as const;

const baseVariables = {
  colorPrimary: "#2563eb",
  colorText: "#0a1628",
  colorTextSecondary: "#64748b",
  colorBackground: "#ffffff",
  colorInputBackground: "#f0f4f8",
  colorInputText: "#0a1628",
  colorNeutral: "#0a1628",
  borderRadius: "0.75rem",
  fontFamily: "var(--font-inter), Inter, system-ui, sans-serif",
  fontSize: "0.875rem",
} as const;

/** Open signup portals (merchant/customer): keep Clerk footer switch visible as backup. */
export const porterchainClerkAppearance = {
  variables: baseVariables,
  elements: {
    ...baseElements,
    footerAction: "mt-4 text-sm text-muted",
    footer: "mt-2",
  },
} as const;

/** Invite-only portals + Platform login: hide Clerk sign-up footer. */
export const porterchainClerkAppearanceInviteOnly = {
  variables: baseVariables,
  elements: {
    ...baseElements,
    footerAction: { display: "none" },
    footer: "hidden",
  },
} as const;
