# Tomato, Banana, and Red Onion Demand Forecasting Pipeline

## Added pipeline

- `ml/demand_alternative/build_demand_pipeline.py` is the runnable entry point:
  `python -m ml.demand_alternative.build_demand_pipeline`.
- `annual_forecast.py` performs rolling-origin evaluation of naive, moving-average,
  linear-trend, and Holt methods for annual PSA per-capita consumption (PCC).
- `denton.py` implements proportional first-difference Denton benchmarking.

## Data preparation and outputs

- Extracts PSA Table 3 Both-sexes annual population projections for 2020-2030
  into `data/vegetable_fruit_demand_sources/population_calabarzon.csv`.
- Retains CALABARZON and Lucena audit rows. `QUEZON_COMBINED` is the PSA QUEZON
  row plus PSA CITY OF LUCENA (Capital), which is listed separately in the workbook.
- Creates reproducible demand outputs in `data/processed/vegetable_fruit_demand/`:
  - `annual_pcc_forecasts.csv`
  - `annual_demand_province.csv`
  - `hfce_quarterly_indicator.csv`
  - `quarterly_demand_province.csv`
  - `model_evaluation.csv`
  - `methodology_summary.md`

## Method

- Uses only PSA SUA annual PCC fields as commodity demand targets; production and
  other SUA supply/use fields are excluded from the demand calculation.
- Applies national PCC to the five CALABARZON provinces using PSA population.
- Uses real quarterly Food and non-alcoholic beverages HFCE at constant 2018 prices
  only as a temporal indicator.
- Forecasts unpublished HFCE quarters and labels indicator values as `OBSERVED` or
  `FORECAST`.
- Benchmarks quarterly metric-ton estimates to annual physical-demand controls with
  exact numerical annual reconciliation.

## Validation

- Validates non-negative PCC and demand values.
- Validates annual-to-quarterly reconciliation.
- Validates five-province spatial reconciliation to CALABARZON, allowing the PSA
  workbook's displayed-population rounding difference of up to 100 people.

## Scope exclusions

- No production-based demand estimation, supply model, prices, FIES, LFS, or ML
  model was added.
- Existing untracked files under `ml/demand/` and `MODEL_EVALUATION.md` are not
  part of this change.
