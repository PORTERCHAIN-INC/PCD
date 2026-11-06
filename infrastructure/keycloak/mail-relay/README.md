# Keycloak → ZeptoMail HTTPS mail relay

Keycloak can only send mail over SMTP. DigitalOcean Droplets block outbound SMTP
(ports 25/465/587). This sidecar accepts SMTP from Keycloak on the Docker
`porterchain-prod_edge` network and forwards each message to ZeptoMail’s HTTPS
Send Mail API (`https://api.zeptomail.ca/v1.1/email`), the same path the API
already uses with `MAIL_TRANSPORT=https`.

See `docs/runbooks/KEYCLOAK_MAIL_HTTPS.md` for deploy and test steps.
