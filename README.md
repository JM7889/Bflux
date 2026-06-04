\# Project Early Warning



Project Early Warning is a lightweight public-data research tool for financial-crisis early warning and country banking-exposure analysis.



The project does not predict crises with certainty. It collects public data, calculates transparent indicators, scores risk channels, and explains the evidence.



\## Current version



Version 1 fetches World Bank public macro data and produces a basic country risk snapshot.



Current indicators:



\- GDP

\- Inflation

\- Current-account balance



\## Planned next step



Add BIS data:



\- BIS Consolidated Banking Statistics

\- BIS Locational Banking Statistics

\- BIS credit-to-GDP gaps

\- BIS Debt Service Ratios

\- BIS global liquidity indicators



\## Commands



```powershell

python src/main.py update-data --country TUR

python src/main.py country TUR

python src/main.py exposure TUR

