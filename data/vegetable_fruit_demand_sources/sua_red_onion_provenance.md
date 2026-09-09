# Red Onion annual per-capita input

`sua_red_onion.csv` contains the PSA Supply Utilization Accounts (SUA) Onion
net-food-disposable per-capita series, expressed in kilograms per year. The
workflow labels the commodity **Red Onion** to match the application catalog;
the PSA SUA publication labels this commodity **Onion**.

The values are compiled from the following PSA publications:

- 2009–2011: [SUA 2009–2011](https://psa.gov.ph/system/files/main-publication/sua_09-11.pdf), Table 3.19.
- 2012–2014: PSA Food Consumption and Nutrition annual per-capita NFD index.
  The PSA's 2006 Onion base is 3.51 g/day and the published index is 100 for
  each of these years; the values are converted to kg/year and rounded to the
  precision published by the SUA series.
- 2015–2017: [SUA 2015–2017](https://psa.gov.ph/system/files/main-publication/SUA_2015-2017.pdf), Table 3.19.
- 2018–2020: [SUA 2018–2020](https://psa.gov.ph/system/files/main-publication/SUA-2018-2020-ao13Nov_ONS-signed.pdf), Table 3.19.
- 2021–2022: [SUA 2020–2022](https://psa.gov.ph/system/files/main-publication/1-%28ons-cleared%29-Report%20SUA_2020-2022_ONS-signed.pdf), Table 3.19.

Only the annual per-capita target is used by the demand workflow. Production,
imports, and other supply/use fields are intentionally excluded.
