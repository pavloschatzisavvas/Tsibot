import discord
import json
import time
import unicodedata
import re
import webserver
from collections import defaultdict

# === ΡΥΘΜΙΣΕΙΣ ===
TOKEN = "MTQzNjMwNzMyNTg1Mjk3NTEwNA.GMF_C7.cRT677u9UURJ1CD14c4J0thISx2VsIIs9jPfuk"
TARGET_USER_ID = 462250676668334081  # <-- ID χρήστη που θα γίνεται mention
DATA_FILE = "emoji_stats.json"

webserver.keep_alive()

# === COOLDOWNS ===
CATEGORY_COOLDOWNS = {
    "money": 15 * 60,   # 15 λεπτά
    "χιαστι": 3 * 60    # 3 λεπτά
}
DEFAULT_COOLDOWN = 1  # αν λείπει κάποια κατηγορία

# === ΚΑΤΗΓΟΡΙΕΣ ===
TRACKED_GROUPS = {
    "money": ["💸", "💵", "cash", "λεφτά", "ευρώ", "€", "αγορά"],
    "χιαστι": ["αρχηγέ μου", "αρχηγέ"]
}

# === ΑΡΧΙΚΟΠΟΙΗΣΗ ===
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
client = discord.Client(intents=intents)

# === CACHE USERS ===
user_cache = {}

async def get_target_user(user_id):
    if user_id not in user_cache:
        try:
            user_cache[user_id] = await client.fetch_user(user_id)
        except discord.NotFound:
            return None
    return user_cache[user_id]

# === NORMALIZE TEXT ===
def normalize_text(text):
    nfkd_form = unicodedata.normalize("NFD", text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower()

# === LOAD/SAVE DATA ===
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

# === MENTION ΜΕ COOLDOWN ===
async def handle_trigger(channel, category):
    now = time.time()
    channel_id = channel.id
    cooldown = CATEGORY_COOLDOWNS.get(category, DEFAULT_COOLDOWN)
    last_time = last_mention_time[category][channel_id]

    if now - last_time >= cooldown:
        last_mention_time[category][channel_id] = now
        target_user = await get_target_user(TARGET_USER_ID)
        if not target_user:
            return

        if category == "money":
            await channel.send(f"{target_user.mention}, ρίξε μια ματιά!")
        else:
            await channel.send(f"{target_user.mention}, παίχτηκε αρχηγική κίνηση!")

# === MESSAGE HANDLER ===
@client.event
async def on_message(message):
    if message.author.bot:
        return

    normalized = normalize_text(message.content)
    user_id = str(message.author.id)
    target_phrase = normalize_text("αχα καλο ε")

    # --- TRIGGERS ---
    for category, triggers in TRACKED_GROUPS.items():
        if any(normalize_text(t) in normalized for t in triggers):
            matched_items = [t for t in triggers if normalize_text(t) in normalized]
            used_item = matched_items[0] if matched_items else "💬"
            stats.setdefault(category, {})
            stats[category][user_id] = stats[category].get(user_id, 0) + 1

            # money category: track amounts
            if category == "money":
                amounts = re.findall(r"(\d+(?:[.,]\d+)?)\s*(?:€|ευρω|euro)", normalized)
                total = sum(float(a.replace(",", ".")) for a in amounts)
                if total > 0:
                    stats.setdefault("money_sum", {})
                    stats["money_sum"][user_id] = stats["money_sum"].get(user_id, 0) + total
                    print(f"{message.author.name} πρόσθεσε {total}€ (σύνολο {stats['money_sum'][user_id]}€)")

            save_data(stats)
            print(f"{message.author.name} ενεργοποίησε {category} με {used_item}")
            await handle_trigger(message.channel, category)
            break

    content = message.content.lower().strip()
    normalized_message = normalized

    # === !stats <category> ===
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

    # === !top <category> ===
    elif content.startswith("!top "):
        parts = content.split()
        if len(parts) >= 2:
            category = parts[1]
            if category in stats and stats[category]:
                sorted_users = sorted(stats[category].items(), key=lambda x: x[1], reverse=True)
                leaderboard = []
                for i, (uid, count) in enumerate(sorted_users[:3], start=1):
                    user = await get_target_user(int(uid))
                    if not user:
                        continue
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
                await message.channel.send(f"🏆 **Leaderboard για {category.upper()}:**\n" + "\n".join(leaderboard))
            else:
                await message.channel.send(f"❌ Δεν υπάρχουν δεδομένα για '{category}'.")

    # === !moneyboard ===
    elif content.startswith(("!λογιστης","!λογιστής")):
        if "money_sum" in stats and stats["money_sum"]:
            sorted_users = sorted(stats["money_sum"].items(), key=lambda x: x[1], reverse=True)
            leaderboard = []
            for i, (uid, total) in enumerate(sorted_users[:5], start=1):
                user = await get_target_user(int(uid))
                if not user:
                    continue
                leaderboard.append(f"{i}. **{user.name}** — {total:.2f}€")
            await message.channel.send(f"💰 **Ποιοι έχουν ξοδέψει τα περισσότερα:**\n" + "\n".join(leaderboard))
        else:
            await message.channel.send("📭 Δεν υπάρχουν ακόμα δεδομένα για ποσά σε ευρώ.")

    # === !categories ===
    elif content.startswith("!categories"):
        categories = ", ".join(TRACKED_GROUPS.keys())
        await message.channel.send(f"📚 Διαθέσιμες κατηγορίες: {categories}")

    # === GIF TRIGGER ===
    elif normalized_message.startswith(target_phrase):
        await message.channel.send("https://tenor.com/bh05x.gif")

    # === !removemoney @user amount ===
    elif content.startswith("!removemoney"):
        parts = content.split()
        if not message.author.guild_permissions.administrator:
            await message.channel.send("🚫 Μόνο διαχειριστές μπορούν να αφαιρέσουν χρήματα από άλλους.")
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

        await message.channel.send(
            f"💸 Αφαιρέθηκαν **{amount:.2f}€** από τον χρήστη **{target_user.name}**.\n"
            f"📉 Νέο σύνολο: **{stats['money_sum'][target_id]:.2f}€**"
        )

@client.event
async def on_ready():
    print(f"✅ Συνδέθηκε ως {client.user}")

client.run(TOKEN)
