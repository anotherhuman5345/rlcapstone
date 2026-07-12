"""Train a 1D CNN to classify EEG windows as ADHD vs Control.

Honesty notes:
  * The label is the child's clinical group, not a diagnosis the EEG "proves".
    This is pattern recognition on a small cohort, nothing more.
  * With only 121 subjects, the danger is learning to recognise individuals.
    So we (a) split by subject everywhere, including a subject-level validation
    slice carved out of the training subjects, and (b) report the SUBJECT-level
    score (average the window probabilities per subject) as the headline, since
    a per-window number is optimistic when one subject contributes many windows.

Trains on train-subject windows, monitors on held-out train subjects, and
reports the final numbers on the untouched test subjects.
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
PREP = ROOT / "data" / "adhd_eeg" / "prepared"
OUT = ROOT / "runs" / "adhd_eeg"
CLASSES = ["Control", "ADHD"]
N_CH = 19


class EEGNet1D(nn.Module):
    """Compact multi-channel 1D CNN. Input [B, 19, 256]."""

    def __init__(self, n_ch=N_CH, n_classes=2):
        super().__init__()

        def block(cin, cout, k=7):
            return nn.Sequential(
                nn.Conv1d(cin, cout, k, padding=k // 2),
                nn.BatchNorm1d(cout),
                nn.ReLU(inplace=True),
                nn.MaxPool1d(2),
            )

        self.features = nn.Sequential(
            block(n_ch, 32), block(32, 64), block(64, 128), block(128, 128),
        )
        self.head = nn.Sequential(
            nn.AdaptiveAvgPool1d(1), nn.Flatten(),
            nn.Dropout(0.4), nn.Linear(128, n_classes),
        )

    def forward(self, x):
        return self.head(self.features(x))


def load(name):
    d = np.load(PREP / f"{name}.npz", allow_pickle=True)
    return d["X"], d["y"], d["subj"].astype(str)


def subject_val_split(subj, y, frac=0.15, seed=0):
    """Hold out whole subjects (stratified by class) for validation."""
    rng = np.random.default_rng(seed)
    uniq = np.unique(subj)
    cls = {s: y[subj == s][0] for s in uniq}
    val = []
    for c in (0, 1):
        subs = sorted(s for s in uniq if cls[s] == c)
        subs = list(rng.permutation(subs))
        val += subs[:max(1, round(len(subs) * frac))]
    val = set(val)
    tr_mask = np.array([s not in val for s in subj])
    return tr_mask, ~tr_mask


def roc_auc(y_true, scores):
    order = np.argsort(scores)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(scores) + 1)
    pos = y_true == 1
    npos, nneg = pos.sum(), (~pos).sum()
    if npos == 0 or nneg == 0:
        return float("nan")
    return (ranks[pos].sum() - npos * (npos + 1) / 2) / (npos * nneg)


@torch.no_grad()
def probs_for(model, X, device, batch=512):
    model.eval()
    out = []
    for i in range(0, len(X), batch):
        xb = torch.from_numpy(X[i:i + batch]).to(device)
        out.append(torch.softmax(model(xb), 1)[:, 1].cpu().numpy())
    return np.concatenate(out)


def subject_scores(p_win, y_win, subj):
    """Aggregate window probs to one score + true label per subject."""
    uniq = np.unique(subj)
    ps = np.array([p_win[subj == s].mean() for s in uniq])
    ys = np.array([y_win[subj == s][0] for s in uniq])
    acc = ((ps >= 0.5).astype(int) == ys).mean()
    return acc, roc_auc(ys, ps), len(uniq)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"Device: {device}")

    Xtr_all, ytr_all, subtr_all = load("train")
    Xte, yte, subte = load("test")
    tr_mask, val_mask = subject_val_split(subtr_all, ytr_all, seed=args.seed)
    Xtr, ytr = Xtr_all[tr_mask], ytr_all[tr_mask]
    Xval, yval, subval = Xtr_all[val_mask], ytr_all[val_mask], subtr_all[val_mask]
    print(f"train {len(ytr)} win / {len(np.unique(subtr_all[tr_mask]))} subj   "
          f"val {len(yval)} win / {len(np.unique(subval))} subj   "
          f"test {len(yte)} win / {len(np.unique(subte))} subj")

    counts = np.bincount(ytr, minlength=2).astype(float)
    weights = torch.tensor(counts.sum() / (2 * counts), dtype=torch.float32).to(device)

    tr_loader = DataLoader(
        TensorDataset(torch.from_numpy(Xtr), torch.from_numpy(ytr)),
        batch_size=args.batch, shuffle=True, drop_last=True)

    model = EEGNet1D().to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, args.epochs)
    crit = nn.CrossEntropyLoss(weight=weights)

    history, best = [], -1.0
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

        pv = probs_for(model, Xval, device)
        win_acc = (((pv >= 0.5).astype(int)) == yval).mean()
        subj_acc, subj_auc, _ = subject_scores(pv, yval, subval)
        history.append({"epoch": epoch, "train_loss": total / len(ytr),
                        "val_win_acc": float(win_acc),
                        "val_subj_acc": float(subj_acc),
                        "val_subj_auc": float(subj_auc)})
        print(f"epoch {epoch:2d}  loss {total/len(ytr):.4f}  "
              f"val_win_acc {win_acc:.3f}  val_subj_acc {subj_acc:.3f}  "
              f"val_subj_auc {subj_auc:.3f}")
        if subj_acc > best:
            best = subj_acc
            torch.save(model.state_dict(), OUT / "adhd_best.pt")

    model.load_state_dict(torch.load(OUT / "adhd_best.pt"))
    pte = probs_for(model, Xte, device)
    win_acc = float((((pte >= 0.5).astype(int)) == yte).mean())
    win_auc = float(roc_auc(yte, pte))
    subj_acc, subj_auc, n_subj = subject_scores(pte, yte, subte)
    print("\n=== TEST (unseen subjects) ===")
    print(f"window-level : acc {win_acc:.3f}  auc {win_auc:.3f}")
    print(f"subject-level: acc {subj_acc:.3f}  auc {subj_auc:.3f}  ({n_subj} subjects)")

    report = {"classes": CLASSES, "history": history,
              "test": {"window_acc": win_acc, "window_auc": win_auc,
                       "subject_acc": float(subj_acc), "subject_auc": float(subj_auc),
                       "n_test_subjects": int(n_subj)}}
    (OUT / "adhd_report.json").write_text(json.dumps(report, indent=2))
    print(f"\nSaved model + report to {OUT}")


if __name__ == "__main__":
    main()
