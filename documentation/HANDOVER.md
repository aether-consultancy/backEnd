# EDUWAY BACKEND — HANDOVER / ONBOARDING DOC
_Read this before touching the codebase. Written for whoever (human or AI) picks this up next._

---

## 1. WHO YOU ARE WORKING WITH

Terse, fast-moving, hands-on-keyboard. Runs every command himself on
his own machine (`osaka`), copy-pasting from chat. No direct filesystem
access — every code block is something HE executes and reports back.

- **All code delivered as heredoc** (`PYEOF() { cat <<'EOF' ... EOF }; PYEOF | bash`
  or `PYEOF() { cat <<'EOF' ... EOF }; PYEOF > /tmp/x.py && cat /tmp/x.py > target/path`)
  **or `sed -i`.** Never open an editor. Never create files for download.
- Code style: minimal spacing, no decorative alignment, compact, non-AI-looking.
- **Always re-verify** by asking him to `cat`/`grep` the file back before
  declaring anything done. Don't assume a write succeeded.
- **"we good??"** is his standard check-in. Answer honestly, fix real bugs.
- He drives architecture, you propose options with real reasoning.
- Currency: KSH. Based in Nakuru, Kenya (phone format `+254...`, CBC curriculum).
- User preferences on file: no long AI explanations, all code in chat,
  fixes as `sed -i`/python commands, code as PYEOF heredoc.

---

## 2. THE PROJECT

**Eduway** — learning terminal system for schools without an existing
school management system. Portals: Student (eduWay), Parent (eduParent).
Teacher portal not started.

- Backend: FastAPI + SQLAlchemy + PostgreSQL, deployed on Railway.
- Backend root: `~/work/Eduway/backend`
- Frontend apps: `~/work/Eduway/eduParent` and `~/work/Eduway/eduWay/frontend`
- Both apps Expo/React Native, SDK 57.

Brand: electric green `#3ED65E` + deep blue `#1A3FA0`. Mascots: Dobi
(starfish, younger grades), Zeek & Zara (older grades).

---

## 3. THE MANAGER ARCHITECTURE

One manager, one job. A manager owns ONE domain, never reaches into
another manager's tables directly — cross-manager work goes through
importing the other manager's `crud` module. Each manager: models.py /
logic.py / schemas.py / crud.py / router.py (logic.py optional if
nothing rule-based to enforce).

| Manager | Owns | Status |
|---|---|---|
| `dbmanager` | DB engine/session (`connection.py`) | ✅ |
| `parentmanager` | `Parent` table (identity only, no password) | ✅ |
| `securitymanager` | all password hashes, all tokens/codes (parent + kid), generic owner_token (proof_token) | ✅ |
| `kidsmanager` | `Kid`, `KidInfo` | ✅ |
| `sessionmanager` | opaque bearer-token sessions (parent+kid, one table, owner_type/owner_id), issue/validate/logout/logout-all, TTL 7d default / 90d remember_me, `deps.py` holds `get_current_parent`/`get_current_kid` | ✅ |
| `confirmationmanager` | email verification codes + Brevo sending | ✅ |
| `frontendmanager/eduParent` | FE-facing EPs for parent app, aggregates other managers | ✅ full auth lifecycle |
| `frontendmanager/eduWay` | FE-facing EPs for kid app, aggregates other managers | ✅ full auth lifecycle |
| `schoolmanager` | assignments/subjects/timetables | ❌ does not exist yet |

Passwords never live on Parent/Kid tables — separate `ParentPassword`/
`KidPassword` tables in securitymanager, unique FK back to owner.
Grade/learning_system on Kid are plain strings — validated in FE only.
Kid-parent is 1:1 currently (`Kid.parent_id`); `MAX_PARENTS_PER_KID = 2`
stubbed in kidsmanager/logic.py for a future many-to-many, unused today.

---

## 4. THE TWO KID AUTH FLOWS

Both use the same HMAC-signed token mechanism (`securitymanager/logic.py`:
`generate_kid_token`/`verify_kid_token`), different DB tables, never conflate.

