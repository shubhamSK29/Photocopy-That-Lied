# PHOTOCOPY THAT LIED

AI-assisted image-integrity screening for crop-insurance claim photographs.

The system combines several deliberately weak forensic signals (copy-move, local
processing inconsistency, compression/resampling, visible timestamp) and reports
**Manipulation Evidence** and **Data Coverage** separately, together with the
regions, explanations and limitations a human reviewer needs.

It does **not** decide whether a claim is fraudulent, and it must not be used to
reject a claim automatically.

## What it reports

| Output | Meaning |
| --- | --- |
| Manipulation Evidence (0–100) | How much manipulation evidence was found under the system's tested conditions |
| Data Coverage (0–100) | How well the submitted image fits the conditions the system was tested on |
| Risk band | `No significant manipulation evidence` / `Review required` / `High-priority forensic review` |
| Detector status | `detected`, `not_detected`, `insufficient_evidence`, `not_applicable` |
| Heatmap / regions | Approximate forensic signal, not pixel-perfect proof |
| Timestamp integrity | EXIF timestamp and/or visible timestamp, never authenticated |
| Warnings and limitations | Including the false-positive caveats below |

Missing EXIF, compression and resizing are **not** treated as evidence of
manipulation. Where no timestamp evidence remains in the submitted image, the
system reports that verification is impossible rather than inventing one.

## Requirements

- Python 3.10+
- Node 20+ (frontend)
- Optional: `tesseract-ocr` for visible-timestamp OCR (the pipeline degrades to
  `not_applicable` when it is absent)

## Setup (Windows)

```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Optional: copy environment file
copy .env.example .env
```

## Setup (Linux/macOS)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # optional; defaults work out of the box
```

## Run the backend (Windows)

```powershell
.venv\Scripts\uvicorn backend.main:app --reload --port 8000
```

## Run the backend (Linux/macOS)

```bash
.venv/bin/uvicorn backend.main:app --reload --port 8000
```

- `POST /api/analyze` — upload an image and run the full pipeline
- `GET /api/analysis/{analysis_id}`
- `GET /api/report/{analysis_id}` (`?format=html` for a printable report)
- `GET /api/artifacts/{analysis_id}/{name}`
- `GET /api/health`

## Run the frontend (Windows)

```powershell
cd frontend
npm install
npm run dev
```

## Run the frontend (Linux/macOS)

```bash
cd frontend
npm install
npm run dev
```

## Demo dataset

No real claim photographs are shipped. `scripts/generate_dataset.py` renders a
clearly labelled **synthetic** dataset with per-device, per-session and
per-source grouping, natural-processing variants, hard negatives, copy-move,
splicing and timestamp-overlay examples:

### Windows
```powershell
.venv\Scripts\python scripts\generate_dataset.py --per-device 4
```

### Linux/macOS
```bash
.venv/bin/python scripts/generate_dataset.py --per-device 4
```

Synthetic data is a development aid only. Nothing measured on it should be
presented as real-world validation.

## Analysing images from the shell

### Windows
```powershell
.venv\Scripts\python scripts\run_analysis.py path\to\image.jpg
.venv\Scripts\python scripts\detector_sweep.py
```

### Linux/macOS
```bash
.venv/bin/python scripts/run_analysis.py path/to/image.jpg
.venv/bin/python scripts/detector_sweep.py      # detector behaviour over the demo dataset
```

## Demo mode

Until a fusion model is trained, the evidence score comes from a clearly
labelled deterministic fallback (`DEMO MODE`, `model_version =
fusion-demo-fallback`). It is never presented as a trained model.

## Training and evaluation

The generator writes a versioned manifest with parent/source/session groups.  Do
not replace a manifest in place when changing a dataset version.  The training
script splits by parent/source group and aborts if any group leaks across splits.

### Windows
```powershell
.venv\Scripts\python scripts\generate_dataset.py --per-device 4
.venv\Scripts\python scripts\train_model.py --manifest dataset\manifests\dataset.csv --output-dir models --dataset-version dataset-synthetic-v1
.venv\Scripts\python scripts\evaluate_model.py --manifest dataset\manifests\dataset.csv
.venv\Scripts\python scripts\run_ablation.py --manifest dataset\manifests\dataset.csv
.venv\Scripts\python -m pytest
```

### Linux/macOS
```bash
python scripts/generate_dataset.py --per-device 4
python scripts/train_model.py --manifest dataset/manifests/dataset.csv --output-dir models --dataset-version dataset-synthetic-v1
python scripts/evaluate_model.py --manifest dataset/manifests/dataset.csv
python scripts/run_ablation.py --manifest dataset/manifests/dataset.csv
pytest
```

Training saves a calibrated logistic-regression model, persisted feature schema,
metrics, ROC/confusion-matrix figures, and run metadata under `models/fusion-v1`.
Inference refuses to use a trained model when the current feature schema differs.
`reports/evaluations` and `reports/ablations` contain reproducible reports.

The included dataset is synthetic/demo only; its measurements are not claims of
performance on real claim photographs.

## Testing

### Backend tests (pytest)
```powershell
# Windows
.venv\Scripts\python -m pytest backend/tests/ -v

# Linux/macOS
.venv/bin/python -m pytest backend/tests/ -v
```

### Frontend tests
```powershell
# Windows
cd frontend
npm install  # Required first to install test dependencies
npm test

# Linux/macOS
cd frontend
npm install  # Required first to install test dependencies
npm test
```

**Note**: TypeScript may show "Cannot find module" errors for vitest and testing-library packages until `npm install` is run. These errors are expected in development environments where dependencies haven't been installed yet.

### Full test suite
```powershell
# Windows
.venv\Scripts\python -m pytest backend/tests/ -v
cd frontend
npm test
npm run build
```

## CI/CD

The project includes a GitHub Actions workflow (`.github/workflows/ci.yml`) that:

1. Runs backend pytest tests
2. Runs frontend tests and build
3. Validates the model pipeline
4. Checks for schema mismatches

This ensures code quality and reproducibility across different environments.
