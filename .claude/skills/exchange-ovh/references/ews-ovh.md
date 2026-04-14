# OVH Exchange — spécificités EWS

## Endpoints EWS possibles

OVH ne publie pas d'Autodiscover accessible publiquement sur tous les plans. Il faut passer le serveur explicitement. Par ordre de fréquence :

1. `ex.mail.ovh.net` — plateformes mutualisées standard
2. `ex3.mail.ovh.net` — clusters récents
3. `mail.ovh.net` — certains hébergements Exchange
4. `exchange.<domaine-client>` — plans Private Exchange dédiés

URL EWS complète : `https://<server>/EWS/Exchange.asmx`

Pour trouver ton endpoint exact :
1. Espace client OVH → Emails → onglet Exchange → "Informations générales".
2. La ligne « Serveur entrant » / « Serveur Autodiscover » te donne l'hôte.

## Authentification

- Basic auth (username = full email, password = mot de passe du compte).
- Pas d'OAuth sur OVH Exchange.
- Si ton plan Exchange supporte les **mots de passe d'application**, en créer un dédié à ce skill et l'utiliser à la place du mot de passe principal.

## Limitations connues

- **Throttling EWS** : OVH applique des limites (souvent ~60 requêtes/min par user).
  `exchangelib` retry automatiquement avec backoff.
- **Autodiscover** : désactivé dans ce skill (`autodiscover=False`) car il échoue souvent côté OVH.
- **Pièces jointes** : limite de ~25 MB par mail.
- **Catégories / labels** : stockées côté serveur, visibles dans Outlook mais pas dans le webmail OVH ancien.

## Test rapide hors skill

```python
from exchangelib import Account, Credentials, Configuration, DELEGATE

creds = Credentials("user@domain.fr", "password")
cfg = Configuration(server="ex.mail.ovh.net", credentials=creds)
acc = Account("user@domain.fr", config=cfg, autodiscover=False, access_type=DELEGATE)
print(acc.inbox.total_count, acc.inbox.unread_count)
```
