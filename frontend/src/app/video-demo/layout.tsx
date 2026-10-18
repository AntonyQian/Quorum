import type { ReactNode } from "react";

export default function VideoDemoLayout({ children }: { children: ReactNode }) {
  return (
    <div className="fixed inset-0 z-[100] h-[100dvh] w-[100dvw] overflow-hidden">
      {children}
    </div>
  );
}
