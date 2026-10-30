"""Markdown daily report: new matches with source attribution and apply links."""

from __future__ import annotations

from .dedup import canonical_url
from .models import Job

RISK_BADGE = {"low": "", "medium": " [medium risk]", "high": " [high risk]"}


def _salary(job: Job) -> str:
    s = job.salary
    if not s or (s.min is None and s.max is None):
        return "salary not stated"
    unit = {"year": "/yr", "month": "/mo", "hour": "/hr"}[s.period]

    def fmt(v: float | None) -> str:
        if v is None:
            return "?"
        return f"${v / 1000:.0f}k" if s.period == "year" and v >= 1000 else f"${v:,.0f}"

    return f"{fmt(s.min)}–{fmt(s.max)}{unit}" if s.min != s.max else f"{fmt(s.max)}{unit}"


def _entry(i: int, job: Job, extra: list[str]) -> list[str]:
    lines = [
        f"### {i}. {job.title} — {job.company}{RISK_BADGE.get(job.risk, '')}",
        f"- **Where:** {job.location_text()} · {job.remote}",
        f"- **Pay:** {_salary(job)}",
    ]
    lines += extra
    src = f"via {job.source}"
    if job.also_on:
        src += f" (also on {', '.join(job.also_on)})"
    if job.risk_flags:
        lines.append(f"- **Flags:** {', '.join(job.risk_flags)}")
    lines.append(
        f"- **Source:** {src} · [apply on the employer's site]({canonical_url(job.apply_url)})"
        if job.apply_url
        else f"- **Source:** {src}"
    )
    lines.append("")
    return lines


def render_report(
    run_date: str,
    jobs: dict[str, Job],
    shortlist: list[dict],
    rankings: list[dict] | None = None,
    top_n: int = 15,
    stats: dict | None = None,
) -> str:
    out = [f"# Rojgaar-Scout report — {run_date}", ""]
    if stats:
        out.append(
            f"_Fetched {stats.get('fetched', 0)} postings · {stats.get('new', 0)} new · "
            f"{stats.get('duplicates', 0)} duplicates · {stats.get('passed_filters', 0)} passed filters._"
        )
        out.append("")
    if rankings:
        out += ["## Best matches (ranked by your rubric)", ""]
        for i, r in enumerate(rankings[:top_n], 1):
            job = jobs.get(r["uid"])
            if not job:
                continue
            j = r["judgement"]
            extra = [f"- **Fit:** {j.get('verdict', '?')} · score {r['score']:.2f}"]
            if j.get("reasons"):
                extra.append("- **Why:** " + "; ".join(j["reasons"]))
            if j.get("gaps"):
                extra.append("- **Gaps:** " + "; ".join(j["gaps"]))
            out += _entry(i, job, extra)
    elif shortlist:
        out += ["## New matches (cheap scoring only, no LLM)", ""]
        for i, s in enumerate(shortlist[:top_n], 1):
            job = jobs.get(s["uid"])
            if job:
                out += _entry(i, job, [f"- **Relevance:** rank {i} (BM25 rank {s.get('bm25_rank')})"])
    else:
        out += ["No new matching jobs today.", ""]
    out += ["---", "Rojgaar-Scout never submits applications. Review, edit and apply yourself."]
    return "\n".join(out) + "\n"
