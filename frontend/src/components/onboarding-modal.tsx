"use client";

import { useEffect, useState, type ReactNode } from "react";
import { Dialog } from "@base-ui/react/dialog";
import Image from "next/image";
import { Check, Search, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { bar, typeScale } from "@/design/tokens";
import { formatCents } from "@/lib/money";
import { cn } from "cn";

/** Set once the Shopper has seen (or skipped) the intro; the modal only opens on its own when this is absent. */
const SEEN_KEY = "quorum.onboarding.v1";
const SHOW_EVENT = "quorum:show-intro";

const LIST_CENTS = 109900;
const TIER_1_CENTS = 98900;
const TIER_2_CENTS = 87900;

function photo(id: string): string {
  return `https://images.unsplash.com/photo-${id}?auto=format&fit=crop&w=240&q=70`;
}

const SIDEBOARD = photo("1767963758785-b9def36c13e3");
const WALNUT_TABLE = photo("1505409628601-edc9af17fda6");
const OAK_TABLE = photo("1604578762246-41134e37f9cc");

function readSeen(): boolean {
  try {
    return window.localStorage.getItem(SEEN_KEY) != null;
  } catch {
    return true; // Storage blocked: don't nag on every load.
  }
}

function writeSeen() {
  try {
    window.localStorage.setItem(SEEN_KEY, "1");
  } catch {
    // Nothing to do; the modal will just show again next visit.
  }
}

/** Re-opens the intro from the top bar. */
export function HowItWorksButton() {
  return (
    <button
      type="button"
      className="hidden h-8 items-center rounded-lg px-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground sm:inline-flex"
      onClick={() => window.dispatchEvent(new Event(SHOW_EVENT))}
    >
      How it works
    </button>
  );
}

/** Returns 0, then 1, 2, ... as each delay (ms, measured from the previous one) elapses. */
function usePhase(delays: readonly number[]): number {
  const [phase, setPhase] = useState(0);
  useEffect(() => {
    let at = 0;
    const timers = delays.map((delay, index) => {
      at += delay;
      return window.setTimeout(() => setPhase(index + 1), at);
    });
    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [delays]);
  return phase;
}

/** Counts from `from` up to `to` one step at a time once `active` turns true. */
function useCountUp(from: number, to: number, active: boolean, stepMs: number): number {
  const [value, setValue] = useState(from);
  useEffect(() => {
    if (!active) return;
    const timer = window.setInterval(() => {
      setValue((current) => {
        if (current >= to) {
          window.clearInterval(timer);
          return current;
        }
        return current + 1;
      });
    }, stepMs);
    return () => window.clearInterval(timer);
  }, [active, to, stepMs]);
  return value;
}

/** Types `text` out one character at a time. */
function useTyped(text: string, stepMs: number): string {
  const [length, setLength] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => {
      setLength((current) => {
        if (current >= text.length) {
          window.clearInterval(timer);
          return current;
        }
        return current + 1;
      });
    }, stepMs);
    return () => window.clearInterval(timer);
  }, [text, stepMs]);
  return text.slice(0, length);
}

const pop = "animate-in fade-in zoom-in-95 duration-500 fill-mode-both";
const rise = "animate-in fade-in slide-in-from-bottom-2 duration-500 fill-mode-both";

function Thumb({ src, alt }: { src: string; alt: string }) {
  return (
    <div className="relative size-12 shrink-0 overflow-hidden rounded-lg bg-muted">
      <Image src={src} alt={alt} fill sizes="48px" className="object-cover" />
    </div>
  );
}

function AnimatedPrice({ cents, struck }: { cents: number; struck?: number }) {
  return (
    <p className="flex items-baseline gap-2">
      <span key={cents} className={cn(typeScale.priceLead, rise)}>
        {formatCents(cents)}
      </span>
      {struck != null && struck > cents ? (
        <span className={typeScale.compare}>{formatCents(struck)}</span>
      ) : null}
    </p>
  );
}

