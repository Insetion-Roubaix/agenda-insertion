# Agenda de l'insertion

Récupère chaque jour les évènements emploi de l'API **Mes évènements emploi**
(francetravail.io), les trie par filtres et par mots-clés, puis publie :

- une **page web** de consultation (recherche par mot-clé, statut, type, période) ;
- un **flux d'agenda `agenda.ics`** auquel on s'abonne depuis Outlook, Google
  Agenda, Apple ou un téléphone.

Le projet n'utilise que la bibliothèque standard de Python 3.11+ (plus `tzdata`).

## Ce qui se règle sans toucher au code

| Fichier | Rôle |
|---|---|
| `config/sources.toml` | Sources actives et **filtres envoyés à l'API** (départements, public, type, rayon autour d'un point…) |
| `config/regles.toml` | **Tri par mots-clés** : à inclure, à exclure, à vérifier |
| `config/cibles.toml` | Sorties (nom du calendrier, titre de la page…) |

## Pour les utilisateurs de Windows : les fichiers à double-cliquer

Ne double-cliquez pas sur `lancer.py` : la fenêtre s'ouvre et se referme avant
que vous ayez le temps de lire quoi que ce soit. Utilisez plutôt :

| Fichier | Ce qu'il fait |
|---|---|
| `demo.bat` | Crée une démonstration avec des évènements fictifs et **ouvre la page** dans votre navigateur |
| `tester_api.bat` | Premier contact avec la vraie API (zone de `config/sources.toml`) : ouvre le Bloc-notes pour vos identifiants la première fois, puis enregistre `reponse_brute.json` |
| `mise_a_jour.bat` | Récupère les vrais évènements et ouvre la page `docs\index.html` |

Ces fichiers installent d'eux-mêmes la petite extension `tzdata` (la liste des
fuseaux horaires, absente de Windows). Si vous préférez l'invite de commandes :

```
python -m pip install tzdata
python lancer.py --demo
```

## Essayer tout de suite (sans accès à l'API)

