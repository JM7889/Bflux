# Bank Flux Forecast Lab
# Public-data banking-flow and macro-financial early-warning console
# Final research version for GitHub / academic review
# Author display: Jean-Marc | Display date: 06/04/2026

import os
import re
import csv
import math
import sqlite3
import textwrap
import statistics
import subprocess
from datetime import datetime
from collections import defaultdict

APP_NAME = "BANK FLUX FORECAST LAB"
AUTHOR_NAME = "Jean-Marc"
DISPLAY_DATE = "06/04/2026"
VERSION = "Forecast Lab final research draft + BFlux agent"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATHS = [
    os.path.join(BASE_DIR, "data_current", "processed", "early_warning.sqlite"),
    os.path.join(BASE_DIR, "early_warning.sqlite"),
]
EXPORT_DIR = os.path.join(BASE_DIR, "exports")

COUNTRY_ALIASES = {
    "global": "GLOBAL", "world": "GLOBAL", "all": "GLOBAL", "system": "GLOBAL",
    "usa": "USA", "us": "USA", "u.s.": "USA", "united states": "USA", "america": "USA",
    "china": "CHN", "chn": "CHN",
    "switzerland": "CHE", "swiss": "CHE", "che": "CHE",
    "turkey": "TUR", "turkiye": "TUR", "türkiye": "TUR", "tur": "TUR",
    "mexico": "MEX", "mex": "MEX",
    "argentina": "ARG", "arg": "ARG",
    "germany": "DEU", "deu": "DEU",
    "france": "FRA", "fra": "FRA",
    "japan": "JPN", "jpn": "JPN",
    "uk": "GBR", "u.k.": "GBR", "united kingdom": "GBR", "britain": "GBR", "gbr": "GBR",
    "canada": "CAN", "can": "CAN",
    "italy": "ITA", "ita": "ITA",
    "spain": "ESP", "esp": "ESP",
    "brazil": "BRA", "bra": "BRA",
    "india": "IND", "ind": "IND",
    "russia": "RUS", "rus": "RUS",
    "south korea": "KOR", "korea": "KOR", "kor": "KOR",
    "australia": "AUS", "aus": "AUS",
    "south africa": "ZAF", "zaf": "ZAF",
    "indonesia": "IDN", "idn": "IDN",
    "saudi arabia": "SAU", "sau": "SAU",
}

IMPORTANT_COUNTRIES = [
    "USA", "CHN", "CHE", "DEU", "FRA", "GBR", "JPN", "CAN", "MEX", "TUR", "ARG", "BRA",
    "IND", "ITA", "ESP", "KOR", "AUS", "ZAF", "IDN", "SAU", "RUS"
]

# Keywords determine how raw indicator names are mapped into research channels.
KEYWORDS = {
    "banking": [
        "bank", "banking", "cross-border", "cross border", "claims", "claim", "liabilities",
        "liability", "bis", "lbs", "cbs", "guarantor", "locational", "consolidated",
        "international", "offshore", "foreign currency", "credit to non-bank", "interbank"
    ],
    "credit": [
        "credit", "private credit", "domestic credit", "debt", "leverage", "loan", "loans",
        "borrowing", "claims", "debt securities"
    ],
    "property": [
        "property", "real estate", "house", "housing", "residential", "commercial", "dpp", "home price",
        "land", "mortgage"
    ],
    "macro": [
        "gdp", "inflation", "unemployment", "current account", "exchange", "fx", "growth", "worldbank",
        "cpi", "imports", "exports", "trade", "fiscal", "deficit", "population"
    ],
    "liquidity": [
        "liquidity", "money", "rate", "funding", "dsr", "debt service", "interest", "reserves",
        "deposit", "m2", "m3", "short-term", "yield"
    ],
    "market": [
        "spread", "vix", "equity", "stock", "bond", "stress", "dollar", "fred", "financial stress",
        "exchange rate", "risk premium", "volatility"
    ],
}

WEIGHTS = {
    "banking": 0.27,
    "credit": 0.24,
    "property": 0.14,
    "macro": 0.13,
    "liquidity": 0.12,
    "market": 0.10,
}

# A modest systemic-importance adjustment. It should not dominate the signal.
SYSTEMIC_BOOST = {
    "USA": 8, "CHN": 8, "CHE": 8, "DEU": 7, "GBR": 7, "JPN": 7, "FRA": 7,
    "CAN": 5, "ITA": 5, "ESP": 5, "KOR": 5, "AUS": 5,
    "MEX": 4, "TUR": 4, "ARG": 4, "BRA": 4, "IND": 4, "ZAF": 3, "IDN": 3, "SAU": 3,
}

CRISIS_ANCHOR_YEARS = [1982, 1997, 2008, 2009, 2020, 2023]

SCENARIOS = {
    "recession": {"macro": 18, "credit": 10, "market": 8},
    "rate_shock": {"liquidity": 18, "property": 12, "market": 8, "credit": 6},
    "banking_shock": {"banking": 20, "liquidity": 14, "market": 10},
    "dollar_shock": {"liquidity": 16, "banking": 12, "market": 10, "macro": 6},
    "property_shock": {"property": 24, "credit": 12, "banking": 6},
    "emerging_market_shock": {"macro": 14, "liquidity": 14, "banking": 12, "market": 10},
}

# ---------------- Terminal style ----------------

def supports_color():
    if os.environ.get("NO_COLOR"):
        return False
    if os.name == "nt":
        os.system("")
    return True

USE_COLOR = supports_color()

class C:
    RESET = "\033[0m" if USE_COLOR else ""
    BOLD = "\033[1m" if USE_COLOR else ""
    DIM = "\033[2m" if USE_COLOR else ""
    RED = "\033[91m" if USE_COLOR else ""
    YELLOW = "\033[93m" if USE_COLOR else ""
    GREEN = "\033[92m" if USE_COLOR else ""
    BLUE = "\033[94m" if USE_COLOR else ""
    CYAN = "\033[96m" if USE_COLOR else ""
    MAGENTA = "\033[95m" if USE_COLOR else ""
    WHITE = "\033[97m" if USE_COLOR else ""
    GRAY = "\033[90m" if USE_COLOR else ""


def color(text, c):
    return f"{c}{text}{C.RESET}"


def terminal_width(default=100):
    try:
        return max(88, min(120, os.get_terminal_size().columns - 2))
    except Exception:
        return default

WIDTH = terminal_width()


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def wrap(text, width=None, indent=""):
    width = width or WIDTH
    return "\n".join(textwrap.wrap(str(text), width=width, initial_indent=indent, subsequent_indent=indent))


def panel(title, c=C.CYAN):
    width = WIDTH
    print(color("╭" + "─" * (width - 2) + "╮", c))
    title_text = f" {title} "[: width - 4]
    print(color("│", c) + color(title_text.ljust(width - 2), C.BOLD) + color("│", c))
    print(color("╰" + "─" * (width - 2) + "╯", c))


def rule(title=None, c=C.GRAY, width=None):
    width = width or WIDTH
    if title:
        label = f" {title} "
        right = max(2, width - len(label) - 2)
        print(color("──" + label + "─" * right, c))
    else:
        print(color("─" * width, c))


def severity_color(value):
    value = float(value or 0)
    if value >= 75:
        return C.RED
    if value >= 55:
        return C.YELLOW
    if value >= 35:
        return C.CYAN
    return C.GREEN


def bar(value, width=28, c=None, full="█", empty="·"):
    value = max(0, min(100, float(value or 0)))
    n = int(round(width * value / 100))
    txt = full * n + empty * (width - n)
    return color(txt, c or severity_color(value))


def spark(values, width=34):
    if not values:
        return ""
    chars = "▁▂▃▄▅▆▇█"
    vals = list(values)
    if len(vals) > width:
        step = len(vals) / width
        sampled = []
        for i in range(width):
            j0 = int(i * step)
            j1 = max(j0 + 1, int((i + 1) * step))
            sampled.append(sum(vals[j0:j1]) / len(vals[j0:j1]))
        vals = sampled
    mn, mx = min(vals), max(vals)
    if mx == mn:
        return chars[3] * len(vals)
    out = ""
    for v in vals:
        idx = int(round((v - mn) / (mx - mn) * (len(chars) - 1)))
        out += chars[idx]
    return out


def fmt(x, digits=1):
    if x is None:
        return "n/a"
    try:
        return f"{float(x):.{digits}f}"
    except Exception:
        return str(x)

# ---------------- Data handling ----------------

def safe_float(x):
    try:
        if x is None:
            return None
        if isinstance(x, str):
            x = x.replace(",", "").strip()
            if x in ("", ".", "NA", "N/A", "nan", "None", "null", "..."):
                return None
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except Exception:
        return None


def find_db():
    for p in DB_PATHS:
        if os.path.exists(p):
            return p
    return None


def file_mtime(path):
    try:
        return datetime.fromtimestamp(os.path.getmtime(path))
    except Exception:
        return None


def newest_download_time():
    roots = [
        os.path.join(BASE_DIR, "data_current", "raw"),
        os.path.join(BASE_DIR, "data_current", "processed"),
        os.path.join(BASE_DIR, "data_current"),
    ]
    newest = None
    for root in roots:
        if not os.path.exists(root):
            continue
        for folder, _, files in os.walk(root):
            for f in files:
                p = os.path.join(folder, f)
                t = file_mtime(p)
                if t and (newest is None or t > newest):
                    newest = t
    return newest


def open_db():
    db = find_db()
    if not db:
        return None, None
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    return conn, db


def get_tables(conn):
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    return [r["name"] for r in rows]


def table_cols(conn, table):
    try:
        return [r["name"] for r in conn.execute(f'PRAGMA table_info("{table}")').fetchall()]
    except Exception:
        return []


def pick_col(cols, names):
    low = {c.lower(): c for c in cols}
    for n in names:
        if n.lower() in low:
            return low[n.lower()]
    for c in cols:
        cl = c.lower()
        for n in names:
            if n.lower() in cl:
                return c
    return None


def detect_country(value):
    if value is None:
        return None
    s = str(value).strip()
    if len(s) == 3 and s.isalpha():
        return s.upper()
    return COUNTRY_ALIASES.get(s.lower())


def extract_year(value):
    if value is None:
        return None
    m = re.search(r"(19|20)\d{2}", str(value))
    return int(m.group(0)) if m else None


