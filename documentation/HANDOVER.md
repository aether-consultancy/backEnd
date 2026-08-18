# EDUWAY BACKEND — HANDOVER / ONBOARDING DOC
_Read this before touching the codebase. Written for whoever (human or AI) picks this up next._

---

## 1. WHO YOU ARE WORKING WITH

The person running this project is the founder/sole dev. Key things to know before writing a single line:

- **Terse, fast-moving, hands-on-keyboard.** He runs every command himself on his own machine (`osaka`), copy-pasting from chat. You never have direct filesystem access — treat every code block you write as something HE executes and reports back to you.
- **All code delivered as heredoc (`PYEOF() { cat <<'EOF' ... EOF }; PYEOF | bash` or `PYEOF() { cat <<'EOF' ... EOF }; PYEOF > /tmp/x.py && cat /tmp/x.py > target/path`) or `sed -i`.** Never tell him to open an editor. Never create files for download — everything is a terminal command.
- **No file downloads, no artifacts.** This is a CLI-only workflow.
- **Code style:** minimal spacing, no decorative padding/alignment, clean and compact — "this is official codebase," not a tutorial.
- **He catches your mistakes.** Multiple bugs have shipped in first drafts (dangling imports, orphaned fields, unguarded routes). ALWAYS re-verify by asking him to `cat`/`grep` the file back before declaring something done. Don't assume a write succeeded — confirm.
- **He asks "we good??" a lot.** Answer honestly — if there's a real bug, say so and fix it. Don't rubber-stamp.
- **He drives architecture, you propose options.** When he asks "what would you suggest," give a real recommendation with reasoning, not a menu with no opinion. He'll often cut it down ("that's a shit list") — that's normal, don't take it personally, just tighten up.
- **Currency: KSH, not USD**, if money ever comes up.
- **He is based in Nakuru, Kenya** — relevant for phone number formats (E.164, `+254...`), curriculum references (CBC), and localization decisions.

---

## 2. THE PROJECT

**Eduway** — a learning terminal system for schools that don't have an existing school management system. Three portals: Student, Parent, Teacher (student portal not yet built at time of writing).

- Two separate Expo/React Native apps: `eduParent` (parent-facing) and `eduWay/frontend` (kid-facing).
- Backend: FastAPI + SQLAlchemy + PostgreSQL, deployed on Railway.
- Backend root: `~/work/Eduway/backend`
- Frontend apps: `~/work/Eduway/eduParent` and `~/work/Eduway/eduWay/frontend`

Brand: electric green `#3ED65E` + deep blue `#1A3FA0`. Mascots: Dobi (starfish, younger grades), Zeek & Zara (older grades).

---

## 3. THE MANAGER ARCHITECTURE (READ THIS CAREFULLY)

The entire backend is being restructured from a monolithic `app/` folder into independent **managers**. This is the single most important structural decision in the codebase — do not violate it.

### The rule: one manager, one job.
A manager owns ONE domain. It does not reach into another manager's tables directly. Cross-manager work happens by importing the other manager's `crud` module and calling its functions — never by querying another manager's models directly from your own crud/router.

### Every manager has (up to) 5 files:
1. **`models.py`** — SQLAlchemy tables this manager owns. Nothing else lives here.
2. **`logic.py`** — the "brain." Pure business rules, constraints, validation functions. NO db session, no I/O. Pure functions that take data in, return decisions out.
3. **`schemas.py`** — Pydantic request/response shapes.
4. **`crud.py`** — the only file that touches the DB session directly. Every read/write goes through here. Can import other managers' `crud` when cross-manager writes are needed (see parentmanager→securitymanager example below).
5. **`router.py`** — FastAPI routes ("EPs" — endpoints, his shorthand). Calls into `crud`/`logic`. No DB logic of its own.

Not every manager needs a `logic.py` if there's nothing rule-based to enforce — but models/schemas/crud/router are close to mandatory once a manager owns any table.

### Managers that exist so far:

| Manager | Owns | Status |
|---|---|---|
| `dbmanager` | DB engine/session (`connection.py`) — no models of its own | ✅ done |
| `parentmanager` | `Parent` table (identity/profile data only — NOT password) | ✅ done |
| `securitymanager` | `ParentPassword`, `KidPassword`, `KidClaimToken`, `KidLoginToken`, `ParentResetCode`, `KidResetCode` — ALL password hashes, ALL tokens/codes | ✅ done |
| `kidsmanager` | `Kid`, `KidInfo` | ✅ done |
| `sessionmanager` | opaque bearer-token sessions (parent + kid, one table via owner_type/owner_id), issue/validate/logout/logout-all, TTL 7d default / 90d remember_me | ✅ done |
| `confirmationmanager` | email verification codes + Brevo sending | ✅ done, not wired to legacy parentmanager signup (see below) |
| `schoolmanager` | assignments/subjects/timetables | ❌ still not built — doesn't exist as a folder yet |
| `frontendmanager` | aggregates multi-manager calls into single FE-facing EPs, split into `frontendmanager/eduParent` and `frontendmanager/eduWay` subfolders (one per app, never mixed) | ✅ full auth lifecycle done for both apps (see §9) |

