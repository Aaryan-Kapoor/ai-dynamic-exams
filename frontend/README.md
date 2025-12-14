# Frontend (Next.js)

This folder contains the **modern UI** for the AI-Powered Adaptive Examination System.

## How it talks to the backend

The frontend proxies API calls to the FastAPI backend using Next.js rewrites in `next.config.ts`:

- `/auth/*` → `http://127.0.0.1:8000/auth/*`
- `/student/*` → `http://127.0.0.1:8000/student/*`
- `/teacher/*` → `http://127.0.0.1:8000/teacher/*`
- `/admin/*` → `http://127.0.0.1:8000/admin/*`

So: **start the backend first**, then run the frontend.

## Run locally

```bash
npm install
npm run dev
```

Open `http://localhost:3000`.

## Notes

- This frontend assumes the backend is running on port `8000`. If you change that, update `frontend/next.config.ts`.
- Session auth is cookie-based; run both apps on localhost during development for the simplest setup.
