import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any


TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"
DEFAULT_THEME = "素白风"

_THEME_PATTERN = re.compile(r"[\w-]+")


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
            "size": path.stat().st_size,
            "status": "published" if file_theme == DEFAULT_THEME else str(data.get("status") or "published"),
        })
    return items


@lru_cache
def load_templates() -> dict[str, dict[str, Any]]:
    templates: dict[str, dict[str, Any]] = {}
    for meta in list_templates():
        if meta.get("status") != "published":
            continue
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


def get_template(theme: str | None, templates: dict[str, Any] | None = None) -> dict[str, Any] | None:
    templates = load_templates() if templates is None else templates
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


# ===================================================================
# 模板 CRUD — 供管理后台增删替换下载（theme 即文件名去 .json 后缀）
# ===================================================================


def _clear_cache() -> None:
    list_templates.cache_clear()
    load_templates.cache_clear()


def _sanitize_theme(name: str | None) -> str:
    theme = unicodedata.normalize("NFKC", (name or "")).strip()
    if not theme:
        raise ValueError("模板名称不能为空")
    if len(theme) > 50 or not _THEME_PATTERN.fullmatch(theme):
        raise ValueError("模板名称仅支持中文、字母、数字、下划线和连字符，长度不超过 50")
    return theme


def _require_template_file(theme: str | None) -> Path:
    try:
        clean = _sanitize_theme(theme)
    except ValueError as exc:
        raise ValueError(f"非法的模板 ID：{exc}") from exc
    path = TEMPLATE_DIR / f"{clean}.json"
    # 防路径穿越：解析后必须仍在模板目录内
    if path.resolve().parent != TEMPLATE_DIR.resolve():
        raise ValueError("非法的模板 ID")
    if not path.exists():
        raise ValueError(f"模板「{clean}」不存在")
    return path


def _parse_template_data(template_data: str | None) -> dict[str, Any]:
    if template_data is None or not str(template_data).strip():
        raise ValueError("模板内容不能为空")
    try:
        data = json.loads(str(template_data))
    except Exception as exc:
        raise ValueError(f"模板内容不是有效的 JSON：{exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("模板 JSON 顶层必须是对象（{...}）")
    if not str(data.get("html_template") or "").strip():
        raise ValueError("模板 JSON 缺少 html_template 字段，无法用于 PPT 生成")
    return data


def _write_template_file(path: Path, data: dict[str, Any], description: str | None) -> None:
    data["template_name"] = path.stem
    if description is not None and str(description).strip():
        data["description"] = str(description).strip()
    data["is_default"] = path.stem == DEFAULT_THEME
    data.pop("export_info", None)
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    _clear_cache()


def create_template(name: str, template_data: str, description: str | None = None) -> dict[str, Any]:
    theme = _sanitize_theme(name)
    data = _parse_template_data(template_data)
    path = TEMPLATE_DIR / f"{theme}.json"
    if path.exists():
        raise ValueError(f"模板「{theme}」已存在，请更换名称")
    _write_template_file(path, data, description)
    return {"theme": theme, "filename": path.name}


def replace_template(theme: str, template_data: str, description: str | None = None) -> dict[str, Any]:
    path = _require_template_file(theme)
    if path.stem == DEFAULT_THEME:
        raise ValueError("默认模板不可替换，请新建模板后使用")
    data = _parse_template_data(template_data)
    _write_template_file(path, data, description)
    return {"theme": path.stem, "filename": path.name}


def delete_template(theme: str) -> dict[str, Any]:
    path = _require_template_file(theme)
    if path.stem == DEFAULT_THEME:
        raise ValueError("默认模板不可删除")
    path.unlink()
    _clear_cache()
    return {"theme": path.stem, "filename": path.name}


def set_template_status(theme: str, status: str) -> dict[str, Any]:
    if status not in {"published", "unpublished"}:
        raise ValueError("模板状态必须为 published 或 unpublished")
    path = _require_template_file(theme)
    if path.stem == DEFAULT_THEME and status != "published":
        raise ValueError("默认模板不可停用")
    data = _load_json(path)
    if not data:
        raise ValueError("模板文件无效")
    data["status"] = status
    _write_template_file(path, data, None)
    return {"theme": path.stem, "status": status}


def get_template_file(theme: str) -> Path:
    return _require_template_file(theme)

