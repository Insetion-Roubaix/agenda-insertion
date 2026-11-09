@echo off
cd /d "%~dp0"
echo Installation de la liste des fuseaux horaires (une seule fois)...
python -m pip install --quiet tzdata
echo.
echo Creation de la demonstration...
python lancer.py --demo
if errorlevel 1 goto erreur
echo.
echo Ouverture de la page dans votre navigateur...
start "" "%~dp0demo\index.html"
goto fin
:erreur
echo.
echo Une erreur est survenue : copiez le message ci-dessus pour le transmettre.
:fin
echo.
pause
