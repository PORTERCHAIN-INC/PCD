import { cn } from "@/lib/utils";

type AnswerItem = {
  question: string;
  answer: string;
};

type AnswerBlockProps = {
  title?: string;
  items: AnswerItem[];
  className?: string;
  /** Visual tone — homepage uses light; dark for navy sections */
  tone?: "light" | "dark";
  /** stack = single column; grid = 2-col on md+ */
  layout?: "stack" | "grid";
  titleId?: string;
};

/**
 * Concise answer block for AEO / GEO — direct Q&A near top of money pages.
 * FAQ schema is emitted separately only when full FAQ sections exist on page.
 */
export default function AnswerBlock({
  title,
  items,
  className = "",
  tone = "light",
  layout = "stack",
  titleId,
}: AnswerBlockProps) {
  if (items.length === 0) return null;

  const isDark = tone === "dark";

  return (
    <div className={cn(className)} aria-label={title ?? "Quick answers"}>
      {title ? (
        <h2
          id={titleId}
          className={cn("type-h2 text-balance", isDark ? "text-white" : "text-primary")}
        >
          {title}
        </h2>
      ) : null}
      <dl
        className={cn(
          title && "mt-8 sm:mt-10",
          layout === "grid"
            ? "grid gap-x-10 gap-y-8 sm:grid-cols-2 sm:gap-y-10"
            : "space-y-6 sm:space-y-7"
        )}
      >
        {items.map((item, index) => (
          <div
            key={item.question}
            className={cn(
              "border-l-2 pl-4 sm:pl-5",
              isDark ? "border-secondary/60" : "border-secondary"
            )}
          >
            <dt
              className={cn(
                "speakable-faq-q text-base font-semibold tracking-tight sm:text-lg",
                isDark ? "text-white" : "text-primary"
              )}
            >
              <span className="sr-only">{index + 1}. </span>
              {item.question}
            </dt>
            <dd
              className={cn(
                "speakable-faq-a mt-2 text-sm leading-relaxed sm:text-[0.95rem] sm:leading-7",
                isDark ? "text-white/75" : "text-muted"
              )}
            >
              {item.answer}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export type { AnswerItem };
