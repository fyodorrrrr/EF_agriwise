"""Build PSA-based Tomato, Banana, and Red Onion provincial quarterly demand estimates."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .annual_forecast import evaluate, forecast
from .denton import proportional_denton


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data" / "vegetable_fruit_demand_sources"
OUTPUT = ROOT / "data" / "processed" / "vegetable_fruit_demand"
FORECAST_PREPARED = ROOT / "ml" / "artifacts" / "prepared"
PROVINCES = ("BATANGAS", "CAVITE", "LAGUNA", "QUEZON_COMBINED", "RIZAL")
DISPLAY_PROVINCE = {"QUEZON_COMBINED": "Quezon", "BATANGAS": "Batangas", "CAVITE": "Cavite", "LAGUNA": "Laguna", "RIZAL": "Rizal"}

COMMODITY_SOURCES = (
    ("Tomato", "sua_tomato.csv", "UT Per Capita kg/yr"),
    ("Banana", "sua_banana.csv", "UT Per Capita (kg/yr)"),
    ("Red Onion", "sua_red_onion.csv", "UT Per Capita kg/yr"),
)


def extract_population() -> pd.DataFrame:
    """Read the Table 3 Both sexes provincial/HUC total rows from the PSA workbook."""
    book = SOURCE / "Statistical Tables (2020 CBPP Subnational).xlsx"
    raw = pd.read_excel(book, sheet_name="Table 3", header=None)
    labels = {
        "REGION IV-A (CALABARZON)": "REGION IV-A (CALABARZON)",
        "BATANGAS": "BATANGAS",
        "CAVITE": "CAVITE",
        "LAGUNA": "LAGUNA",
        "QUEZON": "QUEZON",
        "CITY OF LUCENA (Capital)": "CITY OF LUCENA (Capital)",
        "RIZAL": "RIZAL",
    }
    years = list(range(2020, 2031))
    both_sex_columns = [1, 4, 7, 10, 14, 17, 20, 23, 27, 30, 33]
    records = []
    for workbook_label, output_label in labels.items():
        matched = raw.index[raw.iloc[:, 0].astype(str).eq(workbook_label)].tolist()
        if len(matched) != 1:
            raise AssertionError(f"Expected one Table 3 row for {workbook_label}, found {matched}")
        # Table 3 places the geography heading on one row and the Both-sexes
        # population total on its immediately following ``Total`` row.
        total_row = matched[0] + 1
        if str(raw.iat[total_row, 0]) != "Total":
            raise AssertionError(f"Expected Total row below {workbook_label}")
        values = raw.iloc[total_row, both_sex_columns].to_numpy(dtype=float)
        records.extend({"year": year, "geography": output_label, "population": value} for year, value in zip(years, values))
    population = pd.DataFrame(records)
    pivot = population.pivot(index="year", columns="geography", values="population")
    five_province_sum = pivot[["BATANGAS", "CAVITE", "LAGUNA", "QUEZON", "CITY OF LUCENA (Capital)", "RIZAL"]].sum(axis=1)
    # PSA's displayed component values are rounded to hundreds; the largest
    # resulting difference from the displayed regional total is 100 persons.
    if not np.allclose(five_province_sum, pivot["REGION IV-A (CALABARZON)"], rtol=0, atol=100):
        raise AssertionError("PSA provincial/HUC rows do not reconcile to CALABARZON")
    combined = pivot["QUEZON"] + pivot["CITY OF LUCENA (Capital)"]
    population = pd.concat(
        [population, pd.DataFrame({"year": years, "geography": "QUEZON_COMBINED", "population": combined.to_numpy()})],
        ignore_index=True,
    ).sort_values(["year", "geography"])
    return population


def build_pcc() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    rows, evaluations, selections = [], [], {}
    for commodity, filename, pcc_column in COMMODITY_SOURCES:
        # Read only the annual PCC target. Production and other SUA supply/use
        # fields are deliberately excluded from the demand calculation.
        source = pd.read_csv(SOURCE / filename, usecols=["Year", pcc_column]).sort_values("Year")
        history = source[["Year", pcc_column]].rename(columns={"Year": "year", pcc_column: "pcc_kg_person_year"})
        history["year"] = history["year"].astype(int)
        history["commodity"] = commodity
        history["value_type"] = "OBSERVED"
        history["model"] = "PSA SUA"
        values = history["pcc_kg_person_year"].to_numpy(float)
        result, selected = evaluate(values)
        selections[commodity] = selected
        for item in result:
            evaluations.append({"series": f"annual_pcc_{commodity.lower()}", **item, "selected": item["method"] == selected})
        future_years = range(history.year.max() + 1, 2031)
        forecasts = []
        for year in future_years:
            value = max(0.0, forecast(values, selected, horizon=year - history.year.max()))
            forecasts.append({"commodity": commodity, "year": year, "pcc_kg_person_year": value, "value_type": "FORECAST", "model": selected})
        rows.extend(history[["commodity", "year", "pcc_kg_person_year", "value_type", "model"]].to_dict("records"))
        rows.extend(forecasts)
    return pd.DataFrame(rows).sort_values(["commodity", "year"]), pd.DataFrame(evaluations), selections


def _quarter_index(year: int, quarter: str) -> int:
    return year * 4 + int(quarter[1]) - 1


def _hfce_prediction(values: list[float], quarter_number: int, method: str) -> float:
    if method == "seasonal_naive":
        return values[-4]
    seasonal = values[quarter_number - 1 :: 4]
    if method == "seasonal_mean_3":
        return float(np.mean(seasonal[-3:]))
    if method == "recent_yoy_growth":
        growth = np.asarray(seasonal[-3:]) / np.asarray(seasonal[-4:-1])
        return float(seasonal[-1] * np.mean(growth))
    raise ValueError(method)


def build_hfce() -> tuple[pd.DataFrame, pd.DataFrame, str, list[str]]:
    raw = pd.read_csv(SOURCE / "hfce_food_quarterly_constant_2018.csv")
    observed = raw.loc[
        (raw["Purpose"] == "..Food and non-alcoholic beverages")
        & (raw["Type of Valuation"] == "At Constant 2018 Prices"),
        ["Year", "Period", "Value"],
    ].rename(columns={"Year": "year", "Period": "quarter", "Value": "hfce_food_constant_2018"})
    observed = observed.sort_values(["year", "quarter"]).copy()
    observed["year"] = observed["year"].astype(int)
    observed["hfce_food_constant_2018"] = observed["hfce_food_constant_2018"].astype(float)
    observed["status"] = "OBSERVED"
    observed_values = observed["hfce_food_constant_2018"].tolist()
    methods = ("seasonal_naive", "seasonal_mean_3", "recent_yoy_growth")
    evaluations = []
    for method in methods:
        errors, actuals = [], []
        for index in range(max(16, len(observed_values) - 20), len(observed_values)):
            prediction = _hfce_prediction(observed_values[:index], index % 4 + 1, method)
            errors.append(prediction - observed_values[index])
            actuals.append(observed_values[index])
        errors, actuals = np.asarray(errors), np.asarray(actuals)
        evaluations.append({"series": "quarterly_hfce_food", "method": method, "mae": float(np.mean(abs(errors))), "rmse": float(np.sqrt(np.mean(errors**2))), "mape": float(np.mean(abs(errors / actuals)) * 100), "bias": float(np.mean(errors)), "n_test": len(errors)})
    selected = min(evaluations, key=lambda row: (row["mae"], row["rmse"]))["method"]
    for row in evaluations:
        row["selected"] = row["method"] == selected
    result = observed.to_dict("records")
    values = observed_values[:]
    start = _quarter_index(int(observed.iloc[-1].year), observed.iloc[-1].quarter) + 1
    forecast_periods = []
    for index in range(start, _quarter_index(2030, "Q4") + 1):
        year, quarter_number = divmod(index, 4)
        quarter_number += 1
        value = _hfce_prediction(values, quarter_number, selected)
        values.append(value)
        quarter = f"Q{quarter_number}"
        result.append({"year": year, "quarter": quarter, "hfce_food_constant_2018": value, "status": "FORECAST"})
        forecast_periods.append(f"{year} {quarter}")
    return pd.DataFrame(result).sort_values(["year", "quarter"]), pd.DataFrame(evaluations), selected, forecast_periods


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    population = extract_population()
    population.to_csv(SOURCE / "population_calabarzon.csv", index=False)
    pcc, annual_evaluation, selected_models = build_pcc()
    hfce, hfce_evaluation, hfce_method, hfce_forecasts = build_hfce()
    evaluation = pd.concat([annual_evaluation, hfce_evaluation], ignore_index=True)
    pcc.to_csv(OUTPUT / "annual_pcc_forecasts.csv", index=False)
    hfce.to_csv(OUTPUT / "hfce_quarterly_indicator.csv", index=False)
    evaluation.to_csv(OUTPUT / "model_evaluation.csv", index=False)

    population_pivot = population.pivot(index="year", columns="geography", values="population")
    demand_rows = []
    for commodity, _, _ in COMMODITY_SOURCES:
        series = pcc[pcc.commodity.eq(commodity)].set_index("year")
        for province in PROVINCES:
            for year in range(2020, 2031):
                item = series.loc[year]
                demand_rows.append({"commodity": commodity, "province": DISPLAY_PROVINCE[province], "year": year, "population": population_pivot.loc[year, province], "pcc_kg_person_year": item.pcc_kg_person_year, "annual_demand_mt": item.pcc_kg_person_year * population_pivot.loc[year, province] / 1000, "pcc_status": item.value_type})
    annual_demand = pd.DataFrame(demand_rows)
    annual_demand.to_csv(OUTPUT / "annual_demand_province.csv", index=False)

    hfce_window = hfce[hfce.year.between(2020, 2030)].sort_values(["year", "quarter"])
    quarterly_rows = []
    max_error = 0.0
    for (commodity, province), group in annual_demand.groupby(["commodity", "province"], sort=False):
        controls = group.sort_values("year")["annual_demand_mt"].to_numpy()
        quarterly = proportional_denton(hfce_window["hfce_food_constant_2018"].to_numpy(), controls)
        for (_, indicator), value, annual in zip(hfce_window.iterrows(), quarterly, np.repeat(controls, 4)):
            quarterly_rows.append({"commodity": commodity, "province": province, "year": indicator.year, "quarter": indicator.quarter, "annual_demand_mt": annual, "quarterly_demand_mt": value, "hfce_indicator": indicator.hfce_food_constant_2018, "hfce_status": indicator.status})
        max_error = max(max_error, np.max(np.abs(quarterly.reshape(-1, 4).sum(axis=1) - controls)))
    quarterly_demand = pd.DataFrame(quarterly_rows)
    quarterly_demand.to_csv(OUTPUT / "quarterly_demand_province.csv", index=False)
    red_onion = quarterly_demand[quarterly_demand["commodity"] == "Red Onion"].copy()
    red_onion["date"] = pd.PeriodIndex(
        red_onion["year"].astype(str) + red_onion["quarter"], freq="Q"
    ).start_time
    red_onion = red_onion.rename(columns={"quarterly_demand_mt": "target"})[
        ["commodity", "province", "date", "target", "hfce_status"]
    ]
    FORECAST_PREPARED.mkdir(parents=True, exist_ok=True)
    red_onion.to_csv(FORECAST_PREPARED / "red_onion_demand_mt.csv", index=False)

    # Required validations.
    assert (pcc.loc[pcc.value_type.eq("FORECAST"), "pcc_kg_person_year"] >= 0).all()
    assert (annual_demand.annual_demand_mt >= 0).all() and (quarterly_demand.quarterly_demand_mt >= 0).all()
    assert max_error < 1e-6
    provincial_totals = annual_demand.groupby(["commodity", "year"]).annual_demand_mt.sum()
    regional_population = population_pivot["REGION IV-A (CALABARZON)"]
    for (commodity, year), value in provincial_totals.items():
        regional_demand = pcc[(pcc.commodity == commodity) & (pcc.year == year)].iloc[0].pcc_kg_person_year * regional_population[year] / 1000
        # Difference is due solely to PSA population values being rounded to
        # hundreds at the displayed provincial and regional levels.
        assert abs(value - regional_demand) <= 100 * pcc[(pcc.commodity == commodity) & (pcc.year == year)].iloc[0].pcc_kg_person_year / 1000 + 1e-6
    assert not ((hfce.status == "OBSERVED") & (hfce.year > 2026)).any()
    assert not ((pcc.value_type == "OBSERVED") & (pcc.year > 2022)).any()

    summary = f"""# Demand forecasting methodology\n\n- PSA SUA **UT Per Capita kg/yr** is the annual commodity consumption/utilization benchmark.\n- A small rolling-origin comparison selects an annual PCC forecasting method separately for Tomato and Banana.\n- PSA 2020 Census-Based Both-sexes population projections scale national PCC to CALABARZON provinces. `QUEZON_COMBINED` is PSA `QUEZON` plus PSA `CITY OF LUCENA (Capital)`; Table 3 reconciliation confirms these are separate components.\n- Real quarterly Food and non-alcoholic beverages HFCE at constant 2018 prices provides temporal movement only.\n- Proportional first-difference Denton benchmarks quarterly physical estimates to annual metric-ton controls exactly.\n- National PCC is assumed applicable to CALABARZON provinces; it is not a direct provincial consumption measurement.\n- HFCE is broad food consumption, not commodity-specific consumption. Production and all other supply fields are deliberately excluded from demand estimation.\n"""
    (OUTPUT / "methodology_summary.md").write_text(summary, encoding="utf-8")

    print("DEMAND PIPELINE COMPLETE")
    print(f"Population: 2020-2030; {', '.join(PROVINCES)} plus CALABARZON/Lucena audit rows; Quezon = Quezon + Lucena.")
    for commodity, _, _ in COMMODITY_SOURCES:
        metrics = annual_evaluation[(annual_evaluation.series == f"annual_pcc_{commodity.lower()}") & annual_evaluation.selected].iloc[0]
        latest = pcc[(pcc.commodity == commodity) & (pcc.year == 2030)].iloc[0]
        observed = pcc[(pcc.commodity == commodity) & (pcc.value_type == "OBSERVED")]
        print(f"{commodity}: {observed.year.min()}-{observed.year.max()}; {selected_models[commodity]}; MAE {metrics.mae:.3f}, RMSE {metrics.rmse:.3f}, MAPE {metrics.mape:.2f}%, latest PCC {latest.pcc_kg_person_year:.3f}.")
    print(f"HFCE: observed 2000 Q1-2026 Q2; {hfce_method}; forecast 2026 Q3-2030 Q4.")
    print(f"Quarterly demand: 2020 Q1-2030 Q4; reconciliation max error {max_error:.3e}.")
    print("Files created: population_calabarzon.csv; annual_pcc_forecasts.csv; annual_demand_province.csv; hfce_quarterly_indicator.csv; quarterly_demand_province.csv; model_evaluation.csv; methodology_summary.md")
    print("Warnings: National SUA PCC is applied uniformly to provinces; HFCE is a broad temporal indicator.")


if __name__ == "__main__":
    main()
