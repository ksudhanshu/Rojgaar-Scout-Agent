import pytest
from pydantic import ValidationError

from rojgaar.rubric import Judgement, judge_schema, rank, weighted_score

W = {"title": 2, "must_have": 3, "seniority": 2, "logistics": 2, "preference": 1}


def j(uid="a", **scores):
    base = {"title": 3, "must_have": 3, "seniority": 3, "logistics": 3, "preference": 3}
    base.update(scores)
    return Judgement(uid=uid, scores=base, verdict="strong")


def test_perfect_score_is_one():
    assert weighted_score(j(), W) == 1.0


def test_weights_matter():
    must_have_gap = j(must_have=0)
    preference_gap = j(preference=0)
    assert weighted_score(must_have_gap, W) < weighted_score(preference_gap, W)
    assert weighted_score(must_have_gap, W) == round(7 / 10, 4)


def test_dealbreaker_zeroes_score():
    judgement = j()
    judgement.dealbreaker_hit = True
    assert weighted_score(judgement, W) == 0


def test_rank_orders_by_score_then_uid():
    ranked = rank([j("b", title=1), j("a"), j("c")], W)
    assert [x[0].uid for x in ranked] == ["a", "c", "b"]


@pytest.mark.parametrize(
    "scores",
    [
        {"title": 3, "must_have": 3, "seniority": 3, "logistics": 3},  # missing dimension
        {"title": 4, "must_have": 3, "seniority": 3, "logistics": 3, "preference": 3},  # out of range
        {"title": 3, "must_have": 3, "seniority": 3, "logistics": 3, "preference": 3, "vibes": 2},  # unknown
    ],
)
def test_invalid_scores_rejected(scores):
    with pytest.raises(ValidationError):
        Judgement(uid="x", scores=scores, verdict="good")


def test_at_most_three_reasons():
    with pytest.raises(ValidationError):
        Judgement(uid="x", scores=j().scores, verdict="good", reasons=["1", "2", "3", "4"])


def test_schema_exports():
    schema = judge_schema()
    assert "judgements" in schema["properties"]