Double-cliquez sur `demo.bat`, ou lancez `python lancer.py --demo`.
Cela crée `demo\index.html` (la page) et `demo\agenda.ics` (le flux d'agenda)
à partir d'évènements fictifs. Le dossier `demo` n'apparaît qu'une fois la
commande terminée avec succès.

## Première utilisation avec la vraie API

1. **Vos identifiants** : au premier lancement de `tester_api.bat`, le Bloc-notes s'ouvre
   sur le fichier `identifiants.txt`. Collez l'identifiant et la clé secrète de votre
   application francetravail.io après les signes `=`, enregistrez, fermez.
   Le programme retire tout seul les espaces ou guillemets collés par erreur.
   Ce fichier reste sur votre ordinateur : ne l'envoyez à personne.
2. **La zone** : `config/sources.toml` est réglé sur Roubaix + 15 km. Pour la changer,
   modifiez `latitude`, `longitude` et `rayon` (ou utilisez `departements`), avec le Bloc-notes.
3. Le test affiche le nombre de caractères lus pour l'identifiant et la clé, récupère
   **tous** les évènements de la période, affiche un bilan (nombre d'évènements par type,
   par ville et par modalité) et enregistre `reponse_brute.json` : ce fichier permet de
   vérifier le tri et d'ajuster les règles.
4. Double-cliquez sur `mise_a_jour.bat` pour le programme complet
   (ou `python lancer.py`, ou, pour rejouer la réponse enregistrée :
   `python lancer.py --fichier-mee reponse_brute.json`).

En cas d'erreur « invalid_client » : l'identifiant ou la clé n'a pas été reconnu.
Recopiez-les depuis la page de l'application (identifiant et clé non inversés),
ou générez une nouvelle clé secrète, puis corrigez `identifiants.txt`.

Résultat dans `docs/` : `index.html` et `agenda.ics`. La mémoire entre deux
jours est dans `data/etat.json`.

## Mise en ligne automatique (GitHub)

**Guide pas à pas pour non-initiés : `MISE_EN_LIGNE.md`.** Résumé :

1. Créez un dépôt GitHub et envoyez-y ce dossier.
2. *Settings → Secrets and variables → Actions* : ajoutez `FT_CLIENT_ID` et `FT_CLIENT_SECRET`.
3. *Settings → Pages* : source « Deploy from a branch », branche `main`, dossier `/docs`.
4. *Actions → Mise à jour de l'agenda → Run workflow* pour un premier lancement.
   Ensuite, la mise à jour est quotidienne (voir `.github/workflows/quotidien.yml`).

La page sera à `https://<compte>.github.io/<dépôt>/` et le flux à
`.../agenda.ics`. **Sur un compte gratuit, la page est publique** (accessible à
qui a le lien) : elle ne contient que des évènements publics. N'ajoutez jamais
au dépôt de données sur les personnes accompagnées. Si le dépôt reste inactif
longtemps, GitHub peut suspendre les tâches planifiées : un lancement manuel les relance.

## S'abonner dans Outlook

*Ajouter un calendrier → S'abonner à partir du web*, puis coller l'adresse de
`agenda.ics` (la page la propose avec un bouton « Copier »). Le calendrier
dédié peut être masqué ou affiché à volonté. Les évènements ne bloquent pas
les créneaux. Le rafraîchissement dépend d'Outlook (de quelques heures à une journée).

## Fonctionnement des tris

Tout se règle dans `config/regles.toml`, avec le Bloc-notes. Les accents et les
majuscules sont ignorés ; un mot cherché est un mot entier (`FLE` ne trouve pas
« flexible ») ; une étoile accepte toute fin de mot (`atelier*` trouve « ateliers »).

Chaque évènement est classé **retenu**, **à vérifier** ou **écarté**, avec la raison
affichée dans « Détails » sur la page. Les évènements écartés restent consultables
(statut « Écartés ») pour pouvoir corriger les règles. Ordre d'application :

1. **Distanciel** : écarté si toutes les modalités sont à distance (un évènement à la
   fois en physique et à distance est conservé) ;
2. **Villes** : liste de villes écartées (`[villes] exclues`), ou au contraire liste des
   seules villes acceptées (`acceptees`) ;
3. **Types** : types souhaités (`accepter`) et non souhaités (`ecarter`). Un type ni
   dans l'une ni dans l'autre liste (nouveau type, type vide) passe en **à vérifier** ;
4. **Mots-clés** : `[exclure]` écarte, `[inclure]` retient d'office, `[a_verifier]` signale.

Les listes `[inclure]` et `[exclure]` sont vides au départ : vous les remplirez au vu des
résultats. Les mots à exclure ne sont cherchés que dans le **titre** par défaut : dans
« publics », « Ouvert aux cadres » côtoie souvent d'autres publics.

**Évènements réservés au public d'une autre structure** : impossible à écarter à coup sûr
sans écarter à tort des évènements ouverts à tous. La liste `[a_verifier]` contient donc
des mots comme « uniquement » ou « réservé » : l'évènement n'est pas supprimé, il est
marqué « À vérifier » avec le mot qui l'a signalé. Complétez cette liste avec les
formulations rencontrées.

## Ce que le suivi quotidien apporte

- **Nouveau** et **Modifié** (pendant 7 jours) ;
- **Annulé ?** quand un évènement futur disparaît de la source. Ce n'est signalé que si
  la source a bien répondu, n'est pas vide et si les filtres n'ont pas changé ;
- un numéro de version stable par évènement : les agendas mettent à jour
  l'existant au lieu de créer un doublon.

## Ajouter une source ou un autre agenda

- **Nouvelle source** : un fichier dans `src/agenda/sources/` avec une fonction
  `recuperer(cfg, maintenant)` qui renvoie une liste d'`Evenement`
  (voir `modele.py`), à inscrire dans le registre `SOURCES` de `main.py`, avec
  une section `[sources.<nom>]` dans `sources.toml`.
- **Nouvel agenda cible** (Outlook via Microsoft Graph, Google Calendar…) : un fichier
  dans `src/agenda/cibles/` avec une fonction
  `publier(evenements, cfg, dossier, maintenant)`, à inscrire dans `CIBLES`.
  Les évènements arrivent déjà triés et suivis.

## Points à vérifier avec la première vraie réponse

La documentation de l'API contient quelques incohérences ; le comportement réel
est à confirmer :

- numérotation des pages (0 ou 1) : `--tester-pagination`, puis `page_depart` ;
- `modalite` : la description cite `ADIST` / `ENPHY`, l'exemple utilise `"1"`. L'API renvoie
  « en physique » et « à distance » : le tri du distanciel se fait sur la réponse ;
- `secteurActivite` : lettres de A à N dans le texte, numéros de 1 à 14 dans le référentiel ;
- `beneficeParticipations` : son référentiel est identique à celui des publics ;
- plusieurs valeurs dans `publicCible` ou `objectifs` : combinées en « ou » ou en « et » ?
- l'API ne donne ni date de fin, ni évènement sur plusieurs jours : la fin est
  celle de `heureFin` le jour de début.

## Tests

```
python -m unittest discover -s tests -v
```
