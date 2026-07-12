"""Turn raw MIT-BIH records into beat windows labelled by AAMI class.

Pipeline:
  1. Read each record's MLII lead (the standard lead used in the literature)
     and its .atr beat annotations.
  2. Map each beat's annotation symbol to one of the 5 AAMI classes.
  3. Cut a fixed window centred on every beat's R-peak.
  4. Split BY PATIENT (not by beat) so no subject appears in both train and
     test — otherwise the model cheats by memorising a person's beat shape.

Output: data/mitbih/prepared/{train,test}.npz with X [n, WINDOW] float32 and
y [n] int64, plus meta.json.

AAMI groups the ~19 MIT-BIH beat symbols into superclasses. We use the 4 that
the standard inter-patient protocol evaluates (the 5th, Q = paced/unknown, is
dropped: its beats come almost entirely from the 4 paced records that this
protocol excludes, leaving only a handful of examples — not learnable and not
part of the published benchmark):
  N  - normal + bundle-branch blocks (N, L, R, e, j)
  S  - supraventricular ectopic       (A, a, J, S)
  V  - ventricular ectopic            (V, E)
  F  - fusion of ventricular + normal (F)
Non-beat annotations (rhythm marks, noise, etc.) and Q-class beats are ignored.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
import wfdb

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "mitbih"
DEST = SRC / "prepared"

FS = 360               # MIT-BIH sampling rate (Hz)
WINDOW = 260           # samples per beat (~0.72 s), R-peak centred
HALF = WINDOW // 2

# Standard "inter-patient" (DS1 train / DS2 test) split from Chazal et al. 2004,
# which the ECG literature uses so results are comparable. The 4 paced records
# (102, 104, 107, 217) are conventionally excluded.
DS1_TRAIN = [101, 106, 108, 109, 112, 114, 115, 116, 118, 119, 122, 124,
             201, 203, 205, 207, 208, 209, 215, 220, 223, 230]
DS2_TEST = [100, 103, 105, 111, 113, 117, 121, 123, 200, 202, 210, 212,
            213, 214, 219, 221, 222, 228, 231, 232, 233, 234]

CLASSES = ["N", "S", "V", "F"]
SYMBOL_TO_CLASS = {
    "N": "N", "L": "N", "R": "N", "e": "N", "j": "N",
    "A": "S", "a": "S", "J": "S", "S": "S",
    "V": "V", "E": "V",
    "F": "F",
}
CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}


def lead_index(header, want=("MLII", "II", "ML2")) -> int:
    names = [s.upper() for s in header.sig_name]
    for w in want:
        if w.upper() in names:
            return names.index(w.upper())
    return 0  # fall back to first lead


def beats_from_record(record_id: int):
    rec_path = str(SRC / str(record_id))
    rec = wfdb.rdrecord(rec_path)
    ann = wfdb.rdann(rec_path, "atr")
    li = lead_index(rec)
    sig = rec.p_signal[:, li].astype(np.float32)

    windows, labels = [], []
    for sample, symbol in zip(ann.sample, ann.symbol):
        cls = SYMBOL_TO_CLASS.get(symbol)
        if cls is None:
            continue
        start, end = sample - HALF, sample + HALF
        if start < 0 or end > len(sig):
            continue
        w = sig[start:end]
        # per-beat z-normalisation: robust to baseline wander / gain differences
        mu, sd = w.mean(), w.std()
        w = (w - mu) / sd if sd > 1e-6 else w - mu
        windows.append(w.astype(np.float32))
        labels.append(CLASS_TO_IDX[cls])
    return windows, labels


def build_split(record_ids: list[int]):
    X, y = [], []
    for rid in record_ids:
        if not (SRC / f"{rid}.hea").exists():
            print(f"  ! missing record {rid}, skipping")
            continue
        w, l = beats_from_record(rid)
        X.extend(w)
        y.extend(l)
        print(f"  record {rid}: {len(w)} beats")
    return np.asarray(X, dtype=np.float32), np.asarray(y, dtype=np.int64)


def summarise(name, y):
    counts = Counter(y.tolist())
    dist = {CLASSES[i]: int(counts.get(i, 0)) for i in range(len(CLASSES))}
    print(f"{name}: {len(y)} beats  {dist}")
    return dist


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    print("Building train split (DS1):")
    Xtr, ytr = build_split(DS1_TRAIN)
    print("Building test split (DS2):")
    Xte, yte = build_split(DS2_TEST)

    tr_dist = summarise("TRAIN", ytr)
    te_dist = summarise("TEST", yte)

    np.savez_compressed(DEST / "train.npz", X=Xtr, y=ytr)
    np.savez_compressed(DEST / "test.npz", X=Xte, y=yte)
    meta = {
        "fs": FS, "window": WINDOW, "classes": CLASSES,
        "train_records": DS1_TRAIN, "test_records": DS2_TEST,
        "train_dist": tr_dist, "test_dist": te_dist,
        "train_n": int(len(ytr)), "test_n": int(len(yte)),
    }
    (DEST / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"\nSaved to {DEST}")


if __name__ == "__main__":
    main()
