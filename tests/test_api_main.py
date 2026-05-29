from fastapi import FastAPI

from voiceagents.api.main import app


def test_api_main_exports_fastapi_app() -> None:
    assert isinstance(app, FastAPI)

