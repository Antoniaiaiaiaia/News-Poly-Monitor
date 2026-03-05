#!/usr/bin/env python3
import json
import os
import re
import subprocess
import time
from html import unescape
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SOURCE_URL = os.environ.get("SOURCE_URL", "https://t.me/s/TechFlowDaily")
TARGET_CHAT_ID = os.environ.get("TARGET_CHAT_ID", "-1003713216091")
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "20"))
STATE_PATH = Path(os.environ.get("STATE_PATH", "/root/.openclaw/workspace/.tg_poly_web_state.json"))
MAX_MARKETS = int(os.environ.get("MAX_MARKETS", "3"))


def load_state():
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_post_id": 0, "seen": []}


def save_state(state):
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def fetch_channel_html():
    req = Request(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", errors="ignore")


def strip_html(s: str) -> str:
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    return unescape(s).strip()


def parse_posts(html: str):
    # 每个消息块包含 data-post="TechFlowDaily/12345"
    blocks = re.findall(r'(<div class="tgme_widget_message_wrap[\s\S]*?</div>\s*</div>)', html)
    out = []
    for b in blocks:
        m = re.search(r'data-post="[^"]+/(\d+)"', b)
        if not m:
            continue
        post_id = int(m.group(1))
        tm = re.search(r'<time[^>]*datetime="([^"]+)"', b)
        dt = tm.group(1) if tm else ""
        txtm = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>([\s\S]*?)</div>', b)
        if not txtm:
            continue
        text = strip_html(txtm.group(1))
        if not text:
            continue
        lines = [x.strip() for x in text.splitlines() if x.strip()]
        title = lines[0][:220] if lines else text[:220]
        content = "\n".join(lines[1:])[:1800] if len(lines) > 1 else text[:1800]
        out.append({"post_id": post_id, "datetime": dt, "title": title, "content": content, "raw": text})
    out.sort(key=lambda x: x["post_id"])
    return out


def run_poly_search(query: str, limit: int = 8):
    p = subprocess.run(["polymarket", "markets", "search", query, "--limit", str(limit), "-o", "json"], capture_output=True, text=True)
    if p.returncode != 0:
        return []
    try:
        data = json.loads(p.stdout)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def market_matches(title: str, content: str):
    res = run_poly_search(title, 8)
    if not res:
        words = re.sub(r"https?://\S+", " ", (title + " " + content).lower())
        words = re.sub(r"[^a-z0-9\u4e00-\u9fff\s]", " ", words)
        toks = [w for w in words.split() if len(w) > 2][:8]
        if toks:
            res = run_poly_search(" ".join(toks), 8)

    out = []
    seen = set()
    for m in res:
        slug = (m.get("slug") or "").strip()
        q = (m.get("question") or "").strip()
        if not slug or not q:
            continue
        if slug in seen:
            continue
        seen.add(slug)
        vol_raw = m.get("volume")
        try:
            vol = float(vol_raw) if vol_raw is not None else None
        except Exception:
            vol = None
        out.append({"title": q, "slug": slug, "volume": vol})
        if len(out) >= MAX_MARKETS:
            break
    return out


def send_to_target(msg: str):
    if not TG_BOT_TOKEN:
        raise RuntimeError("Missing TG_BOT_TOKEN")
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": str(TARGET_CHAT_ID),
        "text": msg,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    req = Request(url, data=urlencode(payload).encode("utf-8"), headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urlopen(req, timeout=25) as r:
        data = json.loads(r.read().decode("utf-8"))
    if not data.get("ok"):
        raise RuntimeError(f"sendMessage failed: {data}")


def format_message(item, markets):
    # 按 volume 从高到低排序
    markets_sorted = sorted(
        markets,
        key=lambda x: (x.get("volume") if isinstance(x.get("volume"), (int, float)) else -1),
        reverse=True,
    )

    lines = [f"*深潮新闻：{item['title']}*", "", "相关 Polymarket"]
    for m in markets_sorted:
        url = f"https://polymarket.com/market/{m['slug']}"
        vol = m.get("volume")
        if isinstance(vol, (int, float)):
            vol_text = f" (${vol:,.0f})"
        else:
            vol_text = ""
        lines.append(f"- [{m['title']}]({url}){vol_text}")
    return "\n".join(lines)[:3800]


def main():
    state = load_state()
    while True:
        try:
            html = fetch_channel_html()
            posts = parse_posts(html)
            if posts:
                for p in posts:
                    if p["post_id"] <= state.get("last_post_id", 0):
                        continue
                    key = str(p["post_id"])
                    if key in state.get("seen", []):
                        continue
                    markets = market_matches(p["title"], p["content"])
                    if markets:
                        send_to_target(format_message(p, markets))
                    state.setdefault("seen", []).append(key)
                    state["seen"] = state["seen"][-2000:]
                    state["last_post_id"] = max(state.get("last_post_id", 0), p["post_id"])
                save_state(state)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print("[WARN]", e, flush=True)
            time.sleep(3)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
