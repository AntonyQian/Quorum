export type DemoPhase =
  | "home-browse"
  | "home-typing"
  | "home-busy"
  | "home-results"
  | "fade-to-retailer"
  | "retailer-at-9"
  | "retailer-to-10"
  | "retailer-launch-glow"
  | "retailer-zoom-notifications"
  | "retailer-cursor-to-bell"
  | "retailer-notifications-open";

export const TYPING_TEXT = "Walnut table";

/** Slow pacing for voiceover — ms per phase (typing length handled separately). */
export const PHASE_MS: Record<Exclude<DemoPhase, "home-typing">, number> = {
  "home-browse": 2200,
  "home-busy": 2400,
  "home-results": 5200,
  "fade-to-retailer": 1400,
  "retailer-at-9": 2800,
  "retailer-to-10": 3200,
  "retailer-launch-glow": 3600,
  "retailer-zoom-notifications": 2200,
  "retailer-cursor-to-bell": 2800,
  "retailer-notifications-open": 60000,
};

export const MS_PER_CHAR = 110;

export const PHASE_ORDER: DemoPhase[] = [
  "home-browse",
  "home-typing",
  "home-busy",
  "home-results",
  "fade-to-retailer",
  "retailer-at-9",
  "retailer-to-10",
  "retailer-launch-glow",
  "retailer-zoom-notifications",
  "retailer-cursor-to-bell",
  "retailer-notifications-open",
];

export function nextPhase(phase: DemoPhase): DemoPhase | null {
  const i = PHASE_ORDER.indexOf(phase);
  if (i < 0 || i >= PHASE_ORDER.length - 1) return null;
  return PHASE_ORDER[i + 1] ?? null;
}

export function phaseDuration(phase: DemoPhase): number {
  if (phase === "home-typing") return TYPING_TEXT.length * MS_PER_CHAR + 400;
  return PHASE_MS[phase];
}