### Critical domain-split decisions already made — do not re-litigate these without him:
- **Passwords never live on the Parent/Kid table.** They live in `securitymanager` as separate tables (`ParentPassword`, `KidPassword`) with a unique FK back to the owner. `parentmanager.crud.create_parent()` does NOT set a password — `parentmanager.router.signup()` calls `securitymanager.crud.create_parent_password()` right after creating the Parent row.
- **Redis was deliberately removed.** Decided not needed at current scale. Logout/blacklist and caching will be handled via Postgres tables in `sessionmanager` instead. Don't reintroduce Redis without discussing it with him first.
- **Grade / learning_system on Kid are plain strings, not enums.** Constraint/validation for allowed values belongs in the FRONTEND, not the DB. This was an explicit reversal — first draft had a Python enum, he corrected it.
- **Kid-parent relationship is currently 1:1 (`Kid.parent_id`).** A future 2-parents-per-kid feature is planned but NOT implemented. `kidsmanager/logic.py` has `MAX_PARENTS_PER_KID = 2` and `can_link_another_parent()` stubbed in, commented as unused, waiting for a future `KidParentLink` many-to-many table.

---

## 4. THE TWO KID AUTH FLOWS (easy to confuse — read carefully)

Both use the same underlying signed-token mechanism (`securitymanager/logic.py`: `generate_kid_token` / `verify_kid_token`), but they are semantically different and use SEPARATE DB tables. Never conflate them.

### A) Claim token (`KidClaimToken`) — signup / first-time provisioning
- Parent creates a Kid record → generates a claim token/QR → kid scans it once → kid sets their password → account is "claimed."
- One-time use. TTL: 15 minutes.
- Route family: `/security/kids/{kid_id}/claim-token`, `/security/kids/claim/{claim_row_id}/{token}`, `.../confirm`

### B) Login token (`KidLoginToken`) — day-to-day QR login
- Parent's app shows a live QR (short-lived) → kid scans it → **token dies immediately at scan** (`used_at` set at resolve, not at password confirm) → app lands kid on a login screen pre-identified as that kid_id, password still required.
- Two-step, decoupled: `/security/kids/login/{login_row_id}/{token}/resolve` (kills token, returns kid_id) → `/security/kids/login/confirm` (plain kid_id + password, NO token involved — token is already dead by this point).
- TTL: 15 minutes, though intended for near-immediate use (like WhatsApp Web QR).
- **Do not require the token to survive into the confirm step** — this was a real bug caught and fixed. The confirm step only needs the `kid_id` the client already got back from resolve.

### Token internals (both A and B share this)
- HMAC-SHA256 signed, `kid_id` embedded in the payload (not a DB lookup for identity — the DB row is ONLY used for replay/expiry tracking via `used_at`/`expires_at`).
- Every generated token/QR link needs BOTH the signed token string AND the DB row's `id` — because the token is self-contained but you still need to know which row to check/mark used. URL shape: `.../{row_id}/{token}`.
- Secret: `TOKEN_SECRET` env var.

## 5. FORGOT PASSWORD (separate mechanism from the above — codes, not tokens)

Both parent and kid have a forgot-password flow, but they're NOT QR/HMAC tokens — they're 6-char alphanumeric codes (`securitymanager/logic.py`: `generate_reset_code`), TTL 15 min, hashed at rest (`code_hash`, same hashing as passwords).

- **Parent flow:** request → confirmationmanager (not yet built) sends the code via Brevo email → parent enters code (`verify` step, two-step) → parent sets new password (`set-password` step). Gated by "is this email verified?" — that gate belongs to confirmationmanager, not securitymanager. securitymanager's routes assume the gate has already passed.
- **Kid flow:** parent generates the code in their own app (nothing sent anywhere — parent just reads it off-screen and tells the kid) → kid enters code → forced onto a set-new-password screen. Same two-step DB pattern (`verified_at` set on verify, `used_at` set on final consume) as parent, just no email/Brevo involved.
- Both use `verified_at` as the hinge between the "verify code" screen and "set new password" screen — this exists specifically to support a two-screen UX without re-sending the code.

**Brevo note:** Brevo is a mail carrier only. It does NOT generate OTPs/codes — you generate the code yourself and Brevo just sends the email. Confirmed via search, don't assume otherwise.

---

## 6. KNOWN GAPS / PLACEHOLDER WIRING (don't be surprised by these)

