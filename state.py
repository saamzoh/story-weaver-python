"""
state.py — Story session helpers

Streamlit reruns the whole script on every interaction, so all persistent
data lives in st.session_state. This module provides typed helpers for
reading and mutating that state — no direct st.session_state access in app.py.
"""

from __future__ import annotations
import copy
import json
import re
from dataclasses import dataclass, field
from typing import Literal

import streamlit as st

SegmentType = Literal["ai", "user", "system"]


@dataclass
class Segment:
    type: SegmentType
    text: str


def init_session():
    """Initialise session_state keys if they don't exist yet."""
    defaults = {
        "story_title":   "",
        "story_genre":   "",
        "story_hook":    "",
        "segments":      [],   # list[Segment]
        "history":       [],   # list[list[Segment]] — undo stack
        "characters":    {},   # {name: description}
        "rules":         [],   # list[str]
        "screen":        "setup",   # "setup" | "story"
        "active_choices": None,     # list[str] | None
        "error":         None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def start_story(title: str, genre: str, hook: str):
    st.session_state.story_title  = title or "Untitled Story"
    st.session_state.story_genre  = genre
    st.session_state.story_hook   = hook
    st.session_state.segments     = []
    st.session_state.history      = []
    st.session_state.characters   = {}
    st.session_state.rules        = []
    st.session_state.active_choices = None
    st.session_state.error        = None
    st.session_state.screen       = "story"


def push_segment(seg_type: SegmentType, text: str):
    st.session_state.segments.append(Segment(type=seg_type, text=text))


def snapshot():
    """Deep-copy current segments onto the undo stack (max 20 deep)."""
    st.session_state.history.append(copy.deepcopy(st.session_state.segments))
    if len(st.session_state.history) > 20:
        st.session_state.history.pop(0)


def undo() -> bool:
    """Restore the most recent snapshot. Returns False if nothing to undo."""
    if not st.session_state.history:
        return False
    st.session_state.segments = st.session_state.history.pop()
    st.session_state.active_choices = None
    return True


def get_story_text() -> str:
    """Full narrative text — excludes system annotations."""
    return "\n\n".join(
        s.text for s in st.session_state.segments if s.type != "system"
    )


def get_word_count() -> int:
    text = get_story_text().strip()
    return len(text.split()) if text else 0


def get_last_ai_segment() -> Segment | None:
    for s in reversed(st.session_state.segments):
        if s.type == "ai":
            return s
    return None


def update_characters_and_rules(raw_json: str):
    """
    Parse JSON from the extraction prompt and update session state.
    Swallows all errors — this is a best-effort sidebar enhancement.
    """
    try:
        match = re.search(r"\{.*\}", raw_json, re.DOTALL)
        if not match:
            return
        data = json.loads(match.group())
        for char in data.get("characters", []):
            name = char.get("name", "").strip()
            desc = char.get("description", "").strip()
            if name and name not in st.session_state.characters:
                st.session_state.characters[name] = desc
        rules = data.get("rules", [])
        if rules:
            st.session_state.rules = [r for r in rules if r]
    except Exception:
        pass  # silent — never crash on extraction failure


def export_markdown() -> str:
    """Serialise the story to a clean Markdown string for download."""
    lines = [
        f"# {st.session_state.story_title}",
        "",
        f"**Genre:** {st.session_state.story_genre}",
        "",
        "---",
        "",
    ]
    for seg in st.session_state.segments:
        if seg.type == "system":
            continue
        if seg.type == "user":
            lines.append(f"*[Author]* {seg.text}")
        else:
            lines.append(seg.text)
        lines.append("")
    return "\n".join(lines)


# ── Session persistence ───────────────────────────────────────────────────────

import json as _json
import time as _time
from pathlib import Path as _Path

_SAVE_DIR  = _Path(".story_saves")
_SAVE_FILE = _SAVE_DIR / "session.json"


def save_session() -> bool:
    """
    Persist the current story session to disk as JSON.
    Returns True on success, False on failure (e.g. permission error).
    """
    try:
        _SAVE_DIR.mkdir(exist_ok=True)
        payload = {
            "title":      st.session_state.story_title,
            "genre":      st.session_state.story_genre,
            "hook":       st.session_state.story_hook,
            "segments":   [{"type": s.type, "text": s.text}
                           for s in st.session_state.segments],
            "characters": st.session_state.characters,
            "rules":      st.session_state.rules,
            "saved_at":   _time.time(),
        }
        _SAVE_FILE.write_text(_json.dumps(payload, ensure_ascii=False, indent=2))
        return True
    except Exception as e:
        print(f"Story Weaver: could not save session — {e}")
        return False


def load_session() -> dict | None:
    """Load the last saved session. Returns None if no save file exists."""
    try:
        if not _SAVE_FILE.exists():
            return None
        return _json.loads(_SAVE_FILE.read_text())
    except Exception:
        return None


def restore_session(payload: dict):
    """Populate session_state from a saved payload dict."""
    st.session_state.story_title  = payload.get("title", "Untitled Story")
    st.session_state.story_genre  = payload.get("genre", "")
    st.session_state.story_hook   = payload.get("hook", "")
    st.session_state.characters   = payload.get("characters", {})
    st.session_state.rules        = payload.get("rules", [])
    st.session_state.history      = []
    st.session_state.active_choices = None
    st.session_state.error        = None
    st.session_state.screen       = "story"
    st.session_state.segments = [
        Segment(type=s["type"], text=s["text"])
        for s in payload.get("segments", [])
    ]


def clear_saved_session():
    """Delete the save file (called on New Story)."""
    try:
        if _SAVE_FILE.exists():
            _SAVE_FILE.unlink()
    except Exception:
        pass


def saved_ago_label(saved_at: float) -> str:
    diff = int(_time.time() - saved_at)
    if diff < 60:
        return "just now"
    if diff < 3600:
        return f"{diff // 60}m ago"
    return f"{diff // 3600}h ago"
