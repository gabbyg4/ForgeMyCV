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


def test_form_renders(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b'name="full_name"' in resp.data
    assert b"cover letter" not in resp.data.lower()


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
