import json, random
from pathlib import Path
import pytest
from ade_integrity.core import judge_paired, verify_ledger, sha256_json


def test_recorded_repository_counts_and_chain():
    root = Path(__file__).resolve().parents[3]
    ledger = root / "LEDGER.jsonl"
    prereg = root / "prereg"
    if not ledger.is_file() or not prereg.is_dir():
        pytest.skip("optional ADE checkout integration; public package ships no research evidence")
    assert sum(1 for _ in ledger.open(encoding="utf-8")) > 0
    assert len(list(prereg.glob("*.json"))) > 0
    assert verify_ledger(ledger) == []


def test_against_scipy_seeded_arrays():
    scipy = pytest.importorskip("scipy.stats")
    rng = random.Random(1193)
    for n in (6, 7, 32, 100):
        for mode in range(13):
            vals = [
                (-1 if mode % 3 == 0 else 1) * (rng.random() - 0.5) for _ in range(n)
            ]
            if mode == 1:
                vals = [1e9 + x * 1e-6 for x in vals]
            if mode == 2:
                vals = [1e-9 * x for x in vals]
            ours = judge_paired(vals)
            ref = scipy.ttest_1samp(vals, 0)
            assert abs(ours["p_value"] - float(ref.pvalue)) < 1e-8
            assert len(ours["ci95"]) == 2