- **`get_current_parent` / `get_current_kid`** are still imported from the OLD `app.api.deps` in every manager's router.py. These need to be replaced once `sessionmanager` is built (session-based auth is replacing raw JWT). Every file importing from `app.api.deps` is a known placeholder, not a mistake.
- **`app.security.hashing`** (the actual `hash_password`/`verify_password` bcrypt functions) is still the old location — securitymanager re-exports it. Fine for now, may get pulled fully into securitymanager later.
- **kidsmanager's `delete_kid` does NOT clean up securitymanager's rows** (KidPassword, tokens, reset codes) — that's intentionally a SEPARATE route (`DELETE /security/kids/{kid_id}`) in securitymanager. The plan is for `frontendmanager` to expose ONE delete-kid endpoint to the FE that internally calls both. `frontendmanager` does not exist yet — until it does, deleting a kid from the FE requires calling both endpoints, or you'll orphan security rows.
- **`schoolmanager`** (assignments/subjects/timetables) and the old `app/api/*.py` files have NOT been migrated into this manager pattern yet. Treat `app/` as legacy soon-to-be-retired scaffolding, not the source of truth.
- **CBC grade/learning_system constraint** lives in the frontend only — the backend stores plain strings, does not validate.

---

## 7. MOBILE APPS (Expo) — CURRENT STATE

- Both `eduParent` and `eduWay/frontend` are on Expo SDK 57.
- Both now have `expo-camera`, `expo-notifications`, `expo-updates` installed.
- Both `app.json` files have `runtimeVersion: {"policy": "appVersion"}` and `updates.url` pointing at their respective `https://u.expo.dev/<projectId>`.
- **A new native build (`eas build`) is required** before OTA updates will work — camera/notifications/updates are new native modules not yet in any built binary. Once that build ships, future JS-only changes can go out via `expo-updates` OTA without a new store build.

---

## 8. HOW TO WORK WITH HIM GOING FORWARD

1. When asked to build a new manager: ask what data/fields first, let him cut the list down, THEN write models. Don't skip straight to code.
2. Deliver everything as heredoc/sed commands he can paste and run. Never say "create a file with this content" without giving the actual terminal command.
3. After any batch of changes, ask him to `cat`/`grep` the affected files back to you and actually check for bugs (missing imports, orphaned references, unguarded routes) — this has caught 4+ real bugs already. Don't skip this step even when you're confident.
4. If a decision has cross-manager implications (e.g. "who owns this field"), state the tradeoff plainly and let him decide — he has strong, fast opinions about domain ownership.
5. Respect the one-manager-one-job rule even when it's less convenient — he has explicitly corrected drift toward convenience (e.g. moving password_hash off Parent even though it was "already working").
6. Check this file's §6 (known gaps) before assuming something is broken — some incomplete wiring is deliberate and waiting on a not-yet-built manager.

---

_Last updated: reflects state through kidsmanager completion (models/logic/schemas/crud/router all shipped). Next manager up: sessionmanager or confirmationmanager._


## 9. FRONTENDMANAGER — FULL AUTH LIFECYCLE (built after this doc's original writing)

Two independent subfolders, never share a file, never call each other:
`frontendmanager/eduParent/` and `frontendmanager/eduWay/`. Each has
schemas.py/crud.py/router.py (no models.py — owns no tables; no logic.py
— ordering rules live inline in crud.py as comments). Router prefixes:
`/frontend/parent/...` and `/frontend/kid/...`.

### Generic owner token (proof_token)
`securitymanager/logic.py` has `generate_owner_token(owner_id)` /
`verify_owner_token(token)` — thin aliases over the existing
`generate_kid_token`/`verify_kid_token` HMAC functions, generalized to
any int owner_id, not just kid_id. 15-min TTL, no DB row (no used_at
tracking — single-shot proof, not a claim). Used wherever a later step
in a flow needs proof "this request came right after a verified step"
without trusting a bare ID in the URL/body (guessable-ID protection).

### eduParent EPs (7 total)
1. `POST /frontend/parent/signup` — atomic(create_parent + create_parent_password);
   password-save failure rolls back the parent row. Verification email
   sent AFTER that succeeds (best-effort, never rolls back a valid
   account). Returns `{parent, verification_id, verification_expires_at}`.
2. `POST /frontend/parent/confirm-email/{verification_id}` — body: `{code}`.
   Verifies via confirmationmanager, returns `{parent_id, status, proof_token}`.
3. `PATCH /frontend/parent/more-info` — body includes `proof_token` +
   profile fields + `remember_me` + `device_info`. Gated by proof_token
   (NOT a bare parent_id in the URL — that was a deliberate fix, see
   git history / prior chat). Fills profile + issues session in one call.
   Returns `{parent, token, expires_at}`.
