import json
import pytest
from ade_integrity.core import *


def test_crosscheck_canonical_and_ledger(tmp_path):
    assert sha256_json({"b": 1, "a": 2}) == sha256_json({"a": 2, "b": 1})
    body = {"seq": 0, "prev_sha256": "", "value": 1}
    body["row_sha256"] = sha256_json(body)
    p = tmp_path / "l"
    p.write_text(json.dumps(body) + "\n")
    assert verify_ledger(p) == []
    body["value"] = 2
    p.write_text(json.dumps(body) + "\n")
    assert verify_ledger(p)


def test_abstention_and_receipt():
    assert judge_paired([1, 1])["verdict"] == "abstain"
    assert judge_paired([0] * 6)["reason"] == "zero_variance"
    assert not verify_receipt(
        {
            "status": "ok",
            "input_sha256": "x",
            "output_sha256": "y",
            "externally_verified": 1,
        }
    )


def test_holm_step_down_and_validation():
    assert list(holm([0.01, 0.03, 0.04]).values()).count(True) == 1
    for bad in ([float("nan")], [1.2], [-0.1]):
        try:
            holm(bad)
        except ValueError:
            pass
        else:
            assert False


def test_missing_chained_sequence_and_bad_tip_fail(tmp_path):
    first = {"seq": 5, "prev_sha256": "", "event": "start"}
    first["row_sha256"] = sha256_json(first)
    second = {"event": "missing seq"}
    second["row_sha256"] = sha256_json(second)
    path = tmp_path / "ledger"
    path.write_text(json.dumps(first) + "\n" + json.dumps(second) + "\n")
    assert any("seq" in e for e in verify_ledger(path))
    path.write_text(json.dumps(first) + "\n")
    tip = tmp_path / "tip"
    tip.write_text(json.dumps({"seq": 5, "row_sha256": "wrong"}))
    assert verify_ledger(path, tip_path=tip)


def test_effect_gate_and_confidence_level_are_honest():
    deltas = [0.99, 1.01, 0.98, 1.02, 1.00, 1.03]
    result = judge_paired(deltas, min_effect=2, alpha=.01)
    assert result["verdict"] == "abstain" and result["reason"] == "below_min_effect"
    assert result["confidence_level"] == .99 and "ci95" not in result
    for kwargs in ({"min_n": 6.5}, {"min_effect": float("nan")}, {"min_effect": True}):
        with pytest.raises(ValueError):
            judge_paired(deltas, **kwargs)
