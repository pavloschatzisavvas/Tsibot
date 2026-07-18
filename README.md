# Tsibot

Το bot αποθηκεύει πλέον τα στατιστικά του σε **MongoDB Atlas** αντί για το τοπικό `emoji_stats.json`. Το Discord token και το MongoDB URI διαβάζονται από environment variables (`.env`), ώστε να μην υπάρχουν secrets μέσα στον κώδικα.

## Εγκατάσταση

```
python -m pip install -r requirements.txt
```

## Ρύθμιση .env

1. Αντίγραψε το `.env.example` σε `.env`:
   ```
   cp .env.example .env
   ```
2. Άνοιξε το `.env` και αντικατέστησε το `<db_password>` με τον πραγματικό κωδικό του χρήστη MongoDB Atlas (`pavlosx`), ώστε η γραμμή `MONGODB_URI` να έχει τη μορφή:
   ```
   MONGODB_URI=mongodb+srv://pavlosx:ΤΟ_ΠΡΑΓΜΑΤΙΚΟ_ΣΟΥ_PASSWORD@tsibotcluster.he3zim8.mongodb.net/?appName=TsibotCluster
   ```
3. Αντικατέστησε το `<discord_bot_token>` με το πραγματικό Discord bot token (από το [Discord Developer Portal](https://discord.com/developers/applications) → το bot σου → Bot → Token):
   ```
   DISCORD_TOKEN=το_πραγματικό_σου_token
   ```

Το `.env` δεν πρέπει ποτέ να ανέβει σε git (είναι ήδη στο `.gitignore`). Στο Render (ή όποιο hosting), τα ίδια δύο variables (`MONGODB_URI`, `DISCORD_TOKEN`) πρέπει να οριστούν από το dashboard του hosting ως Environment Variables.

## Migration παλιών δεδομένων (μία φορά)

Αν υπάρχουν ήδη δεδομένα στο `emoji_stats.json`, μετέφερέ τα στο MongoDB:

```
python migrate_json_to_mongo.py
```

Το script διαβάζει το `emoji_stats.json`, το εισάγει/ενημερώνει στο document με `_id: "global"` στη βάση `tsibot` / collection `stats`, και δεν διαγράφει το αρχείο. Μπορεί να τρέξει ξανά με ασφάλεια χωρίς να δημιουργήσει διπλότυπα.

Σημείωση: μετά από επιτυχημένη migration, το `emoji_stats.json` παραμένει στο project μόνο ως backup — το bot δεν το διαβάζει ούτε το ενημερώνει πλέον.

## Εκκίνηση του bot

```
python bot.py
```

Σε επιτυχή σύνδεση με τη Mongo θα δεις στο log:
```
✅ Επιτυχής σύνδεση με MongoDB
```

## Έλεγχος δεδομένων στο MongoDB Atlas

Στο Atlas UI (ή με `mongosh`), δες τη βάση `tsibot`, collection `stats`, document με `_id: "global"` — εκεί βρίσκονται όλες οι κατηγορίες στατιστικών (π.χ. `money`, `χιαστι`, `money_sum`) ανά χρήστη.
