"""Live view of a headless Chromium running on this server.

Supervisor runs `python -m jgb.browser_stream run` (see
/etc/supervisor/conf.d/jgb-browser-stream.conf). The browser-stream Page
polls frame() and sends input via command().

State lives in <bench>/browser_stream/: frame.jpg (latest JPEG),
meta.json (url/title/ts), cmd.jsonl (append-only command queue).
"""
import base64
import json
import os
import time
from pathlib import Path

import frappe

BENCH = Path(__file__).resolve().parents[3]
STREAM_DIR = BENCH / "browser_stream"
FRAME = STREAM_DIR / "frame.jpg"
META = STREAM_DIR / "meta.json"
CMD = STREAM_DIR / "cmd.jsonl"

VIEWPORT = {"width": 1280, "height": 800}
DELAY = 0.35  # ~3 fps
CMD_MAX_BYTES = 256 * 1024


def _check_access():
    if "System Manager" not in frappe.get_roles():
        frappe.throw("Not permitted", frappe.PermissionError)


@frappe.whitelist()
def frame():
    """Latest screencast frame as base64 JPEG + browser metadata."""
    _check_access()
    meta = {}
    if META.exists():
        try:
            meta = json.loads(META.read_text())
        except ValueError:
            pass
    image = ""
    if FRAME.exists():
        image = base64.b64encode(FRAME.read_bytes()).decode()
    return {
        "image": image,
        "url": meta.get("url"),
        "title": meta.get("title"),
        "ts": meta.get("ts", 0),
        "alive": time.time() - meta.get("ts", 0) < 5,
    }


@frappe.whitelist()
def command(action, **kw):
    """Queue an input command for the streaming browser."""
    _check_access()
    STREAM_DIR.mkdir(exist_ok=True)
    with open(CMD, "a") as f:
        f.write(json.dumps({"action": action, **kw}) + "\n")
    return {"ok": True}


def _read_cmds(state):
    """Yield new commands appended since last read; reset if file too big."""
    if not CMD.exists():
        return
    size = CMD.stat().st_size
    if size < state["off"] or size > CMD_MAX_BYTES:
        state["off"] = 0
    with open(CMD, "rb") as f:
        f.seek(state["off"])
        data = f.read()
        state["off"] = f.tell()
    for line in data.decode().splitlines():
        try:
            yield json.loads(line)
        except ValueError:
            pass


def _apply(page, cmd):
    a = cmd.get("action")
    if a == "goto":
        url = cmd.get("url", "")
        if url and "://" not in url:
            url = "https://" + url
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
    elif a == "back":
        page.go_back(wait_until="domcontentloaded", timeout=10000)
    elif a == "forward":
        page.go_forward(wait_until="domcontentloaded", timeout=10000)
    elif a == "reload":
        page.reload(wait_until="domcontentloaded", timeout=20000)
    elif a == "click":
        page.mouse.click(float(cmd["x"]), float(cmd["y"]),
                         button=cmd.get("button", "left"),
                         click_count=int(cmd.get("count", 1)))
    elif a == "move":
        page.mouse.move(float(cmd["x"]), float(cmd["y"]))
    elif a == "type":
        page.keyboard.type(cmd.get("text", ""))
    elif a == "key":
        page.keyboard.press(cmd["key"])
    elif a == "scroll":
        page.mouse.wheel(0, float(cmd.get("dy", 0)))


def run():
    STREAM_DIR.mkdir(exist_ok=True)
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/home/ubuntu/erp-video/pw-browsers")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        # executable_path pinned: bench env has playwright 1.62 but the only
        # browser builds on disk are 1243 (installed by erp-video's node
        # playwright 1.63). CDP is stable across these revisions.
        browser = p.chromium.launch(headless=True, executable_path=(
            "/home/ubuntu/erp-video/pw-browsers/"
            "chromium_headless_shell-1243/chrome-headless-shell-linux64/"
            "chrome-headless-shell"))
        page = browser.new_page(viewport=VIEWPORT)
        page.goto("about:blank")
        # start at EOF — do not replay commands queued while the process was down
        state = {"off": CMD.stat().st_size if CMD.exists() else 0}
        while True:
            for cmd in _read_cmds(state):
                try:
                    if cmd.get("action") == "close":
                        page.close()
                        page = browser.new_page(viewport=VIEWPORT)
                    else:
                        _apply(page, cmd)
                except Exception as e:  # keep stream alive on bad commands/navigation
                    print(f"command {cmd.get('action')} failed: {e}", flush=True)
            try:
                jpg = page.screenshot(type="jpeg", quality=55)
                tmp = FRAME.with_suffix(".tmp")
                tmp.write_bytes(jpg)
                os.replace(tmp, FRAME)
                META.write_text(json.dumps({
                    "url": page.url,
                    "title": page.title(),
                    "ts": time.time(),
                }))
            except Exception as e:
                print(f"screenshot failed: {e}", flush=True)
                time.sleep(1)
            time.sleep(DELAY)


if __name__ == "__main__":
    run()
