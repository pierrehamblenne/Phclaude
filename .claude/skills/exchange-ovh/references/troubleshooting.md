# Troubleshooting

## `UnauthorizedError` / 401

- Vérifie que `OVH_EMAIL` contient l'adresse **complète** (pas juste le prénom).
- Teste le login dans le [webmail OVH](https://www.ovh.com/fr/emails/) d'abord.
- Si ton plan OVH Exchange a l'option "mot de passe d'application", génères-en un dédié.

## `AutoDiscoverFailed` / redirections en boucle

Le skill force `autodiscover=False`. Si tu vois quand même des erreurs autodiscover, c'est que `OVH_EWS_SERVER` est vide — renseigne-le explicitement dans `.env`.

## `SSLError` / certificat

- Teste les autres endpoints (`ex3.mail.ovh.net`, `mail.ovh.net`).
- En dernier recours pour debug local (jamais en prod) :
  ```
  OVH_SKIP_TLS_VERIFY=1
  ```
  Ne pas commiter cette valeur.

## `ErrorServerBusy` / throttling

OVH limite les requêtes EWS (~60/min). `exchangelib` retry automatiquement avec backoff. Pour les gros imports, ajouter `--limit 20` et boucler manuellement.

## Le récap GitHub Actions ne part pas

1. Vérifie que les secrets sont bien définis (Settings → Secrets and variables → Actions).
2. Regarde les logs du run : `python -m scripts.recap` affiche le message formaté même en cas d'échec du notifier.
3. Vérifie que la sandbox WhatsApp Twilio est toujours active (expiration 72h si tu n'envoies pas depuis ton WhatsApp).

## `ErrorFolderNotFound` quand tu cibles un sous-dossier

Les chemins de `organize move --to` sont relatifs à l'Inbox par défaut. Pour un dossier hors Inbox (ex. `Archive/Perso`) indique le chemin complet tel qu'il apparaît dans Outlook.

## Performances

- Le premier appel est lent (autodiscover désactivé mais `exchangelib` fait un GetFolder complet pour cacher l'arborescence).
- Les appels suivants dans le même processus sont rapides.
- Si tu lances souvent des scripts one-shot, envisage un petit serveur long-running (pas inclus ici).
