"use client";

import { COMMODITIES } from "@/lib/domain";
import type { Commodity } from "@/types/forecast";

interface CommoditySelectProps {
  value: Commodity | null;
  onChange: (commodity: Commodity | null) => void;
  className?: string;
}

export function CommoditySelect({ value, onChange, className }: CommoditySelectProps) {
  return (
    <label className={className ?? "flex flex-col gap-1 text-sm"}>
      <span className="font-medium">Commodity</span>
      <select
        aria-label="Commodity"
        className="select"
        value={value ?? ""}
        onChange={(e) => onChange((e.target.value || null) as Commodity | null)}
      >
        <option value="">Select…</option>
        {COMMODITIES.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>
    </label>
  );
}
