from helpers import NOW, make_job

from rojgaar.dedup import (
    canonical_url,
    dedup_keys,
    estimate_jaccard,
    find_duplicate,
    jaccard,
    minhash,
    norm_company,
    shingles,
)
from rojgaar.store import Store

LONG = (
    "We are hiring a backend engineer to build payment ledgers in Go and PostgreSQL. You will own services end to "
    "end, partner with product, review designs, mentor engineers, improve reliability, reduce latency, and run "
    "on-call for the systems you build. We value clear writing, careful testing, and kindness."
)


def test_canonical_url_strips_tracking():
    a = canonical_url("https://Boards.Greenhouse.io/acme/jobs/1/?gh_src=x&utm_source=li#apply")
    b = canonical_url("https://boards.greenhouse.io/acme/jobs/1")
    assert a == b


def test_norm_company_ignores_suffixes():
    assert norm_company("Acme Fintech, Inc.") == norm_company("acme fintech")


def test_keys_priority():
    keys = dedup_keys(make_job())
    assert keys[0] == "ats:greenhouse:1"
    assert keys[1].startswith("url:https://boards.greenhouse.io/acme/jobs/1")
    assert keys[2] == "ctl:acmefintech|senior backend engineer|sanfrancisco"


def test_engineer_levels_stay_distinct():
    k1 = dedup_keys(make_job(title="Software Engineer I", ats_job_id=None, apply_url=""))
    k2 = dedup_keys(make_job(title="Software Engineer II", ats_job_id=None, apply_url=""))
    assert set(k1).isdisjoint(k2)


def test_sr_normalised_to_senior():
    k1 = dedup_keys(make_job(title="Sr. Backend Engineer", ats_job_id=None, apply_url=""))
    k2 = dedup_keys(make_job(title="Senior Backend Engineer", ats_job_id=None, apply_url=""))
    assert k1 == k2


def test_cross_board_duplicate_found_via_store():
    s = Store()
    canonical = make_job(
        uid="greenhouse:acme:9", title="Staff Platform Engineer", locations=["Remote - US"], remote="remote"
    )
    s.upsert_job(canonical, NOW, keys=dedup_keys(canonical))
    copy = make_job(
        uid="remotive:acme:2002",
        source="remotive",
        title="Staff Platform Engineer",
        locations=["Remote (USA)"],
        remote="remote",
        ats=None,
        ats_job_id=None,
        apply_url="https://remotive.com/x",
    )
    decision = find_duplicate(copy, s)
    assert decision.duplicate_of == "greenhouse:acme:9"
    assert decision.reason == "ctl"


def test_repost_detected_with_minhash():
    s = Store()
    original = make_job(
        uid="a", description=LONG, apply_url="https://x/1", ats_job_id="1", locations=["Oakland, CA"]
    )
    s.upsert_job(original, NOW, keys=dedup_keys(original))
    repost = make_job(
        uid="b",
        description=LONG.replace("kindness.", "kindness and curiosity."),
        apply_url="https://x/2",
        ats_job_id="2",
        locations=["Fremont, CA"],
    )
    decision = find_duplicate(repost, s)
    assert decision == decision.__class__("a", "repost")


def test_different_job_same_company_is_not_a_repost():
    s = Store()
    s.upsert_job(make_job(uid="a", description=LONG), NOW)
    other = make_job(
        uid="b", title="Product Designer", description=LONG, apply_url="https://x/3", ats_job_id="3"
    )
    assert find_duplicate(other, s).duplicate_of is None


def test_minhash_estimates_jaccard():
    a = shingles(LONG)
    b = shingles(LONG + " Extra words appended at the end here.")
    est = estimate_jaccard(minhash(a), minhash(b))
    assert abs(est - jaccard(a, b)) < 0.15
    assert estimate_jaccard(minhash(a), minhash(a)) == 1.0
