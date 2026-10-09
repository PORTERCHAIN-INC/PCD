"use client";

import { forwardRef, type ComponentProps, type MouseEvent } from "react";
import { useLocale } from "next-intl";
import { BaseLink } from "./base-navigation";
import { canonicalInternalHref } from "@/lib/seo/internal-href";
import { readQuoteIntent, rememberQuoteIntent } from "@/lib/visitor-tracking";
import { isClerkClientShellPath } from "@/lib/clerk-shell";

type LinkProps = ComponentProps<typeof BaseLink>;

/**
 * next-intl Link that always renders the FINAL canonical URL (Search Console clean-up):
 *  - never renders `?from=` (CTA source is handed over in sessionStorage on click)
 *  - an href that already carries a locale (/en/faq) is not prefixed twice (/en/en/faq)
 *  - renamed / retired / gated targets are rewritten to where the 301 would land
 *  - links into the Clerk shell (/login, /sign-up) are NOT prefetched: their layout carries the
 *    Clerk browser SDK (~190 KB), which would otherwise download on every marketing page
 */
export const Link = forwardRef<HTMLAnchorElement, LinkProps>(function Link(
  { href, onClick, locale: localeProp, prefetch: prefetchProp, ...rest },
  ref
) {
  const activeLocale = useLocale();
  const pathOf = (value: unknown) =>
    typeof value === "string"
      ? value.split(/[?#]/)[0]
      : typeof value === "object" && value && "pathname" in value
        ? String((value as { pathname?: unknown }).pathname ?? "")
        : "";
  const prefetchFor = (target: unknown) =>
    prefetchProp ?? (isClerkClientShellPath(pathOf(target)) ? false : undefined);
  if (typeof href !== "string") {
    return (
      <BaseLink
        ref={ref}
        href={href}
        locale={localeProp}
        onClick={onClick}
        prefetch={prefetchFor(href)}
        {...rest}
      />
    );
  }
  const resolved = canonicalInternalHref(href, (localeProp as string | undefined) ?? activeLocale);
  if (!resolved) {
    return (
      <BaseLink
        ref={ref}
        href={href}
        locale={localeProp}
        onClick={onClick}
        prefetch={prefetchFor(href)}
        {...rest}
      />
    );
  }
  const { from } = resolved;
  const handleClick =
    from === undefined
      ? onClick
      : (event: MouseEvent<HTMLAnchorElement>) => {
          const query = new URLSearchParams(href.split("?")[1]?.split("#")[0] ?? "");
          rememberQuoteIntent({
            ...readQuoteIntent(),
            from,
            intent: query.get("intent") ?? undefined,
            vehicle: query.get("vehicle") ?? undefined,
          });
          onClick?.(event);
        };
  return (
    <BaseLink
      ref={ref}
      href={resolved.href}
      locale={resolved.locale as typeof localeProp}
      onClick={handleClick}
      prefetch={prefetchFor(resolved.href)}
      {...rest}
    />
  );
});
