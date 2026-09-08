"use client";

import "leaflet/dist/leaflet.css";
import "./leaflet-overrides.css";
import mask from "@turf/mask";
import type {
  Feature,
  FeatureCollection,
  GeoJsonProperties,
  Geometry,
  MultiPolygon,
  Polygon,
} from "geojson";
import type { Layer, LatLngBoundsExpression, Path, PathOptions } from "leaflet";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  CircleMarker,
  GeoJSON,
  LayerGroup,
  LayersControl,
  MapContainer,
  Popup,
  TileLayer,
  Tooltip,
} from "react-leaflet";

import { formatValue } from "@/components/forecast/verdict";
import { featureName, loadGeoJson } from "@/lib/gis/geojson";
import { normalizePsgcCode } from "@/lib/gis/psgc";
import { boundaryStyle, heatColor, type BoundaryLevel } from "@/lib/gis/styles";
import type { MarketRecord } from "@/types/markets";

export interface CalabarzonMapProps {
  markets: MarketRecord[];
  provinceMetrics: Record<string, number | null>;
  heatmapLabel: string;
  heatmapUnit: string | null;
  heatmapMin: number;
  heatmapMax: number;
}

type MapFeature = Feature<Geometry, GeoJsonProperties>;

const CALABARZON_BOUNDS: LatLngBoundsExpression = [
  [13.0, 120.3],
  [15.1, 122.1],
];

const MAX_BOUNDS: LatLngBoundsExpression = [
  [12.4, 119.7],
  [15.7, 122.7],
];

const MIN_ZOOM = 8;

const BOUNDARY_FILES = {
  region: "/gis/calabarzon/region.geojson",
  province: "/gis/calabarzon/provinces.geojson",
  municipality: "/gis/calabarzon/municipalities.geojson",
} as const;

const MASK_EXTENT: Polygon = {
  type: "Polygon",
  coordinates: [
    [
      [110, 5],
      [130, 5],
      [130, 22],
      [110, 22],
      [110, 5],
    ],
  ],
};

const MASK_STYLE = {
  color: "transparent",
  weight: 0,
  fillColor: "#1e293b",
  fillOpacity: 0.55,
} as const;

function useFeatureInteractions(
  level: BoundaryLevel,
  styleForFeature?: (feature: MapFeature) => PathOptions,
  tooltipForFeature?: (feature: MapFeature) => string,
) {
  const selectedRef = useRef<{ path: Path; style: PathOptions } | null>(null);

  return useCallback(
    (feature: MapFeature, layer: Layer) => {
      const name = featureName(feature.properties);
      const psgc = normalizePsgcCode(feature.properties?.psgc_code) ?? "Unavailable";
      const baseStyle = styleForFeature?.(feature) ?? boundaryStyle(level);
      layer.bindTooltip(tooltipForFeature?.(feature) ?? name, { sticky: true });
      layer.bindPopup(`<strong>${name}</strong><br/>PSGC: ${psgc}`);

      layer.on("click", () => {
        const path = layer as Path;
        if (selectedRef.current && selectedRef.current.path !== path) {
          selectedRef.current.path.setStyle(selectedRef.current.style);
        }
        path.setStyle({
          ...baseStyle,
          color: "#171615",
          weight: Number(baseStyle.weight ?? 1) + 2,
          fillOpacity: Math.max(Number(baseStyle.fillOpacity ?? 0), 0.72),
        });
        path.bringToFront();
        selectedRef.current = { path, style: baseStyle };
      });
    },
    [level, styleForFeature, tooltipForFeature],
  );
}