function TierSlider({
  value,
  max,
  markers,
  fast = false,
}: {
  value: number;
  max: number;
  markers: { at: number; label: string }[];
  fast?: boolean;
}) {
  return (
    <div className="relative mx-10 pb-7">
      <div className={bar.track}>
        <div
          className={cn(bar.fill, "ease-out motion-reduce:transition-none", fast ? "transition-[width] duration-100" : "transition-[width] duration-700")}
          style={{ width: `${Math.min(value / max, 1) * 100}%` }}
        />
      </div>
      {markers.map((marker) => (
        <div
          key={marker.at}
          className="absolute -top-0.5 flex -translate-x-1/2 flex-col items-center"
          style={{ left: `${(marker.at / max) * 100}%` }}
        >
          <span className={value >= marker.at ? bar.markerReached : bar.marker} />
          <span className={cn(bar.markerLabel, "whitespace-nowrap", value >= marker.at && "font-medium text-primary")}>
            {marker.label}
          </span>
        </div>
      ))}
    </div>
  );
}

function ProductRow({ src, name, children }: { src: string; name: string; children?: ReactNode }) {
  return (
    <div className="flex items-center gap-3">
      <Thumb src={src} alt={name} />
      <div className="min-w-0 flex-1">
        <p className={cn(typeScale.title, "truncate")}>{name}</p>
        {children}
      </div>
    </div>
  );
}

const ONE_AWAY_DELAYS = [1400, 1400] as const;

/** 9 of 10 Members, you join, Tier 1 unlocks and your price drops. */
function SceneOneAway() {
  const phase = usePhase(ONE_AWAY_DELAYS);
  const count = phase >= 1 ? 10 : 9;
  const price = phase >= 2 ? TIER_1_CENTS : LIST_CENTS;
  return (
    <div className="flex flex-col gap-5">
      <ProductRow src={SIDEBOARD} name="Oak Sideboard">
        <p className={typeScale.meta}>
          <span className="tabular-nums">{count}</span> of 10 Members
        </p>
      </ProductRow>
      <TierSlider value={count} max={10} markers={[{ at: 10, label: "Tier 1 · $110 off" }]} />
      <div className="flex items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <p className={typeScale.eyebrow}>{phase >= 2 ? "Your price" : "Price now"}</p>
          <AnimatedPrice cents={price} struck={phase >= 2 ? LIST_CENTS : undefined} />
        </div>
        {phase >= 1 ? (
          <span key="you" className={cn(pop, "rounded-full bg-primary px-3 py-1 text-xs font-medium text-primary-foreground")}>
            You joined
          </span>
        ) : (
          <span className="rounded-full border border-dashed border-border px-3 py-1 text-xs text-muted-foreground">
            You
          </span>
        )}
      </div>
      <p key={phase} className={cn(typeScale.meta, rise, "min-h-10")}>
        {phase === 0
          ? "9 Members are in. One more unlocks Tier 1."
          : phase === 1
            ? "You join. That makes 10."
            : `Tier 1 unlocked. You pay ${formatCents(TIER_1_CENTS)} instead of ${formatCents(LIST_CENTS)}.`}
      </p>
    </div>
  );
}

const CLIMB_DELAYS = [800, 1700, 1000] as const;

/** The count climbs from 10 to 25, Tier 2 unlocks, and the difference is refunded. */
function SceneClimb() {
  const phase = usePhase(CLIMB_DELAYS);
  const count = useCountUp(10, 25, phase >= 1, 90);
  const price = phase >= 2 ? TIER_2_CENTS : TIER_1_CENTS;
  const refund = TIER_1_CENTS - TIER_2_CENTS;
  return (
    <div className="flex flex-col gap-5">
      <ProductRow src={SIDEBOARD} name="Oak Sideboard">
        <p className={typeScale.meta}>
          <span className="tabular-nums">{count}</span> of 25 Members
        </p>
      </ProductRow>
      <TierSlider
        value={count}
        max={25}
        fast
        markers={[
          { at: 10, label: "Tier 1" },
          { at: 25, label: "Tier 2 · $220 off" },
        ]}
      />
      <div className="flex items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <p className={typeScale.eyebrow}>{phase >= 2 ? "Final price" : "You paid"}</p>
          <AnimatedPrice cents={price} struck={phase >= 2 ? LIST_CENTS : undefined} />
        </div>
        {phase >= 3 ? (
          <span key="refund" className={cn(pop, "rounded-full bg-status-completed/15 px-3 py-1 text-sm font-semibold text-primary tabular-nums")}>
            +{formatCents(refund)} refunded
          </span>
        ) : null}
      </div>
      <p key={phase} className={cn(typeScale.meta, rise, "min-h-10")}>
        {phase <= 1
          ? "Everyone who joined keeps pulling the price down together."
          : phase === 2
            ? "Tier 2 unlocked. The price drops again for every Member."
            : `You already paid ${formatCents(TIER_1_CENTS)}, so the ${formatCents(refund)} difference goes back to your card.`}
      </p>
    </div>
  );
}

