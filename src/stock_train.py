"""Train an MLP to classify a stock's next-week risk (Low / Medium / High
realised volatility) from price + sentiment features.

Honest framing: this predicts VOLATILITY (how much a stock will move), not
DIRECTION (up or down). Volatility clusters in time, so it is genuinely more
predictable than returns — but this is still an educational model, not advice.

To answer "does the sentiment actually help?", we also train a price-only
model (same features minus the three sentiment ones) and report both test
accuracies side by side. A time-based validation slice (tail of the training
period) picks the checkpoint; the final numbers are on the later test period.
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
PREP = ROOT / "data" / "stock" / "prepared"
OUT = ROOT / "runs" / "stock"
CLASSES = ["Low", "Medium", "High"]
SENT_IDX = [8, 9, 10]  # sent_mean_5d, sent_count_5d, sent_last


class RiskMLP(nn.Module):
    def __init__(self, n_in, n_classes=3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_in, 64), nn.BatchNorm1d(64), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(64, 32), nn.BatchNorm1d(32), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(32, n_classes),
        )

    def forward(self, x):
        return self.net(x)


def load(name):
    d = np.load(PREP / f"{name}.npz")
    return d["X"].astype(np.float32), d["y"].astype(np.int64)


def evaluate(model, X, y, device):
    model.eval()
    with torch.no_grad():
        pred = model(torch.from_numpy(X).to(device)).argmax(1).cpu().numpy()
    cm = np.zeros((3, 3), int)
    for t, p in zip(y, pred):
        cm[t, p] += 1
    acc = float((pred == y).mean())
    recalls = [cm[i, i] / cm[i].sum() if cm[i].sum() else 0.0 for i in range(3)]
    f1s = []
    for i in range(3):
        prec = cm[i, i] / cm[:, i].sum() if cm[:, i].sum() else 0.0
        rec = recalls[i]
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return acc, float(np.mean(f1s)), recalls, cm


def train_model(Xtr, ytr, Xval, yval, cols, device, epochs, tag):
    Xtr, Xval = Xtr[:, cols], Xval[:, cols]
    counts = np.bincount(ytr, minlength=3).astype(float)
    w = torch.tensor(counts.sum() / (3 * counts), dtype=torch.float32).to(device)
    loader = DataLoader(TensorDataset(torch.from_numpy(Xtr), torch.from_numpy(ytr)),
                        batch_size=256, shuffle=True, drop_last=True)
    model = RiskMLP(len(cols)).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
    crit = nn.CrossEntropyLoss(weight=w)
    history, best, best_state = [], -1.0, None
    for ep in range(1, epochs + 1):
        model.train()
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            crit(model(xb), yb).backward()
            opt.step()
        acc, f1, _, _ = evaluate(model, Xval, yval, device)
        history.append({"epoch": ep, "val_acc": acc, "val_macro_f1": f1})
        if acc > best:
            best, best_state = acc, {k: v.clone() for k, v in model.state_dict().items()}
    model.load_state_dict(best_state)
    print(f"[{tag}] best val acc {best:.3f}")
    return model, history


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=80)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    torch.manual_seed(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    OUT.mkdir(parents=True, exist_ok=True)

    Xtr_all, ytr_all = load("train")
    Xte, yte = load("test")
    # time-based val = last 15% of the (already chronological) train rows
    cut = int(len(Xtr_all) * 0.85)
    Xtr, ytr = Xtr_all[:cut], ytr_all[:cut]
    Xval, yval = Xtr_all[cut:], ytr_all[cut:]
    print(f"train {len(ytr)}  val {len(yval)}  test {len(yte)}")

    all_cols = list(range(Xtr_all.shape[1]))
    price_cols = [c for c in all_cols if c not in SENT_IDX]

    full, hist = train_model(Xtr, ytr, Xval, yval, all_cols, device, args.epochs, "full")
    price, _ = train_model(Xtr, ytr, Xval, yval, price_cols, device, args.epochs, "price-only")

    acc_f, f1_f, rec_f, cm_f = evaluate(full, Xte[:, all_cols], yte, device)
    acc_p, f1_p, _, _ = evaluate(price, Xte[:, price_cols], yte, device)
    print("\n=== TEST (later period, unseen) ===")
    print(f"full (price+sentiment): acc {acc_f:.3f}  macro-F1 {f1_f:.3f}")
    print(f"price-only            : acc {acc_p:.3f}")
    print(f"sentiment lift        : {(acc_f - acc_p) * 100:+.1f} pts")
    print("per-class recall:", {CLASSES[i]: round(rec_f[i], 3) for i in range(3)})
    print("confusion matrix (rows=true, cols=pred):")
    for i in range(3):
        print(f"  {CLASSES[i]:7s} " + "  ".join(f"{cm_f[i,j]:5d}" for j in range(3)))

    torch.save(full.state_dict(), OUT / "stock_best.pt")
    report = {"classes": CLASSES, "history": hist,
              "test": {"full_acc": acc_f, "full_macro_f1": f1_f,
                       "price_only_acc": acc_p,
                       "sentiment_lift_pts": round((acc_f - acc_p) * 100, 2),
                       "recall": {CLASSES[i]: rec_f[i] for i in range(3)},
                       "confusion_matrix": cm_f.tolist()},
              "chance": round(1 / 3, 3)}
    (OUT / "stock_report.json").write_text(json.dumps(report, indent=2))
    print(f"\nSaved model + report to {OUT}")


if __name__ == "__main__":
    main()
