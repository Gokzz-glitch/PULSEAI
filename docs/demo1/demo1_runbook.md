# Demo 1 Runbook

## Goal
Execute a deterministic 5-minute simulation with 4 fixed scenarios and produce presentation-ready evidence files.

## Steps
1. Open Demo_1_Simulated_4Case_5Min.ipynb in Colab or VS Code Jupyter.
2. Run all cells in order.
3. Verify generated artifacts under docs/demo1/.
4. Copy key outputs into pitch materials.

## Validation Criteria
- Total duration modeled: 300 seconds
- Sampling rate: 500 Hz
- Per-case duration: 75 seconds
- Exactly 4 cases processed

## Troubleshooting
- If matplotlib plot fails to render, rerun the plotting cell once.
- If file save fails, check write permission for docs/demo1/.
- If package import fails in Colab, install missing package and rerun.
