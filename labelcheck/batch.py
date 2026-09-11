"""Batch verification: many applications from a CSV, images matched by filename.

Jobs run in a background thread and live in memory for an hour. Nothing is written to
disk, which is Marcus's "don't store anything sensitive" rule, and it means a restart
drops in flight batches. Documented as a prototype limitation.
"""

import csv
import io
import threading
import time
import uuid

from pydantic import BaseModel, Field

from labelcheck.models import Application, Verdict
from labelcheck.verify import verify

TTL_SECONDS = 3600
CSV_COLUMNS = [
    "application_id", "image", "brand", "class_type", "abv_percent", "net_contents",
    "bottler", "is_import", "origin_country", "beverage_type",
]
_TRUE = {"yes", "true", "1", "y"}


class BatchJob(BaseModel):
    id: str
    total: int
    done: int = 0
    verdicts: list[Verdict] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)

    @property
    def finished(self) -> bool:
        return self.done >= self.total


def parse_csv(data: bytes) -> list[Application]:
    text = data.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        raise ValueError("The spreadsheet has no rows.")
    missing = [c for c in ("brand", "image") if c not in rows[0]]
    if missing:
        raise ValueError(f"The spreadsheet is missing required columns: {', '.join(missing)}.")
    apps = []
    for i, r in enumerate(rows, start=2):
        abv = (r.get("abv_percent") or "").strip()
        try:
            abv_val = float(abv) if abv else None
        except ValueError as e:
            raise ValueError(f"Row {i}: alcohol content '{abv}' is not a number.") from e
        apps.append(Application(
            application_id=(r.get("application_id") or f"row{i}").strip(),
            image=(r.get("image") or "").strip(),
            brand=(r.get("brand") or "").strip(),
            class_type=(r.get("class_type") or "").strip(),
            abv_percent=abv_val,
            net_contents=(r.get("net_contents") or "").strip(),
            bottler=(r.get("bottler") or "").strip(),
            is_import=(r.get("is_import") or "").strip().lower() in _TRUE,
            origin_country=(r.get("origin_country") or "").strip(),
            beverage_type=(r.get("beverage_type") or "spirits").strip().lower() or "spirits",
        ))
    return apps


class BatchStore:
    def __init__(self) -> None:
        self._jobs: dict[str, BatchJob] = {}
        self._lock = threading.Lock()

    def evict(self) -> None:
        cutoff = time.time() - TTL_SECONDS
        with self._lock:
            for k in [k for k, j in self._jobs.items() if j.created_at < cutoff]:
                del self._jobs[k]

    def get(self, job_id: str) -> BatchJob | None:
        return self._jobs.get(job_id)

    def create(self, apps: list[Application], images: dict[str, bytes], llm=None) -> str:
        self.evict()
        job = BatchJob(id=uuid.uuid4().hex[:12], total=len(apps))
        with self._lock:
            self._jobs[job.id] = job
        threading.Thread(target=self._run, args=(job, apps, images, llm), daemon=True).start()
        return job.id

    def _run(self, job: BatchJob, apps: list[Application], images: dict[str, bytes], llm) -> None:
        for app in apps:
            data = images.get(app.image)
            if data is None:
                job.errors.append(f"{app.application_id}: image '{app.image}' was not uploaded.")
                job.verdicts.append(Verdict(application_id=app.application_id, warnings=["Image not uploaded."]))
            else:
                try:
                    job.verdicts.append(verify(app, data, llm=llm))
                except Exception:
                    job.errors.append(f"{app.application_id}: could not read image '{app.image}'.")
                    job.verdicts.append(Verdict(application_id=app.application_id, warnings=["Could not read the image."]))
            job.done += 1


def export_csv(job: BatchJob) -> str:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["application_id", "overall", "brand", "abv", "net_contents", "bottler", "origin", "warning", "processing_ms", "notes"])
    for v in job.verdicts:
        by = {r.field: r for r in v.results}
        notes = "; ".join(f"{f}: {by[f].note}" for f in by if by[f].note and by[f].status != "PASS")
        w.writerow([v.application_id, v.overall.value if v.results else "ERROR"]
                   + [by[f].status.value if f in by else "" for f in ("brand", "abv", "net_contents", "bottler", "origin", "warning")]
                   + [v.processing_ms, notes or "; ".join(v.warnings)])
    return out.getvalue()
