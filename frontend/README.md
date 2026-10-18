# Quorum frontend

Next.js app for the shopper and retailer screens. Visual rules live in [`src/design/system.md`](src/design/system.md). Import recipes from `src/design/tokens.ts` instead of inventing colors or type styles.

```bash
npm install
npm run dev
```

The app runs at [http://localhost:3000](http://localhost:3000). API calls go through `src/lib/api.ts` and hit `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`, see `.env.example`). Set `NEXT_PUBLIC_USE_MOCKS=true` in `.env.local` to use the SPEC §8 mock data instead.

```bash
npm test
npm run typecheck
```
