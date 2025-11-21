import streamlit as st
import string
from typing import Dict, List, Tuple
import base64
from pathlib import Path

def add_bg_from_local(image_file: str):
    """
    Use a local image as full-page background.
    Also add a semi-transparent white panel so text is readable.
    """
    img_path = Path(image_file)
    if not img_path.exists():
        return  # if no file, silently skip

    with open(img_path, "rb") as f:
        data = base64.b64encode(f.read()).decode()

    css = f"""
    <style>
    .stApp {{
        background-image: url("data:image/jpeg;base64,{data}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}

    /* main content card, so text stays readable on a soft white panel */
    .block-container {{
        background-color: rgba(255, 255, 255, 0.80);
        padding: 2rem 3rem 3rem 3rem;
        border-radius: 1.5rem;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# =========================
# 1. Lexicons: mood / energy / genre / context
# =========================
# Mood words: loosely inspired by emotion lexicons (e.g., NRC Emotion Lexicon)
mood_lexicon: Dict[str, List[str]] = {
    "chill": [
        "calm", "relax", "relaxed", "chill", "peaceful", "soft",
        "soothing", "smooth", "mellow", "gentle", "quiet", "cozy"
    ],
    "happy": [
        "happy", "bright", "cheerful", "fun", "upbeat", "uplifting",
        "joyful", "exciting", "excited", "optimistic", "hopeful"
    ],
    "sad": [
        "sad", "melancholy", "blue", "lonely", "depressed",
        "heartbroken", "down", "gloomy"
    ],
    "intense": [
        "intense", "strong", "aggressive", "powerful", "heavy",
        "hard", "raw", "angry"
    ],
    "nostalgic": [
        "nostalgic", "old", "retro", "memory", "memories",
        "throwback", "vintage", "classic", "childhood"
    ],
}

# Energy words: adjectives + activity cues
energy_lexicon: Dict[str, List[str]] = {
    "high": [
        "fast", "loud", "energetic", "dance", "party", "rock",
        "run", "running", "jog", "workout", "gym", "cardio",
        "intense", "hype", "powerful", "hard"
    ],
    "low": [
        "slow", "soft", "quiet", "ambient", "background",
        "sleep", "sleepy", "bedtime", "chill", "relax", "relaxed", "calm"
    ],
}

# Genre words: loosely organized based on common Spotify / Last.fm style tags
genre_lexicon: Dict[str, List[str]] = {
    # chill / study vibes
    "lofi": ["lofi", "lo-fi", "beat tape", "chillhop"],
    "jazz": ["jazz", "sax", "saxophone", "swing", "bebop"],
    "classical": ["classical", "piano", "orchestra", "symphony", "violin", "cello"],
    "ambient": ["ambient", "drone", "soundscape"],

    # rock family
    "rock": ["rock", "metal", "punk", "hardcore", "alt-rock", "alternative"],
    "indie": ["indie", "indie-rock", "indie-pop"],

    # pop / dance / mainstream
    "pop": ["pop", "kpop", "k-pop", "jpop", "j-pop", "c-pop", "cpop"],
    "edm": ["edm", "electronic", "techno", "house", "trance", "dubstep"],
    "hiphop": ["hiphop", "hip-hop", "rap", "trap"],

    # groove / chill groove
    "rnb": ["rnb", "r&b", "soul", "neo-soul", "funk"],

    # roots / acoustic
    "folk": ["folk", "acoustic", "singer-songwriter"],
    "country": ["country", "bluegrass"],

    # world / regional
    "latin": ["latin", "reggaeton", "salsa", "bossa", "bossa nova"],
    "reggae": ["reggae", "dub"],

    # others
    "soundtrack": ["soundtrack", "ost", "score", "movie score", "game music"],
}

# Listening context (situations)
context_lexicon: Dict[str, List[str]] = {
    "study": ["study", "studying", "homework", "exam", "reading", "library"],
    "commute": ["commute", "bus", "train", "subway", "metro", "driving", "car", "walk", "walking"],
    "workout": ["workout", "gym", "run", "running", "jog", "cardio", "exercise"],
    "sleep": ["sleep", "sleepy", "bedtime", "before bed", "night", "fall asleep"],
    "relax": ["relax", "relaxed", "relaxing", "chill", "weekend", "coffee", "cafe", "cozy"],
    "party": ["party", "club", "dancefloor", "festival"],
}

# =========================
# 2. Preprocessing & counting
# =========================

def preprocess(text: str) -> List[str]:
    """Lowercase + remove punctuation + tokenize by whitespace."""
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    tokens = [t for t in text.split() if t.strip() != ""]
    return tokens


def count_from_lexicon(tokens: List[str], lexicon: Dict[str, List[str]]) -> Dict[str, int]:
    """Count how many words from each lexicon category appear."""
    counts = {k: 0 for k in lexicon.keys()}
    for cat, words in lexicon.items():
        for w in tokens:
            if w in words:
                counts[cat] += 1
    return counts


def get_max_or_none(counts_dict: Dict[str, int]) -> Tuple[str, int]:
    """Return the category with the highest count and its score."""
    if not counts_dict:
        return None, 0
    max_cat = max(counts_dict, key=lambda k: counts_dict[k])
    return max_cat, counts_dict[max_cat]


def decide_energy(energy_counts: Dict[str, int], context_counts: Dict[str, int]) -> str:
    """
    Decide overall energy level based on:
    - explicit energy words
    - plus listening context (workout/party → high, sleep/relax/study → low)
    """
    base_high = energy_counts["high"]
    base_low = energy_counts["low"]

    context_high = context_counts["workout"] + context_counts["party"]
    context_low = context_counts["sleep"] + context_counts["relax"] + context_counts["study"]

    total_high = base_high + context_high
    total_low = base_low + context_low

    if total_high > total_low:
        return "high"
    elif total_low > total_high:
        return "low"
    else:
        return "mixed"

# =========================
# 3. Music persona → coffee persona
# =========================

def map_persona_to_coffee(
    main_mood: str,
    main_genre: str,
    energy_level: str,
    main_context: str,
    mood_score: int,
    genre_score: int,
):
    """
    Map dominant mood / genre / energy / context into a coffee personality.
    Includes several coffee types and a fallback when nothing matches.
    """

    # 0. No matches at all → Mystery Blend
    if mood_score == 0 and genre_score == 0:
        return (
            "☕ Mystery Blend Coffee",
            "From your description, I could not detect any of the mood/genre keywords "
            "in this small lexicon. This suggests that your taste is either very unique "
            "or simply outside my current database. You are like a mystery blend: "
            "it takes time to discover all the flavors."
        )

    # 1. chill + lofi/jazz/ambient/R&B + study/relax + not high energy → Matcha Latte
    if (
        main_mood == "chill"
        and main_genre in ["lofi", "jazz", "ambient", "rnb"]
        and energy_level != "high"
        and main_context in ["study", "relax", None]
    ):
        return (
            "🍵 Matcha Latte",
            "You seem to enjoy calm, smooth, and atmospheric music (lofi / jazz / ambient / R&B), "
            "often for studying or relaxing. Your music personality is like a matcha latte: "
            "gentle, soothing, and a bit ritualistic."
        )

    # 2. high energy + pop/edm/latin + commute/workout/party → Iced Americano
    if (
        energy_level == "high"
        and main_genre in ["pop", "edm", "latin"]
        and main_context in ["commute", "workout", "party"]
    ):
        return (
            "🧊 Iced Americano",
            "Your playlist is bright, refreshing, and energetic (pop / EDM / Latin), "
            "especially when you are on the move. You are like an iced Americano: "
            "clear, sharp, and perfect for waking up your day."
        )

    # 3. high energy + rock/hiphop/indie + workout/party → Espresso Shot
    if (
        energy_level == "high"
        and main_genre in ["rock", "hiphop", "indie"]
    ):
        return (
            "⚡ Espresso Shot",
            "Your music is intense and full of impact (rock / metal / hip-hop / indie). "
            "You are like an espresso shot: small but very strong."
        )

    # 4. nostalgic or soundtrack/folk/classic focus → Hand-brewed Black Coffee
    if main_mood == "nostalgic" or main_genre in ["soundtrack", "folk"]:
        return (
            "☕ Hand-brewed Black Coffee",
            "You gravitate towards music that carries stories and memories — soundtracks, "
            "folk songs, or classics that remind you of specific moments. "
            "Your music personality is like a hand-brewed black coffee: slow, thoughtful, and deep."
        )

    # 5. sad → Mocha
    if main_mood == "sad":
        return (
            "🍫 Mocha",
            "You resonate with emotional or slightly melancholic music. "
            "You are like a mocha: a mix of bitterness and sweetness, with rich emotional flavor."
        )

    # 6. happy + pop/edm/rnb/latin → Caramel Macchiato
    if main_mood == "happy" and main_genre in ["pop", "edm", "rnb", "latin"]:
        return (
            "🍮 Caramel Macchiato",
            "You enjoy cheerful, fun, and catchy songs. "
            "Your music personality is like a caramel macchiato: sweet, playful, and crowd-pleasing."
        )

    # 7. classical / jazz + study/reading → Flat White
    if main_genre in ["classical", "jazz"] and main_context in ["study", "relax", "sleep"]:
        return (
            "🥛 Flat White",
            "You appreciate structure, detail, and balance in music (classical / jazz), "
            "often as a companion for reading or quiet time. "
            "Your music personality is like a flat white: refined, smooth, and carefully crafted."
        )

    # 8. default → House Blend
    return (
        "🫘 House Blend",
        "Your music taste seems quite diverse and not dominated by any single mood or genre "
        "in this lexicon. You are like a house blend: a balanced mix of different flavors."
    )


def analyze_music_personality(text: str) -> dict:
    """Main analysis function: text → counts → coffee personality."""
    tokens = preprocess(text)

    mood_counts = count_from_lexicon(tokens, mood_lexicon)
    energy_counts = count_from_lexicon(tokens, energy_lexicon)
    genre_counts = count_from_lexicon(tokens, genre_lexicon)
    context_counts = count_from_lexicon(tokens, context_lexicon)

    main_mood, mood_score = get_max_or_none(mood_counts)
    main_genre, genre_score = get_max_or_none(genre_counts)
    main_context, context_score = get_max_or_none(context_counts)

    energy_level = decide_energy(energy_counts, context_counts)

    coffee, explanation = map_persona_to_coffee(
        main_mood, main_genre, energy_level, main_context, mood_score, genre_score
    )

    result = {
        "tokens": tokens,
        "mood_counts": mood_counts,
        "energy_counts": energy_counts,
        "genre_counts": genre_counts,
        "context_counts": context_counts,
        "main_mood": main_mood,
        "main_mood_score": mood_score,
        "main_genre": main_genre,
        "main_genre_score": genre_score,
        "main_context": main_context,
        "main_context_score": context_score,
        "energy_level": energy_level,
        "coffee": coffee,
        "explanation": explanation,
    }
    return result

# =========================
# 4. Streamlit UI
# =========================

st.set_page_config(
    page_title="Which Coffee Matches Your Music Personality?",
    page_icon="☕",
    layout="centered",
)
add_bg_from_local("bg_coffee_music.jpg")

st.title("🎧Which Coffee Matches Your Music Personality?")

st.markdown(
    """
