# Security Policy

## Reporting a vulnerability

Please report security issues privately using GitHub's
[private vulnerability reporting](https://github.com/gabbyg4/ForgeMyCV/security/advisories/new)
rather than opening a public issue. We aim to respond within a few days.

## How ForgeMyCV protects users

- **No data storage.** There are no accounts and no database. Details are sent to OpenAI to write
  the documents and are not stored or logged by the app. Drafts live only in the user's browser
  and expire after 7 days.
- **Safe rendering of AI output.** Markdown is rendered with raw HTML and images disabled, then
  sanitised with an allowlist ([nh3](https://github.com/messense/nh3)). Only `http`, `https`,
  `mailto` and `tel` links survive, with `rel="noopener noreferrer nofollow"`.
- **Content Security Policy.** `default-src 'none'`, with a fresh nonce per response for the inline
  stylesheet and script, so injected scripts, styles, images and frames are blocked.
- **CSRF protection.** Cross-site POST requests are rejected using `Sec-Fetch-Site`, falling back
  to the `Origin` header.
- **Prompt-injection hardening.** User input is fenced as data, invisible/bidirectional control
  characters are stripped, and model output is treated as untrusted.
- **Abuse and cost controls.** Per-client rate limits (IPv6 grouped by /64), a global daily cap,
  a cap on output tokens and request timeouts. Only requests that reach OpenAI use up the quota.
- **Security headers.** HSTS (over HTTPS), `X-Frame-Options`, `X-Content-Type-Options`,
  `Referrer-Policy`, `Permissions-Policy` and cross-origin isolation headers.
- **Input limits.** Per-field length limits and a request size cap.
- **Supply chain.** CI runs the tests, `pip-audit` and `bandit` on every change and weekly;
  Dependabot keeps dependencies up to date.

## Deployment checklist

- Serve over HTTPS only.
- Keep `FLASK_DEBUG` unset in production and run behind gunicorn (see README).
- Set `TRUST_PROXY_HOPS` to the exact number of proxies in front of the app - never more, or
  clients could spoof their IP address to bypass rate limits.
- With several workers or servers, use a shared `RATE_LIMIT_STORAGE` such as Redis.
- Set a monthly spending limit on your OpenAI account as a final safeguard.
- Keep `OPENAI_API_KEY` in your host's secret store or `.env` (which is git-ignored) - never commit it.
