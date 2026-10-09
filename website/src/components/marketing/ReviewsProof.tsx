import { getTranslations } from "next-intl/server";
import Container from "@/components/ui/Container";
import { publishableReviews } from "@/data/customer-reviews";
import { publicEnv } from "@/lib/env";
import {
  getGoogleBusinessReviewUrl,
  isGoogleBusinessReviewConfigured,
} from "@/lib/google-business";

type Props = { locale: string };

function googleRating(): { value: number; count: number } | null {
  const value = Number.parseFloat(publicEnv.googleRatingValue);
  const count = Number.parseInt(publicEnv.googleRatingCount, 10);
  if (!Number.isFinite(value) || value <= 0 || value > 5 || !Number.isFinite(count) || count <= 0) {
    return null;
  }
  return { value, count };
}

/**
 * Social proof: real testimonials + Google rating/review link. Renders NOTHING until real
 * data is configured (customer-reviews.ts entries with verified=true, or the Google env
 * settings), so no placeholder or invented review can reach production.
 */
export default async function ReviewsProof({ locale }: Props) {
  const reviews = publishableReviews(locale);
  const rating = googleRating();
  const reviewUrl = isGoogleBusinessReviewConfigured() ? getGoogleBusinessReviewUrl() : "";
  if (reviews.length === 0 && !rating) return null;

  const t = await getTranslations({ locale, namespace: "marketing.reviewsProof" });

  return (
    <section aria-labelledby="reviews-proof-title" className="bg-white py-14 sm:py-16">
      <Container>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <h2
            id="reviews-proof-title"
            className="text-2xl font-bold tracking-tight text-primary sm:text-3xl"
          >
            {t("title")}
          </h2>
          {rating ? (
            <p className="text-sm text-primary">
              <span className="font-semibold">
                {t("googleRating", { value: rating.value.toFixed(1) })}
              </span>{" "}
              <span className="text-primary/75">{t("reviewCount", { count: rating.count })}</span>
            </p>
          ) : null}
        </div>
        {reviews.length ? (
          <ul className="mt-8 grid gap-5 md:grid-cols-3">
            {reviews.map((r) => (
              <li key={`${r.author}-${r.date ?? ""}`}>
                <figure className="h-full rounded-2xl border border-primary/10 bg-gray-bg p-6">
                  {r.rating ? (
                    <p
                      className="text-sm font-semibold text-primary"
                      aria-label={t("stars", { value: r.rating })}
                    >
                      {"★".repeat(Math.round(r.rating))}
                    </p>
                  ) : null}
                  <blockquote className="mt-2 text-sm leading-relaxed text-primary/90">
                    “{r.quote}”
                  </blockquote>
                  <figcaption className="mt-4 text-sm">
                    <span className="font-semibold text-primary">{r.author}</span>
                    {r.role || r.company ? (
                      <span className="block text-primary/75">
                        {[r.role, r.company].filter(Boolean).join(", ")}
                      </span>
                    ) : null}
                  </figcaption>
                </figure>
              </li>
            ))}
          </ul>
        ) : null}
        {reviewUrl ? (
          <p className="mt-6 text-sm">
            <a
              href={reviewUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="font-semibold text-secondary underline-offset-2 hover:underline"
            >
              {t("googleLink")}
            </a>
          </p>
        ) : null}
      </Container>
    </section>
  );
}
