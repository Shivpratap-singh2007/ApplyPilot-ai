"""Security tests for URL validation, SSRF protection, and DNS rebinding checks."""

from pathlib import Path
import socket
import sys

import pytest

AGENT_ROOT = Path(__file__).resolve().parents[2] / "agent"
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

from applypilot_agent.browser.url_security import UnsafeURLError, validate_target_url  # noqa: E402


@pytest.mark.parametrize(
    "bad_url",
    [
        "",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "ftp://example.com/form",
        "https://user:secret@example.com/apply",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.5/internal",
        "http://192.168.1.10/admin",
        "http://127.0.0.1:8000/api/v1/health",
        "http://localhost:3000/",
    ],
)
def test_blocks_unsafe_or_private_urls_by_default(bad_url: str) -> None:
    with pytest.raises(UnsafeURLError):
        validate_target_url(bad_url, allow_localhost=False)


def test_allows_explicit_localhost_only_when_flag_enabled() -> None:
    target = validate_target_url("http://127.0.0.1:8080/internship", allow_localhost=True)
    assert target.hostname == "127.0.0.1"
    assert "127.0.0.1" in target.resolved_ips


def test_blocks_dns_rebinding_even_when_allow_localhost_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_getaddrinfo(*_args, **_kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    with pytest.raises(UnsafeURLError, match="restricted network range"):
        validate_target_url("https://evil-rebinding.example/apply", allow_localhost=True)

