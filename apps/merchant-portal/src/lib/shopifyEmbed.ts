/**
 * Embedded Shopify app page (/shopify-app), served as plain HTML by a route handler so
 * the shopify-api-key meta and the synchronous App Bridge script are the very first
 * things in <head> (App Bridge refuses to mint session tokens otherwise). No Next
 * chunks, no Clerk: the App Bridge session token is the identity.
 */

import {
  shopifyAdminShippingUrl,
  shopifyInstallError,
  shopifyRatesProblem,
} from "./shopifyStatus.ts";

export const APP_BRIDGE_SRC = "https://cdn.shopify.com/shopifycloud/app-bridge.js";

/** Public client id (not the secret), read at request time from the container env. */
export function shopifyApiKey(): string {
  return (process.env.SHOPIFY_API_KEY ?? "").trim();
}

const esc = (v: string) =>
  v.replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!
  );

/** JSON safe inside <script>. */
const js = (v: unknown) => JSON.stringify(v).replace(/</g, "\\u003c");

const ERROR_CODES = [
  "shop_already_connected",
  "shopify_email_already_bound",
  "session_token_missing",
  "session_token_invalid",
  "shopify_oauth_not_configured",
  "install_failed",
];
const RATE_CODES = [
  "carrier_plan_unsupported",
  "carrier_scope_missing",
  "carrier_no_token",
  "token_reauth_required",
  "carrier_register_failed",
];

export function embeddedAppHtml(opts: {
  apiKey: string;
  apiUrl: string;
  portalUrl: string;
}): string {
  const errors = Object.fromEntries(ERROR_CODES.map((c) => [c, shopifyInstallError(c)]));
  errors._default = shopifyInstallError("unknown_code");
  const rates = Object.fromEntries(RATE_CODES.map((c) => [c, shopifyRatesProblem(c)]));
  const shipping = shopifyAdminShippingUrl("__SHOP__");
  return `<!doctype html>
<html lang="en"><head>
<meta name="shopify-api-key" content="${esc(opts.apiKey)}" />
<script src="${APP_BRIDGE_SRC}"></script>
<meta charset="utf-8" /><meta name="viewport" content="width=device-width,initial-scale=1" />
<title>PorterChain Delivery</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:#0f2742;margin:0}
main{max-width:36rem;margin:0 auto;padding:2rem 1rem}h1{font-size:1.5rem;margin:0 0 1rem}
.box{border-radius:.75rem;padding:.75rem 1rem;margin:0 0 1rem;font-size:.9rem;line-height:1.45}
.ok{background:#ecfdf5;border:1px solid #a7f3d0}.warn{background:#fffbeb;border:1px solid #fde68a}
.note{border:1px solid #e2e8f0}.btn{display:inline-block;padding:.65rem 1.1rem;border-radius:.75rem;
background:#0f2742;color:#fff;text-decoration:none;font-weight:600;font-size:.9rem}
.btn.alt{background:#fff;color:#0f2742;border:1px solid #a7f3d0}small{color:#64748b}ol{padding-left:1.2rem}
</style></head>
<body><main><h1>PorterChain Delivery</h1><div id="app"><p>Connecting your store…</p></div></main>
<script>
(function(){
var API=${js(opts.apiUrl)},PORTAL=${js(opts.portalUrl)},ERR=${js(errors)},RATES=${js(rates)},SHIP=${js(shipping)};
var app=document.getElementById("app");
function e(t){return String(t==null?"":t).replace(/[&<>"']/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]})}
function fail(code){app.innerHTML='<p class="box warn" role="alert">'+e(ERR[code]||ERR._default)+"</p>"}
function bridge(n){return new Promise(function(ok,no){(function t(i){var s=window.shopify;
if(s&&s.idToken)return ok(s);if(i>50)return no(new Error("session_token_missing"));setTimeout(function(){t(i+1)},100)})(0)})}
function render(s){var h="",p=RATES[s.rates];
if(s.rates!=="ready"){h+='<p class="box warn">'+e(p||RATES.carrier_register_failed)+"</p>"}
else{h+='<div class="box ok"><p>PorterChain is registered as a carrier on '+e(s.shop_domain)+'. Shopify does not switch new carriers on by itself, so add PorterChain to your Canada shipping zone:</p><ol><li>Open Settings → Shipping and delivery.</li><li>Open the shipping profile and the zone that includes Canada (Ontario).</li><li>Click Add rate, then choose “Use carrier or app to calculate rates”.</li><li>Pick PorterChain, select its services, click Done, then Save.</li></ol><a class="btn alt" target="_top" href="'+e(SHIP.replace("__SHOP__",s.shop_domain.replace(/\\.myshopify\\.com$/,"")))+'">Open Shipping and delivery</a></div>'}
h+='<p class="box note">PorterChain delivers in Toronto and up to 150 km around it. Orders shipping farther (other regions, provinces or countries) simply don’t see a PorterChain rate at checkout; your other rates keep working.</p>';
if(s.linked){h+="<p>Linked to <strong>"+e(s.company_name)+'</strong>. Pickups, orders and invoices live in the PorterChain portal.</p><p><a class="btn" target="_blank" rel="noreferrer" href="'+e(PORTAL)+'/shopify">Open PorterChain portal</a></p>'}
else{h+='<p>Last step: link this store to your PorterChain account so its orders, pickup address and invoices are yours. New to PorterChain? You can create an account on the next screen.</p><p><a class="btn" target="_blank" rel="noreferrer" href="'+e(PORTAL)+"/shopify?link="+encodeURIComponent(s.link_token||"")+'">Link to my PorterChain account</a></p>'}
h+="<p><small>The app is free. Deliveries are invoiced monthly and paid by Interac e-Transfer.</small></p>";app.innerHTML=h}
bridge().then(function(b){return b.idToken()}).then(function(tok){
return fetch(API+"/v1/integrations/shopify/session",{method:"POST",headers:{Authorization:"Bearer "+tok}})})
.then(function(r){return r.json().catch(function(){return{}}).then(function(b){if(!r.ok)throw new Error(b.code||b.detail||"install_failed");return b})})
.then(render).catch(function(x){fail(x&&x.message||"install_failed")});
})();
</script></body></html>`;
}
