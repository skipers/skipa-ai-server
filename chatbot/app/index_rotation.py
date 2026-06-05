"""Blue/green local index rotation helpers.

The chatbot stores lightweight JSONL vectorstores on disk. Reindexing directly
over the active files can leave the API without a usable index while a refresh
is running, so every index root can keep two slots:

  vectorstore/
    active_slot.json
    blue/documents.jsonl
    blue/manifest.json
    green/documents.jsonl
    green/manifest.json

Readers use the active slot. Writers build the inactive slot first and only
switch active_slot.json after all files are written.
"""

from __future__ import annotations

from datetime import datetime
import json
import shutil
from pathlib import Path
from typing import Any


SLOTS = ("blue", "green")
ACTIVE_SLOT_FILE = "active_slot.json"
DOCUMENTS_FILE = "documents.jsonl"
MANIFEST_FILE = "manifest.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _slot_has_index(root: Path, slot: str) -> bool:
    slot_dir = root / slot
    return (slot_dir / DOCUMENTS_FILE).exists() and (slot_dir / MANIFEST_FILE).exists()


def active_slot_path(root: Path) -> Path:
    return root / ACTIVE_SLOT_FILE


def get_active_slot(root: Path) -> str | None:
    pointer = _read_json(active_slot_path(root))
    slot = str(pointer.get("active_slot") or "")
    if slot in SLOTS and _slot_has_index(root, slot):
        return slot

    candidates: list[tuple[float, str]] = []
    for candidate in SLOTS:
        manifest_path = root / candidate / MANIFEST_FILE
        if _slot_has_index(root, candidate):
            candidates.append((manifest_path.stat().st_mtime, candidate))
    if candidates:
        return sorted(candidates)[-1][1]
    return None


def get_standby_slot(root: Path) -> str:
    active = get_active_slot(root)
    if active == "blue":
        return "green"
    return "blue"


def active_index_dir(root: Path) -> Path:
    slot = get_active_slot(root)
    return root / slot if slot else root


def active_documents_path(root: Path) -> Path:
    return active_index_dir(root) / DOCUMENTS_FILE


def active_manifest_path(root: Path) -> Path:
    return active_index_dir(root) / MANIFEST_FILE


def rotation_status(root: Path) -> dict[str, Any]:
    active = get_active_slot(root)
    slots = []
    for slot in SLOTS:
        slot_dir = root / slot
        manifest_path = slot_dir / MANIFEST_FILE
        docs_path = slot_dir / DOCUMENTS_FILE
        manifest = _read_json(manifest_path)
        slots.append(
            {
                "slot": slot,
                "is_active": slot == active,
                "exists": docs_path.exists() and manifest_path.exists(),
                "document_count": manifest.get("document_count"),
                "refreshed_at": manifest.get("refreshed_at"),
                "manifest_path": str(manifest_path),
                "documents_path": str(docs_path),
            }
        )
    return {
        "strategy": "blue_green",
        "active_slot": active,
        "standby_slot": get_standby_slot(root),
        "pointer_path": str(active_slot_path(root)),
        "active_manifest_path": str(active_manifest_path(root)),
        "active_documents_path": str(active_documents_path(root)),
        "legacy_manifest_path": str(root / MANIFEST_FILE),
        "legacy_documents_path": str(root / DOCUMENTS_FILE),
        "slots": slots,
    }


def write_rotating_index(
    root: Path,
    docs: list[dict[str, Any]],
    manifest: dict[str, Any],
    *,
    mirror_legacy: bool = True,
) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    previous_active = get_active_slot(root)
    target_slot = get_standby_slot(root)
    target_dir = root / target_slot
    target_dir.mkdir(parents=True, exist_ok=True)

    docs_path = target_dir / DOCUMENTS_FILE
    manifest_path = target_dir / MANIFEST_FILE
    tmp_docs = target_dir / f"{DOCUMENTS_FILE}.tmp"
    tmp_manifest = target_dir / f"{MANIFEST_FILE}.tmp"
    tmp_pointer = root / f"{ACTIVE_SLOT_FILE}.tmp"

    final_manifest = dict(manifest)
    final_manifest.update(
        {
            "documents_path": str(docs_path),
            "manifest_path": str(manifest_path),
            "active_slot": target_slot,
            "previous_active_slot": previous_active,
            "rotation": {
                "strategy": "blue_green",
                "active_slot": target_slot,
                "previous_active_slot": previous_active,
                "activated_at": _now(),
                "standby_slot": "green" if target_slot == "blue" else "blue",
            },
        }
    )

    with tmp_docs.open("w", encoding="utf-8") as file:
        for doc in docs:
            file.write(json.dumps(doc, ensure_ascii=False, sort_keys=True) + "\n")
    tmp_manifest.write_text(json.dumps(final_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_docs.replace(docs_path)
    tmp_manifest.replace(manifest_path)

    pointer = {
        "active_slot": target_slot,
        "previous_active_slot": previous_active,
        "activated_at": _now(),
        "active_manifest_path": str(manifest_path),
        "active_documents_path": str(docs_path),
    }
    tmp_pointer.write_text(json.dumps(pointer, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_pointer.replace(active_slot_path(root))

    if mirror_legacy:
        legacy_docs_tmp = root / f"{DOCUMENTS_FILE}.tmp"
        legacy_manifest_tmp = root / f"{MANIFEST_FILE}.tmp"
        shutil.copyfile(docs_path, legacy_docs_tmp)
        shutil.copyfile(manifest_path, legacy_manifest_tmp)
        legacy_docs_tmp.replace(root / DOCUMENTS_FILE)
        legacy_manifest_tmp.replace(root / MANIFEST_FILE)

    return {
        "active_slot": target_slot,
        "previous_active_slot": previous_active,
        "manifest_path": str(manifest_path),
        "documents_path": str(docs_path),
        "legacy_manifest_path": str(root / MANIFEST_FILE),
        "legacy_documents_path": str(root / DOCUMENTS_FILE),
        "rotation": rotation_status(root),
    }
