"""Curated voice palette. Personas pick from this set instead of designing new
voices (voice choice doesn't change per-minute cost; designing voices does).

All entries are ElevenLabs premade voices, so they work on any workspace.
The premade library has no "old" voices, so OLD falls back to MIDDLE_AGED.
"""

from .models import AgeBand, Gender

PALETTE: dict[tuple[Gender, AgeBand], list[tuple[str, str]]] = {
    (Gender.FEMALE, AgeBand.YOUNG): [
        ("cgSgspJ2msm6clMCkdW9", "Jessica - playful, bright, warm"),
        ("EXAVITQu4vr4xnSDxMaL", "Sarah - mature, reassuring"),
    ],
    (Gender.FEMALE, AgeBand.MIDDLE_AGED): [
        ("XrExE9yKIg1WjnnlVkGX", "Matilda - knowledgeable, alto"),
        ("hpp4J3VqNfWAUOO0d1Us", "Bella - professional, warm"),
    ],
    (Gender.MALE, AgeBand.YOUNG): [
        ("bIHbv24MWmeRgasZH58o", "Will - relaxed optimist"),
    ],
    (Gender.MALE, AgeBand.MIDDLE_AGED): [
        ("iP95p4xoKVk53GoZ742B", "Chris - charming, down-to-earth"),
        ("CwhRBWXzGAHq8TQ4Fs17", "Roger - laid-back, resonant"),
        ("cjVigY5qzO86Huf0OWal", "Eric - smooth, trustworthy"),
    ],
    (Gender.NEUTRAL, AgeBand.MIDDLE_AGED): [
        ("SAz9YHcvj6GT2YYXdXww", "River - relaxed, neutral"),
    ],
}

DEFAULT_VOICE_ID = "cjVigY5qzO86Huf0OWal"  # Eric, the agents' default


def pick_voice(gender: Gender, age_band: AgeBand, seed: str = "") -> str:
    """Return a voice_id for the persona. `seed` (e.g. the persona name) keeps
    the choice stable across calls while spreading personas across voices."""
    if age_band is AgeBand.OLD:
        age_band = AgeBand.MIDDLE_AGED
    options = PALETTE.get((gender, age_band)) or PALETTE.get((gender, AgeBand.MIDDLE_AGED))
    if not options:
        return DEFAULT_VOICE_ID
    index = sum(map(ord, seed)) % len(options)
    return options[index][0]
