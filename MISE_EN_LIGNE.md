# Mise en ligne pas à pas (GitHub, gratuit)

Résultat : une adresse web (la page de consultation) et une adresse d'abonnement
(`agenda.ics`) mises à jour automatiquement chaque matin, sans que votre ordinateur
soit allumé.

Temps prévu : 30 à 45 minutes la première fois.

## Avant de commencer : deux règles de sécurité

1. **Le fichier `identifiants.txt` ne doit jamais être envoyé sur GitHub.** Le projet est
   configuré pour l'éviter, à condition d'utiliser GitHub Desktop (étape 2). Vérifiez-le à
   l'étape 4.
2. **La page sera publique** : n'importe qui possédant l'adresse pourra la consulter (elle
   n'est pas référencée par les moteurs de recherche, mais elle n'est pas secrète). Elle ne
   contient que des évènements publics. Ne mettez jamais dans ce dossier de noms ni
   d'informations sur les personnes accompagnées. Par prudence, vérifiez aussi que les
   conditions d'utilisation de l'API autorisent la republication des évènements.

## Étape 1. Créer un compte GitHub

Sur https://github.com, « Sign up » : adresse mail, mot de passe, nom d'utilisateur.
Le nom d'utilisateur apparaîtra dans l'adresse de la page : choisissez-en un neutre.

## Étape 2. Installer GitHub Desktop

Téléchargez-le sur https://desktop.github.com, installez-le, puis connectez-vous avec votre
compte (« Sign in to GitHub.com »).

## Étape 3. Préparer le dossier

Dézippez la dernière version de `agenda-insertion.zip` à un endroit stable (par exemple
dans Documents). Si vous avez déjà un dossier avec `identifiants.txt` rempli, copiez ce
fichier dans le nouveau dossier : il restera sur votre ordinateur.

## Étape 4. Envoyer le dossier sur GitHub

Dans GitHub Desktop :

1. Menu **File → Add local repository…**, choisissez le dossier `agenda-insertion`.
2. Si un message indique que ce n'est pas un dépôt Git, cliquez sur le lien
   **« create a repository here »**, laissez les champs par défaut (ne cochez rien) et
   validez par **Create repository**.
3. **Contrôle important** : dans la liste des fichiers à gauche, **`identifiants.txt` ne doit
   pas apparaître**. S'il apparaît, arrêtez-vous et dites-le-moi avant d'aller plus loin.
4. En bas à gauche, dans « Summary », tapez `Premier envoi`, puis **Commit to main**.
5. En haut, cliquez sur **Publish repository**. **Décochez « Keep this code private »**
   (la page gratuite l'exige), puis **Publish repository**.

## Étape 5. Enregistrer vos identifiants dans GitHub

Sur github.com, ouvrez votre dépôt `agenda-insertion`, puis
**Settings → Secrets and variables → Actions → New repository secret**.
Créez deux secrets (le nom doit être écrit exactement ainsi) :

| Name | Secret |
|---|---|
| `FT_CLIENT_ID` | votre identifiant francetravail.io |
| `FT_CLIENT_SECRET` | votre clé secrète |

Ces valeurs sont chiffrées : personne ne peut les relire, pas même vous après enregistrement.

## Étape 6. Activer la page web

**Settings → Pages** : sous « Build and deployment », Source = **Deploy from a branch**,
Branch = **main**, dossier = **/docs**, puis **Save**.

## Étape 7. Lancer une première mise à jour

Onglet **Actions** → **Mise à jour de l'agenda** → **Run workflow** → **Run workflow**.
Au bout d'une à deux minutes, une coche verte apparaît. Une croix rouge signifie une
erreur : ouvrez l'exécution, copiez le message en rouge et transmettez-le.

La page est alors disponible, au bout de quelques minutes, à l'adresse :

    https://VOTRE-NOM-UTILISATEUR.github.io/agenda-insertion/

et le flux d'agenda à :

    https://VOTRE-NOM-UTILISATEUR.github.io/agenda-insertion/agenda.ics

(Tant que la première mise à jour n'a pas réussi, la page affiche « 404 ».)

## Étape 8. Ajouter l'agenda dans Outlook

- **Outlook sur le web / nouvel Outlook** : Calendrier → **Ajouter un calendrier** →
  **S'abonner à partir du web** → collez l'adresse `agenda.ics` → donnez un nom
  (« Évènements insertion ») → **Importer**.
- **Outlook classique (Windows)** : Fichier → Paramètres du compte → Paramètres du compte →
  onglet **Calendriers Internet** → **Nouveau** → collez l'adresse.

Si votre messagerie professionnelle bloque l'abonnement à un calendrier externe, utilisez
un calendrier Outlook personnel, ou la page web seule. Les évènements ne bloquent pas vos
créneaux. Outlook actualise l'abonnement de lui-même, parfois avec quelques heures de retard.

## Ensuite

- **Mise à jour automatique** : chaque jour vers 6 h / 7 h (heure de Paris).
  Lancement manuel possible à tout moment (étape 7).
- **Modifier les réglages** (zone, villes, types, mots-clés) : modifiez les fichiers du
  dossier `config` avec le Bloc-notes, puis dans GitHub Desktop : résumé (par exemple
  « Nouvelles villes »), **Commit to main**, puis **Push origin**. La mise à jour du
  lendemain en tient compte, ou lancez-la à la main.
- **Nouvelle version du projet** : dézippez la nouvelle archive par-dessus le dossier,
  conservez `identifiants.txt`, puis même procédure (Commit, Push).
- **Si la mise à jour échoue** : GitHub envoie un mail. La page reste celle de la veille.
- **Tâches suspendues** : GitHub arrête les mises à jour planifiées d'un dépôt public
  resté inactif plusieurs semaines. Un lancement manuel (étape 7) les relance.
