from __future__ import annotations

import os
from functools import lru_cache

from fastapi import FastAPI

from src.api.models import AskRequest, AskResponse, HealthResponse, SearchRequest, SearchResponse
from src.app.service import QAService
from src.config.settings import ensure_directories, load_settings


@lru_cache(maxsize=1)
def get_service() -> QAService:
    config_path = os.getenv("APP_CONFIG_PATH", "config/default.yaml")
    settings = load_settings(config_path)
    ensure_directories(settings)
    return QAService(settings)


def create_app() -> FastAPI:
    app = FastAPI(title="Vietnamese Internal Docs RAG Assistant", version="0.1.0")

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        status = get_service().health()
        return HealthResponse(**status.__dict__)

    @app.post("/search", response_model=SearchResponse)
    def search(req: SearchRequest) -> SearchResponse:
        payload = get_service().search(
            query=req.query,
            top_k=req.top_k,
            department_filter=req.department_filter,
            access_level=req.access_level,
            debug=req.debug,
        )
        return SearchResponse(**payload)

    @app.post("/ask", response_model=AskResponse)
    def ask(req: AskRequest) -> AskResponse:
        answer = get_service().ask(
            question=req.question,
            top_k=req.top_k,
            department_filter=req.department_filter,
            access_level=req.access_level,
            debug=req.debug,
        )
        return AskResponse(**answer.to_dict())

    return app


app = create_app()
