import type { Metadata } from "next";
import "./proof.css";

const pageUrl = "https://porterchain.com/proof-of-resolution";

export const metadata: Metadata = {
  title: "Proof of resolution | Porterchain Shopify review",
  description:
    "Shopify requirement 4.5.5. The reviewer screenshot is the model. The same merchant sign-in now accepts the test account and opens the Shopify feature set.",
  alternates: { canonical: pageUrl },
  robots: { index: false, follow: false },
};

const reported =
  "4.5.5. Include functional test credentials. If your app requires login credentials, then the credentials you provide for review must be valid, and grant full access to the app's complete feature set. Double-check all credentials before submission to avoid issues during review. During post-reinstall testing, we opened the merchant portal and attempted to sign in with the supplied identity. The app fails to grant access to its authenticated feature set and displays “Couldn't find your account,” with no usable test credentials available.";

const checks: { requirement: string; resolved: string }[] = [
  {
    requirement: "Include functional test credentials.",
    resolved: "Email and password are listed on this page and open the live merchant portal.",
  },
  {
    requirement: "Credentials must be valid.",
    resolved:
      "shopify-review@porterchain.com is a real account. The sign-in screen accepts it and asks for the password.",
  },
  {
    requirement: "Grant full access to the app's complete feature set.",
    resolved:
      "The account is the owner of PorterChain Shopify Review. Home, Operations, Finance, Account, and Shopify are available. A Toronto pickup is already saved.",
  },
  {
    requirement: "Double-check all credentials before submission.",
    resolved:
      "Signed in on 4 October 2026 at merchant.porterchain.com with the password on this page. The portal opened. The Shopify page loaded.",
  },
  {
    requirement:
      "During post-reinstall testing, open the merchant portal and sign in with the supplied identity.",
    resolved:
      "That is the same Business sign-in screen in the reviewer visual. Use the credentials below after reinstall.",
  },
  {
    requirement: "The app must not display “Couldn't find your account.”",
    resolved:
      "That message is gone for this email. The resolved screen shows the password step for shopify-review@porterchain.com.",
  },
  {
    requirement: "Usable test credentials must be available.",
    resolved: "The credentials below are the ones to enter in the App Store listing and on retest.",
  },
];

export default function ProofOfResolutionPage() {
  return (
    <main className="proof">
      <div className="proof__wrap">
        <p className="proof__kicker">Shopify App Store review</p>
        <h1>Proof of resolution</h1>
        <p className="proof__lead">
          Requirement 4.5.5, functional test credentials. This page uses the screenshot from review
          as the model, then shows that same merchant sign-in after the fix.
        </p>

        <section>
          <h2>What the review reported</h2>
          <blockquote className="proof__quote">
            <p>{reported}</p>
          </blockquote>
        </section>

        <section>
          <h2>What Shopify asked us to show</h2>
          <ul className="proof__asks">
            <li>Use the visual provided by the reviewer as a model for how to show the fix.</li>
            <li>Show the resolved state.</li>
          </ul>
        </section>

        <section>
          <h2>Same screen</h2>
          <p>
            Both images are the PorterChain merchant portal, Business sign-in, with{" "}
            <code>shopify-review@porterchain.com</code>. The first is the screenshot from review.
            The second is that screen on 4 October 2026.
          </p>
          <div className="proof__pair">
            <figure>
              <img
                src="/proof-of-resolution/reviewer-sign-in.png"
                alt="Reviewer screenshot of Business sign-in. The email shopify-review@porterchain.com shows the error Couldn't find your account."
              />
              <figcaption>
                <span className="proof__tag proof__tag--reported">Reviewer visual</span>
                <p>
                  Post-reinstall sign-in. The supplied identity shows “Couldn&apos;t find your
                  account.” The password never gets checked, and the authenticated Shopify features
                  stay closed.
                </p>
              </figcaption>
            </figure>
            <figure>
              <img
                src="/proof-of-resolution/resolved-sign-in.png"
                alt="Resolved Business sign-in. shopify-review@porterchain.com is accepted and the screen asks for the password, with no account error."
              />
              <figcaption>
                <span className="proof__tag proof__tag--resolved">Resolved state</span>
                <p>
                  Same portal, same email. The account is found. The next step is the password. This
                  review account continues with the password alone.
                </p>
              </figcaption>
            </figure>
          </div>
        </section>

        <section>
          <h2>Authenticated feature set</h2>
          <p>
            After the password, the session is PorterChain Shopify Review. This is the screen the
            review could not reach.
          </p>
          <figure>
            <img
              src="/proof-of-resolution/resolved-shopify.png"
              alt="Signed-in PorterChain for Shopify page for PorterChain Shopify Review, with Home, Operations, Finance, Account, and Shopify in the menu, a Toronto pickup, and Connect."
            />
            <figcaption>
              <span className="proof__tag proof__tag--resolved">Resolved state</span>
              <p>
                Owner session. The menu includes Home, Operations, Finance, Account, and Shopify.
                Pickup is 100 King Street West, Toronto. Enter the review store domain and Connect
                is ready. Connect stays quiet until a store domain is typed.
              </p>
            </figcaption>
          </figure>
        </section>

        <section>
          <h2>4.5.5, line by line</h2>
          <div className="proof__scroll">
            <table className="proof__table">
              <thead>
                <tr>
                  <th>What Shopify required</th>
                  <th>Resolved state</th>
                </tr>
              </thead>
              <tbody>
                {checks.map((row) => (
                  <tr key={row.requirement}>
                    <td>{row.requirement}</td>
                    <td>{row.resolved}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <h2>Credentials for retest</h2>
          <dl className="proof__creds">
            <div>
              <dt>Sign-in URL</dt>
              <dd>
                <a href="https://merchant.porterchain.com/sign-in">
                  https://merchant.porterchain.com/sign-in
                </a>
              </dd>
            </div>
            <div>
              <dt>Email</dt>
              <dd>
                <code>shopify-review@porterchain.com</code>
              </dd>
            </div>
            <div>
              <dt>Password</dt>
              <dd>
                <code>Porterchain-Shopify-Review-2026</code>
              </dd>
            </div>
          </dl>
          <p className="proof__note">
            Put these in the App Store listing test-credentials fields before resubmitting. The
            password previously on the listing was never attached to an account.
          </p>
        </section>

        <section>
          <h2>Retest the way the reviewer did</h2>
          <ol>
            <li>Reinstall PorterChain on the review store.</li>
            <li>Open the merchant portal when the app sends you there.</li>
            <li>Sign in with the email and password above.</li>
            <li>Confirm the company name PorterChain Shopify Review. There is no account error.</li>
            <li>
              Open Shopify. Confirm the Toronto pickup, enter the review store, and choose Connect.
            </li>
          </ol>
        </section>
      </div>
    </main>
  );
}
