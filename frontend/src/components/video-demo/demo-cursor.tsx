"use client";

import { cn } from "cn";

type DemoCursorProps = {
  x: number;
  y: number;
  visible: boolean;
  pressing?: boolean;
};

export function DemoCursor({ x, y, visible, pressing }: DemoCursorProps) {
  return (
    <div
      className={cn(
        "pointer-events-none absolute z-[200] transition-opacity duration-500",
        visible ? "opacity-100" : "opacity-0",
      )}
      style={{
        left: x,
        top: y,
        transition: "left 1.4s cubic-bezier(0.22, 1, 0.36, 1), top 1.4s cubic-bezier(0.22, 1, 0.36, 1), opacity 500ms",
      }}
      aria-hidden
    >
      <svg
        width="28"
        height="28"
        viewBox="0 0 28 28"
        fill="none"
        className={cn(
          "drop-shadow-md transition-transform duration-150",
          pressing ? "scale-90" : "scale-100",
        )}
      >
        <path
          d="M4 2L4 22L10 16L14 24L17 22.5L13 14.5L20 14L4 2Z"
          fill="white"
          stroke="rgba(0,0,0,0.75)"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}
