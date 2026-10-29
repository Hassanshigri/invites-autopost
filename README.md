# invites-autopost

Posts Invites by Hassan videos to TikTok (@invitesbyhassan).

- Site + TikTok login: https://invites-autopost.vercel.app (Vercel, `api/` functions)
- Posting: Actions > **TikTok post** > Run workflow (video URL or repo path, caption, privacy)

Secrets (GitHub Actions): `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REFRESH_TOKEN`, optional `GH_PAT` (saves rotated refresh tokens).
Vercel env vars: `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`.
Get the refresh token by opening https://invites-autopost.vercel.app/api/login.
