---
name: app-security-check
description: Security check of a live web app (especially Lovable / Supabase / React / Vite apps). Use when the user asks to "check my app is secure", "run the security checks", "audit security", or names an app/repo to check. Read-only by default; fixes only after the user says yes.
---

# App security check

Check a live app the way an attacker would, then report in plain English. **Read-only by default.**

## Ground rules
- Never print, paste or store secrets, tokens or passwords. If you find one exposed, give its location and type only, never its value.
- Don't change code, data or settings until the user approves the fixes ("Yes" / "Fix all").
- Test only the user's own app. No load or denial-of-service testing, no brute force, and never bypass bot protection or rate limits.
- Test writes only with harmless no-op requests: a `WHERE` that matches nothing, a non-existent id, or a dummy user id that RLS must reject. Never change real rows.
- If a step can't be done (no access, tool missing, network blocked), say so. Don't guess or skip silently.

## 0. Gather
Ask for anything you can't find yourself:
- The live URL.
- The repo, and whether it's attached to this session.
- The Supabase project ref, or the Lovable project id. Use whichever database access exists: Lovable `query_database`, the Supabase MCP, or neither.
- Whether there is a mobile app or browser extension.

## 1. Secrets in the shipped frontend
1. Download the live `index.html`.
2. Crawl every `assets/*.js` chunk, following chunk references until no new files appear, and count them.
3. Grep all chunks for:
   `service_role|sk_live_|sk_test_|rk_live_|whsec_|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|sk-[A-Za-z0-9]{32,}|-----BEGIN|xox[bap]-|ghp_[A-Za-z0-9]{36}|re_[A-Za-z0-9]{20,}`
4. Decode each JWT's payload (middle part only) and report its `role`. `anon` is fine; `service_role` is **critical**.
5. Also grep the repo, including its git history, for committed `.env` files and keys.

## 2. Database access (Supabase)
1. Tables without RLS: `pg_class.relrowsecurity = false` in `public`.
2. Policies that apply to `anon`/`public` with `cmd` in INSERT, UPDATE, DELETE or ALL whose expression doesn't involve `auth.uid()` or a role check. Each one must be an intended public form, with input checks and a rate limit.
3. SECURITY DEFINER functions that `anon` can execute. Read each one and confirm it can't leak private data or write beyond its purpose.
4. Storage buckets marked `public`. Confirm only intentionally public files (images) are in them.
5. Live probes using the public anon key from the bundle:
   - **Reads:** `GET /rest/v1/<table>?select=*&limit=1` for every table that holds user or private data (profiles, CVs, payments, subscriptions, roles, messages, tokens, leads). Expect `[]` or 401/42501.
   - **Writes:** a PATCH or DELETE that matches nothing, and an INSERT into the roles table with a dummy user id. Expect refusal.
   - **Storage:** `POST /storage/v1/object/list/<bucket>` on each private bucket. Expect `[]`.
6. Defence in depth: `anon` table grants for INSERT, UPDATE or DELETE where no policy for that command applies to anon/public. RLS already blocks these writes; revoking the grants adds a second barrier.
7. If an advisor tool is available, run the Supabase security advisor and include its findings.

## 3. Backend / edge functions
1. List the functions with `verify_jwt = false` (`supabase/config.toml`).
2. For each one, confirm its own guard runs **before any work**: a user check, an admin or cron secret, or a webhook signature check.
3. POST `{}` anonymously, with no auth and then with the anon key, to every sensitive function: anything that sends email, calls AI, charges money, runs syncs or admin jobs, or writes data. Expect 401/403.
4. Flag any 200 response. Flag any 500 or 400 that happened before the auth check.
5. Payment webhooks must verify the provider's signature.
6. AI-calling functions need a per-user quota or a fail-closed limit.

## 4. Browser and hosting
1. Check the response headers: HSTS, `X-Content-Type-Options`, `Referrer-Policy`, CSP, and `X-Frame-Options` or `frame-ancestors`.
2. Clickjacking: load the live site inside an `<iframe>` on a test page using Playwright, with and without `sandbox`. The site must refuse or hide. A JS frame guard in `index.html` counts if it works in the test.
3. Confirm HTTP redirects to HTTPS. Check that cookies set by the app are `Secure` and `HttpOnly` where possible.

## 5. Auth settings
These can't be read via SQL, so list them for the user to confirm in the dashboard:
- Leaked password protection.
- Minimum password length.
- Email confirmation.
- OTP / magic-link expiry.
- Redirect-URL allow-list.
- MFA available for admins.

## 6. App logic quick pass (from the repo)
- Admin pages and functions are checked on the **server** (RLS or function), not just hidden in the UI.
- Users can only read and change their own rows: test the policies with `auth.uid()`.
- File uploads limit size and type, and use per-user paths.
- Public forms have rate limits and length limits.
- Outgoing email can't be sent to arbitrary addresses.
- Error messages don't leak internals: stack traces, lists of internal names, raw SQL.
- Dependencies: run `npm audit --omit=dev` and report only high or critical issues in runtime packages.

## 7. Report
Report in plain English, short and non-technical first:
1. **One-line verdict.**
2. **What I checked and passed**, with the evidence: counts, status codes, or what the probe returned.
3. **Issues ranked Critical / High / Medium / Low.** For each: what could happen, who could do it, and the fix.
4. **Settings only the user can change**, with the dashboard path for each.
5. **"Can't check"** items, with the reason.

End with: "Want me to fix these?" **Then stop.**

## 8. Fixing (only after approval)
1. Branch.
2. Make the smallest fixes, as a migration for the database and code changes for the rest.
3. Run the repo's lint, typecheck, tests and build.
4. Open a PR and wait for CI.
5. Merge, apply the migration, and deploy the changed functions and site.
6. **Re-run the exact failing probes** to prove each fix, and report the before and after.
7. If you discover that something you reported was already handled, say so plainly and correct the report.