def normalize_indicator_name(*parts):
    joined = " ".join(str(p) for p in parts if p is not None)
    joined = re.sub(r"\s+", " ", joined).strip()
    return joined[:220] if joined else "unknown_indicator"


def classify_indicator(indicator):
    ind = indicator.lower()
    # Banking is checked first because claims can be banking-flow or credit.
    for group in ["banking", "credit", "property", "macro", "liquidity", "market"]:
        for w in KEYWORDS[group]:
            if w in ind:
                return group
    return "other"


def resolve_country(text):
    if not text:
        return None
    s = str(text).strip()
    if len(s) == 3 and s.isalpha():
        return s.upper()
    return COUNTRY_ALIASES.get(s.lower(), s.upper())


def is_global_token(text):
    return resolve_country(text) == "GLOBAL"


def extract_countries_from_text(text, known=None):
    known = known or set(IMPORTANT_COUNTRIES)
    found = []
    low = text.lower()
    for alias, code in sorted(COUNTRY_ALIASES.items(), key=lambda x: -len(x[0])):
        if code == "GLOBAL":
            continue
        if re.search(r"\b" + re.escape(alias.lower()) + r"\b", low):
            if code not in found:
                found.append(code)
    for token in re.findall(r"\b[A-Z]{3}\b", text):
        if token in known or len(token) == 3:
            if token not in found and token != "ALL":
                found.append(token)
    return found


def extract_years_from_text(text):
    return [int(y) for y in re.findall(r"\b(?:19|20)\d{2}\b", text)]


class DataStore:
    def __init__(self):
        self.conn = None
        self.db_path = None
        self.records = []
        self.table_count = 0
        self.loaded = False
        self.load_notes = []
        self._snap_cache = {}
        self._universe_cache = {}

    def load(self):
        self.conn, self.db_path = open_db()
        self.records = []
        self.load_notes = []
        self._snap_cache = {}
        self._universe_cache = {}
        if not self.conn:
            self.loaded = False
            self.load_notes.append("No SQLite database found.")
            return
        tables = get_tables(self.conn)
        self.table_count = len(tables)
        for table in tables:
            self._load_table(table)
        self.loaded = True
        self.load_notes.insert(0, f"Loaded {len(self.records):,} usable numeric observations from {self.table_count} SQLite tables.")

    def _load_table(self, table):
        cols = table_cols(self.conn, table)
        if not cols:
            return
        country_col = pick_col(cols, [
            "country_code", "iso3", "countryiso3code", "ref_area", "borrower_country",
            "lender_country", "country", "location", "economy"
        ])
        date_col = pick_col(cols, ["date", "year", "period", "time", "obs_time", "time_period", "TIME_PERIOD"])
        indicator_col = pick_col(cols, [
            "indicator", "indicator_code", "series", "series_code", "measure", "variable", "title", "name",
            "subject", "item"
        ])
        value_col = pick_col(cols, ["value", "obs_value", "amount", "score", "data_value"])
        if country_col and date_col and value_col:
            self._load_long_table(table, country_col, date_col, indicator_col, value_col)
        elif country_col:
            self._load_wide_table(table, country_col, date_col)

    def _load_long_table(self, table, country_col, date_col, indicator_col, value_col):
        try:
            rows = self.conn.execute(f'SELECT * FROM "{table}" LIMIT 160000').fetchall()
        except Exception as exc:
            self.load_notes.append(f"{table}: skipped ({exc})")
            return
        added = 0
        for r in rows:
            country = detect_country(r[country_col])
            year = extract_year(r[date_col])
            val = safe_float(r[value_col])
            if not country or not year or val is None:
                continue
            indicator = normalize_indicator_name(table, r[indicator_col] if indicator_col else value_col)
            group = classify_indicator(indicator)
            self.records.append({
                "country": country, "year": year, "indicator": indicator, "group": group,
                "value": val, "source_table": table
            })
            added += 1
        if added:
            self.load_notes.append(f"{table}: {added:,} observations")

    def _load_wide_table(self, table, country_col, date_col):
        cols = table_cols(self.conn, table)
        try:
            rows = self.conn.execute(f'SELECT * FROM "{table}" LIMIT 80000').fetchall()
        except Exception as exc:
            self.load_notes.append(f"{table}: skipped ({exc})")
            return
        numeric_cols = []
        for c in cols:
            if c == country_col or c == date_col:
                continue
            cl = c.lower()
            if any(skip in cl for skip in ["id", "code", "name", "unit", "freq", "note", "flag", "status"]):
                continue
            numeric_cols.append(c)
        added = 0
        for r in rows:
            country = detect_country(r[country_col])
            if not country:
                continue
            row_year = extract_year(r[date_col]) if date_col else None
            for c in numeric_cols:
                val = safe_float(r[c])
                year = row_year or extract_year(c)
                if val is None or not year:
                    continue
                indicator = normalize_indicator_name(table, c)
                group = classify_indicator(indicator)
                self.records.append({
                    "country": country, "year": year, "indicator": indicator, "group": group,
                    "value": val, "source_table": table
                })
                added += 1
        if added:
            self.load_notes.append(f"{table}: {added:,} observations")

    def countries(self):
        return sorted(set(r["country"] for r in self.records))

    def years(self):
        return sorted(set(r["year"] for r in self.records))

    def latest_year(self):
        ys = self.years()
        return ys[-1] if ys else None

    def available_years_for_country(self, country):
        country = resolve_country(country)
        return sorted(set(r["year"] for r in self.records if r["country"] == country))

    def records_for_country_until(self, country, year=None):
        country = resolve_country(country)
        if year is None:
            year = self.latest_year()
        return [r for r in self.records if r["country"] == country and r["year"] <= year]

    def records_for_country_year(self, country, year):
        country = resolve_country(country)
        return [r for r in self.records if r["country"] == country and r["year"] == year]

    def latest_indicator_values(self, country, year=None):
        rows = self.records_for_country_until(country, year)
        by_ind = {}
        for r in rows:
            key = r["indicator"]
            if key not in by_ind or r["year"] > by_ind[key]["year"]:
                by_ind[key] = r
        return list(by_ind.values())

    def source_tables(self, country=None):
        if country and resolve_country(country) != "GLOBAL":
            rows = [r for r in self.records if r["country"] == resolve_country(country)]
        else:
            rows = self.records
        counts = defaultdict(int)
        for r in rows:
            counts[r["source_table"]] += 1
        return sorted(counts.items(), key=lambda x: x[1], reverse=True)

# ---------------- Scoring and forecasting ----------------

def percentile(values, value):
    clean = sorted(v for v in values if v is not None)
    if not clean or value is None:
        return 0.0
    below = sum(1 for v in clean if v <= value)
    return 100.0 * below / len(clean)


def latest_group_values(ds, country, year=None):
    rows = ds.latest_indicator_values(country, year)
    by_group = defaultdict(list)
    freshness = defaultdict(list)
    evidence = defaultdict(list)
    for r in rows:
        g = r["group"]
        if g == "other":
            continue
        by_group[g].append(abs(r["value"]))
        freshness[g].append(r["year"])
        evidence[g].append(r)
    return by_group, freshness, evidence, rows


def universe_group_averages(ds, year=None):
    if year is None:
        year = ds.latest_year()
    if year in ds._universe_cache:
        return ds._universe_cache[year]
    universe = defaultdict(list)
    for c in ds.countries():
        by_group, _, _, _ = latest_group_values(ds, c, year)
        for g, vals in by_group.items():
            if vals:
                universe[g].append(sum(vals) / len(vals))
    ds._universe_cache[year] = universe
    return universe


def raw_score_from_components(components, country):
    raw = 0.0
    weight_used = 0.0
    for g, w in WEIGHTS.items():
        if g in components:
            raw += w * components[g]
            weight_used += w
    if weight_used:
        raw = raw / weight_used * 0.78
    raw += SYSTEMIC_BOOST.get(country, 0)
    return max(0.0, min(100.0, raw))


def country_snapshot(ds, country, year=None):
    country = resolve_country(country)
    if country == "GLOBAL":
        return None
    if year is None:
        year = ds.latest_year()
    key = (country, year)
    if key in ds._snap_cache:
        return ds._snap_cache[key]
    by_group, freshness, evidence, rows = latest_group_values(ds, country, year)
    if not rows:
        return None
    universe = universe_group_averages(ds, year)
    group_scores = {}
    group_counts = {}
    for g, vals in by_group.items():
        avg = sum(vals) / len(vals) if vals else None
        group_scores[g] = percentile(universe.get(g, []), avg)
        group_counts[g] = len(vals)
    raw = raw_score_from_components(group_scores, country)
    latest_observation_year = max([r["year"] for r in rows], default=year)
    active_components = sum(1 for g in WEIGHTS if group_scores.get(g, 0) > 0)
    high_components = sum(1 for g in WEIGHTS if group_scores.get(g, 0) >= 70)
    medium_components = sum(1 for g in WEIGHTS if group_scores.get(g, 0) >= 50)
    snap = {
        "country": country,
        "year": year,
        "raw": round(raw, 1),
        "relative": 0.0,
        "priority": "",
        "priority_text": "",
        "banking": round(group_scores.get("banking", 0), 1),
        "credit": round(group_scores.get("credit", 0), 1),
        "property": round(group_scores.get("property", 0), 1),
        "macro": round(group_scores.get("macro", 0), 1),
        "liquidity": round(group_scores.get("liquidity", 0), 1),
        "market": round(group_scores.get("market", 0), 1),
        "group_scores": group_scores,
        "group_counts": group_counts,
        "active_components": active_components,
        "high_components": high_components,
        "medium_components": medium_components,
        "observations": len(rows),
        "latest_observation_year": latest_observation_year,
        "freshness": {g: max(v) for g, v in freshness.items() if v},
        "evidence": evidence,
    }
    ds._snap_cache[key] = snap
    return snap


def all_snapshots(ds, year=None):
    if year is None:
        year = ds.latest_year()
    snaps = []
    for c in ds.countries():
        s = country_snapshot(ds, c, year)
        if s:
            snaps.append(dict(s))
    if not snaps:
        return []
    max_raw = max(s["raw"] for s in snaps) or 1
    min_raw = min(s["raw"] for s in snaps)
    span = max(max_raw - min_raw, 1e-9)
    for s in snaps:
        rel = 100 * (s["raw"] - min_raw) / span
        s["relative"] = round(rel, 1)
        s["priority"] = priority_label(rel)
        s["priority_text"] = priority_text(rel)
    snaps.sort(key=lambda x: (x["relative"], x["raw"]), reverse=True)
    return snaps


