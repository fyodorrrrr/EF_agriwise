# Quarterly LFS survey-weight audit

`PUFPWGTPRV` is documented in the available PSA DCF codebook as **Final Weight Based on Projection**. It is present on person/member records. The codebook does not establish that it is a household weight, and it is not the historical FIES-LFS `RFACT` field. The builder checks within-household constancy but does not convert or reinterpret the weight.

A defensible household estimator may use the common member value only after confirming that the survey documentation defines the repeated value as the household expansion weight. This audit does not certify that step. Therefore the future regional aggregation formula remains conditional: `p_t = sum_h(w_h,t * y_hat_h,t)` if `w_h,t` is confirmed as the valid household expansion weight; otherwise the estimator is unresolved. `PUFPWGTPRV` is not an XGBoost predictor.
