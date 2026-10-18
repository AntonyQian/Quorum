import { getActiveUserId } from "./account";
import {
   notifications,
   orders,
   poolDetail,
   poolSummaries,
   recommendation,
   retailerPool,
   retailerProducts,
   simClock,
   users,
   walnutDemand,
} from "./mocks";
import type {
   Demand,
   NotificationList,
   Order,
   PoolCreate,
   PoolDetail,
   PoolSummary,
   ProductCreate,
   RecommendResponse,
   RetailerPool,
   RetailerProduct,
   User,
} from "./types";

/** Set NEXT_PUBLIC_USE_MOCKS=true to use the mock data instead of NEXT_PUBLIC_API_URL. */
export const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === "true";

export class ApiError extends Error {
   readonly code: string;

   constructor(code: string, message: string) {
      super(message);
      this.name = "ApiError";
      this.code = code;
   }
}

export type ApiDeps = {
   useMocks: boolean;
   baseUrl: string;
   getUserId: () => string;
   fetch: typeof fetch;
};

type PoolQuery = { status?: string; category?: string };

function withQuery(
   path: string,
   params: Record<string, string | undefined>,
): string {
   const search = new URLSearchParams();
   for (const [key, value] of Object.entries(params)) {
      if (value) search.set(key, value);
   }
   const query = search.toString();
   return query ? `${path}?${query}` : path;
}

function filterPools(query: PoolQuery = {}): PoolSummary[] {
   const statuses = query.status?.split(",").filter(Boolean);
   return poolSummaries.filter((pool) => {
      if (statuses?.length && !statuses.includes(pool.status)) return false;
      if (query.category && pool.product.category !== query.category)
         return false;
      return true;
   });
}

