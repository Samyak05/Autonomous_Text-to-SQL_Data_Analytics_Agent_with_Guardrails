from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parent.parent / "src" / "app.py"


def test_app_renders_without_crashing():
    at = AppTest.from_file(str(APP_PATH), default_timeout=10)
    at.run()

    assert not at.exception


def test_app_displays_project_title():
    at = AppTest.from_file(str(APP_PATH), default_timeout=10)
    at.run()

    assert not at.exception
    assert any(
        "Text-to-SQL Analytics Agent" in title.value
        for title in at.title
    )