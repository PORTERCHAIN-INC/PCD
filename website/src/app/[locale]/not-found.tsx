import { Link } from "@/i18n/navigation";
import SiteShell from "@/components/layout/SiteShell";
import Container from "@/components/ui/Container";

export default function NotFound() {
  return (
    <SiteShell>
      <section className="site-section bg-white">
        <Container className="max-w-xl text-center">
          <h1 className="text-4xl font-bold text-primary">Page not found</h1>
          <p className="mt-4 text-muted">
            The page you requested is not available. Return to the homepage or request
            transportation capacity for your business.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-4">
            <Link href="/" className="btn-primary">
              Home
            </Link>
            <Link href="/contact?intent=quote" className="btn-secondary">
              Get a quote
            </Link>
          </div>
        </Container>
      </section>
    </SiteShell>
  );
}