**A) Claim token (`KidClaimToken`)** — signup/first-time provisioning.
Parent creates Kid → generates claim QR → kid scans once → sets password
→ claimed. One-time use, 15-min TTL. FE-facing via
`frontendmanager/eduWay`: `GET /claim/{row_id}/{token}` (preview, now
returns `is_claimed` — see §9) → `POST /claim/{row_id}/{token}/confirm`
(sets password, consumes token).

**B) Login token (`KidLoginToken`)** — day-to-day QR login. Parent's app
shows a live short-lived QR → kid scans → token dies IMMEDIATELY at scan
(not at password confirm) → kid lands on password screen pre-identified.
FE-facing: `POST /login/{row_id}/{token}/resolve` (kills token, returns
kid info) → `POST /login/confirm` (kid_id + password, NO token — already
dead by this point).

Every token needs both the signed string AND the DB row's id (self-
contained signature + row for replay/expiry tracking). Secret: `TOKEN_SECRET` env var.

---

## 5. FORGOT PASSWORD

Separate from tokens — 6-char alphanumeric codes, 15-min TTL, hashed at
rest. Parent flow needs confirmationmanager to email the code (gated by
"is this email verified?"). Kid flow: parent reads the code off their
own screen, tells the kid, no email involved. Both use `verified_at` as
the hinge between "enter code" and "set new password" screens.

**These routes still live directly in `securitymanager/router.py`, NOT
wrapped by frontendmanager yet.** Not part of the FE cross-check phase
done so far — still open work if/when reset-password screens get built out.

---

## 6. FRONTENDMANAGER — FULL AUTH LIFECYCLE

Two independent subfolders, never share a file, never call each other:
`frontendmanager/eduParent/` and `frontendmanager/eduWay/`. Router
prefixes: `/frontend/parent/...` and `/frontend/kid/...`.

### Generic owner token (proof_token)
`securitymanager/logic.py`: `generate_owner_token(owner_id)` /
`verify_owner_token(token)` — thin aliases over `generate_kid_token`/
`verify_kid_token`, generalized to any int owner_id. 15-min TTL, no DB
row. Used to prove "this request came right after a verified step"
without trusting a bare ID in the URL/body.

### eduParent EPs (9 total)
1. `POST /signup` — atomic(create_parent + create_parent_password),
   rollback on password failure. Verification email sent after, best-effort.
   Returns `{parent, verification_id, verification_expires_at}`.
2. `POST /confirm-email/{verification_id}` — body `{code}`. Returns
   `{parent_id, status, proof_token}`.
3. `PATCH /more-info` — body `{proof_token, ...profile fields, remember_me,
   device_info}`. No parent_id in URL — proof_token-gated. Fills profile +
   issues session. Returns `{parent, token, expires_at}`. This is where
   the person lands on home.
4. `POST /login` — body `{email, password, remember_me, device_info}`.
   Returns `{parent, token, expires_at}`. 401 generic on failure, no
   lockout/rate-limiting (deliberately skipped).
5. `POST /logout` — Bearer token header, revokes current session only.
6. `POST /logout-all` — requires valid session. Cascades to every kid
   under that parent (pulls kid_ids via kidsmanager first).
7. `GET /kids` — list kids for the logged-in parent.
8. `GET /kids/{kid_id}` — single kid profile + claim status.
9. `GET /dashboard` — aggregates parent profile + kid list in one call.
   Added because the old `/auth/me` route the FE was calling doesn't
   exist — this is the correct facade route, session-authed.

### eduWay (kid) EPs (7 total)
1. `GET /claim/{row_id}/{token}` — read-only preview, does NOT consume
   token. Returns `{kid, is_claimed}`. `is_claimed` added post-launch
   (see §9) — FE must branch on it.
2. `POST /claim/{row_id}/{token}/confirm` — body `{password}`. Blocks
   re-claim, sets password, consumes token. Returns `{kid_id, proof_token}`.
3. `PATCH /more-info` — proof_token-gated, same pattern as parent's.
   `remember_me` exposed here too (kids get remember_me — deliberate,
   kids forget passwords more than parents).
