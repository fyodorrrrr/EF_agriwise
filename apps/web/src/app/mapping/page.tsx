import type { Metadata } from "next";
import { MapPageClient } from "@/components/map/MapPageClient";

export const metadata: Metadata = { title: "Mapping — AgriWise" };

export default function MappingPage() {
  return (
    <div className="flex flex-col gap-4">
      <div className="page-head">
        <div>
          <h1>Mapping</h1>
          <p>
            CALABARZON administrative boundaries. Toggle layers with the control in the top-right
            corner of the map.
          </p>
        </div>
      </div>
      <MapPageClient />
    </div>
  );
}
