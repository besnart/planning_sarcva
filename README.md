# Planning médical semi-automatisé — SARCVA

Application web de planning d'un service de chirurgie cardiaque (réanimation, blocs,
CPA, consultation PR, régulation/VPA, KT, astreintes, AI, CA), avec attribution
automatique des postes par quadrimestre et modification manuelle possible ensuite.

**Le planning est accessible en lecture de partout, sans connexion** (voir
`PLANNING_PUBLIC_READ` ci-dessous pour restreindre).

## Installation et lancement

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser          # compte d'administration Django
DEMO_PASSWORD=... python manage.py init_demo --annee 2026 --quadrimestre 1
python manage.py runserver 0.0.0.0:8000   # écoute sur toutes les interfaces
```

Ouvrir http://localhost:8000/ — la page d'accueil redirige vers le mois courant.

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
