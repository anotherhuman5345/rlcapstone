# CAPSTONE — AI Visual Recognition Project

AI capstone project focused on visual recognition, model training, and learning materials.

## Hardware
- NVIDIA GeForce RTX 5060 Ti (8 GB VRAM, Blackwell architecture)
- 32 GB RAM, Windows 11 Pro

## Environment setup
Python 3.12 virtual environment lives in `.venv/`. PyTorch is the CUDA 12.8 build
(required for Blackwell GPUs — the default PyPI build will not see the GPU).

```powershell
# Activate the environment
.venv\Scripts\Activate.ps1

# Recreate from scratch if needed
python -m venv .venv
.venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Project layout
- `src/` — application and training code
- `scripts/` — one-off utilities (env checks, data prep)
- `notebooks/` — Jupyter notebooks for experiments and learning
- `data/` — datasets (git-ignored)
- `models/` — trained weights (git-ignored)

## Verify the GPU works
```powershell
.venv\Scripts\python.exe scripts\check_gpu.py
```