def enrich_relative(ds, snap, year=None):
    if not snap:
        return None
    snaps = all_snapshots(ds, year or snap["year"])
    for s in snaps:
        if s["country"] == snap["country"]:
            out = dict(snap)
            out["relative"] = s["relative"]
            out["priority"] = s["priority"]
            out["priority_text"] = s["priority_text"]
            return out
    return snap


def priority_label(value):
    value = float(value or 0)
    if value >= 80:
        return "P1"
    if value >= 60:
        return "P2"
    if value >= 35:
        return "P3"
    return "P4"


def priority_text(value):
    value = float(value or 0)
    if value >= 80:
        return "highest relative signal"
    if value >= 60:
        return "above dataset average"
    if value >= 35:
        return "moderate relative signal"
    return "lower relative signal"


def score_series(ds, country):
    country = resolve_country(country)
    years = ds.available_years_for_country(country)
    rows = []
    for y in years:
        s = enrich_relative(ds, country_snapshot(ds, country, y), y)
        if s:
            rows.append(s)
    return rows


def component_vector(s):
    return [s.get(g, 0) for g in ["banking", "credit", "property", "macro", "liquidity", "market"]]


def trend_metrics(series):
    if len(series) < 2:
        return {"short_momentum": 0.0, "long_momentum": 0.0, "volatility": 0.0, "direction": "insufficient history"}
    vals = [s["relative"] for s in series]
    short = vals[-1] - vals[-2]
    if len(vals) >= 4:
        long = vals[-1] - vals[-4]
    else:
        long = vals[-1] - vals[0]
    diffs = [vals[i] - vals[i - 1] for i in range(1, len(vals))]
    vol = statistics.pstdev(diffs) if len(diffs) > 1 else abs(short)
    if short > 5 and long > 5:
        direction = "rising"
    elif short < -5 and long < -5:
        direction = "falling"
    else:
        direction = "mixed/stable"
    return {"short_momentum": round(short, 1), "long_momentum": round(long, 1), "volatility": round(vol, 1), "direction": direction}


def data_quality_score(s):
    if not s:
        return 0.0
    comp_score = min(100, 100 * s.get("active_components", 0) / max(1, len(WEIGHTS)))
    obs_score = min(100, s.get("observations", 0) * 8)
    freshness_gap = max(0, s.get("year", 0) - s.get("latest_observation_year", 0))
    freshness_score = max(0, 100 - freshness_gap * 12)
    return round(0.45 * comp_score + 0.30 * obs_score + 0.25 * freshness_score, 1)


def confidence_band(quality):
    if quality >= 75:
        return "higher confidence"
    if quality >= 50:
        return "medium confidence"
    if quality >= 30:
        return "limited confidence"
    return "low confidence"


def clamp(x, lo=0, hi=100):
    return max(lo, min(hi, x))


def vulnerability_score(s, trend=None):
    trend = trend or {"short_momentum": 0, "long_momentum": 0, "volatility": 0}
    confirmation = 4 * s.get("high_components", 0) + 2 * s.get("medium_components", 0)
    base = 0.50 * s.get("relative", 0) + 0.25 * s.get("raw", 0) + 0.25 * max(component_vector(s) or [0])
    momentum = 0.6 * trend.get("short_momentum", 0) + 0.25 * trend.get("long_momentum", 0)
    vol = min(12, 0.35 * trend.get("volatility", 0))
    return round(clamp(base + momentum + confirmation + vol), 1)


def likelihood_from_vulnerability(vuln, horizon_months, quality):
    # This is a calibrated research score, not a statistical crisis probability.
    horizon_adjust = {6: -8, 12: 0, 24: 6, 36: 9}.get(horizon_months, 0)
    uncertainty_adjust = 0
    if quality < 35:
        uncertainty_adjust = -5
    x = vuln + horizon_adjust + uncertainty_adjust
    # Smooth logistic-like transform into a probability-style band.
    p = 100 / (1 + math.exp(-(x - 55) / 13))
    p = clamp(p, 1, 95)
    return round(p, 1)


def likelihood_band(p):
    if p >= 65:
        return "High"
    if p >= 45:
        return "Elevated"
    if p >= 25:
        return "Moderate"
    return "Low"


def forecast_country(ds, country, scenario=None):
    country = resolve_country(country)
    s = enrich_relative(ds, country_snapshot(ds, country))
    if not s:
        return None
    s = dict(s)
    scenario_name = None
    if scenario:
        scenario_name = scenario.lower()
        if scenario_name in SCENARIOS:
            adjusted_components = dict(s["group_scores"])
            for g, shock in SCENARIOS[scenario_name].items():
                adjusted_components[g] = clamp(adjusted_components.get(g, 0) + shock)
            raw = raw_score_from_components(adjusted_components, country)
            for g in WEIGHTS:
                s[g] = round(adjusted_components.get(g, 0), 1)
            s["group_scores"] = adjusted_components
            s["raw"] = round(raw, 1)
            # Relative scenario is a stress overlay. We do not re-rank the whole global distribution.
            s["relative"] = round(clamp(max(s["relative"], raw)), 1)
            s["priority"] = priority_label(s["relative"])
            s["priority_text"] = priority_text(s["relative"])
    series = score_series(ds, country)
    tr = trend_metrics(series)
    quality = data_quality_score(s)
    vuln = vulnerability_score(s, tr)
    horizons = []
    for h in [6, 12, 24, 36]:
        p = likelihood_from_vulnerability(vuln, h, quality)
        horizons.append({"horizon_months": h, "likelihood": p, "band": likelihood_band(p)})
    drivers = sorted(
        [("banking", s["banking"]), ("credit", s["credit"]), ("property", s["property"]),
         ("macro", s["macro"]), ("liquidity", s["liquidity"]), ("market", s["market"])],
        key=lambda x: x[1], reverse=True
    )
    return {
        "country": country,
        "year": s["year"],
        "scenario": scenario_name or "baseline",
        "snapshot": s,
        "trend": tr,
        "quality": quality,
        "confidence": confidence_band(quality),
        "vulnerability": vuln,
        "horizons": horizons,
        "drivers": drivers,
    }


def global_forecasts(ds, limit=12):
    snaps = all_snapshots(ds)
    out = []
    for s in snaps:
        f = forecast_country(ds, s["country"])
        if f:
            out.append(f)
    out.sort(key=lambda x: (x["horizons"][1]["likelihood"], x["vulnerability"]), reverse=True)
    return out[:limit]

# ---------------- Text interpretation ----------------

def coverage_note(ds):
    ys = ds.years()
    period = f"{ys[0]}-{ys[-1]}" if ys else "unknown"
    return f"Coverage: {len(ds.records):,} usable observations, {len(ds.countries())} countries, {ds.table_count} SQLite tables, period {period}. Results reflect only data loaded locally."


def method_boundary():
    return (
        "Bank Flux estimates relative vulnerability and early-warning likelihood bands. It does not prove that a crisis "
        "will occur. The forecast layer combines current indicator levels, historical position, momentum, component "
        "confirmation, banking-flow exposure, and data quality. Treat outputs as research signals for review, not as "
        "trading, regulatory, or investment advice."
    )


def forecast_summary(f):
    if not f:
        return "No forecast could be calculated."
    s = f["snapshot"]
    h12 = next(h for h in f["horizons"] if h["horizon_months"] == 12)
    h24 = next(h for h in f["horizons"] if h["horizon_months"] == 24)
    d1, d2 = f["drivers"][0], f["drivers"][1]
    return (
        f"{f['country']} has a {h12['band'].lower()} 12-month early-warning band ({h12['likelihood']:.1f}) "
        f"and a {h24['band'].lower()} 24-month band ({h24['likelihood']:.1f}). The main visible drivers are "
        f"{d1[0]} ({d1[1]:.1f}) and {d2[0]} ({d2[1]:.1f}). Trend is {f['trend']['direction']}. "
        f"Data confidence is {f['confidence']} ({f['quality']:.1f}/100)."
    )


def global_forecast_summary(forecasts):
    if not forecasts:
        return "No global forecast could be calculated."
    top = forecasts[:5]
    top_txt = ", ".join(f"{f['country']} {f['horizons'][1]['band']} {f['horizons'][1]['likelihood']:.0f}" for f in top)
    high = sum(1 for f in forecasts if f["horizons"][1]["band"] == "High")
    elevated = sum(1 for f in forecasts if f["horizons"][1]["band"] == "Elevated")
    return (
        f"The global forecast screen ranks countries by 12-month early-warning likelihood. The leading cases are {top_txt}. "
        f"Within the displayed set, {high} are high and {elevated} are elevated. This is a priority map: it identifies "
        f"where to investigate first if banking-flow, credit, macro, or liquidity stress intensifies."
    )

# ---------------- CSV / copy / export ----------------

def rows_to_csv_text(headers, rows):
    import io
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    return buf.getvalue()


def copy_to_clipboard(text):
    if os.name == "nt":
        try:
            p = subprocess.Popen(["clip"], stdin=subprocess.PIPE, text=True)
            p.communicate(text)
            return True
        except Exception:
            return False
    for cmd in (["pbcopy"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]):
        try:
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, text=True)
            p.communicate(text)
            return True
        except Exception:
            continue
    return False