4. `POST /frontend/parent/login` — body: `{email, password, remember_me,
   device_info}`. Resolves email→parent_id, verifies password, issues
   session. No lockout/rate-limiting (deliberately skipped — sessionmanager
   covers revocation, lockout wasn't asked for).
5. `POST /frontend/parent/logout` — single device. Bearer token in
   Authorization header, revokes that one session row.
6. `POST /frontend/parent/logout-all` — requires an active session
   (`get_current_parent` dependency). Cascades to every kid under that
   parent (pulls kid_ids via kidsmanager, since sessionmanager never
   imports kidsmanager directly — one-manager-one-job).

### eduWay (kid) EPs (6 total)
1. `GET /frontend/kid/claim/{claim_row_id}/{token}` — read-only preview,
   validates claim token WITHOUT consuming it, returns kid record for
   the "is this you" screen.
2. `POST /frontend/kid/claim/{claim_row_id}/{token}/confirm` — body:
   `{password}`. Re-verifies token, blocks re-claiming an already-claimed
   kid, sets password, marks token used, returns `{kid_id, proof_token}`.
3. `PATCH /frontend/kid/more-info` — same proof_token-gated shape as
   parent's more-info. `remember_me` is exposed here too — kids get
   remember_me (deliberate call: kids forget passwords more than
   parents, QR+remember_me minimizes friction without weakening security
   since revocation still works via the sessions table).
4. `POST /frontend/kid/login/{login_row_id}/{token}/resolve` — QR scan:
   kills the login token IMMEDIATELY at this step (used_at set here, not
   at confirm), returns kid record so app can show "Hi {name}".
5. `POST /frontend/kid/login/confirm` — body: `{kid_id, password,
   remember_me, device_info}`. NO token here — resolve already killed
   it, this is plain credential check + session issuance.
6. `POST /frontend/kid/logout` — single device only. No logout-all for
   kids (that's parent-triggered only, lives in eduParent's logout-all).

### Stale routes — commented out, NOT deleted
Two pairs of routes were superseded by frontendmanager but kept
(commented, with a pointer comment to the replacement) as rollback
insurance until the new routes are proven in production:
- `parentmanager/router.py` — the old `/parent/signup` POST route is
  marked `# STALE` (function body still live/uncommented, just flagged)
  since frontendmanager/eduParent's signup fully replaces it (adds
  atomic rollback + verification email it never had).
- `securitymanager/router.py` — `preview_claim`/`confirm_claim`
  (`GET/POST /security/kids/claim/{claim_row_id}/{token}...`) are FULLY
  commented out (not just flagged) since frontendmanager/eduWay's
  claim-preview/claim-confirm are a strict superset (adds proof_token).
  `create_claim_token`, `claim_token_status`, `create_login_token`,
  `resolve_login`/`confirm_login` (old, pre-frontendmanager versions)
  are all still LIVE and NOT stale — only the preview+confirm PAIR was
  duplicated by frontendmanager.

### main.py — brand new, `app/` folder deleted
The old `app/` folder (auth.py, progress.py, app.db.connection, and
app.security.hashing) is GONE — deleted and backed up to
`~/work/Eduway/backend/app_folder_backup_20260819.tar.gz`. `main.py` is
now at the backend ROOT (`~/work/Eduway/backend/main.py`), not inside
any `app/` folder. It imports `Base`/`engine` from `dbmanager.connection`
(not the old `app.db.connection`) and wires all 7 manager routers plus
both frontendmanager routers via `include_router`.

`hash_password`/`verify_password` (passlib bcrypt) moved from the
deleted `app/security/hashing.py` into `securitymanager/logic.py` —
this is their permanent home now, re-exported from `securitymanager/crud.py`
for any router that still imports from there.

**`progress.py` was NOT migrated** — its logic (UserProgress data,
part of the original C++ rendering engine backend architecture) is
sitting in the backup tarball only. No manager owns it yet. If progress
tracking work comes up, decide then whether it becomes its own manager
or folds into an existing one — don't assume it's covered.

**FastAPI version note**: this backend runs FastAPI 0.140.7, which
wraps `include_router()` calls as lazy `_IncludedRouter` objects — DO
NOT check `len(app.routes)` or iterate `app.routes` directly to verify
routes registered (older-FastAPI habit, gives false negatives on this
version). Use `app.openapi()['paths']` instead — that forces full
resolution and shows every real registered endpoint.

## 10. NEXT PHASE — FRONTEND CROSS-CHECK (see FE_CROSSCHECK_ORIENTATION.md)

As of this doc's update, backend auth work for BOTH apps is functionally
complete and smoke-tested (app loads, all expected paths present in the
OpenAPI schema). The person is now moving to validate/rebuild the FE
screens against these new contracts — starting with eduParent, then
eduWay, then bundling both apps together (with an app-update-check
page/logic still to be added after that). See the dedicated orientation
doc for full context on that phase; it's long enough to warrant its own
file rather than growing this one further.
