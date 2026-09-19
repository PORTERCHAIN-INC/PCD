import Container from "@/components/ui/Container";
import FadeIn from "@/components/corporate/motion/FadeIn";
import SocialLinks from "@/components/layout/SocialLinks";

interface ContactSocialBarProps {
  label: string;
  title: string;
}

export default function ContactSocialBar({ label, title }: ContactSocialBarProps) {
  return (
    <section className="py-14 md:py-16 bg-white border-t border-primary/[0.04]">
      <Container>
        <FadeIn>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-secondary">
                {label}
              </p>
              <h2 className="mt-2 text-xl font-semibold text-primary tracking-tight">{title}</h2>
            </div>
            <SocialLinks variant="contact" />
          </div>
        </FadeIn>
      </Container>
    </section>
  );
}
