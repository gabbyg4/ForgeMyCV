from types import SimpleNamespace

import pytest
from openai import APIConnectionError

import app as cv_app

VALID = {
    "full_name": "Ada Lovelace",
    "email": "ada@example.com",
    "target_role": "Software Engineer",
    "experience": "Analyst, Babbage & Co, 1842-1843. Wrote the first algorithm.",
    "skills": "Mathematics, Algorithms",
}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    cv_app.app.config["TESTING"] = True
    cv_app.limiter.reset()
    return cv_app.app.test_client()


def fake_openai(content=None, error=None, calls=None):
    def create(**kwargs):
        if calls is not None:
            calls.append(kwargs)
        if error:
            raise error
        message = SimpleNamespace(content=content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    completions = SimpleNamespace(create=create)
    return lambda: SimpleNamespace(chat=SimpleNamespace(completions=completions))


def test_landing_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Build my CV" in resp.data
    assert b'href="/build"' in resp.data
    assert resp.headers["X-Frame-Options"] == "DENY"


def test_form_renders(client):
    resp = client.get("/build")
    assert resp.status_code == 200
    assert b'name="full_name"' in resp.data
    assert b'name="cover_letter"' in resp.data


def test_missing_required_fields_rerenders_form(client):
    resp = client.post("/generate", data={"full_name": "Ada"})
    assert resp.status_code == 400
    assert b"Work experience is required." in resp.data
    assert b'value="Ada"' in resp.data  # input is preserved


def test_too_long_field_rejected(client):
    resp = client.post("/generate", data={**VALID, "skills": "x" * 1001})
    assert resp.status_code == 400
    assert b"Skills must be at most 1000 characters." in resp.data


def test_missing_api_key(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY")
    resp = client.post("/generate", data=VALID)
    assert resp.status_code == 500
    assert b"OPENAI_API_KEY" in resp.data


def test_generates_cv(client, monkeypatch):
    calls = []
    md = "```markdown\n# Ada Lovelace\n\n## Skills\n\n- Mathematics\n```"
    monkeypatch.setattr(cv_app, "get_client", fake_openai(md, calls=calls))
    resp = client.post("/generate", data=VALID)
    assert resp.status_code == 200
    assert b"<h1>Ada Lovelace</h1>" in resp.data
    assert b"<li>Mathematics</li>" in resp.data
    assert b"```" not in resp.data
    prompt = calls[0]["messages"][1]["content"]
    assert "Ada Lovelace" in prompt and "Job description" not in prompt
    assert len(calls) == 1  # no cover letter unless requested
    assert b'role="tablist"' not in resp.data


def test_model_html_is_escaped(client, monkeypatch):
    md = "# Ada\n\n<script>alert(1)</script>"
    monkeypatch.setattr(cv_app, "get_client", fake_openai(md))
    resp = client.post("/generate", data=VALID)
    assert b"<script>alert(1)</script>" not in resp.data


def test_api_error_is_handled(client, monkeypatch):
    err = APIConnectionError(request=None)
    monkeypatch.setattr(cv_app, "get_client", fake_openai(error=err))
    resp = client.post("/generate", data=VALID)
    assert resp.status_code == 502
    assert b"try again" in resp.data
    assert b'value="Ada Lovelace"' in resp.data


def test_cover_letter_requires_company(client):
    resp = client.post("/generate", data={**VALID, "cover_letter": "on"})
    assert resp.status_code == 400
    assert b"Company name is required for a cover letter." in resp.data
    assert b'id="cover_letter" checked' in resp.data  # choice is preserved


def test_generates_cv_and_cover_letter(client, monkeypatch):
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        system = kwargs["messages"][0]["content"]
        text = "Dear Hiring Manager," if "cover letter" in system else "# CV body"
        message = SimpleNamespace(content=text)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(cv_app, "get_client", lambda: fake)
    form = {**VALID, "cover_letter": "on", "company": "Analytical Engines Ltd",
            "motivation": "I love engines."}
    resp = client.post("/generate", data=form)

    assert resp.status_code == 200
    assert len(calls) == 2
    assert b"<h1>CV body</h1>" in resp.data
    assert b"Dear Hiring Manager," in resp.data
    assert b'role="tablist"' in resp.data

    prompts = {c["messages"][0]["content"]: c["messages"][1]["content"] for c in calls}
    cv_prompt = prompts[cv_app.CV_PROMPT]
    letter_prompt = prompts[cv_app.COVER_LETTER_PROMPT]
    assert "Analytical Engines Ltd" in letter_prompt and "I love engines." in letter_prompt
    assert "Analytical Engines Ltd" not in cv_prompt and "I love engines." not in cv_prompt


def test_crlf_line_breaks_count_once(client, monkeypatch):
    monkeypatch.setattr(cv_app, "get_client", fake_openai("# CV"))
    skills = "a\r\n" * 333 + "a"  # 1000 characters once CRLF becomes LF
    resp = client.post("/generate", data={**VALID, "skills": skills})
    assert resp.status_code == 200


def test_invalid_email_rejected(client):
    resp = client.post("/generate", data={**VALID, "email": "not-an-email"})
    assert resp.status_code == 400
    assert b"Enter a valid email address." in resp.data
    assert b'aria-invalid="true"' in resp.data


def test_get_generate_redirects_to_form(client):
    resp = client.get("/generate")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/build")


def test_edit_prefills_form(client):
    resp = client.post("/edit", data={**VALID, "cover_letter": "on", "company": "Acme"})
    assert resp.status_code == 200
    assert b'value="Acme"' in resp.data
    assert b'id="cover_letter" checked' in resp.data
    assert b"is required" not in resp.data  # editing never shows validation errors


def test_result_page_carries_details_for_edit_and_regenerate(client, monkeypatch):
    monkeypatch.setattr(cv_app, "get_client", fake_openai("# CV"))
    resp = client.post("/generate", data={**VALID, "experience": "Line one\nLine two"})
    assert b'formaction="/edit"' in resp.data
    assert b'name="experience" value="Line one\nLine two"' in resp.data


def test_empty_response_is_handled(client, monkeypatch):
    monkeypatch.setattr(cv_app, "get_client", fake_openai("   "))
    resp = client.post("/generate", data=VALID)
    assert resp.status_code == 502
    assert b"came back empty" in resp.data


def test_invalid_api_key_is_reported(client, monkeypatch):
    # Built without __init__ so the test doesn't depend on the SDK's HTTP library.
    err = cv_app.AuthenticationError.__new__(cv_app.AuthenticationError)
    monkeypatch.setattr(cv_app, "get_client", fake_openai(error=err))
    resp = client.post("/generate", data=VALID)
    assert resp.status_code == 500
    assert b"API key is invalid" in resp.data


def test_rate_limit(client, monkeypatch):
    monkeypatch.setattr(cv_app, "RATE_LIMIT", "2 per hour")
    monkeypatch.setattr(cv_app, "get_client", fake_openai("# CV"))
    assert client.post("/generate", data=VALID).status_code == 200
    assert client.post("/generate", data=VALID).status_code == 200
    resp = client.post("/generate", data=VALID)
    assert resp.status_code == 429
    assert b"Please wait" in resp.data
    assert b'value="Ada Lovelace"' in resp.data


def test_oversized_request(client):
    resp = client.post("/generate", data={"experience": "x" * 300_000})
    assert resp.status_code == 413
    assert b"too much text" in resp.data


def test_404_page(client):
    resp = client.get("/nope")
    assert resp.status_code == 404
    assert b"Page not found" in resp.data
