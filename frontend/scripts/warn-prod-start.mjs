/** Remind local devs that `next start` has no hot reload (skip on CI/hosting). */
const hosted = process.env.CI || process.env.VERCEL || process.env.RENDER;

if (!hosted) {
  console.warn(`
\x1b[33m⚠  npm run start\x1b[0m serves the last \x1b[1mproduction\x1b[0m build from \`.next/\`.
   File edits will \x1b[1mnot\x1b[0m appear until you run \x1b[1mnpm run build\x1b[0m again.

   For hot reload while coding, use:\x1b[1m npm run dev\x1b[0m
`);
}
