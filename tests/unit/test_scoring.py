from helpers import make_job

from rojgaar.preferences import Preferences
from rojgaar.scoring import BM25, build_query, cosine, rrf, shortlist, tokenize


def prefs():
    return Preferences.model_validate(
        {"ranking": {"target_titles": ["Backend Engineer"], "core_skills": {"Go": 3, "PostgreSQL": 2}}}
    )


def test_tokenize_keeps_tech_symbols_and_drops_stopwords():
    assert tokenize("We use C++, C# and Node.js with the team") == ["use", "c++", "c#", "node.js", "team"]


def test_bm25_prefers_matching_documents():
    docs = [tokenize("go postgresql backend"), tokenize("react css design"), tokenize("go go go")]
    scores = BM25(docs).score(tokenize("go postgresql"))
    assert scores[0] > scores[2] > scores[1] == 0


def test_build_query_weights_skills():
    q = build_query(prefs(), ["Kafka"])
    assert q.count("go") == 3
    assert q.count("postgresql") == 2
    assert q.count("backend") == 2
    assert "kafka" in q


def test_rrf_rewards_agreement():
    fused = rrf([["a", "b", "c"], ["b", "a", "c"]])
    assert fused["a"] == fused["b"] > fused["c"]


def test_cosine():
    assert cosine([1, 0], [1, 0]) == 1
    assert cosine([1, 0], [0, 1]) == 0
    assert cosine([0, 0], [1, 1]) == 0


def test_shortlist_bm25_only_is_deterministic():
    jobs = [
        make_job(uid="design", title="Product Designer", description="Figma, user research"),
        make_job(uid="be", title="Backend Engineer", description="Go and PostgreSQL services"),
        make_job(uid="fe", title="Frontend Engineer", description="React"),
    ]
    out = shortlist(jobs, prefs(), n=2)
    assert [s.uid for s in out] == ["be", "fe"]
    assert out[0].bm25_rank == 1 and out[0].embed_rank is None
    assert shortlist([], prefs(), n=5) == []


class FakeEmbedder:
    """Embeds by counting a few keywords, so rankings are predictable."""

    VOCAB = ["go", "postgresql", "react", "figma", "backend"]

    def embed(self, texts):
        return [[t.lower().count(w) for w in self.VOCAB] for t in texts]


def test_shortlist_fuses_embeddings():
    jobs = [
        make_job(uid="be", title="Backend Engineer", description="Go PostgreSQL"),
        make_job(uid="fe", title="Frontend Engineer", description="React React React"),
    ]
    out = shortlist(jobs, prefs(), n=2, embedder=FakeEmbedder())
    assert out[0].uid == "be"
    assert out[0].embed_rank == 1
    assert out[0].to_dict()["embed"] is not None
