import Route from "@ember/routing/route";
import { inject as service } from "@ember/service";
import pathToRoute from "@fleetbase/ember-core/utils/path-to-route";
import removeBootLoader from "../../utils/remove-boot-loader";

/**
 * PorterChain SSO entry — admin opens /porterchain/sso?token=<jwt>.
 * Exchanges JWT for Fleetbase Sanctum session; no login form.
 * Canonical copy: packages/porterchain-bridge/console/ (synced into apps/fleetbase/console).
 */
export default class PorterchainSsoRoute extends Route {
  @service session;
  @service router;
  @service fetch;
  @service notifications;
  @service urlSearchParams;

  beforeModel() {
    this.session.prohibitAuthentication("console");
  }

  async model() {
    const ssoToken = this.urlSearchParams.get("token");
    const shift = this.urlSearchParams.get("shift");

    if (!ssoToken) {
      this.notifications.warning("Missing sign-in token. Please sign in again from Porterchain.");
      return this.router.transitionTo("auth.login");
    }

    if (shift) {
      this.session.setRedirect(pathToRoute(shift));
    }

    try {
      const response = await this.fetch.post("porterchain/sso/exchange", { token: ssoToken });
      const token = response?.token;

      if (!token) {
        throw new Error("SSO exchange returned no session token.");
      }

      await this.session.manuallyAuthenticate(token);
      removeBootLoader();
      return this.router.transitionTo("console");
    } catch (error) {
      const apiError = error?.errors?.[0]?.error || error?.payload?.error || error?.message || "";

      if (typeof apiError === "string" && apiError.includes("sso_token_expired")) {
        this.notifications.warning(
          "This sign-in link has expired — open Fleetbase again from the PorterChain admin portal."
        );
      } else {
        this.notifications.warning(
          "Could not sign you in via PorterChain — please reopen Fleetbase from the admin portal."
        );
      }

      return this.router.transitionTo("auth.login");
    }
  }
}
