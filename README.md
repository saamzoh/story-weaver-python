# Story Weaver ✦
### Python + Streamlit + OpenAI

A collaborative fiction engine that lets you write stories together with AI. The model remembers every character, plot detail, and world rule across the entire session.

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/story-weaver-python.git
cd story-weaver-python
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Add your API key

```bash
cp .env.example .env
# edit .env and set OPENAI_API_KEY=sk-...
```

### 3. Run

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`.

---

## Features

| Feature | Description |
|---|---|
| **Story Setup** | Title, 6 genre options, freeform opening hook |
| **AI Continuation** | 1–2 coherent paragraphs; full story history sent on every call |
| **Give Me Choices** | 3 story-specific branching paths; pick one to continue |
| **Add Mine** | Inject your own sentences (shown in blue italic) |
| **Genre Remix** | Rewrites the last AI paragraph in a randomly chosen other genre |
| **Undo** | Reverts the last turn (up to 20 levels deep) |
| **Export** | Downloads the full story as a clean `.md` file |
| **Character Tracker** | Live sidebar — auto-populated after each AI turn |
| **Story Rules** | World rules extracted and shown in the sidebar |
| **Creativity Slider** | Temperature 0.0–1.0 applied to every API call |
| **Error handling** | Friendly messages for rate limits, overload, network failures |
| **Retry logic** | Exponential backoff on overloaded responses, up to 2 retries |
| **Streaming** | Live word-by-word output via `st.write_stream()` — toggle in sidebar |
| **Session persistence** | Auto-saves to `.story_saves/session.json`; resume banner on next launch |

---

## Project Structure

```
story-weaver-python/
├── app.py              # Streamlit UI — screens, layout, action handlers
├── llm.py              # OpenAI wrapper — call_llm(), errors, retries
├── prompts.py          # All prompt builders and genre configuration
├── state.py            # Session state helpers, Segment dataclass, export
├── requirements.txt
├── .env.example
├── .gitignore
├── .streamlit/
│   └── config.toml     # Streamlit theme (parchment colours, serif font)
└── README.md
```

**Module responsibilities:**

- **llm.py** — One public function, `call_llm()`. Owns all OpenAI imports, retry logic, and typed error messages. Nothing else touches the OpenAI SDK.
- **prompts.py** — All prompt strings in one place. Change the AI's behaviour by editing this file alone.
- **state.py** — All `st.session_state` access goes through typed helpers here. The rest of the codebase never touches `st.session_state` directly.
- **app.py** — UI layout and event handlers. Each handler: validate → snapshot → call LLM → update state → `st.rerun()`.

---

## Stack

- **Python 3.11+**
- **[Streamlit](https://streamlit.io)** `>=1.35`
- **[OpenAI Python SDK](https://github.com/openai/openai-python)** `>=1.30`
- **[python-dotenv](https://pypi.org/project/python-dotenv/)**
- **Model:** `gpt-4o`

---

## Model & Provider

**Model:** `gpt-4o` · **Provider:** OpenAI

`gpt-4o` was chosen for its strong creative writing quality, fast response times, and 128k-token context window — large enough for an entire collaborative session without summarising older content.

To switch models, change `MODEL` in `llm.py`.

---

## Prompt Engineering

### System prompt (pinned to every story call)

```
You are a masterful collaborative fiction writer specializing in {genre} stories.

CORE RULES:
- Stay 100% consistent with ALL prior events, character names, personalities,
  and world details. Never contradict what has been established.
- Write in vivid, evocative third-person prose.
- NEVER restart the story or ignore prior context.
  The full story history is your absolute ground truth.
...
GENRE — {genre}: {tone description}
ORIGINAL STORY PREMISE: "{hook}"
```

Genre-specific tone instructions are injected per genre (e.g. Horror: *"dread over shock, the mundane made terrifying"*) so the model stays in register throughout.

### Choices prompt

Asks the model for a numbered list of exactly 3 branching options. A regex parser extracts them — robust to minor formatting variation.

### Extraction prompt

A separate low-temperature (`0.2`) call after each AI turn asks for `{characters, rules}` as JSON. Failures are swallowed — the sidebar is an enhancement, not a blocker.

---

## Memory & Consistency Strategy

**The full story text is sent with every API call.** No summarisation, no sliding window.

This guarantees the model sees every established fact. It works comfortably within `gpt-4o`'s 128k-token context window for all practical session lengths.

For very long sessions (50k+ words), a future improvement would compress older chapters into a summary and keep only recent turns verbatim.

---

## What Didn't Work at First

**The choices parser broke on lightly varied model output.** The parser initially expected a rigid `1. [Label]: text` format, but `gpt-4o` sometimes responded with `1) text` or just `1. text`. Stories got stuck when choices couldn't be parsed.

**Fix:** Rewrote `_parse_choices()` with a permissive regex — `r"^\d+[\.\)]\s*(?:\[.*?\]:\s*)?(.+)$"` — that handles any numbered-list format.

---

## What I'd Improve Next

1. ~~**Streaming**~~ — ✅ Shipped.
2. ~~**Session persistence**~~ — ✅ Shipped. Auto-saves to `.story_saves/session.json`; resume banner on launch.
3. **Long-story memory** — Summarise chapters older than ~40k tokens, keeping recent turns verbatim.
4. **Scene images** — Generate a DALL-E 3 prompt after each turn and display the image in the sidebar.
5. **Multiple save slots** — Let users name and switch between several in-progress stories.

---

## License

MIT
