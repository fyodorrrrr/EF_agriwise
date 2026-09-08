import { apiFetch } from "@/lib/api";
import type { Commodity, Province } from "@/types/forecast";
import type { MarketListResponse, MarketRankingResponse } from "@/types/markets";

export function listMarkets(province?: Province): Promise<MarketListResponse> {
  const query = province ? `?${new URLSearchParams({ province })}` : "";
  return apiFetch<MarketListResponse>(`/markets${query}`);
}

export function rankMarkets(
  commodity: Commodity,
  province: Province,
): Promise<MarketRankingResponse> {
  const query = new URLSearchParams({ commodity, province });
  return apiFetch<MarketRankingResponse>(`/markets/rank?${query}`);
}
