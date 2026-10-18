"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  readSelectedUserId,
  resolveSelectedUserId,
  setActiveUserId,
  writeSelectedUserId,
} from "@/lib/account";
import { api } from "@/lib/api";
import type { User } from "@/lib/types";
import { POLL_INTERVAL_MS, layout } from "@/design/tokens";
import { TopBar } from "@/components/top-bar";

type AccountContextValue = {
  users: User[];
  userId: string | null;
  /** The active account, once the account list has loaded. */
  user: User | null;
  /** True once the account list has loaded (or failed to), so screens can fetch as the right user. */
  ready: boolean;
  clock: string | null;
  unread: number;
  /** Bumped after a demo action changes server state, so screens that don't poll refetch. */
  dataVersion: number;
  selectUser: (userId: string) => void;
  /** Re-reads the Sim Clock and tells screens to refetch. */
  refresh: () => Promise<void>;
};

const AccountContext = createContext<AccountContextValue | null>(null);

export function useAccount(): AccountContextValue {
  const value = useContext(AccountContext);
  if (!value) throw new Error("useAccount must be used inside AccountProvider");
  return value;
}

export function AccountProvider({ children }: { children: ReactNode }) {
  const [users, setUsers] = useState<User[]>([]);
  const [userId, setUserId] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [clock, setClock] = useState<string | null>(null);
  const [unread, setUnread] = useState(0);
  const [dataVersion, setDataVersion] = useState(0);

  const loadClock = useCallback(async () => {
    try {
      setClock((await api.getClock()).now);
    } catch {
      // The readout keeps its last value; the next refresh tries again.
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const listed = await api.listUsers();
        if (cancelled) return;
        // Resolve before any per-user request, so a stale stored id never reaches the API.
        const nextId = resolveSelectedUserId(
          readSelectedUserId(window.localStorage),
          listed,
        );
        if (nextId) {
          writeSelectedUserId(window.localStorage, nextId);
          setActiveUserId(nextId);
          setUserId(nextId);
        }
        setUsers(listed);
      } catch {
        // Screens still render anonymously; their own requests show the error.
      } finally {
        if (!cancelled) setReady(true);
      }
    }

    void load();
    api
      .getClock()
      .then(({ now }) => {
        if (!cancelled) setClock(now);
      })
      .catch(() => {
        // The readout shows "—" until a demo action refreshes it.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!userId) return;
    let cancelled = false;

    async function loadUnread() {
      try {
        const notes = await api.listNotifications();
        if (!cancelled) setUnread(notes.unread);
      } catch {
        // Keep the last count.
      }
    }

    void loadUnread();
    const timer = window.setInterval(() => void loadUnread(), POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [userId, dataVersion]);

  const refresh = useCallback(async () => {
    await loadClock();
    setDataVersion((version) => version + 1);
  }, [loadClock]);

  const value = useMemo<AccountContextValue>(
    () => ({
      users,
      userId,
      user: users.find((entry) => String(entry.id) === userId) ?? null,
      ready,
      clock,
      unread,
      dataVersion,
      selectUser(nextId: string) {
        writeSelectedUserId(window.localStorage, nextId);
        setActiveUserId(nextId);
        setUnread(0);
        setUserId(nextId);
      },
      refresh,
    }),
    [users, userId, ready, clock, unread, dataVersion, refresh],
  );

  return (
    <AccountContext.Provider value={value}>
      <TopBar />
      <div className={layout.page}>{children}</div>
    </AccountContext.Provider>
  );
}
