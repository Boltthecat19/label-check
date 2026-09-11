# Label Check

Compares an alcohol label image to the fields on its COLA application and reports, field by field, whether they match. Runs entirely on the machine it is installed on: no cloud APIs, no accounts, nothing stored after the check. One label takes about a second on a laptop CPU.

Built as a take-home prototype for the TTB label review workflow. Not affiliated with TTB.

## Run it

Requires Docker.

```
docker compose up
```

Open http://localhost:8081. That is the complete offline app: OCR plus rule based checks.

To add the optional local AI second opinion (a small language model that comments on borderline rows), download the model once and start the profile:

```
./tools/get_model.sh                       # about 1 GB, one time
LLM_BASE_URL=http://llm:8080/v1 docker compose --profile llm up
```

Nothing leaves the machine in either mode.

## Use it

**One label.** Type the application fields into Step 1, choose the label image in Step 2, press the button. You get one row per field: PASS, REVIEW, or FAIL, with what the application said, what the label said, and a note. REVIEW means the tool is not sure and an agent should look. The time taken is shown on every result.

**Many labels.** Open "Many labels". Choose a CSV with one row per application and a folder of images, and the tool checks them all and gives you a table and a CSV download.

CSV columns: `application_id, image, brand, class_type, abv_percent, net_contents, bottler, is_import, origin_country, beverage_type`. Only `brand` and `image` are required. `image` is the file name of that row's label. `is_import` is yes or no. `beverage_type` is spirits, wine, or beer. A sample sheet and images are produced by the test label generator (below).

## What it checks

| Field | How |
|---|---|
| Brand name | Case and punctuation ignored. Every word of the brand must appear on one line of the label to pass. Close spellings go to REVIEW. |
| Alcohol content | Reads the percent and the proof if present; proof must be twice the percent. Missing on spirits fails; missing on beer or wine goes to REVIEW because exemptions exist. |
| Net contents | Reads mL, L, cL, or fl oz and compares in millilitres. |
| Bottler or producer | Name must match and a "bottled by" style phrase must be present. |
| Country of origin | Only checked when the application marks an import. |
| Government warning | Must be present, the header must read GOVERNMENT WARNING: in capitals, and the wording must be exact. Single letter OCR misreads go to REVIEW; changed words fail. Bold cannot be seen by OCR and the result says so. |

## Run the tests

```
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python tools/make_labels.py tests/fixtures     # renders 100 synthetic labels
.venv/bin/pytest
```

The synthetic set is 20 labels across spirits, wine, and beer, half correct and half with one seeded defect each, times five photo conditions: clean, rotated, blurred, glare, and heavy JPEG compression. Tests assert every clean label gets the right verdict, no defect is ever passed on a noisy photo, and the 95th percentile time stays under five seconds.

## Deployed prototype

URL: to be added at deployment.

## Limitations

See APPROACH.md for the decisions, the tradeoffs, and what a production version would need.