function SearchBox({ text, loading }: { text: string; loading?: boolean }) {
  return (
    <div className="flex h-10 items-center gap-2 rounded-lg border border-input bg-background px-3 text-sm">
      <Search className="size-4 shrink-0 text-muted-foreground" aria-hidden />
      <span className="min-w-0 flex-1 truncate">
        {text}
        <span className="ml-px inline-block h-4 w-px translate-y-0.5 animate-pulse bg-foreground" />
      </span>
      <span className="rounded-md bg-primary px-2 py-0.5 text-xs font-medium text-primary-foreground">
        {loading ? "Finding..." : "Find it"}
      </span>
    </div>
  );
}

const MATCH_QUERY = "A walnut dining table for six";
const MATCH_DELAYS = [MATCH_QUERY.length * 55 + 300] as const;

/** The AI product matcher finds live Pools that fit the request. */
function SceneMatch() {
  const typed = useTyped(MATCH_QUERY, 55);
  const phase = usePhase(MATCH_DELAYS);
  return (
    <div className="flex flex-col gap-4">
      <SearchBox text={typed} loading={phase === 0 && typed.length === MATCH_QUERY.length} />
      {phase >= 1 ? (
        <div className="flex flex-col gap-2">
          {[
            { src: WALNUT_TABLE, name: "Walnut Dining Table", fit: 96, reason: "Solid walnut, seats four to six.", delay: "0ms" },
            { src: OAK_TABLE, name: "Oak Trestle Dining Table", fit: 81, reason: "Seats six, in oak instead of walnut.", delay: "250ms" },
          ].map((hit) => (
            <div
              key={hit.name}
              className={cn(rise, "flex items-center gap-3 rounded-xl border border-border bg-card p-2")}
              style={{ animationDelay: hit.delay }}
            >
              <Thumb src={hit.src} alt={hit.name} />
              <div className="min-w-0 flex-1">
                <p className={cn(typeScale.title, "truncate")}>{hit.name}</p>
                <p className={cn(typeScale.meta, "truncate")}>{hit.reason}</p>
              </div>
              <span className="rounded-full bg-secondary px-2 py-0.5 text-xs font-medium tabular-nums">
                {hit.fit}% fit
              </span>
            </div>
          ))}
          <p className={cn(typeScale.meta, rise)} style={{ animationDelay: "600ms" }}>
            Matches are live Pools you can join right now.
          </p>
        </div>
      ) : (
        <div className="h-[8.5rem]" aria-hidden />
      )}
    </div>
  );
}

const MISS_QUERY = "A pink velvet credenza";
const MISS_DELAYS = [MISS_QUERY.length * 55 + 300, 1300, 1500] as const;

/** Nothing matches, so the Wish is saved and the demand reaches Retailers. */
function SceneMiss() {
  const typed = useTyped(MISS_QUERY, 55);
  const phase = usePhase(MISS_DELAYS);
  const hits = phase >= 2 ? 10 : 9;
  return (
    <div className="flex flex-col gap-3">
      <SearchBox text={typed} loading={phase === 0 && typed.length === MISS_QUERY.length} />
      <div className="flex min-h-[8.5rem] flex-col gap-2">
        {phase >= 1 ? (
          <div className={cn(rise, "rounded-xl border border-dashed border-border p-3")}>
            <p className="text-sm font-medium">Nothing live matches yet</p>
            <p className={typeScale.meta}>We saved your Wish so Retailers can see the demand.</p>
          </div>
        ) : null}
        {phase >= 2 ? (
          <div className={cn(rise, "flex flex-col gap-1.5 rounded-xl bg-secondary p-3")}>
            <div className="flex items-baseline justify-between gap-3">
              <p className={typeScale.eyebrow}>Demand for this item</p>
              <p className="text-sm font-medium tabular-nums">{hits} of 10</p>
            </div>
            <div className={bar.track}>
              <div
                className={cn(bar.fill, "transition-[width] duration-700 motion-reduce:transition-none")}
                style={{ width: `${hits * 10}%` }}
              />
            </div>
          </div>
        ) : null}
        {phase >= 3 ? (
          <div className={cn(rise, "flex items-start gap-2 rounded-xl border border-primary/30 bg-primary/5 p-3")}>
            <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
              <Check className="size-3" aria-hidden />
            </span>
            <p className="text-sm">
              A Retailer sees <span className="font-medium">10 shoppers want this</span> and can launch a Pool. We
              will let you know.
            </p>
          </div>
        ) : null}
      </div>
    </div>
  );
}

