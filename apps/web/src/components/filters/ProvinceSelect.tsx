"use client";

import { PROVINCES } from "@/lib/domain";
import type { Province } from "@/types/forecast";

interface ProvinceSelectProps {
  value: Province | null;
  onChange: (province: Province | null) => void;
  className?: string;
}

export function ProvinceSelect({ value, onChange, className }: ProvinceSelectProps) {
  return (
    <label className={className ?? "flex flex-col gap-1 text-sm"}>
      <span className="font-medium">Province</span>
      <select
        aria-label="Province"
        className="select"
        value={value ?? ""}
        onChange={(e) => onChange((e.target.value || null) as Province | null)}
      >
        <option value="">Select…</option>
        {PROVINCES.map((p) => (
          <option key={p} value={p}>
            {p}
          </option>
        ))}
      </select>
    </label>
  );
}