4. `POST /login/{row_id}/{token}/resolve` — kills token immediately.
   Returns kid info for "Hi {name}" screen.
5. `POST /login/confirm` — body `{kid_id, password, remember_me,
   device_info}`. No token — already consumed by resolve.
6. `POST /logout` — single device only, no logout-all for kids (that's
   parent-triggered, cascading, lives in eduParent's logout-all).
7. `GET /dashboard` — session-authed (`get_current_kid`), returns
   `KidProfileOut`. Replaces the dead `/auth/me` the FE was calling.

### Stale routes — commented/flagged, not deleted (rollback insurance)
- `parentmanager/router.py` `/parent/signup` — marked `# STALE`, body
  still live. Superseded by frontendmanager's signup (adds rollback +
  verification email).
- `securitymanager/router.py` `preview_claim`/`confirm_claim` pair
  (`/security/kids/claim/{row_id}/{token}...`) — FULLY commented out.
  `create_claim_token`, `claim_token_status`, `create_login_token`,
  `resolve_login`, `confirm_login` are all still LIVE, not stale.

---

## 7. main.py, requirements, DEPLOY STATE (major changes this pass)

- Old `app/` folder (auth.py, progress.py, app.db.connection,
  app.security.hashing) — **DELETED**, backed up to
  `~/work/Eduway/backend/app_folder_backup_20260819.tar.gz`. `progress.py`
  logic (UserProgress) was NOT migrated — no manager owns it, only in
  the backup tarball. Decide later if/when progress tracking work comes up.
- `main.py` now lives at backend ROOT, not inside any `app/` folder.
  Imports `Base`/`engine` from `dbmanager.connection`, wires all 7
  manager routers + both frontendmanager routers.
- `hash_password`/`verify_password` (passlib bcrypt) moved permanently
  into `securitymanager/logic.py`, re-exported from `securitymanager/crud.py`.
- **`Base.metadata.create_all(bind=engine)` REMOVED from main.py.**
  Alembic now owns schema exclusively. This was a real bug this
  session — `create_all()` racing against `alembic upgrade` caused a
  `DuplicateTable` crash. Never re-add `create_all()` to main.py.
- **Alembic baseline regenerated from scratch.** All old migration
  files deleted (explicit call, fresh start), new baseline autogenerated
  (`migrations/versions/a8a20ec8d647_baseline.py`) against a fully
  empty DB — contains real `CREATE TABLE` statements for all 12 tables.
  `migrations/env.py` correctly imports all 5 manager `models.py` files.
- **`config/requirements.txt` cleaned:** dropped `redis`, `pyjwt`
  (confirmed zero imports anywhere in codebase). Added `requests`
  (confirmationmanager's Brevo calls need it — was a real missing-dep
  crash on Railway) and `alembic==1.18.5` (pinned to match local).
- **`Procfile` fixed:** was `web: uvicorn app.main:app` (stale, pointed
  at deleted folder) — now `web: uvicorn main:app --host 0.0.0.0 --port $PORT`.
- **Local Postgres and Railway Postgres were both wiped and rebuilt**
  from the new baseline this session (`DROP SCHEMA public CASCADE;
  CREATE SCHEMA public;` then `alembic upgrade head`) — deliberate
  fresh-start call, not accidental data loss.
- **Redis service is STILL PROVISIONED on Railway** as of this doc's
  writing — flagged for removal (decision already made, not yet
  executed). Check `railway status` — if `Redis: ● Online` still shows,
  it needs to be removed via Railway dashboard/CLI once confirmed
  nothing depends on it.
- **Railway deploy status: was actively being debugged when this doc
  was last updated.** Crash chain this session: (1) stale Procfile →
  fixed, (2) missing `requests` dependency → fixed, (3) missing `KidOut`
  import in `frontendmanager/eduParent/schemas.py` (real bug, `DashboardOut`
  used `KidOut` without importing it) → fixed. **Check `railway status`
  and `railway logs --service backEnd` before assuming production is
  healthy** — do not trust this doc's "done" claims over the live check.
