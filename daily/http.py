from __future__ import annotations

import re
import ssl
import subprocess
import urllib.request


CHROMIUM: str = "/snap/bin/chromium"

ssl_ctx: ssl.SSLContext = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


def fetch_html_static(url: str, timeout: int = 12) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(
        req, timeout=timeout, context=ssl_ctx
    ).read().decode("utf-8", errors="replace")


def chromium_dom(url: str, timeout: int = 45, budget: int = 30000) -> str:
    try:
        r = subprocess.run(
            [CHROMIUM, "--headless=new", "--no-sandbox", "--disable-gpu",
             "--disable-dev-shm-usage",
             f"--virtual-time-budget={budget}", "--dump-dom", url],
            capture_output=True, text=True, timeout=timeout
        )
        return r.stdout
    except Exception:
        return ""


def _preprocess_html(html: str) -> str:
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.I | re.S)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.I | re.S)
    return html
