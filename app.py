"""ForgeMyCV - a small Flask app that turns your details into a polished CV
and, optionally, a matching cover letter."""

import logging
import os
from concurrent.futures import ThreadPoolExecutor

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
    ("job_description", "Job description", False, 6000),
    ("company", "Company name", False, 150),
    ("hiring_manager", "Hiring manager", False, 100),
    ("motivation", "Why you want this role", False, 1500),
]
LIMITS = {name: max_len for name, _, _, max_len in FIELDS}

# Fields that only matter for the cover letter.
COVER_LETTER_FIELDS = {"company", "hiring_manager", "motivation"}

_SHARED_RULES = """- Never invent employers, dates, qualifications, metrics or contact details.
- If a job description is given, emphasise the most relevant experience and \
skills, without adding facts.
- Write in the same language as the user's details.
- Output only the requested document in Markdown. No preamble, notes, \
code fences or [placeholders]."""

CV_PROMPT = f"""You are an expert CV writer. Write a single professional, \
ATS-friendly CV in Markdown using only the facts supplied by the user.

Rules:
- Start with the candidate's name as a level-1 heading, followed by one line \
of contact details separated by " | ".
- Use level-2 headings for sections, in this order where content exists: \
Professional Summary, Skills, Work Experience, Education, Additional.
- Under Work Experience, use a level-3 heading per role (title, company, dates) \
and concise bullet points that start with strong action verbs.
- Omit any section or detail that was not provided.
{_SHARED_RULES}"""

COVER_LETTER_PROMPT = f"""You are an expert career writer. Write a tailored, \
one-page cover letter in Markdown using only the facts supplied by the user.

Rules:
- Start with the candidate's name as a level-1 heading, followed by one line \
of contact details separated by " | ". Do not include a date or postal addresses.
- Address the hiring manager by name if given, otherwise "Dear Hiring Manager,".
- 3-4 short paragraphs, 250-400 words: a specific opening naming the role and \
company, one or two paragraphs linking the candidate's real achievements and \
skills to the role's needs, and a confident closing with a call to action.
- Sound natural and specific; avoid clichés such as "I am writing to apply".
- End with "Yours sincerely," and the candidate's full name on the next line.
{_SHARED_RULES}"""


def get_client() -> OpenAI:
    return OpenAI()  # reads OPENAI_API_KEY from the environment


def read_form(form) -> tuple[dict, bool, list[str]]:
    want_letter = form.get("cover_letter") == "on"
    data, errors = {}, []
    for name, label, required, max_len in FIELDS:
        value = form.get(name, "").strip()
        if required and not value:
            errors.append(f"{label} is required.")
        elif len(value) > max_len:
            errors.append(f"{label} must be at most {max_len} characters.")
        data[name] = value
    if want_letter and not data["company"]:
        errors.append("Company name is required for a cover letter.")
    return data, want_letter, errors


def build_prompt(intro: str, data: dict, skip=()) -> str:
    lines = [intro, ""]
    for name, label, _, _ in FIELDS:
        if data.get(name) and name not in skip:
            lines.append(f"## {label}\n{data[name]}\n")
    return "\n".join(lines)


def complete(system_prompt: str, user_prompt: str) -> str:
    response = get_client().chat.completions.create(
        model=MODEL,
        temperature=0.4,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    content = (response.choices[0].message.content or "").strip()
    # Strip a surrounding ```markdown fence if the model adds one.
    if content.startswith("```"):
        content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return content


def generate_cv(data: dict) -> str:
    prompt = build_prompt("Create a CV from these details:", data, skip=COVER_LETTER_FIELDS)
    return complete(CV_PROMPT, prompt)


def generate_cover_letter(data: dict) -> str:
    prompt = build_prompt("Write a cover letter from these details:", data)
    return complete(COVER_LETTER_PROMPT, prompt)


def render_form(data=None, errors=(), status=200, want_letter=False):
    page = render_template(
        "form.html", limits=LIMITS, data=data or {}, errors=errors, want_letter=want_letter
    )
    return page, status


@app.get("/")
def form():
    return render_form()


@app.post("/generate")
def generate():
    data, want_letter, errors = read_form(request.form)

    def fail(message, status):
        return render_form(data, errors or [message], status, want_letter)

    if errors:
        return fail(None, 400)
    if not os.getenv("OPENAI_API_KEY"):
        return fail("The server is missing OPENAI_API_KEY. Add it to your .env file.", 500)

    jobs = {"cv": ("CV", generate_cv)}
    if want_letter:
        jobs["cover_letter"] = ("Cover letter", generate_cover_letter)

    try:
        # Generate the documents concurrently to halve the wait.
        with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
            futures = {key: pool.submit(fn, data) for key, (_, fn) in jobs.items()}
            results = {key: future.result() for key, future in futures.items()}
    except OpenAIError:
        logger.exception("Document generation failed")
        return fail("We couldn't generate your documents right now. Please try again.", 502)

    if not all(results.values()):
        return fail("The response came back empty. Please try again.", 502)

    documents = [
        {
            "id": key,
            "title": title,
            "html": Markup(_markdown.render(results[key])),
            "markdown": results[key],
        }
        for key, (title, _) in jobs.items()
    ]
    return render_template("result.html", documents=documents, full_name=data["full_name"])


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")
