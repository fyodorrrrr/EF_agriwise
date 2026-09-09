# About the AgriWise Analytics

AgriWise turns public Philippine agriculture data into province-level demand,
supply, price, and opportunity readings for four commodities across the
CALABARZON region. It is a planning aid for smallholder farmers and
agricultural extension workers, not a guarantee of outcomes. Every figure it
shows comes from the same forecasting service; the chat assistant reads those
same figures and never computes new ones.

## Coverage and resolution

The analytics cover four commodities — Rice, Tomato, Red Onion, and Banana —
and the five CALABARZON provinces: Batangas, Cavite, Laguna, Quezon, and
Rizal. Everything is province-resolution. A municipality is not forecast on
its own; a municipality selection resolves to its province. Not every
commodity has every component: for example Red Onion supply and price are not
available, and where a component lacks enough data it is marked "Not Enough
Data" and no estimate is shown.

## Estimated Demand Proxy

Demand is reported as an Estimated Demand Proxy — an index with a base around
100, published quarterly. It is built from a Family Income and Expenditure
Survey (FIES) expenditure category, combined with Labour Force Survey activity
and seasonal indices, to express committed demand pressure. It is not observed
commodity consumption and it is not metric-tonne demand. A rising index means
household spending pressure on that category is rising relative to its own
baseline, not that a specific tonnage will be bought.

## Supply

Supply is reported in metric tonnes (MT), quarterly, per province. It reflects
production volume for the commodity in that province. Supply is only shown for
commodities where a usable series and model exist; otherwise it is marked not
available.

## Price

Price is reported in pesos per kilogram (PHP/kg), monthly, per province. The
forecasting view buckets the monthly series into quarters so it lines up with
supply and demand. Prices are farmgate-oriented reference levels for planning,
not a live market quote.

## Opportunity score

The Opportunity score ranks one province against the other four for a
commodity in a shared quarter, from 0 to 100, with a classification label. It
is a peer-relative decision-support score: a higher score means this province
looks more favourable than its neighbours on the weighted mix of demand,
supply, and price. It is not a causal finding, not a profit prediction, and
not a physical supply gap. Opportunity needs demand, supply, and price for
every province in one shared quarter; if any is missing the score is not
available.

## Forecast quality labels

Each component carries a quality label so you know how much weight to give it.
"Good Forecast" (PASS) means a model met the accuracy bar. "Planning Estimate"
(CAUTION) means the forecast is usable for planning but less certain.
"Estimated Demand" (USABLE_PROXY) and "Demand Trend" (INDICATIVE_PROXY) apply
to the demand proxy and indicate decreasing confidence. "Not Enough Data"
(INSUFFICIENT_DATA) means nothing is shown. Forecasts use the model that
earned the label, or a seasonal-naive fallback named in the "source" field.
Confidence intervals are not published because the underlying artifacts do not
provide them.

## The dashboard sections

The Dashboard gives a one-screen province outlook across all four commodities.
Forecasting shows one commodity in one province in detail — demand, supply,
and price charts, a chosen horizon of two to four quarters, and a "why this
result" explanation. Markets ranks physical markets for a selected commodity
and province. Mapping shows a province-resolution value for each province as a
shaded map and marks provinces where a layer is unavailable. Model Evidence
lists the per-component verdicts, accuracy metrics, seasonal-naive baselines,
and province hold-out results behind the forecasts.

## Limitations to keep in mind

The analytics are province-resolution and backward-looking in construction:
they extrapolate patterns in past public data and cannot see weather shocks,
policy changes, pest outbreaks, or local conditions. The demand proxy is an
expenditure index, not tonnage. The opportunity score is a relative ranking
among five provinces, not advice to plant. Use the figures alongside your own
knowledge of your farm and a local agricultural technician or the Department
of Agriculture.
