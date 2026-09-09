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
import {
  divIcon,
  type Layer,
  type LatLngBoundsExpression,
  type Map as LeafletMap,
  type Path,
  type PathOptions,
} from "leaflet";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  GeoJSON,
  LayerGroup,
  LayersControl,
  MapContainer,
  Marker,
  Pane,
  TileLayer,
  Tooltip,
  useMapEvents,
} from "react-leaflet";

import { formatValue } from "@/components/forecast/verdict";
import { featureName, loadGeoJson } from "@/lib/gis/geojson";
import { normalizePsgcCode } from "@/lib/gis/psgc";
import {
  boundaryStyle,
  heatColor,
  heatGradientCss,
  type BoundaryLevel,
  type HeatPalette,
} from "@/lib/gis/styles";
import type { MarketRecord } from "@/types/markets";

export interface CalabarzonMapProps {
  markets: MarketRecord[];
  provinceMetrics: Record<string, number | null>;
  heatmapLabel: string;
  heatmapUnit: string | null;
  heatmapMin: number;
  heatmapMax: number;
  heatPalette: HeatPalette;
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
const MARKET_MARKER_PANE = "market-markers";

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

// Fully hides everything outside CALABARZON (opaque, matching the app's card
// surface) rather than dimming it -- only the CALABARZON boundary shows basemap detail.
const MASK_STYLE = {
  color: "transparent",
  weight: 0,
  fillColor: "#ffffff",
  fillOpacity: 1,
} as const;

type KadiwaMarkerDetails = {
  className: string;
  glyph: string;
  label: string;
};

export function isKadiwaMarket(market: MarketRecord): boolean {
  return market.market_type?.startsWith("KADIWA ") ?? false;
}

export function kadiwaMarkerDetails(marketType: string | null): KadiwaMarkerDetails {
  switch (marketType) {
    case "KADIWA Permanent":
      return { className: "kadiwa-marker--permanent", glyph: "▣", label: "Permanent KADIWA" };
    case "KADIWA Temporary":
      return { className: "kadiwa-marker--temporary", glyph: "◆", label: "Temporary KADIWA" };
    default:
      return { className: "kadiwa-marker--recurring", glyph: "↻", label: "Recurring KADIWA" };
  }
}

function kadiwaIcon(details: KadiwaMarkerDetails) {
  return divIcon({
    className: "kadiwa-leaflet-icon",
    html: `<span class="kadiwa-marker ${details.className}" aria-hidden="true">${details.glyph}</span>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  });
}

function marketIcon() {
  return divIcon({
    className: "market-leaflet-icon",
    html: `<svg class="market-marker" viewBox="0 0 32 38" aria-hidden="true">
      <path d="M16 1.5C8.7 1.5 3 7.1 3 14.1c0 9.4 13 21.9 13 21.9s13-12.5 13-21.9C29 7.1 23.3 1.5 16 1.5Z" fill="#334155" stroke="#ffffff" stroke-width="2.5"/>
      <path d="M8.5 13.5h15l-1.4-4.3H9.9l-1.4 4.3Z" fill="#fbbf24" stroke="#ffffff" stroke-width="1"/>
      <path d="M10.5 14v7.5h11V14M13 21.5v-4.2h6v4.2" fill="none" stroke="#ffffff" stroke-width="1.8" stroke-linejoin="round"/>
    </svg>`,
    iconSize: [32, 38],
    iconAnchor: [16, 36],
  });
}

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

// Leaflet sizes its canvas from the container's dimensions at mount time.
// On mobile, the container often isn't at its final size yet (sidebar
// collapsing, orientation change, browser chrome resizing), leaving the map
// stretched or cropped until something nudges it. Watch the container and
// re-measure whenever it changes.
function useMapResize(mapRef: React.RefObject<LeafletMap | null>) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(() => {
      mapRef.current?.invalidateSize();
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [mapRef]);

  return containerRef;
}

// Clicking empty map background (not a marker or a boundary polygon) closes the
// market detail panel, mirroring the outside-pointerdown behavior of FloatingChat.
function MapBackgroundClickHandler({ onBackgroundClick }: { onBackgroundClick: () => void }) {
  useMapEvents({ click: onBackgroundClick });
  return null;
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
  heatPalette,
}: CalabarzonMapProps) {
  const region = useBoundary<Polygon | MultiPolygon>(BOUNDARY_FILES.region);
  const province = useBoundary(BOUNDARY_FILES.province);
  const municipality = useBoundary(BOUNDARY_FILES.municipality);
  const error = region.error || province.error || municipality.error;

  const mapRef = useRef<LeafletMap | null>(null);
  const resizeContainerRef = useMapResize(mapRef);
  const [selectedMarket, setSelectedMarket] = useState<MarketRecord | null>(null);

  useEffect(() => {
    if (!selectedMarket) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setSelectedMarket(null);
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [selectedMarket]);

  const provinceStyle = useCallback(
    (feature?: MapFeature): PathOptions => {
      if (!feature) return boundaryStyle("province");
      const value = provinceMetrics[featureName(feature.properties)] ?? null;
      return {
        color: "#7c2d12",
        weight: 1.5,
        fillColor: heatColor(value, heatmapMin, heatmapMax, heatPalette),
        fillOpacity: value === null ? 0.35 : 0.68,
      };
    },
    [heatmapMax, heatmapMin, heatPalette, provinceMetrics],
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
  const ordinaryMarkets = markets.filter((market) => !isKadiwaMarket(market));
  const kadiwaMarkets = markets.filter(isKadiwaMarket);

  return (
    <div className="flex flex-col gap-2">
      {error && <p className="state state-error">{error}</p>}
      <div
        ref={resizeContainerRef}
        className="relative h-[60vh] min-h-[360px] w-full overflow-hidden rounded-lg border border-line sm:h-[70vh]"
      >
        <MapContainer
          ref={mapRef}
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
          <MapBackgroundClickHandler onBackgroundClick={() => setSelectedMarket(null)} />
          {surroundingMask && (
            <GeoJSON data={surroundingMask} style={MASK_STYLE} interactive={false} />
          )}
          <Pane name={MARKET_MARKER_PANE} style={{ zIndex: 650 }} />
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
            <LayersControl.Overlay name={`Ordinary Markets (${ordinaryMarkets.length})`} checked>
              <LayerGroup>
                {ordinaryMarkets.map((market) => (
                  <Marker
                    key={market.market_id}
                    position={[market.latitude, market.longitude]}
                    icon={marketIcon()}
                    pane={MARKET_MARKER_PANE}
                    eventHandlers={{ click: () => setSelectedMarket(market) }}
                  >
                    <Tooltip direction="top" offset={[0, -34]} opacity={1}>
                      <strong>{market.market_name}</strong>
                      <br />
                      {market.municipality}, {market.province}
                      <br />
                      {market.market_type ?? "Market"} ·{" "}
                      {market.coordinate_confidence.toLowerCase()}-confidence coordinates
                    </Tooltip>
                  </Marker>
                ))}
              </LayerGroup>
            </LayersControl.Overlay>
            <LayersControl.Overlay name={`KADIWA Markets (${kadiwaMarkets.length})`} checked>
              <LayerGroup>
                {kadiwaMarkets.map((market) => {
                  const details = kadiwaMarkerDetails(market.market_type);
                  return (
                    <Marker
                      key={market.market_id}
                      position={[market.latitude, market.longitude]}
                      icon={kadiwaIcon(details)}
                      pane={MARKET_MARKER_PANE}
                      eventHandlers={{ click: () => setSelectedMarket(market) }}
                    >
                      <Tooltip direction="top" offset={[0, -16]} opacity={1}>
                        <strong>{market.market_name}</strong>
                        <br />
                        {market.municipality}, {market.province}
                        <br />
                        {details.label}
                      </Tooltip>
                    </Marker>
                  );
                })}
              </LayerGroup>
            </LayersControl.Overlay>
          </LayersControl>
        </MapContainer>
        <div className="pointer-events-none absolute inset-x-3 bottom-3 z-[1000] flex flex-col gap-2 sm:inset-x-4 sm:bottom-4 sm:flex-row sm:items-end sm:justify-between">
          <div
            className="pointer-events-none max-w-[60%] rounded-md border border-line bg-white/95 p-3 shadow-md sm:max-w-none sm:min-w-48"
            aria-label="Heatmap legend"
          >
            <div className="text-xs font-semibold text-ink">{heatmapLabel}</div>
            <div
              className="mt-2 h-2 rounded-full"
              style={{ background: heatGradientCss(heatPalette) }}
            />
            <div className="mt-1 flex justify-between gap-4 text-[11px] text-muted">
              <span>{formatValue(heatmapMin, heatmapUnit)}</span>
              <span>{formatValue(heatmapMax, heatmapUnit)}</span>
            </div>
          </div>
          <div
            className="pointer-events-none self-start rounded-md border border-line bg-white/95 px-3 py-2 text-xs shadow-md sm:self-auto"
            aria-label="Market marker legend"
          >
            <div className="font-semibold text-ink">Market markers</div>
            <div className="mt-1 grid grid-cols-[1rem_auto] gap-x-2 gap-y-1 text-muted">
              <span className="text-center text-base leading-none text-[#334155]">⌂</span><span>Local market</span>
              <span className="text-center text-base leading-none text-[#217a3a]">▣</span><span>Permanent KADIWA</span>
              <span className="text-center text-base leading-none text-[#0f7490]">↻</span><span>Recurring KADIWA</span>
              <span className="text-center text-base leading-none text-[#c76a12]">◆</span><span>Temporary KADIWA</span>
            </div>
          </div>
        </div>
        <div
          className={`absolute inset-y-0 right-0 z-[1100] w-[320px] max-w-[85%] transform border-l border-line bg-white shadow-lg transition-transform duration-300 ${
            selectedMarket ? "translate-x-0" : "translate-x-full"
          }`}
          role="dialog"
          aria-label="Market details"
          aria-hidden={!selectedMarket}
        >
          {selectedMarket && (
            <div className="flex h-full flex-col gap-3 overflow-y-auto p-4">
              <div className="card-head">
                <div>
                  <span className="card-kicker">
                    {isKadiwaMarket(selectedMarket)
                      ? kadiwaMarkerDetails(selectedMarket.market_type).label
                      : (selectedMarket.market_type ?? "Market")}
                  </span>
                  <p className="card-title">{selectedMarket.market_name}</p>
                </div>
                <button
                  type="button"
                  className="btn btn-ghost btn-icon"
                  aria-label="Close market details"
                  onClick={() => setSelectedMarket(null)}
                >
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={2}
                    strokeLinecap="round"
                    aria-hidden="true"
                  >
                    <path d="M18 6 6 18M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <div className="card-body flex flex-col gap-2">
                <span>
                  {selectedMarket.municipality}, {selectedMarket.province}
                </span>
                <span className="text-muted">
                  {selectedMarket.coordinate_confidence.toLowerCase()}-confidence coordinates
                </span>
                {selectedMarket.notes && (
                  <span className="text-muted">{selectedMarket.notes}</span>
                )}
                {selectedMarket.operator && (
                  <span>
                    <span className="font-medium text-ink">Operator: </span>
                    {selectedMarket.operator}
                  </span>
                )}
                {selectedMarket.source_url && (
                  <a
                    href={selectedMarket.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="btn btn-ghost btn-sm self-start text-xs"
                  >
                    View source →
                  </a>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
