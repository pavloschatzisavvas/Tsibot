import discord
import json
import time
import unicodedata
import re
import webserver
from collections import defaultdict

# === ΡΥΘΜΙΣΕΙΣ ===
TOKEN = "MTQzNjMwNzMyNTg1Mjk3NTEwNA.GW4yY0.b1L_nuZkclWXpthUIoPJy4ZH1D8PjJrbQW4ysI"
TARGET_USER_ID = 462250676668334081  # <-- ID χρήστη που θα γίνεται mention
DATA_FILE = "emoji_stats.json"
JORDAN_ID = 559721059302113285
KARA_ID = 373217412964679681
DEV_ID = 371439997410213889

webserver.keep_alive()

# === COOLDOWNS ===
CATEGORY_COOLDOWNS = {
    "money": 15 * 60,   # 15 λεπτά
    "χιαστι": 3 * 60    # 3 λεπτά
}
DEFAULT_COOLDOWN = 1 #1 * 60  # αν λείπει κάποια κατηγορία

# === ΚΑΤΗΓΟΡΙΕΣ ===
TRACKED_GROUPS = {
    "money": ["💸", "💵", "cash", "λεφτά", "ευρώ", "€", "αγορά","χρήμα"],
    "χιαστι": ["αρχηγέ μου", "αρχηγέ"]
}

# === ΑΡΧΙΚΟΠΟΙΗΣΗ ===
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
client = discord.Client(intents=intents)

def normalize_text(text):
    """Αφαιρεί τόνους και κάνει lowercase"""
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

stats = load_data()
# κρατάει χρόνο τελευταίου mention ανά κατηγορία και κανάλι
last_mention_time = defaultdict(lambda: defaultdict(lambda: 0))

# === MENTION ΜΕ COOLDOWN ΑΝΑ ΚΑΤΗΓΟΡΙΑ ===
async def handle_trigger(channel, user, category, item):
    now = time.time()
    channel_id = channel.id

    cooldown = CATEGORY_COOLDOWNS.get(category, DEFAULT_COOLDOWN)
    last_time = last_mention_time[category][channel_id]

    if now - last_time >= cooldown:
        last_mention_time[category][channel_id] = now
        target_user = await client.fetch_user(TARGET_USER_ID)
        if category == "money":
            await channel.send(f"{target_user.mention}, ρίξε μια ματιά!")
        else:
            await channel.send(f"{target_user.mention}, παίχτηκε αρχηγική κίνηση!")

