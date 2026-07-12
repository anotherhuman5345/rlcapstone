"""Build feature vectors + risk labels for the stock volatility predictor.

For each (ticker, trading day t) we build a fixed feature vector from data up to
and INCLUDING day t (never the future), combining price features and the news
sentiment signal. The label is the realised volatility over the NEXT H trading
days, bucketed into Low / Medium / High by terciles.

No-lookahead guarantees:
  * every feature uses only days <= t;
  * the label uses days t+1..t+H;
  * the train/test split is by time with a gap >= H days, so no test label
    window overlaps the training period.

Normalisation (z-score) uses TRAIN statistics only. We ship already-normalised
feature vectors, so the browser/app demo just feeds the stored vector — no
client-side scaling to get wrong. Output: data/stock/prepared/{train,test}.npz
+ meta.json, and samples.json for the demo picker.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "stock"
DEST = SRC / "prepared"

H = 5                      # forecast horizon (trading days)
TRAIN_END = "2023-10-01"   # train: dates strictly before this
TEST_START = "2023-10-09"  # test: dates on/after this (gap > H days)
CLASSES = ["Low", "Medium", "High"]

FEATURES = [
    "ret_1d", "ret_5d", "vol_5d", "vol_10d", "vol_21d", "hl_range",
    "vol_ratio", "volume_z", "sent_mean_5d", "sent_count_5d", "sent_last", "dd_5d",
]


def build_ticker(px: pd.DataFrame, sent: pd.DataFrame) -> pd.DataFrame:
    px = px.sort_values("date").reset_index(drop=True)
    close = px["close"].to_numpy()
    ret = np.zeros(len(close))
    ret[1:] = np.log(close[1:] / close[:-1])
    px["ret"] = ret

    s = sent.set_index("date")
    net = px["date"].map(s["net_sent"]).fillna(0.0).to_numpy()
    cnt = px["date"].map(s["n_articles"]).fillna(0.0).to_numpy()

    rows = []
    n = len(px)
    for t in range(21, n - H):
        r = px["ret"].to_numpy()
        win5, win10, win21 = r[t - 4:t + 1], r[t - 9:t + 1], r[t - 20:t + 1]
        vol5, vol21 = win5.std(), win21.std()
        vol_seq = close[t - 4:t + 1]
        dd = float((vol_seq / np.maximum.accumulate(vol_seq) - 1).min())
        vol20 = px["volume"].to_numpy()[t - 19:t + 1]
        vz = (px["volume"].to_numpy()[t] - vol20.mean()) / (vol20.std() + 1e-9)
        hl = ((px["high"].to_numpy()[t - 4:t + 1] - px["low"].to_numpy()[t - 4:t + 1])
              / close[t - 4:t + 1]).mean()
        feat = {
            "ret_1d": r[t], "ret_5d": win5.sum(),
            "vol_5d": vol5, "vol_10d": win10.std(), "vol_21d": vol21,
            "hl_range": hl, "vol_ratio": vol5 / (vol21 + 1e-9),
            "volume_z": vz,
            "sent_mean_5d": net[t - 4:t + 1].mean(),
            "sent_count_5d": cnt[t - 4:t + 1].sum(),
            "sent_last": net[t], "dd_5d": dd,
        }
        future_vol = r[t + 1:t + 1 + H].std()
        feat.update(ticker=px["ticker"].iloc[0], date=px["date"].iloc[t],
                    future_vol=future_vol,
                    close_window=json.dumps([round(float(c), 2) for c in close[t - 20:t + 1]]))
        rows.append(feat)
    return pd.DataFrame(rows)


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    prices = pd.read_csv(SRC / "prices.csv")
    sent = pd.read_csv(SRC / "sentiment_daily.csv")

    parts = []
    for tk, grp in prices.groupby("ticker"):
        parts.append(build_ticker(grp, sent[sent.ticker == tk]))
    df = pd.concat(parts, ignore_index=True).dropna()

    train = df[df.date < TRAIN_END].copy()
    test = df[df.date >= TEST_START].copy()

    # terciles from TRAIN future_vol
    q1, q2 = train["future_vol"].quantile([1 / 3, 2 / 3]).to_numpy()

    def label(v):
        return 0 if v <= q1 else (1 if v <= q2 else 2)

    train["y"] = train["future_vol"].map(label)
    test["y"] = test["future_vol"].map(label)

    mu = train[FEATURES].mean()
    sd = train[FEATURES].std().replace(0, 1)

    def pack(d, name):
        X = ((d[FEATURES] - mu) / sd).to_numpy(dtype=np.float32)
        y = d["y"].to_numpy(dtype=np.int64)
        np.savez_compressed(DEST / f"{name}.npz", X=X, y=y)
        dist = {CLASSES[i]: int((y == i).sum()) for i in range(3)}
        print(f"{name}: {len(y)} samples  X{X.shape}  {dist}")
        return X, y

    pack(train, "train")
    Xte, yte = pack(test, "test")

    meta = {
        "features": FEATURES, "classes": CLASSES, "horizon": H,
        "train_end": TRAIN_END, "test_start": TEST_START,
        "tercile_thresholds": [float(q1), float(q2)],
        "feat_mean": {f: float(mu[f]) for f in FEATURES},
        "feat_std": {f: float(sd[f]) for f in FEATURES},
    }
    (DEST / "meta.json").write_text(json.dumps(meta, indent=2))

    # demo samples: a spread of test examples across classes + tickers
    rng = np.random.default_rng(7)
    picks = []
    for cls in range(3):
        sub = test[test.y == cls]
        # prefer well-known tickers with news
        sub = sub[sub.sent_count_5d > 0]
        if len(sub) == 0:
            sub = test[test.y == cls]
        for _, row in sub.sample(n=min(2, len(sub)), random_state=cls).iterrows():
            xi = ((row[FEATURES] - mu) / sd).to_numpy(dtype=float)
            picks.append({
                "ticker": row["ticker"], "date": row["date"],
                "trueClass": CLASSES[cls],
                "features": [round(float(v), 4) for v in xi],
                "closes": json.loads(row["close_window"]),
                "sentiment": round(float(row["sent_mean_5d"]), 3),
                "sentCount": int(row["sent_count_5d"]),
            })
    (DEST / "samples.json").write_text(json.dumps({"classes": CLASSES, "samples": picks}))
    print(f"Wrote {len(picks)} demo samples")


if __name__ == "__main__":
    main()
