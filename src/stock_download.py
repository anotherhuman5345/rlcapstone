"""Assemble the raw inputs for the stock risk predictor.

Two sources, both public:
  * Ticker-level news sentiment (Polygon news sample via Kaggle) — each article
    has a date, tickers, and a positive/negative/neutral label per ticker.
  * Daily OHLCV prices from Yahoo Finance (yfinance).

We pick a universe of the best-covered tickers (most sentiment articles in 2023),
download their prices over a window padded on both ends (lookback for features,
forward for the volatility label), and write two tidy CSVs:
  data/stock/sentiment_daily.csv : date, ticker, net_sent, n_articles
  data/stock/prices.csv          : date, ticker, open, high, low, close, volume
"""

from __future__ import annotations

import collections
import json
import re
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
SENT_JSON = ROOT / "data" / "stock_sentiment" / "polygon_news_sample.json"
DEST = ROOT / "data" / "stock"
N_TICKERS = 60
PRICE_START, PRICE_END = "2022-10-01", "2024-02-01"
SENT_VALUE = {"positive": 1.0, "negative": -1.0, "neutral": 0.0}
SIMPLE_TICKER = re.compile(r"^[A-Z]{1,5}$")


def load_sentiment():
    articles = json.load(open(SENT_JSON))
    rows = []
    counts = collections.Counter()
    for a in articles:
        date = (a.get("published_utc") or "")[:10]
        if not date:
            continue
        for ins in (a.get("insights") or []):
            t = ins.get("ticker", "")
            s = ins.get("sentiment")
            if not SIMPLE_TICKER.match(t) or s not in SENT_VALUE:
                continue
            rows.append((date, t, SENT_VALUE[s]))
            counts[t] += 1
    df = pd.DataFrame(rows, columns=["date", "ticker", "sent"])
    return df, counts


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    sent, counts = load_sentiment()
    universe = [t for t, _ in counts.most_common(N_TICKERS)]
    print(f"Universe ({len(universe)}): {', '.join(universe)}")

    daily = (sent[sent.ticker.isin(universe)]
             .groupby(["date", "ticker"])
             .agg(net_sent=("sent", "mean"), n_articles=("sent", "size"))
             .reset_index())
    daily.to_csv(DEST / "sentiment_daily.csv", index=False)
    print(f"sentiment_daily.csv: {len(daily)} (ticker, date) rows")

    print("Downloading prices from Yahoo Finance ...")
    raw = yf.download(universe, start=PRICE_START, end=PRICE_END,
                      auto_adjust=True, progress=False, group_by="ticker")
    frames = []
    for t in universe:
        try:
            sub = raw[t].reset_index()
        except KeyError:
            print(f"  ! no price data for {t}")
            continue
        sub = sub.rename(columns=str.lower)
        sub["ticker"] = t
        sub = sub[["date", "ticker", "open", "high", "low", "close", "volume"]]
        frames.append(sub.dropna())
    prices = pd.concat(frames, ignore_index=True)
    prices["date"] = pd.to_datetime(prices["date"]).dt.strftime("%Y-%m-%d")
    prices.to_csv(DEST / "prices.csv", index=False)
    print(f"prices.csv: {len(prices)} rows over "
          f"{prices.ticker.nunique()} tickers")


if __name__ == "__main__":
    main()
