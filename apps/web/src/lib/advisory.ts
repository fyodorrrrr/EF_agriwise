import { apiFetch } from "@/lib/api";
import type { Province } from "@/types/forecast";
import type { AdvisoryResponse } from "@/types/advisory";

export function getAdvisories(province: Province): Promise<AdvisoryResponse> {
  return apiFetch<AdvisoryResponse>(`/advisory?${new URLSearchParams({ province })}`);
}
