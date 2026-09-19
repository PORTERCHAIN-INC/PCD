"use client";

import { CheckCircle2, Circle, Clock, LogOut, RefreshCw, Shield, XCircle } from "lucide-react";
import { SignOutButton } from "@clerk/nextjs";
import MerchantLogo from "@/components/branding/MerchantLogo";
import Button from "@/components/ui/Button";
import { merchantStatusLabel, onboardingStepStatusLabel } from "@/lib/catalog";
import {
  merchantSignupUrl,
  onboardingWaitCopy,
  shouldAskOwnerForCompanyFile,
  type PortalOnboardingStatus,
} from "@/lib/onboarding";
import { publicEnv } from "@/lib/env";
import { cn } from "@/lib/utils";
import {
  AddressAutocompleteInput,
  GoogleMapsProvider,
  type BookingAddress,
} from "@porterchain/maps";
import { useState } from "react";

function stepIcon(step: PortalOnboardingStatus["steps"][number]) {
  if (step.complete) return <CheckCircle2 className="h-5 w-5 text-emerald-600" />;
  if (step.status === "suspended" || step.status === "inactive" || step.status === "closed") {
    return <XCircle className="h-5 w-5 text-red-600" />;
  }
  if (
    step.status === "pending_review" ||
    step.status === "onboarding" ||
    step.status === "pending"
  ) {
    return <Clock className="h-5 w-5 text-amber-600" />;
  }
  return <Circle className="h-5 w-5 text-muted" />;
}

function statusLabel(step: PortalOnboardingStatus["steps"][number]) {
  return step.status_label || onboardingStepStatusLabel(step.status, step.complete);
}

