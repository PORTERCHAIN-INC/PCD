import type { ComponentProps } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Link } from "@/i18n/navigation";

interface MarkdownContentProps {
  content: string;
}

/**
 * Site-relative links in post bodies ("/solutions/medical") go through the locale-aware Link,
 * which adds the locale prefix and resolves legacy paths — otherwise every such link is a
 * 301 (/solutions/x → /en/solutions/x) that crawlers report as "Page with redirect".
 */
function MarkdownLink(props: ComponentProps<"a"> & { node?: unknown }) {
  const { href, children, ...rest } = props;
  delete rest.node; // react-markdown's AST node must not reach the DOM
  if (href && href.startsWith("/") && !href.startsWith("//")) {
    return (
      <Link href={href} {...rest}>
        {children}
      </Link>
    );
  }
  return (
    <a href={href} {...rest}>
      {children}
    </a>
  );
}

export default function MarkdownContent({ content }: MarkdownContentProps) {
  return (
    <div className="blog-prose max-w-none">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ a: MarkdownLink }}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
