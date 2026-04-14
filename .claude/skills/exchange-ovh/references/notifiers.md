# Setup des notifieurs

## Option 1 — WhatsApp via Twilio (recommandé)

1. Crée un compte Twilio (free trial avec crédits).
2. Console → Messaging → Try it out → **Send a WhatsApp message**.
3. Rejoins la sandbox en envoyant le code "join xxx-yyy" au numéro affiché (+1 415 523 8886) depuis ton WhatsApp.
4. Note :
   - `TWILIO_ACCOUNT_SID` (Console → Account info)
   - `TWILIO_AUTH_TOKEN` (Console → Account info)
   - `TWILIO_WHATSAPP_FROM = whatsapp:+14155238886` (numéro sandbox)
   - `NOTIFY_WHATSAPP_TO = whatsapp:+33XXXXXXXXX` (ton numéro, avec indicatif pays)

**Pour la prod** : demande l'activation d'un numéro WhatsApp Business dédié dans Twilio Console (payant, approbation Meta requise). Change alors `TWILIO_WHATSAPP_FROM` vers ton numéro validé.

Coût approximatif : ~0,005 $ / message sandbox, ~0,05 € / message business EU.

## Option 2 — Telegram (gratuit, simple)

1. Sur Telegram, ouvre une conversation avec [@BotFather](https://t.me/BotFather).
2. `/newbot` → donne un nom → `/token` pour récupérer le token.
3. Envoie un message à ton bot pour l'activer.
4. Récupère ton `chat_id` via [@userinfobot](https://t.me/userinfobot) ou en visitant :
   `https://api.telegram.org/bot<TOKEN>/getUpdates` (cherche `chat.id`).
5. Remplis `TELEGRAM_BOT_TOKEN` et `TELEGRAM_CHAT_ID`.

Avantages : gratuit, illimité, pas d'approbation. Inconvénient : ce n'est pas WhatsApp.

## Option 3 — Email (fallback)

Définir `NOTIFY_EMAIL_TO` = adresse destinataire (peut être ta propre boîte OVH ou une adresse perso Gmail). Le récap est envoyé depuis ta boîte Exchange elle-même.

## Sélection du canal

Le recap lit `NOTIFY_CHANNEL` ou l'argument `--notify`. Valeurs : `auto` (défaut), `whatsapp`, `telegram`, `email`, `none`.

`auto` choisit dans l'ordre de préférence : WhatsApp → Telegram → email → none.