Type a few sentences to describe your music taste, for example:

- What kinds of music do you usually listen to?  
  (lofi, jazz, pop, rock, metal, hip-hop, EDM, classical, ambient, folk, Latin, soundtrack…)
- In what situations do you listen?  
  (studying, commuting, working out, at the gym, in the car, before bed, at a party…)
- How does this music make you feel?  
  (calm, peaceful, excited, hyped, sad, nostalgic, etc.)

This web uses a tiny hand-crafted lexicon, inspired by genre labels on platforms like Spotify/Last.fm and by emotion lexicons,
to do a **simple text analysis** and then suggest a playful
**“music coffee personality”** for you.😊 

*Note: This is just for fun, not a scientific personality test.*
"""
)

user_text = st.text_area(
    "✏️ Describe your music taste in English:",
    height=180,
    placeholder=(
        "For example: I listen to energetic pop and EDM at the gym, "
        "and chill lofi beats when I study at night."
    ),
)

if st.button("☕ Generate my music coffee"):
    if not user_text.strip():
        st.warning("Please type something about your music taste first.")
    else:
        res = analyze_music_personality(user_text)

        st.subheader("Result")
        st.markdown(f"### {res['coffee']}")
        st.write(res["explanation"])

        st.markdown("---")
        st.markdown("#### Tiny text breakdown")

        with st.expander("🔎 View tokens"):
            st.write(res["tokens"])

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.write("**Mood counts**")
            st.json(res["mood_counts"])
        with col2:
            st.write("**Energy counts**")
            st.json(res["energy_counts"])
        with col3:
            st.write("**Genre counts**")
            st.json(res["genre_counts"])
        with col4:
            st.write("**Context counts**")
            st.json(res["context_counts"])

        st.caption(
            "This is a playful, lexicon-based demo for a class exercise, "
            "not a scientific assessment."
        )
