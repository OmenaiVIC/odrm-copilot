# ODRM-Copilot Frontend

Next.js (App Router, TypeScript) + Tailwind CSS v4. Foundation only — no feature screens yet.

```bash
npm install
cp .env.local.example .env.local
npm run dev        # http://localhost:3000
```

| Script              | Purpose          |
| ------------------- | ---------------- |
| `npm run dev`       | Local dev server |
| `npm run lint`      | ESLint           |
| `npm run typecheck` | `tsc --noEmit`   |
| `npm run format`    | Prettier write   |
| `npm run build`     | Production build |

The typed API wrapper lives in `src/lib/api.ts` and expects the backend at
`NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000/api/v1`).

System design, commercial model, and data contracts: see
[`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md).
