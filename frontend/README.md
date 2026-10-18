# Quorum frontend

Next.js app for the shopper and retailer screens. Visual rules live in [`src/design/system.md`](src/design/system.md). Import recipes from `src/design/tokens.ts` instead of inventing colors or type styles.

```bash
npm install
npm run dev
```

The app runs at [http://localhost:3000](http://localhost:3000). API calls go through `src/lib/api.ts` and hit `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`, see `.env.example`). Set `NEXT_PUBLIC_USE_MOCKS=true` in `.env.local` to use the SPEC §8 mock data instead.

### Dev vs production server

| Command | Use when |
|--------|-----------|
| **`npm run dev`** | Day-to-day coding — **hot reload** (Fast Refresh) |
| `npm run build` then **`npm run start`** | Production preview only — serves frozen `.next` output, **no** hot reload |

If UI changes only show up after `build` + `start`, you're on the production server. Stop it (Ctrl+C) and run `npm run dev` instead.

```bash
npm test
npm run typecheck
```