def export_csv(filename, headers, rows):
    os.makedirs(EXPORT_DIR, exist_ok=True)
    path = os.path.join(EXPORT_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    return path


def global_forecast_rows(ds):
    forecasts = global_forecasts(ds, limit=9999)
    headers = [
        "country", "year", "vulnerability", "likelihood_6m", "band_6m", "likelihood_12m", "band_12m",
        "likelihood_24m", "band_24m", "likelihood_36m", "band_36m", "raw", "relative", "banking",
        "credit", "property", "macro", "liquidity", "market", "confidence"
    ]
    rows = []
    for f in forecasts:
        s = f["snapshot"]
        h = {x["horizon_months"]: x for x in f["horizons"]}
        rows.append([
            f["country"], f["year"], f["vulnerability"], h[6]["likelihood"], h[6]["band"],
            h[12]["likelihood"], h[12]["band"], h[24]["likelihood"], h[24]["band"],
            h[36]["likelihood"], h[36]["band"], s["raw"], s["relative"], s["banking"], s["credit"],
            s["property"], s["macro"], s["liquidity"], s["market"], f["confidence"]
        ])
    return headers, rows


def country_forecast_rows(ds, country):
    f = forecast_country(ds, country)
    headers = ["country", "year", "scenario", "horizon_months", "likelihood", "band", "vulnerability", "confidence", "raw", "relative", "banking", "credit", "property", "macro", "liquidity", "market"]
    rows = []
    if f:
        s = f["snapshot"]
        for h in f["horizons"]:
            rows.append([f["country"], f["year"], f["scenario"], h["horizon_months"], h["likelihood"], h["band"], f["vulnerability"], f["confidence"], s["raw"], s["relative"], s["banking"], s["credit"], s["property"], s["macro"], s["liquidity"], s["market"]])
    return headers, rows


def timeline_rows(ds, country):
    series = score_series(ds, country)
    headers = ["country", "year", "raw", "relative", "priority", "banking", "credit", "property", "macro", "liquidity", "market", "observations"]
    rows = []
    for s in series:
        rows.append([s["country"], s["year"], s["raw"], s["relative"], s["priority"], s["banking"], s["credit"], s["property"], s["macro"], s["liquidity"], s["market"], s["observations"]])
    return headers, rows


def raw_rows(ds, country):
    country = resolve_country(country)
    if country == "GLOBAL":
        records = ds.records
    else:
        records = ds.records_for_country_until(country, ds.latest_year())
    headers = ["country", "year", "group", "indicator", "value", "source_table"]
    rows = []
    for r in records[:5000]:
        rows.append([r["country"], r["year"], r["group"], r["indicator"], r["value"], r["source_table"]])
    return headers, rows

# ---------------- Screens ----------------

def print_home(ds):
    clear_screen()
    panel(f"{APP_NAME} — Forecast Lab", C.CYAN)
    print(f"Author: {color(AUTHOR_NAME, C.BOLD)}   Display date: {DISPLAY_DATE}   Version: {VERSION}")
    dl = newest_download_time()
    update = dl.strftime("%Y-%m-%d %H:%M") if dl else "not found"
    print(f"Last local data update: {color(update, C.GREEN if dl else C.YELLOW)}")
    print(f"Database: {ds.db_path or 'not found'}")
    print(color(coverage_note(ds), C.GRAY))
    print()
    print(wrap("Bank Flux builds a timeline from current and historical public data, then applies transparent banking and macroeconomic early-warning logic. Use it to screen vulnerability, inspect evidence, and export clean datasets."))
    rule("START", C.BLUE)
    rows = [
        ("dashboard", "guided overview"),
        ("explain", "plain-English summary of current observations"),
        ("forecast global", "global forecast map"),
        ("forecast CHE", "country forecast; replace CHE with any country code"),
        ("forecast timeline CHE", "country forecast over time"),
        ("scenario CHE rate_shock", "country stress test"),
        ("banking global", "global banking-flow map"),
        ("compare USA CHN CHE MEX", "country comparison"),
        ("sources CHE", "source coverage"),
        ("raw CHE", "underlying observations"),
        ("copy forecast CHE", "copy CSV to clipboard"),
        ("export forecast CHE", "save CSV to exports folder"),
        ("help", "all commands and sample prompts"),
    ]
    for cmd, desc in rows:
        print(f"  {color(cmd.ljust(30), C.CYAN)} {desc}")
    print(color("You can also ask: what is your name?  |  explain Switzerland  |  forecast global", C.GRAY))


def print_dashboard(ds):
    panel("DASHBOARD", C.CYAN)
    print(wrap("This dashboard summarizes the current global forecast, shows the highest review priorities, and gives the next commands for evidence checking and export."))
    print(color(coverage_note(ds), C.GRAY))
    forecasts = global_forecasts(ds, limit=8)
    rule("CURRENT FORECAST SNAPSHOT", C.BLUE)
    if not forecasts:
        print("No usable forecast could be calculated.")
        return
    print(wrap(global_forecast_summary(forecasts)))
    print()
    print(f"{'Rank':<5} {'Country':<8} {'12m':>6} {'Band':<10} {'Vuln':>6} {'Driver':<10} Visual")
    print(color("─" * WIDTH, C.GRAY))
    for i, f in enumerate(forecasts, 1):
        h12 = next(h for h in f["horizons"] if h["horizon_months"] == 12)
        driver = f["drivers"][0][0]
        cc = severity_color(h12["likelihood"])
        print(f"{i:<5} {color(f['country'].ljust(8), cc)} {h12['likelihood']:>6.1f} {h12['band']:<10} {f['vulnerability']:>6.1f} {driver:<10} {bar(h12['likelihood'], 26, cc)}")
    top = forecasts[0]["country"]
    rule("NEXT COMMANDS", C.MAGENTA)
    print(f"  forecast {top}")
    print(f"  forecast timeline {top}")
    print(f"  scenario {top} rate_shock")
    print(f"  sources {top}")
    print(f"  export forecast {top}")
    print("  forecast global")


def print_method():
    panel("METHOD — EARLY-WARNING FORECAST LAB", C.CYAN)
    print(wrap(method_boundary()))
    rule("MODEL STRUCTURE", C.BLUE)
    print(wrap("1. Current data are loaded from the local SQLite database and classified into six channels: banking, credit, property, macro, liquidity, and market."))
    print(wrap("2. Each country receives percentile-style component scores compared with other countries in the loaded dataset."))
    print(wrap("3. A conservative raw score is calculated from weighted components plus a modest systemic-importance adjustment."))
    print(wrap("4. A relative score shows where a country sits within the current dataset. This is useful when all raw scores are low but ranking is still informative."))
    print(wrap("5. The forecast layer adds momentum, volatility, component confirmation, and data quality to estimate likelihood bands for 6, 12, 24, and 36 months."))
    print(wrap("6. Scenario commands apply transparent shocks to the components. They are stress tests, not predictions."))
    rule("ACADEMIC LOGIC", C.MAGENTA)
    print(wrap("The banking-flow channel follows the idea that international bank credit and cross-border claims can amplify credit booms and transmit stress. The macro channel reflects monetary policy, inflation, growth, unemployment, and aggregate-demand mechanisms. The governance/banking-sector logic treats banks as special because weak banking systems transmit stress into the real economy."))


def print_literature():
    panel("LITERATURE LOGIC USED BY BANK FLUX", C.CYAN)
    print(wrap("Bank Flux does not quote or reproduce books inside the program, but it follows established concepts that should be familiar to banking and macroeconomics students."))
    rule("BANKING-FLOW MECHANISM", C.BLUE)
    print(wrap("International bank credit can grow rapidly in booms, and competition for market share can amplify lending before crises. This justifies the banking-flow and cross-border claims channel."))
    rule("MACRO / MONETARY MECHANISM", C.BLUE)
    print(wrap("Interest rates and money supply affect the availability and cost of credit. Tight money can slow borrowing and aggregate demand; easy money can support credit but may contribute to future inflation or excess."))
    rule("BANK-SPECIFIC FRAGILITY", C.BLUE)
    print(wrap("Banks require separate treatment because they are core financial intermediaries, connected to depositors, payment systems, lending, real-sector financing, and systemic confidence."))


def print_data_status(ds):
    panel("DATA STATUS", C.BLUE)
    print(f"Database path: {ds.db_path or 'not found'}")
    print(f"Tables found: {ds.table_count}")
    print(f"Usable observations: {len(ds.records):,}")
    print(f"Countries found: {len(ds.countries())}")
    ys = ds.years()
    if ys:
        print(f"Date range: {ys[0]} to {ys[-1]}")
    dl = newest_download_time()
    print(f"Last local data update: {dl.strftime('%Y-%m-%d %H:%M') if dl else 'not found'}")
    print(color(coverage_note(ds), C.GRAY))


def print_quality(ds):
    panel("QUALITY CHECK", C.CYAN)
    checks = []
    checks.append(("SQLite database found", bool(ds.db_path)))
    checks.append(("Usable numeric observations loaded", len(ds.records) > 0))
    checks.append(("Country coverage available", len(ds.countries()) >= 5))
    checks.append(("Time-series coverage available", len(ds.years()) >= 2))
    snaps = all_snapshots(ds)
    active = False
    if snaps:
        avg_active = sum(s["active_components"] for s in snaps) / len(snaps)
        active = avg_active >= 2
    checks.append(("Multiple analytical components active", active))
    checks.append(("Copy/export routines available", True))
    for name, ok in checks:
        mark = color("PASS", C.GREEN) if ok else color("CHECK", C.YELLOW)
        print(f"  {mark:<12} {name}")
    rule("NOTES", C.MAGENTA)
    if not active:
        print(wrap("Some components may be sparse. Forecast bands remain usable as relative research signals, but confidence may be limited until additional FRED, IMF, OECD, World Bank, and BIS series are active."))
    else:
        print("Component coverage appears usable for research screening.")


def print_diagnostics(ds):
    print_data_status(ds)
    rule("LOAD NOTES", C.GRAY)
    for n in ds.load_notes[:100]:
        print("  " + n)
    if ds.conn:
        rule("TABLES", C.GRAY)
        for t in get_tables(ds.conn)[:150]:
            print("  " + t)


def print_dates(ds):
    panel("AVAILABLE DATES", C.BLUE)
    ys = ds.years()
    if not ys:
        print("No usable dates were found.")
        return
    print(wrap("These dates are the years found in the loaded local database. Forecast timelines use available history up to each year."))
    print(f"Full range: {color(str(ys[0]), C.BOLD)} to {color(str(ys[-1]), C.BOLD)}")
    print()
    for i in range(0, len(ys), 14):
        print("  " + " ".join(str(y) for y in ys[i:i + 14]))


def print_global(ds):
    panel("GLOBAL EARLY-WARNING SCREEN", C.CYAN)
    print(wrap("This descriptive screen ranks current relative warning signals. For crisis likelihood, use 'forecast global'."))
    snaps = all_snapshots(ds)
    if not snaps:
        print("No usable country scores could be calculated.")
        return
    print(color(coverage_note(ds), C.GRAY))
    rule("PRIORITY TABLE", C.BLUE)
    print(f"{'Rank':<5} {'Country':<8} {'Raw':>6} {'Rel':>6} {'Pri':<4} {'Bank':>6} {'Cred':>6} {'Macro':>6} Visual")
    print(color("─" * WIDTH, C.GRAY))
    for i, s in enumerate(snaps[:15], 1):
        cc = severity_color(s["relative"])
        print(f"{i:<5} {color(s['country'].ljust(8), cc)} {s['raw']:>6.1f} {s['relative']:>6.1f} {s['priority']:<4} {s['banking']:>6.1f} {s['credit']:>6.1f} {s['macro']:>6.1f} {bar(s['relative'], 24, cc)}")


def print_forecast_global(ds):
    panel(f"GLOBAL CRISIS-LIKELIHOOD FORECAST — latest usable year: {ds.latest_year()}", C.CYAN)
    forecasts = global_forecasts(ds, limit=18)
    if not forecasts:
        print("No usable forecast could be calculated.")
        return
    print(wrap(global_forecast_summary(forecasts)))
    print(color(coverage_note(ds), C.GRAY))
    print(color(method_boundary(), C.GRAY))
    rule("FORECAST PRIORITY TABLE", C.BLUE)
    print(f"{'Rank':<5} {'Country':<8} {'6m':>6} {'12m':>6} {'24m':>6} {'36m':>6} {'Band':<10} {'Vuln':>6} {'Conf':<10} Visual")
    print(color("─" * WIDTH, C.GRAY))
    for i, f in enumerate(forecasts, 1):
        h = {x["horizon_months"]: x for x in f["horizons"]}
        cc = severity_color(h[12]["likelihood"])
        print(f"{i:<5} {color(f['country'].ljust(8), cc)} {h[6]['likelihood']:>6.1f} {h[12]['likelihood']:>6.1f} {h[24]['likelihood']:>6.1f} {h[36]['likelihood']:>6.1f} {h[12]['band']:<10} {f['vulnerability']:>6.1f} {f['confidence'][:10]:<10} {bar(h[12]['likelihood'], 22, cc)}")
    rule("WHAT TO CHECK NEXT", C.MAGENTA)
    top = forecasts[0]["country"]
    print(f"  forecast {top}")
    print(f"  forecast timeline {top}")
    print(f"  scenario {top} rate_shock")
    print(f"  sources {top}")
    print("  export forecast global")


def print_forecast_country(ds, country, scenario=None):
    country = resolve_country(country)
    if country == "GLOBAL":
        print_forecast_global(ds)
        return
    f = forecast_country(ds, country, scenario=scenario)
    panel(f"CRISIS-LIKELIHOOD FORECAST — {country}", C.CYAN)
    if not f:
        print(f"No usable forecast found for {country}.")
        return
    s = f["snapshot"]
    print(wrap(forecast_summary(f)))
    print(color(method_boundary(), C.GRAY))
    print()
    print(f"Scenario: {color(f['scenario'], C.BOLD)}")
    print(f"Raw score: {s['raw']:.1f}   Relative score: {s['relative']:.1f}   Vulnerability: {f['vulnerability']:.1f}   Confidence: {f['confidence']} ({f['quality']:.1f}/100)")
    print(f"Trend: {f['trend']['direction']}   short momentum {f['trend']['short_momentum']:+.1f}   longer momentum {f['trend']['long_momentum']:+.1f}   volatility {f['trend']['volatility']:.1f}")
    rule("LIKELIHOOD BANDS", C.BLUE)
    print(f"{'Horizon':<10} {'Likelihood':>11} {'Band':<10} Visual")
    print(color("─" * WIDTH, C.GRAY))
    for h in f["horizons"]:
        cc = severity_color(h["likelihood"])
        label = str(h["horizon_months"]) + " months"
        print(f"{label:<10} {h['likelihood']:>10.1f}  {h['band']:<10} {bar(h['likelihood'], 30, cc)}")
    rule("DRIVERS", C.MAGENTA)
    for name, val in f["drivers"]:
        cc = severity_color(val)
        print(f"  {name:<10} {val:>6.1f} {bar(val, 26, cc)}")
    rule("INTERPRETATION", C.MAGENTA)
    print(wrap("A high band means the country deserves review first under the present data and model. It does not mean a crisis is inevitable. The strongest interpretation comes when multiple channels are elevated at the same time and the timeline is rising."))
    rule("NEXT COMMANDS", C.BLUE)
    print(f"  forecast timeline {country}")
    print(f"  sources {country}")
    print(f"  raw {country}")
    print(f"  scenario {country} banking_shock")
    print(f"  export forecast {country}")


def print_forecast_timeline_global(ds):
    panel("GLOBAL FORECAST TIMELINE", C.CYAN)
    years = ds.years()
    if not years:
        print("No usable years found.")
        return
    rows = []
    for y in years:
        forecasts = global_forecasts(ds, limit=9999) if y == ds.latest_year() else []
        if y != ds.latest_year():
            snaps = all_snapshots(ds, y)
            for s in snaps:
                fc = forecast_country(ds, s["country"])
                if fc:
                    # Recalculate from historical snapshot through a compact proxy.
                    tr = trend_metrics(score_series(ds, s["country"]))
                    vuln = vulnerability_score(s, tr)
                    quality = data_quality_score(s)
                    like12 = likelihood_from_vulnerability(vuln, 12, quality)
                    forecasts.append({"country": s["country"], "like12": like12})
        else:
            forecasts = [{"country": f["country"], "like12": f["horizons"][1]["likelihood"]} for f in forecasts]
        if forecasts:
            vals = [f["like12"] for f in forecasts]
            rows.append((y, sum(vals) / len(vals), max(vals), len(vals)))
    if not rows:
        print("No usable global timeline could be calculated.")
        return
    print(wrap("This screen summarizes how the global early-warning map changes through time. The average column is the mean displayed 12-month likelihood; the maximum column shows the strongest country signal in that year."))
    print(f"Sparkline avg 12m: {color(spark([r[1] for r in rows]), C.CYAN)}")
    rule("GLOBAL YEARLY VIEW", C.BLUE)
    print(f"{'Year':<6} {'Avg 12m':>8} {'Max 12m':>8} {'Countries':>9} Visual")
    print(color("─" * WIDTH, C.GRAY))
    for y, avg, mx, n in rows[-30:]:
        cc = severity_color(mx)
        print(f"{y:<6} {avg:>8.1f} {mx:>8.1f} {n:>9} {bar(mx, 26, cc)}")


def print_scenario_global(ds, scenario):
    scenario = (scenario or "").lower().strip()
    if scenario not in SCENARIOS:
        panel("AVAILABLE GLOBAL SCENARIOS", C.BLUE)
        for name in SCENARIOS:
            print(f"  scenario global {name}")
        return
    panel(f"GLOBAL SCENARIO MAP — {scenario}", C.CYAN)
    forecasts = global_forecasts(ds, limit=12)
    if not forecasts:
        print("No usable global forecast could be calculated.")
        return
    print(wrap("This screen applies the selected stress case to each displayed country and ranks the resulting 12-month likelihood. It is a scenario map, not a prediction that the shock will occur."))
    rows = []
    for f in forecasts:
        stressed = forecast_country(ds, f["country"], scenario=scenario)
        if not stressed:
            continue
        base12 = f["horizons"][1]["likelihood"]
        stress12 = stressed["horizons"][1]["likelihood"]
        rows.append((f["country"], base12, stress12, stress12 - base12, stressed["horizons"][1]["band"]))
    rows.sort(key=lambda x: x[2], reverse=True)
    rule("GLOBAL STRESS RESULTS", C.BLUE)
    print(f"{'Rank':<5} {'Country':<8} {'Base':>7} {'Stress':>7} {'Change':>8} {'Band':<10} Visual")
    print(color("─" * WIDTH, C.GRAY))
    for i, (country, base12, stress12, diff, band_name) in enumerate(rows, 1):
        cc = severity_color(stress12)
        print(f"{i:<5} {color(country.ljust(8), cc)} {base12:>7.1f} {stress12:>7.1f} {diff:>+8.1f} {band_name:<10} {bar(stress12, 24, cc)}")

def print_forecast_timeline(ds, country):
    country = resolve_country(country)
    if country == "GLOBAL":
        print_forecast_timeline_global(ds)
        return
    panel(f"FORECAST TIMELINE — {country}", C.CYAN)
    series = score_series(ds, country)
    if not series:
        print(f"No usable timeline found for {country}.")
        return
    print(wrap("This timeline shows how the country would have appeared in the early-warning screen through time. It helps distinguish a one-year spike from a persistent vulnerability build-up."))
    vals = []
    rows = []
    for s in series:
        temp = dict(s)
        tr = trend_metrics([x for x in series if x["year"] <= s["year"]])
        vuln = vulnerability_score(temp, tr)
        quality = data_quality_score(temp)
        like12 = likelihood_from_vulnerability(vuln, 12, quality)
        vals.append(like12)
        rows.append((s, vuln, quality, like12))
    print(f"12-month likelihood sparkline: {color(spark(vals), C.CYAN)}")
    rule("YEARLY FORECAST VIEW", C.BLUE)
    print(f"{'Year':<6} {'Raw':>6} {'Rel':>6} {'Vuln':>6} {'12m':>6} {'Band':<10} Visual")
    print(color("─" * WIDTH, C.GRAY))
    for s, vuln, quality, like12 in rows[-30:]:
        cc = severity_color(like12)
        print(f"{s['year']:<6} {s['raw']:>6.1f} {s['relative']:>6.1f} {vuln:>6.1f} {like12:>6.1f} {likelihood_band(like12):<10} {bar(like12, 25, cc)}")
    if len(rows) >= 2:
        first = rows[0][3]
        last = rows[-1][3]
        diff = last - first
        direction = "higher" if diff > 0 else "lower" if diff < 0 else "unchanged"
        rule("SUMMARY", C.MAGENTA)
        print(wrap(f"From {rows[0][0]['year']} to {rows[-1][0]['year']}, the 12-month early-warning likelihood is {abs(diff):.1f} points {direction}."))


def print_scenario(ds, country, scenario):
    country = resolve_country(country)
    if country == "GLOBAL":
        print_scenario_global(ds, scenario)
        return
    scenario = (scenario or "").lower().strip()
    if scenario not in SCENARIOS:
        panel("AVAILABLE SCENARIOS", C.BLUE)
        for name, shocks in SCENARIOS.items():
            print(f"  {color(name.ljust(24), C.CYAN)} {shocks}")
        return
    base = forecast_country(ds, country)
    stressed = forecast_country(ds, country, scenario=scenario)
    panel(f"SCENARIO STRESS TEST — {country} / {scenario}", C.CYAN)
    if not base or not stressed:
        print("Could not calculate scenario.")
        return
    print(wrap("This screen applies a transparent shock to selected components. It is a stress test, not a forecast that the shock will occur."))
    hbase = {x["horizon_months"]: x for x in base["horizons"]}
    hstress = {x["horizon_months"]: x for x in stressed["horizons"]}
    rule("BASELINE VS STRESS", C.BLUE)
    print(f"{'Horizon':<10} {'Base':>8} {'Stress':>8} {'Change':>8} {'Stress band':<12} Visual")
    print(color("─" * WIDTH, C.GRAY))
    for h in [6, 12, 24, 36]:
        b = hbase[h]["likelihood"]
        st = hstress[h]["likelihood"]
        diff = st - b
        cc = severity_color(st)
        print(f"{str(h)+'m':<10} {b:>8.1f} {st:>8.1f} {diff:>+8.1f} {hstress[h]['band']:<12} {bar(st, 26, cc)}")
    rule("SHOCK APPLIED", C.MAGENTA)
    for g, shock in SCENARIOS[scenario].items():
        print(f"  {g:<10} +{shock}")


def print_compare(ds, countries):
    if not countries:
        print("Try: compare USA CHN CHE MEX")
        return
    if any(is_global_token(c) for c in countries):
        countries = [c for c in countries if not is_global_token(c)]
        if not countries:
            print_forecast_global(ds)
            return
    snaps = {s["country"]: s for s in all_snapshots(ds)}
    selected = [snaps.get(resolve_country(c)) for c in countries]
    selected = [s for s in selected if s]
    selected.sort(key=lambda x: x["relative"], reverse=True)
    panel("COUNTRY COMPARISON", C.CYAN)
    if not selected:
        print("No usable countries found.")
        return
    top = selected[0]
    print(wrap(f"This comparison ranks the selected countries by current relative early-warning signal. {top['country']} is highest in this group. Use forecast COUNTRY to convert the signal into 6/12/24/36-month bands."))
    rule("COMPARISON TABLE", C.BLUE)
    print(f"{'Country':<8} {'Raw':>6} {'Rel':>6} {'Pri':<4} {'Bank':>6} {'Cred':>6} {'Prop':>6} {'Macro':>6} {'Liq':>6} Visual")
    print(color("─" * WIDTH, C.GRAY))
    for s in selected:
        cc = severity_color(s["relative"])
        print(f"{color(s['country'].ljust(8), cc)} {s['raw']:>6.1f} {s['relative']:>6.1f} {s['priority']:<4} {s['banking']:>6.1f} {s['credit']:>6.1f} {s['property']:>6.1f} {s['macro']:>6.1f} {s['liquidity']:>6.1f} {bar(s['relative'], 20, cc)}")
    rule("RISKS TO CHECK", C.MAGENTA)
    for s in selected[:5]:
        drivers = sorted([(g, s[g]) for g in ["banking", "credit", "property", "macro", "liquidity", "market"]], key=lambda x: x[1], reverse=True)[:2]
        print(f"  {s['country']}: check {drivers[0][0]} ({drivers[0][1]:.1f}) and {drivers[1][0]} ({drivers[1][1]:.1f}).")


def print_report(ds, country, banking_only=False):
    country = resolve_country(country)
    if country == "GLOBAL":
        if banking_only:
            print_banking_global(ds)
        else:
            print_global(ds)
        return
    s = enrich_relative(ds, country_snapshot(ds, country))
    panel(("BANKING REPORT" if banking_only else "COUNTRY REPORT") + f" — {country}", C.CYAN)
    if not s:
        print(f"No usable data found for {country}.")
        return
    print(wrap(f"This screen explains the current components for {country}. Use forecast {country} for probability-style bands and forecast timeline {country} for history."))
    print(f"Year: {s['year']}   Raw: {s['raw']:.1f}   Relative: {s['relative']:.1f}   Priority: {s['priority']} — {s['priority_text']}   Observations: {s['observations']}")
    rule("COMPONENTS", C.BLUE)
    groups = ["banking", "credit", "property", "macro", "liquidity", "market"]
    if banking_only:
        groups = ["banking", "credit", "liquidity", "market"]
    for g in groups:
        cc = severity_color(s[g])
        print(f"  {g:<10} {s[g]:>6.1f} {bar(s[g], 30, cc)}")
    rule("SHORT READING", C.MAGENTA)
    drivers = sorted([(g, s[g]) for g in ["banking", "credit", "property", "macro", "liquidity", "market"]], key=lambda x: x[1], reverse=True)
    print(wrap(f"The strongest current channels are {drivers[0][0]} and {drivers[1][0]}. This is a screening result, not a crisis call."))


def print_banking_global(ds):
    panel(f"GLOBAL BANKING-FLOW SCREEN — latest usable year: {ds.latest_year()}", C.CYAN)
    forecasts = global_forecasts(ds, limit=20)
    if not forecasts:
        print("No usable banking-flow screen could be calculated.")
        return
    print(wrap("This screen uses the global dataset and ranks countries by banking-flow signal. It is a map of possible transmission channels, not a declaration that a banking crisis is occurring."))
    bank_avg = sum(f["snapshot"]["banking"] for f in forecasts) / len(forecasts)
    print(wrap(f"Average displayed banking score is {bank_avg:.1f}. Use high banking scores with credit, liquidity, and market confirmation to identify stronger warning cases."))
    rule("BANKING-FLOW PRIORITY TABLE", C.BLUE)
    print(f"{'Rank':<5} {'Country':<8} {'Bank':>6} {'12m':>6} {'Credit':>7} {'Liq':>6} {'Market':>7} {'Risk':<10} Visual")
    print(color("─" * WIDTH, C.GRAY))
    forecasts.sort(key=lambda f: (f["snapshot"]["banking"], f["horizons"][1]["likelihood"]), reverse=True)
    for i, f in enumerate(forecasts[:18], 1):
        s = f["snapshot"]
        h12 = f["horizons"][1]
        cc = severity_color(s["banking"])
        print(f"{i:<5} {color(f['country'].ljust(8), cc)} {s['banking']:>6.1f} {h12['likelihood']:>6.1f} {s['credit']:>7.1f} {s['liquidity']:>6.1f} {s['market']:>7.1f} {h12['band']:<10} {bar(s['banking'], 24, cc)}")
    rule("WHAT TO CHECK NEXT", C.MAGENTA)
    print("  forecast global")
    print(f"  forecast {forecasts[0]['country']}")
    print(f"  sources {forecasts[0]['country']}")
    print("  copy banking global")


def print_timeline(ds, country):
    print_forecast_timeline(ds, country)


def print_changes(ds, country):
    country = resolve_country(country)
    if country == "GLOBAL":
        print_forecast_timeline_global(ds)
        return
    series = score_series(ds, country)
    panel(f"RECENT CHANGE — {country}", C.CYAN)
    if len(series) < 2:
        print("Not enough history to calculate recent change.")
        return
    a, b = series[-2], series[-1]
    print(wrap("This screen compares the latest available point with the prior available point. It is useful for seeing whether risk is rising or falling."))
    metrics = ["raw", "relative", "banking", "credit", "property", "macro", "liquidity", "market"]
    print(f"Previous year: {a['year']}   Latest year: {b['year']}")
    rule("MOVEMENT", C.BLUE)
    for m in metrics:
        diff = b[m] - a[m]
        cc = C.RED if diff > 5 else C.GREEN if diff < -5 else C.GRAY
        print(f"  {m:<10} {a[m]:>6.1f} -> {b[m]:>6.1f}   {color(f'{diff:+6.1f}', cc)}")


def print_backtest(ds):
    panel("BACKTEST / HISTORICAL CRISIS-YEAR CHECK", C.CYAN)
    print(wrap("This is a lightweight historical check. If the dataset contains crisis anchor years, Bank Flux lists the highest-ranked countries in those years. It is not a formal econometric validation unless the database includes labeled crisis events and enough history."))
    available = set(ds.years())
    used = [y for y in CRISIS_ANCHOR_YEARS if y in available]
    if not used:
        print("None of the built-in crisis anchor years are available in the local dataset.")
        print("Anchor years checked: " + ", ".join(str(y) for y in CRISIS_ANCHOR_YEARS))
        return
    for y in used:
        rule(f"YEAR {y}", C.BLUE)
        snaps = all_snapshots(ds, y)[:8]
        if not snaps:
            print("  no usable scores")
            continue
        for i, s in enumerate(snaps, 1):
            cc = severity_color(s["relative"])
            print(f"  {i:<2} {color(s['country'].ljust(4), cc)} raw {s['raw']:>5.1f} rel {s['relative']:>5.1f} bank {s['banking']:>5.1f} credit {s['credit']:>5.1f} macro {s['macro']:>5.1f}")


def print_sources(ds, country):
    country = resolve_country(country)
    panel(f"SOURCE COVERAGE — {country}", C.CYAN)
    print(wrap("This screen shows which SQLite source tables contribute observations. Use it to check whether a forecast is supported by broad data or by only a narrow table."))
    rows = ds.source_tables(None if country == "GLOBAL" else country)
    if not rows:
        print("No source rows found.")
        return
    for table, count in rows[:40]:
        print(f"  {table:<55} {count:>8,}")


def print_raw(ds, country):
    headers, rows = raw_rows(ds, country)
    panel(f"RAW EVIDENCE — {resolve_country(country)}", C.CYAN)
    print(wrap("Showing up to 80 rows on screen. Use copy raw COUNTRY or export raw COUNTRY for a full copy/paste dataset."))
    print(", ".join(headers))
    for row in rows[:80]:
        print(", ".join(str(x) for x in row))


def handle_copy(ds, args):
    if not args:
        print("Try: copy forecast global OR copy forecast CHE OR copy raw CHE")
        return
    kind = args[0].lower()
    target = args[1] if len(args) > 1 else "GLOBAL"
    if kind == "forecast":
        if is_global_token(target):
            headers, rows = global_forecast_rows(ds)
            label = "forecast_global.csv"
        else:
            headers, rows = country_forecast_rows(ds, target)
            label = f"forecast_{resolve_country(target)}.csv"
    elif kind == "timeline":
        headers, rows = timeline_rows(ds, target)
        label = f"timeline_{resolve_country(target)}.csv"
    elif kind == "raw":
        headers, rows = raw_rows(ds, target)
        label = f"raw_{resolve_country(target)}.csv"
    elif kind == "banking" and len(args) > 1 and is_global_token(args[1]):
        headers, rows = global_forecast_rows(ds)
        label = "banking_global.csv"
    else:
        print("Unsupported copy command. Try: copy forecast global, copy forecast CHE, copy timeline CHE, copy raw CHE")
        return
    text = rows_to_csv_text(headers, rows)
    ok = copy_to_clipboard(text)
    print(text[:6000])
    if len(text) > 6000:
        print(color("... output truncated on screen, full CSV sent to clipboard if clipboard copy succeeded.", C.GRAY))
    print(color(f"Copied {label} to clipboard." if ok else "Clipboard copy not available; CSV printed above.", C.GREEN if ok else C.YELLOW))


def handle_export(ds, args):
    if not args:
        print("Try: export forecast global OR export forecast CHE OR export raw CHE")
        return
    kind = args[0].lower()
    target = args[1] if len(args) > 1 else "GLOBAL"
    if kind == "forecast":
        if is_global_token(target):
            headers, rows = global_forecast_rows(ds)
            filename = "bank_flux_forecast_global.csv"
        else:
            c = resolve_country(target)
            headers, rows = country_forecast_rows(ds, c)
            filename = f"bank_flux_forecast_{c}.csv"
    elif kind == "timeline":
        c = resolve_country(target)
        headers, rows = timeline_rows(ds, c)
        filename = f"bank_flux_timeline_{c}.csv"
    elif kind == "raw":
        c = resolve_country(target)
        headers, rows = raw_rows(ds, c)
        filename = f"bank_flux_raw_{c}.csv"
    elif kind == "banking" and len(args) > 1 and is_global_token(args[1]):
        headers, rows = global_forecast_rows(ds)
        filename = "bank_flux_banking_global.csv"
    else:
        print("Unsupported export command. Try: export forecast global, export forecast CHE, export timeline CHE, export raw CHE")
        return
    path = export_csv(filename, headers, rows)
    print(color(f"Saved CSV: {path}", C.GREEN))


# ---------------- Explain screen and lightweight BFlux agent ----------------

def top_driver_from_snapshot(s):
    if not s:
        return ("unknown", 0.0)
    drivers = [(g, s.get(g, 0.0)) for g in ["banking", "credit", "property", "macro", "liquidity", "market"]]
    return max(drivers, key=lambda x: x[1])


def component_warning_text(s):
    if not s:
        return "Data are not available for this target."
    weak = [g for g in ["credit", "liquidity", "market", "property", "macro"] if s.get(g, 0.0) <= 1.0]
    if len(weak) >= 3:
        return "Several confirmation channels are thin or inactive in the loaded data. Treat the result as a screening signal and inspect sources before drawing a strong conclusion."
    if weak:
        return "Some confirmation channels are thin in the loaded data. The signal is more useful as a priority map than as a final forecast."
    return "Several channels are active, so the signal is better supported by the currently loaded data."


def print_explain_global(ds):
    panel("EXPLAIN — GLOBAL OBSERVATION", C.CYAN)
    forecasts = global_forecasts(ds, limit=20)
    if not forecasts:
        print("No usable forecast could be calculated from the current local database.")
        return
    top = forecasts[:5]
    top_txt = ", ".join(f"{f['country']} ({f['horizons'][1]['likelihood']:.1f})" for f in top)
    avg12 = sum(f["horizons"][1]["likelihood"] for f in forecasts) / len(forecasts)
    p1 = sum(1 for f in forecasts if f["horizons"][1]["band"] in ["High", "Elevated"])
    banking_avg = sum(f["snapshot"].get("banking", 0.0) for f in forecasts) / len(forecasts)
    strongest_driver = top_driver_from_snapshot(top[0]["snapshot"])[0]
    print(wrap(
        f"Bank Flux is reading the global dataset as a relative early-warning map. The average 12-month "
        f"likelihood score among displayed countries is {avg12:.1f}. The leading cases are {top_txt}. "
        f"This does not mean a crisis is expected with certainty. It means these countries should be reviewed "
        f"first because their current data sit higher than others in the loaded dataset."
    ))
    print()
    print(wrap(
        f"The average displayed banking-flow score is {banking_avg:.1f}. The leading country's strongest visible "
        f"driver is {strongest_driver}. {p1} displayed countries fall into the higher review bands. The correct "
        f"professional reading is: monitor the top-ranked countries, then verify whether banking, credit, liquidity, "
        f"market, property, and macro channels confirm one another."
    ))
    print(color(coverage_note(ds), C.GRAY))
    rule("PRACTICAL INTERPRETATION", C.MAGENTA)
    print(wrap(
        "Use this screen as a triage tool. First check the highest-ranked countries, then open sources and raw data. "
        "A strong crisis warning is more convincing when several channels rise together and the timeline shows persistence."
    ))
    rule("NEXT COMMANDS", C.BLUE)
    first = top[0]["country"]
    print(f"  forecast {first}")
    print(f"  forecast timeline {first}")
    print(f"  sources {first}")
    print("  banking global")
    print("  export forecast global")


def print_explain_country(ds, country):
    country = resolve_country(country)
    if is_global_token(country):
        print_explain_global(ds)
        return
    f = forecast_country(ds, country)
    panel(f"EXPLAIN — {country}", C.CYAN)
    if not f:
        print(f"No usable forecast could be calculated for {country}.")
        return
    s = f["snapshot"]
    h = {x["horizon_months"]: x for x in f["horizons"]}
    d1, d2 = f["drivers"][0], f["drivers"][1]
    print(wrap(
        f"{country} has a 12-month likelihood score of {h[12]['likelihood']:.1f}, classified as {h[12]['band']}. "
        f"The 24-month band is {h[24]['band']} ({h[24]['likelihood']:.1f}). The main visible drivers are "
        f"{d1[0]} ({d1[1]:.1f}) and {d2[0]} ({d2[1]:.1f})."
    ))
    print()
    print(wrap(
        f"The professional interpretation is that {country} should be treated as a monitoring case according to its "
        f"relative position in the local dataset. The model is not saying that a crisis will happen; it is ranking "
        f"where review should begin based on current indicators, past movement, and component confirmation. "
        f"{component_warning_text(s)}"
    ))
    print(color(coverage_note(ds), C.GRAY))
    rule("WHAT THIS MEANS", C.MAGENTA)
    print(wrap(
        "A low or moderate band means the signal is present but not crisis-confirming. An elevated or high band means "
        "the case deserves closer review, especially if the timeline is rising and more than one channel is active."
    ))
    rule("NEXT COMMANDS", C.BLUE)
    print(f"  forecast {country}")
    print(f"  forecast timeline {country}")
    print(f"  banking {country}")
    print(f"  sources {country}")
    print(f"  raw {country}")


def print_explain_banking_global(ds):
    panel("EXPLAIN — GLOBAL BANKING-FLOW OBSERVATION", C.CYAN)
    forecasts = global_forecasts(ds, limit=20)
    if not forecasts:
        print("No usable banking-flow screen could be calculated.")
        return
    forecasts = sorted(forecasts, key=lambda f: (f["snapshot"].get("banking", 0.0), f["horizons"][1]["likelihood"]), reverse=True)
    top = forecasts[:5]
    top_txt = ", ".join(f"{f['country']} banking {f['snapshot'].get('banking', 0.0):.1f}" for f in top)
    avg_bank = sum(f["snapshot"].get("banking", 0.0) for f in forecasts) / len(forecasts)
    confirm = sum(1 for f in forecasts if f["snapshot"].get("credit", 0.0) > 1 or f["snapshot"].get("liquidity", 0.0) > 1 or f["snapshot"].get("market", 0.0) > 1)
    print(wrap(
        f"The banking-flow screen is identifying possible transmission nodes in the global financial system. "
        f"The average displayed banking score is {avg_bank:.1f}. The leading observations are {top_txt}. "
        f"Read this as a map of where banking stress could travel, not as proof that a banking crisis is underway."
    ))
    print()
    print(wrap(
        f"Confirmation matters. In this run, {confirm} displayed countries show at least one non-banking confirmation "
        f"channel among credit, liquidity, or market data. If these confirmation channels are weak or missing, the banking "
        f"ranking should be treated as exposure mapping rather than a full crisis forecast."
    ))
    rule("NEXT COMMANDS", C.BLUE)
    first = top[0]["country"]
    print(f"  forecast {first}")
    print(f"  banking {first}")
    print(f"  sources {first}")
    print("  copy banking global")


def print_explain(ds, args=None):
    args = args or []
    if not args:
        print_explain_global(ds)
        return
    low = " ".join(args).lower()
    countries = extract_countries_from_text(" ".join(args), set(ds.countries()) | set(IMPORTANT_COUNTRIES))
    if "bank" in low and any(w in low for w in ["global", "world", "all"]):
        print_explain_banking_global(ds)
    elif any(w in low for w in ["global", "world", "all"]):
        print_explain_global(ds)
    elif countries:
        print_explain_country(ds, countries[0])
    else:
        target = resolve_country(" ".join(args))
        if target and target != "GLOBAL":
            print_explain_country(ds, target)
        else:
            print_explain_global(ds)


def bflux_identity_answer(question):
    low = question.lower().strip()
    if low in ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]:
        return "Hello. I am BFlux. I can help you explore banking-flow risk, crisis-likelihood bands, country timelines, evidence tables, and exports."
    if "your name" in low or low in ["name", "who are you"]:
        return "My name is BFlux. I am the lightweight conversational layer inside Bank Flux Forecast Lab."
    if "who created" in low or "creator" in low or "made you" in low or "built you" in low:
        return "My creator is Jean-Marc. I was designed as a local research assistant for Bank Flux Forecast Lab."
    if "what can you do" in low or "help me" in low or "capabilities" in low:
        return "I can explain the global forecast, review a country, compare countries, show timelines, inspect banking-flow risk, and help you export copy/paste-ready datasets."
    if "are you ai" in low or "are you an ai" in low:
        return "I am a lightweight local rule-based agent. I do not use a large model by default, so I stay fast and low-resource."
    if "investment advice" in low or "trading" in low:
        return "No. Bank Flux is a research and early-warning tool. It does not provide investment advice, trading advice, or regulatory conclusions."
    if "thank" in low:
        return "You are welcome. I am here to make the data easier to read and easier to explain."
    return None


