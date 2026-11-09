@echo off
cd /d "%~dp0"
python -m pip install --quiet tzdata
echo.
if not exist identifiants.txt (
  copy identifiants.exemple.txt identifiants.txt >nul
  echo Le Bloc-notes va s'ouvrir : collez votre identifiant et votre cle secrete,
  echo enregistrez, puis fermez le Bloc-notes pour continuer.
  start /wait notepad identifiants.txt
)
echo.
python outils\test_api.py --tester-pagination --tout
echo.
echo Si le test a reussi, le fichier reponse_brute.json est cree dans ce dossier (tous les evenements).
echo En cas d'echec sur l'identifiant : corrigez le fichier identifiants.txt et relancez.
pause
