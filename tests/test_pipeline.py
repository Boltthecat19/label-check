"""Accuracy and timing on the synthetic label set."""

import json
import statistics
from pathlib import Path

import pytest

from labelcheck.models import Application, Status
from labelcheck.verify import verify

FIX = Path(__file__).parent / "fixtures"
pytestmark = pytest.mark.timeout(600)


@pytest.fixture(scope="module")
def manifest():
    mf = FIX / "manifest.json"
    if not mf.exists() or any(not (FIX / m["file"]).exists() for m in json.loads(mf.read_text())):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from tools.make_labels import main
        main(FIX)
    return json.loads(mf.read_text())


@pytest.fixture(scope="module")
def verdicts(manifest):
    out = []
    for m in manifest:
        app = Application(**m["application"])
        v = verify(app, (FIX / m["file"]).read_bytes())
        out.append((m, v))
    return out


def _misses(pairs):
    rows = []
    for m, v in pairs:
        by = {r.field: r.status for r in v.results}
        expected_fields = {**{f: Status.PASS for f in by if by[f] != Status.NOT_CHECKED}, **{k: Status(s) for k, s in m["expect"].items()}}
        if v.overall != Status(m["overall"]):
            rows.append((m["file"], "overall", m["overall"], v.overall))
        for f, exp in expected_fields.items():
            if f in by and by[f] != exp:
                rows.append((m["file"], f, exp, by[f]))
    return rows


def test_clean_labels_exact(verdicts):
    clean = [(m, v) for m, v in verdicts if m["variant"] == "clean"]
    misses = _misses(clean)
    assert not misses, "\n".join(f"{f}: {fld} expected {e} got {g}" for f, fld, e, g in misses)


def test_augmented_no_false_pass_and_accuracy(verdicts):
    aug = [(m, v) for m, v in verdicts if m["variant"] != "clean"]
    # A defect the clean label expects to FAIL must never come back PASS on a noisy image.
    false_pass = [(m["file"], f) for m, v in aug for f, s in m["expect"].items()
                  if s == "FAIL" and next(r.status for r in v.results if r.field == f) == Status.PASS]
    assert not false_pass, false_pass
    ok = sum(1 for m, v in aug if v.overall == Status(m["overall"]))
    acc = ok / len(aug)
    misses = _misses(aug)
    assert acc >= 0.8, f"augmented accuracy {acc:.2f}\n" + "\n".join(f"{f}: {fld} expected {e} got {g}" for f, fld, e, g in misses[:30])


def test_timing_p95_under_5s(verdicts):
    ms = sorted(v.processing_ms for _, v in verdicts)
    p95 = ms[int(len(ms) * 0.95) - 1]
    print(f"\nprocessing ms: median {statistics.median(ms):.0f} p95 {p95} max {ms[-1]} n={len(ms)}")
    assert p95 < 5000
