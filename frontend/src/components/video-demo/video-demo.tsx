"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useAccount } from "@/components/account-provider";
import { DemoCursor } from "@/components/video-demo/demo-cursor";
import { VideoDemoHomeScene } from "@/components/video-demo/home-scene";
import { VideoDemoRetailerScene } from "@/components/video-demo/retailer-scene";
import {
  MS_PER_CHAR,
  PHASE_MS,
  TYPING_TEXT,
  nextPhase,
  phaseDuration,
  type DemoPhase,
} from "@/components/video-demo/timeline";
import { recommendation } from "@/lib/mocks";
import type { Notification, RecommendResponse } from "@/lib/types";
import { cn } from "cn";

const SHOPPER_ID = "1";
const RETAILER_ID = "3";

const WALNUT_RESULT: RecommendResponse = {
  ...recommendation,
  parsed: {
    category: "dining_table",
    budget_max_cents: null,
    style_tags: ["walnut"],
    size_notes: null,
  },
};

const BASE_NOTIFICATIONS: Notification[] = [
  {
    id: 2,
    kind: "tier_refund",
    title: "Tier Refund",
    body: "You were refunded $100.00 on Oak Dresser.",
    link: "/orders",
    read: true,
    created_at: "2026-10-10T21:00:00Z",
  },
];

const DEMAND_NOTIFICATION: Notification = {
  id: 3,
  kind: "demand_threshold",
  title: "10 shoppers want something like Walnut Dining Table. Launch a pool?",
  body: "The Demand Threshold for this Hidden Listing has been reached.",
  link: "/retailer?product=31",
  read: false,
  created_at: "2026-10-17T21:00:00Z",
};

function sceneForPhase(phase: DemoPhase): "home" | "retailer" | "fade" {
  if (phase.startsWith("home-")) return "home";
  if (phase === "fade-to-retailer") return "fade";
  return "retailer";
}

function demandHitsForPhase(phase: DemoPhase): number {
  if (phase === "retailer-at-9") return 9;
  return 10;
}