export default function PortalOnboardingView({
  data,
  refreshing,
  onRefresh,
  onSaveVertical,
  onSaveCompany,
}: {
  data: PortalOnboardingStatus;
  refreshing?: boolean;
  onRefresh: () => void;
  onSaveVertical?: (vertical: string) => Promise<void>;
  onSaveCompany?: (body: {
    company_name?: string;
    legal_name?: string;
    phone?: string;
    hst_number?: string;
    billing_address?: {
      formatted: string;
      postal?: string;
      place_id?: string;
      lat?: number;
      lng?: number;
    };
  }) => Promise<void>;
}) {
  const [savingVertical, setSavingVertical] = useState(false);
  const [verticalError, setVerticalError] = useState<string | null>(null);
  const file = data.company_file;
  const [companyName, setCompanyName] = useState(file?.company_name ?? "");
  const [legalName, setLegalName] = useState(file?.legal_name ?? "");
  const [phone, setPhone] = useState(file?.phone ?? "");
  const [hst, setHst] = useState(file?.hst_number ?? "");
  const [billing, setBilling] = useState<BookingAddress>({
    formatted: file?.billing_address?.formatted ?? "",
    postal: file?.billing_address?.postal,
    placeId: file?.billing_address?.place_id,
  });
  const [savingFile, setSavingFile] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const [fileSaved, setFileSaved] = useState(false);

  const verticalStep = data.steps.find((s) => s.id === "business_vertical");
  const showVerticalPicker =
    Boolean(data.can_edit_company) &&
    verticalStep &&
    !verticalStep.complete &&
    (data.vertical_options?.length ?? 0) > 0;

  const signupUrl = merchantSignupUrl(data.signup_url);
  const askOwnerForFile = shouldAskOwnerForCompanyFile(data);

  async function saveFile() {
    if (!onSaveCompany) return;
    setSavingFile(true);
    setFileError(null);
    setFileSaved(false);
    try {
      await onSaveCompany({
        company_name: companyName || undefined,
        legal_name: legalName || undefined,
        phone: phone || undefined,
        hst_number: hst || undefined,
        billing_address: billing.formatted
          ? {
              formatted: billing.formatted,
              postal: billing.postal,
              place_id: billing.placeId,
              lat: billing.lat,
              lng: billing.lng,
            }
          : undefined,
      });
      setFileSaved(true);
    } catch (err) {
      setFileError(err instanceof Error ? err.message : "Could not save the company file.");
    } finally {
      setSavingFile(false);
    }
  }

  return (
    <GoogleMapsProvider apiKey={publicEnv.googleMapsApiKey}>
      <div className="min-h-dvh bg-gray-bg">
        <header className="border-b border-primary/10 bg-white">
          <div className="mx-auto flex max-w-3xl items-center justify-between gap-4 px-4 py-4">
            <div className="flex items-center gap-3">
              <MerchantLogo src={data.logo_url} name={data.company_name} />
              <div>
                <p className="text-sm font-bold text-primary">PorterChain Merchant</p>
                <p className="text-xs text-muted">
                  {data.status_label || merchantStatusLabel(data.status)}
                  {data.role_label ? ` · ${data.role_label}` : ""}
                </p>
              </div>
            </div>
            <SignOutButton redirectUrl="/sign-in">
              <button
                type="button"
                className="inline-flex items-center gap-2 rounded-xl border border-primary/10 px-3 py-2 text-sm text-muted"
              >
                <LogOut className="h-4 w-4" />
                Sign out
              </button>
            </SignOutButton>
          </div>
        </header>

        <main className="mx-auto max-w-3xl px-4 py-8">
          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <div className="flex items-start gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-amber-50">
                <Shield className="h-6 w-6 text-amber-700" />
              </div>
              <div className="min-w-0 flex-1">
                <h1 className="text-xl font-bold text-primary">
                  {data.company_name || "Company file"}
                </h1>
                <p className="mt-2 text-sm text-muted">{onboardingWaitCopy(data)}</p>
              </div>
              <button
                type="button"
                onClick={onRefresh}
                disabled={refreshing}
                className="inline-flex shrink-0 items-center gap-2 rounded-xl border border-primary/10 px-3 py-2 text-sm"
              >
                <RefreshCw className={cn("h-4 w-4", refreshing && "animate-spin")} />
                Refresh
              </button>
            </div>
          </div>

          {data.can_edit_company && onSaveCompany ? (
            <div className="mt-6 rounded-2xl border border-primary/10 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-primary">Company file</h2>
              <p className="mt-1 text-sm text-muted">
                Legal name, phone, billing address, and HST. This is the same record Settings uses
                after activation.
              </p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <label className="text-sm">
                  Operating name
                  <input
                    className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                  />
                </label>
                <label className="text-sm">
                  Legal name
                  <input
                    className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2"
                    value={legalName}
                    onChange={(e) => setLegalName(e.target.value)}
                  />
                </label>
                <label className="text-sm">
                  Phone
                  <input
                    className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                  />
                </label>
                <label className="text-sm">
                  HST number
                  <input
                    className="mt-1 w-full rounded-xl border border-primary/15 px-3 py-2"
                    value={hst}
                    onChange={(e) => setHst(e.target.value)}
                    placeholder="123456789RT0001"
                  />
                </label>
                <label className="text-sm sm:col-span-2">
                  Billing address
                  <div className="mt-1">
                    <AddressAutocompleteInput
                      id="onboarding-billing"
                      value={billing.formatted}
                      onChange={(formatted) => setBilling({ ...billing, formatted })}
                      onPlaceSelect={setBilling}
                      apiKey={publicEnv.googleMapsApiKey}
                      placeholder="Ontario billing address"
                      fallbackClassName="w-full rounded-xl border border-primary/15 px-3 py-2"
                    />
                  </div>
                </label>
              </div>
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <Button size="sm" disabled={savingFile} onClick={() => void saveFile()}>
                  Save company file
                </Button>
                {fileSaved ? <p className="text-sm text-emerald-700">Saved</p> : null}
              </div>
              {fileError ? (
                <p className="mt-2 text-sm text-red-600" role="alert">
                  {fileError}
                </p>
              ) : null}
            </div>
          ) : askOwnerForFile ? (
            <p className="mt-6 rounded-2xl border border-primary/10 bg-white px-4 py-3 text-sm text-muted">
              Ask your owner to finish the company file
              {data.role_label ? `. Your role is ${data.role_label}` : ""}.
            </p>
          ) : null}

          {showVerticalPicker && onSaveVertical ? (
            <div className="mt-6 rounded-2xl border border-secondary/20 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-primary">Select your business vertical</h2>
              <p className="mt-1 text-sm text-muted">Optional. Does not unlock bookings.</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {data.vertical_options!.map((option) => (
                  <button
                    key={option.slug}
                    type="button"
                    disabled={savingVertical}
                    onClick={async () => {
                      setVerticalError(null);
                      setSavingVertical(true);
                      try {
                        await onSaveVertical(option.slug);
                      } catch (err) {
                        setVerticalError(
                          err instanceof Error ? err.message : "Could not save that business type."
                        );
                      } finally {
                        setSavingVertical(false);
                      }
                    }}
                    className={cn(
                      "rounded-xl border px-4 py-3 text-left text-sm transition-colors",
                      data.vertical === option.slug
                        ? "border-secondary bg-secondary/5 font-semibold text-primary"
                        : "border-primary/10 hover:border-secondary/40"
                    )}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
              {verticalError ? (
                <p className="mt-3 text-sm text-red-600" role="alert">
                  {verticalError}
                </p>
              ) : null}
            </div>
          ) : null}

          <ol className="mt-6 space-y-3">
            {data.steps.map((step) => (
              <li
                key={step.id}
                className={cn(
                  "rounded-2xl border bg-white p-5 shadow-sm",
                  step.complete
                    ? "border-emerald-100"
                    : step.status === "onboarding" || step.status === "pending"
                      ? "border-amber-100"
                      : "border-primary/8"
                )}
              >
                <div className="flex items-start gap-3">
                  {stepIcon(step)}
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="font-semibold text-primary">{step.label}</h2>
                      <span
                        className={cn(
                          "rounded-full px-2 py-0.5 text-xs font-medium",
                          step.complete ? "bg-emerald-50 text-emerald-700" : "bg-gray-bg text-muted"
                        )}
                      >
                        {statusLabel(step)}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-muted">{step.description}</p>
                  </div>
                </div>
              </li>
            ))}
          </ol>

          {data.ready ? (
            <div className="mt-6 rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
              This company is {merchantStatusLabel("ACTIVE")} — opening your merchant portal…
            </div>
          ) : (
            <p className="mt-6 text-center text-xs text-muted">
              Teammates create their own account at{" "}
              <a href={signupUrl} className="font-medium text-secondary underline">
                {signupUrl}
              </a>{" "}
              with the email you reserved. Password stays in Clerk. Status refreshes every 30
              seconds.
            </p>
          )}
        </main>
      </div>
    </GoogleMapsProvider>
  );
}
