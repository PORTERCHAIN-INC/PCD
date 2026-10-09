/**
 * Merchant logos for the homepage trust strip.
 * Add a merchant ONLY with their written permission to show the logo (file in /public/images/logos).
 * While this list is empty the logo row is not rendered — no placeholder or stock logos.
 */
export type MerchantLogo = {
  name: string;
  src: string;
  width: number;
  height: number;
};

export const MERCHANT_LOGOS: MerchantLogo[] = [];
