# BFlux enhanced data fetcher
# Creates/updates data_current/processed/early_warning.sqlite and crisis_history.csv.
# Standard-library only for World Bank and starter crisis data. Optional openpyxl/pandas improve Excel parsing.

from pathlib import Path
import argparse, csv, json, os, re, sqlite3, sys, time, urllib.request, urllib.parse, zipfile

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data_current" / "raw"
PROCESSED = ROOT / "data_current" / "processed"
DB_PATH = PROCESSED / "early_warning.sqlite"
CRISIS_CSV_SRC = ROOT / "data" / "crisis_history.csv"
CRISIS_CSV_DST = PROCESSED / "crisis_history.csv"

COUNTRIES = ["USA","CHN","CHE","DEU","FRA","GBR","JPN","CAN","MEX","TUR","ARG","BRA","IND","ITA","ESP","KOR","AUS","ZAF","IDN","SAU","RUS","THA","IRL","GRC"]
WORLD_BANK_INDICATORS = {
    "NY.GDP.MKTP.KD.ZG": "worldbank_gdp_growth",
    "FP.CPI.TOTL.ZG": "worldbank_inflation_cpi",
    "SL.UEM.TOTL.ZS": "worldbank_unemployment",
    "BN.CAB.XOKA.GD.ZS": "worldbank_current_account_pct_gdp",
    "FI.RES.TOTL.CD": "worldbank_total_reserves_usd",
    "DT.DOD.DECT.GN.ZS": "worldbank_external_debt_pct_gni",
    "FS.AST.PRVT.GD.ZS": "worldbank_private_credit_by_banks_pct_gdp",
}

HBS_CRISIS_XLSX_URL = "https://www.hbs.edu/behavioral-finance-and-financial-stability/Documents/ChartData/MapCharts/20160923_global_crisis_data.xlsx"
BIS_BULK_URL = "https://data.bis.org/bulkdownload"
BIS_TOPICS = [
    "Credit-to-GDP gaps (CSV, flat)",
    "Credit to the non-financial sector (CSV, flat)",
    "Debt service ratios (CSV, flat)",
    "Locational banking statistics (CSV, flat)",
    "Consolidated banking statistics (CSV, flat)",
    "Selected residential property prices (CSV, flat)",
    "Commercial property prices (CSV, flat)",
    "Effective exchange rates (CSV, flat)",
    "Central bank policy rates (CSV, flat)",
]
FRED_SERIES = {
    "VIXCLS": "fred_vix",
    "NFCI": "fred_chicago_national_financial_conditions_index",
    "STLFSI4": "fred_st_louis_financial_stress_index",
    "BAMLH0A0HYM2": "fred_high_yield_spread",
    "FEDFUNDS": "fred_fed_funds_rate",
    "DGS10": "fred_10y_treasury_yield",
    "DTWEXBGS": "fred_trade_weighted_us_dollar",
}

def ensure_dirs():
    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    (RAW / "crises").mkdir(parents=True, exist_ok=True)
    (RAW / "worldbank").mkdir(parents=True, exist_ok=True)
    (RAW / "bis").mkdir(parents=True, exist_ok=True)
    (RAW / "fred").mkdir(parents=True, exist_ok=True)
    (ROOT / "data").mkdir(parents=True, exist_ok=True)

def download(url, path, timeout=60):
    path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "BFlux/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    path.write_bytes(data)
    return path

def connect():
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    return conn

