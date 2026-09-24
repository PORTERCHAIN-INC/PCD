# GitHub SSH keys (PorterChain)

Local reference for which key does what. **Never commit private keys** — only fingerprints and paths.

Last verified: 2026-09-24 (MacBook Pro). `ssh -T git@github.com` → `Hi porterchain!`  
Repo: `PORTERCHAIN-INC/PCD` (org Free plan — no Team / branch protection).

## Inventory

| Role                  | GitHub title  | Fingerprint                                          | Local private key                                 | Notes                                                                                       |
| --------------------- | ------------- | ---------------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Account push key      | `git push`    | `SHA256:3gW+fcm7Hxjyv6hcakMdgOUYrOxTFHKMTVG/4pyWPZY` | **Not on this Mac** (private key missing locally) | User account SSH key on `porterchain`                                                       |
| MacBook / repo access | `MacBook Key` | `SHA256:lP6CHfL/RmFo5mcpkEDGFZUZVOG1csvbWO3eFcG3vT0` | `~/.ssh/id_porterchain`                           | **User account** SSH key (moved off deploy-key after org transfer). Use for git push/fetch. |
| Default ed25519       | —             | `SHA256:CQCe7ZoXDLDke6TT87+xV0aLrjbDVf38xWxdk53Co9Q` | `~/.ssh/id_ed25519`                               | Comment: `ravi@macbook` — not authorized for this GitHub account                            |
| Droplet SSH           | —             | `SHA256:5IsItWQ8mxH/UXtHAvYUVCKEW4ydtCssK5aMfX/TIqY` | `~/.ssh/pcd_deploy`                               | DigitalOcean droplet only (`Host porterchain-droplet`), not GitHub                          |

## Recommended push from this Mac

Permanent setup is `~/.ssh/config` (already the default `Host github.com` on this machine). Do not use `id_ed25519` for this repo — it is not authorized.

```sshconfig
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_porterchain
    IdentitiesOnly yes
```

Remote: `git@github.com:PORTERCHAIN-INC/PCD.git`. Then `git fetch` / `git push` with no extra `GIT_SSH_COMMAND`.

`gh` stays HTTPS (`gh auth status`). That does not replace the SSH key above.

Optional host alias (not required):

```sshconfig
Host github.com-porterchain
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_porterchain
    IdentitiesOnly yes
```

Then:

```text
git@github.com-porterchain:PORTERCHAIN-INC/PCD.git
```

## Verify fingerprints

```bash
ssh-keygen -lf ~/.ssh/id_porterchain.pub
ssh-keygen -lf ~/.ssh/id_ed25519.pub
ssh-keygen -lf ~/.ssh/pcd_deploy.pub

# Account keys (needs gh auth)
gh api user/keys --jq '.[] | .key' | while read -r k; do echo "$k" | ssh-keygen -lf -; done

# Repo should have no deploy keys for day-to-day git (user key only)
gh api repos/PORTERCHAIN-INC/PCD/keys --jq 'length'
```

## Notes

- Prefer a **user account** SSH key over a repo deploy key so org transfer / GHCR / Actions identity stay aligned.
- Account key `git push` (`3gW+…`) only works if its private key is restored onto a machine; until then use `id_porterchain`.
- Do not paste private key material into this file or into chat logs.
- Stay on **GitHub Free for organizations** — no Team upgrade required for CI/Deploy. Branch protection on private repos needs Team; we accept that constraint.
