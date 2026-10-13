# Macca Instagram token maintenance

Macca's publishing jobs continue using the existing `INSTAGRAM_ACCESS_TOKEN` secret.
The separate workflow `.github/workflows/instagram-token-maintenance.yml` checks
the account/token type and, where applicable, renews credentials on the **5th of
each month** without reducing publishing volume.

## One-time setup

1. Create a fine-grained GitHub personal access token scoped **only** to
   `PkLavc/lab`, with repository permission **Secrets: Read and write**.
   The GitHub token needs to remain valid for the automated updates to work.
2. In the `PkLavc/lab` repository's Actions secrets, save it as
   `INSTAGRAM_ROTATION_GITHUB_TOKEN`. Never commit or paste it into issues/PRs.
3. Leave `INSTAGRAM_ACCESS_TOKEN` unchanged. It is already used by Macca to
   publish and collect Instagram metrics.
4. After merging, run **Actions → Maintain Macca Instagram token → Run workflow**
   with `check` first. This tests token identity and GitHub secret read access
   without changing the Instagram token. Run `renew` only when using an
   Instagram Login token at least 24 hours old.

## What the workflow does

- **Instagram Login, long-lived token:** verifies the Instagram identity,
  confirms access to the GitHub Actions secret public key, requests a new token
  using Meta's `ig_refresh_token` operation, verifies that the refreshed token
  belongs to the same account, and updates **only**
  `PkLavc/lab → INSTAGRAM_ACCESS_TOKEN` using GitHub CLI.
- **Facebook Page token:** verifies that it belongs to Macca's configured
  Facebook Page, then leaves it unchanged. Facebook Page tokens are a different
  credential type and **must not** be sent to the Instagram Login refresh API.
  Long-lived Page tokens can have no scheduled expiration, but can be revoked.
- **Failure:** no secret is overwritten if GitHub access fails, if the token
  cannot be classified safely, or if Meta does not return a matching account.
  Failures are visible in GitHub Actions and do not pause existing workflows.

The script uses a separate credential for GitHub Secrets, masks newly issued
Meta tokens, and does not log token values. A successful *read* check is not
proof of write access: the first actual refresh verifies the write permission.

## Scope

This maintenance job is only for the **Macca** account in `PkLavc/lab`. It
does not modify PkLavc's Instagram credentials, the sibling blog/site repositories,
YouTube credentials, or `INSTAGRAM_AUDIO_ACCESS_TOKEN` if configured separately.

If the current token was issued with Facebook Login as a user token instead
of a Page token, this job fails safely rather than attempting an incompatible
Instagram Login refresh. That token must be exchanged or reauthorized through
its original Facebook Login flow.