export function VideoDemo() {
  const { selectUser } = useAccount();
  const [phase, setPhase] = useState<DemoPhase>("home-browse");
  const [typingProgress, setTypingProgress] = useState(0);
  const [bellRect, setBellRect] = useState<{ x: number; y: number }>({
    x: 0,
    y: 0,
  });
  const [cursor, setCursor] = useState({ x: 0, y: 0, visible: false, pressing: false });

  const scene = sceneForPhase(phase);
  const queryLen =
    phase === "home-browse"
      ? 0
      : phase === "home-typing"
        ? typingProgress
        : TYPING_TEXT.length;
  const query = TYPING_TEXT.slice(0, Math.min(queryLen, TYPING_TEXT.length));

  const homeMode =
    phase === "home-busy" || phase === "home-results" ? "wish" : "browse";
  const homeBusy = phase === "home-busy";
  const homeResult = phase === "home-results" ? WALNUT_RESULT : null;
  const showCaret = phase === "home-typing";

  const demandHits = demandHitsForPhase(phase);
  const launchGlow = phase === "retailer-launch-glow";
  const zoomNotifications =
    phase === "retailer-zoom-notifications" ||
    phase === "retailer-cursor-to-bell" ||
    phase === "retailer-notifications-open";
  const unread =
    phase === "retailer-zoom-notifications" ||
    phase === "retailer-cursor-to-bell" ||
    phase === "retailer-notifications-open"
      ? 1
      : 0;
  const notificationsOpen = phase === "retailer-notifications-open";

  const notifications = useMemo(
    () =>
      unread > 0
        ? [DEMAND_NOTIFICATION, ...BASE_NOTIFICATIONS]
        : BASE_NOTIFICATIONS,
    [unread],
  );

  const onBellMeasure = useCallback((center: { x: number; y: number }) => {
    setBellRect(center);
  }, []);

  useEffect(() => {
    selectUser(SHOPPER_ID);
  }, [selectUser]);

  useEffect(() => {
    if (phase === "fade-to-retailer") {
      selectUser(RETAILER_ID);
    }
  }, [phase, selectUser]);

  useEffect(() => {
    const next = nextPhase(phase);
    if (!next) return;
    const timer = window.setTimeout(() => setPhase(next), phaseDuration(phase));
    return () => window.clearTimeout(timer);
  }, [phase]);

  useEffect(() => {
    if (phase !== "home-typing") return;
    let cancelled = false;
    let i = 0;
    const start = window.setTimeout(() => {
      if (cancelled) return;
      setTypingProgress(0);
      const tick = () => {
        if (cancelled) return;
        i += 1;
        setTypingProgress(i);
        if (i < TYPING_TEXT.length) window.setTimeout(tick, MS_PER_CHAR);
      };
      window.setTimeout(tick, MS_PER_CHAR);
    }, 0);
    return () => {
      cancelled = true;
      window.clearTimeout(start);
    };
  }, [phase]);

  useEffect(() => {
    if (phase !== "retailer-cursor-to-bell") {
      if (phase === "retailer-notifications-open") {
        const hide = window.setTimeout(() => {
          setCursor((c) => ({ ...c, visible: false, pressing: false }));
        }, 0);
        return () => window.clearTimeout(hide);
      }
      return;
    }

    const startX = window.innerWidth * 0.55;
    const startY = window.innerHeight * 0.55;
    const show = window.setTimeout(() => {
      setCursor({ visible: true, pressing: false, x: startX, y: startY });
    }, 0);
    const moveTimer = window.setTimeout(() => {
      setCursor((c) => ({
        ...c,
        x: bellRect.x,
        y: bellRect.y,
      }));
    }, 180);
    const pressTimer = window.setTimeout(() => {
      setCursor((c) => ({ ...c, pressing: true }));
    }, PHASE_MS["retailer-cursor-to-bell"] - 500);
    const releaseTimer = window.setTimeout(() => {
      setCursor((c) => ({ ...c, pressing: false }));
    }, PHASE_MS["retailer-cursor-to-bell"] - 200);
    return () => {
      window.clearTimeout(show);
      window.clearTimeout(moveTimer);
      window.clearTimeout(pressTimer);
      window.clearTimeout(releaseTimer);
    };
  }, [phase, bellRect.x, bellRect.y]);

  return (
    <div className="relative h-[100dvh] w-[100dvw] overflow-hidden bg-background">
      <div
        className={cn(
          "absolute inset-0 transition-opacity duration-[1.2s] ease-in-out",
          scene === "home" ? "opacity-100" : "pointer-events-none opacity-0",
        )}
      >
        <VideoDemoHomeScene
          query={query}
          mode={homeMode}
          busy={homeBusy}
          result={homeResult}
          showCaret={showCaret}
        />
      </div>

      <div
        className={cn(
          "absolute inset-0 bg-background transition-opacity duration-[1.2s] ease-in-out",
          scene === "retailer" ? "opacity-100" : "pointer-events-none opacity-0",
          scene === "fade" && "opacity-40",
        )}
      >
        <VideoDemoRetailerScene
          demandHits={demandHits}
          threshold={10}
          launchGlow={launchGlow}
          zoomNotifications={zoomNotifications}
          unread={unread}
          notificationsOpen={notificationsOpen}
          notifications={notifications}
          onBellMeasure={onBellMeasure}
        />
      </div>

      {scene === "fade" ? (
        <div
          className="pointer-events-none absolute inset-0 bg-background/70 backdrop-blur-[2px] animate-in fade-in duration-700"
          aria-hidden
        />
      ) : null}

      <DemoCursor
        x={cursor.x}
        y={cursor.y}
        visible={cursor.visible}
        pressing={cursor.pressing}
      />
    </div>
  );
}
