# Delhi data provenance

- Publisher: UrbanEmissions.Info, compiling CPCB daily AQI bulletins.
- Download: https://urbanemissions.info/wp-content/uploads/ncap/aqibulletins/Delhi_AQIBulletins.csv
- Description: https://urbanemissions.info/india-air-quality/india-ncap-aqi-indian-cities-2015-2023/
- Archived all-India compilation: https://doi.org/10.5281/zenodo.11146316
- Downloaded: 2026-10-06. File: `delhi.csv`, 144,266 bytes, 3,143 rows.
- SHA-256: `3bb4435d91457dca820e1189357446849235bcce18e4092267a5c6fc1e9fd61d`.
- Date range: 2015-05-01 through 2023-12-31. Missing dates are not interpolated.

Credit the publisher and CPCB. The archive page does not specify a license in its visible metadata; do not invent one or claim unrestricted commercial licensing. Source data is preserved unchanged for coursework reproducibility. It is historical city-average AQI, not station-level or personal exposure data.

## Independent 2025 backtest

`delhi-holdout-2025.csv` contains the 211 Delhi rows from 2025-01-02 through 2025-07-31, extracted without changing values from UrbanEmissions.Info's CPCB compilation. This is a separate evaluation file, never merged into model fitting or validation selection.

- Immutable source: https://raw.githubusercontent.com/urbanemissionsinfo/AQI_bulletins/e9be70419346b001ef73a8f7b27765c830aa9a7a/data/Processed/AllIndiaBulletins_Master2025.csv
- Full source: 1,955,101 bytes; SHA-256 `dfdbb183872ff7885d848732ae1535cf800b3072128a64c1c318d0838177cd00`.
- Extracted snapshot SHA-256: `e3112e31bdd70e0b06f5197dee15fa9ed0cf0ea40aff51818f12d4ff4829ea74`.
- Downloaded and immutable source verified 2026-10-27. Preserve original columns, filter `City == Delhi`, write UTF-8 CSV with LF newlines.
- Publisher repository includes a GPL-3.0 license; its text is included in `URBANEMISSIONS-LICENSE.txt`. Credit UrbanEmissions.Info and CPCB; do not infer additional commercial permissions.

## Current official observations

`observations.py` downloads official CPCB bulletins from `https://cpcb.nic.in/upload/Downloads/AQI_Bulletin_YYYYMMDD.pdf`. These are city AQI for the past 24 hours, published at 4 PM, rather than instantaneous station readings. Requested date, unique Delhi row, AQI category/range and positive station coverage are checked. Each result records its original URL and SHA-256. Only a missing/unpublished bulletin permits a one-day fallback; other failures are explicit. Seven consecutive daily observations are required. Successful source responses refresh within an hour; the training snapshot is never silently replaced.