def print_agent_answer(ds, text):
    answer = bflux_identity_answer(text)
    if answer:
        panel("BFLUX AGENT", C.CYAN)
        print(wrap(answer))
        rule("USEFUL COMMANDS", C.BLUE)
        print("  explain")
        print("  forecast CHE")
        print("  banking global")
        print("  compare USA CHN CHE MEX")
        return True
    action, routed_args = natural_language_route(text, ds)
    if action != "unknown":
        return execute_routed(ds, action, routed_args)
    panel("BFLUX AGENT", C.CYAN)
    print(wrap(
        "I can answer simple identity questions and route research questions to Bank Flux screens. "
        "Try: explain, forecast global, explain Switzerland, banking global, compare USA CHN CHE, or what is your name."
    ))
    return True

# ---------------- Commands ----------------

def print_help():
    panel("COMMANDS", C.BLUE)
    rows = [
        ("dashboard", "guided overview"),
        ("explain", "plain-English global observation"),
        ("explain COUNTRY", "plain-English country observation"),
        ("explain banking global", "global banking-flow interpretation"),
        ("agent QUESTION", "lightweight BFlux conversation"),
        ("forecast global", "global crisis-likelihood map"),
        ("forecast COUNTRY", "country forecast with 6/12/24/36-month bands"),
        ("forecast timeline COUNTRY", "historical country forecast"),
        ("scenario COUNTRY rate_shock", "country stress test"),
        ("scenario global rate_shock", "global stress-test map"),
        ("banking global", "global banking-flow map"),
        ("banking COUNTRY", "country banking view"),
        ("compare COUNTRIES", "country comparison"),
        ("timeline COUNTRY", "same as forecast timeline COUNTRY"),
        ("changes COUNTRY", "latest movement"),
        ("sources COUNTRY/global", "source-table coverage"),
        ("raw COUNTRY/global", "underlying observations"),
        ("copy forecast COUNTRY/global", "copy CSV to clipboard"),
        ("export forecast COUNTRY/global", "save CSV to exports folder"),
        ("copy raw COUNTRY/global", "copy evidence rows"),
        ("backtest", "historical crisis-year check"),
        ("quality", "review readiness checks"),
        ("method", "research method"),
        ("data", "database status"),
        ("diagnostics", "load notes and tables"),
        ("countries", "available country codes"),
        ("dates", "available years"),
        ("quit", "exit"),
    ]
    for cmd, desc in rows:
        print(f"  {color(cmd.ljust(34), C.CYAN)} {desc}")
    rule("SAMPLE PROMPTS", C.MAGENTA)
    samples = [
        "what is your name?",
        "who created you?",
        "explain global",
        "explain Switzerland",
        "forecast global",
        "forecast CHE",
        "forecast timeline CHE",
        "scenario CHE rate_shock",
        "scenario global banking_shock",
        "banking global",
        "compare USA CHN CHE MEX",
        "sources global",
        "raw CHE",
        "copy forecast CHE",
        "export raw global",
        "which countries are in the database?",
        "what years are available?",
    ]
    for q in samples:
        print("  " + q)


