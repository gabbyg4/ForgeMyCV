# ForgeMyCV

**ForgeMyCV** is a small Flask web app that turns your details into a polished, ATS-friendly CV and, optionally, a matching cover letter using OpenAI.

## Features

- Landing page explaining the product, plus a focused builder at `/build`
- Structured form: contact details, target role, experience, education, skills and extras
- Optional job description to tailor your documents to a specific advert
- Optional cover letter: add the company, hiring manager and why you want the role
- Never invents facts: only the details you provide are used
- CV and cover letter are generated in parallel and shown in tabs
- Download either as a PDF (via the browser's print dialog) or copy as Markdown
- Edit your details or generate another version straight from the result page
- Your draft is autosaved in your browser, so a refresh or accidental close loses nothing
- Inline validation errors, friendly error pages, per-IP rate limiting and basic security headers
- No accounts and no database: nothing is stored on the server

## Setup

```bash
git clone https://github.com/gabbyg4/ForgeMyCV.git
cd ForgeMyCV
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # then add your OpenAI API key
```

### Configuration (`.env`)

| Variable             | Default        | Description                                                          |
|----------------------|----------------|----------------------------------------------------------------------|
| `OPENAI_API_KEY`     | -              | **Required.** Your OpenAI API key                                    |
| `OPENAI_MODEL`       | `gpt-4o-mini`  | Model used to write the documents                                    |
| `OPENAI_TIMEOUT`     | `90`           | Seconds to wait for OpenAI before giving up                          |
| `RATE_LIMIT`         | `10 per hour`  | Generations allowed per client IP (protects your API credits)       |
| `RATE_LIMIT_STORAGE` | `memory://`    | Rate-limit store; use e.g. `redis://localhost:6379` with several workers |
| `TRUST_PROXY_HOPS`   | `0`            | Set to the number of reverse proxies in front of the app             |
| `FLASK_DEBUG`        | off            | Set to `1` to enable debug mode locally (never in production)        |

## Run locally

```bash
python app.py
```

Visit `http://localhost:5000` in your browser.

## Run in production

Use a production WSGI server, and allow enough time for the AI to respond:

```bash
pip install gunicorn
gunicorn --workers 2 --threads 4 --timeout 120 --bind 0.0.0.0:8000 app:app
```

Serve it over HTTPS, and if it sits behind a reverse proxy, set `TRUST_PROXY_HOPS` so rate limiting sees real client IPs. With more than one worker, point `RATE_LIMIT_STORAGE` at a shared store such as Redis.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## License

MIT License
