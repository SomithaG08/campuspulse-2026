/*
 * Deployment configuration.
 *
 * This file is REWRITTEN at deploy time from `terraform output` - see
 * docs/deployment/04-deploy-dashboard.md. It is kept separate from app.js so
 * that deploying to a new API never means editing application code.
 *
 * Nothing here is secret. An API endpoint and a Cognito client id are public
 * identifiers: the client id is designed to be visible in a browser, and the
 * endpoint refuses every request that arrives without a valid token.
 */
window.CAMPUSPULSE_CONFIG = {
  API_URL: "https://wsjs04q4yi.execute-api.eu-west-3.amazonaws.com/",
  apiEndpoint: "https://wsjs04q4yi.execute-api.eu-west-3.amazonaws.com/",
  userPoolId: "eu-west-3_h0OpNKIwF",
  clientId: "4mcnb4t8o9fk0cd3egjvhp66ro",
  region: "eu-west-3",
  POLL_SECONDS: 10,
  // Stop polling after this long without interaction. A dashboard left open
  // in a forgotten tab would otherwise make ~17,000 requests a day against a
  // pay-per-request API, which is exactly the kind of quiet spend the brief
  // warns about.
  IDLE_PAUSE_MINUTES: 15,
};
