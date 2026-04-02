"""
prompts.py — Prompt builders and genre configuration

All prompt strings live here. Keeping them separate from app logic makes
them easy to iterate on without touching UI or state code.
"""

GENRES = ["Fantasy", "Sci-Fi", "Mystery", "Romance", "Horror", "Comedy"]

GENRE_TONES = {
    "Fantasy": "Rich world-building, mythic stakes, magic with rules and costs, heroic or morally complex characters.",
    "Sci-Fi":  "Scientific plausibility, speculative technology, existential or societal themes, wonder and dread.",
    "Mystery": "Carefully planted clues, unreliable appearances, mounting tension, satisfying logical resolution.",
    "Romance": "Emotional depth, slow-burn tension, authentic dialogue, characters with genuine flaws and desires.",
    "Horror":  "Dread over shock, atmospheric unease, psychological depth, the mundane made terrifying.",
    "Comedy":  "Timing and subverted expectations, wit over slapstick, character-driven humor, joyful absurdity.",
}

GENRE_ICONS = {
    "Fantasy": "🧙",
    "Sci-Fi":  "🚀",
    "Mystery": "🔍",
    "Romance": "🌹",
    "Horror":  "🕯️",
    "Comedy":  "🎭",
}


def build_system_prompt(genre: str, hook: str) -> str:
    """
    Core system prompt pinned to every story-continuation call.
    Locks in genre, tone, and the author's original premise so the model
    cannot drift or contradict earlier content.
    """
    tone = GENRE_TONES.get(genre, "Engaging, vivid, and emotionally resonant.")
    return f"""You are a masterful collaborative fiction writer specializing in {genre} stories.

CORE RULES:
- Stay 100% consistent with ALL prior events, character names, personalities, and world details. Never contradict what has been established.
- Write in vivid, evocative third-person prose. Match the {genre} genre's conventions and tone precisely.
- Keep responses focused and tight — no padding, throat-clearing, or filler phrases.
- When continuing, write 1–2 paragraphs (150–250 words). End on a compelling note that invites the next contribution.
- NEVER restart the story or ignore prior context. The full story history is your absolute ground truth.
- Character voices must remain distinct and consistent. If a character is brave, they stay brave. If a city is ruined, it stays ruined.

GENRE — {genre}: {tone}

ORIGINAL STORY PREMISE (set by the author):
"{hook}"
"""


def build_opening_prompt(genre: str, hook: str) -> str:
    return (
        f'Write a vivid, compelling opening for a {genre} story.\n\n'
        f'Author\'s premise: "{hook}"\n\n'
        f'Requirements:\n'
        f'- 150–220 words\n'
        f'- Start in medias res — drop the reader straight into the world\n'
        f'- Establish the protagonist and setting in the first two sentences\n'
        f'- End on a hook that makes the reader want to know what happens next\n'
        f'- Do NOT include a title or chapter heading'
    )


def build_continuation_prompt(story_so_far: str) -> str:
    return (
        f'FULL STORY SO FAR:\n{story_so_far}\n\n'
        f'Continue the story naturally for 1–2 paragraphs. '
        f'Stay in genre and remain 100% consistent with all established details.'
    )


def build_choices_prompt(story_so_far: str) -> str:
    return (
        f'FULL STORY SO FAR:\n{story_so_far}\n\n'
        f'Based on everything established, suggest EXACTLY 3 story-branch options for what could happen next. '
        f'Each must be genuinely different in direction (action vs. character revelation vs. world event, etc.).\n\n'
        f'Format your response as a numbered list, exactly like this — nothing else:\n'
        f'1. [Option A label]: One sentence describing this path.\n'
        f'2. [Option B label]: One sentence describing this path.\n'
        f'3. [Option C label]: One sentence describing this path.'
    )


def build_choice_continuation_prompt(story_so_far: str, chosen: str) -> str:
    return (
        f'The author has chosen this story direction: "{chosen}"\n\n'
        f'Continue the story from this choice for 1–2 vivid paragraphs. '
        f'Honour every detail established previously.\n\n'
        f'FULL STORY SO FAR:\n{story_so_far}'
    )


def build_remix_prompt(passage: str, new_genre: str) -> str:
    return (
        f'Rewrite ONLY the following passage in {new_genre} genre style, '
        f'while preserving the exact plot events, character names, and facts. '
        f'Completely transform the tone, atmosphere, vocabulary, and prose style:\n\n'
        f'"{passage}"'
    )


def build_extraction_prompt(story_so_far: str, genre: str) -> str:
    """
    Silent background call to extract characters and world rules.
    Returns JSON — failures in the caller are swallowed.
    """
    recent = story_so_far[-3000:]  # keep token cost bounded
    return (
        f'From this {genre} story excerpt, extract named characters and '
        f'2–3 key world/story rules established so far. Be concise.\n\n'
        f'Story:\n{recent}\n\n'
        f'Respond with valid JSON only — no markdown, no preamble:\n'
        f'{{"characters":[{{"name":"...","description":"one sentence"}}],"rules":["...","...","..."]}}'
    )
