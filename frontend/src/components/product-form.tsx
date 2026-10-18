"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { PoolFields } from "@/components/pool-fields";
import { categories, chip, demo, memberPanel, typeScale } from "@/design/tokens";
import { ApiError, api } from "@/lib/api";
import { dollarsToCents } from "@/lib/money";
import { buildPoolCreate, emptyPoolForm, type PoolFormState } from "@/lib/pool-form";
import type { Visibility } from "@/lib/types";
import { cn } from "cn";

const DEFAULT_IMAGE =
  "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?auto=format&fit=crop&w=900&q=80";

export function ProductForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<string>(categories[0].id);
  const [styleTags, setStyleTags] = useState("");
  const [dimensions, setDimensions] = useState("");
  const [imageUrl, setImageUrl] = useState(DEFAULT_IMAGE);
  const [list, setList] = useState("");
  const [floor, setFloor] = useState("");
  const [visibility, setVisibility] = useState<Visibility>("public");
  const [threshold, setThreshold] = useState("10");
  const [pool, setPool] = useState<PoolFormState>(emptyPoolForm);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const listCents = dollarsToCents(list);
  const floorCents = dollarsToCents(floor);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    if (!name.trim()) return setError("Give the product a name.");
    if (listCents == null || floorCents == null || listCents < 1) {
      return setError("Enter a List Price and a Floor Price in dollars.");
    }
    let poolBody;
    if (visibility === "public") {
      const built = buildPoolCreate(pool, { listCents, floorCents });
      if ("error" in built) return setError(built.error);
      poolBody = built.pool;
    }
    setBusy(true);
    try {
      await api.createRetailerProduct({
        name: name.trim(),
        description: description.trim(),
        category,
        style_tags: styleTags.split(",").map((tag) => tag.trim()).filter(Boolean),
        dimensions: dimensions.trim(),
        image_url: imageUrl.trim() || DEFAULT_IMAGE,
        list_price_cents: listCents,
        floor_price_cents: floorCents,
        visibility,
        demand_threshold: visibility === "hidden" ? Number(threshold) || 1 : null,
        pool: poolBody,
      });
      router.push("/retailer");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save the product.");
      setBusy(false);
    }
  }

  const field = (label: string, node: React.ReactNode) => (
    <label className={demo.field}>
      <span className={typeScale.meta}>{label}</span>
      {node}
    </label>
  );
  const input = `${demo.input} h-9 w-full`;

  return (
    <form onSubmit={submit} className="flex max-w-2xl flex-col gap-4">
      <h1 className={typeScale.display}>New product</h1>
      {field("Name", <input className={input} value={name} onChange={(e) => setName(e.target.value)} />)}
      {field(
        "Description",
        <textarea className={`${input} h-20 py-2`} value={description} onChange={(e) => setDescription(e.target.value)} />,
      )}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {field(
          "Category",
          <select className={input} value={category} onChange={(e) => setCategory(e.target.value)}>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.label}</option>
            ))}
          </select>,
        )}
        {field("Style tags (comma separated)", <input className={input} value={styleTags} onChange={(e) => setStyleTags(e.target.value)} />)}
        {field("Dimensions", <input className={input} value={dimensions} onChange={(e) => setDimensions(e.target.value)} placeholder="180 x 90 x 75 cm" />)}
        {field("Image URL", <input className={input} value={imageUrl} onChange={(e) => setImageUrl(e.target.value)} />)}
        {field("List Price ($)", <input inputMode="decimal" className={input} value={list} onChange={(e) => setList(e.target.value)} />)}
        {field("Floor Price ($)", <input inputMode="decimal" className={input} value={floor} onChange={(e) => setFloor(e.target.value)} />)}
      </div>

      <div className="flex gap-2" role="group" aria-label="Visibility">
        {(["public", "hidden"] as const).map((v) => (
          <button
            key={v}
            type="button"
            aria-pressed={visibility === v}
            className={cn(chip.base, visibility === v ? chip.selected : chip.idle)}
            onClick={() => setVisibility(v)}
          >
            {v === "public" ? "Public + Pool" : "Hidden + Demand Threshold"}
          </button>
        ))}
      </div>

      {visibility === "hidden" ? (
        field(
          "Demand Threshold (Wishes before you are alerted)",
          <input type="number" min={1} className={`${demo.input} w-28`} value={threshold} onChange={(e) => setThreshold(e.target.value)} />,
        )
      ) : (
        <PoolFields value={pool} onChange={setPool} listCents={listCents ?? 0} />
      )}

      {error ? <p className={memberPanel.error} role="alert">{error}</p> : null}
      <Button type="submit" size="lg" disabled={busy} className="self-start">
        {busy ? "Saving..." : visibility === "public" ? "Create product and open Pool" : "Create Hidden Listing"}
      </Button>
    </form>
  );
}
