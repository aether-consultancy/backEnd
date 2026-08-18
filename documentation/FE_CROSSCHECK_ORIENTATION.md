# EDUWAY — FRONTEND CROSS-CHECK ORIENTATION
_For whoever picks up the FE validation phase. Read HANDOVER.md first — this doc assumes everything in it, especially §9 and §10._

---

## 1. WHAT THIS PHASE IS

The backend auth lifecycle (signup, verification/claim, profile
completion, login, logout) is DONE for both apps, built through
`frontendmanager` — a BE layer that aggregates multi-manager calls into
single FE-facing endpoints, split into `frontendmanager/eduParent/` and
`frontendmanager/eduWay/` (one subfolder per app, contracts never mixed).

The FE apps (`~/work/Eduway/eduParent` and `~/work/Eduway/eduWay/frontend`,
both Expo/React Native) were built against an OLDER, now-partially-stale
BE contract. Your job in this phase is NOT to build new backend — it's
to walk through each FE screen in the auth flow, confirm it calls the
right frontendmanager EP with the right shape, and fix mismatches.
Order: **eduParent first, prove it out completely, then eduWay, then
the person bundles both apps together** (with an update-check page/logic
to be added after that — not your job unless asked).

---

## 2. WORKING STYLE (same as backend phase — do not deviate)

- **Terse, fast-moving, hands-on-keyboard.** He runs every command
  himself, copy-pasting from chat. You have no direct filesystem access.
- **ALL code delivered as heredoc** (`PYEOF() { cat <<'EOF' ... EOF }; PYEOF | bash`
  or `PYEOF() { cat <<'EOF' ... EOF }; PYEOF > /tmp/x.js && cat /tmp/x.js > target/path`)
  **or `sed -i`.** Never tell him to open an editor.
- **No file downloads, no artifacts.** CLI-only.
- Code style: minimal spacing, no decorative alignment, compact,
  non-AI-looking. Comments only where they explain a real decision —
  not restating what the code does.
- **He catches mistakes.** ALWAYS ask him to `cat`/`grep` a file back
  after writing it, before declaring anything done.
- **"we good??" is his standard check-in phrase.** Answer honestly.
- **He drives architecture decisions, you propose options with real
  reasoning** — not a menu with no opinion.
- Currency: KSH. Based in Nakuru, Kenya (phone format `+254...`, CBC
  curriculum references).
- User preferences on file (apply automatically): no long AI
  explanations, all code in chat, code fixes as `sed -i` or python
  commands, code given as PYEOF CLI heredoc commands.

---

## 3. FULL BACKEND CONTRACT — READ BEFORE TOUCHING ANY FE FILE

This is the ENTIRE surface you're validating against. Every field name,
every gate, matters — the FE must match exactly.

### eduParent (parent app) — prefix `/frontend/parent`

