from __future__ import annotations
import hashlib, json, math
from pathlib import Path


def canonical_json(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def sha256_json(value):
    return hashlib.sha256(canonical_json(value)).hexdigest()


def verify_seal(payload, expected):
    body = dict(payload)
    body.pop("seal_sha256", None)
    return sha256_json(body) == expected


def verify_ledger(path, *, tip_path=None):
    errors = []
    with open(path, encoding="utf-8") as handle:
        rows = [json.loads(x) for x in handle if x.strip()]
    prev = ""
    seq = None
    for i, row in enumerate(rows, 1):
        recorded = row.get("row_sha256")
        body = {k: v for k, v in row.items() if k != "row_sha256"}
        if "row_sha256" not in row:
            errors.append(f"line {i}: missing row hash")
        elif sha256_json(body) != recorded:
            errors.append(f"line {i}: row hash")
        if "seq" in row or seq is not None:
            value = row.get("seq")
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                errors.append(f"line {i}: missing or invalid seq")
                continue
            if seq is None:
                seq = value
                prev = str(rows[i - 2].get("row_sha256") or "") if i > 1 else ""
            if value != seq or row.get("prev_sha256", "") != prev:
                errors.append(f"line {i}: chain")
            seq += 1
            prev = str(recorded or "")
    if tip_path is not None:
        tip = json.loads(Path(tip_path).read_text(encoding="utf-8"))
        if not rows or tip.get("seq") != rows[-1].get("seq") or tip.get("row_sha256") != rows[-1].get("row_sha256"):
            errors.append("tip does not match final row")
    return errors


def verify_seals(directory):
    bad = []
    total = 0
    for path in sorted(__import__("pathlib").Path(directory).glob("*.json")):
        total += 1
        payload = json.loads(path.read_text(encoding="utf-8"))
        recorded = str(payload.get("seal_sha256") or "")
        body = {k: v for k, v in payload.items() if k != "seal_sha256"}
        if not recorded or sha256_json(body) != recorded:
            bad.append(path.name)
    return {"total": total, "bad": bad}


def judge_paired(deltas, min_n=6, alpha=0.05, min_effect=0.0):
    if (
        isinstance(min_n, bool)
        or not isinstance(min_n, int)
        or min_n < 6
        or not isinstance(alpha, (int, float))
        or isinstance(alpha, bool)
        or not 0 < alpha < 1
        or not isinstance(min_effect, (int, float))
        or isinstance(min_effect, bool)
        or not math.isfinite(min_effect)
        or min_effect < 0
    ):
        raise ValueError("min_n must be >= 6 and alpha must be in (0,1)")
    deltas = list(deltas)
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in deltas):
        raise ValueError("deltas must be numeric, non-boolean values")
    vals = [float(x) for x in deltas]
    n = len(vals)
    if any(not math.isfinite(x) for x in vals):
        return {"verdict": "abstain", "reason": "nonfinite", "n": n}
    if n < min_n:
        return {"verdict": "abstain", "reason": "insufficient_sample", "n": n}
    try:
        mean = math.fsum(x / n for x in vals)
        var = math.fsum((x - mean) ** 2 for x in vals) / (n - 1)
    except OverflowError:
        return {"verdict": "abstain", "reason": "numeric_overflow", "n": n}
    if not math.isfinite(var):
        return {"verdict": "abstain", "reason": "numeric_overflow", "n": n}
    if var == 0:
        return {"verdict": "abstain", "reason": "zero_variance", "n": n, "mean": mean}
    t = mean / math.sqrt(var / n)
    df = n - 1
    p = _tpvalue(abs(t), df)
    verdict = (
        "positive"
        if p < alpha and mean > 0 and mean >= min_effect
        else "negative"
        if p < alpha and mean < 0
        else "abstain"
    )
    crit = _tinverse(1 - alpha / 2, df)
    se = math.sqrt(var / n)
    interval = [mean - crit * se, mean + crit * se]
    return {
        "verdict": verdict,
        "reason": None if verdict != "abstain" else "below_min_effect" if p < alpha else "not_significant",
        "n": n,
        "mean": mean,
        "p_value": p,
        "alpha": alpha,
        "confidence_level": 1 - alpha,
        "confidence_interval": interval,
        **({"ci95": interval} if alpha == 0.05 else {}),
        "statistical_test": "paired_two_sided_t",
    }


def _tpvalue(t, df):
    return _betai(df / 2, 0.5, df / (df + t * t))


def _tcdf(t, df):
    x = df / (df + t * t)
    return 1 - 0.5 * _betai(df / 2, 0.5, x)


def _tinverse(prob, df):
    lo, hi = 0.0, 1.0
    while _tcdf(hi, df) < prob:
        hi *= 2
    for _ in range(100):
        mid = (lo + hi) / 2
        if _tcdf(mid, df) < prob:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _betacf(a, b, x):
    qab = a + b
    qap = a + 1
    qam = a - 1
    c = 1
    d = 1 - qab * x / qap
    d = 1e-30 if abs(d) < 1e-30 else d
    d = 1 / d
    h = d
    for m in range(1, 201):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1 + aa * d
        d = 1e-30 if abs(d) < 1e-30 else d
        c = 1 + aa / c
        c = 1e-30 if abs(c) < 1e-30 else c
        d = 1 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1 + aa * d
        d = 1e-30 if abs(d) < 1e-30 else d
        c = 1 + aa / c
        c = 1e-30 if abs(c) < 1e-30 else c
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 3e-14:
            break
    return h


def _betai(a, b, x):
    if x <= 0:
        return 0
    if x >= 1:
        return 1
    bt = math.exp(
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log1p(-x)
    )
    return (
        bt * _betacf(a, b, x) / a
        if x < (a + 1) / (a + b + 2)
        else 1 - bt * _betacf(b, a, 1 - x) / b
    )


def verify_receipt(
    receipt, required_fields=("status", "input_sha256", "output_sha256"), verifier=None
):
    if not all(receipt.get(k) for k in required_fields):
        return False
    return bool(verifier and verifier(receipt))


def holm(pvalues, alpha=0.05):
    if not 0 < alpha < 1 or any(
        not math.isfinite(float(p)) or not 0 <= float(p) <= 1 for p in pvalues
    ):
        raise ValueError("invalid p-values or alpha")
    ordered = sorted(enumerate(pvalues), key=lambda x: x[1])
    out = {}
    passed = True
    for rank, (i, p) in enumerate(ordered):
        passed = passed and p <= alpha / (len(ordered) - rank)
        out[i] = passed
    return out


def bh(pvalues, alpha=0.05):
    if not 0 < alpha < 1 or any(
        not math.isfinite(float(p)) or not 0 <= float(p) <= 1 for p in pvalues
    ):
        raise ValueError("invalid p-values or alpha")
    ordered = sorted(enumerate(pvalues), key=lambda x: x[1])
    k = max(
        (
            rank
            for rank, (_, p) in enumerate(ordered, 1)
            if p <= alpha * rank / len(ordered)
        ),
        default=0,
    )
    return {i: (rank <= k) for rank, (i, _) in enumerate(ordered, 1)}
