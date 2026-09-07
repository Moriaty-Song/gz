import csv
import json
from datetime import datetime, timezone
from urllib.request import Request, urlopen

# Federal Reserve Board의 공식 월간 GZ/EBP CSV
SOURCE_URL = "https://www.federalreserve.gov/econres/notes/feds-notes/ebp_csv.csv"

req = Request(
    SOURCE_URL,
    headers={"User-Agent": "Mozilla/5.0 (GitHub Actions; GZ data updater)"}
)

with urlopen(req, timeout=60) as response:
    raw = response.read().decode("utf-8-sig")

reader = csv.DictReader(raw.splitlines())

rows = []
for r in reader:
    date = (r.get("date") or "").strip()
    if not date:
        continue

    def num(name):
        v = (r.get(name) or "").strip()
        if not v:
            return None
        return float(v)

    rows.append({
        "date": date,
        "gz": num("gz_spread"),
        "ebp": num("ebp"),
        "recession": num("est_prob")
    })

if not rows:
    raise RuntimeError("Fed CSV에서 데이터를 읽지 못했습니다.")

# 날짜순 정렬 + 중복 제거
rows.sort(key=lambda x: x["date"])
unique = {}
for row in rows:
    unique[row["date"]] = row
rows = list(unique.values())

latest = rows[-1]

payload = {
    "title": "GZ 신용스프레드와 EBP (1973~)",
    "unit": "%p",
    "frequency": "매월",
    "source": "Federal Reserve Board · Gilchrist·Zakrajsek",
    "source_url": SOURCE_URL,
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "latest_date": latest["date"],
    "data": rows
}

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

print(f"완료: {len(rows)}개")
print(f"최초: {rows[0]['date']}")
print(f"최신: {latest['date']}")
print(f"GZ: {latest['gz']}")
print(f"EBP: {latest['ebp']}")
print(f"침체확률: {latest['recession']}")
