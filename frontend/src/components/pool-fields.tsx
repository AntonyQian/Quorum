"use client";

import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { demo, typeScale } from "@/design/tokens";
import { MAX_TIERS, type PoolFormState } from "@/lib/pool-form";
import { dollarsToCents, formatCents } from "@/lib/money";

/** Tier builder, Deadline slider and Stock Cap, shared by the product form and the Launch modal. */
export function PoolFields({
  value,
  onChange,
  listCents,
}: {
  value: PoolFormState;
  onChange: (next: PoolFormState) => void;
  listCents: number;
}) {
  function setRow(index: number, patch: Partial<PoolFormState["tiers"][number]>) {
    onChange({
      ...value,
      tiers: value.tiers.map((row, i) => (i === index ? { ...row, ...patch } : row)),
    });
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <h3 className={typeScale.eyebrow}>Tiers (commits → discount)</h3>
        {value.tiers.map((row, index) => {
          const discount = dollarsToCents(row.discount);
          return (
            <div key={index} className="flex flex-wrap items-end gap-2">
              <label className={demo.field}>
                <span className={typeScale.meta}>Tier {index + 1} Members</span>
                <input
                  type="number"
                  min={1}
                  className={`${demo.input} w-24`}
                  value={row.min}
                  onChange={(event) => setRow(index, { min: event.target.value })}
                />
              </label>
              <label className={demo.field}>
                <span className={typeScale.meta}>Discount ($)</span>
                <input
                  inputMode="decimal"
                  className={`${demo.input} w-28`}
                  value={row.discount}
                  onChange={(event) => setRow(index, { discount: event.target.value })}
                />
              </label>
              <p className={`${typeScale.meta} pb-1.5`}>
                {discount != null && listCents > 0 ? `Price ${formatCents(listCents - discount)}` : "—"}
              </p>
              {value.tiers.length > 1 ? (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  aria-label={`Remove Tier ${index + 1}`}
                  onClick={() => onChange({ ...value, tiers: value.tiers.filter((_, i) => i !== index) })}
                >
                  <Trash2 />
                </Button>
              ) : null}
            </div>
          );
        })}
        {value.tiers.length < MAX_TIERS ? (
          <Button
            type="button"
            variant="outline"
            className="self-start"
            onClick={() => {
              const last = value.tiers[value.tiers.length - 1];
              onChange({
                ...value,
                tiers: [
                  ...value.tiers,
                  {
                    min: String((Number(last?.min) || 0) + 10),
                    discount: String((Number(last?.discount) || 0) + 50),
                  },
                ],
              });
            }}
          >
            <Plus /> Add Tier
          </Button>
        ) : null}
      </div>

      <label className={demo.field}>
        <span className={typeScale.meta}>Deadline: {value.deadlineDays} days</span>
        <input
          type="range"
          min={1}
          max={30}
          value={value.deadlineDays}
          onChange={(event) => onChange({ ...value, deadlineDays: Number(event.target.value) })}
        />
      </label>

      <label className={demo.field}>
        <span className={typeScale.meta}>Stock cap (optional)</span>
        <input
          type="number"
          min={1}
          className={`${demo.input} w-28`}
          value={value.stockCap}
          onChange={(event) => onChange({ ...value, stockCap: event.target.value })}
        />
      </label>
    </div>
  );
}
