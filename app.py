"""ForgeMyCV - a small Flask app that turns your details into a polished CV."""

import logging
import os

from dotenv import load_dotenv
from flask import Flask, render_template, request
from markdown_it import MarkdownIt
from markupsafe import Markup
from openai import OpenAI, OpenAIError

load_dotenv()

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024  # reject oversized form posts

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Raw HTML in the model's output is escaped rather than rendered.
_markdown = MarkdownIt("commonmark", {"html": False})

# (form name, label, required, max length)
FIELDS = [
    ("full_name", "Full name", True, 100),
    ("email", "Email", False, 200),
    ("phone", "Phone", False, 50),
    ("location", "Location", False, 100),
    ("links", "Links (LinkedIn, portfolio, GitHub)", False, 300),
    ("target_role", "Target job title", True, 150),
    ("summary", "Professional summary", False, 2000),
    ("experience", "Work experience", True, 6000),
    ("education", "Education", False, 2000),
    ("skills", "Skills", True, 1000),
    ("extras", "Certifications, languages, projects", False, 2000),
    ("job_description", "Job description to tailor to", False, 6000),
]

SYSTEM_PROMPT = """You are an expert CV writer. Write a single professional, \
ATS-friendly CV in Markdown using only the facts supplied by the user.

Rules:
- Start with the candidate's name as a level-1 heading, followed by one line \
of contact details separated by " | ".
- Use level-2 headings for sections, in this order where content exists: \
Professional Summary, Skills, Work Experience, Education, Additional.
- Under Work Experience, use a level-3 heading per role (title, company, dates) \
and concise bullet points that start with strong action verbs.
- Never invent employers, dates, qualifications, metrics or contact details. \
Omit any section or detail that was not provided.
- If a job description is given, prioritise and phrase the relevant experience \
and skills to match it, without adding facts.
- Output only the CV. No preamble, notes, placeholders or cover letter."""


LIMITS = {name: max_len for name, _, _, max_len in FIELDS}


def get_client() -> OpenAI:
    return OpenAI()  # reads OPENAI_API_KEY from the environment


def read_form(form) -> tuple[dict, list[str]]:
    data, errors = {}, []
    for name, label, required, max_len in FIELDS:
        value = form.get(name, "").strip()
        if required and not value:
            errors.append(f"{label} is required.")
        elif len(value) > max_len:
            errors.append(f"{label} must be at most {max_len} characters.")
        data[name] = value
    return data, errors


def build_prompt(data: dict) -> str:
    lines = ["Create a CV from these details:", ""]
    for name, label, _, _ in FIELDS:
        if data.get(name):
            lines.append(f"## {label}\n{data[name]}\n")
    return "\n".join(lines)


def generate_cv(data: dict) -> str:
    response = get_client().chat.completions.create(
        model=MODEL,
        temperature=0.4,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(data)},
        ],
    )
    content = (response.choices[0].message.content or "").strip()
    # Strip a surrounding ```markdown fence if the model adds one.
    if content.startswith("```"):
        content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return content


def render_form(data=None, errors=(), status=200):
    page = render_template("form.html", limits=LIMITS, data=data or {}, errors=errors)
    return page, status


@app.get("/")
def form():
    return render_form()


@app.post("/generate")
def generate():
    data, errors = read_form(request.form)
    if errors:
        return render_form(data, errors, 400)

    if not os.getenv("OPENAI_API_KEY"):
        return render_form(data, ["The server is missing OPENAI_API_KEY. Add it to your .env file."], 500)

    try:
        cv_markdown = generate_cv(data)
    except OpenAIError:
        logger.exception("CV generation failed")
        return render_form(data, ["We couldn't generate your CV right now. Please try again."], 502)

    if not cv_markdown:
        return render_form(data, ["The CV came back empty. Please try again."], 502)

    return render_template(
        "result.html",
        cv_html=Markup(_markdown.render(cv_markdown)),
        cv_markdown=cv_markdown,
        full_name=data["full_name"],
    )


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")