**1. `POST /signup`**
Request body: `{full_name, email, phone, preferred_language, nickname,
avatar_url, relation, family_name_for_kids, password, terms_accepted}`
(see `parentmanager/schemas.py` `ParentSignup` for the authoritative
field list — this doc may drift, that file won't).
Response: `{parent: {...ParentOut fields}, verification_id: int,
verification_expires_at: ISO string}`.
BE validates: terms_accepted must be true, phone must include country
code, password strength, email not already registered. Any failure =
400 with a message string.

**2. `POST /confirm-email/{verification_id}`**
Path param: verification_id (int, from step 1's response).
Body: `{code: string}` (6-char alphanumeric code, sent via email).
Response: `{parent_id: int, status: "verified", proof_token: string}`.
**The FE MUST hold onto `proof_token`** — it's required for step 3 and
is NOT re-derivable from anything else. 15-min TTL from issuance.

**3. `PATCH /more-info`**
Body: `{proof_token: string, full_name?, phone?, preferred_language?,
nickname?, avatar_url?, relation?, family_name_for_kids?, remember_me:
bool, device_info?: string}`. All profile fields optional (partial
update). `proof_token` is REQUIRED — this is how the BE knows which
parent_id to act on (there is NO parent_id in the URL, deliberately —
see HANDOVER.md §9 for why).
Response: `{parent: {...}, token: string, expires_at: ISO string}`.
**`token` here is the SESSION token** — different from proof_token.
This is what the app stores and sends as `Authorization: Bearer {token}`
on every subsequent authenticated request. This is also the point
where the person LANDS ON HOME — more-info submit = session issued =
logged in.

**4. `POST /login`**
Body: `{email, password, remember_me: bool, device_info?: string}`.
Response on success: `{parent: {...}, token: string, expires_at: ISO string}`.
Response on failure: 401, generic "Invalid email or password" (does
NOT distinguish wrong-email from wrong-password — don't build a FE that
tries to tell those apart either).

**5. `POST /logout`**
No body. Header: `Authorization: Bearer {token}`.
204 No Content on success. 400 if token invalid/already revoked.
This revokes ONE session (the current device only).

**6. `POST /logout-all`**
No body. Header: `Authorization: Bearer {token}` (must be a currently
VALID session — this uses `get_current_parent`, not a raw token check).
Response: `{sessions_revoked: int}`.
**This cascades to every kid under that parent too** — logging out all
devices as a parent also kills every kid session linked to that
parent's kids. This is intentional (see HANDOVER.md/prior chat: "log
out on all devices logs everyone out even the kids"). If the FE builds
a "log out everywhere" button, the copy/confirmation dialog should
reflect that it affects kid devices too, not just the parent's own.

### eduWay (kid app) — prefix `/frontend/kid`

**Context: signup for kids is PARENT-INITIATED.** The parent creates
the Kid record (via `/kids` POST, parentmanager-side, already existing,
not part of this new lifecycle) and generates a claim QR
(`/security/kids/{kid_id}/claim-token`, also pre-existing/still live).
The kid's OWN app-side flow starts at scanning that QR.

**1. `GET /claim/{claim_row_id}/{token}`**
Path params come from the QR code content (parent's app generates a
URL/deeplink shaped `.../claim/{claim_row_id}/{token}`).
Response: `{kid: {id, full_name, school, grade, learning_system}}`.
Read-only — does NOT consume/mark-used the token. This is the "is this
you?" preview screen — no password yet.

**2. `POST /claim/{claim_row_id}/{token}/confirm`**
Same path params as step 1. Body: `{password: string}`.
Response: `{kid_id: int, proof_token: string}`.
This is where the token actually gets consumed (marked used) and the
password gets set. 400 if token invalid/expired OR kid already claimed
(re-claim is blocked).

**3. `PATCH /more-info`**
Body: `{proof_token: string, nickname?, age?, favorite_color?,
favorite_animal?, subjects_loved?: string[], remember_me: bool,
device_info?: string}`. Same proof_token-gating pattern as parent's
more-info. `age` has BE-side range validation (`is_valid_age` in
kidsmanager/logic.py) — 400 if out of range.
Response: `{kid: {...KidProfileOut fields, includes nickname/age/etc},
token: string, expires_at: ISO string}`.
Same as parent: `token` here is the session token, this is where the
kid lands on home.

**4. `POST /login/{login_row_id}/{token}/resolve`**
Path params from a QR the PARENT's app displays LIVE (short-lived,
regenerated) — the kid scans the parent's screen. Kills the token
IMMEDIATELY at this call.
Response: `{kid: {id, full_name, school, grade, learning_system}}`.
This is the "Hi {name}, enter your password" screen trigger — no
password involved yet, and the QR token is already dead by this point
(don't try to reuse it).

**5. `POST /login/confirm`**
Body: `{kid_id: int, password: string, remember_me: bool, device_info?:
string}`. **No token in this call** — step 4 already consumed it, this
is a plain credential check using the `kid_id` the app already has from
step 4's response.
Response: `{kid: {...}, token: string, expires_at: ISO string}`.
401 on wrong password.

**6. `POST /logout`**
Same shape as parent's single-device logout. No logout-all for kids —
that's parent-only, cascading (see eduParent EP6).

---

## 4. THINGS THAT WILL BITE YOU IF YOU DON'T KNOW THEM

- **`proof_token` vs session `token` are DIFFERENT THINGS with
  DIFFERENT LIFETIMES.** proof_token: 15-min TTL, HMAC-signed, used
  exactly once between two specific steps of signup/claim. Session
  token: 7-day or 90-day TTL, opaque random string, used on every
  authenticated request afterward. If a FE screen is confusing these
  two, that's a bug — check variable names carefully in the FE code
  you're reviewing.
- **`remember_me` is exposed on kid flows too** — don't assume it's
  parent-only if you see it missing from a kid screen; it should be
  there (a toggle or default-true, per the person's call that kids need
  it more due to password-forgetting).
- **Kid login has NO password-reveal on the resolve step** — resolve
  only returns kid info, never touches password. If a FE screen tries
  to pre-fill or skip the password step after resolve, that's wrong —
  password confirm is always a separate explicit step.
- **`/frontend/kid/claim/...` (GET preview) is read-only and safe to
  call repeatedly** — but confirm (POST) is NOT idempotent past the
  first successful call (blocks re-claim). If a "back" button on the
  kid app re-triggers confirm after a successful claim, expect a 400 —
  that's correct BE behavior, not a bug to "fix" on the BE side.
- **Old/stale BE routes still exist but should NOT be what the FE
  calls** — `/parent/signup` (parentmanager, not frontendmanager) and
  the commented-out `/security/kids/claim/...` pair are legacy. If you
  find FE code hitting `/parent/signup` instead of
  `/frontend/parent/signup`, that's exactly the kind of mismatch this
  phase exists to catch — fix it to point at frontendmanager.
- **FastAPI version is 0.140.7** — if you ever need to verify routes
  are live BE-side, use `app.openapi()['paths']`, NOT `app.routes`
  iteration (see HANDOVER.md §9, this version lazy-wraps included
  routers and `len(app.routes)` gives false readings).

---

## 5. WHERE THINGS LIVE

- Backend root: `~/work/Eduway/backend` — `main.py` is at this root
  now (not inside any `app/` folder — that folder is deleted).
- eduParent app: `~/work/Eduway/eduParent`
- eduWay (kid) app: `~/work/Eduway/eduWay/frontend` — correct repo root
  has capital W (`eduWay`), a stray lowercase `eduway/` dir was deleted
  previously.
- eduParent already has SOME frontendmanager-shaped FE code:
  `frontendmanager/eduParent/gateway.js` and `crud.js` (JS-side, NOT to
  be confused with the BE Python frontendmanager folders) — these
  predate the current BE contract and are near-certainly stale (old
  contract needed `user_id`, current BE takes `email` for login, and
  none of the new EP shapes — proof_token, split more-info — exist in
  that JS yet). Expect to rewrite these, don't assume they're close.
- eduParent has an AuthScreen with a lanyard/ID-badge flip-card design
  (navy/green branding) — existing UI shell, likely needs its call
  logic rewired rather than its visuals rebuilt.

---

## 6. HOW TO START

1. `cat` the existing `frontendmanager/eduParent/gateway.js` and
   `crud.js` (JS-side) plus the AuthScreen component(s) — see what's
   there before assuming anything.
2. Map each existing FE call site to the correct EP from §3 above.
3. Fix one screen/flow at a time, ask him to test each in the actual
   app (or at minimum confirm the request/response shape via a manual
   call) before moving to the next.
4. Don't touch eduWay until eduParent is fully confirmed working
   end-to-end (signup → confirm → more-info → home, AND login → home,
   AND logout).
5. Update `HANDOVER.md` §10 (or add an §11) with what you find/fix, so
   the next phase (bundling) has continuity.

Good luck — the backend contract in §3 is complete and accurate as of
this doc's writing. Trust it over guessing.
