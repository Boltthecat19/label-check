# Label Check

Checks an alcohol label image against its COLA application, field by field, in about a second. Runs entirely on the machine it is installed on. No cloud calls, no accounts, nothing kept after the check.

Prototype for the TTB label review workflow. Not affiliated with TTB.

## Run

```
docker compose up
```

Open http://localhost:8081.

Optional local AI second opinion on borderline rows (a small language model, about 1 GB, still nothing leaves the machine):

```
./tools/get_model.sh
LLM_BASE_URL=http://llm:8080/v1 docker compose --profile llm up
```

## Use

**One label.** Enter the application fields, choose the label image, press the button. One row per field: PASS, REVIEW, or FAIL, with what the application said, what the label said, and why. REVIEW means an agent should look.

**Many labels.** Upload a CSV and the images it names. You get a table and a CSV download.

CSV columns: `application_id, image, brand, class_type, abv_percent, net_contents, bottler, is_import, origin_country, beverage_type`. Only `brand` and `image` are required. `is_import` is yes or no. `beverage_type` is spirits, wine, or beer.

## Checks

| Field | Rule |
|---|---|
| Brand | Case and punctuation ignored. Every word must appear on one label line. Near spellings are REVIEW. |
| Alcohol content | Percent, plus proof if shown; proof must be twice the percent. Missing fails on spirits, REVIEW on beer and wine. |
| Net contents | mL, L, cL, or fl oz, compared in millilitres. |
| Bottler | Name must match and a "bottled by" style phrase must be present. |
| Country of origin | Checked only for imports. |
| Government warning | Present, header in capitals, wording exact. One letter OCR slips are REVIEW; changed words fail. Bold cannot be seen by OCR and the result says so. |

## Tests

```
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python tools/make_labels.py tests/fixtures
.venv/bin/pytest
```

100 synthetic labels: 20 applications, half with a seeded defect, under five photo conditions (clean, rotated, blurred, glare, heavy JPEG). Tests require every clean label to get the right verdict, no defect to pass on a noisy photo, and 95th percentile time under five seconds.

## Deployed prototype

https://boltsplex.tail99f1df.ts.net:8443 (prototype hosting on a home server behind Tailscale Funnel; the same Compose file runs anywhere Docker does).

## Design and limits

See APPROACH.md.
