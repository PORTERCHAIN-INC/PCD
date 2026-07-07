import { getAuthorForPost } from "@/lib/blog";
import { cn } from "@/lib/utils";

interface AuthorCardProps {
  authorId: string;
  writtenByLabel: string;
  variant?: "default" | "compact";
  className?: string;
}

export default function AuthorCard({
  authorId,
  writtenByLabel,
  variant = "default",
  className,
}: AuthorCardProps) {
  const author = getAuthorForPost(authorId);
  const initials = author.name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2);

  return (
    <div
      className={cn(
        "flex items-start gap-4",
        variant === "default" && "p-5 rounded-2xl border border-primary/[0.06] bg-gray-bg",
        className
      )}
    >
      <div
        className={cn(
          "rounded-full bg-secondary text-white font-semibold flex items-center justify-center shrink-0",
          variant === "compact" ? "w-10 h-10 text-sm" : "w-12 h-12 text-base"
        )}
        aria-hidden
      >
        {initials}
      </div>
      <div>
        <p className="text-xs font-medium uppercase tracking-wider text-muted">{writtenByLabel}</p>
        <p className="mt-0.5 font-semibold text-primary">{author.name}</p>
        <p className="text-sm text-secondary">{author.role}</p>
        {variant === "default" && (
          <p className="mt-2 text-sm text-muted leading-relaxed">{author.bio}</p>
        )}
      </div>
    </div>
  );
}
