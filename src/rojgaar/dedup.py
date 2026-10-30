"""Deduplicate the same job across boards and detect reposts.

Exact keys first (ATS id → canonical apply URL → company|title|location), never
fuzzy title similarity: "Engineer I" and "Engineer II" are different jobs.
Reposts with lightly edited text are caught by MinHash within one company.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import Job

TRACKING_PARAMS = re.compile(
    r"^(utm_.*|gh_src|gh_jid_src|lever-source.*|source|src|ref|referrer|trk|fbclid|gclid)$", re.I
)
COMPANY_SUFFIX = re.compile(r"\b(inc|inc\.|llc|ltd|corp|corporation|co|company|technologies|labs)\b\.?", re.I)


def canonical_url(url: str) -> str:
    if not url:
        return ""
    parts = urlsplit(url.strip())
    query = [
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=False) if not TRACKING_PARAMS.match(k)
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(
        (parts.scheme.lower() or "https", parts.netloc.lower(), path, urlencode(sorted(query)), "")
    )


def norm_company(name: str) -> str:
    name = COMPANY_SUFFIX.sub(" ", name.lower())
    return re.sub(r"[^a-z0-9]+", "", name)


def norm_title(title: str) -> str:
    t = title.lower()
    t = re.sub(r"\bsr\.?\b", "senior", t)
    t = re.sub(r"\bjr\.?\b", "junior", t)
    t = re.sub(r"[^a-z0-9+#]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def norm_location(job: Job) -> str:
    if job.remote == "remote":
        return "remote"
    first = job.locations[0] if job.locations else ""
    return re.sub(r"[^a-z]+", "", first.split(",")[0].lower())


def dedup_keys(job: Job) -> list[str]:
    keys = []
    if job.ats and job.ats_job_id:
        keys.append(f"ats:{job.ats}:{job.ats_job_id}")
    url = canonical_url(job.apply_url)
    if url:
        keys.append(f"url:{url}")
    keys.append(f"ctl:{norm_company(job.company)}|{norm_title(job.title)}|{norm_location(job)}")
    return keys


# -- MinHash -----------------------------------------------------------------
def shingles(text: str, k: int = 5) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    if len(words) < k:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i : i + k]) for i in range(len(words) - k + 1)}


def minhash(sh: set[str], num_perm: int = 128) -> list[int]:
    if not sh:
        return [0] * num_perm
    sig = []
    for seed in range(num_perm):
        salt = seed.to_bytes(4, "little")
        sig.append(
            min(
                int.from_bytes(hashlib.blake2b(s.encode(), digest_size=8, salt=salt).digest(), "little")
                for s in sh
            )
        )
    return sig


def estimate_jaccard(a: list[int], b: list[int]) -> float:
    return sum(1 for x, y in zip(a, b, strict=True) if x == y) / len(a) if a else 0.0


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


@dataclass
class DedupDecision:
    duplicate_of: str | None
    reason: str | None


def find_duplicate(job: Job, store, threshold: float = 0.8, min_words: int = 40) -> DedupDecision:  # type: ignore[no-untyped-def]
    """Return the uid this job duplicates, if any, using the store's key index and MinHash."""
    for key in dedup_keys(job):
        uid = store.uid_for_key(key)
        if uid and uid != job.uid:
            return DedupDecision(uid, key.split(":", 1)[0])

    if len(job.description.split()) < min_words:
        return DedupDecision(None, None)
    sh = shingles(job.description)
    sig = minhash(sh)
    for other in store.company_jobs(job.company, exclude_uid=job.uid):
        if norm_title(other.title) != norm_title(job.title):
            continue
        other_sh = shingles(other.description)
        if estimate_jaccard(sig, minhash(other_sh)) >= threshold and jaccard(sh, other_sh) >= threshold:
            return DedupDecision(other.uid, "repost")
    return DedupDecision(None, None)