const STEPS = [
  {
    title: "One Member away from a discount",
    body: "Join a Pool for free. When enough Members join, the Tier unlocks and the price drops.",
    scene: SceneOneAway,
  },
  {
    title: "More Members, lower price",
    body: "Each new Tier lowers the price for everyone. If it drops after you paid, you get the difference back.",
    scene: SceneClimb,
  },
  {
    title: "Tell us what you want",
    body: "Describe it in your own words and our AI matcher finds the live Pools that fit.",
    scene: SceneMatch,
  },
  {
    title: "No match? Retailers still hear you",
    body: "Your Wish becomes demand. Retailers see it and may list the product as a Pool.",
    scene: SceneMiss,
  },
] as const;

export function OnboardingModal() {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);

  useEffect(() => {
    // Read storage after mount (never during render) and let the page settle first.
    const timer = window.setTimeout(() => {
      if (!readSeen()) setOpen(true);
    }, 400);
    function show() {
      setStep(0);
      setOpen(true);
    }
    window.addEventListener(SHOW_EVENT, show);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener(SHOW_EVENT, show);
    };
  }, []);

  function close() {
    writeSeen();
    setOpen(false);
  }

  const last = step === STEPS.length - 1;
  const current = STEPS[step];
  const Scene = current.scene;

  return (
    <Dialog.Root open={open} onOpenChange={(next) => (next ? setOpen(true) : close())}>
      <Dialog.Portal>
        <Dialog.Backdrop className="fixed inset-0 z-50 bg-foreground/30 backdrop-blur-[2px] transition-opacity duration-200 data-[ending-style]:opacity-0 data-[starting-style]:opacity-0" />
        <Dialog.Popup className="fixed top-1/2 left-1/2 z-50 flex max-h-[92vh] w-[min(92vw,28rem)] -translate-x-1/2 -translate-y-1/2 flex-col gap-5 overflow-y-auto rounded-2xl border bg-background p-5 shadow-xl outline-none transition-[opacity,scale] duration-200 data-[ending-style]:scale-95 data-[ending-style]:opacity-0 data-[starting-style]:scale-95 data-[starting-style]:opacity-0 sm:p-6">
          <div className="flex items-center justify-between">
            <p className={typeScale.eyebrow}>
              How Quorum works · {step + 1} of {STEPS.length}
            </p>
            <Dialog.Close
              className="inline-flex size-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              aria-label="Close"
            >
              <X className="size-4" aria-hidden />
            </Dialog.Close>
          </div>
          <div className="flex flex-col gap-1.5">
            <Dialog.Title key={step} className={cn(typeScale.display, "text-2xl", rise)}>
              {current.title}
            </Dialog.Title>
            <Dialog.Description className={typeScale.meta}>{current.body}</Dialog.Description>
          </div>
          <div className="min-h-[19rem] rounded-xl bg-secondary/50 p-4">
            <Scene key={step} />
          </div>
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-1.5" aria-hidden>
              {STEPS.map((entry, index) => (
                <span
                  key={entry.title}
                  className={cn(
                    "h-1.5 rounded-full transition-all duration-300",
                    index === step ? "w-5 bg-primary" : "w-1.5 bg-border",
                  )}
                />
              ))}
            </div>
            <div className="flex items-center gap-2">
              {step > 0 ? (
                <Button variant="ghost" size="lg" onClick={() => setStep(step - 1)}>
                  Back
                </Button>
              ) : (
                <Button variant="ghost" size="lg" onClick={close}>
                  Skip
                </Button>
              )}
              <Button size="lg" onClick={() => (last ? close() : setStep(step + 1))}>
                {last ? "Get started" : "Next"}
              </Button>
            </div>
          </div>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
