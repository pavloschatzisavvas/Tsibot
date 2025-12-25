import discord
import json
import time
import unicodedata
import re
import webserver
from collections import defaultdict

# === ΡΥΘΜΙΣΕΙΣ ===
TOKEN = "MTQzNjMwNzMyNTg1Mjk3NTEwNA.GW4yY0.b1L_nuZkclWXpthUIoPJy4ZH1D8PjJrbQW4ysI"
TARGET_USER_ID = 462250676668334081
DATA_FILE = "emoji_stats.json"

JORDAN_ID = 559721059302113285
KARA_ID = 373217412964679681
DEV_ID = 371439997410213889

webserver.keep_alive()

# === COOLDOWNS ===
CATEGORY_COOLDOWNS = {
    "money": 15 * 60,
    "χιαστι": 3 * 60
}
DEFAULT_COOLDOWN = 60

# === ΚΑΤΗΓΟΡΙΕΣ ===
TRACKED_GROUPS = {
    "money": ["💸", "💵", "cash", "λεφτά", "ευρώ", "€", "αγορά", "χρήμα","ευρω","λεφτα","χρημα","αγορα"],
    "χιαστι": ["αρχηγέ μου", "αρχηγέ","αρχηγε","αρχηγε μου"]
}

# === DISCORD INIT ===
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# === HELPERS ===
def normalize_text(text):
    nfkd_form = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfkd_form if not unicodedata.combining(c)).lower()

def match_word(text, word):
    pattern = rf"\b{re.escape(word)}\b"
    return re.search(pattern, text) is not None

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

stats = load_data()
last_mention_time = defaultdict(lambda: defaultdict(lambda: 0))

# === MENTION HANDLER ===
async def handle_trigger(channel, category):
    now = time.time()
    channel_id = channel.id
    cooldown = CATEGORY_COOLDOWNS.get(category, DEFAULT_COOLDOWN)

    if now - last_mention_time[category][channel_id] >= cooldown:
        last_mention_time[category][channel_id] = now
        user = await client.fetch_user(TARGET_USER_ID)

        if category == "money":
            await channel.send(f"{user.mention}, ρίξε μια ματιά!")
        else:
            await channel.send(f"{user.mention}, παίχτηκε αρχηγική κίνηση!")

# === MESSAGE EVENT ===
@client.event
async def on_message(message):
    if message.author.bot:
        return

    normalized = normalize_text(message.content)
    user_id = str(message.author.id)

    # === TRACKED GROUPS ===
    for category, triggers in TRACKED_GROUPS.items():
        for t in triggers:
            if t in message.content or match_word(normalized, normalize_text(t)):
                stats.setdefault(category, {})
                stats[category][user_id] = stats[category].get(user_id, 0) + 1
                save_data(stats)
                await handle_trigger(message.channel, category)
                break
        else:
            continue
        break

    # === CUSTOM WORD TRIGGERS ===
    if any(match_word(normalized, w) for w in ("smite", "σμαιτ")):
        jordan = await client.fetch_user(JORDAN_ID)
        await message.channel.send(
            f"{jordan.mention}, Πότε θα φτάσεις διαμοντ λουλουδένιε μου??"
        )
        return

    if any(match_word(normalized, w) for w in ("ζουγκλα", "ζούγκλα")):
        kara = await client.fetch_user(KARA_ID)
        await message.channel.send(f"{kara.mention}, ΑΚΑΛΑ")
        return

    if match_word(normalized, "ντεβ"):
        dev = await client.fetch_user(DEV_ID)
        await message.channel.send(
            f"{dev.mention}, Σκουπίδι ντεβ δεν κάνεις για τίποτα, "
            f"μακάρι ΔΥΠΑ και τα σχετικά. ΣΙΧΑΜΑ!!"
        )
        return

    # === COMMANDS ===
    content = message.content.lower().strip()

    if content.startswith("!stats "):
        category = content.split()[1]
        count = stats.get(category, {}).get(user_id, 0)
        await message.channel.send(
            f"📊 {message.author.name}, "
            f"έχεις ενεργοποιήσει **{category}** {count} φορές!"
        )

    elif content.startswith("!categories"):
        await message.channel.send(
            f"📚 Διαθέσιμες κατηγορίες: {', '.join(TRACKED_GROUPS.keys())}"
        )

# === READY ===
@client.event
async def on_ready():
    print(f"✅ Συνδέθηκε ως {client.user}")

client.run(TOKEN)
