# Pattern Generator Demo (standalone)

Local demo: spray **image/GIF → bullet points → `(dx, dy, delay)` → Lua-ready steps**.

Not a public AimSync release — standalone tool for explaining / testing the workflow.

## Run

```bat
run.bat
```

Or manually:

```bat
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python app.py
```

Open **http://127.0.0.1:5055**

## Quick demo

1. Click **Load sample AK GIF**
2. Review suggested points (edit with click / right-click undo)
3. **Generate Pattern**
4. Copy CSV or Lua sketch

## What it shows

| Step | Meaning |
|------|---------|
| Detect still | Dark blobs, heuristic order (top→bottom) |
| Detect GIF | Frame-diff centroids ≈ shot order |
| Manual edit | You own the final order |
| Generate | `dx,dy = (P_i - P_{i-1}) * scale * invert` |
| Lua sketch | `MoveMouseRelativeFractional(dx * kava * SensSetting, …)` |

## Folder

```
PatternGenerator-Demo/
├── app.py
├── engine.py
├── requirements.txt
├── run.bat
├── samples/weapon_ak47.gif
├── static/
└── templates/
```
