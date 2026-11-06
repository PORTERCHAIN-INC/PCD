# Keycloak SMTP → ZeptoMail HTTPS (DigitalOcean blocks outbound SMTP).
FROM python:3.12-slim-bookworm
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY relay.py .
ENV RELAY_BIND=0.0.0.0 RELAY_PORT=1025 \
    ZEPTOMAIL_API_URL=https://api.zeptomail.ca/v1.1/email \
    MAIL_FROM_ADDRESS=no-reply@porterchain.com \
    MAIL_FROM_NAME=Porterchain
EXPOSE 1025
USER nobody
CMD ["python", "-u", "relay.py"]
