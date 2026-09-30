# ade-integrity

Portable standard-library checks for canonical JSON seals, chained ledger rows,
paired result abstention, and external receipt structure. It does not import ADE,
create signatures, or establish independent human/model confirmation.

MIT licensed. Version 0.1.1. Install the wheel from the GitHub release or build from
this directory with `python -m pip install .`. There is no PyPI upload.

Run `python -m pip install pytest scipy` and `python -m pytest tests` to check a
source checkout. SciPy is optional and used only for numerical cross-checks. The
ADE ledger integration check skips when no ADE evidence checkout is present.

```python
import json
from pathlib import Path
from ade_integrity.core import verify_ledger, verify_seal, judge_paired
errors = verify_ledger("LEDGER.jsonl", tip_path="LEDGER.jsonl.tip")
for path in Path("prereg").glob("*.json"):
    seal = json.loads(path.read_text(encoding="utf-8"))
    expected = seal.pop("seal_sha256")
    assert verify_seal(seal, expected)
result = judge_paired([.10, .15, .08, .12, .19, .11], min_effect=.1)
```

The paired two-sided Student t test assumes independent paired units. It abstains
below six observations or at zero variance. `confidence_interval` uses the stated
`confidence_level`; `ci95` is supplied only for alpha=.05. Effect thresholds must
be chosen before observing results. Holm/BH accept the complete declared family.
The library checks bytes and numeric procedures; it cannot establish that units,
data sources, model families or human signatures are independent. A receipt needs
an application-supplied signature verifier; structural fields alone never pass.

The independent implementation is numerically cross-checked against SciPy in
`tests/ci_crosscheck.py`. SciPy is a test dependency only.

Version 0.1.1 fixes one-shot p-value iterators and safely abstains when the standard
error underflows. Canonical JSON rejects NaN and infinities. These cases were found
by a separate GPT cloud engineering audit of 0.1.0; it was not a scientific replication.
