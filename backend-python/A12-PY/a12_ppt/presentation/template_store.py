import json
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any


TEMPLATE_DIR = Path(__file__).with_name("templates")
DEFAULT_THEME = "素白风"


def _norm(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", (value or "").strip()).lower()
    return "".join(ch for ch in text if not ch.isspace() and ch not in {"_", "-", "—"})


def _load_json(path: Path) -> dict[str, Any] | None:
    for encoding in ("utf-8", "utf-8-sig", "gbk"):
        try:
            return json.loads(path.read_text(encoding=encoding))
        except UnicodeDecodeError:
            continue
        except Exception:
            return None
    return None


@lru_cache
def list_templates() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted(TEMPLATE_DIR.glob("*.json"), key=lambda p: p.stem):
        data = _load_json(path)
        if not data:
            continue
        file_theme = path.stem.strip()
        template_name = str(data.get("template_name") or file_theme).strip()
        description = str(data.get("description") or "").strip()
        tags = data.get("tags") if isinstance(data.get("tags"), list) else []
        aliases = sorted({
            file_theme,
            template_name,
            *[str(tag).strip() for tag in tags if str(tag).strip()],
        })
        items.append({
            "theme": file_theme,
            "template_name": template_name,
            "description": description,
            "aliases": aliases,
            "is_default": file_theme == DEFAULT_THEME,
            "filename": path.name,
        })
    return items


@lru_cache
def load_templates() -> dict[str, dict[str, Any]]:
    templates: dict[str, dict[str, Any]] = {}
    for meta in list_templates():
        path = TEMPLATE_DIR / str(meta["filename"])
        data = _load_json(path)
        if not data:
            continue
        data["_file_theme"] = meta["theme"]
        data["_template_meta"] = meta
        keys = set(meta["aliases"])
        keys.update(_norm(alias) for alias in meta["aliases"])
        for key in keys:
            if key:
                templates[key] = data
    return templates


def get_template(theme: str | None) -> dict[str, Any] | None:
    templates = load_templates()
    if not templates:
        return None

    requested = (theme or "").strip()
    if requested:
        for key in (requested, _norm(requested)):
            if key in templates:
                selected = dict(templates[key])
                meta = dict(selected.get("_template_meta") or {})
                selected["_selected_theme"] = meta.get("theme") or requested
                return selected

        normalized_requested = _norm(requested)
        for data in templates.values():
            meta = data.get("_template_meta") or {}
            aliases = meta.get("aliases") or []
            if any(normalized_requested and normalized_requested in _norm(alias) for alias in aliases):
                selected = dict(data)
                selected["_selected_theme"] = meta.get("theme") or requested
                return selected

        return {
            "template_name": requested,
            "html_template": "",
            "_selected_theme": requested,
            "_missing_template": True,
        }

    fallback_key = DEFAULT_THEME if DEFAULT_THEME in templates else _norm(DEFAULT_THEME)
    selected = dict(templates.get(fallback_key) or next(iter(templates.values())))
    meta = selected.get("_template_meta") or {}
    selected["_selected_theme"] = meta.get("theme") or DEFAULT_THEME
    return selected

