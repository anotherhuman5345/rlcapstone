"""Train a 1D CNN to classify MIT-BIH heartbeats into 4 AAMI classes.

Why this is not just "maximise accuracy": ~90% of beats are normal, so a model
that predicts "N" every time already scores ~90%. What matters clinically is
recall on the rare classes (S, V, F). We therefore:
  * weight the loss by inverse class frequency, and
  * select the best checkpoint by MACRO recall (mean per-class recall), not
    overall accuracy, and report a full per-class breakdown + confusion matrix.

Trains on DS1, reports on the patient-independent DS2 test set. A small
stratified slice of DS1 is held out purely for per-epoch monitoring / the
progress chart; final numbers come from DS2.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parents[1]
PREP = ROOT / "data" / "mitbih" / "prepared"
OUT = ROOT / "runs" / "ecg"
CLASSES = ["N", "S", "V", "F"]


class ECGNet(nn.Module):
    """Compact 1D CNN: 4 conv blocks -> global pool -> FC. ~ small enough for
    on-device / in-browser inference."""

    def __init__(self, n_classes: int = 4):
        super().__init__()

        def block(cin, cout):
            return nn.Sequential(
                nn.Conv1d(cin, cout, kernel_size=7, padding=3),
                nn.BatchNorm1d(cout),
                nn.ReLU(inplace=True),
                nn.MaxPool1d(2),
            )

        self.features = nn.Sequential(
            block(1, 16), block(16, 32), block(32, 64), block(64, 128),
        )
        self.head = nn.Sequential(
            nn.AdaptiveAvgPool1d(1),
            nn.Flatten(),
            nn.Dropout(0.3),
            nn.Linear(128, n_classes),
        )

    def forward(self, x):
        return self.head(self.features(x))


def load_npz(name):
    d = np.load(PREP / name)
    X = torch.from_numpy(d["X"]).unsqueeze(1)  # [n, 1, window]
    y = torch.from_numpy(d["y"])
    return X, y


def stratified_val_split(X, y, frac=0.1, seed=0):
    g = torch.Generator().manual_seed(seed)
    val_idx, tr_idx = [], []
    for c in y.unique():
        idx = (y == c).nonzero(as_tuple=True)[0]
        idx = idx[torch.randperm(len(idx), generator=g)]
        k = max(1, int(len(idx) * frac))
        val_idx.append(idx[:k])
        tr_idx.append(idx[k:])
    return torch.cat(tr_idx), torch.cat(val_idx)


@torch.no_grad()
def evaluate(model, loader, device, n_classes=4):
    model.eval()
    cm = torch.zeros(n_classes, n_classes, dtype=torch.long)
    for xb, yb in loader:
        pred = model(xb.to(device)).argmax(1).cpu()
        for t, p in zip(yb, pred):
            cm[t, p] += 1
    recalls = []
    for c in range(n_classes):
        denom = cm[c].sum().item()
        recalls.append(cm[c, c].item() / denom if denom else 0.0)
    acc = cm.diag().sum().item() / cm.sum().item()
    return acc, recalls, cm


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--batch", type=int, default=256)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"Device: {device}")

    Xtr_all, ytr_all = load_npz("train.npz")
    Xte, yte = load_npz("test.npz")
    tr_idx, val_idx = stratified_val_split(Xtr_all, ytr_all, seed=args.seed)
    Xtr, ytr = Xtr_all[tr_idx], ytr_all[tr_idx]
    Xval, yval = Xtr_all[val_idx], ytr_all[val_idx]
    print(f"train {len(ytr)}  val {len(yval)}  test {len(yte)}")

    # inverse-frequency class weights from the training slice
    counts = torch.bincount(ytr, minlength=len(CLASSES)).float()
    weights = (counts.sum() / (len(CLASSES) * counts)).to(device)
    print("class counts:", counts.tolist())
    print("loss weights:", [round(w, 2) for w in weights.tolist()])

    tr_loader = DataLoader(TensorDataset(Xtr, ytr), batch_size=args.batch,
                           shuffle=True, drop_last=True)
    val_loader = DataLoader(TensorDataset(Xval, yval), batch_size=512)
    te_loader = DataLoader(TensorDataset(Xte, yte), batch_size=512)

    model = ECGNet(len(CLASSES)).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, args.epochs)
    crit = nn.CrossEntropyLoss(weight=weights)

    history = []
    best_macro = -1.0
    for epoch in range(1, args.epochs + 1):
        model.train()
        total = 0.0
        for xb, yb in tr_loader:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            loss = crit(model(xb), yb)
            loss.backward()
            opt.step()
            total += loss.item() * len(xb)
        sched.step()

        acc, recalls, _ = evaluate(model, val_loader, device)
        macro = float(np.mean(recalls))
        history.append({
            "epoch": epoch, "train_loss": total / len(ytr),
            "val_acc": acc, "val_macro_recall": macro,
            "val_recall": {CLASSES[i]: recalls[i] for i in range(len(CLASSES))},
        })
        rec_str = "  ".join(f"{CLASSES[i]}:{recalls[i]:.2f}" for i in range(len(CLASSES)))
        print(f"epoch {epoch:2d}  loss {total/len(ytr):.4f}  "
              f"val_acc {acc:.4f}  macro_recall {macro:.4f}  [{rec_str}]")

        if macro > best_macro:
            best_macro = macro
            torch.save(model.state_dict(), OUT / "ecg_best.pt")

    # final report on the patient-independent DS2 test set
    model.load_state_dict(torch.load(OUT / "ecg_best.pt"))
    acc, recalls, cm = evaluate(model, te_loader, device)
    macro = float(np.mean(recalls))
    print("\n=== DS2 TEST (patient-independent) ===")
    print(f"accuracy {acc:.4f}   macro-recall {macro:.4f}")
    for i, c in enumerate(CLASSES):
        print(f"  {c}: recall {recalls[i]:.3f}")
    print("confusion matrix (rows=true, cols=pred):")
    print("     " + "  ".join(f"{c:>6}" for c in CLASSES))
    for i, c in enumerate(CLASSES):
        print(f"  {c}  " + "  ".join(f"{cm[i,j].item():6d}" for j in range(len(CLASSES))))

    report = {
        "classes": CLASSES,
        "history": history,
        "test": {
            "accuracy": acc, "macro_recall": macro,
            "recall": {CLASSES[i]: recalls[i] for i in range(len(CLASSES))},
            "confusion_matrix": cm.tolist(),
        },
    }
    (OUT / "ecg_report.json").write_text(json.dumps(report, indent=2))
    print(f"\nSaved model + report to {OUT}")


if __name__ == "__main__":
    main()
