# exchange-ovh — skill Claude Code pour boîte Exchange OVH

Gestion complète d'une boîte email **Exchange hébergée chez OVH** depuis Claude Code, plus un **récap 3×/jour** envoyé sur WhatsApp / Telegram / email.

## Pourquoi EWS et pas Microsoft Graph

OVH héberge des tenants Exchange on-premise : **Graph n'est pas disponible** (réservé à Microsoft 365). EWS (Exchange Web Services, SOAP) reste le seul protocole couvrant mail + calendrier + contacts + règles. Ce skill s'appuie sur [`exchangelib`](https://github.com/ecederstrand/exchangelib), la lib Python la plus mature pour EWS.

## Installation

```bash
cd .claude/skills/exchange-ovh
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# édite .env avec tes identifiants
python -m scripts.client --test
```

Si la connexion échoue, lis `references/ews-ovh.md` — les plateformes OVH n'utilisent pas toutes le même serveur EWS.

## Utilisation (via Claude Code)

Claude détecte automatiquement ce skill via sa description. Demande simplement :

- « Montre-moi mes mails non lus »
- « Cherche les mails de Dupont des 7 derniers jours »
- « Réponds à ce mail en disant que c'est OK »
- « Range tous les mails d'Amazon dans un dossier Commandes »
- « Quels sont mes RDV demain ? »
- « Envoie-moi un récap maintenant sur WhatsApp »

Claude lancera les scripts sous le capot. Pour un appel direct sans Claude, voir le bloc d'exemples dans `SKILL.md`.

## Récap automatique 3×/jour

Le workflow `.github/workflows/exchange-recap.yml` tourne 3×/jour et envoie le récap sur le canal configuré. Pour l'activer :

1. Pousse ce repo sur GitHub.
2. Settings → Secrets and variables → Actions → ajoute :
   - `OVH_EMAIL`, `OVH_PASSWORD`, `OVH_EWS_SERVER`
   - `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`, `NOTIFY_WHATSAPP_TO`
   - (ou) `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
   - (ou) `NOTIFY_EMAIL_TO`
3. Actions → "Exchange OVH recap" → Run workflow pour tester.
4. Pour ajuster les horaires, édite `schedule.cron` (UTC) dans le workflow.

## Sécurité

- `.env` est dans `.gitignore` — ne jamais committer.
- Les secrets GitHub Actions sont chiffrés côté GitHub.
- Utilise un mot de passe d'application OVH dédié si ton plan le permet.

## Structure

```
.claude/skills/exchange-ovh/
├── SKILL.md                  # Entrée discoverable par Claude Code
├── README.md                 # Ce fichier
├── requirements.txt
├── .env.example
├── .gitignore
├── scripts/
│   ├── client.py             # Wrapper EWS + helpers communs
│   ├── read_mail.py          # inbox / unread / search / show
│   ├── send_mail.py          # send / reply / forward
│   ├── organize.py           # folders / mkdir / move / mark / categorize / delete
│   ├── calendar.py           # list / create (avec invitations)
│   ├── contacts.py           # list / search / create
│   ├── notifier.py           # WhatsApp (Twilio) / Telegram / email
│   └── recap.py              # orchestration + formatage du résumé
└── references/
    ├── ews-ovh.md            # spécificités OVH Exchange
    ├── notifiers.md          # setup Twilio / Telegram
    └── troubleshooting.md    # erreurs courantes
```
