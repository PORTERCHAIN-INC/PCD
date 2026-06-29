import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface BlogPaginationProps {
  currentPage: number;
  totalPages: number;
  basePath: string;
  previousLabel: string;
  nextLabel: string;
  pageLabel: string;
}

export default function BlogPagination({
  currentPage,
  totalPages,
  basePath,
  previousLabel,
  nextLabel,
  pageLabel,
}: BlogPaginationProps) {
  if (totalPages <= 1) return null;

  const pageHref = (page: number) => (page === 1 ? basePath : `${basePath}?page=${page}`);

  return (
    <nav
      className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-10 border-t border-primary/[0.06]"
      aria-label="Pagination"
    >
      <p className="text-sm text-muted order-2 sm:order-1">
        {pageLabel}
      </p>
      <div className="flex items-center gap-2 order-1 sm:order-2">
        {currentPage > 1 ? (
          <Link
            href={pageHref(currentPage - 1)}
            className="inline-flex items-center gap-1 px-4 py-2 rounded-full text-sm font-medium border border-primary/10 hover:border-secondary/30 hover:text-secondary transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            {previousLabel}
          </Link>
        ) : (
          <span className="inline-flex items-center gap-1 px-4 py-2 rounded-full text-sm font-medium text-muted/40 border border-primary/[0.04] cursor-not-allowed">
            <ChevronLeft className="w-4 h-4" />
            {previousLabel}
          </span>
        )}
        {currentPage < totalPages ? (
          <Link
            href={pageHref(currentPage + 1)}
            className={cn(
              "inline-flex items-center gap-1 px-4 py-2 rounded-full text-sm font-medium",
              "bg-secondary text-white hover:bg-[#1d4ed8] transition-colors"
            )}
          >
            {nextLabel}
            <ChevronRight className="w-4 h-4" />
          </Link>
        ) : (
          <span className="inline-flex items-center gap-1 px-4 py-2 rounded-full text-sm font-medium text-muted/40 border border-primary/[0.04] cursor-not-allowed">
            {nextLabel}
            <ChevronRight className="w-4 h-4" />
          </span>
        )}
      </div>
    </nav>
  );
}
