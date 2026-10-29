// Starts TikTok Login Kit. Redirects to TikTok's consent screen.
const crypto = require("crypto");

const SCOPES = "user.info.basic,video.upload,video.publish";

module.exports = (req, res) => {
  const clientKey = process.env.TIKTOK_CLIENT_KEY;
  if (!clientKey) {
    res.status(500).send("TIKTOK_CLIENT_KEY is not set in Vercel.");
    return;
  }
  const state = crypto.randomBytes(16).toString("hex");
  const redirectUri = `https://${req.headers.host}/api/callback`;
  const url = new URL("https://www.tiktok.com/v2/auth/authorize/");
  url.searchParams.set("client_key", clientKey);
  url.searchParams.set("scope", SCOPES);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("redirect_uri", redirectUri);
  url.searchParams.set("state", state);
  res.setHeader("Set-Cookie", `tt_state=${state}; Path=/api; HttpOnly; Secure; SameSite=Lax; Max-Age=600`);
  res.writeHead(302, { Location: url.toString() });
  res.end();
};
