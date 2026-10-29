// TikTok redirects here after login. Exchanges the code for tokens and shows
// the refresh token once, so it can be saved as the TIKTOK_REFRESH_TOKEN secret.

const page = (title, body) => `<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>${title} | Invites Autopost</title>
<style>body{font-family:system-ui,sans-serif;max-width:720px;margin:40px auto;padding:0 16px;line-height:1.6;color:#222}
textarea{width:100%;height:90px;font-family:monospace}a{color:#b0466b}</style></head><body>
<h1>${title}</h1>${body}<p><a href="/">Home</a></p></body></html>`;

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);

module.exports = async (req, res) => {
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  const { code, state, error, error_description } = req.query;

  if (error) {
    res.status(400).send(page("Login failed", `<p>${esc(error)}: ${esc(error_description || "")}</p>`));
    return;
  }
  const cookieState = (req.headers.cookie || "").match(/(?:^|;\s*)tt_state=([^;]+)/);
  if (!code || !state || !cookieState || cookieState[1] !== state) {
    res.status(400).send(page("Login failed", '<p>Invalid or expired login. <a href="/api/login">Try again</a>.</p>'));
    return;
  }

  const body = new URLSearchParams({
    client_key: process.env.TIKTOK_CLIENT_KEY,
    client_secret: process.env.TIKTOK_CLIENT_SECRET,
    code,
    grant_type: "authorization_code",
    redirect_uri: `https://${req.headers.host}/api/callback`,
  });
  const r = await fetch("https://open.tiktokapis.com/v2/oauth/token/", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  const data = await r.json();
  if (!data.refresh_token) {
    res.status(502).send(page("Login failed", `<p>${esc(data.error || r.status)}: ${esc(data.error_description || "")}</p>`));
    return;
  }

  res.setHeader("Set-Cookie", "tt_state=; Path=/api; Max-Age=0");
  res.send(page("Connected to TikTok", `
<p>Copy this refresh token and save it in GitHub as the Actions secret <b>TIKTOK_REFRESH_TOKEN</b>.
It is shown only once and is valid for about a year.</p>
<textarea readonly onclick="this.select()">${esc(data.refresh_token)}</textarea>
<p>Scopes granted: ${esc(data.scope)}</p>`));
};