export function createApi(deps: ApiDeps) {
   async function request<T>(path: string, init?: RequestInit): Promise<T> {
      const headers = new Headers(init?.headers);
      headers.set("X-User-Id", deps.getUserId());
      if (init?.body) headers.set("Content-Type", "application/json");
      const response = await deps.fetch(`${deps.baseUrl}${path}`, {
         ...init,
         headers,
      });
      const body: unknown = await response.json();
      if (!response.ok) {
         const detail = (
            body as { detail?: { code?: string; message?: string } }
         ).detail;
         throw new ApiError(
            detail?.code ?? "error",
            detail?.message ?? response.statusText,
         );
      }
      return body as T;
   }

   return {
      listUsers(options?: { includeSimulated?: boolean }): Promise<User[]> {
         if (deps.useMocks) {
            return Promise.resolve(
               options?.includeSimulated
                  ? users
                  : users.filter((user) => !user.is_simulated),
            );
         }
         return request(
            withQuery("/api/users", {
               include_simulated: options?.includeSimulated
                  ? "true"
                  : undefined,
            }),
         );
      },

      async getMe(): Promise<User> {
         if (deps.useMocks) {
            const user =
               users.find((entry) => String(entry.id) === deps.getUserId()) ??
               users[0];
            if (!user) throw new ApiError("not_found", "Account not found");
            return user;
         }
         return request("/api/me");
      },

      listPools(query?: PoolQuery): Promise<PoolSummary[]> {
         if (deps.useMocks) return Promise.resolve(filterPools(query));
         return request(
            withQuery("/api/pools", {
               status: query?.status,
               category: query?.category,
            }),
         );
      },

      async getPool(id: number): Promise<PoolDetail> {
         if (deps.useMocks) {
            const detail = poolDetail(id);
            if (!detail) throw new ApiError("not_found", "Pool not found");
            return detail;
         }
         return request(`/api/pools/${id}`);
      },

      joinPool(id: number): Promise<PoolDetail> {
         if (deps.useMocks) return this.getPool(id);
         return request(`/api/pools/${id}/join`, { method: "POST" });
      },

      leavePool(id: number): Promise<PoolDetail> {
         if (deps.useMocks) return this.getPool(id);
         return request(`/api/pools/${id}/leave`, { method: "POST" });
      },

      recommend(text: string): Promise<RecommendResponse> {
         if (deps.useMocks) return Promise.resolve(recommendation);
         return request<RecommendResponse>("/api/recommend", {
            method: "POST",
            body: JSON.stringify({ text }),
         }).then((body) => ({
            wish_id: body.wish_id,
            parsed: body.parsed,
            recommendations: body.recommendations.map((entry) => ({
               pool: entry.pool,
            })),
            suggestions: (body.suggestions ?? []).map((entry) => ({
               pool: entry.pool,
            })),
         }));
      },

      listOrders(): Promise<Order[]> {
         if (deps.useMocks) return Promise.resolve(orders);
         return request("/api/me/orders");
      },

      listNotifications(): Promise<NotificationList> {
         if (deps.useMocks) return Promise.resolve(notifications);
         return request("/api/me/notifications");
      },

      markNotificationRead(id: number): Promise<{ ok: true }> {
         if (deps.useMocks) return Promise.resolve({ ok: true });
         return request(`/api/notifications/${id}/read`, { method: "POST" });
      },

      createSetupSession(returnTo?: string): Promise<{ url: string }> {
         if (deps.useMocks) {
            return Promise.resolve({
               url: "http://localhost:3000/payment/success?session_id=mock_1",
            });
         }
         return request("/api/payments/setup-session", {
            method: "POST",
            body: JSON.stringify({ return_to: returnTo }),
         });
      },

      confirmSetup(sessionId: string): Promise<{ card_label: string }> {
         if (deps.useMocks) {
            return Promise.resolve({ card_label: "Visa •••• 4242" });
         }
         return request("/api/payments/confirm-setup", {
            method: "POST",
            body: JSON.stringify({ session_id: sessionId }),
         });
      },

      listRetailerProducts(): Promise<RetailerProduct[]> {
         if (deps.useMocks) return Promise.resolve(retailerProducts);
         return request("/api/retailer/products");
      },

      createRetailerProduct(body: ProductCreate): Promise<RetailerProduct> {
         if (deps.useMocks) return Promise.resolve(retailerProducts[1]!);
         return request("/api/retailer/products", {
            method: "POST",
            body: JSON.stringify(body),
         });
      },

      async updateRetailerProduct(
         id: number,
         body: Partial<ProductCreate>,
      ): Promise<RetailerProduct> {
         if (deps.useMocks) {
            const product =
               retailerProducts.find((entry) => entry.id === id) ??
               retailerProducts[0];
            if (!product) throw new ApiError("not_found", "Product not found");
            return product;
         }
         return request(`/api/retailer/products/${id}`, {
            method: "PATCH",
            body: JSON.stringify(body),
         });
      },

      deleteRetailerProduct(id: number): Promise<{ ok: true }> {
         if (deps.useMocks) return Promise.resolve({ ok: true });
         return request(`/api/retailer/products/${id}`, { method: "DELETE" });
      },

      launchProduct(id: number, body: PoolCreate): Promise<PoolDetail> {
         if (deps.useMocks) return this.getPool(1);
         return request(`/api/retailer/products/${id}/launch`, {
            method: "POST",
            body: JSON.stringify(body),
         });
      },

      async getDemand(id: number): Promise<Demand> {
         if (deps.useMocks) {
            if (id !== 31) throw new ApiError("not_found", "Product not found");
            return walnutDemand;
         }
         return request(`/api/retailer/products/${id}/demand`);
      },

      async getRetailerPool(id: number): Promise<RetailerPool> {
         if (deps.useMocks) {
            const pool = retailerPool(id);
            if (!pool) throw new ApiError("not_found", "Pool not found");
            return pool;
         }
         return request(`/api/retailer/pools/${id}`);
      },

      listRetailerNotifications(): Promise<NotificationList> {
         if (deps.useMocks) return Promise.resolve(notifications);
         return request("/api/retailer/notifications");
      },

      getClock(): Promise<{ now: string }> {
         if (deps.useMocks) return Promise.resolve(simClock);
         return request("/api/demo/clock");
      },

      advanceClock(body: {
         hours?: number;
         days?: number;
         to_deadline_of_pool?: number;
      }): Promise<{ now: string }> {
         if (deps.useMocks) return Promise.resolve(simClock);
         return request("/api/demo/clock/advance", {
            method: "POST",
            body: JSON.stringify(body),
         });
      },

      simulateJoins(
         id: number,
         body: { count: number; include_declining_card?: boolean },
      ): Promise<PoolDetail> {
         if (deps.useMocks) return this.getPool(id);
         return request(`/api/demo/pools/${id}/simulate-joins`, {
            method: "POST",
            body: JSON.stringify(body),
         });
      },

      simulateLeaves(id: number, count: number): Promise<PoolDetail> {
         if (deps.useMocks) return this.getPool(id);
         return request(`/api/demo/pools/${id}/simulate-leaves`, {
            method: "POST",
            body: JSON.stringify({ count }),
         });
      },

      removeDemand(id: number, count: number): Promise<{ total_hits: number }> {
         if (deps.useMocks) return Promise.resolve({ total_hits: 0 });
         return request(`/api/demo/products/${id}/remove-demand`, {
            method: "POST",
            body: JSON.stringify({ count }),
         });
      },

      simulateDemand(
         id: number,
         count: number,
      ): Promise<{ total_hits: number }> {
         if (deps.useMocks) return Promise.resolve({ total_hits: 9 });
         return request(`/api/demo/products/${id}/simulate-demand`, {
            method: "POST",
            body: JSON.stringify({ count }),
         });
      },

      resetDemo(): Promise<{ ok: true }> {
         if (deps.useMocks) return Promise.resolve({ ok: true });
         return request("/api/demo/reset", { method: "POST" });
      },
   };
}

export const api = createApi({
   useMocks: USE_MOCKS,
   baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
   getUserId: getActiveUserId,
   fetch: (input, init) => fetch(input, init),
});

export type Api = ReturnType<typeof createApi>;
