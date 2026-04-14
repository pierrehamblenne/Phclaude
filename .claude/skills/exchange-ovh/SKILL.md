---
name: exchange-ovh
description: Gère une boîte email Exchange hébergée chez OVH via EWS (lire, chercher, envoyer, répondre, transférer, organiser en dossiers, calendrier, contacts) et produit des récaps programmables envoyés sur WhatsApp/Telegram/email. Invoque ce skill quand l'utilisateur demande de lire/envoyer/trier/organiser ses mails Exchange OVH, consulter son agenda, gérer ses contacts, ou configurer des récaps périodiques de sa boîte.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Exchange OVH — Skill de gestion de boîte mail

Ce skill parle à une boîte **Exchange hébergée chez OVH** via **EWS** (Exchange Web Services), la seule API complète supportée par cet hébergeur (Microsoft Graph n'est dispo que sur Microsoft 365). Il couvre mail, calendrier, contacts, et produit des récaps automatiques envoyés sur WhatsApp (Twilio), Telegram ou email.

## Quand utiliser ce skill

- L'utilisateur veut **lire / chercher / trier** ses mails Exchange OVH.
- L'utilisateur veut **envoyer, répondre, transférer** un mail.
- L'utilisateur veut **organiser** sa boîte (dossiers, déplacer, marquer lu/non lu, catégories).
- L'utilisateur veut consulter son **agenda** ou gérer ses **contacts**.
- L'utilisateur veut des **récaps programmés** (3×/jour par défaut) sur WhatsApp / Telegram / email.
- L'utilisateur demande de configurer/modifier l'automatisation GitHub Actions du récap.

## Configuration (à faire une fois)

1. Copier `.env.example` vers `.env` à la racine du skill et remplir :
   - `OVH_EMAIL` : adresse complète (ex. `prenom.nom@exemple.fr`)
   - `OVH_PASSWORD` : mot de passe du compte Exchange OVH (ou mot de passe d'application)
   - `OVH_EWS_SERVER` : par défaut `ex.mail.ovh.net` (peut varier : `mail.ovh.net`, `ex3.mail.ovh.net` selon la plateforme)
   - Optionnel pour WhatsApp : `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`, `NOTIFY_WHATSAPP_TO`
   - Optionnel pour Telegram : `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
   - Optionnel pour email fallback : `NOTIFY_EMAIL_TO`
2. Installer les deps : `pip install -r .claude/skills/exchange-ovh/requirements.txt`
3. Tester la connexion : `python -m scripts.client --test` (depuis le dossier du skill)

## Utilisation (lignes de commande disponibles)

Depuis `/home/user/Phclaude/.claude/skills/exchange-ovh/` :

```bash
# Lire / rechercher
python -m scripts.read_mail inbox --limit 20
python -m scripts.read_mail search --query "facture" --since 7d
python -m scripts.read_mail show --id <item_id>
python -m scripts.read_mail unread

# Envoyer / répondre / transférer
python -m scripts.send_mail send --to a@b.fr --subject "Hello" --body "..."
python -m scripts.send_mail reply --id <item_id> --body "..." [--all]
python -m scripts.send_mail forward --id <item_id> --to c@d.fr --body "..."

# Organiser
python -m scripts.organize folders                        # lister dossiers
python -m scripts.organize mkdir --name "Factures" --parent Inbox
python -m scripts.organize move --id <item_id> --to "Factures"
python -m scripts.organize mark --id <item_id> --read/--unread
python -m scripts.organize categorize --id <item_id> --categories "Perso,Urgent"

# Calendrier
python -m scripts.calendar list --since today --until 7d
python -m scripts.calendar create --subject "RDV" --start "2026-04-15T10:00" --duration 30 --attendees a@b.fr

# Contacts
python -m scripts.contacts list --limit 50
python -m scripts.contacts search --query "Dupont"
python -m scripts.contacts create --name "Jean Dupont" --email jean@example.fr

# Récap (manuel ou via cron GitHub Actions)
python -m scripts.recap --window since-last-recap --notify whatsapp
```

## Workflow typique pour Claude

1. **Lire la demande utilisateur** et déterminer l'opération (read/send/organize/calendar/contacts/recap).
2. **Vérifier `.env`** : si `OVH_EMAIL` manquant, guider l'utilisateur pour la configuration.
3. **Lancer le script approprié** en mode JSON (`--json`) pour parser proprement la sortie.
4. **Résumer le résultat** en langage naturel à l'utilisateur.
5. Pour les **actions destructives** (suppression, move massif, envoi de mail), **confirmer** avant exécution.

## Automatisation des récaps 3×/jour

Le fichier `.github/workflows/exchange-recap.yml` lance `scripts/recap.py` 3× par jour (08:00, 13:00, 18:00 Europe/Paris). Il envoie un résumé des nouveaux mails (expéditeur, sujet, 1 ligne d'aperçu, priorité détectée) sur le canal configuré (WhatsApp Twilio par défaut, sinon Telegram, sinon email).

Pour changer la fréquence, éditer le champ `schedule.cron` dans le workflow.

Les secrets nécessaires sur GitHub (Settings → Secrets and variables → Actions) :
`OVH_EMAIL`, `OVH_PASSWORD`, `OVH_EWS_SERVER`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`, `NOTIFY_WHATSAPP_TO` (ou équivalents Telegram).

## Références

- `references/ews-ovh.md` : détails plateforme OVH Exchange (serveurs, limitations)
- `references/notifiers.md` : setup Twilio WhatsApp & Telegram bot
- `references/troubleshooting.md` : erreurs courantes (autodiscover, TLS, throttling)

## Sécurité

- **Jamais** committer `.env` (dans `.gitignore`).
- Préférer un **mot de passe d'application** dédié côté OVH quand possible.
- Les secrets GitHub Actions sont chiffrés — ne jamais les echo dans les logs.
