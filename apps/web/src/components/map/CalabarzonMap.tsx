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
  heatBuckets,
  heatColor,
  heatGradientCss,
  type BoundaryLevel,
  type HeatPalette,
} from "@/lib/gis/styles";
import type { MarketRecord } from "@/types/markets";

export interface MunicipalMetric {
  value: number | null;
  unit: string | null;
  label: string;
  classification?: string;
}

export interface CalabarzonMapProps {
  markets: MarketRecord[];
  geographicView?: "province" | "municipality";
  provinceMetrics: Record<string, number | null>;
  municipalityMetrics?: Record<string, MunicipalMetric>;
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

// Kept tight around MAX_BOUNDS (not a full SE-Asia extent) -- nothing beyond MAX_BOUNDS
// is ever reachable (maxBoundsViscosity=1.0), and an oversized mask polygon makes
// Leaflet's SVG renderer reproject a huge pixel-coordinate path on every pan, which
// visibly lags behind the (instantly CSS-transformed) tile layer and flickers.
const MASK_EXTENT: Polygon = {
  type: "Polygon",
  coordinates: [
    [
      [118.7, 11.4],
      [123.7, 11.4],
      [123.7, 16.7],
      [118.7, 16.7],
      [118.7, 11.4],
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
  popupForFeature?: (feature: MapFeature) => string,
) {
  const selectedRef = useRef<{ path: Path; style: PathOptions } | null>(null);

  return useCallback(
    (feature: MapFeature, layer: Layer) => {
      const name = featureName(feature.properties);
      const psgc = normalizePsgcCode(feature.properties?.psgc_code) ?? "Unavailable";
      const baseStyle = styleForFeature?.(feature) ?? boundaryStyle(level);
      layer.bindTooltip(tooltipForFeature?.(feature) ?? name, { sticky: true });
      layer.bindPopup(popupForFeature?.(feature) ?? `<strong>${name}</strong><br/>PSGC: ${psgc}`);

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
    [level, popupForFeature, styleForFeature, tooltipForFeature],
  );
}

// Leaflet sizes its canvas from the container's dimensions at mount time.
// On mobile, the container often isn't at its final size yet (sidebar
// collapsing, orientation change, browser chrome resizing), leaving the map
// stretched or cropped until something nudges it. Watch the container and
// re-measure whenever it changes.
//
// The container also needs an explicit pixel width kept in sync with its
// parent: on the Mapping page's wide layout, `w-full`/`max-w-full` alone can
// leave this element rendered at the page's max container width instead of
// its actual (narrower, sidebar-adjacent) column, pushing the map, its
// legends, and the market-detail panel outside the visible area.
function useMapResize(mapRef: React.RefObject<LeafletMap | null>, ready: boolean) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const hasFitRef = useRef(false);

  useEffect(() => {
    const el = containerRef.current;
    const parent = el?.parentElement;
    if (!el || !parent || typeof ResizeObserver === "undefined") return;
    // `mapRef.current` is populated via react-leaflet's forwardedRef, which
    // is wired through a `context` state update made *inside* the mount-time
    // ref callback -- it isn't guaranteed to have flushed yet on this first
    // effect run. `ready` (flipped by <MapContainer whenReady>, Leaflet's own
    // "the map instance exists" signal) forces this effect to re-run once it
    // truly does.
    if (!ready) return;

    const sync = () => {
      el.style.width = `${parent.clientWidth}px`;
      const map = mapRef.current;
      if (!map) return;
      // Leaflet measures its OWN container (map.getContainer(), a distinct
      // element rendered by <MapContainer> one level inside `el`) to size
      // itself -- that element hits the exact same stuck-at-container-full-
      // width CSS issue independently of `el`, so it needs the same explicit
      // pixel-width correction or Leaflet's fit/pan math runs against a
      // canvas wider than what's actually visible.
      map.getContainer().style.width = `${el.clientWidth}px`;
      // The first correction can follow a mount-time fitBounds that ran
      // against the stale (pre-sync) width -- invalidateSize()'s default
      // pixel-delta pan would "preserve" that wrong center instead of
      // re-centering on CALABARZON_BOUNDS. Re-fit once, then fall back to
      // the normal resize behavior so later legitimate resizes (sidebar
      // toggle, window resize) don't fight the user's own pan/zoom.
      if (!hasFitRef.current) {
        hasFitRef.current = true;
        map.invalidateSize({ pan: false });
        map.fitBounds(CALABARZON_BOUNDS, { animate: false });
      } else {
        map.invalidateSize();
      }
    };

    const observer = new ResizeObserver(sync);
    sync();
    observer.observe(parent);
    observer.observe(el);
    return () => observer.disconnect();
  }, [mapRef, ready]);

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
  geographicView = "province",
  provinceMetrics,
  municipalityMetrics = {},
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
  const [mapReady, setMapReady] = useState(false);
  const resizeContainerRef = useMapResize(mapRef, mapReady);
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
      if (geographicView === "municipality") {
        return { color: "#7c2d12", weight: 1.5, fillColor: "#FFFFFF", fillOpacity: 0.35 };
      }
      const value = provinceMetrics[featureName(feature.properties)] ?? null;
      return {
        color: "#7c2d12",
        weight: 1.5,
        fillColor: heatColor(value, heatmapMin, heatmapMax, heatPalette),
        fillOpacity: value === null ? 0.35 : 0.68,
      };
    },
    [geographicView, heatmapMax, heatmapMin, heatPalette, provinceMetrics],
  );

  const provinceTooltip = useCallback(
    (feature: MapFeature) => {
      const name = featureName(feature.properties);
      if (geographicView === "municipality") return `${name}: No provincial data in municipal view`;
      const value = provinceMetrics[name] ?? null;
      return `${name}: ${value === null ? "Data unavailable" : formatValue(value, heatmapUnit)}`;
    },
    [geographicView, heatmapUnit, provinceMetrics],
  );

  const municipalityStyle = useCallback(
    (feature?: MapFeature): PathOptions => {
      const psgc = normalizePsgcCode(feature?.properties?.psgc_code);
      const metric = psgc ? municipalityMetrics[psgc] : undefined;
      const value = metric?.value ?? null;
      return {
        color: "#c89b3c",
        weight: 1,
        fillColor: value === null ? "#FFFFFF" : heatColor(value, heatmapMin, heatmapMax, heatPalette),
        fillOpacity: value === null ? 0.25 : 0.68,
      };
    },
    [heatmapMax, heatmapMin, heatPalette, municipalityMetrics],
  );

  const municipalityTooltip = useCallback(
    (feature: MapFeature) => {
      const psgc = normalizePsgcCode(feature.properties?.psgc_code);
      const metric = psgc ? municipalityMetrics[psgc] : undefined;
      return metric && metric.value !== null
        ? `${featureName(feature.properties)}: ${formatValue(metric.value, metric.unit)}`
        : `${featureName(feature.properties)}: Data unavailable`;
    },
    [municipalityMetrics],
  );

  const municipalityPopup = useCallback(
    (feature: MapFeature) => {
      const psgc = normalizePsgcCode(feature.properties?.psgc_code) ?? "Unavailable";
      const metric = municipalityMetrics[psgc];
      const provinceName = String(feature.properties?.province ?? "Unavailable");
      if (!metric) {
        return `<strong>${featureName(feature.properties)}</strong><br/>${provinceName}<br/>PSGC: ${psgc}<br/>Data unavailable`;
      }
      const value = metric.value === null ? "Data unavailable" : formatValue(metric.value, metric.unit);
      return `<strong>${featureName(feature.properties)}</strong><br/>${provinceName}<br/>PSGC: ${psgc}<br/>${metric.label}: ${value}${
        metric.classification ? `<br/>Classification: ${metric.classification}` : ""
      }<br/><small>MVP synthetic municipal benchmark</small>`;
    },
    [municipalityMetrics],
  );

  const onEachRegionFeature = useFeatureInteractions("region");
  const onEachProvinceFeature = useFeatureInteractions(
    "province",
    provinceStyle,
    provinceTooltip,
  );
  const onEachMunicipalityFeature = useFeatureInteractions(
    "municipality",
    geographicView === "municipality" ? municipalityStyle : undefined,
    geographicView === "municipality" ? municipalityTooltip : undefined,
    geographicView === "municipality" ? municipalityPopup : undefined,
  );

  const surroundingMask = useMemo(() => {
    if (!region.data) return null;
    return mask(region.data, MASK_EXTENT);
  }, [region.data]);
  const ordinaryMarkets = markets.filter((market) => !isKadiwaMarket(market));
  const kadiwaMarkets = markets.filter(isKadiwaMarket);

  return (
    <div className="flex min-w-0 flex-col gap-2">
      {error && <p className="state state-error">{error}</p>}
      <div
        ref={resizeContainerRef}
        className="relative isolate h-[60dvh] min-h-[360px] w-full max-w-full overflow-hidden rounded-lg border border-line sm:h-[70dvh]"
      >
        <MapContainer
          ref={mapRef}
          bounds={CALABARZON_BOUNDS}
          maxBounds={MAX_BOUNDS}
          maxBoundsViscosity={1.0}
          minZoom={MIN_ZOOM}
          className="h-full w-full"
          scrollWheelZoom
          whenReady={() => setMapReady(true)}
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
          <LayersControl key={geographicView} position="topright">
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
              <LayersControl.Overlay
                name={geographicView === "municipality" ? "Provincial boundaries" : `${heatmapLabel} heatmap`}
                checked
              >
                <GeoJSON
                  key={`${heatmapLabel}-${heatmapMin}-${heatmapMax}`}
                  data={province.data}
                  style={provinceStyle}
                  onEachFeature={onEachProvinceFeature}
                />
              </LayersControl.Overlay>
            )}
            {municipality.data && (
              <LayersControl.Overlay
                name={geographicView === "municipality" ? `${heatmapLabel} heatmap` : "Municipalities"}
                checked={geographicView === "municipality"}
              >
                <GeoJSON
                  key={`${geographicView}-${heatmapLabel}-${heatmapMin}-${heatmapMax}`}
                  data={municipality.data}
                  style={geographicView === "municipality" ? municipalityStyle : boundaryStyle("municipality")}
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
            <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] text-muted">
              {heatBuckets(heatPalette).map((bucket) => (
                <span key={bucket.label} className="flex items-center gap-1.5">
                  <span
                    className="inline-block h-2.5 w-2.5 flex-none rounded-sm"
                    style={{ background: bucket.color }}
                  />
                  {bucket.label}
                </span>
              ))}
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
                {selectedMarket.market_description && (
                  <p>{selectedMarket.market_description}</p>
                )}
                {selectedMarket.description_status_note && (
                  <p className="text-muted italic">
                    {selectedMarket.description_status_note}
                  </p>
                )}
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
                {selectedMarket.contact_number && (
                  <span>
                    <span className="font-medium text-ink">Contact: </span>
                    {selectedMarket.contact_number}
                  </span>
                )}
                <div className="flex flex-wrap gap-2">
                  {selectedMarket.facebook_url && (
                    <a
                      href={selectedMarket.facebook_url}
                      target="_blank"
                      rel="noreferrer"
                      className="btn btn-ghost btn-sm self-start text-xs"
                    >
                      Facebook page →
                    </a>
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
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
