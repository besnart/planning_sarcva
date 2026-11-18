# Planning médical semi-automatisé — SARCVA

Application web de planning d'un service de chirurgie cardiaque (réanimation, blocs,
CPA, consultation PR, régulation/VPA, KT, astreintes, AI, CA), avec attribution
automatique des postes par quadrimestre et modification manuelle possible ensuite.

**Le planning est accessible en lecture de partout, sans connexion** (voir
`PLANNING_PUBLIC_READ` ci-dessous pour restreindre).

## Installation et lancement

### Obtenir une URL publique (hébergement, sans rien installer localement)

Deux options, au choix :

**Option A — GitHub Codespaces (le plus simple, 100 % clics).** Sur la page de la
branche, bouton vert **Code → Codespaces → Create codespace**. Le conteneur démarre
tout seul (`.devcontainer/` : install, migrations, données de démo, serveur sur le
port 8000). Ouvrez l'onglet **Ports**, clic droit sur le port 8000 → **Public**, puis
partagez l'URL `https://<codespace>-8000.app.github.dev` (le planning est public en
lecture ; comptes de démo `admin`/`demo`, `bernard`/`demo`). Nécessite un compte
GitHub (quotas Codespaces gratuits inclus).

**Option B — Mistral App (URL de production sur l'infrastructure Mistral).** Le dépôt
contient déjà `mistral.json` + `deploy/Dockerfile` + `deploy/entrypoint.sh` (base
Postgres managée fournie automatiquement via `DATABASE_URL`). Prérequis : fusionner la
PR sur `main`, connecter GitHub à votre compte Mistral et installer
[l'app GitHub Mistral](https://github.com/apps/mistralai) sur ce dépôt, et un plan
incluant Apps. Puis, depuis un clone du dépôt :

```bash
mistral login        # une seule fois, validation dans le navigateur
mistral deploy       # construit le commit poussé sur main et publie l'URL
```

L'URL publique est affichée à la fin du deploy. Secrets à définir dans l'onglet
**Secrets** de l'app dans Studio : `DJANGO_SECRET_KEY` (obligatoire), `SEED_DEMO=1` +
`DEMO_PASSWORD` (données de démo), `CSRF_TRUSTED_ORIGINS=https://<url-de-l-app>`.

**Option C — votre propre serveur (VPS/Docker)** : `docker build -t planning-sarcva .`
puis `docker run -p 8000:8000 -e DJANGO_SECRET_KEY=... -e DJANGO_DEBUG=0
-e CSRF_TRUSTED_ORIGINS=https://votre-domaine planning-sarcva` (voir `deploy/Dockerfile` ;
`requirements-hosting.txt` ajoute gunicorn + Postgres via `DATABASE_URL`).

### Version hors ligne téléchargeable, SANS synchronisation

L'exécutable des releases (voir ci-dessous) est **strictement hors ligne** : base
SQLite locale (`db.sqlite3` à côté de l'exe), **aucun appel réseau sortant, aucune
synchronisation** avec une version en ligne. Pour transférer ponctuellement des
données d'une instance à l'autre, utiliser l'export/import **manuel** :

```bash
python manage.py exporter_donnees snapshot.json         # sur l'instance en ligne
python manage.py importer_donnees snapshot.json --vider # dans l'exe hors ligne
```

### Sans aucune ligne de commande (100 % visuel)

1. Télécharger le code de la branche : ouvrir
   [la page de la branche](https://github.com/besnart/planning_sarcva/tree/vibe/planning-semi-auto-69dd08)
   puis bouton vert **Code → Download ZIP** (ou directement
   [le ZIP de la branche](https://github.com/besnart/planning_sarcva/archive/refs/heads/vibe/planning-semi-auto-69dd08.zip)),
   puis dézipper. (Sur `main`, le ZIP ne contient pas encore l'application tant que la PR n'est pas fusionnée.)
2. Installer **Python 3.12+** si absent : [python.org](https://www.python.org/downloads/)
   en cochant **« Add python.exe to PATH »** à l'installation.
3. Double-cliquer sur **`start.bat`** (Windows), **`start.command`** (macOS) ou
   **`start.sh`** (Linux) : le lanceur installe les dépendances, crée la base et un
   jeu de données de démonstration, démarre le serveur, puis **ouvre le navigateur
   uniquement quand le serveur répond**.
4. Tout se teste ensuite au clic dans le navigateur (voir « Scénarios de test »).
   Le mot de passe des comptes de démo vaut `demo` par défaut (variable
   `DEMO_PASSWORD` à définir avant le lancement pour le changer).

Comptes de démo : `admin` (Super Administrateur), `bernard`, `caron` (Utilisateurs).

**Dépannage Codespaces** : si l'aperçu intégré de VS Code affiche `ERR_BLOCKED_BY_RESPONSE`,
c'est l'en-tête `X-Frame-Options: DENY` qui bloque le chargement en iframe. Deux solutions :
ouvrir l'URL dans un **vrai onglet de navigateur** (onglet Ports → icône globe « Open in Browser",
ou copier l'URL publique dans Opera/Chrome), ou reconstruire le Codespace après ce commit
(le devcontainer définit `X_FRAME_OPTIONS=""` pour autoriser l'aperçu en démo ; en production,
garder `DENY`).

**Dépannage** : laissez la fenêtre noire (console) ouverte — la fermer arrête le serveur.
Si le navigateur affiche « site inaccessible / ERR_CONNECTION_REFUSED », attendez le
message « ouverture du navigateur » dans la console (le navigateur ne s'ouvre plus
avant que le serveur ne réponde). Si le pare-feu Windows bloque, autorisez Python.
Si le port 8000 est occupé, relancez avec `PORT=8001` (dans la console :
`set PORT=8001` puis `start.bat` sous Windows).

### Version autonome : AUCUN Python requis (recommandé pour tester)

Un exécutable prêt à l'emploi est construit automatiquement par GitHub Actions à
chaque push sur la branche et publié dans les **Releases** du dépôt :

- [planning-sarcva.exe (Windows)](https://github.com/besnart/planning_sarcva/releases/tag/app-windows-latest)
- [planning-sarcva (Linux)](https://github.com/besnart/planning_sarcva/releases/tag/app-linux-latest)

Utilisation : téléchargez l'exécutable, double-cliquez dessus. Une console s'ouvre
(installation de la base + données de démo la première fois), puis **le navigateur
s'ouvre tout seul** sur http://localhost:8000/ quand le serveur répond. Laissez la
console ouverte (la fermer arrête le serveur). Les données vivent dans `db.sqlite3`
à côté de l'exécutable. Comptes de démo : `admin` / `demo`, `bernard` / `demo`,
`caron` / `demo`. Le build se relance aussi manuellement depuis l'onglet **Actions**
(« Build de l'application autonome » → *Run workflow*).

### En ligne de commande (avec Python)

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser          # compte d'administration Django
DEMO_PASSWORD=... python manage.py init_demo --annee 2026 --quadrimestre 1
python manage.py runserver 0.0.0.0:8000   # écoute sur toutes les interfaces
```

Ouvrir http://localhost:8000/ — la page d'accueil redirige vers le mois courant.

### Scénarios de test (tout au clic, dans le navigateur)

| À tester | Où | Résultat attendu |
|---|---|---|
| Lecture de partout | `/planning/2026/1/` sans être connecté | planning visible, aucun bouton d'édition |
| Stats protégées | `/stats/` en anonyme | redirection vers la page de connexion |
| Rôles | connexion `bernard` puis `/praticiens/`, `/accreditations/` | 403 ; `/stats/`, `/disponibilites/` OK |
| Édition | connexion `admin`, bouton **Modifier** sur le planning | listes de praticiens, fermetures, étiquettes |
| Règle CA | poster quelqu'un en CA puis ailleurs le même jour | message « règle obligatoire » |
| Vendredi = dimanche | changer la garde du vendredi | le dimanche suit automatiquement |
| Génération auto | bouton **Générer le quadrimestre** | planning rempli, AI/CA conservés |
| Stats | `/stats/?echelle=quadrimestre&annee=2026&quadrimestre=1` | tableaux en journées (0,5 par demi-journée) |
| Données en tableaux | `/admin/` (compte `admin`) | praticiens, affectations, fermetures éditables visuellement |

Variables d'environnement :

| Variable | Rôle | Défaut |
|---|---|---|
| `DJANGO_SECRET_KEY` | clé secrète (obligatoire en production) | clé de dev |
| `DJANGO_DEBUG` | mode debug (`1`/`0`) | `1` |
| `DJANGO_ALLOWED_HOSTS` | hôtes autorisés (séparés par des virgules) | `*` |
| `PLANNING_PUBLIC_READ` | `1` = planning lisible sans connexion, de partout | `1` |
| `DEMO_PASSWORD` | mot de passe des comptes créés par `init_demo` | aucun |

Pour un déploiement réel : `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY` unique,
`DJANGO_ALLOWED_HOSTS` restreint au nom de domaine, servi derrière HTTPS
(nginx/Apache + `gunicorn config.wsgi`). Mettre `PLANNING_PUBLIC_READ=0`
pour exiger au minimum un compte Visionnage pour lire le planning.

## Niveaux d'accréditation

| Niveau | Droits |
|---|---|
| **Visionnage** | Voir le planning. Ni statistiques, ni modification. |
| **Utilisateur** | + statistiques, + déclarer ses disponibilités/indisponibilités (lui seul). |
| **Administrateur** | + modifier les postages, générer le planning, modifier les règles de postage (fermetures de sections, étiquettes de blocs) et la liste des praticiens. |
| **Super Administrateur** | + attribuer les niveaux d'accréditation. |

L'attribution des niveaux se fait dans **Accréditations** (super admin seul).

## Pages

- `/planning/<annee>/<mois>/` — planning du mois. Chaque mois commence un lundi et
  finit un dimanche (déborde éventuellement sur les mois voisins). Menu déroulant
  année/mois ; les semaines se parcourent en **scrollant latéralement**. Lecture
  publique. En mode édition (bouton *Modifier*, admin) : chaque poste devient une
  liste déroulante de praticiens, les sections peuvent être fermées/réouvertes
  par jour, les étiquettes de blocs sont modifiables, et le bouton
  **Générer le quadrimestre** lance l'attribution automatique.
- `/stats/` — statistiques par praticien, par poste et total, exprimées en
  **journées** (vacation matin = 0,5, après-midi = 0,5) et en heures. Échelle
  **mois / quadrimestre / année**. Utilisateur et plus.
- `/praticiens/` — liste des praticiens avec quote-part (%) ; 100 % = **1747 h/an**.
  Types « P » et « L » (les « L » sont privilégiés sur les blocs — règle idéale) ;
  étiquette « DJ ». Administrateur et plus.
- `/disponibilites/` — disponibilités/indisponibilités du compte connecté
  (matin / après-midi / journée), prises en compte par la génération.
- `/accreditations/` — niveaux d'accréditation. Super administrateur seul.
- `/admin/` — administration Django classique.

## Structure journalière (schéma implémenté)

Tous les jours : **AI** (6 vacations : 3 matin + 3 après-midi, postées manuellement)
et **CA** (6 vacations, postées manuellement).

Semaine (hors samedi, dimanche, jours fériés — calculés automatiquement) :

- **Réanimation** : réa 1, 2, 3 (1 personne, journée 10 h) ; réa 4 (1 personne,
  demi-journée 5 h) ; réa DJ (réservé aux praticiens étiquetés DJ) ; garde
  (même personne que réa 1, nuit 14 h).
- **Blocs 1 et 6** : même personne matin + après-midi (5,5 h chacune).
- **Bloc 2** : même personne matin/après-midi (5,5 h).
- **Bloc 3** : deux personnes différentes ; l'après-midi est la personne d'astreinte.
- **Bloc 4** : même personne ; le mercredi une personne avec étiquette **CEC**,
  les autres jours aucune personne et étiquette **CONGENITAL**.
- **Bloc 5** : même personne matin/après-midi.
- Étiquettes de blocs : CEC, LASER, CONGENITAL, STRUCTUREL, VASCULAIRE.
- **CPA** matin/après-midi (2 personnes, 4 h) ; **Consultation PR** le matin =
  même personne que CPA après-midi (4 h) ; **Régulation/VPA** et **KT**
  (même personne les deux vacations) ; **Astreinte** = bloc 3 après-midi (6 h).
- Certaines sections peuvent être **fermées** pour un jour : aucune personne postée.

Week-ends et jours fériés : **garde 24 h** et **astreinte 12 h**.

## Règles d'attribution

Postes **AI et CA saisis manuellement** ; le reste est généré par quadrimestre
(**Q1 = janv.-avr., Q2 = mai-août, Q3 = sept.-déc.**) via le bouton dédié.
Après génération, toute **modification manuelle** est possible (admin).

Règles **obligatoires** (jamais violées, y compris en manuel) :

- une personne en CA n'est postée nulle part ailleurs ce jour ;
- une personne en AI matin/après-midi n'est pas postée sur un créneau équivalent
  le même jour ;
- personne n'est posté le lendemain d'une garde ou d'une astreinte ;
- garde et astreinte du **vendredi = mêmes personnes le dimanche** ;
- réanimation DJ réservée aux praticiens étiquetés DJ ;
- une seule vacation de travail par personne et par jour (hors postes liés).

Règles **idéales** (best effort) :

- répartition homogène selon la quote-part (100 % = 1747 h/an) ;
- praticiens « L » privilégiés sur les blocs ;
- réanimation des jours précédant/suivant les gardes de week-end ;
- réanimation 4 la semaine précédant une garde.

Les statistiques alimentent l'équité : la génération équilibre les heures
restant dues par rapport à la quote-part de chacun.

## Commandes utiles

```bash
python manage.py test planning                 # 30 tests (règles, permissions, génération)
DEMO_PASSWORD=... python manage.py init_demo   # données de démo + planning généré
python manage.py createsuperuser               # puis lier le compte à un praticien
                                               # et passer son niveau à Super Administrateur
```

## Stack

Python 3.12 + Django 5.2 (voir `requirements.txt`), SQLite par défaut,
templates Django + CSS statique, aucun service externe requis.
