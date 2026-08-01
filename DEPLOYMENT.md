# PrepPilot Deployment Plan (Render + Vercel)

Target topology:

| Piece | Platform | Status |
|---|---|---|
| AI Service (FastAPI) | Vercel | ✅ already deployed — `https://interview-prep-pilot-ai.vercel.app` |
| Gateway (Spring Cloud Gateway) | Render (own service) | ⬜ to deploy |
| User Service (Spring Boot) | Render (own service) | ⬜ to deploy |
| Topic Service (Spring Boot) | Render (own service) | ⬜ to deploy |
| Frontend (React/Vite) | Vercel | ⬜ to deploy |
| MongoDB | Atlas | ✅ already provisioned (a real Atlas URI is already sitting in the local `.env` files) |

This doc is based on scanning every service's `application.yml`, Dockerfile, `.env.example`, security/CORS config, and the root `docker-compose.yml`. Facts below reflect the code as it exists today, not assumptions.

---

## 1. The one architectural decision that drives everything

**The frontend currently talks to the backend with relative paths only.**

- `frontend/src/api/axiosInstance.ts` → `baseURL: '/api/v1'`
- `frontend/src/api/chatStream.ts` → `fetchEventSource('/api/v1/topics/${topicId}/chat/messages', ...)`
- `VITE_API_BASE_URL` is defined in `frontend/.env.example` but is **not referenced anywhere in the frontend source** — it's dead config.
- `LoginPage.tsx` links to `/oauth2/authorization/google` (also relative).

Today this works because Vite's dev proxy forwards `/api`, `/oauth2`, `/login/oauth2` to the gateway on `localhost:8080`, and in docker-compose the frontend's nginx container sits behind the gateway. **Once the frontend moves to Vercel and the gateway moves to Render, they're on two different domains**, so this relative-path scheme breaks unless something proxies for it.

There are two ways to fix this. **I recommend Option A** — it requires zero frontend application code changes and sidesteps every CORS/cookie complication.

### Option A (recommended): Vercel rewrites act as the proxy

Add a `frontend/vercel.json` that rewrites API/auth paths to the Render gateway:

```json
{
  "rewrites": [
    { "source": "/api/v1/:path*", "destination": "https://<gateway>.onrender.com/api/v1/:path*" },
    { "source": "/oauth2/:path*", "destination": "https://<gateway>.onrender.com/oauth2/:path*" },
    { "source": "/login/oauth2/:path*", "destination": "https://<gateway>.onrender.com/login/oauth2/:path*" }
  ]
}
```

Why this works cleanly:
- The browser only ever talks to the Vercel domain — from its perspective every request is same-origin. **No CORS headers are needed, and the existing `allowCredentials: true` CORS config on the gateway becomes irrelevant for this traffic path** (though harmless to leave as-is).
- The `refresh_token` cookie (set by `user-service`, no `Domain` attribute, no `SameSite` attribute today) will be scoped to whatever host the browser made the request to — i.e. the Vercel domain — automatically, with **zero code changes** to `AuthController.java` / `OAuthSuccessHandler.java`.
- The Google OAuth2 flow still works: Google redirects the browser to `${FRONTEND_ORIGIN}/login/oauth2/code/google`, which lands on the Vercel domain, which the rewrite forwards to the gateway, which routes it (per its `/login/oauth2/**` whitelist + route) to `user-service`.
- `LoginPage.tsx`'s `/oauth2/authorization/google` link works the same way.

**One thing to verify after deploying**: SSE streaming (Learn Mode) through a Vercel rewrite to an external origin. Vercel rewrites to absolute URLs are proxied at the edge (this is exactly what the Vite dev proxy already does locally, successfully), so it should stream fine, but it hasn't been tested through Vercel specifically in this repo. If tokens stop arriving mid-stream after deploy, fall back to Option B below for just the chat endpoint, or in full.

### Option B (fallback, more invasive): true cross-origin calls

