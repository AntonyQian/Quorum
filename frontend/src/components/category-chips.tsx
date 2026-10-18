"use client";

import { filter } from "@/design/tokens";
import { cn } from "cn";

export function CategoryChips({
  categories,
  selected,
  onSelect,
}: {
  categories: { id: string; label: string }[];
  selected: string | null;
  onSelect: (category: string | null) => void;
}) {
  return (
    <div className={filter.scroller} role="toolbar" aria-label="Categories">
      <button
        type="button"
        className={cn(filter.pill, selected == null ? filter.pillSelected : filter.pillIdle)}
        aria-pressed={selected == null}
        onClick={() => onSelect(null)}
      >
        All
      </button>
      {categories.map((category) => (
        <button
          key={category.id}
          type="button"
          className={cn(
            filter.pill,
            selected === category.id ? filter.pillSelected : filter.pillIdle,
          )}
          aria-pressed={selected === category.id}
          onClick={() => onSelect(category.id)}
        >
          {category.label}
        </button>
      ))}
    </div>
  );
}
