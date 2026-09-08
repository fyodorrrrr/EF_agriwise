"use client";

import "leaflet/dist/leaflet.css";
import "./leaflet-overrides.css";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { GeoJSON, LayersControl, MapContainer, TileLayer } from "react-leaflet";
import mask from "@turf/mask";
import type {
  Feature,
  FeatureCollection,
  GeoJsonProperties,
  Geometry,
  MultiPolygon,
  Polygon,
} from "geojson";
import type { Layer, LatLngBoundsExpression, Path } from "leaflet";
import { boundaryStyle, selectedBoundaryStyle, type BoundaryLevel } from "@/lib/gis/styles";
import { featureName, loadGeoJson } from "@/lib/gis/geojson";
import { normalizePsgcCode } from "@/lib/gis/psgc";

const CALABARZON_BOUNDS: LatLngBoundsExpression = [
  [13.0, 120.3],
  [15.1, 122.1],
];

// Padded slightly beyond CALABARZON_BOUNDS so panning/zooming is locked to
// the region (with a little breathing room) instead of drifting to Manila,
// Bicol, or elsewhere.
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

// A world-spanning mask polygon runs into Leaflet's SVG renderer precision
// limits at this zoom level (edges silently fail to draw when panned).
// Bounding the mask well beyond MAX_BOUNDS avoids that while still being
// unreachable, since panning/zooming is locked to MAX_BOUNDS/MIN_ZOOM.
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

// Selecting a feature traces its exact shape in a bold black outline
// (see selectedBoundaryStyle) instead of relying on the browser's default
// rectangular focus outline, and reverts the previously selected feature
// in the same layer group back to its normal style.
function useFeatureInteractions(level: BoundaryLevel) {
  const selectedRef = useRef<Path | null>(null);

  return useCallback(
    (feature: Feature<never, GeoJsonProperties>, layer: Layer) => {
      const name = featureName(feature.properties);
      const psgc = normalizePsgcCode(feature.properties?.psgc_code) ?? "Unavailable";
      layer.bindTooltip(name, { sticky: true });
      layer.bindPopup(`<strong>${name}</strong><br/>PSGC: ${psgc}`);

      layer.on("click", () => {
        const path = layer as Path;
        if (selectedRef.current && selectedRef.current !== path) {
          selectedRef.current.setStyle(boundaryStyle(level));
        }
        path.setStyle(selectedBoundaryStyle(level));
        path.bringToFront();
        selectedRef.current = path;
      });
    },
    [level],
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

export default function CalabarzonMap() {
  const region = useBoundary<Polygon | MultiPolygon>(BOUNDARY_FILES.region);
  const province = useBoundary(BOUNDARY_FILES.province);
  const municipality = useBoundary(BOUNDARY_FILES.municipality);
  const error = region.error || province.error || municipality.error;

  const onEachRegionFeature = useFeatureInteractions("region");
  const onEachProvinceFeature = useFeatureInteractions("province");
  const onEachMunicipalityFeature = useFeatureInteractions("municipality");

  const surroundingMask = useMemo(() => {
    if (!region.data) return null;
    return mask(region.data, MASK_EXTENT);
  }, [region.data]);

  return (
    <div className="flex flex-col gap-2">
      {error && <p className="state state-error">{error}</p>}
      <div className="h-[70vh] w-full overflow-hidden rounded-lg border border-line">
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
              <LayersControl.Overlay name="Provinces" checked>
                <GeoJSON
                  data={province.data}
                  style={boundaryStyle("province")}
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
          </LayersControl>
        </MapContainer>
      </div>
    </div>
  );
}
