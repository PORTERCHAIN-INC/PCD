# Secrets (SOPS + age)

Encrypted files live here as `secrets/{droplet,ubuntu,oracle,ci}.enc.yaml` (doc 37).
Only encrypted files are committed. Plaintext and private keys never are (`.gitignore`).

## One-time setup (Ravi)

1. On each host (droplet, Ubuntu, Oracle) and once for yourself, create a key:
   `mkdir -p ~/.config/sops/age && age-keygen -o ~/.config/sops/age/keys.txt && chmod 600 ~/.config/sops/age/keys.txt`
   It prints `Public key: age1...`. Only that public line goes into `.sops.yaml`.
2. Keep your own `keys.txt` offline (paper or USB). For CI, make one more key and store the
   private part as the GitHub Actions secret `SOPS_AGE_KEY`.
3. Replace the `age1..._PLACEHOLDER` values in `/.sops.yaml` with the public keys.
4. Create a file: `sops secrets/ubuntu.enc.yaml` (opens your editor; saved encrypted).
   Import from an existing dotenv: `sops -e --input-type dotenv --output-type yaml .env > secrets/ubuntu.enc.yaml`.

## Use

- Load into a dotenv file (mode 600): `bash scripts/secrets/sops-load.sh ubuntu /path/to/.env`
- Run a command with the secrets in its env only: `bash scripts/secrets/sops-load.sh ubuntu --exec -- pnpm dev`
- Droplet sync: `SOPS_SECRETS_FILE=secrets/droplet.enc.yaml bash infrastructure/deploy/sync-secrets.sh`
  (Deploy uses the same file: CI decrypts it with the `SOPS_AGE_KEY` GitHub secret.)
