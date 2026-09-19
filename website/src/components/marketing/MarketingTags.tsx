"use client";

import Script from "next/script";
import { marketingPublicEnv } from "@/lib/marketing/config";
import type { ConsentState } from "@/lib/marketing/consent";

type Props = {
  consent: ConsentState;
};

/**
 * Env-gated marketing / experience tags.
 * When GTM is configured, only GTM loads for marketing (avoid double-fire).
 */
export default function MarketingTags({ consent }: Props) {
  const cfg = marketingPublicEnv;
  const nodes: React.ReactNode[] = [];

  if (cfg.gtmId && (consent.analytics || consent.marketing)) {
    nodes.push(
      <Script key="gtm" id="pc-gtm" strategy="afterInteractive">{`
        (function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
        new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
        j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
        'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
        })(window,document,'script','dataLayer','${cfg.gtmId}');
      `}</Script>
    );
  }

  if (!cfg.useGtmForMarketing && consent.marketing) {
    if (cfg.googleAdsId) {
      nodes.push(
        <Script
          key="ads"
          src={`https://www.googletagmanager.com/gtag/js?id=${cfg.googleAdsId}`}
          strategy="afterInteractive"
        />,
        <Script key="ads-cfg" id="pc-google-ads" strategy="afterInteractive">{`
          window.dataLayer = window.dataLayer || [];
          function gtag(){dataLayer.push(arguments);}
          gtag('config', '${cfg.googleAdsId}');
        `}</Script>
      );
    }
    if (cfg.metaPixelId) {
      nodes.push(
        <Script key="meta" id="pc-meta-pixel" strategy="afterInteractive">{`
          !function(f,b,e,v,n,t,s)
          {if(f.fbq)return;n=f.fbq=function(){n.callMethod?
          n.callMethod.apply(n,arguments):n.queue.push(arguments)};
          if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
          n.queue=[];t=b.createElement(e);t.async=!0;
          t.src=v;s=b.getElementsByTagName(e)[0];
          s.parentNode.insertBefore(t,s)}(window,document,'script',
          'https://connect.facebook.net/en_US/fbevents.js');
          fbq('init', '${cfg.metaPixelId}');
          fbq('track', 'PageView');
        `}</Script>
      );
    }
    if (cfg.linkedInPartnerId) {
      nodes.push(
        <Script key="li" id="pc-linkedin" strategy="afterInteractive">{`
          _linkedin_partner_id = "${cfg.linkedInPartnerId}";
          window._linkedin_data_partner_ids = window._linkedin_data_partner_ids || [];
          window._linkedin_data_partner_ids.push(_linkedin_partner_id);
          (function(l){
            if(!l){window.lintrk=function(a,b){window.lintrk.q.push([a,b])};
            window.lintrk.q=[]}
            var s=document.getElementsByTagName("script")[0];
            var b=document.createElement("script");
            b.type="text/javascript";b.async=true;
            b.src="https://snap.licdn.com/li.lms-analytics/insight.min.js";
            s.parentNode.insertBefore(b,s);
          })(window.lintrk);
        `}</Script>
      );
    }
    if (cfg.microsoftUetId) {
      nodes.push(
        <Script key="uet" id="pc-microsoft-uet" strategy="afterInteractive">{`
          (function(w,d,t,r,u){var f,n,i;w[u]=w[u]||[],f=function(){
          var o={ti:"${cfg.microsoftUetId}"};o.q=w[u],w[u]=new UET(o),
          w[u].push("pageLoad")},n=d.createElement(t),n.src=r,n.async=1,
          n.onload=n.onreadystatechange=function(){var s=this.readyState;
          s&&s!=="loaded"&&s!=="complete"||(f(),n.onload=n.onreadystatechange=null)},
          i=d.getElementsByTagName(t)[0],i.parentNode.insertBefore(n,i)
          })(window,document,"script","https://bat.bing.com/bat.js","uetq");
        `}</Script>
      );
    }
    if (cfg.twitterPixelId) {
      nodes.push(
        <Script key="x" id="pc-twitter-pixel" strategy="afterInteractive">{`
          !function(e,t,n,s,u,a){e.twq||(s=e.twq=function(){s.exe?s.exe.apply(s,arguments):
          s.queue.push(arguments);},s.version='1.1',s.queue=[],u=t.createElement(n),
          u.async=!0,u.src='https://static.ads-twitter.com/uwt.js',
          a=t.getElementsByTagName(n)[0],a.parentNode.insertBefore(u,a))}
          (window,document,'script');twq('config','${cfg.twitterPixelId}');
        `}</Script>
      );
    }
  }

  if (consent.experience) {
    if (cfg.experienceTool === "clarity" && cfg.clarityId) {
      nodes.push(
        <Script key="clarity" id="pc-clarity" strategy="afterInteractive">{`
          (function(c,l,a,r,i,t,y){
            c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};
            t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;
            y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
          })(window, document, "clarity", "script", "${cfg.clarityId}");
        `}</Script>
      );
    } else if (cfg.experienceTool === "hotjar" && cfg.hotjarId) {
      nodes.push(
        <Script key="hotjar" id="pc-hotjar" strategy="afterInteractive">{`
          (function(h,o,t,j,a,r){
            h.hj=h.hj||function(){(h.hj.q=h.hj.q||[]).push(arguments)};
            h._hjSettings={hjid:${Number(cfg.hotjarId) || 0},hjsv:6};
            a=o.getElementsByTagName('head')[0];
            r=o.createElement('script');r.async=1;
            r.src=t+h._hjSettings.hjid+j+h._hjSettings.hjsv;
            a.appendChild(r);
          })(window,document,'https://static.hotjar.com/c/hotjar-','.js?sv=');
        `}</Script>
      );
    }
  }

  return <>{nodes}</>;
}
