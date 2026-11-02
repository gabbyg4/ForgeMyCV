# ForgeMyCV

**ForgeMyCV** is a small Flask web app that turns your details into a polished, ATS-friendly CV and, optionally, a matching cover letter using OpenAI.

## Features

- Structured form: contact details, target role, experience, education, skills and extras
- Optional job description to tailor your documents to a specific advert
- Optional cover letter: add the company, hiring manager and why you want the role
- Generates a clean, formatted CV (and cover letter) without making up any facts
- CV and cover letter are generated in parallel and shown in tabs
- Download either as a PDF (via your browser's print dialog) or copy as Markdown
- Validates input and shows friendly errors without losing what you typed

## Setup

```bash
git clone https://github.com/gabbyg4/ForgeMyCV.git
cd ForgeMyCV
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # then add your OpenAI API key
```

`.env` settings:

| Variable         | Required | Description                                   |
|------------------|----------|-----------------------------------------------|
| `OPENAI_API_KEY` | Yes      | Your OpenAI API key                           |
| `OPENAI_MODEL`   | No       | Model to use (default `gpt-4o-mini`)          |
| `FLASK_DEBUG`    | No       | Set to `1` to enable debug mode locally       |

## Run

```bash
python app.py
```

Visit `http://localhost:5000` in your browser.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## License

MIT License
