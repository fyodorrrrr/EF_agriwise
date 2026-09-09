# Red Onion Synthetic Runtime Artifacts — MVP

These files are synthetic proof-of-functioning-concept data.
They are NOT PSA-observed Red Onion supply or price data.

## Source files
Place under:
data/synthetic_data/red_onion/

- red_onion_supply_source.csv
- red_onion_price_source.csv

## Runtime prepared artifacts
Place under:
ml/artifacts/prepared/

- red_onion_supply_features.csv
- red_onion_price_features.csv

## Metadata bundles
Place under:

ml/artifacts/supply/red_onion.joblib
ml/artifacts/price/red_onion.joblib

Use:
- red_onion_supply.joblib
- red_onion_price.joblib

## Runtime contract

Supply:
geolocation,date,target,lag_4

Observed:
- 2024 Q3 through 2026 Q2
- target is numeric

Forecast:
- 2026 Q3 through 2027 Q2
- target is blank
- lag_4 is same quarter previous year

Price:
geolocation,date,target,lag_12

Observed:
- 2025-07 through 2026-06
- target numeric

Forecast:
- 2026-07 through 2027-06
- target blank
- lag_12 is same month previous year

## Integration behavior

Real Red Onion demand remains untouched:
ml/artifacts/prepared/red_onion_demand_mt.csv

Existing ForecastService should read these prepared artifacts.
Existing OpportunityScorer should calculate opportunity automatically
once demand + supply + price are all available across all five provinces.

The model-free bundles use:
verdict = CAUTION
strategy = seasonal_naive
model = null

This should expose MODERATE confidence for the synthetic supply/price components.

IMPORTANT:
The current runtime may still label source as `seasonal_naive`.
Use the limitations text to disclose that the values are synthetic MVP data.
