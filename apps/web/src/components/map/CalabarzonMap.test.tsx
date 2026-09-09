import { forwardRef, type ReactNode } from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import CalabarzonMap from "@/components/map/CalabarzonMap";

vi.mock("@turf/mask", () => ({ default: () => null }));

// jsdom doesn't implement ResizeObserver.
global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

vi.mock("@/lib/gis/geojson", async () => {
  const actual = await vi.importActual<typeof import("@/lib/gis/geojson")>(
    "@/lib/gis/geojson",
  );
  return {
    ...actual,
    loadGeoJson: vi.fn().mockResolvedValue({
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          properties: { name: "Laguna", psgc_code: "0403400000" },
          geometry: {
            type: "Polygon",
            coordinates: [
              [
                [121, 14],
                [121.1, 14],
                [121.1, 14.1],
                [121, 14],
              ],
            ],
          },
        },
      ],
    }),
  };
});

vi.mock("react-leaflet", () => {
  const Container = ({ children }: { children?: ReactNode }) => <div>{children}</div>;
  const LayersControl = Object.assign(Container, { Overlay: Container });
  const MapContainer = forwardRef<unknown, { children?: ReactNode }>(({ children }, _ref) => (
    <div>{children}</div>
  ));
  return {
    CircleMarker: Container,
    GeoJSON: Container,
    LayerGroup: Container,
    LayersControl,
    MapContainer,
    Popup: Container,
    TileLayer: Container,
    Tooltip: Container,
  };
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("CalabarzonMap", () => {
  it("renders market pins with hover and popup information", async () => {
    render(
      <CalabarzonMap
        markets={[
          {
            market_id: "LAG-001",
            market_name: "Biñan Public Market",
            municipality: "Biñan",
            province: "Laguna",
            latitude: 14.33,
            longitude: 121.08,
            market_type: "Public Market",
            coordinate_confidence: "HIGH",
            source_url: null,
            notes: "Verified public market",
          },
        ]}
        provinceMetrics={{ Laguna: 72 }}
        heatmapLabel="Rice · Demand proxy"
        heatmapUnit="index (base~100)"
        heatmapMin={72}
        heatmapMax={72}
      />,
    );

    await waitFor(() =>
      expect(screen.getAllByText("Biñan Public Market").length).toBeGreaterThan(0),
    );
    expect(screen.getAllByText(/Biñan, Laguna/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Public Market/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/High-confidence coordinates/i).length).toBeGreaterThan(0);
  });
});
