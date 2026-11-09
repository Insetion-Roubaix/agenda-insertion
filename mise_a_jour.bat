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
python lancer.py
if errorlevel 1 goto erreur
start "" "%~dp0docs\index.html"
goto fin
:erreur
echo.
echo Une erreur est survenue : copiez le message ci-dessus pour le transmettre.
:fin
echo.
pause
