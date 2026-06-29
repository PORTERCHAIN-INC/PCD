"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useTranslations } from "next-intl";
import { ArrowRight } from "lucide-react";

export default function StickyCta() {
  const t = useTranslations("businessPage.stickyCta");
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > 600);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const scrollToInquiry = () => {
    document.getElementById("inquiry")?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ y: 100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 100, opacity: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
          className="fixed bottom-0 left-0 right-0 z-40 px-4 pt-2 safe-bottom pointer-events-none"
        >
          <div className="max-w-lg mx-auto pointer-events-auto">
            <div className="biz-glass-dark rounded-2xl px-4 sm:px-5 py-3 sm:py-3.5 flex items-center justify-between gap-3 sm:gap-4 biz-shadow-lg">
              <p className="text-white text-sm font-medium hidden sm:block min-w-0">
                {t("message")}
              </p>
              <button
                onClick={scrollToInquiry}
                className="flex items-center justify-center gap-2 w-full sm:w-auto min-h-[2.75rem] px-5 py-2.5 rounded-xl bg-[#ff7a00] text-white text-sm font-semibold hover:bg-[#e66e00] transition-colors whitespace-nowrap sm:ml-auto"
              >
                {t("button")}
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
