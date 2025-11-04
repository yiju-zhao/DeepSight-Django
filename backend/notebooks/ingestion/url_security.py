"""
URL security validation and SSRF protection.
"""

import ipaddress
import logging
import socket
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class SSRFProtectionError(Exception):
    """Raised when SSRF protection blocks a request."""

    pass


def validate_url_security(
    url: str, allow_private_networks: bool = False
) -> tuple[bool, Optional[str]]:
    """
    Validate URL against SSRF attacks.

    Args:
        url: URL to validate
        allow_private_networks: If True, allow private/internal IP addresses

    Returns:
        (is_valid, error_message) tuple

    Raises:
        SSRFProtectionError: If URL is blocked by SSRF protection
    """
    try:
        parsed = urlparse(url)

        # Only allow http/https
        if parsed.scheme not in ("http", "https"):
            return False, f"Invalid URL scheme: {parsed.scheme}. Only http/https allowed."

        # Require netloc (domain/IP)
        if not parsed.netloc:
            return False, "URL must have a valid domain or IP address"

        # Extract hostname (remove port if present)
        hostname = parsed.hostname
        if not hostname:
            return False, "Could not extract hostname from URL"

        # Resolve hostname to IP
        try:
            ip_addresses = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC)
            ips = [addr[4][0] for addr in ip_addresses]
        except socket.gaierror as e:
            return False, f"DNS resolution failed: {e}"

        # Check each resolved IP
        for ip_str in ips:
            try:
                ip = ipaddress.ip_address(ip_str)

                # Check for private/internal networks
                if not allow_private_networks:
                    if ip.is_private:
                        return False, f"Private IP address blocked: {ip}"
                    if ip.is_loopback:
                        return False, f"Loopback IP address blocked: {ip}"
                    if ip.is_link_local:
                        return False, f"Link-local IP address blocked: {ip}"
                    if ip.is_reserved:
                        return False, f"Reserved IP address blocked: {ip}"

                    # Additional checks for IPv6
                    if isinstance(ip, ipaddress.IPv6Address):
                        if ip.is_site_local:
                            return False, f"Site-local IPv6 address blocked: {ip}"

            except ValueError:
                # If IP parsing fails, continue (might be a valid hostname)
                continue

        return True, None

    except Exception as e:
        logger.error(f"URL security validation error: {e}")
        return False, f"URL validation failed: {e}"


def validate_redirect_security(
    redirect_url: str, allow_private_networks: bool = False
) -> tuple[bool, Optional[str]]:
    """
    Validate redirect URL for SSRF protection.

    Same as validate_url_security but specifically for redirects.
    """
    return validate_url_security(redirect_url, allow_private_networks)


def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """
    Sanitize filename by removing dangerous characters.

    Args:
        filename: Original filename
        max_length: Maximum filename length

    Returns:
        Sanitized filename
    """
    import re

    # Remove path separators and dangerous characters
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", filename)

    # Remove control characters
    filename = "".join(c for c in filename if c.isprintable())

    # Trim whitespace
    filename = filename.strip()

    # Limit length while preserving extension
    if len(filename) > max_length:
        name_part, ext = split_filename_extension(filename)
        name_part = name_part[: max_length - len(ext)]
        filename = name_part + ext

    return filename or "download"


def split_filename_extension(filename: str) -> tuple[str, str]:
    """
    Split filename into name and extension.

    Args:
        filename: Filename to split

    Returns:
        (name, extension) tuple
    """
    from pathlib import Path

    path = Path(filename)
    return path.stem, path.suffix
