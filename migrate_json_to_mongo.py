import asyncio
import json
import os

from dotenv import load_dotenv
from pymongo import AsyncMongoClient

DATA_FILE = "emoji_stats.json"


async def migrate():
    load_dotenv()
    mongodb_uri = os.getenv("MONGODB_URI")

    if not mongodb_uri:
        print("❌ Δεν βρέθηκε η μεταβλητή περιβάλλοντος MONGODB_URI. Δημιούργησε ένα αρχείο .env (δες το .env.example).")
        return

    if "<db_password>" in mongodb_uri:
        print("❌ Το MONGODB_URI περιέχει ακόμα το placeholder <db_password>. Αντικατέστησέ το με τον πραγματικό κωδικό στο .env πριν τρέξεις το migration.")
        return

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            local_stats = json.load(f)
    except FileNotFoundError:
        print(f"❌ Δεν βρέθηκε το αρχείο {DATA_FILE}.")
        return
    except json.JSONDecodeError as e:
        print(f"❌ Το {DATA_FILE} δεν είναι έγκυρο JSON: {e}")
        return

    document = {"_id": "global", **local_stats}

    mongo_client = AsyncMongoClient(mongodb_uri)
    try:
        await mongo_client.admin.command("ping")

        # replace_one με upsert=True: ασφαλές να τρέξει ξανά χωρίς να δημιουργήσει διπλότυπα.
        await mongo_client["tsibot"]["stats"].replace_one(
            {"_id": "global"},
            document,
            upsert=True
        )
        print(f"✅ Η migration ολοκληρώθηκε επιτυχώς. Το {DATA_FILE} παρέμεινε ως έχει (backup).")
    except Exception:
        print("❌ Η migration απέτυχε. Έλεγξε ότι το MONGODB_URI στο .env είναι σωστό.")
    finally:
        await mongo_client.close()


if __name__ == "__main__":
    asyncio.run(migrate())
