"""Tests for Issue #2: Proper HTTP status codes and error handling.

Tests verify that the monitor server returns appropriate HTTP status codes
(400 for bad input, 500 for server errors, 404 with JSON body for unknown routes)
and includes Content-Length headers.

These tests accept any valid implementation — they check status codes and
response structure, not specific error messages.
"""
from __future__ import annotations

import http.client
import json
import threading
from http.server import HTTPServer
from unittest.mock import patch

import pytest

from monitor_server import DashboardHandler


@pytest.fixture(scope="module")
def server():
    """Start a test server on a random port."""
    httpd = HTTPServer(("127.0.0.1", 0), DashboardHandler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd, port
    httpd.shutdown()


def _request(port, method, path, body=None, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    hdrs = headers or {}
    if body is not None:
        if isinstance(body, dict):
            body = json.dumps(body)
        hdrs.setdefault("Content-Type", "application/json")
    conn.request(method, path, body=body, headers=hdrs)
    resp = conn.getresponse()
    data = resp.read()
    conn.close()
    return resp, data


# ---------------------------------------------------------------------------
# Issue #2a: POST /api/classify — bad input returns 400
# ---------------------------------------------------------------------------


class TestClassifyBadInput:
    def test_empty_post_text_returns_400(self, server):
        """POST /api/classify with empty post_text should return 400."""
        _, port = server
        resp, body = _request(port, "POST", "/api/classify", {"post_text": ""})
        assert resp.status == 400, (
            f"Expected 400 for empty post_text, got {resp.status}"
        )

    def test_missing_post_text_returns_400(self, server):
        """POST /api/classify with no post_text key should return 400."""
        _, port = server
        resp, body = _request(port, "POST", "/api/classify", {"other": "data"})
        assert resp.status == 400, (
            f"Expected 400 for missing post_text, got {resp.status}"
        )

    def test_invalid_json_body_returns_400(self, server):
        """POST /api/classify with invalid JSON should return 400."""
        _, port = server
        resp, body = _request(
            port, "POST", "/api/classify", body="not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status == 400, (
            f"Expected 400 for invalid JSON, got {resp.status}"
        )

    def test_bad_input_returns_json_error_envelope(self, server):
        """Error responses should be JSON with a consistent structure."""
        _, port = server
        resp, body = _request(port, "POST", "/api/classify", {"post_text": ""})
        data = json.loads(body)
        # Should have a status/error field indicating failure
        assert "error" in data or data.get("status") in ("error", "failure"), (
            "Error response should include an error field or failure status"
        )


# ---------------------------------------------------------------------------
# Issue #2b: POST /api/classify — server error returns 500
# ---------------------------------------------------------------------------


class TestClassifyServerError:
    def test_classify_exception_returns_500(self, server):
        """If classify() raises an unexpected error, return 500 not 200."""
        _, port = server
        with patch("monitor_server.classify", side_effect=RuntimeError("boom")):
            resp, body = _request(
                port, "POST", "/api/classify",
                {"post_text": "Test post for classification"},
            )
        assert resp.status == 500, (
            f"Expected 500 for server error, got {resp.status}"
        )

    def test_server_error_returns_json_envelope(self, server):
        """500 responses should still be valid JSON."""
        _, port = server
        with patch("monitor_server.classify", side_effect=RuntimeError("boom")):
            resp, body = _request(
                port, "POST", "/api/classify",
                {"post_text": "Test post for classification"},
            )
        data = json.loads(body)
        assert "error" in data or data.get("status") in ("error", "failure")


# ---------------------------------------------------------------------------
# Issue #2c: Unknown routes return 404 with JSON body
# ---------------------------------------------------------------------------


class TestNotFound:
    def test_get_unknown_route_returns_404(self, server):
        """GET to an unknown path should return 404."""
        _, port = server
        resp, body = _request(port, "GET", "/api/nonexistent")
        assert resp.status == 404

    def test_post_unknown_route_returns_404(self, server):
        """POST to an unknown path should return 404."""
        _, port = server
        resp, body = _request(port, "POST", "/api/nonexistent", {"data": 1})
        assert resp.status == 404

    def test_404_has_json_body(self, server):
        """404 responses should have a JSON body, not be empty."""
        _, port = server
        resp, body = _request(port, "GET", "/api/nonexistent")
        assert len(body) > 0, "404 response should have a body"
        data = json.loads(body)
        assert isinstance(data, dict), "404 body should be a JSON object"


# ---------------------------------------------------------------------------
# Issue #2d: Content-Length header
# ---------------------------------------------------------------------------


class TestContentLength:
    def test_api_events_has_content_length(self, server):
        """API responses should include Content-Length header."""
        _, port = server
        resp, body = _request(port, "GET", "/api/events")
        cl = resp.getheader("Content-Length")
        assert cl is not None, "Response should include Content-Length header"
        assert int(cl) == len(body)

    def test_classify_error_has_content_length(self, server):
        """Error responses should also include Content-Length header."""
        _, port = server
        resp, body = _request(port, "POST", "/api/classify", {"post_text": ""})
        cl = resp.getheader("Content-Length")
        assert cl is not None, "Error response should include Content-Length header"
        assert int(cl) == len(body)
