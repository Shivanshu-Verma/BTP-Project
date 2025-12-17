# Client (Next.js)

Next.js 16 app for the receipt intelligence platform: upload, dashboard, AI search. Tailwind 4, React 19, Chart.js, React-Toastify.

## Scripts

- `npm run dev` — start dev server (http://localhost:3000)
- `npm run build` — production build
- `npm run start` — start built app
- `npm run lint` — lint

## API Base

Currently hardcoded to `http://localhost:8000` in [lib/api.ts](lib/api.ts). For non-local setups, either change that value or introduce `NEXT_PUBLIC_API_BASE` and read from env.

## Getting Started

```bash
cd client
npm install
npm run dev
# open http://localhost:3000
```

## Environment (optional)

Create `.env.local` if you parameterize the API base:

```
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

## Production Notes

- Serve the built app behind HTTPS (e.g., reverse proxy or Vercel/Netlify equivalent).
- Set strict CSP/CORS to your backend origin.
- Keep cookies httpOnly/secure if you move auth to cookies.
