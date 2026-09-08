import type { FeatureCollection, GeoJsonProperties, Geometry } from "geojson";

export async function loadGeoJson<G extends Geometry = Geometry>(
  path: string,
): Promise<FeatureCollection<G>> {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Failed to load ${path}: HTTP ${response.status}`);
  }
  const data = (await response.json()) as FeatureCollection<G>;
  if (!data.features || data.features.length === 0) {
    throw new Error(`${path} contains no features`);
  }
  return data;
}

export function featureName(properties: GeoJsonProperties): string {
  const p = properties ?? {};
  return (
    (p.name as string) ||
    (p.region as string) ||
    (p.province as string) ||
    (p.municipality as string) ||
    (p.barangay as string) ||
    "Unnamed feature"
  );
}
