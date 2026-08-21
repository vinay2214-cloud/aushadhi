# AUSHADHI Frontend — Autonomous Medicine Supply Intelligence Dashboard

Operations dashboard for AUSHADHI, an autonomous medicine supply chain system for
rural health centers in Andhra Pradesh. It surfaces what the backend's five-agent
pipeline is doing in real time: stock levels across every health center, disease
outbreak clusters inferred from medicine consumption signatures, and the purchase
orders generated in response.

## Screens

- **Dashboard** — live metrics, health center stock status, agent activity feed
- **Inventory** — per-center, per-medicine stock heatmap with stockout runway
- **Outbreaks** — Gemini-detected outbreak clusters, evidence and response actions
- **Purchase Orders** — auto-generated POs awaiting district officer approval
- **Pipeline** — SENTINEL → DQMS → FORECAST → PROCUREMENT → ALERT agent flow and logs

## Stack

TanStack Start (SSR + file-based routing), React 19, TanStack Query, Tailwind CSS v4,
axios, Zustand, Recharts, Lucide icons.

## Running locally

The FastAPI backend must be running (default `http://localhost:8000`).

```sh
bun install
bun run dev
```

Configure the API connection in `.env.local`:

```sh
VITE_API_BASE_URL=http://localhost:8000
VITE_API_KEY=<AUSHADHI_API_KEY from the backend .env>
```

`VITE_API_BASE_URL` is the source of truth for the API origin; without it the app
falls back to `http://localhost:8000` when served from a local dev port.

## Live updates

The dashboard subscribes to the backend's SSE stream at `/api/v1/stream`
(authenticated by query parameter, since `EventSource` cannot send headers).
Reconnection uses exponential backoff — 3s, 6s, 12s, 30s, 60s — and never
reconnects after unmount.
