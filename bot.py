import discord
import json
import time
import unicodedata
import re
from collections import defaultdict
from threading import Thread
from flask import Flask

# === ΡΥΘΜΙΣΕΙΣ ===
TOKEN = "MTQzNjMwNzMyNTg1Mjk3NTEwNA.GW4yY0.b1L_nuZkclWXpthUIoPJy4ZH1D8PjJrbQW4ysI"
TARGET_USER_ID = 462250676668334081
JORDAN_ID = 559721059302113285
KARA_ID = 373217412964679681
DEV_ID = 371439997410213889
DATA_FILE = "emoji_stats.json"

# === COOLDOWNS ===
CATEGORY_COOLDOWNS = {
    "money": 15 * 60,
    "χιαστι": 3 * 60
}
DEFAULT_COOLDOWN = 60

# === ΚΑΤΗΓΟΡΙΕΣ ===
TRACKED_GROUPS = {
    "money": ["💸", "💵", "cash", "λεφτά", "ευρώ", "€", "αγορά","χρήμα"],
    "χιαστι": ["αρχηγέ μου", "αρχηγέ"]
}

# === DISCORD BOT ===
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# === FLASK SERVER ΓΙΑ KEEP-ALIVE ===
app = Flask('')

@app.route('/')
def home():
    return "Bot is up!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# === UTILS ===
def normalize_text(text):
    nfkd_form = unicodedata.normalize("NFD", text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower()

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def contains_word(text, words):
    for w in words:
        pattern = rf"\b{re.escape(w)}\b"
        if re.search(pattern, text):
            return True
    return False

# === DATA & COOLDOWN TRACKER ===
stats = load_data()
last_mention_time = defaultdict(lambda: defaultdict(lambda: 0))  # category -> channel -> timestamp

# === HANDLE TRIGGER ΜΕ COOLDOWN ===
async def handle_trigger(channel, category):
    now = time.time()
    cooldown = CATEGORY_COOLDOWNS.get(category, DEFAULT_COOLDOWN)
    last_time = last_mention_time[category][channel.id]

    if now - last_time >= cooldown:
        last_mention_time[category][channel.id] = now
        target_user = await client.fetch_user(TARGET_USER_ID)
        if category == "money":
            await channel.send(f"{target_user.mention}, ρίξε μια ματιά!")
        else:
            await channel.send(f"{target_user.mention}, παίχτηκε αρχηγική κίνηση!")

# === DISCORD EVENTS ===
@client.event
async def on_ready():
    print(f"✅ Συνδέθηκε ως {client.user}")

@client.event
async def on_message(message):
    if message.author.bot:
        return

    normalized = normalize_text(message.content)
    user_id = str(message.author.id)
    content = message.content.lower().strip()
    normalized_message = normalized

    # === TRIGGERS ===
    for category, triggers in TRACKED_GROUPS.items():
        triggered = False
        for t in triggers:
            normalized_t = normalize_text(t)
            if normalized_t in normalized:
                triggered = True
                used_item = t
                break

        if triggered:
            stats.setdefault(category, {})
            stats[category][user_id] = stats[category].get(user_id, 0) + 1

            # === MONEY SUM ===
            if category == "money":
                amounts = re.findall(r"(\d+(?:[.,]\d+)?)\s*(?:€|ευρω|euro)", normalized)
                total = sum(float(a.replace(",", ".")) for a in amounts)
                if total > 0:
                    stats.setdefault("money_sum", {})
                    stats["money_sum"][user_id] = stats["money_sum"].get(user_id, 0) + total

            save_data(stats)
            await handle_trigger(message.channel, category)
            break

    # === COMMANDS ===
    if content.startswith("!stats "):
        parts = content.split()
        if len(parts) >= 2:
            category = parts[1]
            if category in stats:
                count = stats[category].get(user_id, 0)
                await message.channel.send(f"📊 {message.author.name}, έχεις ενεργοποιήσει την κατηγορία **{category}** {count} φορές!")
            else:
                await message.channel.send(f"❌ Δεν υπάρχει κατηγορία '{category}'.")

    elif content.startswith(("!λογιστης","!λογιστής")):
        if "money_sum" in stats and stats["money_sum"]:
            sorted_users = sorted(stats["money_sum"].items(), key=lambda x: x[1], reverse=True)
            leaderboard = []
            for i, (uid, total) in enumerate(sorted_users[:5], start=1):
                user = await client.fetch_user(int(uid))
                leaderboard.append(f"{i}. **{user.name}** — {total:.2f}€")
            await message.channel.send(f"💰 **Ποιοι έχουν ξοδέψει τα περισσότερα:**\n" + "\n".join(leaderboard))
        else:
            await message.channel.send("📭 Δεν υπάρχουν ακόμα δεδομένα για ποσά σε ευρώ.")

    elif content.startswith("!categories"):
        categories = ", ".join(TRACKED_GROUPS.keys())
        await message.channel.send(f"📚 Διαθέσιμες κατηγορίες: {categories}")

    elif content.startswith("!top "):
        parts = content.split()
        if len(parts) >= 2:
            category = parts[1]
            if category in stats and stats[category]:
                sorted_users = sorted(stats[category].items(), key=lambda x: x[1], reverse=True)
                leaderboard = []
                for i, (uid, count) in enumerate(sorted_users[:3], start=1):
                    user = await client.fetch_user(int(uid))
                    if i == 1:
                        msg = f"🥇 **{user.name}** — {count} φορές!"
                    elif i == 2:
                        msg = f"🥈 **{user.name}** — {count} φορές!"
                    else:
                        msg = f"🥉 **{user.name}** — {count} φορές!"
                    leaderboard.append(msg)
                await message.channel.send(f"🏆 **Leaderboard για {category.upper()}:**\n" + "\n".join(leaderboard))
            else:
                await message.channel.send(f"❌ Δεν υπάρχουν δεδομένα για '{category}'.")

    elif content.startswith("!removemoney"):
        parts = content.split()
        if not message.author.guild_permissions.administrator:
            await message.channel.send("🚫 Μόνο διαχειριστές μπορούν να αφαιρέσουν χρήματα.")
            return
        if len(parts) < 3 or not message.mentions:
            await message.channel.send("❌ Χρήση: `!removemoney @user ποσό`")
            return
        target_user = message.mentions[0]
        try:
            amount = float(parts[-1].replace(",", "."))
        except:
            await message.channel.send("❌ Το ποσό δεν είναι έγκυρο.")
            return
        target_id = str(target_user.id)
        stats.setdefault("money_sum", {})
        stats["money_sum"][target_id] = max(0, stats["money_sum"].get(target_id, 0) - amount)
        save_data(stats)
        await message.channel.send(f"💸 Αφαιρέθηκαν **{amount:.2f}€** από τον χρήστη **{target_user.name}**.\n📉 Νέο σύνολο: **{stats['money_sum'][target_id]:.2f}€**")

# === MAIN ===
if __name__ == "__main__":
    keep_alive()  # Flask server για Render
    client.run(TOKEN)
