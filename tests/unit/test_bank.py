import pytest

from rojgaar.bank import BankError, example_bank_text, load_bank, parse_bank


def test_example_bank_is_valid():
    bank = parse_bank(example_bank_text())
    idx = bank.claim_index()
    assert "exp.acme.b1" in idx
    claim, role = idx["exp.acme.b1"]
    assert claim.qualifiers == ["co-led", "team of 4"]
    assert role.start_year() == 2022 and role.end_year() is None
    assert {"python", "go", "kubernetes"} <= bank.all_skills()


def test_duplicate_claim_ids_rejected():
    text = """
roles:
  - {id: r1, org: A, title: T, start: "2020", claims: [{id: c1, text: x}, {id: c1, text: y}]}
"""
    with pytest.raises(BankError, match="duplicate claim id"):
        parse_bank(text)


def test_profile_summary_excludes_unverified_claims():
    text = """
roles:
  - id: r1
    org: A
    title: T
    start: "2020"
    claims:
      - {id: c1, text: verified one, verified_by_user: true}
      - {id: c2, text: not checked yet}
"""
    summary = parse_bank(text).profile_summary()
    texts = [h["text"] for h in summary["work"][0]["highlights"]]
    assert texts == ["verified one"]


def test_missing_bank_file(tmp_path):
    with pytest.raises(BankError, match="rojgaar init"):
        load_bank(tmp_path / "bank.yaml")
