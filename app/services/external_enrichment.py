import re
import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx

MAX_HTML_BYTES = 1_500_000
MAX_REDIRECTS = 3


def _collapse(text: str) -> str:
    return " ".join(text.split())


def _validate_public_https_url(url: str):
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("Only https URLs are allowed")
    if not parsed.hostname:
        raise ValueError("Invalid hostname")

    host = parsed.hostname.lower()
    blocked_hosts = {"localhost", "127.0.0.1", "::1"}
    if host in blocked_hosts:
        raise ValueError("Local addresses are blocked")

    # SSRF guard: reject private/reserved destination IPs.
    try:
        infos = socket.getaddrinfo(host, parsed.port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise ValueError(f"Hostname resolution failed: {exc}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError("Target resolves to non-public network")
    return parsed


def _fetch_limited_html(client: httpx.Client, url: str) -> str:
    current_url = url
    for _ in range(MAX_REDIRECTS + 1):
        _validate_public_https_url(current_url)
        with client.stream("GET", current_url, follow_redirects=False) as resp:
            status = resp.status_code
            if status in {301, 302, 303, 307, 308}:
                location = resp.headers.get("location")
                if not location:
                    raise ValueError("Redirect without location header")
                current_url = urljoin(current_url, location)
                continue
            resp.raise_for_status()
            content_type = (resp.headers.get("content-type") or "").lower()
            if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                raise ValueError("URL did not return HTML content")
            chunks: list[bytes] = []
            total = 0
            for chunk in resp.iter_bytes():
                total += len(chunk)
                if total > MAX_HTML_BYTES:
                    raise ValueError("HTML response exceeded size limit")
                chunks.append(chunk)
            return b"".join(chunks).decode(resp.encoding or "utf-8", errors="ignore")
    raise ValueError("Too many redirects")


def extract_company_summary(url: str, timeout: float = 6.0) -> str:
    _validate_public_https_url(url)
    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        html = _fetch_limited_html(client, url)

    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    title = _collapse(title_match.group(1)) if title_match else ""

    meta_match = re.search(
        r'<meta[^>]+name=[\"\']description[\"\'][^>]+content=[\"\'](.*?)[\"\']',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    meta_desc = _collapse(meta_match.group(1)) if meta_match else ""

    body_text = re.sub(r"<script.*?>.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    body_text = re.sub(r"<style.*?>.*?</style>", " ", body_text, flags=re.IGNORECASE | re.DOTALL)
    body_text = re.sub(r"<[^>]+>", " ", body_text)
    body_text = _collapse(body_text)[:800]

    parts = [part for part in [title, meta_desc, body_text] if part]
    return " | ".join(parts)[:1500]
