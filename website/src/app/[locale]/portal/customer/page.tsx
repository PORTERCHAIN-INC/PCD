"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import SiteShell from "@/components/layout/SiteShell";
import Container from "@/components/ui/Container";
import CustomerAccessGate from "@/components/portal/CustomerAccessGate";
import CustomerPortalHeader from "@/components/portal/CustomerPortalHeader";
import CustomerDashboardView from "@/components/portal/CustomerDashboardView";
import {
  createCustomerSupportTicket,
  getCustomerDashboard,
  getCustomerRebookPayload,
  type CustomerDashboard,
} from "@/lib/api";
import { isClerkConfigured } from "@/lib/env";

export default function CustomerPortalPage() {
  if (isClerkConfigured()) {
    return <CustomerPortalClerk />;
  }
  return <CustomerPortalContent isLoaded isSignedIn getToken={async () => "dev"} />;
}

function CustomerPortalClerk() {
  const router = useRouter();
  const { isSignedIn, isLoaded, getToken } = useAuth();

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      router.replace("/login");
    }
  }, [isLoaded, isSignedIn, router]);

  if (!isLoaded || !isSignedIn) {
    return (
      <SiteShell>
        <Container className="py-16 md:py-24 max-w-4xl">
          <p className="type-small text-muted">Loading…</p>
        </Container>
      </SiteShell>
    );
  }

  return (
    <CustomerAccessGate>
      <CustomerPortalContent
        isLoaded={isLoaded}
        isSignedIn={Boolean(isSignedIn)}
        getToken={getToken}
      />
    </CustomerAccessGate>
  );
}

function CustomerPortalContent({
  isLoaded,
  isSignedIn,
  getToken,
}: {
  isLoaded: boolean;
  isSignedIn: boolean;
  getToken: () => Promise<string | null>;
}) {
  const t = useTranslations("portal.customer");
  const [dashboard, setDashboard] = useState<CustomerDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [supportSubject, setSupportSubject] = useState("");
  const [supportMessage, setSupportMessage] = useState("");
  const [supportSent, setSupportSent] = useState(false);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    let cancelled = false;
    async function load() {
      try {
        const token = (await getToken()) ?? "dev";
        const data = await getCustomerDashboard(token);
        if (!cancelled) {
          setDashboard(data);
          setError(null);
        }
      } catch {
        if (!cancelled) setError(t("loadError"));
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [isLoaded, isSignedIn, getToken, t]);

  const submitSupport = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const token = (await getToken()) ?? "dev";
      await createCustomerSupportTicket(token, {
        subject: supportSubject,
        description: supportMessage,
        order_id: dashboard?.active_order?.order_id,
      });
      setSupportSent(true);
      setSupportSubject("");
      setSupportMessage("");
    } catch {
      setError(t("supportError"));
    }
  };

  const rebook = async (orderId: string) => {
    try {
      const token = (await getToken()) ?? "dev";
      const payload = await getCustomerRebookPayload(token, orderId);
      const params = new URLSearchParams({
        rebook: payload.source_order_id,
        tracking: payload.tracking_number,
      });
      window.location.href = `/#book?${params}`;
    } catch {
      setError(t("rebookError"));
    }
  };

  return (
    <SiteShell>
      <Container className="py-16 md:py-24 max-w-4xl">
        <CustomerPortalHeader />
        <CustomerDashboardView
          dashboard={dashboard}
          error={error}
          supportSent={supportSent}
          supportSubject={supportSubject}
          supportMessage={supportMessage}
          onSupportSubjectChange={setSupportSubject}
          onSupportMessageChange={setSupportMessage}
          onSubmitSupport={submitSupport}
          onRebook={rebook}
        />
      </Container>
    </SiteShell>
  );
}
