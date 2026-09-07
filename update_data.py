import csv
import json
from datetime import datetime, timezone
from urllib.request import Request, urlopen

# This is the current official CSV link listed by the Federal Reserve.
SOURCE_URL = "https://www.federalreserve.gov/econresdata/notes/feds-notes/2016/files/ebp_csv.csv"

req = Request(
    SOURCE_URL,
    headers={
        "User-Agent": "Mozilla/5.0 (compatible; GZ-data-updater/1.0)"
    },
)

with urlopen(req, timeout=60) as response:
    raw = response.read().decode("utf-8-sig")

reader = csv.DictReader(raw.splitlines())

required = {"date", "gz_spread", "ebp", "est_prob"}
if not required.issubset(set(reader.fieldnames or [])):
    raise RuntimeError(
        f"Unexpected columns: {reader.fieldnames}. "
        f"Expected at least {sorted(required)}"
    )

rows = []
for r in reader:
    date = (r.get("date") or "").strip()
    if not date:
        continue

    def number(name):
        value = (r.get(name) or "").strip()
        if value in ("", ".", "NA", "NaN"):
            return None
        return float(value)

    rows.append({
        "date": date,
        "gz": number("gz_spread"),
        "ebp": number("ebp"),
        "recession": number("est_prob"),
    })

# date ascending + duplicate removal
rows.sort(key=lambda x: x["date"])
dedup = {}
for row in rows:
    dedup[row["date"]] = row
rows = list(dedup.values())

if len(rows) < 500:
    raise RuntimeError(f"Too few rows: {len(rows)}")

latest = rows[-1]

payload = {
    "title": "GZ 신용스프레드와 EBP (1973~)",
    "unit": "%p",
    "frequency": "매월",
    "source": "Federal Reserve Board · Gilchrist·Zakrajsek",
    "source_url": SOURCE_URL,
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "latest_date": latest["date"],
    "data": rows,
}

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

print(f"rows={len(rows)}")
print(f"first={rows[0]['date']}")
print(f"latest={latest['date']}")
print(f"gz={latest['gz']}")
print(f"ebp={latest['ebp']}")
print(f"recession={latest['recession']}")
