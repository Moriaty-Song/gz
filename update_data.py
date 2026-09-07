import csv
import io
import json
import urllib.request
from datetime import datetime, timezone

SOURCE_URL = "https://charlie7375.github.io/charlie73/data/gz.csv"
OUTPUT_FILE = "data.json"


def download_csv():
    req = urllib.request.Request(
        SOURCE_URL,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8-sig")


def main():
    text = download_csv()

    # Remove blank/comment lines, then parse the real CSV.
    lines = [
        line for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    if not lines:
        raise RuntimeError("CSV is empty")

    reader = csv.DictReader(io.StringIO("\n".join(lines)))

    if not reader.fieldnames:
        raise RuntimeError("CSV header not found")

    headers = [h.strip() for h in reader.fieldnames]

    # Accept both the original Federal Reserve naming and the current
    # source naming: date,gz_spread,ebp,est_prob OR date,gz,ebp,prob.
    def pick(*names):
        for name in names:
            if name in headers:
                return name
        return None

    date_col = pick("date")
    gz_col = pick("gz_spread", "gz")
    ebp_col = pick("ebp")
    prob_col = pick("est_prob", "prob")

    missing = []
    if not date_col:
        missing.append("date")
    if not gz_col:
        missing.append("gz_spread/gz")
    if not ebp_col:
        missing.append("ebp")
    if not prob_col:
        missing.append("est_prob/prob")

    if missing:
        raise RuntimeError(
            f"Missing columns: {missing}. Found: {headers}"
        )

    rows = []

    for raw in reader:
        row = {str(k).strip(): (v.strip() if isinstance(v, str) else v)
               for k, v in raw.items()}

        date = row.get(date_col, "")
        gz = row.get(gz_col, "")
        ebp = row.get(ebp_col, "")
        prob = row.get(prob_col, "")

        if not date:
            continue

        try:
            gz = float(gz)
            ebp = float(ebp)
            prob = float(prob)
        except (TypeError, ValueError):
            continue

        rows.append({
            "date": date,
            "gz": gz,
            "ebp": ebp,
            "recession": prob
        })

    # Sort by YYYY-MM or M/D/YYYY safely.
    def date_key(r):
        s = r["date"]
        for fmt in ("%Y-%m", "%m/%d/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                pass
        return datetime.min

    rows.sort(key=date_key)

    # Remove duplicate dates, keeping the latest occurrence.
    unique = {}
    for row in rows:
        unique[row["date"]] = row
    rows = sorted(unique.values(), key=date_key)

    if len(rows) < 500:
        raise RuntimeError(f"Too few rows: {len(rows)}")

    latest = rows[-1]

    # Safety check: this project is expected to contain 2026 data.
    latest_key = date_key(latest)
    if latest_key.year < 2026:
        raise RuntimeError(
            f"Data is still stale. Latest={latest['date']}. "
            "Expected 2026 data."
        )

    output = {
        "title": "GZ 신용스프레드와 EBP (1973~)",
        "unit": "%p",
        "frequency": "매월",
        "source": "Federal Reserve Board · Gilchrist·Zakrajsek",
        "source_url": SOURCE_URL,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "latest_date": latest["date"],
        "data": rows
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"rows={len(rows)}")
    print(f"first={rows[0]['date']}")
    print(f"latest={latest['date']}")
    print(f"gz={latest['gz']}")
    print(f"ebp={latest['ebp']}")
    print(f"recession={latest['recession']}")


if __name__ == "__main__":
    main()
