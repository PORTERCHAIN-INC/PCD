/**
 * Embedded Shopify app page (/shopify-app), served as plain HTML by a route handler so
 * the shopify-api-key meta and the synchronous App Bridge script are the very first
 * things in <head> (App Bridge refuses to mint session tokens otherwise). No Next
 * chunks, no Keycloak: the App Bridge session token is the identity.
 */

import { shopifyInstallError, shopifyRatesProblem } from "./shopifyStatus.ts";

/** App Bridge admin link: navigates the same admin tab (no new tab, no store handle). */
export const ADMIN_SHIPPING = "shopify://admin/settings/shipping";

export const APP_BRIDGE_SRC = "https://cdn.shopify.com/shopifycloud/app-bridge.js";

/** Public client id (not the secret), read at request time from the container env. */
export function shopifyApiKey(requested?: string | null): string {
  // Custom-distribution apps open /shopify-app?app=<client_id>; only listed ids are honoured.
  const extra = (process.env.SHOPIFY_EXTRA_API_KEYS ?? "").split(",").map((k) => k.trim());
  if (requested && extra.includes(requested)) return requested;
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
  /** 4-click onboarding (confirm pickup → Go live). Off: page is byte-identical to the reviewed one. */
  fourClick?: boolean;
  /**
   * Reviewer-proof onboarding (74 §2, G20): the install auto-provisions the organisation,
   * so an unlinked store is shown as ready inside the iframe. No new-tab link step, no
   * Keycloak/Keycloak page, no OTP or CAPTCHA. Off: legacy "Link to my PorterChain account".
   */
  autoProvision?: boolean;
}): string {
  const errors = Object.fromEntries(ERROR_CODES.map((c) => [c, shopifyInstallError(c)]));
  errors._default = shopifyInstallError("unknown_code");
  const rates = Object.fromEntries(RATE_CODES.map((c) => [c, shopifyRatesProblem(c)]));

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
<body><main><h1>PorterChain Delivery</h1><div id="app"><p>Connecting your store…</p></div></main>${opts.fourClick ? fourClickJs(opts.apiUrl) : ""}
<script>
(function(){
var AUTO=${opts.autoProvision ? "true" : "false"},API=${js(opts.apiUrl)},PORTAL=${js(opts.portalUrl)},ERR=${js(errors)},RATES=${js(rates)},SHIP=${js(ADMIN_SHIPPING)};
var app=document.getElementById("app");
function e(t){return String(t==null?"":t).replace(/[&<>"']/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]})}
function openShipping(){try{open(SHIP,"_top")}catch(x){}return false}
window.openShipping=openShipping;
function fail(code){app.innerHTML='<p class="box warn" role="alert">'+e(ERR[code]||ERR._default)+"</p>"}
function bridge(n){return new Promise(function(ok,no){(function t(i){var s=window.shopify;
if(s&&s.idToken)return ok(s);if(i>50)return no(new Error("session_token_missing"));setTimeout(function(){t(i+1)},100)})(0)})}
function rp(a){window.shopify.idToken().then(function(t){return fetch(API+"/v1/integrations/shopify/route-pricing",a?{method:"POST",headers:{Authorization:"Bearer "+t,"Content-Type":"application/json"},body:JSON.stringify({action:a})}:{headers:{Authorization:"Bearer "+t}})}).then(function(r){return r.ok?r.json():null}).then(function(p){var el=document.getElementById("rp");if(!el||!p)return;if(p.opted_in){el.innerHTML=a?'<p class="box ok">Route pricing is on. Checkout rates and bookings use it.</p>':"";return}if(!p.show_banner){el.innerHTML="";return}var m=function(c){return"$"+(c/100).toFixed(2)};var h='<div class="box note"><p><strong>New: route pricing.</strong> '+e(p.summary)+"</p>";if(p.examples.length){h+="<table><caption>Your price today vs route pricing (1 parcel, cargo van, before any tax)</caption><tr><th scope=col>Example</th><th scope=col>Today</th><th scope=col>Route pricing</th></tr>"+p.examples.map(function(x){return"<tr><td>"+e(x.from_fsa)+" → "+e(x.to_fsa)+"</td><td>"+m(x.old_cents)+"</td><td><strong>"+m(x.new_cents)+"</strong></td></tr>"}).join("")+"</table>"}h+='<p><button class="btn" id="rpin">Opt in</button> <button class="btn alt" id="rpno">Not now</button></p></div>';el.innerHTML=h;document.getElementById("rpin").onclick=function(){this.disabled=true;rp("opt_in")};document.getElementById("rpno").onclick=function(){rp("dismiss")}}).catch(function(){})}
var PRICING_NOTE='<div class="box note" id="howprice"><p><strong>How your delivery price is worked out.</strong> Each delivery is CA$6 for a small parcel or CA$9 for a van-size parcel, plus any surcharge shown at checkout (distance, weight or size). Vehicle bookings are charged by the hour. If PorterChain agreed a custom price with you, that price is used instead. Checkout shows a short summary, e.g. “1 stop · 2 boxes · 18 kg”.</p></div>';
function money(n){return"CA$"+Number(n||0).toFixed(0)}
function billingBox(b){if(!b||!b.required)return"";
function capForm(b){var u=b.usage||{};var used=u.capped_amount?'<br><small>Used this period: '+Number(u.balance_used||0).toFixed(2)+" of "+Number(u.capped_amount).toFixed(2)+" "+e(u.currency||"")+".</small>":"";
var o=(b.cap_choices_cad||[]).map(function(c){return'<option value="'+c+'">'+money(c)+" per 30 days</option>"}).join("");
return (used?"<p>"+used.replace("<br>","")+"</p>":"")+(o?'<form id="capf" style="display:flex;flex-wrap:wrap;gap:.5rem;margin-top:.5rem"><label for="capv">Monthly spending limit</label><select id="capv" style="padding:.4rem;border:1px solid #cbd5e1;border-radius:.5rem">'+o+'</select><button class="btn alt" type="submit">Change limit</button></form><p id="capmsg" role="status"></p>':"")}
window.__pcCap=function(){var f=document.getElementById("capf");if(!f)return;f.onsubmit=function(ev){ev.preventDefault();var m=document.getElementById("capmsg");m.textContent="Opening Shopify approval…";
api("/v1/integrations/shopify/billing/cap",{method:"POST",body:JSON.stringify({amount_cad:Number(document.getElementById("capv").value)})}).then(function(r){open(r.confirmation_url,"_top")}).catch(function(x){m.textContent="Could not change the limit: "+x.message+". Try again."})}};
if(b.status==="active")return'<div class="box ok"><p>Plan approved: <strong>'+e(b.plan)+'</strong>. Each completed delivery is charged on your Shopify bill (usage-based, up to '+money(b.capped_amount)+' per 30 days, converted to your Shopify billing currency).'+(b.test?" Test mode: no real charge.":"")+"</p>"+capForm(b)+"</div>";
if(b.status==="cap_reached")return'<div class="box warn" role="alert" id="billing"><p><strong>Booking is paused.</strong> '+e(b.message||"Your monthly limit is used up.")+"</p>"+capForm(b)+"</div>";
var h='<div class="box warn" role="alert" id="billing">';
if(b.status==="declined"||b.status==="cancelled")h+="<p><strong>Booking is blocked.</strong> You declined the PorterChain Delivery plan, so we can’t book deliveries for this store. Approve the plan to start booking.</p>";
else h+="<p><strong>Approve the PorterChain Delivery plan to start booking.</strong> There is no monthly fee. "+e(b.terms)+" Charges appear on your Shopify bill, capped at "+money(b.capped_amount)+" per 30 days.</p>";
if(b.confirmation_url)h+='<p><a class="btn" id="approve" target="_top" href="'+e(b.confirmation_url)+'">Review and approve plan</a></p>';
else h+="<p>We couldn’t open the approval screen. Reload this page to try again.</p>";
return h+"</div>"}
window.__pcBillingBox=billingBox;
var ST={booked:"Booked",not_booked:"Not booked",cancelled:"Cancelled",error:"Needs attention"};
function api(path,opt){return window.shopify.idToken().then(function(t){opt=opt||{};opt.headers={Authorization:"Bearer "+t};if(opt.body)opt.headers["Content-Type"]="application/json";return fetch(API+path,opt)}).then(function(r){return r.json().catch(function(){return{}}).then(function(b){if(!r.ok)throw new Error(typeof b.detail==="string"?b.detail:"Something went wrong. Try again.");return b})})}
function orders(q,msg){var el=document.getElementById("orders");if(!el)return;
api("/v1/integrations/shopify/orders"+(q?"?q="+encodeURIComponent(q):"")).then(function(d){var rows=d.orders||[];
var h='<h2 style="font-size:1.1rem;margin:1.5rem 0 .5rem">Shopify orders</h2><p><small>Every paid order from your store is listed here, even when the buyer chose another shipping rate. Search by order number, e.g. #1001.</small></p>'+
'<form id="osf" role="search" style="display:flex;gap:.5rem;margin:.5rem 0"><label for="osq" class="sr" style="position:absolute;left:-9999px">Search orders</label><input id="osq" value="'+e(q||"")+'" placeholder="#1001 or customer name" style="flex:1;padding:.55rem;border:1px solid #cbd5e1;border-radius:.6rem"/><button class="btn alt" type="submit">Search</button><button class="btn alt" type="button" id="osync">Sync now</button></form>'+(msg?'<p class="box note" role="status">'+e(msg)+"</p>":"");
if(!rows.length)h+='<p class="box note">'+(q?"No order matches “"+e(q)+"”. Try Sync now if you just placed it.":"No orders yet. Place a test order in your store, then press Sync now (new orders also appear by themselves within a minute).")+"</p>";
else{h+='<div style="overflow-x:auto;-webkit-overflow-scrolling:touch" role="region" aria-label="Shopify orders table" tabindex="0"><table style="width:100%;min-width:560px;border-collapse:collapse;font-size:.85rem"><thead><tr><th scope=col align=left>Order</th><th scope=col align=left>Ship to</th><th scope=col align=left>Items</th><th scope=col align=right>Total</th><th scope=col align=left>Status</th><th scope=col><span style="position:absolute;left:-9999px">Action</span></th></tr></thead><tbody>'+rows.map(function(o){
var items=(o.line_items||[]).map(function(i){return(i.quantity||1)+" × "+e(i.title||"item")}).join(", ");
var act=o.porterchain_order_id?"<small>"+e(o.tracking_number||"In PorterChain")+"</small>":(o.can_book?'<button class="btn" data-book="'+e(o.id)+'" style="padding:.35rem .6rem;font-size:.8rem">Book with PorterChain</button>':"");
return'<tr style="border-top:1px solid #e2e8f0;vertical-align:top"><td><strong>'+e(o.order_name||o.shopify_order_id)+"</strong>"+(o.is_test?' <small>(test)</small>':"")+"<br><small>"+e(o.shipping_title||"")+"</small></td><td>"+e(o.customer_name||"")+"<br><small>"+e(o.ship_to||"")+"</small></td><td>"+items+'</td><td align=right>'+(o.total_cents!=null?"$"+(o.total_cents/100).toFixed(2)+" "+e(o.currency||""):"")+"</td><td>"+e(ST[o.status]||o.status)+(o.status!=="booked"&&o.reason?"<br><small>"+e(o.reason)+"</small>":"")+"</td><td>"+act+"</td></tr>"}).join("")+"</tbody></table></div>"}
el.innerHTML=h;
document.getElementById("osf").onsubmit=function(ev){ev.preventDefault();orders(document.getElementById("osq").value.trim())};
document.getElementById("osync").onclick=function(){this.disabled=true;this.textContent="Syncing…";api("/v1/integrations/shopify/orders/sync",{method:"POST"}).then(function(r){orders(q,"Checked Shopify: "+(r.found||0)+" recent order(s), "+(r.new||0)+" new.")}).catch(function(x){orders(q,x.message)})};
Array.prototype.forEach.call(el.querySelectorAll("[data-book]"),function(b){b.onclick=function(){b.disabled=true;b.textContent="Booking…";api("/v1/integrations/shopify/orders/"+encodeURIComponent(b.getAttribute("data-book"))+"/book",{method:"POST"}).then(function(r){orders(q,r.order_id?"Booked. Tracking "+(r.tracking_number||"")+". Status and tracking will show on the Shopify order.":"Not booked. The reason is shown next to the order.")}).catch(function(x){orders(q,x.message)})}})
}).catch(function(x){el.innerHTML='<p class="box warn" role="alert">Orders could not load: '+e(x.message)+' <button class="btn alt" type="button" onclick="location.reload()">Retry</button></p>'})}
function render(s){var h=billingBox(s.billing),p=RATES[s.rates];
if(s.rates!=="ready"){h+='<p class="box warn">'+e(p||RATES.carrier_register_failed)+"</p>"}
else{h+='<div class="box ok"><p>PorterChain is registered as a carrier on '+e(s.shop_domain)+'. Shopify does not switch new carriers on by itself. If checkout already lists PorterChain for Canada you are done; otherwise:</p><p><strong>Newer admin (“Shipping has moved to Markets”):</strong></p><ol><li>Open Settings → Shipping and delivery → Markets, then the Canada market.</li><li>Under shipping rates, click Add rate → “Use carrier or app to calculate rates”.</li><li>Choose PorterChain (via app), select its services, then Save.</li></ol><p><strong>Older admin:</strong> Settings → Shipping and delivery → your shipping profile → the zone with Canada → Add rate → “Use carrier or app to calculate rates” → PorterChain → Done → Save.</p><a class="btn alt" target="_top" href="'+SHIP+'" onclick="return openShipping()">Open Shipping and delivery</a></div>'}
h+='<p class="box note">PorterChain delivers in Toronto and up to 150 km around it. Orders shipping farther (other regions, provinces or countries) simply don’t see a PorterChain rate at checkout; your other rates keep working.</p>';
if(s.linked){h+="<p>Linked to <strong>"+e(s.company_name)+'</strong>. Every Shopify order is listed below (search by order number, e.g. #1001). You can also manage pickups in your PorterChain portal.</p><p><a class="btn" target="_blank" rel="noreferrer" href="'+e(PORTAL)+'/shopify">Open PorterChain portal</a></p>'+PRICING_NOTE}
else if(AUTO){h+='<p class="box ok">Your PorterChain account for <strong>'+e(s.shop_domain)+'</strong> is ready. No sign-up or login is needed: everything runs here in Shopify admin.</p>'+PRICING_NOTE;s.linked=true}
else{h+='<p>Last step: link this store to your PorterChain account so its orders and pickup address are yours. New to PorterChain? You can create an account on the next screen.</p><p><a class="btn" target="_blank" rel="noreferrer" href="'+e(PORTAL)+"/shopify?link="+encodeURIComponent(s.link_token||"")+'">Link to my PorterChain account</a></p>'}
h+=s.billing&&s.billing.required?"<p><small>Billing is through Shopify: no monthly fee, you only pay for completed deliveries.</small></p>":"";if(s.linked)h+='<div id="rp"></div><div id="orders"></div>';app.innerHTML=h;if(window.__pcCap)window.__pcCap();if(s.linked){rp();orders("")}}
bridge().then(function(b){return b.idToken()}).then(function(tok){
return fetch(API+"/v1/integrations/shopify/session",{method:"POST",headers:{Authorization:"Bearer "+tok}})})
.then(function(r){return r.json().catch(function(){return{}}).then(function(b){if(!r.ok)throw new Error(b.code||b.detail||"install_failed");return b})})
.then(${opts.fourClick ? "function(s){return window.__pcOnboard(s,render)}" : "render"}).catch(function(x){fail(x&&x.message||"install_failed")});
})();
</script></body></html>`;
}

/** Steps 3–4 for the flagged flow. Runs before the main script resolves (defines window.__pcOnboard). */
const fourClickJs = (apiUrl: string) => `
<script>
(function(){
window.__pcApi=${js(apiUrl)};var app=document.getElementById("app");
function e(t){return String(t==null?"":t).replace(/[&<>"']/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]})}
function call(path,opt){return window.shopify.idToken().then(function(t){opt=opt||{};opt.headers={Authorization:"Bearer "+t,"Content-Type":"application/json"};
return fetch(window.__pcApi+path,opt)}).then(function(r){return r.json().catch(function(){return{}}).then(function(b){if(!r.ok)throw new Error(b.detail||"install_failed");return b})})}
window.__pcOnboard=function(s,orig){return call("/v1/integrations/shopify/onboarding").then(function(p){
if(p.source==="saved")return orig(s);
app.innerHTML='<p class="box note"><strong>Step 3 of 4.</strong> Confirm where we pick up your orders.</p><label for="pa"><small>Pickup address</small></label><input id="pa" style="width:100%;box-sizing:border-box;padding:.6rem;border:1px solid #cbd5e1;border-radius:.6rem;margin:.3rem 0 1rem" value="'+e(p.address.formatted)+'"/><button class="btn" id="go">Confirm pickup</button>';
document.getElementById("go").onclick=function(){var a=p.address;a.formatted=document.getElementById("pa").value;
if(a.formatted!==p.address.formatted){a.lat=null;a.lng=null}
app.innerHTML='<p class="box note"><strong>Step 4 of 4.</strong> Pickup: '+e(a.formatted)+'</p><button class="btn" id="live">Go live</button>';
document.getElementById("live").onclick=function(){this.disabled=true;this.textContent="Going live…";
call("/v1/integrations/shopify/onboarding/go-live",{method:"POST",body:JSON.stringify({address:a})}).then(function(r){
app.innerHTML=(window.__pcBillingBox?window.__pcBillingBox(s.billing):"")+'<div class="box ok"><p><strong>'+(r.live?"You’re live.":"Almost there.")+'</strong> Pickup saved, rate card '+e(r.rate_card)+'.</p><p>Last step in Shopify:</p><ol>'+r.next_step.steps.map(function(x){return"<li>"+e(x)+"</li>"}).join("")+'</ol><a class="btn" target="_top" href="'+r.next_step.deep_link+'">Open Shipping and delivery</a></div><p><small>Deliveries are charged on your Shopify bill. No separate signup or login.</small></p>'
}).catch(function(x){app.innerHTML='<p class="box warn">'+e(x.message)+'</p>'})}}
}).catch(function(){return orig(s)})};
})();
</script>`;
