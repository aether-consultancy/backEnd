# EDUWAY — FRONTEND CROSS-CHECK ORIENTATION
_For whoever picks up remaining FE validation. Read HANDOVER.md first — this doc assumes everything in it._

---

## 1. WHERE THIS PHASE ACTUALLY STANDS

Original plan: validate eduParent fully, then eduWay, then bundle.
**What actually happened: eduWay got the bulk of the FE fix work this
session** (kid claim flow, kid login flow, kid logout, kid dashboard
screens, kid update-check screen) — confirmed working end-to-end by the
person, visually. **eduParent's FE screens have NOT been re-walked**
since the original older contract — only its backend (frontendmanager/eduParent,
including a new `/dashboard` EP) was touched. Do not assume eduParent's
FE is validated. Start there if picking this back up.

---

## 2. WORKING STYLE (unchanged, do not deviate)

- Terse, fast-moving, hands-on-keyboard. No direct filesystem access —
  every code block is something he runs and reports back.
- **ALL code as heredoc** (`PYEOF() { cat <<'EOF' ... EOF }; PYEOF | bash`
  or `PYEOF() { cat <<'EOF' ... EOF }; PYEOF > /tmp/x.js && cat /tmp/x.js > target/path`)
  **or `sed -i`.** Never an editor, never a file download.
- Code style: compact, minimal spacing, non-AI-looking.
- **Always `cat`/`grep` back after writing**, before declaring done.
- "we good??" is his check-in phrase — answer honestly.
- User preferences: no long AI explanations, all code in chat, fixes
  as `sed -i`/python, code as PYEOF heredoc.
- Currency KSH, Nakuru Kenya, `+254...` phone format, CBC curriculum.

---

## 3. FULL BACKEND CONTRACT (unchanged from original — still accurate)

### eduParent — prefix `/frontend/parent`
1. `POST /signup` — body: `ParentSignup` shape (see parentmanager/schemas.py).
   Returns `{parent, verification_id, verification_expires_at}`.
2. `POST /confirm-email/{verification_id}` — body `{code}`. Returns
   `{parent_id, status, proof_token}`. **FE must hold proof_token.**
3. `PATCH /more-info` — body `{proof_token, ...fields, remember_me,
   device_info}`. No parent_id in URL. Returns `{parent, token,
   expires_at}` — `token` is the SESSION token, different from
   proof_token. This is where the person lands on home.
4. `POST /login` — body `{email, password, remember_me, device_info}`.
   Returns `{parent, token, expires_at}`. 401 generic on failure.
5. `POST /logout` — Bearer header, single device.
6. `POST /logout-all` — Bearer header (valid session required).
   Cascades to every kid under that parent — copy should reflect this.
7. `GET /kids` — list.
8. `GET /kids/{kid_id}` — single, includes claim status.
9. `GET /dashboard` — parent profile + kid list in one call, session-authed.
   **This is what any screen doing "fetch my info" should call — never
   hit `/parent/profile` or `/kids` separately from the FE, that's the
   whole point of the facade.**

### eduWay — prefix `/frontend/kid`
1. `GET /claim/{row_id}/{token}` — read-only preview. Returns `{kid,
   is_claimed}`. **If `is_claimed` is true, redirect to KidLogin — do
   not continue into ConfirmDetails/SetPassword, confirm will 400.**
2. `POST /claim/{row_id}/{token}/confirm` — body `{password}`. Returns
   `{kid_id, proof_token}`. Not idempotent past first success.
3. `PATCH /more-info` — body `{proof_token, ...fields, remember_me,
   device_info}`. Returns `{kid, token, expires_at}`. Lands on home.
4. `POST /login/{row_id}/{token}/resolve` — kills token immediately at
   scan. Returns `{kid}` for "Hi {name}" screen.
5. `POST /login/confirm` — body `{kid_id, password, remember_me,
   device_info}`. NO token — already dead. Returns `{kid, token,
   expires_at}`. 401 on wrong password.
6. `POST /logout` — Bearer header, single device only.
7. `GET /dashboard` — session-authed (`get_current_kid`), returns
   `KidProfileOut`. **Use this everywhere the old `/auth/me` was called.**

---

## 4. THINGS THAT WILL BITE YOU

- **proof_token ≠ session token.** proof_token: 15-min TTL, single-shot,
  used once between two specific steps. Session token: 7d/90d TTL,
  opaque, used on every authenticated request after. Check variable
  names carefully — confusing the two is a real bug class here.
- **`remember_me` applies to kids too** — not parent-only, deliberate.
- **Kid login resolve never touches password** — if a screen tries to
  skip the password step after resolve, that's wrong.
