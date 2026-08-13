"use client";

import { PASSWORD_ALLOWED_SPECIAL_DISPLAY, PASSWORD_MIN_LENGTH } from "./passwordPolicy";

export type PasswordRequirementsCopy = {
  title?: string;
  intro?: string;
  minLength?: string;
  uppercase?: string;
  lowercase?: string;
  number?: string;
  special?: string;
  allowedLabel?: string;
  strength?: string;
};

const DEFAULT_COPY: Required<PasswordRequirementsCopy> = {
  title: "How to set your password",
  intro: "If you create an email password, use all of the following so it is accepted:",
  minLength: `At least ${PASSWORD_MIN_LENGTH} characters`,
  uppercase: "An uppercase letter (A–Z)",
  lowercase: "A lowercase letter (a–z)",
  number: "A number (0–9)",
  special: "One allowed symbol (list below)",
  allowedLabel: "Allowed symbols",
  strength:
    "A strength meter appears as you type. Common or leaked passwords are blocked even if they match this pattern.",
};

type Props = {
  copy?: PasswordRequirementsCopy;
};

/**
 * Visible password recipe for Clerk SignUp. Clerk still enforces strength
 * (Fair+) and breach checks; this lists the character mix users should use.
 */
export function PasswordRequirements({ copy }: Props) {
  const t = { ...DEFAULT_COPY, ...copy };
  const items = [t.minLength, t.uppercase, t.lowercase, t.number, t.special];

  return (
    <aside
      className="mt-5 rounded-xl border border-primary/8 bg-gray-bg px-4 py-3"
      aria-label={t.title}
    >
      <p className="text-xs font-semibold text-primary">{t.title}</p>
      <p className="mt-1 text-xs leading-relaxed text-muted">{t.intro}</p>
      <ul className="mt-2 list-disc space-y-0.5 pl-4 text-xs leading-relaxed text-primary/85">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
      <p className="mt-2 text-xs leading-relaxed text-muted">
        {t.allowedLabel}:{" "}
        <span className="break-all font-mono text-[0.7rem] text-primary">
          {PASSWORD_ALLOWED_SPECIAL_DISPLAY}
        </span>
      </p>
      <p className="mt-2 text-xs leading-relaxed text-muted">{t.strength}</p>
    </aside>
  );
}
