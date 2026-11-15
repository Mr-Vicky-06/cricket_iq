"""Security tests for Remote Document Ingestion and SSRF Defenses in CricketIQ."""

import pytest
from cricketiq.backend.app.ingestion.secure_downloader import (
    validate_url_security, validate_ip_address, SecurityValidationError,
    OFFICIAL_APPROVED_HOSTS
)


def test_approved_official_hosts_list():
    assert "icc-cricket.com" in OFFICIAL_APPROVED_HOSTS
    assert "images.icc-cricket.com" in OFFICIAL_APPROVED_HOSTS
    assert "resources.pulse.icc-cricket.com" in OFFICIAL_APPROVED_HOSTS
    assert "lords.org" in OFFICIAL_APPROVED_HOSTS


def test_security_rejects_insecure_scheme():
    with pytest.raises(SecurityValidationError, match="Insecure scheme"):
        validate_url_security("http://icc-cricket.com/rules.pdf")


def test_security_rejects_userinfo():
    with pytest.raises(SecurityValidationError, match="Userinfo"):
        validate_url_security("https://admin:secret@icc-cricket.com/rules.pdf")


def test_security_rejects_nonstandard_port():
    with pytest.raises(SecurityValidationError, match="Nonstandard port"):
        validate_url_security("https://icc-cricket.com:8443/rules.pdf")


def test_security_rejects_unapproved_domain():
    with pytest.raises(SecurityValidationError, match="not in approved official hosts allowlist"):
        validate_url_security("https://untrusted-cricket.com/rules.pdf")


def test_security_rejects_ip_literal():
    with pytest.raises(SecurityValidationError, match="Direct IP literals"):
        validate_url_security("https://142.250.190.46/rules.pdf")


def test_ip_validation_blocks_loopback_and_private_ranges():
    # Loopback (127.0.0.1, ::1)
    with pytest.raises(SecurityValidationError, match="Loopback"):
        validate_ip_address("127.0.0.1")
    with pytest.raises(SecurityValidationError, match="Loopback"):
        validate_ip_address("::1")

    # Private RFC 1918
    with pytest.raises(SecurityValidationError, match="Private network"):
        validate_ip_address("10.0.0.1")
    with pytest.raises(SecurityValidationError, match="Private network"):
        validate_ip_address("172.16.0.1")
    with pytest.raises(SecurityValidationError, match="Private network"):
        validate_ip_address("192.168.1.1")

    # Link-Local (Cloud metadata endpoint 169.254.169.254)
    with pytest.raises(SecurityValidationError, match="Link-local"):
        validate_ip_address("169.254.169.254")

    # Multicast
    with pytest.raises(SecurityValidationError, match="Multicast"):
        validate_ip_address("224.0.0.1")


def test_ip_validation_allows_public_ip():
    # Public Google DNS IP as a public IP test
    validate_ip_address("8.8.8.8")
