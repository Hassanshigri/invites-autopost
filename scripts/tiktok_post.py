#!/usr/bin/env python3
"""Direct-post one video to TikTok via the Content Posting API.

Env: TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_REFRESH_TOKEN,
     VIDEO (https URL or repo path), CAPTION, PRIVACY (default SELF_ONLY).
Optional: GH_PAT + GITHUB_REPOSITORY to save a rotated refresh token.
"""
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

API = "https://open.tiktokapis.com"
MB = 1024 * 1024


def mask(value):
    print(f"::add-mask::{value}", flush=True)


def call(method, url, data=None, headers=None, form=False):
    headers = dict(headers or {})
    body = None
    if data is not None:
        if form:
            body = urllib.parse.urlencode(data).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif isinstance(data, bytes):
            body = data
        else:
            body = json.dumps(data).encode()
            headers["Content-Type"] = "application/json; charset=UTF-8"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        raw = e.read()
        print(f"HTTP {e.code} from {url.split('?')[0]}: {raw[:500]!r}", file=sys.stderr)
        if not raw.strip().startswith(b"{"):
            sys.exit(1)
    return json.loads(raw) if raw.strip() else {}


def refresh_access_token():
    old = os.environ["TIKTOK_REFRESH_TOKEN"]
    res = call("POST", f"{API}/v2/oauth/token/", {
        "client_key": os.environ["TIKTOK_CLIENT_KEY"],
        "client_secret": os.environ["TIKTOK_CLIENT_SECRET"],
        "grant_type": "refresh_token",
        "refresh_token": old,
    }, form=True)
    if "access_token" not in res:
        sys.exit(f"Token refresh failed: {res.get('error')} {res.get('error_description')}")
    mask(res["access_token"])
    new = res.get("refresh_token")
    if new and new != old:
        mask(new)
        if os.environ.get("GH_PAT"):
            subprocess.run(
                ["gh", "secret", "set", "TIKTOK_REFRESH_TOKEN", "--repo", os.environ["GITHUB_REPOSITORY"], "--body", new],
                check=True, env={**os.environ, "GH_TOKEN": os.environ["GH_PAT"]},
            )
            print("Saved rotated refresh token.")
        else:
            print("::warning::TikTok rotated the refresh token. Log in again at /api/login and update TIKTOK_REFRESH_TOKEN, or add a GH_PAT secret to save it automatically.")
    return res["access_token"]


def ok(res, step):
    err = res.get("error", {})
    if err.get("code") not in (None, "ok"):
        sys.exit(f"{step} failed: {err.get('code')} {err.get('message')} (log_id {err.get('log_id')})")
    return res.get("data", {})


def load_video(src):
    if src.startswith("http://") or src.startswith("https://"):
        print(f"Downloading {src}")
        with urllib.request.urlopen(src, timeout=300) as r:
            return r.read()
    with open(src, "rb") as f:
        return f.read()


def chunk_plan(size):
    # TikTok: chunks 5-64MB, last chunk may absorb the remainder; under 5MB goes whole.
    if size <= 64 * MB:
        return size, 1
    chunk = 10 * MB
    return chunk, size // chunk


def main():
    caption = os.environ.get("CAPTION", "").strip()
    privacy = os.environ.get("PRIVACY", "SELF_ONLY").strip() or "SELF_ONLY"
    video = load_video(os.environ["VIDEO"])
    size = len(video)
    print(f"Video size: {size / MB:.1f} MB")

    token = refresh_access_token()
    auth = {"Authorization": f"Bearer {token}"}

    info = ok(call("POST", f"{API}/v2/post/publish/creator_info/query/", {}, auth), "creator_info")
    print(f"Posting as @{info.get('creator_username')}")
    if privacy not in info.get("privacy_level_options", []):
        sys.exit(f"Privacy {privacy} not allowed. Options: {info.get('privacy_level_options')}")

    chunk, count = chunk_plan(size)
    init = ok(call("POST", f"{API}/v2/post/publish/video/init/", {
        "post_info": {
            "title": caption,
            "privacy_level": privacy,
            "disable_comment": bool(info.get("comment_disabled")),
            "disable_duet": bool(info.get("duet_disabled")),
            "disable_stitch": bool(info.get("stitch_disabled")),
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": size,
            "chunk_size": chunk,
            "total_chunk_count": count,
        },
    }, auth), "init")
    publish_id, upload_url = init["publish_id"], init["upload_url"]

    for i in range(count):
        start = i * chunk
        end = size if i == count - 1 else start + chunk
        call("PUT", upload_url, video[start:end], {
            "Content-Type": "video/mp4",
            "Content-Range": f"bytes {start}-{end - 1}/{size}",
        })
        print(f"Uploaded chunk {i + 1}/{count}")

    for _ in range(60):
        time.sleep(10)
        st = ok(call("POST", f"{API}/v2/post/publish/status/fetch/", {"publish_id": publish_id}, auth), "status")
        status = st.get("status")
        print(f"Status: {status}")
        if status == "PUBLISH_COMPLETE":
            print(f"Posted. publish_id={publish_id} post_ids={st.get('publicaly_available_post_id')}")
            return
        if status == "FAILED":
            sys.exit(f"Publish failed: {st.get('fail_reason')}")
    sys.exit("Timed out waiting for TikTok to finish processing.")


if __name__ == "__main__":
    main()
