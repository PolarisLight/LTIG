#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


AUTO_BLOCK_START = "<!-- AUTO-FAMILY-LINKS:START -->"
AUTO_BLOCK_END = "<!-- AUTO-FAMILY-LINKS:END -->"
SYSTEM_TAGS = {
    "paper-note",
    "triage-note",
    "index",
    "pending",
    "excluded",
    "audit",
    "bases",
    "template-cleanup",
}


@dataclass
class NoteInfo:
    path: Path
    rel_path: str
    title: str
    year: int | None
    tags: list[str]
    method_tags: list[str]
    task_tags: list[str]
    family_tags: list[str]
    subtype: str
    category: str


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh end-of-note family links for paper notes in a research KB vault."
    )
    parser.add_argument("--vault", required=True, help="Obsidian vault root.")
    parser.add_argument("--prefix", help="KB prefix tag, for example ltvr.")
    parser.add_argument("--notes-folder", help="Optional canonical notes folder name.")
    parser.add_argument("--triage-folder", help="Optional triage notes folder name.")
    parser.add_argument("--max-links", type=int, default=8, help="Maximum notes per related section.")
    parser.add_argument(
        "--include-triage",
        action="store_true",
        help="Also refresh family blocks for triage notes.",
    )
    return parser.parse_args(argv)


def clean_text(text: str | None) -> str:
    return (text or "").strip()


