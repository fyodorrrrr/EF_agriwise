import type { Metadata } from "next";
import { MapPageClient } from "@/components/map/MapPageClient";

export const metadata: Metadata = { title: "Mapping — AgriWise" };

export default function MappingPage() {
  return (
    <div className="flex flex-col gap-4 p-6">
      <div>
        <h1 className="text-2xl font-semibold">Mapping</h1>
        <p className="text-slate-600 dark:text-slate-300">
          CALABARZON administrative boundaries. Toggle layers with the control in the top-right
          corner of the map.
        </p>
      </div>
      <MapPageClient />
    </div>
  );
}
