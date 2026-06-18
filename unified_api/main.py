"""Single-port FastAPI entrypoint for SKIPA AI server APIs."""

from __future__ import annotations

import copy
import importlib
import sys
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from prometheus_fastapi_instrumentator import Instrumentator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVAL_SRC = PROJECT_ROOT / "eval_logic" / "src"

for path in (PROJECT_ROOT, EVAL_SRC):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)


def _import_app(module_name: str) -> FastAPI:
    module = importlib.import_module(module_name)
    app = getattr(module, "app", None)
    if not isinstance(app, FastAPI):
        raise RuntimeError(f"{module_name}.app is not a FastAPI app")
    return app


chatbot_app = _import_app("chatbot.app.main")
eval_logic_app = _import_app("apps.api.main")
pre_application_app = _import_app("pre_application_valuation.api")

DIRECT_API_APPS: list[tuple[str, FastAPI]] = [
    ("eval_logic", eval_logic_app),
    ("pre_application", pre_application_app),
]

OPENAPI_APPS: list[tuple[str, str, FastAPI]] = [
    ("", "eval_logic", eval_logic_app),
    ("", "pre_application", pre_application_app),
    ("", "chatbot", chatbot_app),
]

LIFESPAN_APPS: list[tuple[str, FastAPI]] = [
    ("eval_logic", eval_logic_app),
    ("pre_application", pre_application_app),
    ("chatbot", chatbot_app),
]


@asynccontextmanager
async def lifespan(application: FastAPI):
    async with AsyncExitStack() as stack:
        for _, sub_app in LIFESPAN_APPS:
            lifespan_context = getattr(sub_app.router, "lifespan_context", None)
            if lifespan_context is not None:
                await stack.enter_async_context(lifespan_context(sub_app))
        yield


app = FastAPI(
    title="SKIPA AI Server Unified API",
    description=(
        "SKIPA AI Server의 chatbot, eval_logic, pre-application valuation, "
        "portfolio insights API를 한 포트에서 노출합니다."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/", tags=["system"], summary="통합 API 루트")
def root() -> dict[str, Any]:
    return {
        "status": "ok",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "apps": {
            "chatbot": "/api/v1",
            "eval_logic": "/api/v1",
            "pre_application": "/api/v1",
            "ai_insights": "/api/v1/portfolio/insights",
        },
    }


@app.get("/health", tags=["system"], summary="통합 API 헬스체크")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "apps": [name for name, _ in LIFESPAN_APPS],
    }


for _, sub_app in DIRECT_API_APPS:
    app.include_router(sub_app.router, include_in_schema=False)

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

app.mount("/", chatbot_app, name="chatbot")


def _prefixed_path(prefix: str, path: str) -> str:
    if not prefix:
        return path
    if path == "/":
        return prefix
    return f"{prefix}{path}"


def _replace_refs(value: Any, ref_map: dict[str, str]) -> Any:
    if isinstance(value, dict):
        replaced = {}
        for key, item in value.items():
            if key == "$ref" and isinstance(item, str):
                replaced[key] = ref_map.get(item, item)
            else:
                replaced[key] = _replace_refs(item, ref_map)
        return replaced
    if isinstance(value, list):
        return [_replace_refs(item, ref_map) for item in value]
    return value


def _merge_components(
    target: dict[str, Any],
    source: dict[str, Any],
    *,
    namespace: str,
) -> tuple[dict[str, Any], dict[str, str]]:
    ref_map: dict[str, str] = {}
    source_components = source.get("components") if isinstance(source.get("components"), dict) else {}
    for group, entries in source_components.items():
        if not isinstance(entries, dict):
            continue
        target_group = target.setdefault("components", {}).setdefault(group, {})
        for name, schema in entries.items():
            new_name = f"{namespace}_{name}"
            ref_map[f"#/components/{group}/{name}"] = f"#/components/{group}/{new_name}"
            target_group[new_name] = schema
    return target, ref_map


def _tag_with_namespace(operation: dict[str, Any], namespace: str) -> None:
    tags = operation.get("tags")
    if not isinstance(tags, list) or not tags:
        operation["tags"] = [namespace]
        return
    operation["tags"] = [f"{namespace}:{tag}" for tag in tags]


def _merged_openapi() -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema.setdefault("paths", {})
    schema.setdefault("components", {})

    hidden_paths = {"/", "/health"}
    for prefix, namespace, sub_app in OPENAPI_APPS:
        sub_schema = copy.deepcopy(sub_app.openapi())
        schema, ref_map = _merge_components(schema, sub_schema, namespace=namespace)
        for path, methods in sub_schema.get("paths", {}).items():
            if path in hidden_paths:
                continue
            prefixed = _prefixed_path(prefix, path)
            rendered_methods = _replace_refs(methods, ref_map)
            if isinstance(rendered_methods, dict):
                for operation in rendered_methods.values():
                    if isinstance(operation, dict):
                        _tag_with_namespace(operation, namespace)
            schema["paths"][prefixed] = rendered_methods

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = _merged_openapi
