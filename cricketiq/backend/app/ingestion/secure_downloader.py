"""Secure Official Document Downloader for CricketIQ.

Enforces SSRF defense, DNS resolution validation (blocking loopback, private,
and reserved IP ranges), strict approved official host checks, HTTPS enforcement,
redirect revalidation, PDF magic-byte checks, streaming size bounds, and path traversal protection.
"""

from __future__ import annotations
import hashlib
import ipaddress
import os
import re
import socket
import uuid
from pathlib import Path
from typing import Tuple, Set
from urllib.parse import urlparse

import httpx

OFFICIAL_APPROVED_HOSTS: Set[str] = {
    "icc-cricket.com",
    "www.icc-cricket.com",
    "resources.pulse.icc-cricket.com",
    "images.icc-cricket.com",
    "lords.org",
    "www.lords.org",
}

PDF_MAGIC_BYTES = b"%PDF-"
MAX_DOCUMENT_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB limit
DEFAULT_TIMEOUT_SECONDS = 15.0


class SecurityValidationError(ValueError):
    """Raised when a download violates SSRF or security policies."""
    pass


def validate_ip_address(ip_str: str) -> None:
    """Validate that an IP is publicly routable and not private, loopback, or reserved."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError as e:
        raise SecurityValidationError(f"Invalid IP address format: {ip_str}") from e

    if ip.is_loopback:
        raise SecurityValidationError(f"Loopback IP rejected: {ip_str}")
    if ip.is_link_local:
        raise SecurityValidationError(f"Link-local IP rejected: {ip_str}")
    if ip.is_private:
        raise SecurityValidationError(f"Private network IP rejected: {ip_str}")
    if ip.is_multicast:
        raise SecurityValidationError(f"Multicast IP rejected: {ip_str}")
    if ip.is_reserved:
        raise SecurityValidationError(f"Reserved IP rejected: {ip_str}")


def validate_url_security(url: str) -> Tuple[str, int]:
    """Perform comprehensive SSRF and URL validation before any network request."""
    parsed = urlparse(url)

    if parsed.scheme.lower() != "https":
        raise SecurityValidationError(f"Insecure scheme '{parsed.scheme}'. Only HTTPS is permitted.")

    if parsed.username or parsed.password:
        raise SecurityValidationError("Userinfo (credentials) in URL is forbidden.")

    port = parsed.port or 443
    if port != 443:
        raise SecurityValidationError(f"Nonstandard port {port} rejected. Only port 443 is permitted.")

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise SecurityValidationError("URL missing valid hostname.")

    # Check if host is an IP literal before any allowlist check
    is_ip_literal = False
    try:
        ipaddress.ip_address(hostname)
        is_ip_literal = True
    except ValueError:
        is_ip_literal = False

    if is_ip_literal:
        raise SecurityValidationError("Direct IP literals in hostnames are prohibited.")

    if hostname not in OFFICIAL_APPROVED_HOSTS:
        raise SecurityValidationError(f"Hostname '{hostname}' is not in approved official hosts allowlist.")

    # DNS Resolution and SSRF / DNS Rebinding check
    try:
        addr_info = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise SecurityValidationError(f"DNS resolution failed for '{hostname}': {e}") from e

    resolved_ips = set()
    for entry in addr_info:
        sockaddr = entry[4]
        ip_str = sockaddr[0]
        resolved_ips.add(ip_str)
        validate_ip_address(ip_str)

    if not resolved_ips:
        raise SecurityValidationError(f"No IP addresses resolved for '{hostname}'.")

    return hostname, port


class SecureDocumentDownloader:
    """Streams and validates official PDFs under strict security constraints."""

    def __init__(self, dest_dir: Path, max_size_bytes: int = MAX_DOCUMENT_SIZE_BYTES):
        self.dest_dir = Path(dest_dir)
        self.dest_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = max_size_bytes

    def download_pdf(self, url: str) -> Tuple[Path, str]:
        """Download an official PDF securely. Returns (local_path, sha256_hash)."""
        validate_url_security(url)

        # Generate a safe, server-generated filename to prevent path traversal
        safe_filename = f"{uuid.uuid4().hex}.pdf"
        target_path = self.dest_dir / safe_filename

        sha256 = hashlib.sha256()
        bytes_received = 0
        magic_bytes_verified = False

        transport = httpx.HTTPTransport(retries=1)
        with httpx.Client(transport=transport, timeout=DEFAULT_TIMEOUT_SECONDS, follow_redirects=False) as client:
            try:
                with client.stream("GET", url) as response:
                    # If server returns redirect, re-validate redirect target
                    if response.is_redirect:
                        redirect_url = response.headers.get("location")
                        if not redirect_url:
                            raise SecurityValidationError("Redirect missing Location header.")
                        validate_url_security(redirect_url)
                        # Re-execute against revalidated target
                        return self.download_pdf(redirect_url)

                    if response.status_code != 200:
                        raise ValueError(f"HTTP request failed with status code {response.status_code}")

                    with open(target_path, "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            if not magic_bytes_verified and chunk:
                                if not chunk.startswith(PDF_MAGIC_BYTES):
                                    raise SecurityValidationError("Downloaded content lacks valid PDF magic bytes.")
                                magic_bytes_verified = True

                            bytes_received += len(chunk)
                            if bytes_received > self.max_size_bytes:
                                raise SecurityValidationError(f"File exceeded maximum allowed size of {self.max_size_bytes} bytes.")

                            sha256.update(chunk)
                            f.write(chunk)
            except Exception:
                if target_path.exists():
                    target_path.unlink()
                raise

        if not magic_bytes_verified or bytes_received == 0:
            if target_path.exists():
                target_path.unlink()
            raise SecurityValidationError("Downloaded file was empty or not a valid PDF.")

        return target_path, sha256.hexdigest()
