import { forwardRef, type ReactNode } from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import CalabarzonMap, {
  kadiwaMarkerDetails,
} from "@/components/map/CalabarzonMap";

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
  const Overlay = ({ children, name }: { children?: ReactNode; name?: string }) => (
    <div data-layer-name={name}>{children}</div>
  );
  const LayersControl = Object.assign(Container, { Overlay });
  const MapContainer = forwardRef<unknown, { children?: ReactNode }>(({ children }, _ref) => (
    <div>{children}</div>
  ));
  return {
    GeoJSON: Container,
    LayerGroup: Container,
    LayersControl,
    MapContainer,
    Marker: ({ children, position, pane }: { children?: ReactNode; position: [number, number]; pane?: string }) => (
      <div data-market-position={position.join(",")} data-market-pane={pane}>{children}</div>
    ),
    Pane: ({ children, name }: { children?: ReactNode; name?: string }) => (
      <div data-pane-name={name}>{children}</div>
    ),
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
            operator: null,
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

  it("distinguishes KADIWA marker types and keeps their layer separate", async () => {
    expect(kadiwaMarkerDetails("KADIWA Permanent")).toMatchObject({
      className: "kadiwa-marker--permanent",
      label: "Permanent KADIWA",
    });
    expect(kadiwaMarkerDetails("KADIWA Recurring")).toMatchObject({
      className: "kadiwa-marker--recurring",
      label: "Recurring KADIWA",
    });
    expect(kadiwaMarkerDetails("KADIWA Temporary")).toMatchObject({
      className: "kadiwa-marker--temporary",
      label: "Temporary KADIWA",
    });

    render(
      <CalabarzonMap
        markets={[
          {
            market_id: "ORD-1", market_name: "Ordinary Market", municipality: "Calamba",
            province: "Laguna", latitude: 14.2, longitude: 121.1, market_type: "Public Market",
            operator: null, coordinate_confidence: "HIGH", source_url: null, notes: null,
          },
          {
            market_id: "K-1", market_name: "KADIWA - LARES", municipality: "Lipa City",
            province: "Batangas", latitude: 13.9588, longitude: 121.1662,
            market_type: "KADIWA Recurring", operator: "DA CALABARZON",
            coordinate_confidence: "HIGH", source_url: "https://example.test/kadiwa",
            notes: "Every Monday",
          },
        ]}
        provinceMetrics={{ Laguna: 72 }}
        heatmapLabel="Rice Â· Demand proxy"
        heatmapUnit="index (base~100)"
        heatmapMin={72}
        heatmapMax={72}
      />,
    );

    await waitFor(() => expect(screen.getAllByText("KADIWA - LARES").length).toBeGreaterThan(0));
    expect(screen.getByText("Operator")).toBeInTheDocument();
    expect(screen.getByText("DA CALABARZON")).toBeInTheDocument();
    expect(screen.getByText("View official source")).toBeInTheDocument();
    expect(screen.getByText("Every Monday")).toBeInTheDocument();
    expect(document.querySelector('[data-layer-name="Ordinary Markets (1)"]')).not.toBeNull();
    expect(document.querySelector('[data-layer-name="KADIWA Markets (1)"]')).not.toBeNull();
    expect(document.querySelector('[data-pane-name="market-markers"]')).not.toBeNull();
    expect(document.querySelector('[data-market-position="14.2,121.1"]')).toHaveAttribute("data-market-pane", "market-markers");
    expect(document.querySelector('[data-market-position="13.9588,121.1662"]')).toHaveAttribute("data-market-pane", "market-markers");
  });
});
