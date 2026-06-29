"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MapPin, Clock, Briefcase, ChevronDown, ArrowRight } from "lucide-react";
import Container from "@/components/ui/Container";
import SectionHeader from "@/components/ui/SectionHeader";
import { cn } from "@/lib/utils";
import { careerDepartments, CAREERS_APPLY_EMAIL, type CareerDepartment } from "@/data/careers";
import type { PositionData } from "@/lib/careers-content";

interface OpenPositionsSectionProps {
  label: string;
  title: string;
  subtitle: string;
  allLabel: string;
  departmentLabels: Record<CareerDepartment, string>;
  positions: PositionData[];
}

export default function OpenPositionsSection({
  label,
  title,
  subtitle,
  allLabel,
  departmentLabels,
  positions,
}: OpenPositionsSectionProps) {
  const [activeDept, setActiveDept] = useState<CareerDepartment | "all">("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const filtered =
    activeDept === "all"
      ? positions
      : positions.filter((p) => p.department === activeDept);

  const deptCounts = careerDepartments.reduce(
    (acc, dept) => {
      acc[dept] = positions.filter((p) => p.department === dept).length;
      return acc;
    },
    {} as Record<CareerDepartment, number>
  );

  return (
    <section id="positions" className="site-section bg-gray-bg scroll-mt-nav">
      <Container>
        <SectionHeader label={label} title={title} subtitle={subtitle} />

        <div className="flex flex-wrap gap-2 mb-10">
          <FilterChip
            active={activeDept === "all"}
            onClick={() => setActiveDept("all")}
            label={allLabel}
            count={positions.length}
          />
          {careerDepartments.map((dept) => (
            <FilterChip
              key={dept}
              active={activeDept === dept}
              onClick={() => setActiveDept(dept)}
              label={departmentLabels[dept]}
              count={deptCounts[dept]}
            />
          ))}
        </div>

        <div className="space-y-3">
          <AnimatePresence mode="popLayout">
            {filtered.map((position) => {
              const isOpen = expandedId === position.id;
              return (
                <motion.article
                  key={position.id}
                  layout
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.2 }}
                  className="card-surface overflow-hidden"
                >
                  <button
                    type="button"
                    onClick={() => setExpandedId(isOpen ? null : position.id)}
                    className="w-full flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 sm:p-6 text-left cursor-pointer hover:bg-white/80 transition-colors"
                    aria-expanded={isOpen}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2 mb-2">
                        <span className="text-[10px] font-semibold uppercase tracking-wider text-secondary px-2 py-0.5 rounded-full bg-secondary/10">
                          {departmentLabels[position.department]}
                        </span>
                      </div>
                      <h3 className="text-lg font-semibold text-primary tracking-tight">
                        {position.title}
                      </h3>
                      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted">
                        <span className="inline-flex items-center gap-1.5">
                          <MapPin className="w-3.5 h-3.5 text-secondary/70" aria-hidden />
                          {position.location}
                        </span>
                        <span className="inline-flex items-center gap-1.5">
                          <Briefcase className="w-3.5 h-3.5 text-secondary/70" aria-hidden />
                          {position.employmentType}
                        </span>
                        <span className="inline-flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5 text-secondary/70" aria-hidden />
                          {position.experience}
                        </span>
                      </div>
                    </div>
                    <motion.span
                      animate={{ rotate: isOpen ? 180 : 0 }}
                      className="shrink-0 self-start sm:self-center"
                    >
                      <ChevronDown className="w-5 h-5 text-secondary" />
                    </motion.span>
                  </button>

                  <AnimatePresence initial={false}>
                    {isOpen && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.25 }}
                      >
                        <div className="px-5 sm:px-6 pb-6 pt-0 border-t border-primary/[0.04]">
                          <p className="text-sm text-muted leading-relaxed max-w-3xl pt-4">
                            {position.description}
                          </p>
                          <a
                            href={`mailto:${CAREERS_APPLY_EMAIL}?subject=Application: ${encodeURIComponent(position.title)}`}
                            className="mt-5 inline-flex items-center gap-2 px-6 py-2.5 rounded-full bg-secondary text-white text-sm font-semibold hover:bg-[#1d4ed8] transition-colors shadow-md shadow-secondary/20"
                          >
                            {position.applyLabel}
                            <ArrowRight className="w-4 h-4" />
                          </a>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.article>
              );
            })}
          </AnimatePresence>
        </div>
      </Container>
    </section>
  );
}

function FilterChip({
  active,
  onClick,
  label,
  count,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  count: number;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all cursor-pointer min-h-[2.5rem]",
        active
          ? "bg-secondary text-white shadow-md shadow-secondary/25"
          : "bg-white text-primary/75 border border-primary/[0.08] hover:border-secondary/30 hover:text-primary"
      )}
    >
      {label}
      <span
        className={cn(
          "text-xs px-1.5 py-0.5 rounded-full",
          active ? "bg-white/20" : "bg-gray-bg text-muted"
        )}
      >
        {count}
      </span>
    </button>
  );
}
