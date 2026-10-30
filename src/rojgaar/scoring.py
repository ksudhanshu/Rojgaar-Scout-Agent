"""Stage 2 of the funnel: cheap local scoring.

BM25 (pure Python) plus optional local embeddings (fastembed), fused with
Reciprocal Rank Fusion. Embeddings are optional: without them the shortlist is
BM25-only and still deterministic.
"""

from __future__ import annotations

import math
import os
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from .models import Job
from .preferences import Preferences

STOPWORDS = set(
    "a an and are as at be by for from has have in is it its of on or our that the to we will with you your "
    "this they their who what when where which while about into over under more most than then them these "
    "those such can may must should would could also all any each other some only own same so too very".split()
)
TOKEN = re.compile(r"[a-z0-9][a-z0-9+#.]*[a-z0-9+#]|[a-z0-9]")


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN.findall(text.lower()) if t not in STOPWORDS]


class BM25:
    def __init__(self, docs: Sequence[list[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.docs = docs
        self.k1, self.b = k1, b
        self.n = len(docs)
        self.avgdl = (sum(len(d) for d in docs) / self.n) if self.n else 0.0
        self.tf = [Counter(d) for d in docs]
        df: Counter[str] = Counter()
        for d in docs:
            df.update(set(d))
        self.idf = {t: math.log(1 + (self.n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def score(self, query: list[str]) -> list[float]:
        out = []
        for i, tf in enumerate(self.tf):
            dl = len(self.docs[i]) or 1
            s = 0.0
            for q in query:
                f = tf.get(q)
                if not f:
                    continue
                s += (
                    self.idf.get(q, 0.0)
                    * f
                    * (self.k1 + 1)
                    / (f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1)))
                )
            out.append(s)
        return out


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class FastEmbedder:
    def __init__(self, model: str = "BAAI/bge-small-en-v1.5") -> None:
        from fastembed import TextEmbedding  # type: ignore[import-not-found]

        self._model = TextEmbedding(model_name=model)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [list(map(float, v)) for v in self._model.embed(texts)]


def get_embedder() -> Embedder | None:
    if os.environ.get("ROJGAAR_NO_EMBED"):
        return None
    try:
        return FastEmbedder()
    except Exception:  # fastembed not installed or model unavailable offline
        return None


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def rrf(rankings: list[list[str]], k: int = 60) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, uid in enumerate(ranking, 1):
            scores[uid] = scores.get(uid, 0.0) + 1.0 / (k + rank)
    return scores


def build_query(prefs: Preferences, bank_skills: list[str] | None = None) -> list[str]:
    q: list[str] = []
    for title in prefs.ranking.target_titles:
        q += tokenize(title) * 2
    for skill, weight in prefs.ranking.core_skills.items():
        q += tokenize(skill) * max(1, int(weight))
    for domain in prefs.ranking.preferred_domains:
        q += tokenize(domain)
    for skill in bank_skills or []:
        q += tokenize(skill)
    return q


def job_document(job: Job) -> str:
    return f"{job.title} {job.title} {job.title}\n{job.description}"


@dataclass
class ScoredJob:
    uid: str
    fused: float
    bm25_rank: int
    bm25: float
    embed_rank: int | None = None
    embed: float | None = None

    def to_dict(self) -> dict:
        return {
            "uid": self.uid,
            "fused": round(self.fused, 6),
            "bm25_rank": self.bm25_rank,
            "bm25": round(self.bm25, 4),
            "embed_rank": self.embed_rank,
            "embed": None if self.embed is None else round(self.embed, 4),
        }


def shortlist(
    jobs: list[Job],
    prefs: Preferences,
    n: int,
    bank_skills: list[str] | None = None,
    embedder: Embedder | None = None,
    ideal_jds: list[str] | None = None,
) -> list[ScoredJob]:
    if not jobs:
        return []
    docs = [tokenize(job_document(j)) for j in jobs]
    bm = BM25(docs).score(build_query(prefs, bank_skills))
    bm_order = sorted(range(len(jobs)), key=lambda i: (-bm[i], jobs[i].uid))
    bm_rank = {jobs[i].uid: r for r, i in enumerate(bm_order, 1)}
    rankings = [[jobs[i].uid for i in bm_order]]

    emb_score: dict[str, float] = {}
    emb_rank: dict[str, int] = {}
    if embedder is not None:
        queries = ideal_jds or [" ".join(prefs.ranking.target_titles + list(prefs.ranking.core_skills))]
        qv = embedder.embed(queries)
        dv = embedder.embed([job_document(j)[:4000] for j in jobs])
        for j, v in zip(jobs, dv, strict=True):
            emb_score[j.uid] = max(cosine(v, q) for q in qv)
        order = sorted(jobs, key=lambda j: (-emb_score[j.uid], j.uid))
        emb_rank = {j.uid: r for r, j in enumerate(order, 1)}
        rankings.append([j.uid for j in order])

    fused = rrf(rankings)
    results = [
        ScoredJob(
            uid=j.uid,
            fused=fused[j.uid],
            bm25_rank=bm_rank[j.uid],
            bm25=bm[i],
            embed_rank=emb_rank.get(j.uid),
            embed=emb_score.get(j.uid),
        )
        for i, j in enumerate(jobs)
    ]
    results.sort(key=lambda s: (-s.fused, s.bm25_rank, s.uid))
    return results[:n]