function useBoundary<G extends Geometry = Geometry>(url: string) {
  const [data, setData] = useState<FeatureCollection<G> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    loadGeoJson<G>(url)
      .then((fc) => {
        if (!cancelled) setData(fc);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [url]);

  return { data, error };
}

export default function CalabarzonMap({
  markets,
  provinceMetrics,
  heatmapLabel,
  heatmapUnit,
  heatmapMin,
  heatmapMax,
}: CalabarzonMapProps) {
  const region = useBoundary<Polygon | MultiPolygon>(BOUNDARY_FILES.region);
  const province = useBoundary(BOUNDARY_FILES.province);
  const municipality = useBoundary(BOUNDARY_FILES.municipality);
  const error = region.error || province.error || municipality.error;

  const provinceStyle = useCallback(
    (feature?: MapFeature): PathOptions => {
      if (!feature) return boundaryStyle("province");
      const value = provinceMetrics[featureName(feature.properties)] ?? null;
      return {
        color: "#7c2d12",
        weight: 1.5,
        fillColor: heatColor(value, heatmapMin, heatmapMax),
        fillOpacity: value === null ? 0.35 : 0.68,
      };
    },
    [heatmapMax, heatmapMin, provinceMetrics],
  );

  const provinceTooltip = useCallback(
    (feature: MapFeature) => {
      const name = featureName(feature.properties);
      const value = provinceMetrics[name] ?? null;
      return `${name}: ${value === null ? "Data unavailable" : formatValue(value, heatmapUnit)}`;
    },
    [heatmapUnit, provinceMetrics],
  );

  const onEachRegionFeature = useFeatureInteractions("region");
  const onEachProvinceFeature = useFeatureInteractions(
    "province",
    provinceStyle,
    provinceTooltip,
  );
  const onEachMunicipalityFeature = useFeatureInteractions("municipality");

  const surroundingMask = useMemo(() => {
    if (!region.data) return null;
    return mask(region.data, MASK_EXTENT);
  }, [region.data]);

  return (
    <div className="flex flex-col gap-2">
      {error && <p className="state state-error">{error}</p>}
      <div className="relative h-[70vh] w-full overflow-hidden rounded-lg border border-line">
        <MapContainer
          bounds={CALABARZON_BOUNDS}
          maxBounds={MAX_BOUNDS}
          maxBoundsViscosity={1.0}
          minZoom={MIN_ZOOM}
          className="h-full w-full"
          scrollWheelZoom
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          />
          {surroundingMask && (
            <GeoJSON data={surroundingMask} style={MASK_STYLE} interactive={false} />
          )}
          <LayersControl position="topright">
            {region.data && (
              <LayersControl.Overlay name="CALABARZON boundary" checked>
                <GeoJSON
                  data={region.data}
                  style={boundaryStyle("region")}
                  onEachFeature={onEachRegionFeature}
                />
              </LayersControl.Overlay>
            )}
            {province.data && (
              <LayersControl.Overlay name={`${heatmapLabel} heatmap`} checked>
                <GeoJSON
                  key={`${heatmapLabel}-${heatmapMin}-${heatmapMax}`}
                  data={province.data}
                  style={provinceStyle}
                  onEachFeature={onEachProvinceFeature}
                />
              </LayersControl.Overlay>
            )}
            {municipality.data && (
              <LayersControl.Overlay name="Municipalities">
                <GeoJSON
                  data={municipality.data}
                  style={boundaryStyle("municipality")}
                  onEachFeature={onEachMunicipalityFeature}
                />
              </LayersControl.Overlay>
            )}
            <LayersControl.Overlay name={`Markets (${markets.length})`} checked>
              <LayerGroup>
                {markets.map((market) => (
                  <CircleMarker
                    key={market.market_id}
                    center={[market.latitude, market.longitude]}
                    radius={6}
                    pathOptions={{
                      color: "#ffffff",
                      weight: 2,
                      fillColor: "#171615",
                      fillOpacity: 1,
                    }}
                  >
                    <Tooltip direction="top" offset={[0, -5]} opacity={1}>
                      <strong>{market.market_name}</strong>
                      <br />
                      {market.municipality}, {market.province}
                      <br />
                      {market.market_type ?? "Market"} ·{" "}
                      {market.coordinate_confidence.toLowerCase()}-confidence coordinates
                    </Tooltip>
                    <Popup>
                      <div className="flex min-w-48 flex-col gap-1 text-sm">
                        <strong>{market.market_name}</strong>
                        <span>
                          {market.municipality}, {market.province}
                        </span>
                        <span>{market.market_type ?? "Market"}</span>
                        <span className="text-muted">
                          {market.coordinate_confidence.toLowerCase()}-confidence coordinates
                        </span>
                        {market.notes && <span className="text-muted">{market.notes}</span>}
                        {market.source_url && (
                          <a href={market.source_url} target="_blank" rel="noreferrer">
                            View source
                          </a>
                        )}
                      </div>
                    </Popup>
                  </CircleMarker>
                ))}
              </LayerGroup>
            </LayersControl.Overlay>
          </LayersControl>
        </MapContainer>
        <div
          className="pointer-events-none absolute bottom-4 left-4 z-[1000] min-w-48 rounded-md border border-line bg-white/95 p-3 shadow-md"
          aria-label="Heatmap legend"
        >
          <div className="text-xs font-semibold text-ink">{heatmapLabel}</div>
          <div
            className="mt-2 h-2 rounded-full"
            style={{
              background:
                "linear-gradient(90deg, #fde68a, #fbbf24, #f97316, #dc2626)",
            }}
          />
          <div className="mt-1 flex justify-between gap-4 text-[11px] text-muted">
            <span>{formatValue(heatmapMin, heatmapUnit)}</span>
            <span>{formatValue(heatmapMax, heatmapUnit)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