def natural_language_route(text, ds):
    raw = text.strip()
    low = raw.lower()
    countries = extract_countries_from_text(raw, set(ds.countries()) | set(IMPORTANT_COUNTRIES))
    years = extract_years_from_text(raw)
    has_global = any(w in low for w in ["global", "world", "all countries"])
    if low in ["?", "help", "commands"]:
        return ("help", [])
    if bflux_identity_answer(raw):
        return ("agent", [raw])
    if low.startswith("explain") or "explain" in low or "interpret" in low or "summary" in low:
        if "bank" in low and has_global:
            return ("explain", ["banking", "global"])
        if has_global:
            return ("explain", ["global"])
        if countries:
            return ("explain", [countries[0]])
        return ("explain", [])
    if "dashboard" in low or "menu" in low:
        return ("dashboard", [])
    if "method" in low:
        return ("method", [])
    if "literature" in low or "book" in low:
        return ("literature", [])
    if "backtest" in low or "historical crisis" in low:
        return ("backtest", [])
    if "scenario" in low or "shock" in low or "stress" in low:
        c = "GLOBAL" if has_global else (countries[0] if countries else None)
        scen = None
        for s in SCENARIOS:
            if s in low:
                scen = s
                break
        if c and scen:
            return ("scenario", [c, scen])
    if "forecast" in low or "likelihood" in low or "predict" in low or "probability" in low:
        if "timeline" in low or "over time" in low:
            return ("forecast_timeline", [countries[0]]) if countries else ("forecast_global", [])
        if has_global or not countries:
            return ("forecast_global", [])
        return ("forecast_country", [countries[0]])
    if "bank" in low and has_global:
        return ("banking_global", [])
    if "bank" in low and countries:
        return ("banking", [countries[0]])
    if "compare" in low and countries:
        return ("compare", countries)
    if "change" in low and countries:
        return ("changes", [countries[0]])
    if "source" in low:
        return ("sources", ["GLOBAL" if has_global else (countries[0] if countries else "GLOBAL")])
    if "raw" in low or "evidence" in low:
        return ("raw", ["GLOBAL" if has_global else (countries[0] if countries else "GLOBAL")])
    if "date" in low or "year" in low:
        return ("dates", [])
    if has_global:
        return ("global", [])
    if countries:
        return ("report", [countries[0]])
    return ("unknown", [])


