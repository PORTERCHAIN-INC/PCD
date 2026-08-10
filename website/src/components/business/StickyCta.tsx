"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useTranslations } from "next-intl";
import { ArrowRight } from "lucide-react";
import { Link } from "@/i18n/navigation";
import { quoteSignUpPath } from "@/data/portal-links";

export default function StickyCta() {
  const t = useTranslations("businessPage.stickyCta");
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > 600);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ y: 100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 100, opacity: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
          className="pointer-events-none fixed bottom-0 left-0 right-0 z-40 px-4 pt-2 safe-bottom"
        >
          <div className="pointer-events-auto mx-auto max-w-lg">
            <div className="biz-glass-dark biz-shadow-lg flex items-center justify-between gap-3 rounded-2xl px-4 py-3 sm:gap-4 sm:px-5 sm:py-3.5">
              <p className="hidden min-w-0 text-sm font-medium text-white sm:block">
                {t("message")}
              </p>
              <Link
                href={quoteSignUpPath({ from: "business-sticky" })}
                className="flex min-h-[2.75rem] w-full items-center justify-center gap-2 whitespace-nowrap rounded-xl bg-[#2563eb] px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#1d4ed8] sm:ml-auto sm:w-auto"
              >
                {t("button")}
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
