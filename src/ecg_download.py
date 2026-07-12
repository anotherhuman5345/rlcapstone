"""Download the MIT-BIH Arrhythmia Database from PhysioNet.

Open-access, no credentials needed. Pulls the full 48-record set (each record
is a ~30 min two-lead recording sampled at 360 Hz, with a cardiologist's
beat-by-beat annotations). Saved under data/mitbih/.
"""

from __future__ import annotations

from pathlib import Path

import wfdb

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data" / "mitbih"


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    print(f"Downloading MIT-BIH Arrhythmia DB -> {DEST}")
    # Grabs .dat (signal), .hea (header), .atr (annotations) for every record.
    wfdb.dl_database("mitdb", str(DEST))

    records = sorted(p.stem for p in DEST.glob("*.hea"))
    print(f"\nDone. {len(records)} records: {', '.join(records)}")


if __name__ == "__main__":
    main()
