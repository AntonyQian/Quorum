"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Bell } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAccount } from "@/components/account-provider";
import { api } from "@/lib/api";
import type { Notification } from "@/lib/types";
import { cn } from "cn";

export function NotificationBell() {
  const { unread, refresh, userId } = useAccount();
  const router = useRouter();
  const [items, setItems] = useState<Notification[]>([]);

  async function load() {
    try {
      setItems((await api.listNotifications()).items);
    } catch {
      setItems([]);
    }
  }

  async function open(note: Notification) {
    if (!note.read) {
      try {
        await api.markNotificationRead(note.id);
      } catch {
        // The link still works; the count catches up on the next poll.
      }
      await refresh();
    }
    if (note.link) router.push(note.link);
  }

  return (
    <DropdownMenu onOpenChange={(isOpen) => isOpen && void load()} key={userId}>
      <DropdownMenuTrigger
        aria-label={unread > 0 ? `Notifications, ${unread} unread` : "Notifications"}
        className={cn(buttonVariants({ variant: "outline", size: "icon" }), "relative")}
      >
        <Bell />
        {unread > 0 ? (
          <Badge className="absolute -top-1 -right-1 h-4 min-w-4 px-1">{unread}</Badge>
        ) : null}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuGroup>
          <DropdownMenuLabel>Notifications</DropdownMenuLabel>
          {items.length === 0 ? (
            <p className="px-2 py-3 text-sm text-muted-foreground">Nothing yet.</p>
          ) : (
            items.map((note) => (
              <DropdownMenuItem key={note.id} onClick={() => void open(note)}>
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className={note.read ? "" : "font-semibold"}>{note.title}</span>
                  <span className="text-xs text-muted-foreground">{note.body}</span>
                </span>
              </DropdownMenuItem>
            ))
          )}
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
