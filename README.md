# ODRM-Copilot (Syngas Shovel)

AI-driven Surrogate Process & Optimization Model for Flare Gas Valorization. Built to democratize advanced process simulation (Aspen HYSYS/COMSOL) for the Global South.

This is a B2B SaaS platform using AI and Surrogate models to optimize Oxy-Dry Reforming of Methane (ODRM) for flare gas valorization, predicting syngas yields, carbon deposition risks, and techno-economic ROI.

## Local development

Requires Python 3.11.x. Run these from the repository root in PowerShell.

```powershell
# Install backend + dev dependencies into the project venv
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

# Test, lint, and type-check
.\.venv\Scripts\python.exe -m pytest backend/tests -q
.\.venv\Scripts\python.exe -m ruff check backend scripts
.\.venv\Scripts\python.exe -m mypy backend/src scripts

# Generate the deterministic v1 dataset
.\.venv\Scripts\python.exe scripts\generate_odrm_data.py --n 10000 --seed 7
```

The generator validates every row, then writes an immutable Parquet batch and
manifest under `data/processed/odrm/v1/` plus a byte-identical roadmap copy at
`data/odrm_dataset.parquet`. Both are reproducible from the committed generator,
seed, and schema contract, and are gitignored by default.

> The v1 dataset is **synthetic**: it comes from a reduced-order reaction-extent
> model, not experimental, Aspen HYSYS, or COMSOL output. See
> [`docs/SPRINT_1_REPORT.md`](docs/SPRINT_1_REPORT.md) for limitations.