def create_tables(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS enhanced_indicators (
            country_code TEXT NOT NULL,
            year INTEGER NOT NULL,
            indicator TEXT NOT NULL,
            value REAL NOT NULL,
            source TEXT,
            raw_indicator TEXT,
            fetched_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS crisis_history (
            country_code TEXT NOT NULL,
            country_name TEXT,
            crisis_name TEXT NOT NULL,
            crisis_type TEXT NOT NULL,
            start_year INTEGER NOT NULL,
            peak_year INTEGER,
            end_year INTEGER,
            severity TEXT,
            source TEXT,
            notes TEXT
        )
    """)
    conn.commit()

def insert_indicator(conn, country, year, indicator, value, source, raw_indicator=None):
    if value is None:
        return
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO enhanced_indicators
        (country_code, year, indicator, value, source, raw_indicator, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
    """, (country, int(year), indicator, float(value), source, raw_indicator or indicator))

def reset_source(conn, source_prefix):
    cur = conn.cursor()
    cur.execute("DELETE FROM enhanced_indicators WHERE source LIKE ?", (source_prefix + "%",))
    conn.commit()

def load_crisis_csv(conn):
    if not CRISIS_CSV_SRC.exists():
        raise FileNotFoundError(f"Missing {CRISIS_CSV_SRC}")
    CRISIS_CSV_DST.parent.mkdir(parents=True, exist_ok=True)
    CRISIS_CSV_DST.write_text(CRISIS_CSV_SRC.read_text(encoding="utf-8"), encoding="utf-8")

    cur = conn.cursor()
    cur.execute("DELETE FROM crisis_history")
    with CRISIS_CSV_SRC.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            rows.append((
                r.get("country_code","").upper(),
                r.get("country_name",""),
                r.get("crisis_name",""),
                r.get("crisis_type",""),
                int(float(r.get("start_year") or 0)),
                int(float(r.get("peak_year") or r.get("start_year") or 0)),
                int(float(r.get("end_year") or r.get("peak_year") or r.get("start_year") or 0)),
                r.get("severity",""),
                r.get("source",""),
                r.get("notes",""),
            ))
    cur.executemany("""
        INSERT INTO crisis_history
        (country_code, country_name, crisis_name, crisis_type, start_year, peak_year, end_year, severity, source, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    print(f"Loaded starter Crisis Memory: {len(rows)} events")

def fetch_hbs_crisis_raw():
    out = RAW / "crises" / "hbs_global_crisis_data.xlsx"
    try:
        download(HBS_CRISIS_XLSX_URL, out, timeout=90)
        print(f"Downloaded HBS/Reinhart-Rogoff crisis workbook: {out}")
    except Exception as exc:
        print(f"HBS workbook download failed: {exc}")
    print("The starter crisis_history.csv remains the operational calibration table unless you manually inspect/merge the workbook.")

def fetch_worldbank(conn, countries=None, start=1960, end=2026):
    countries = countries or COUNTRIES
    reset_source(conn, "World Bank")
    total = 0
    for country in countries:
        for code, name in WORLD_BANK_INDICATORS.items():
            url = (
                "https://api.worldbank.org/v2/country/"
                + urllib.parse.quote(country)
                + "/indicator/"
                + urllib.parse.quote(code)
                + f"?format=json&per_page=20000&date={start}:{end}"
            )
            try:
                req = urllib.request.Request(url, headers={"User-Agent":"BFlux/1.0"})
                with urllib.request.urlopen(req, timeout=45) as r:
                    payload = json.loads(r.read().decode("utf-8"))
                if not isinstance(payload, list) or len(payload) < 2:
                    continue
                for item in payload[1]:
                    val = item.get("value")
                    yr = item.get("date")
                    if val is None or not yr:
                        continue
                    insert_indicator(conn, country, int(yr), name, float(val), "World Bank API", code)
                    total += 1
                time.sleep(0.05)
            except Exception as exc:
                print(f"World Bank skipped {country} {code}: {exc}")
    conn.commit()
    print(f"World Bank observations inserted: {total}")

def fetch_fred(conn):
    key = os.environ.get("FRED_API_KEY", "").strip()
    env_path = ROOT / ".env"
    if not key and env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("FRED_API_KEY="):
                key = line.split("=",1)[1].strip()
    if not key:
        print("FRED skipped: set FRED_API_KEY in .env first.")
        return
    reset_source(conn, "FRED")
    total = 0
    for sid, name in FRED_SERIES.items():
        url = ("https://api.stlouisfed.org/fred/series/observations?"
               + urllib.parse.urlencode({"series_id": sid, "api_key": key, "file_type": "json"}))
        try:
            with urllib.request.urlopen(url, timeout=45) as r:
                payload = json.loads(r.read().decode("utf-8"))
            annual = {}
            for obs in payload.get("observations", []):
                val = obs.get("value")
                if val in (None, ".", ""):
                    continue
                year = int(obs.get("date", "0000")[:4])
                annual.setdefault(year, []).append(float(val))
            for year, vals in annual.items():
                insert_indicator(conn, "USA", year, name, sum(vals)/len(vals), "FRED API", sid)
                total += 1
        except Exception as exc:
            print(f"FRED skipped {sid}: {exc}")
    conn.commit()
    print(f"FRED annual observations inserted: {total}")

def fetch_bis_raw():
    try:
        html = urllib.request.urlopen(urllib.request.Request(BIS_BULK_URL, headers={"User-Agent":"BFlux/1.0"}), timeout=45).read().decode("utf-8", errors="ignore")
    except Exception as exc:
        print(f"BIS bulk page failed: {exc}")
        return
    links = re.findall(r'href="([^"]+)"[^>]*>([^<]+)</a>', html)
    saved = 0
    for href, text in links:
        label = re.sub(r"\s+", " ", text).strip()
        if not any(topic in label for topic in BIS_TOPICS):
            continue
        url = href if href.startswith("http") else urllib.parse.urljoin(BIS_BULK_URL, href)
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", label)[:90] + ".zip"
        out = RAW / "bis" / safe
        try:
            download(url, out, timeout=180)
            print(f"Downloaded BIS: {label} -> {out.name}")
            saved += 1
        except Exception as exc:
            print(f"BIS download skipped {label}: {exc}")
    print(f"BIS raw zip files downloaded: {saved}")
    print("BIS raw files are saved locally. Existing BFlux loaders will use SQLite tables after your BIS conversion pipeline imports them.")

def status():
    print(f"Project: {ROOT}")
    print(f"Database: {DB_PATH} {'FOUND' if DB_PATH.exists() else 'missing'}")
    for p in [CRISIS_CSV_DST, RAW / "crises", RAW / "worldbank", RAW / "bis", RAW / "fred"]:
        print(f"{p}: {'FOUND' if p.exists() else 'missing'}")

def main():
    parser = argparse.ArgumentParser(description="Fetch enhanced public data for Bank Flux / BFlux.")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--crises", action="store_true")
    parser.add_argument("--worldbank", action="store_true")
    parser.add_argument("--fred", action="store_true")
    parser.add_argument("--bis", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    ensure_dirs()
    if args.status:
        status()
        return

    conn = connect()
    create_tables(conn)

    if args.all or args.crises:
        load_crisis_csv(conn)
        fetch_hbs_crisis_raw()
    if args.all or args.worldbank:
        fetch_worldbank(conn)
    if args.all or args.fred:
        fetch_fred(conn)
    if args.all or args.bis:
        fetch_bis_raw()

    conn.close()
    print("Done.")
    print("Next: python bank_flux.py")

if __name__ == "__main__":
    main()
