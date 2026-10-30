"""The only place Rojgaar-Scout talks to the network.

Guardrails live in code so every source adapter inherits them:
honest User-Agent, one request per host at a time with a minimum delay,
``Retry-After`` honoured, bounded retries, robots.txt for HTML pages.
No CAPTCHA solving, no stealth browsers, no proxy rotation, no logins.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from . import __version__

DEFAULT_UA = (
    f"RojgaarScout/{__version__} (+https://github.com/rojgaar-scout/Rojgaar-Scout-Agent; personal job search)"
)
RETRY_STATUS = {429, 500, 502, 503, 504}


class FetchError(RuntimeError):
    def __init__(self, url: str, message: str, status: int | None = None):
        super().__init__(f"{message} ({url})")
        self.url = url
        self.status = status


class PoliteClient:
    def __init__(
        self,
        user_agent: str = DEFAULT_UA,
        min_delay: float = 1.0,
        jitter: float = 1.0,
        max_retries: int = 3,
        timeout: float = 20.0,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        max_retry_after: float = 120.0,
    ) -> None:
        self.min_delay = min_delay
        self.jitter = jitter
        self.max_retries = max_retries
        self.max_retry_after = max_retry_after
        self._sleep = sleep
        self._clock = clock
        self._last: dict[str, float] = {}
        self._robots: dict[str, RobotFileParser | None] = {}
        self.user_agent = user_agent
        self.request_log: list[tuple[str, str]] = []
        self._client = httpx.Client(
            headers={"User-Agent": user_agent, "Accept": "application/json, text/html;q=0.8, */*;q=0.5"},
            timeout=timeout,
            transport=transport,
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> PoliteClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- politeness -------------------------------------------------------
    def _wait_for_host(self, host: str) -> None:
        last = self._last.get(host)
        if last is not None:
            gap = self.min_delay + (random.uniform(0, self.jitter) if self.jitter else 0.0)
            remaining = gap - (self._clock() - last)
            if remaining > 0:
                self._sleep(remaining)
        self._last[host] = self._clock()

    def _retry_after(self, response: httpx.Response, attempt: int) -> float:
        header = response.headers.get("Retry-After")
        if header and header.strip().isdigit():
            return min(float(header), self.max_retry_after)
        return min(2.0**attempt, self.max_retry_after)

    # -- requests ---------------------------------------------------------
    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        host = urlsplit(url).netloc.lower()
        for attempt in range(self.max_retries + 1):
            self._wait_for_host(host)
            self.request_log.append((method, url))
            try:
                response = self._client.request(method, url, **kwargs)
            except httpx.HTTPError as exc:
                if attempt >= self.max_retries:
                    raise FetchError(url, f"network error: {exc}") from exc
                self._sleep(min(2.0**attempt, self.max_retry_after))
                continue
            if response.status_code in RETRY_STATUS and attempt < self.max_retries:
                self._sleep(self._retry_after(response, attempt))
                continue
            if response.status_code >= 400:
                raise FetchError(url, f"HTTP {response.status_code}", status=response.status_code)
            return response
        raise FetchError(url, "retries exhausted")  # pragma: no cover

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        response = self.request("GET", url, params=params)
        try:
            return response.json()
        except ValueError as exc:
            raise FetchError(url, "response was not JSON") from exc

    def get_text(self, url: str, params: dict[str, Any] | None = None, check_robots: bool = True) -> str:
        if check_robots and not self.allowed_by_robots(url):
            raise FetchError(url, "disallowed by robots.txt")
        return self.request("GET", url, params=params).text

    def allowed_by_robots(self, url: str) -> bool:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            parser: RobotFileParser | None = RobotFileParser()
            try:
                text = self.request("GET", origin + "/robots.txt").text
                parser.parse(text.splitlines())
            except FetchError as exc:
                # No robots.txt (404) means allowed; an outright refusal means stay away.
                parser = None if exc.status in (401, 403) else _allow_all()
            self._robots[origin] = parser
        rp = self._robots[origin]
        return False if rp is None else rp.can_fetch(self.user_agent, url)


def _allow_all() -> RobotFileParser:
    rp = RobotFileParser()
    rp.parse([])
    return rp
