"""Turn the ADHD/Control EEG CSV into per-subject windowed samples.

The dataset (Nasrabadi et al., via Kaggle) is one long CSV: each row is one
128 Hz time sample with 19 EEG channels, a Class (ADHD/Control) and a subject
ID. Recordings are a visual-attention task.

Pipeline:
  1. Group rows by subject; every subject has one class.
  2. Split SUBJECTS into train/test (stratified by class, fixed seed) — never
     split by window, or the model learns to recognise people, not ADHD.
  3. Cut each subject's [T, 19] signal into non-overlapping WINDOW-sample
     windows, z-normalise each channel within the window.
  4. Save X [n, 19, WINDOW], y [n], and the per-window subject id (so we can
     score at the subject level, not just per window).

Output: data/adhd_eeg/prepared/{train,test}.npz + meta.json
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "adhd_eeg" / "adhdata.csv"
DEST = ROOT / "data" / "adhd_eeg" / "prepared"

CHANNELS = ["Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4", "O1", "O2",
            "F7", "F8", "T7", "T8", "P7", "P8", "Fz", "Cz", "Pz"]
FS = 128
WINDOW = 256          # 2 seconds
TEST_FRAC = 0.2
SEED = 0
CLASSES = ["Control", "ADHD"]   # index 0 / 1


def split_subjects(subject_class: dict[str, str]):
    rng = np.random.default_rng(SEED)
    train, test = [], []
    for cls in CLASSES:
        subs = sorted(s for s, c in subject_class.items() if c == cls)
        subs = list(rng.permutation(subs))
        k = max(1, round(len(subs) * TEST_FRAC))
        test += subs[:k]
        train += subs[k:]
    return set(train), set(test)


def windows_for_subject(sig: np.ndarray):
    """sig: [T, 19] -> list of [19, WINDOW] z-normalised windows."""
    out = []
    n = (len(sig) // WINDOW) * WINDOW
    for start in range(0, n, WINDOW):
        w = sig[start:start + WINDOW].T.astype(np.float32)   # [19, WINDOW]
        mu = w.mean(axis=1, keepdims=True)
        sd = w.std(axis=1, keepdims=True)
        sd[sd < 1e-6] = 1.0
        out.append((w - mu) / sd)
    return out


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    print(f"Loading {CSV} ...")
    df = pd.read_csv(CSV)
    subject_class = df.groupby("ID")["Class"].first().to_dict()
    train_subs, test_subs = split_subjects(subject_class)
    print(f"Subjects: {len(subject_class)}  "
          f"train {len(train_subs)}  test {len(test_subs)}")

    splits = {"train": ([], [], []), "test": ([], [], [])}  # X, y, subj
    for sid, sub in df.groupby("ID"):
        cls_idx = CLASSES.index(subject_class[sid])
        sig = sub[CHANNELS].to_numpy(dtype=np.float32)
        wins = windows_for_subject(sig)
        which = "test" if sid in test_subs else "train"
        X, y, subj = splits[which]
        X.extend(wins)
        y.extend([cls_idx] * len(wins))
        subj.extend([sid] * len(wins))

    meta = {"channels": CHANNELS, "fs": FS, "window": WINDOW,
            "classes": CLASSES, "test_frac": TEST_FRAC,
            "train_subjects": sorted(train_subs),
            "test_subjects": sorted(test_subs)}
    for name in ("train", "test"):
        X, y, subj = splits[name]
        Xa = np.asarray(X, dtype=np.float32)
        ya = np.asarray(y, dtype=np.int64)
        np.savez_compressed(DEST / f"{name}.npz", X=Xa, y=ya, subj=np.array(subj))
        n_adhd = int((ya == 1).sum())
        meta[f"{name}_windows"] = len(ya)
        meta[f"{name}_dist"] = {"Control": int((ya == 0).sum()), "ADHD": n_adhd}
        print(f"{name}: {len(ya)} windows  X{Xa.shape}  "
              f"Control {int((ya==0).sum())}  ADHD {n_adhd}")

    (DEST / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"Saved to {DEST}")


if __name__ == "__main__":
    main()
