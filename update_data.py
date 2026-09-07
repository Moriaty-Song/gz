import csv
import io
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

# The original reference site republishes the Federal Reserve GZ/EBP monthly CSV.
# The direct Federal Reserve endpoint currently returns an older cached file to
# GitHub Actions, while the reference site's copy is updated through 2026-07.
SOURCE_URL = "https://charlie7375.github.io/charlie73/_sources_dl/%EC%97%B0%EC%A4%80_GZ%EC%8A%A4%ED%94%84%EB%A0%88%EB%93%9C_%EC%9B%94%EB%B3%84.csv"
OFFICIAL_SOURCE_URL = "https://www.federalreserve.gov/econresdata/notes/feds-notes/2016/files/ebp_csv.csv"

OUT = Path("data.json")


def parse_number(value):
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    return float(s.replace(",", ""))


def parse_date(value):
    s = str(value).strip()

    # ISO / YYYY-MM
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y/%m/%d", "%Y/%m"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass

    # Common M/D/YYYY form used by the reference CSV
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass

    raise ValueError(f"Unsupported date: {value!r}")


def normalize_date(value):
    return parse_date(value).strftime("%Y-%m")


def main():
    # Cache-busting query helps avoid stale CDN/proxy copies.
    url = SOURCE_URL + "?" + urlencode({"v": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")})

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; GZ-data-updater/1.0)",
            "Accept": "text/csv,text/plain,*/*",
            "Cache-Control": "no-cache",
        },
    )

    with urllib.request.urlopen(req, timeout=60) as response:
        raw = response.read()

    text = raw.decode("utf-8-sig")

    # The reference CSV contains a metadata/comment line before the real
    # CSV header (e.g. "# GZ 신용스프레드..."). Remove blank/comment lines
    # before passing the content to DictReader.
    clean_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        clean_lines.append(line)

    if not clean_lines:
        raise RuntimeError("CSV header not found")

    reader = csv.DictReader(io.StringIO("\\n".join(clean_lines)))
    if not reader.fieldnames:
        raise RuntimeError("CSV header not found")

    fields = {f.strip().lower(): f for f in reader.fieldnames if f}
    required = ["date", "gz_spread", "ebp", "est_prob"]
    missing = [x for x in required if x not in fields]
    if missing:
        raise RuntimeError(
            f"Missing columns: {missing}. Found: {reader.fieldnames}"
        )

    rows_by_date = {}

    for raw_row in reader:
        if not raw_row:
            continue

        date_raw = raw_row.get(fields["date"])
        if not date_raw:
            continue

        try:
            d = normalize_date(date_raw)
            gz = parse_number(raw_row.get(fields["gz_spread"]))
            ebp = parse_number(raw_row.get(fields["ebp"]))
            recession = parse_number(raw_row.get(fields["est_prob"]))
        except (ValueError, TypeError) as e:
            print(f"Skipping row: {raw_row} ({e})")
            continue

        if gz is None or ebp is None or recession is None:
            continue

        rows_by_date[d] = {
            "date": d,
            "gz": gz,
            "ebp": ebp,
            "recession": recession,
        }

    rows = [rows_by_date[d] for d in sorted(rows_by_date)]

    if len(rows) < 600:
        raise RuntimeError(f"Too few rows: {len(rows)}")

    latest = rows[-1]

    # Safety check: do not silently publish stale data again.
    if latest["date"] < "2026-01":
        raise RuntimeError(
            f"Source is stale: latest={latest['date']}. "
            "Refusing to overwrite data.json."
        )

    payload = {
        "title": "GZ 신용스프레드와 EBP (1973~)",
        "unit": "%p",
        "frequency": "매월",
        "source": "Federal Reserve Board · Gilchrist·Zakrajsek",
        "source_url": OFFICIAL_SOURCE_URL,
        "data_source_url": SOURCE_URL,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "latest_date": latest["date"],
        "data": rows,
    }

    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"rows={len(rows)}")
    print(f"first={rows[0]['date']}")
    print(f"latest={latest['date']}")
    print(f"gz={latest['gz']}")
    print(f"ebp={latest['ebp']}")
    print(f"recession={latest['recession']}")


if __name__ == "__main__":
    main()
