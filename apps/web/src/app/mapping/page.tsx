import type { Metadata } from "next";

import { MappingAnalytics } from "./MappingAnalytics";

export const metadata: Metadata = { title: "Mapping — AgriWise" };

export default function MappingPage() {
  return (
    <div className="flex flex-col gap-4">
      <div className="page-head">
        <div>
          <h1>Mapping</h1>
          <p>
            CALABARZON administrative boundaries with province-resolution analytics.
            Toggle boundary layers on the map; pick an analytics layer below.
          </p>
        </div>
      </div>
      <MappingAnalytics />
    </div>
  );
}
