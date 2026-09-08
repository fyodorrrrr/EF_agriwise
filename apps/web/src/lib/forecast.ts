import { apiFetch } from "@/lib/api";
import type {
  CatalogResponse,
  Commodity,
  EvidenceResponse,
  MethodologyResponse,
  OutlookResponse,
  Province,
} from "@/types/forecast";

export function getCatalog(): Promise<CatalogResponse> {
  return apiFetch<CatalogResponse>("/forecast/catalog");
}

export function getOutlook(
  commodity: Commodity,
  province: Province,
): Promise<OutlookResponse> {
  const query = new URLSearchParams({ commodity, province });
  return apiFetch<OutlookResponse>(`/forecast/outlook?${query}`);
}

export function getEvidence(): Promise<EvidenceResponse> {
  return apiFetch<EvidenceResponse>("/forecast/evidence");
}

export function getMethodology(): Promise<MethodologyResponse> {
  return apiFetch<MethodologyResponse>("/forecast/methodology");
}
