# BFlux / Bank Flux Forecast Lab

BFlux is a local public-data early-warning research console for studying financial-crisis vulnerability. It combines current macro-financial data, banking-flow indicators, country timelines, scenario shocks, historical crisis cases, and backtesting-style checks.

BFlux does not predict crises with certainty. It produces transparent vulnerability bands and evidence screens for research review.

## Quick start

```powershell
python fetch_bflux_data.py --crises
python fetch_bflux_data.py --worldbank
python bank_flux.py
```

## Core workflow

```text
full
forecast calibrated global
forecast calibrated USA
crises
case USA 2008
backtest crises
scenario global banking_shock
scenario USA rate_shock
compare USA CHN CHE MEX
audit USA
sources USA
raw USA
```

## What the model does

BFlux organizes indicators into six channels:

- banking-flow exposure
- credit pressure
- property and housing pressure
- macroeconomic stress
- liquidity and funding pressure
- market stress

The Crisis Memory module adds known financial-crisis cases and uses them for case review, calibrated forecasts, and pre-crisis backtest diagnostics.

## Data

The program expects a local SQLite database at:

```text
data_current/processed/early_warning.sqlite
```

The fetcher can create/update tables from Crisis Memory and World Bank data. Optional FRED data requires a `.env` file containing `FRED_API_KEY=your_key_here`. BIS raw downloads may be large and are kept local.

## Important commands

```text
help                         command list
full                         complete visual review
forecast calibrated global   global crisis-vulnerability map
forecast calibrated COUNTRY  country forecast using Crisis Memory
crises                       list historical crisis cases
case COUNTRY YEAR            inspect a crisis case
backtest crises              check warning signals before known crises
scenario COUNTRY rate_shock  country stress test
audit COUNTRY                verify data, drivers, confidence, and evidence
sources COUNTRY              source-table coverage
raw COUNTRY                  underlying observations
```

## Academic boundary

BFlux is a research prototype. It is not investment advice, regulatory advice, or a deterministic crisis-prediction system. Scores should be read as relative vulnerability and early-warning bands.

## Author

Jean-Marc