- **`GET /claim/...` is safe to call repeatedly, `POST confirm` is not**
  — re-triggering confirm after success 400s correctly, not a bug.
- **Old/dead routes to watch for in FE code:** `/parent/signup`
  (parentmanager, stale), `/auth/me` (doesn't exist at all — was a
  leftover from a pre-frontendmanager contract, now fully dead on both
  apps), `/auth/kids/login` (dead, replaced by
  `/frontend/kid/login/confirm`). If you find any FE file still hitting
  these, that's exactly the mismatch this phase exists to catch.
- **FastAPI 0.140.7** — verify routes via `app.openapi()['paths']`,
  never `app.routes` iteration/count.
- **Local dev server:** `cd ~/work/Eduway/backend && uvicorn main:app
  --host 0.0.0.0 --port 8010 --reload` — this is how live testing
  against a phone on the same network happens. Not Railway.

---

## 5. WHERE THINGS LIVE

- Backend root: `~/work/Eduway/backend`, `main.py` at root.
- eduParent app: `~/work/Eduway/eduParent`
- eduWay (kid) app: `~/work/Eduway/eduWay/frontend` — capital W in `eduWay`.
- eduWay's app entry: `~/work/Eduway/eduWay/frontend/operations/App.js`
  (not `index.js` — that just registers `./operations/App`).
- Both apps have `.env` with `EXPO_PUBLIC_API_URL` now pointing at
  Railway production. Only takes effect on a real `eas build`.

---

## 6. eduWay — CONFIRMED DONE THIS SESSION

- `ScanQrScreen.js` — correctly calls claim-preview, branches on
  `is_claimed`, navigates to KidLogin or ConfirmDetails accordingly.
  Already correct, no changes needed.
- `KidLoginScreen.js` — rewritten from dead `/auth/kids/login` +
  `/auth/me` to `/frontend/kid/login/confirm`, `remember_me: true`
  hardcoded (no UI toggle exists), reads `data.token`/`data.kid.*`
  instead of `data.access_token`/a separate me-fetch.
- `ProfileScreen.js` — `handleLogout` now actually calls
  `/frontend/kid/logout` before clearing local session (was local-only
  before, real bug). Dashboard fetch repointed to `/frontend/kid/dashboard`.
- `KidsHomeScreen.js`, `SchoolScreen.js`, `AssignmentsScreen.js` — all
  repointed from `/auth/me` to `/frontend/kid/dashboard`. Fields not yet
  in `KidProfileOut` (`school_activated`, `subjects`) come back
  `undefined` — already safe due to existing `|| []`/optional-chaining
  fallbacks in these files, will just render empty until schoolmanager exists.
- New: `src/hooks/useAppUpdates.js` — `useAppUpdates()` (silent
  check-on-launch, mounted in App.js, shows a dismissable banner) and
  `useManualUpdateCheck()` (full status states for an on-demand screen).
  Both guard against the native `expo-updates` module being absent
  (`require()` wrapped in try/catch) so dev-client/Expo Go don't crash.
- New: `src/screens/landing/kids/UpdateCheckScreen.js` — manual check
  screen, linked from a "Check for updates" row in ProfileScreen
  (between profile data and logout button). Registered in App.js as `"UpdateCheck"`.

---

## 7. eduParent — NOT YET VALIDATED THIS SESSION

Only backend changed (`/dashboard` EP added to frontendmanager/eduParent).
Nobody has re-opened:
- `frontendmanager/eduParent/gateway.js`/`crud.js` (JS-side, predates
  current contract, near-certainly stale — old contract needed
  `user_id`, current BE takes `email` for login).
- The AuthScreen (lanyard/ID-badge flip-card design) and whatever
  signup-flow screens exist on the parent side.
- Any parent-side dashboard/profile screen that might still be hitting
  `/parent/profile` + `/kids` separately instead of the new `/dashboard` facade.
- Parent logout — confirm it actually calls `/frontend/parent/logout`,
  not just clearing local state (this exact bug existed on eduWay's
  side and was only caught by explicit testing).

**Start here if resuming this phase.** Same process as eduWay: `cat` the
existing files first, map each call site against §3 above, fix one flow
at a time, confirm each with the person before moving on.

---

## 8. WHAT'S OUTSIDE THIS PHASE'S SCOPE (don't touch unless asked)

- Forgot-password screens (both apps) — routes exist BE-side, unwrapped
  by frontendmanager, not part of this cross-check.
- schoolmanager (assignments/subjects/timetables) — doesn't exist yet.
- Railway deployment health, DB state, Redis removal — see HANDOVER.md §7,
  separate concern from FE validation.
- App bundling / store submission — comes after both apps are fully validated.
