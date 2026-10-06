import AccountSecurityClient from "@/components/account/AccountSecurityClient";

/** Account security is session-bound; no shared list to prefetch. */
export default function AccountSecurityPage() {
  return <AccountSecurityClient />;
}
