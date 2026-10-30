import httpx
import pytest

from rojgaar.http import DEFAULT_UA, FetchError, PoliteClient


def make(handler, **kw):
    sleeps: list[float] = []
    kw.setdefault("min_delay", 0)
    kw.setdefault("jitter", 0)
    c = PoliteClient(transport=httpx.MockTransport(handler), sleep=sleeps.append, **kw)
    return c, sleeps


def test_honest_user_agent_is_sent():
    seen = {}

    def handler(req):
        seen["ua"] = req.headers["user-agent"]
        return httpx.Response(200, json={})

    c, _ = make(handler)
    c.get_json("https://example.com/x")
    assert seen["ua"] == DEFAULT_UA
    assert "personal job search" in seen["ua"]


def test_retry_after_is_honoured():
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "3"})
        return httpx.Response(200, json={"ok": True})

    c, sleeps = make(handler)
    assert c.get_json("https://example.com/x") == {"ok": True}
    assert calls["n"] == 2
    assert 3.0 in sleeps


def test_server_errors_retry_with_backoff_then_fail():
    c, sleeps = make(lambda req: httpx.Response(503), max_retries=2)
    with pytest.raises(FetchError) as exc:
        c.get_json("https://example.com/x")
    assert exc.value.status == 503
    assert sleeps == [1.0, 2.0]


def test_client_errors_do_not_retry():
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        return httpx.Response(404)

    c, _ = make(handler)
    with pytest.raises(FetchError, match="HTTP 404"):
        c.get_json("https://example.com/missing")
    assert calls["n"] == 1


def test_min_delay_per_host():
    t = {"now": 100.0}
    sleeps: list[float] = []
    c = PoliteClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})),
        min_delay=2.0,
        jitter=0,
        sleep=sleeps.append,
        clock=lambda: t["now"],
    )
    c.get_json("https://a.example/1")
    c.get_json("https://a.example/2")  # same host, no time passed → must wait 2s
    c.get_json("https://b.example/1")  # different host → no wait
    assert sleeps == [2.0]


def test_non_json_raises():
    c, _ = make(lambda r: httpx.Response(200, text="<html>"))
    with pytest.raises(FetchError, match="not JSON"):
        c.get_json("https://example.com/x")


def test_robots_txt_respected():
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private/\n")
        return httpx.Response(200, text="page")

    c, _ = make(handler)
    assert c.get_text("https://example.com/careers") == "page"
    with pytest.raises(FetchError, match="robots"):
        c.get_text("https://example.com/private/jobs")


def test_missing_robots_means_allowed_and_forbidden_means_stay_away():
    c, _ = make(
        lambda r: httpx.Response(404) if r.url.path == "/robots.txt" else httpx.Response(200, text="ok")
    )
    assert c.allowed_by_robots("https://example.com/careers")
    c2, _ = make(lambda r: httpx.Response(403))
    assert not c2.allowed_by_robots("https://blocked.example/careers")


def test_network_errors_retry_then_raise():
    def handler(req):
        raise httpx.ConnectError("boom", request=req)

    c, sleeps = make(handler, max_retries=1)
    with pytest.raises(FetchError, match="network error"):
        c.get_json("https://example.com/x")
    assert sleeps == [1.0]
