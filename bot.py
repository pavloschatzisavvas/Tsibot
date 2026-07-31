import discord
import time
import unicodedata
import re
import os
import asyncio
import webserver
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
from discord.ext import tasks
from dotenv import load_dotenv
from pymongo import AsyncMongoClient, ReturnDocument

# === ΡΥΘΜΙΣΕΙΣ ===
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise SystemExit(
        "❌ Δεν βρέθηκε η μεταβλητή περιβάλλοντος DISCORD_TOKEN. "
        "Δημιούργησε ένα αρχείο .env (δες το .env.example) και όρισε εκεί το DISCORD_TOKEN."
    )

TARGET_USER_ID = 462250676668334081  # <-- ID χρήστη που θα γίνεται mention

FURNOS_TARGET_USER_ID = 373217412964679681
FURNOS_GIF_URL = "https://klipy.com/gifs/carlton-the-bear-bakery"

HOURLY_GIF_URL = "https://klipy.com/gifs/air-quotes-9"

FURNOS_COOLDOWN = 15 * 60  # 15 λεπτά
HOURLY_GIF_CHANNEL_ID = 1176993664371785762

webserver.keep_alive()

# === MONGODB ===
MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise SystemExit(
        "❌ Δεν βρέθηκε η μεταβλητή περιβάλλοντος MONGODB_URI. "
        "Δημιούργησε ένα αρχείο .env (δες το .env.example) και όρισε εκεί το MONGODB_URI."
    )

mongo_client = AsyncMongoClient(MONGODB_URI)
mongo_db = mongo_client["tsibot"]
stats_collection = mongo_db["stats"]

# === COOLDOWNS ===
CATEGORY_COOLDOWNS = {
    "money": 15 * 60,   # 15 λεπτά
    "χιαστι": 3 * 60    # 3 λεπτά
}
DEFAULT_COOLDOWN = 1  # αν λείπει κάποια κατηγορία