- **FastAPI version 0.140.7** — wraps `include_router()` as lazy
  `_IncludedRouter` objects. Use `app.openapi()['paths']`, NOT
  `len(app.routes)`, to verify routes registered.

---

## 8. MOBILE APPS — BUILD STATE

- Both apps: Expo SDK 57, `expo-camera`/`expo-notifications`/`expo-updates` installed.
- `.env` files in both apps: `EXPO_PUBLIC_API_URL` uncommented, pointing
  at Railway production URL (`https://backend-production-0bf71.up.railway.app`).
  This only takes effect on a real `eas build` — not a dev reload.
- Both `eas.json` now have `"appVersionSource": "remote"` set at the
  `cli` level (EAS tracks version codes server-side, avoids local
  version-file collisions).
- **eduParent production APK build: completed** this session
  (`eas build --platform android --profile production`), `autoIncrement:
  true` added to its production profile to match eduWay.
- **eduWay production APK build: was in progress/queued** as of this
  doc's last update — confirm completion status before assuming it's
  ready to ship to clients.
- Neither app has a build yet that bundles `expo-updates`' native
  module in a way that's been verified working — `useAppUpdates`/
  `useManualUpdateCheck` hooks (eduWay) guard against the native module
  being absent (`require('expo-updates')` wrapped in try/catch) so the
  app won't crash on older/dev-client builds, but OTA won't actually
  function until a build with the module properly linked is confirmed
  and an `eas update` is published against it.

---

## 9. UPDATE — claim preview now returns is_claimed

`frontendmanager/eduWay`'s `GET /claim/{row_id}/{token}` returns
`{kid, is_claimed}`. Closes a dead-end: previously an already-claimed
kid's QR would preview fine, walk through ConfirmDetails/SetPassword,
and only fail at final confirm with a 400. FE (`ScanQrScreen.js`) now
checks `is_claimed` right after the scan and redirects straight to
`KidLoginScreen`, skipping the dead path. Computed in
`frontendmanager/eduWay/crud.py`'s `preview_claim` via
`security_crud.get_kid_password(db, kid_id) is not None`.

---

## 10. WHAT'S CONFIRMED WORKING END-TO-END (this session, eduWay only)

- Full kid claim flow: scan → preview (with is_claimed check) → confirm
  password → more-info → session issued → home. Visually confirmed by
  the person, not just BE-tested.
- Kid QR login flow: resolve → confirm → session. Fixed from a dead
  `/auth/kids/login` + `/auth/me` combo to the real
  `/frontend/kid/login/confirm` contract (also dropped the redundant
  second fetch — confirm's response already has the full kid profile).
- Kid logout: `ProfileScreen.js` now actually calls `/frontend/kid/logout`
  before clearing local session state (previously was local-only, a real bug).
- Kid dashboard-fetching screens (`KidsHomeScreen`, `ProfileScreen`,
  `SchoolScreen`, `AssignmentsScreen`) repointed from dead `/auth/me` to
  `/frontend/kid/dashboard`.
- eduWay-only manual "Check for updates" screen, linked from Profile,
  built and wired (separate from the silent auto-check-on-launch banner
  in App.js — both exist, serve different purposes).

## 11. WHAT'S NOT YET CONFIRMED (do not assume done)

- **eduParent FE screens were NOT walked through this session** beyond
  BE-side dashboard EP addition. `ScanQrScreen`-equivalent, `AuthScreen`,
  signup flow screens on the parent app have not been re-verified
  against the current frontendmanager contract. Treat as unverified,
  not broken — just unchecked.
- **Forgot-password flows (both apps)** — routes exist BE-side in
  securitymanager, un-wrapped by frontendmanager, FE screens
  (`ResetCodeScreen`, `ResetPasswordConfirmScreen` on eduWay) not
  checked against them this session.
- **Railway's actual live/healthy status** — see §7, was mid-fix at
  last doc update. Verify before treating production as stable.
- **Redis removal on Railway** — decision made, not executed.
- **eduWay's production build completion** — confirm before distributing.