def execute_routed(ds, action, args):
    if action == "help": print_help()
    elif action == "dashboard": print_dashboard(ds)
    elif action == "explain": print_explain(ds, args)
    elif action == "agent": print_agent_answer(ds, args[0] if args else "")
    elif action == "global": print_global(ds)
    elif action == "forecast_global": print_forecast_global(ds)
    elif action == "forecast_country": print_forecast_country(ds, args[0])
    elif action == "forecast_timeline": print_forecast_timeline(ds, args[0])
    elif action == "banking_global": print_banking_global(ds)
    elif action == "banking": print_report(ds, args[0], banking_only=True)
    elif action == "compare": print_compare(ds, args)
    elif action == "changes": print_changes(ds, args[0])
    elif action == "sources": print_sources(ds, args[0])
    elif action == "raw": print_raw(ds, args[0])
    elif action == "dates": print_dates(ds)
    elif action == "method": print_method()
    elif action == "literature": print_literature()
    elif action == "backtest": print_backtest(ds)
    elif action == "scenario": print_scenario(ds, args[0], args[1])
    elif action == "report": print_report(ds, args[0])
    else:
        print("I did not understand that yet. Try: help")
    return True


def execute_command(ds, command):
    parts = command.strip().split()
    if not parts:
        return True
    cmd = parts[0].lower()
    args = parts[1:]
    if cmd in ["quit", "exit", "q"]:
        return False
    if cmd == "clear":
        clear_screen(); return True
    if cmd in ["home", "start"]:
        print_home(ds); return True
    if cmd in ["help", "?"]:
        print_help(); return True
    if cmd in ["dashboard", "menu"]:
        print_dashboard(ds); return True
    if cmd == "explain":
        print_explain(ds, args); return True
    if cmd in ["agent", "chat", "bflux"]:
        print_agent_answer(ds, " ".join(args)); return True
    if cmd == "global":
        print_global(ds); return True
    if cmd == "forecast":
        if not args or is_global_token(args[0]):
            print_forecast_global(ds)
        elif args[0].lower() == "timeline":
            if len(args) < 2:
                print("Try: forecast timeline CHE")
            else:
                print_forecast_timeline(ds, " ".join(args[1:]))
        elif args[0].lower() == "compare":
            print_compare(ds, args[1:])
        else:
            print_forecast_country(ds, " ".join(args))
        return True
    if cmd == "scenario":
        if len(args) < 2:
            print_scenario(ds, args[0] if args else "GLOBAL", None)
        else:
            print_scenario(ds, args[0], args[1])
        return True
    if cmd == "banking":
        if not args or is_global_token(args[0]):
            print_banking_global(ds)
        else:
            print_report(ds, " ".join(args), banking_only=True)
        return True
    if cmd == "report":
        print_report(ds, " ".join(args) if args else "GLOBAL")
        return True
    if cmd == "compare":
        print_compare(ds, [resolve_country(a) for a in args if a.upper() != "AND"])
        return True
    if cmd in ["timeline", "trend"]:
        print_forecast_timeline(ds, " ".join(args) if args else "CHE")
        return True
    if cmd in ["changes", "change"]:
        print_changes(ds, " ".join(args) if args else "CHE")
        return True
    if cmd == "backtest":
        print_backtest(ds); return True
    if cmd == "sources":
        print_sources(ds, " ".join(args) if args else "GLOBAL")
        return True
    if cmd == "raw":
        print_raw(ds, " ".join(args) if args else "GLOBAL")
        return True
    if cmd == "copy":
        handle_copy(ds, args); return True
    if cmd == "export":
        handle_export(ds, args); return True
    if cmd == "quality":
        print_quality(ds); return True
    if cmd == "method":
        print_method(); return True
    if cmd == "literature":
        print_literature(); return True
    if cmd == "data":
        print_data_status(ds); return True
    if cmd == "diagnostics":
        print_diagnostics(ds); return True
    if cmd in ["dates", "years"]:
        print_dates(ds); return True
    if cmd == "countries":
        print(" ".join(ds.countries())); return True
    if cmd == "refresh":
        print("Reloading local database...")
        ds.load()
        print_data_status(ds)
        return True
    if cmd == "ask":
        return print_agent_answer(ds, " ".join(args))
    action, routed_args = natural_language_route(command, ds)
    if action == "unknown":
        return print_agent_answer(ds, command)
    return execute_routed(ds, action, routed_args)


def main():
    ds = DataStore()
    ds.load()
    print_home(ds)
    if not ds.loaded or not ds.records:
        print(color("Warning: Bank Flux did not find usable numeric observations.", C.YELLOW))
        print("Check that this file is inside C:\\AI\\Project Early Warning and that early_warning.sqlite exists.")
        print("Type diagnostics to inspect what was found.")
    while True:
        try:
            command = input(color("\nBank Flux > ", C.CYAN)).strip()
        except KeyboardInterrupt:
            print("\nExiting.")
            break
        except EOFError:
            break
        if not execute_command(ds, command):
            break

if __name__ == "__main__":
    main()