# === ΚΑΤΗΓΟΡΙΕΣ ===
TRACKED_GROUPS = {
    "money": ["💸", "💵", "cash", "λεφτά", "ευρώ", "€", "αγορά"],
    "χιαστι": ["αρχηγέ μου", "αρχηγέ", "αρχηγός", "αρχηγό","αρχηηγέ","αρχηηγός","αρχηγεε"]
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

# === TRIGGER MATCHING (word-boundary safe) ===
def trigger_matches(trigger, normalized_text):
    normalized_trigger = normalize_text(trigger)
    if re.search(r"\w", normalized_trigger, flags=re.UNICODE):
        # κανονική λέξη/φράση: απαιτούνται όρια λέξης πριν/μετά ολόκληρο το trigger
        pattern = r"(?<!\w)" + re.escape(normalized_trigger) + r"(?!\w)"
        return re.search(pattern, normalized_text, flags=re.UNICODE) is not None
    # emoji/σύμβολο (π.χ. 💸, 💵, €): απλός έλεγχος παρουσίας
    return normalized_trigger in normalized_text

# === MONGODB DATA FUNCTIONS ===
async def load_stats():
    doc = await stats_collection.find_one({"_id": "global"})
    if not doc:
        return {}
    doc.pop("_id", None)
    return doc

async def increment_stat(category, user_id, amount=1):
    await stats_collection.update_one(
        {"_id": "global"},
        {"$inc": {f"{category}.{user_id}": amount}},
        upsert=True
    )

async def update_money(user_id, amount):
    result = await stats_collection.find_one_and_update(
        {"_id": "global"},
        {"$inc": {f"money_sum.{user_id}": amount}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    return result["money_sum"][user_id]

async def remove_money(user_id, amount):
    # atomic clamp-at-zero: new value = max(0, current - amount)
    result = await stats_collection.find_one_and_update(
        {"_id": "global"},
        [
            {
                "$set": {
                    "_id": "global",
                    f"money_sum.{user_id}": {
                        "$max": [
                            0,
                            {"$subtract": [{"$ifNull": [f"$money_sum.{user_id}", 0]}, amount]}
                        ]
                    }
                }
            }
        ],
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    return result["money_sum"][user_id]

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

    # === !φουρνος ===
    if trigger_matches("!φουρνος", normalized):
        now = time.time()
        channel_id = message.channel.id
        if now - last_mention_time["furnos"][channel_id] >= FURNOS_COOLDOWN:
            last_mention_time["furnos"][channel_id] = now
            await message.channel.send(
                f"<@{FURNOS_TARGET_USER_ID}>\n{FURNOS_GIF_URL}"
            )
        return

    # --- TRIGGERS ---
    for category, triggers in TRACKED_GROUPS.items():
        matched_items = [t for t in triggers if trigger_matches(t, normalized)]
        if matched_items:
            used_item = matched_items[0]
            await increment_stat(category, user_id, 1)

            # money category: track amounts
            if category == "money":
                amounts = re.findall(r"(\d+(?:[.,]\d+)?)\s*(?:€|ευρω|euro)", normalized)
                total = sum(float(a.replace(",", ".")) for a in amounts)
                if total > 0:
                    new_sum = await update_money(user_id, total)
                    print(f"{message.author.name} πρόσθεσε {total}€ (σύνολο {new_sum}€)")

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
            data = await load_stats()
            if category in data:
                count = data[category].get(user_id, 0)
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
            data = await load_stats()
            if category in data and data[category]:
                sorted_users = sorted(data[category].items(), key=lambda x: x[1], reverse=True)
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
        data = await load_stats()
        if "money_sum" in data and data["money_sum"]:
            sorted_users = sorted(data["money_sum"].items(), key=lambda x: x[1], reverse=True)
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
        new_total = await remove_money(target_id, amount)

        await message.channel.send(
            f"💸 Αφαιρέθηκαν **{amount:.2f}€** από τον χρήστη **{target_user.name}**.\n"
            f"📉 Νέο σύνολο: **{new_total:.2f}€**"
        )

# === ΠΡΟΓΡΑΜΜΑΤΙΣΜΕΝΟ GIF (καθημερινές, 11:00-17:00, Ελλάδα) ===
last_hourly_gif_slot = None

@tasks.loop(minutes=1)
async def hourly_gif_task():
    global last_hourly_gif_slot

    now = datetime.now(ZoneInfo("Europe/Athens"))

    if now.weekday() >= 5:  # Σάββατο/Κυριακή
        return
    if not (11 <= now.hour <= 17):
        return
    if now.minute != 0:
        return

    current_slot = now.strftime("%Y-%m-%d-%H")
    if current_slot == last_hourly_gif_slot:
        return

    if HOURLY_GIF_CHANNEL_ID == 0:
        return

    try:
        channel = client.get_channel(HOURLY_GIF_CHANNEL_ID)
        if channel is None:
            channel = await client.fetch_channel(HOURLY_GIF_CHANNEL_ID)

        await channel.send(HOURLY_GIF_URL)
        last_hourly_gif_slot = current_slot
    except Exception as error:
        print(f"Hourly GIF task error: {error}")

@hourly_gif_task.before_loop
async def before_hourly_gif_task():
    await client.wait_until_ready()

@client.event
async def on_ready():
    print(f"✅ Συνδέθηκε ως {client.user}")
    if not hourly_gif_task.is_running():
        hourly_gif_task.start()

# discord.Client δεν είναι subclassed εδώ, οπότε το setup_hook (καλείται μία
# φορά πριν συνδεθεί στο gateway) περνάει ως instance attribute.
async def setup_hook():
    try:
        await mongo_client.admin.command("ping")
        print("✅ Επιτυχής σύνδεση με MongoDB")
    except Exception:
        print("❌ Αποτυχία σύνδεσης με MongoDB. Έλεγξε το MONGODB_URI στο .env.")
        raise

client.setup_hook = setup_hook

try:
    client.run(TOKEN)
finally:
    asyncio.run(mongo_client.close())
