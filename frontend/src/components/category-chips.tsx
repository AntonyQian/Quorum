"use client";

import { chip, layout } from "@/design/tokens";
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
    <div className={layout.cluster} role="toolbar" aria-label="Categories">
      <button
        type="button"
        className={cn(chip.base, selected == null ? chip.selected : chip.idle)}
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
            chip.base,
            selected === category.id ? chip.selected : chip.idle,
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
