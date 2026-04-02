"""
app.py — Story Weaver (Streamlit + OpenAI)

Run with:
    streamlit run app.py
"""

import random
import streamlit as st

from llm import call_llm, stream_llm
from prompts import (
    GENRES, GENRE_ICONS,
    build_system_prompt,
    build_opening_prompt,
    build_continuation_prompt,
    build_choices_prompt,
    build_choice_continuation_prompt,
    build_remix_prompt,
    build_extraction_prompt,
)
from state import (
    init_session,
    start_story,
    push_segment,
    snapshot,
    undo,
    get_story_text,
    get_word_count,
    get_last_ai_segment,
    update_characters_and_rules,
    export_markdown,
    save_session,
    load_session,
    restore_session,
    clear_saved_session,
    saved_ago_label,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Story Weaver",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;1,400&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1, h2, h3 { font-family: 'Playfair Display', Georgia, serif !important; }

.story-text {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 1.05rem;
    line-height: 1.9;
    color: #1a1410;
}
.seg-ai     { margin-bottom: 1.2rem; }
.seg-user   { margin-bottom: 1.2rem; color: #1a3060; font-style: italic; }
.seg-system {
    margin-bottom: 0.8rem;
    text-align: center;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.82rem;
    color: #6b5d52;
    font-style: italic;
}
.ornament {
    font-size: 1.4rem;
    letter-spacing: 0.3em;
    color: #b8860b;
    text-align: center;
    display: block;
    margin-bottom: 0.2rem;
}
.char-card {
    background: rgba(255,255,255,0.6);
    border: 1px solid rgba(90,60,30,0.15);
    border-radius: 6px;
    padding: 0.5rem 0.7rem;
    margin-bottom: 0.4rem;
    font-size: 0.82rem;
}
.char-name { font-weight: 500; color: #1a1410; }
.char-desc { color: #6b5d52; font-size: 0.72rem; margin-top: 0.1rem; }
.rule-pill {
    padding-left: 0.6rem;
    border-left: 2px solid #e8d9c4;
    margin-bottom: 0.35rem;
    font-size: 0.8rem;
    color: #6b5d52;
    line-height: 1.5;
}
.error-box {
    background: #fcebeb;
    border: 1px solid #f09595;
    border-radius: 6px;
    padding: 0.7rem 1rem;
    color: #a32d2d;
    font-size: 0.88rem;
    margin-bottom: 1rem;
}
/* Streaming output container */
.stream-box {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 1.05rem;
    line-height: 1.9;
    color: #1a1410;
    padding: 0.5rem 0;
    border-left: 3px solid #c4633a;
    padding-left: 1rem;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

init_session()


# ══════════════════════════════════════════════════════════════════════════════
# SETUP SCREEN
# ══════════════════════════════════════════════════════════════════════════════

def render_setup():
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown('<span class="ornament">✦ ✦ ✦</span>', unsafe_allow_html=True)
        st.markdown("<h1 style='text-align:center;margin-bottom:0.2rem'>Story Weaver</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;color:#6b5d52;margin-bottom:2rem'>A collaborative fiction engine — powered by AI</p>", unsafe_allow_html=True)

        # ── Resume banner ─────────────────────────────────────────────────────
        saved = load_session()
        if saved and saved.get("segments"):
            wc_saved = len(" ".join(
                s["text"] for s in saved["segments"] if s["type"] != "system"
            ).split())
            with st.container():
                st.info(
                    f"📖 **Saved story found:** *{saved.get('title','Untitled')}* "
                    f"({saved.get('genre','')} · {wc_saved:,} words · "
                    f"saved {saved_ago_label(saved.get('saved_at', 0))})"
                )
                rc1, rc2 = st.columns(2)
                with rc1:
                    if st.button("Resume →", type="primary", use_container_width=True):
                        restore_session(saved)
                        st.rerun()
                with rc2:
                    if st.button("Discard & start fresh", use_container_width=True):
                        clear_saved_session()
                        st.rerun()
                st.markdown("")

        title = st.text_input("Story Title", placeholder="The Forgotten Archive…")

        st.markdown("**Genre**")
        genre = st.session_state.get("_selected_genre", "")
        cols  = st.columns(3)
        for i, g in enumerate(GENRES):
            with cols[i % 3]:
                is_active = genre == g
                if st.button(
                    f"{GENRE_ICONS[g]} {g}",
                    key=f"genre_{g}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                ):
                    st.session_state["_selected_genre"] = g
                    st.rerun()

        hook = st.text_area(
            "Opening Hook / Setting",
            placeholder="Set the scene — where does this story begin? Who do we follow? What's the inciting spark?",
            height=120,
        )

        if st.button("Begin the Story →", type="primary", use_container_width=True):
            selected = st.session_state.get("_selected_genre", "")
            if not selected:
                st.warning("Please pick a genre first.")
            elif not hook.strip():
                st.warning("Add an opening hook to begin.")
            else:
                start_story(title, selected, hook)
                _generate_opening()
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# STORY SCREEN
# ══════════════════════════════════════════════════════════════════════════════

def render_story():
    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"### ✦ {st.session_state.story_title}")
        genre = st.session_state.story_genre
        wc    = get_word_count()
        st.caption(f"{GENRE_ICONS.get(genre, '')} {genre}  ·  {wc:,} words")
        st.divider()

        st.markdown("**Creativity**")
        temperature = st.slider(
            "Temperature", 0.0, 1.0, 0.7, 0.05,
            label_visibility="collapsed",
            help="Higher = more surprising prose",
        )
        label = "🎲 Unpredictable" if temperature > 0.8 else ("✍️ Balanced" if temperature > 0.4 else "📐 Precise")
        st.caption(label)
        st.session_state["_temperature"] = temperature

        # Streaming toggle
        st.divider()
        streaming = st.toggle(
            "⚡ Live streaming",
            value=st.session_state.get("_streaming", True),
            help="Stream AI output word-by-word instead of waiting for the full response",
        )
        st.session_state["_streaming"] = streaming
        st.divider()

        # Characters
        st.markdown("**Characters**")
        chars = st.session_state.characters
        if chars:
            for name, desc in chars.items():
                st.markdown(
                    f'<div class="char-card"><div class="char-name">{name}</div>'
                    f'<div class="char-desc">{desc}</div></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Characters will appear as the story unfolds.")
        st.divider()

        # Story rules
        st.markdown("**Story Rules**")
        if st.session_state.rules:
            for r in st.session_state.rules:
                st.markdown(f'<div class="rule-pill">• {r}</div>', unsafe_allow_html=True)
        else:
            st.caption("World establishing…")
        st.divider()

        # Utility buttons
        if st.button("↩ Undo Last Turn", use_container_width=True):
            if undo():
                st.success("Last turn undone.")
            else:
                st.warning("Nothing to undo.")
            st.rerun()

        md    = export_markdown()
        fname = st.session_state.story_title.lower().replace(" ", "-") + ".md"
        st.download_button("Export Story ↓", data=md, file_name=fname,
                           mime="text/markdown", use_container_width=True)

        if st.button("New Story", use_container_width=True):
            clear_saved_session()
            st.session_state.screen = "setup"
            st.session_state["_selected_genre"] = ""
            st.rerun()

    # ── Main story column ─────────────────────────────────────────────────────
    st.markdown(f"## {st.session_state.story_title}")

    if st.session_state.error:
        st.markdown(
            f'<div class="error-box">{st.session_state.error}</div>',
            unsafe_allow_html=True,
        )
        st.session_state.error = None

    # Render completed segments
    story_html = ""
    for seg in st.session_state.segments:
        text       = seg.text.replace("<", "&lt;").replace(">", "&gt;")
        paragraphs = [f"<p>{p}</p>" for p in text.split("\n\n") if p.strip()]
        block      = "\n".join(paragraphs) if paragraphs else f"<p>{text}</p>"
        if seg.type == "ai":
            story_html += f'<div class="seg-ai story-text">{block}</div>'
        elif seg.type == "user":
            story_html += f'<div class="seg-user story-text">{block}</div>'
        else:
            story_html += f'<div class="seg-system">{text}</div>'

    if story_html:
        st.markdown(f'<div>{story_html}</div>', unsafe_allow_html=True)

    # Active choices
    choices = st.session_state.active_choices
    if choices:
        st.markdown("---")
        st.markdown("**Choose your path:**")
        for i, choice in enumerate(choices):
            if st.button(choice, key=f"choice_{i}", use_container_width=True):
                st.session_state.active_choices = None
                _continue_from_choice(choice)
                st.rerun()
        if st.button("↩ Cancel choices", key="cancel_choices"):
            st.session_state.active_choices = None
            st.rerun()
        return

    st.markdown("---")

    # ── Input bar ─────────────────────────────────────────────────────────────
    user_text = st.text_area(
        "Your contribution",
        placeholder="Add your own sentences, or use the buttons below to let AI continue…",
        height=80,
        label_visibility="collapsed",
        key="user_input_box",
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("✦ Continue with AI", type="primary", use_container_width=True):
            _ai_continue()
            st.rerun()
    with c2:
        if st.button("Give Me Choices", use_container_width=True):
            _give_choices()
            st.rerun()
    with c3:
        if st.button("Add Mine", use_container_width=True):
            text = user_text.strip()
            if text:
                snapshot()
                push_segment("user", text)
                save_session()
                st.session_state["user_input_box"] = ""
            st.rerun()
    with c4:
        if st.button("Genre Remix", use_container_width=True):
            _genre_remix()
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ACTION HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

def _sys_prompt() -> str:
    return build_system_prompt(st.session_state.story_genre, st.session_state.story_hook)

def _temp() -> float:
    return st.session_state.get("_temperature", 0.7)

def _use_streaming() -> bool:
    return st.session_state.get("_streaming", True)


def _stream_and_collect(messages: list[dict], system_prompt: str = "") -> str:
    """
    Stream a response into a live st.write_stream() container and return
    the fully collected text when done.

    The streaming output is rendered with a left-border accent so users
    can see it's live. Once complete, the caller pushes it to state and
    the page reruns to render it in the normal story format.
    """
    collected = []

    def _generator():
        for chunk in stream_llm(messages, system_prompt=system_prompt, temperature=_temp()):
            collected.append(chunk)
            yield chunk

    with st.container():
        st.markdown('<div class="stream-box">', unsafe_allow_html=True)
        st.write_stream(_generator())
        st.markdown('</div>', unsafe_allow_html=True)

    return "".join(collected).strip()


def _generate_opening():
    messages = [{"role": "user", "content": build_opening_prompt(
        st.session_state.story_genre, st.session_state.story_hook,
    )}]
    try:
        if _use_streaming():
            text = _stream_and_collect(messages, system_prompt=_sys_prompt())
        else:
            text = call_llm(messages, system_prompt=_sys_prompt(), temperature=_temp())
        push_segment("ai", text)
        save_session()
        _extract_sidebar()
    except RuntimeError as e:
        st.session_state.error = str(e)


def _ai_continue():
    snapshot()
    messages = [{"role": "user", "content": build_continuation_prompt(get_story_text())}]
    try:
        if _use_streaming():
            text = _stream_and_collect(messages, system_prompt=_sys_prompt())
        else:
            text = call_llm(messages, system_prompt=_sys_prompt(), temperature=_temp())
        push_segment("ai", text)
        save_session()
        _extract_sidebar()
    except RuntimeError as e:
        st.session_state.error = str(e)


def _give_choices():
    snapshot()
    try:
        # Choices parsing needs the full response at once — no streaming
        raw = call_llm(
            messages=[{"role": "user", "content": build_choices_prompt(get_story_text())}],
            system_prompt=_sys_prompt(),
            temperature=_temp(),
        )
        choices = _parse_choices(raw)
        if choices:
            st.session_state.active_choices = choices
        else:
            st.session_state.error = "⚠️ Could not parse choices — please try again."
    except RuntimeError as e:
        st.session_state.error = str(e)


def _continue_from_choice(choice: str):
    messages = [{"role": "user", "content": build_choice_continuation_prompt(
        get_story_text(), choice
    )}]
    try:
        if _use_streaming():
            text = _stream_and_collect(messages, system_prompt=_sys_prompt())
        else:
            text = call_llm(messages, system_prompt=_sys_prompt(), temperature=_temp())
        push_segment("system", f'↳ Chose: "{choice}"')
        push_segment("ai", text)
        save_session()
        _extract_sidebar()
    except RuntimeError as e:
        st.session_state.error = str(e)


def _genre_remix():
    last = get_last_ai_segment()
    if not last:
        st.session_state.error = "⚠️ No AI segments to remix yet."
        return
    others    = [g for g in GENRES if g != st.session_state.story_genre]
    new_genre = random.choice(others)
    snapshot()
    messages  = [{"role": "user", "content": build_remix_prompt(last.text, new_genre)}]
    try:
        if _use_streaming():
            text = _stream_and_collect(messages)
        else:
            text = call_llm(messages, temperature=_temp())
        push_segment("system", f"✦ Genre Remix → {new_genre}")
        push_segment("ai", text)
        save_session()
    except RuntimeError as e:
        st.session_state.error = str(e)


def _extract_sidebar():
    """Fire-and-forget extraction — always non-streaming, low temp."""
    try:
        raw = call_llm(
            messages=[{"role": "user", "content": build_extraction_prompt(
                get_story_text(), st.session_state.story_genre,
            )}],
            temperature=0.2,
        )
        update_characters_and_rules(raw)
    except Exception:
        pass


def _parse_choices(raw: str) -> list[str] | None:
    import re
    lines   = [l.strip() for l in raw.strip().splitlines() if l.strip()]
    choices = []
    for line in lines:
        m = re.match(r"^\d+[\.\)]\s*(?:\[.*?\]:\s*)?(.+)$", line)
        if m:
            choices.append(m.group(1).strip())
    return choices if len(choices) >= 2 else None


# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state.screen == "setup":
    render_setup()
else:
    render_story()