Only pursue this if Option A's SSE proxying misbehaves. Requires:
1. `frontend/src/api/axiosInstance.ts` and `chatStream.ts`: change relative paths to an absolute `VITE_API_BASE_URL` (finally wiring up the currently-unused env var).
2. `user-service`: cookie `SameSite=None` on the `refresh_token` cookie in both `AuthController.java` and `OAuthSuccessHandler.java` (jakarta `Cookie` has no `SameSite` setter — needs to be set via a raw `Set-Cookie` header string or `ResponseCookie` builder instead).
3. Google Cloud Console: change the registered redirect URI from the frontend origin to the gateway/user-service's own public origin, and update `application.yml`'s `redirect-uri` accordingly (new env var, e.g. `BACKEND_ORIGIN`).
4. Gateway CORS config already exists and would just need `FRONTEND_ORIGIN` set to the Vercel domain (no other change needed there).

I have **not** made this change — flagging it only so you know the exact scope if Option A doesn't hold up.

---

## 2. Other required/recommended changes found while scanning

| # | Item | File(s) | Required? |
|---|---|---|---|
| 1 | Add `vercel.json` with the 3 rewrites above | `frontend/vercel.json` (new file) | **Required** (for Option A) |
| 2 | MongoDB Atlas Network Access must allow Render's egress | Atlas dashboard only, no repo change | **Required** |
| 3 | `JWT_SECRET` must be the *same value* on `gateway` and `user-service` Render services | Render env vars | **Required** |
| 4 | `INTERNAL_API_KEY` must be the *same value* on `topic-service` (Render) and the already-deployed `ai-service` (Vercel) | Render + Vercel env vars | **Required** |
| 5 | Google Cloud Console: add the production redirect URI (`https://<vercel-domain>/login/oauth2/code/google`) to the OAuth client's authorized redirect URIs | Google Cloud Console only | **Required** |
| 6 | Set Render "Health Check Path" to `/actuator/health` for all 3 Java services | Render dashboard setting | Recommended |
| 7 | Add container-aware JVM memory flags to each Java Dockerfile (`-XX:MaxRAMPercentage=75.0`) — 3 separate JVMs on small Render instances can OOM with default heap sizing | `gateway/Dockerfile`, `user-service/Dockerfile`, `topic-service/Dockerfile` | Recommended |
| 8 | `ai-service/Dockerfile` has a pre-existing bug unrelated to this deployment: `CMD ["uvicorn", "main:app", ...]` references a top-level `main.py` that doesn't exist — the real app lives at `app/main.py` (Vercel doesn't use this Dockerfile at all, it uses `api/index.py` + `vercel.json`, so production is unaffected, but local `docker-compose up` for `ai-service` is currently broken) | `ai-service/Dockerfile` | Optional (not blocking Render/Vercel deploy) |
| 9 | `.gitignore` lines 19-24 accidentally **ignore** all `.env.example` files repo-wide, directly contradicting the comment above them ("`.env.example` files ARE tracked"). Net effect: these safe template files exist only on this machine and were never actually pushed to GitHub — anyone else cloning the repo (including Render/Vercel's checkout, though that doesn't matter for env vars) has no template to work from. | `.gitignore` | Recommended — remove those lines and `git add` the `.env.example` files |
| 10 | The root `.env.example` has 16 stray lines after the two real Mongo vars (`cd50d-5e538`, `cc4ab-acbc6`, ... — hyphenated 5+5 char strings, look like license/redemption keys, not env vars). Not committed to git (see #9 — it's currently untracked), so no leak, but worth deleting before you do commit it. | `.env.example` | Recommended cleanup |

**Good news on secrets**: I checked — every real `.env` file (`gateway/.env`, `user-service/.env`, `topic-service/.env`, `ai-service/.env`, root `.env`) is properly `.gitignore`d and confirmed **not tracked** in git history. Nothing has leaked. You'll still enter fresh values directly into Render/Vercel's dashboards (never commit them).

---

## 3. Full environment variable matrix

### Gateway (Render)
| Var | Value |
|---|---|
| `JWT_SECRET` | same shared secret as `user-service` |
| `FRONTEND_ORIGIN` | `https://<your-vercel-domain>` |
| `USER_SERVICE_URL` | `https://<user-service>.onrender.com` |
| `TOPIC_SERVICE_URL` | `https://<topic-service>.onrender.com` |
| `AI_SERVICE_URL` | `https://interview-prep-pilot-ai.vercel.app` |

Server listens on `8080` (hardcoded in `application.yml`); Dockerfile `EXPOSE 8080` — Render will auto-detect this.

### User Service (Render)
| Var | Value |
|---|---|
| `MONGODB_URI` | Atlas URI, `users_db` |
| `JWT_SECRET` | same shared secret as gateway |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | from Google Cloud Console |
| `FRONTEND_ORIGIN` | `https://<your-vercel-domain>` (used to build the OAuth `redirect-uri` *and* the post-login `#token=` redirect) |

Server listens on `8081` (hardcoded). No CORS config exists in this service itself — it relies entirely on the gateway's CORS + the Option A proxy making CORS moot.

### Topic Service (Render)
| Var | Value |
|---|---|
| `MONGODB_URI` | Atlas URI, `topics_db` |
| `INTERNAL_API_KEY` | same shared value as `ai-service` on Vercel |
| `AI_SERVICE_URL` | `https://interview-prep-pilot-ai.vercel.app` |

Server listens on `8082` (hardcoded). Note: `topic-service` trusts the `X-User-Id` header unconditionally with no signature/shared-secret check of its own — it relies entirely on only being reachable through the gateway. **Render gives each Docker web service a public URL by default** — there's no network-level way in Render's free/starter tier to make a service reachable only from another Render service. This is a pre-existing trust-boundary assumption in the code (not something introduced by this deploy), but worth knowing: once deployed, `topic-service`'s Render URL is technically internet-reachable, and anyone who calls it directly with an arbitrary `X-User-Id` header can read/write that user's data. Locally this was fine because `topic-service` had no `ports:` mapping in docker-compose. Flagging this as a real gap — mitigating it (e.g. adding a shared-secret header check between gateway and topic-service, similar to `INTERNAL_API_KEY`) is out of scope for "deploy as-is" but you should decide if you want it before going live with real user data.

### AI Service (Vercel — already deployed, just confirm/update)
| Var | Value |
|---|---|
| `OPENAI_API_KEY` | your OpenAI key |
| `LLM_MODEL` | e.g. `gpt-4o-mini` (defaults to `gpt-4o` in code if unset) |
| `INTERNAL_API_KEY` | must match `topic-service`'s value above |

Go into the Vercel project's dashboard → Settings → Environment Variables and confirm these are set (the local `.env` file is never read by the deployed instance).

### Frontend (Vercel)
No env vars are strictly required under Option A (the proxy approach), since the frontend never constructs an absolute backend URL. `frontend/vercel.json` (new file, see §1) is what actually wires it to the gateway.

---

## 4. Deployment order

Because the gateway needs to know the frontend's URL (for `FRONTEND_ORIGIN`) and the frontend needs to know the gateway's URL (for the rewrite destination), there's a circular reference. The clean way to handle it is **two passes**:

### Pass 1 — create all four deployments to get their URLs
Order doesn't matter much here since each service will simply fail to start (or start with stale/placeholder env vars) until Pass 2 — you're just doing this to get Render/Vercel to hand you stable `*.onrender.com` / `*.vercel.app` URLs.

1. **Topic Service** on Render (least dependents — only the gateway calls it, and its one dependency, `ai-service`, is already live).
2. **User Service** on Render.
3. **Gateway** on Render.
4. **Frontend** on Vercel.

### Pass 2 — wire the real env vars together and redeploy
1. Update Google Cloud Console: add `https://<vercel-domain>/login/oauth2/code/google` to the OAuth client's authorized redirect URIs (keep the localhost one too, for continued local dev).
2. Set the full env var matrix from §3 on `gateway`, `user-service`, `topic-service` (Render) and confirm `ai-service` (Vercel).
3. Add `frontend/vercel.json` with the real gateway URL, commit, push → Vercel auto-redeploys.
4. Trigger a manual redeploy on `gateway` and `user-service` (Render doesn't always auto-redeploy on env var changes depending on settings — check "Auto-Deploy" or just click "Manual Deploy").

If you own a custom domain, you can collapse this into one pass by deciding hostnames upfront (e.g. `api.yourapp.com` for the gateway, `app.yourapp.com` for the frontend) and setting env vars correctly the first time — Render and Vercel both support custom domains with free TLS.

---

## 5. Step-by-step: deploying each Java service to Render

Repeat for `gateway`, `user-service`, `topic-service` (each is its own Render "Web Service"):

1. Render dashboard → **New +** → **Web Service** → connect the GitHub repo (already has an `origin` remote, so this should be a normal "import from GitHub" flow).
2. **Root Directory**: set to `gateway` (or `user-service` / `topic-service`) — Render supports monorepos this way.
3. **Runtime**: Render should auto-detect **Docker** from the `Dockerfile` in that root directory. If it doesn't, select Docker explicitly.
4. **Instance type**: Free or Starter (Starter recommended for anything beyond a demo — Free-tier Render services spin down after inactivity, which is rough for a gateway).
5. **Health Check Path**: `/actuator/health`.
6. **Environment**: add the vars from the matrix in §3 (leave cross-service URL vars blank/placeholder for now if this is Pass 1; you'll circle back in Pass 2).
7. Deploy. Note the assigned `https://<service-name>-xxxx.onrender.com` URL — you'll need it for the other services' env vars.

---

## 6. Step-by-step: deploying the frontend to Vercel

1. Vercel dashboard → **Add New** → **Project** → import the same GitHub repo.
2. **Root Directory**: `frontend`.
3. **Framework Preset**: Vite (should auto-detect from `package.json`).
4. **Build Command**: `npm run build` (default, runs `tsc && vite build`).
5. **Output Directory**: `dist` (default for Vite).
6. Add `frontend/vercel.json` (§1) to the repo before or right after this first deploy — it can be committed and pushed at any point; Vercel picks up rewrites on the next deploy.
7. Deploy. Note the `https://<project-name>.vercel.app` URL.

---

## 7. Post-deploy verification checklist

- [ ] Load the Vercel frontend URL — Login page renders (this alone doesn't touch the backend, so a working page here just confirms the static build shipped).
- [ ] Register a new account — confirms `frontend → (rewrite) → gateway → user-service → MongoDB Atlas` end-to-end, and that `MONGODB_URI` + Atlas Network Access are correct.
- [ ] Log in with that account — confirms JWT issuance and that `JWT_SECRET` matches between gateway and user-service.
- [ ] Sign in with Google — confirms the OAuth redirect URI change in Google Cloud Console and the `/oauth2/**` + `/login/oauth2/**` rewrite paths.
- [ ] Refresh the page after logging in (forces the silent-refresh flow) — confirms the `refresh_token` cookie round-trips correctly through the Vercel→Render proxy.
- [ ] Create a topic, open Learn Mode, send a message — confirms SSE streaming survives the full chain (browser → Vercel rewrite → Render gateway → Render topic-service → Vercel ai-service). **This is the one step most likely to surface an issue** (see §1's Option A caveat).
- [ ] Take a test on a topic (generation + submission + evaluation) — confirms `topic-service ↔ ai-service` over `INTERNAL_API_KEY`.
- [ ] Browser DevTools → Application → Cookies: confirm `refresh_token` is present, `Secure`, `HttpOnly`, scoped to the Vercel domain.
- [ ] Browser DevTools → Console/Network: confirm no CORS errors anywhere (there shouldn't be any under Option A).
- [ ] Render dashboard → each service's Logs: confirm clean startup, no crash loops, no `MongoTimeoutException` (would indicate Atlas Network Access isn't allowing Render's IPs yet).
- [ ] MongoDB Atlas → Metrics: confirm active connections from the new Render services.

---

## 8. Summary of what I did *not* change

This document is research + a plan only — I have not modified any files yet (no `vercel.json`, no Dockerfile edits, no `.gitignore` fix). Let me know which pieces you want implemented first (I'd suggest starting with the `frontend/vercel.json` file and the `.gitignore` fix, since both are small, safe, and unblock everything else).