def normalize_text(text: str | None) -> str:
    value = clean_text(text).lower()
    value = re.sub(r"[^\w\s\u4e00-\u9fff-]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def load_kb_config(vault: Path, prefix: str | None) -> dict[str, object]:
    if not prefix:
        return {}
    path = vault / "assets" / "paper_search" / "configs" / f"{prefix}-kb-config.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def resolve_note_folders(vault: Path, prefix: str | None, notes_folder_arg: str | None, triage_folder_arg: str | None) -> tuple[str, str]:
    config = load_kb_config(vault, prefix)
    notes_folder = clean_text(notes_folder_arg) or clean_text(str(config.get("notes_folder", "")))
    triage_folder = clean_text(triage_folder_arg) or clean_text(str(config.get("triage_folder", "")))

    if not notes_folder and prefix:
        candidates = [
            child.name
            for child in vault.iterdir()
            if child.is_dir()
            and child.name not in {"assets", ".obsidian"}
            and child.name.startswith(f"{prefix}-")
            and not child.name.endswith("-待处理")
        ]
        if len(candidates) == 1:
            notes_folder = candidates[0]

    if not triage_folder and notes_folder:
        guessed = f"{notes_folder}-待处理"
        if (vault / guessed).exists():
            triage_folder = guessed

    return notes_folder, triage_folder


def parse_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return "", text
    return parts[0][4:], parts[1]


def extract_tags(frontmatter: str) -> list[str]:
    tags: list[str] = []
    in_tags = False
    for line in frontmatter.splitlines():
        if line.strip() == "tags:":
            in_tags = True
            continue
        if in_tags:
            if line.startswith("  - "):
                tags.append(line[4:].strip())
            elif line.startswith(" ") or not line.strip():
                continue
            else:
                break
    return tags


def extract_scalar(frontmatter: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", frontmatter, flags=re.MULTILINE)
    if not match:
        return ""
    return match.group(1).strip().strip("\"'")


def extract_heading(body: str) -> str:
    match = re.search(r"^#\s+(.+)$", body, flags=re.MULTILINE)
    return clean_text(match.group(1)) if match else ""


def parse_year(raw: str) -> int | None:
    raw = clean_text(raw)
    if raw.isdigit():
        return int(raw)
    return None


def family_tags_from(tags: list[str]) -> list[str]:
    results: list[str] = []
    for tag in tags:
        if tag in SYSTEM_TAGS:
            continue
        if tag.startswith(("method-", "task-", "category-")):
            continue
        if re.fullmatch(r"\d{4}", tag):
            continue
        results.append(tag)
    return results


def should_include_note(
    note: NoteInfo,
    prefix: str | None,
    notes_folder: str,
    triage_folder: str,
    include_triage: bool,
) -> bool:
    if "paper-note" not in note.tags:
        return False
    if prefix:
        in_notes_folder = bool(notes_folder) and note.rel_path.startswith(f"{notes_folder}/")
        in_triage_folder = bool(triage_folder) and note.rel_path.startswith(f"{triage_folder}/")
        if notes_folder or triage_folder:
            if not in_notes_folder and not in_triage_folder:
                return False
        elif prefix not in note.tags:
            return False
    if not include_triage and "triage-note" in note.tags:
        return False
    return True


def load_notes(
    vault: Path,
    prefix: str | None,
    notes_folder: str,
    triage_folder: str,
    include_triage: bool,
) -> list[NoteInfo]:
    notes: list[NoteInfo] = []
    for path in vault.rglob("*.md"):
        parts_lower = {part.lower() for part in path.parts}
        if ".obsidian" in parts_lower or "assets" in parts_lower:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        frontmatter, body = parse_frontmatter(text)
        tags = extract_tags(frontmatter)
        note = NoteInfo(
            path=path,
            rel_path=path.relative_to(vault).as_posix(),
            title=extract_scalar(frontmatter, "title") or extract_heading(body) or path.stem,
            year=parse_year(extract_scalar(frontmatter, "year")),
            tags=tags,
            method_tags=[tag for tag in tags if tag.startswith("method-")],
            task_tags=[tag for tag in tags if tag.startswith("task-")],
            family_tags=family_tags_from(tags),
            subtype=extract_scalar(frontmatter, "subtype"),
            category=extract_scalar(frontmatter, "category"),
        )
        if should_include_note(note, prefix, notes_folder, triage_folder, include_triage):
            notes.append(note)
    return notes


def link_to(note: NoteInfo) -> str:
    return f"[[{note.rel_path}|{note.title}]]"


def format_overlap_list(values: list[str], prefix: str) -> str:
    display = [value.removeprefix(prefix) for value in values]
    return ", ".join(display)


def sort_key(item: tuple[NoteInfo, list[str]]) -> tuple[int, int, str]:
    note, overlaps = item
    return (-len(overlaps), -(note.year or 0), note.title.lower())


def build_related_block(note: NoteInfo, pool: list[NoteInfo], max_links: int) -> str:
    method_items: list[tuple[NoteInfo, list[str]]] = []
    task_items: list[tuple[NoteInfo, list[str]]] = []
    subtype_items: list[tuple[NoteInfo, list[str]]] = []

    used: set[str] = set()
    for other in pool:
        if other.rel_path == note.rel_path:
            continue
        shared_methods = sorted(set(note.method_tags) & set(other.method_tags))
        shared_tasks = sorted(set(note.task_tags) & set(other.task_tags))
        if shared_methods:
            method_items.append((other, shared_methods))
            continue
        if shared_tasks:
            task_items.append((other, shared_tasks))
            continue
        if note.subtype and other.subtype and note.subtype == other.subtype:
            subtype_items.append((other, [note.subtype]))

    lines = ["## 库内同家族笔记", ""]

    def emit_section(title: str, items: list[tuple[NoteInfo, list[str]]], label_prefix: str) -> None:
        nonlocal lines, used
        lines.append(f"### {title}")
        lines.append("")
        emitted = 0
        for other, overlaps in sorted(items, key=sort_key):
            if other.rel_path in used:
                continue
            used.add(other.rel_path)
            extra = format_overlap_list(overlaps, label_prefix)
            year_part = f" ({other.year})" if other.year else ""
            if extra:
                lines.append(f"- {link_to(other)}{year_part} · 共享：{extra}")
            else:
                lines.append(f"- {link_to(other)}{year_part}")
            emitted += 1
            if emitted >= max_links:
                break
        if emitted == 0:
            if title == "同方法家族":
                lines.append("- 暂无可自动关联的条目；补齐 `method-*` 标签后可刷新。")
            elif title == "同任务家族":
                lines.append("- 暂无可自动关联的条目；补齐 `task-*` 标签后可刷新。")
            else:
                lines.append("- 暂无可自动关联的同设定条目。")
        lines.append("")

    emit_section("同方法家族", method_items, "method-")
    emit_section("同任务家族", task_items, "task-")
    emit_section("同子任务设定", subtype_items, "")

    managed = "\n".join(lines).rstrip()
    return f"{AUTO_BLOCK_START}\n{managed}\n{AUTO_BLOCK_END}"


def upsert_block(content: str, block: str) -> str:
    if AUTO_BLOCK_START in content and AUTO_BLOCK_END in content:
        return re.sub(
            re.escape(AUTO_BLOCK_START) + r".*?" + re.escape(AUTO_BLOCK_END),
            block,
            content,
            flags=re.DOTALL,
        )
    return content.rstrip() + "\n\n" + block + "\n"


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    vault = Path(args.vault).expanduser().resolve()
    notes_folder, triage_folder = resolve_note_folders(vault, args.prefix, args.notes_folder, args.triage_folder)
    notes = load_notes(vault, args.prefix, notes_folder, triage_folder, args.include_triage)

    updated = 0
    for note in notes:
        content = note.path.read_text(encoding="utf-8", errors="ignore")
        block = build_related_block(note, notes, args.max_links)
        new_content = upsert_block(content, block)
        if new_content != content:
            note.path.write_text(new_content, encoding="utf-8")
            updated += 1

    print(f"Vault: {vault}")
    print(f"Prefix: {args.prefix or 'ALL'}")
    print(f"NotesScanned={len(notes)}")
    print(f"NotesUpdated={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