# === MESSAGE TRIGGER ===
@client.event
async def on_message(message):
    if message.author.bot:
        return

    normalized = normalize_text(message.content)
    user_id = str(message.author.id)

    target_phrase = normalize_text("αχα καλο ε")
    normalized_message = normalize_text(message.content)

    for category, triggers in TRACKED_GROUPS.items():
        triggered = False
        used_item = None

        for t in triggers:
            normalized_t = normalize_text(t)

            # === EMOJI CHECK ===
            if normalized_t == "":
                if t in message.content:
                    triggered = True
                    used_item = t
                    break
            # === WORD CHECK ===
            else:
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
            await handle_trigger(message.channel, message.author, category, used_item)
            break


    content = message.content.lower().strip()

    # === !stats <κατηγορία> ===
    if content.startswith("!stats "):
        parts = content.split()
        if len(parts) >= 2:
            category = parts[1]
            if category in stats:
                count = stats[category].get(user_id, 0)
                await message.channel.send(
                    f"📊 {message.author.name}, έχεις ενεργοποιήσει την κατηγορία **{category}** {count} φορές!"
                )
            else:
                await message.channel.send(f"❌ Δεν υπάρχει κατηγορία '{category}'.")

    elif any(word in normalized_message for word in ("smite", "σμαιτ")):
        jordan = await client.fetch_user(JORDAN_ID)
        await message.channel.send(f"{jordan.mention}, Πότε θα φτάσεις διαμοντ λουλουδένιε μου??")
        return

    elif any(word in normalized_message for word in ("ζούγκλα", "ζουγκλα")):
        kara = await client.fetch_user(KARA_ID)
        await message.channel.send(f"{kara.mention}, ΑΚΑΛΑ")
        return

    elif any(word in normalized_message for word in ("ντεβ",)):
        dev = await client.fetch_user(DEV_ID)
        await message.channel.send(f"{dev.mention}, Σκουπίδι ντεβ δεν κάνεις για τίποτα, μακάρι ΔΥΠΑ και τα σχετικά. ΣΙΧΑΜΑ!!")
        return
    # === !top <κατηγορία> ===
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
                        msg = (
                            f"🥇 **{user.name}** — {count} φορές! "
                            f"{'Ο απόλυτος <<αρχηγός>> της ΧΙΑΣΤΗΣ❌!' if category == 'χιαστι' else f'Ο νικητής του {category.upper()}! Πας για μεγάλη επιστροφή φόρου!'}"
                        )
                    elif i == 2:
                        msg = (
                            f"🥈 **{user.name}** — {count} φορές! "
                            f"{'Δυνατά τα χέρια σου!' if category == 'χιαστι' else 'Πολύ κοντά στην κορυφή! Πρέπει να πληρώνεις λίγο παραπάνω με κάρτα!'}"
                        )
                    elif i == 3:
                        msg = (
                            f"🥉 **{user.name}** — {count} φορές! "
                            f"{'Θέλει περισσότερη προσπάθεια στον καρπό!' if category == 'χιαστι' else 'Του χρόνου πάμε καλύτερα για το αφορολόγητο!'}"
                        )
                    leaderboard.append(msg)

                leaderboard_text = "\n".join(leaderboard)
                await message.channel.send(f"🏆 **Leaderboard για {category.upper()}:**\n{leaderboard_text}")
            else:
                await message.channel.send(f"❌ Δεν υπάρχουν δεδομένα για '{category}'.")

    # === !moneyboard ===
    elif content.startswith(("!λογιστης","!λογιστής")):
        if "money_sum" in stats and stats["money_sum"]:
            sorted_users = sorted(stats["money_sum"].items(), key=lambda x: x[1], reverse=True)
            leaderboard = []
            for i, (uid, total) in enumerate(sorted_users[:5], start=1):
                user = await client.fetch_user(int(uid))
                leaderboard.append(f"{i}. **{user.name}** — {total:.2f}€")
            text = "\n".join(leaderboard)
            await message.channel.send(f"💰 **Ποιοι έχουν ξοδέψει τα περισσότερα:**\n{text}")
        else:
            await message.channel.send("📭 Δεν υπάρχουν ακόμα δεδομένα για ποσά σε ευρώ.")

    elif content.startswith("!categories"):
        categories = ", ".join(TRACKED_GROUPS.keys())
        await message.channel.send(f"📚 Διαθέσιμες κατηγορίες: {categories}")

    elif normalized_message.startswith(target_phrase):
        await message.channel.send("https://tenor.com/bh05x.gif")
        return

    # === !removemoney @user ποσό  (ADMIN ONLY) ===
    elif content.startswith("!removemoney"):
        parts = content.split()

        # ❗ Μόνο admins
        if not message.author.guild_permissions.administrator:
            await message.channel.send("🚫 Μόνο διαχειριστές μπορούν να αφαιρέσουν χρήματα από άλλους.")
            return

        # Πρέπει να υπάρχει mention και ποσό
        if len(parts) < 3:
            await message.channel.send("❌ Χρήση: `!removemoney @user ποσό`")
            return

        # Έλεγχος για mention
        if not message.mentions:
            await message.channel.send("❌ Πρέπει να κάνεις mention κάποιον χρήστη.")
            return

        target_user = message.mentions[0]
        amount_text = parts[-1]

        # Μετατροπή ποσού
        try:
            amount = float(amount_text.replace(",", "."))
        except:
            await message.channel.send("❌ Το ποσό δεν είναι έγκυρο.")
            return

        target_id = str(target_user.id)

        # Αν δεν υπάρχει money_sum, φτιάχνουμε το key
        stats.setdefault("money_sum", {})
        current = stats["money_sum"].get(target_id, 0)

        # Υπολογισμός νέου ποσού (δεν πάει αρνητικό)
        new_value = max(0, current - amount)
        stats["money_sum"][target_id] = new_value

        save_data(stats)

        await message.channel.send(
            f"💸 Αφαιρέθηκαν **{amount:.2f}€** από τον χρήστη **{target_user.name}**.\n"
            f"📉 Νέο σύνολο: **{new_value:.2f}€**"
        )
        return

@client.event
async def on_ready():
    print(f"✅ Συνδέθηκε ως {client.user}")

    channel_id = 1176993664371785762  # <-- ΒΑΛΕ ΕΔΩ ΤΟ CHANNEL ID
    channel = client.get_channel(channel_id)

    # if channel:
    #     await channel.send("🤖 Εδώ ειμαιιιιι!! Εδωωωωωω!!")
    # else:
    #     print("⚠️ Δεν μπόρεσα να βρω το κανάλι!")

client.run(TOKEN)
