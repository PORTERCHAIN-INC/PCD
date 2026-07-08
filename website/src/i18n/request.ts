import { getRequestConfig } from "next-intl/server";
import { hasLocale } from "next-intl";
import { routing } from "./routing";

export default getRequestConfig(async ({ requestLocale }) => {
  const requested = await requestLocale;
  const locale = hasLocale(routing.locales, requested) ? requested : routing.defaultLocale;

  const baseMessages = (await import(`../../messages/${locale}.json`)).default;
  const businessMessages = (await import(`../../messages/business-${locale}.json`)).default;
  const corporateMessages = (await import(`../../messages/corporate-${locale}.json`)).default;
  const blogMessages = (await import(`../../messages/blog-${locale}.json`)).default;
  const siteFooterMessages = (await import(`../../messages/site-footer-${locale}.json`)).default;
  const legalMessages = (await import(`../../messages/legal-${locale}.json`)).default;
  const vehiclePartnerMessages = (await import(`../../messages/vehicle-partner-${locale}.json`))
    .default;

  return {
    locale,
    messages: {
      ...baseMessages,
      businessPage: businessMessages,
      corporate: corporateMessages,
      blog: blogMessages,
      siteFooter: siteFooterMessages,
      legal: legalMessages,
      vehiclePartner: vehiclePartnerMessages,
    },
  };
});
