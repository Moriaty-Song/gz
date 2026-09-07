import csv
import io
import json
import urllib.request
from datetime import datetime, timezone

# 실제 최신 데이터가 들어 있는 참조 CSV
DATA_URL = (
    "https://charlie7375.github.io/charlie73/_sources_dl/"
    "%EC%97%B0%EC%A4%80_GZ%EC%8A%A4%ED%94%84%EB%A0%88%EB%93%9C_%EC%9B%94%EB%B3%84.csv"
)

# 화면에 표시할 공식 출처
OFFICIAL_SOURCE_URL = (
    "https://www.federalreserve.gov/econres/economic-research-data.htm"
)


def download_csv():
    req = urllib.request.Request(
        DATA_URL,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/csv,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8-sig")


def normalize_number(value):
    if value is None or str(value).strip() == "":
        return None
    return float(str(value).strip())


def main():
    text = download_csv()

    # 원본 CSV에는 설명용 # 주석 줄이 앞부분에 있을 수 있으므로 제거
    clean_lines = [
        line for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    if not clean_lines:
        raise RuntimeError("CSV 데이터가 비어 있습니다.")

    reader = csv.DictReader(io.StringIO("\n".join(clean_lines)))
    fieldnames = [str(x).strip().lower() for x in (reader.fieldnames or [])]

    # 실제 참조 CSV: date,gz,ebp,prob
    def find_column(*names):
        for name in names:
            if name in fieldnames:
                return reader.fieldnames[fieldnames.index(name)]
        return None

    date_col = find_column("date")
    gz_col = find_column("gz", "gz_spread")
    ebp_col = find_column("ebp")
    prob_col = find_column("prob", "est_prob")

    missing = []
    if date_col is None:
        missing.append("date")
    if gz_col is None:
        missing.append("gz")
    if ebp_col is None:
        missing.append("ebp")
    if prob_col is None:
        missing.append("prob")

    if missing:
        raise RuntimeError(
            f"필수 컬럼이 없습니다: {missing}\n"
            f"발견된 컬럼: {reader.fieldnames}"
        )

    rows = []

    for row in reader:
        date_raw = str(row.get(date_col, "")).strip()

        if not date_raw:
            continue

        # YYYY-MM 형식으로 통일
        try:
            if len(date_raw) == 7 and date_raw[4] == "-":
                dt = datetime.strptime(date_raw, "%Y-%m")
            else:
                dt = datetime.strptime(date_raw, "%m/%d/%Y")
        except ValueError:
            continue

        try:
            gz = normalize_number(row.get(gz_col))
            ebp = normalize_number(row.get(ebp_col))
            prob = normalize_number(row.get(prob_col))
        except (TypeError, ValueError):
            continue

        if gz is None or ebp is None or prob is None:
            continue

        rows.append(
            {
                "date": dt.strftime("%Y-%m"),
                "gz": gz,
                "ebp": ebp,
                "prob": prob,
            }
        )

    if not rows:
        raise RuntimeError("유효한 데이터 행을 찾지 못했습니다.")

    rows.sort(key=lambda x: datetime.strptime(x["date"], "%Y-%m"))

    latest = rows[-1]

    # 최신 데이터가 과거로 후퇴하는 경우 GitHub Pages에 잘못된 파일을 배포하지 않음
    if int(latest["date"][:4]) < 2026:
        raise RuntimeError(
            f"최신 데이터가 {latest['date']}입니다. "
            "2026년 데이터가 없어 업데이트를 중단합니다."
        )

    output = {
        "source": "Federal Reserve FEDS Notes",
        "source_url": OFFICIAL_SOURCE_URL,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "latest_date": latest["date"],
        "latest_gz": latest["gz"],
        "latest_ebp": latest["ebp"],
        "latest_recession_probability": latest["prob"],
        "count": len(rows),
        "data": rows,
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"rows={len(rows)}")
    print(f"first={rows[0]['date']}")
    print(f"latest={latest['date']}")
    print(f"gz={latest['gz']}")
    print(f"ebp={latest['ebp']}")
    print(f"recession={latest['prob']}")


if __name__ == "__main__":
    main()
