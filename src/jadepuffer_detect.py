"""JADEPUFFER detector — a DEFENSIVE tool that spots agentic database-extortion
in a database activity log.

Background: JADEPUFFER (reported by Sysdig) is the first documented case of
"agentic ransomware" — an LLM drives an end-to-end attack that breaks into a
database, plants a backdoor admin, encrypts every config with AES_ENCRYPT(),
drops the originals, and leaves a ransom table demanding Bitcoin. This tool is
the opposite of that: it reads a log of SQL statements (and optional system
lines) and flags the behaviours and indicators that give the attack away, so a
defender can catch it. It never runs anything — it only reads and scores text.

This is the v2 companion to the AI Hacking Agent project: educational, defensive.

Usage:
    python src/jadepuffer_detect.py <logfile>
    # or import scan() and pass a list of SQL statements / log lines.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# --- Known indicators of compromise from the public report ------------------
# (Defenders match these literally; behaviour rules below catch variants.)
IOCS = {
    "c2 / beacon host": ["45.131.66.106"],
    "exfil / staging host": ["64.20.53.230"],
    "beacon path": ["/beacon"],
    "ransom bitcoin address": ["3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"],
    "ransom contact email": ["e78393397@proton.me"],
    "known ransom table names": ["README_RANSOM", "RECOVER_YOUR_DATA",
                                 "PLEASE_READ_ME", "WARNING"],
}

# --- Behavioural rules (single-statement, regex) ----------------------------
# weight is a risk contribution; higher = more damning.
RULES = [
    {
        "id": "RANSOM_TABLE", "weight": 45,
        "name": "Ransom-note table created",
        "stage": "Impact / Extortion", "mitre": "T1486 Data Encrypted for Impact",
        "re": re.compile(r"\b(create\s+table|insert\s+into)\b[^;]*\b"
                         r"(readme_ransom|recover_your_data|please_read_me|"
                         r"decrypt|ransom|read_me_to_recover)\b", re.I),
        "why": "A table whose name reads like a ransom note is created — the "
               "attacker's demand is stored in the database itself.",
    },
    {
        "id": "RANSOM_MARKERS", "weight": 35,
        "name": "Ransom-note text / crypto markers",
        "stage": "Impact / Extortion", "mitre": "T1657 Financial Theft",
        "re": re.compile(r"(bitcoin|btc\b|monero|\bwallet\b|decryptor|"
                         r"pay\s+.*(to\s+)?(recover|restore|decrypt)|"
                         r"your\s+data\s+has\s+been\s+encrypted|"
                         r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b|"
                         r"\b[\w.+-]+@proton\.me\b)", re.I),
        "why": "Ransom-note wording, a crypto wallet, or a contact address "
               "appears in the SQL — hallmark of an extortion payload.",
    },
    {
        "id": "BULK_ENCRYPT", "weight": 30,
        "name": "Bulk AES encryption of a table",
        "stage": "Impact", "mitre": "T1486 Data Encrypted for Impact",
        "re": re.compile(r"create\s+table\s+\w+[^;]*\bas\s+select\b[^;]*"
                         r"aes_encrypt\s*\(", re.I),
        "why": "A whole table is copied through AES_ENCRYPT() into a new "
               "table — the 'encrypt everything' step of the ransom.",
    },
    {
        "id": "FK_DISABLE", "weight": 20,
        "name": "Foreign-key checks disabled",
        "stage": "Impact", "mitre": "T1485 Data Destruction",
        "re": re.compile(r"set\s+(global\s+)?foreign_key_checks\s*=\s*0", re.I),
        "why": "Foreign-key checks are switched off — usually to force through "
               "mass DROPs that constraints would otherwise block.",
    },
    {
        "id": "DROP_DESTRUCTIVE", "weight": 15,
        "name": "Destructive DROP / TRUNCATE",
        "stage": "Impact", "mitre": "T1485 Data Destruction",
        "re": re.compile(r"\b(drop\s+(table|database)|truncate\s+table)\b", re.I),
        "why": "Tables or databases are being destroyed.",
    },
    {
        "id": "BACKDOOR_ADMIN", "weight": 30,
        "name": "Backdoor admin account inserted",
        "stage": "Persistence / PrivEsc", "mitre": "T1136 Create Account",
        "re": re.compile(r"insert\s+into\s+(users|roles)\b[^;]*"
                         r"(role_admin|\brole\b.*admin|\$2[aby]\$)", re.I),
        "why": "A new user or admin role is inserted straight into the auth "
               "tables (often with a bcrypt hash) — a database backdoor.",
    },
    {
        "id": "CONTAINER_ESCAPE", "weight": 25,
        "name": "Privilege / container-escape probing",
        "stage": "Discovery / PrivEsc", "mitre": "T1611 Escape to Host",
        "re": re.compile(r"(load_file\s*\(\s*['\"]?/(proc|var/run/docker\.sock|"
                         r"etc/)|into\s+(out|dump)file|from\s+mysql\.func\b)", re.I),
        "why": "The DB is used to read host files (/proc, docker.sock) or write "
               "files / list UDFs — probing to break out of the database.",
    },
    {
        "id": "SECRET_HARVEST", "weight": 15,
        "name": "Secret / credential harvesting",
        "stage": "Credential Access", "mitre": "T1552 Unsecured Credentials",
        "re": re.compile(r"(credentials\.json|\.env\b|secret|api[_-]?key|"
                         r"minioadmin)", re.I),
        "why": "Queries reach for credential files or secrets in the environment.",
    },
    {
        "id": "AGENTIC_REASONING", "weight": 20,
        "name": "AI-style reasoning left in the SQL (agentic tell)",
        "stage": "Attribution", "mitre": "Behavioural",
        "re": re.compile(r"(--|#|/\*)[^\n]*\b(high[- ]?roi|largest|drop it too|"
                         r"already\s+backed\s+up|prioriti|let'?s\s|we\s+should|"
                         r"i'?ll\s|step\s+\d|todo:)\b", re.I),
        "why": "Human attackers don't leave natural-language reasoning in "
               "throwaway SQL. Comments like 'high-ROI DBs to drop' are a "
               "signature of an LLM-driven (agentic) operator — the thing that "
               "makes JADEPUFFER new.",
    },
]

LEVELS = [(90, "CRITICAL"), (55, "HIGH"), (25, "MEDIUM"), (1, "LOW"), (0, "CLEAN")]


def _level(score: int) -> str:
    for threshold, name in LEVELS:
        if score >= threshold:
            return name
    return "CLEAN"


def scan(statements: list[str]) -> dict:
    """Scan a list of log lines / SQL statements. Returns a findings report."""
    findings = []
    joined = "\n".join(statements)

    # single-statement behavioural rules
    for i, stmt in enumerate(statements):
        for rule in RULES:
            if rule["re"].search(stmt):
                findings.append({
                    "rule": rule["id"], "name": rule["name"],
                    "stage": rule["stage"], "mitre": rule["mitre"],
                    "weight": rule["weight"], "why": rule["why"],
                    "line": i + 1, "evidence": stmt.strip()[:140],
                })

    # cross-statement behaviour: encrypt-a-table then drop the original
    enc = [re.search(r"create\s+table\s+(\w+)[^;]*aes_encrypt", s, re.I)
           for s in statements]
    enc_tables = {m.group(1).lower() for m in enc if m}
    dropped = {m.group(1).lower() for s in statements
               for m in [re.search(r"drop\s+table\s+`?(\w+)`?", s, re.I)] if m}
    # the classic pattern: config_info_enc created, config_info dropped
    if enc_tables and dropped:
        findings.append({
            "rule": "ENCRYPT_THEN_DESTROY", "name": "Encrypt-copy then destroy original",
            "stage": "Impact", "mitre": "T1486 / T1485", "weight": 25,
            "why": "A table was copied through encryption and originals were then "
                   "dropped — the full 'lock the data and delete the key holder' "
                   "ransom pattern, not routine maintenance.",
            "line": 0, "evidence": f"encrypted: {sorted(enc_tables)}; dropped: {sorted(dropped)}",
        })

    # known IOCs (literal matches)
    ioc_hits = []
    low = joined.lower()
    for label, values in IOCS.items():
        for v in values:
            if v.lower() in low:
                ioc_hits.append({"type": label, "value": v})

    score = sum(f["weight"] for f in findings) + 25 * len(ioc_hits)
    score = min(score, 100)

    return {
        "risk_score": score,
        "risk_level": _level(score),
        "n_findings": len(findings),
        "findings": findings,
        "ioc_hits": ioc_hits,
        "verdict": ("Looks like JADEPUFFER-style agentic database extortion."
                    if score >= 55 else
                    "Some suspicious activity — review." if score >= 25 else
                    "No JADEPUFFER indicators found."),
    }


def load_log(path: Path) -> list[str]:
    """Split a log into statements. Splits on ';' and newlines, keeps non-empty."""
    text = path.read_text(encoding="utf-8", errors="replace")
    parts = re.split(r";\s*\n|\n", text)
    return [p.strip() for p in parts if p.strip()]


def print_report(report: dict) -> None:
    print("=" * 64)
    print(f"  JADEPUFFER detector — risk {report['risk_score']}/100  "
          f"[{report['risk_level']}]")
    print(f"  {report['verdict']}")
    print("=" * 64)
    if report["ioc_hits"]:
        print("\nKnown indicators of compromise matched:")
        for h in report["ioc_hits"]:
            print(f"  ! {h['type']}: {h['value']}")
    if report["findings"]:
        print(f"\nBehaviour flags ({report['n_findings']}):")
        for f in report["findings"]:
            loc = f"line {f['line']}" if f["line"] else "sequence"
            print(f"  [{f['stage']}] {f['name']}  ({loc}, +{f['weight']})")
            print(f"      {f['mitre']}")
            print(f"      evidence: {f['evidence']}")
    else:
        print("\nNo behavioural flags.")
    print()


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: python src/jadepuffer_detect.py <logfile.sql|.log>")
        raise SystemExit(1)
    report = scan(load_log(Path(sys.argv[1])))
    print_report(report)
    out = Path(sys.argv[1]).with_suffix(".jadepuffer.json")
    out.write_text(json.dumps(report, indent=2))
    print(f"(full report written to {out})")


if __name__ == "__main__":
    main()
