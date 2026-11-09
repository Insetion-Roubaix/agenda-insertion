"""Lecture de l'identifiant et de la clé secrète francetravail.io.

Ordre de recherche :
  1. variables d'environnement FT_CLIENT_ID et FT_CLIENT_SECRET
     (c'est ce que GitHub Actions utilise) ;
  2. fichier `identifiants.txt` à la racine du projet (usage sur un ordinateur).

Les valeurs sont nettoyées : les espaces, retours à la ligne, guillemets et
caractères invisibles collés par erreur avec le texte sont retirés.
"""

from __future__ import annotations

import os
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
FICHIER = RACINE / "identifiants.txt"
_GUILLEMETS = "\"'“”‘’«»`"


def nettoyer(valeur: str | None) -> str:
    if not valeur:
        return ""
    return "".join(
        c for c in valeur
        if c.isprintable() and not c.isspace() and c not in _GUILLEMETS
    )


def _lire_fichier(chemin: Path) -> dict[str, str]:
    valeurs: dict[str, str] = {}
    if not chemin.exists():
        return valeurs
    for ligne in chemin.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        cle, _, valeur = ligne.partition("=")
        valeurs[cle.strip()] = nettoyer(valeur)
    return valeurs


def lire(chemin: Path | None = None) -> tuple[str, str]:
    """Renvoie (identifiant, clé secrète), chaînes vides si introuvables."""
    fichier = _lire_fichier(chemin or FICHIER)
    identifiant = nettoyer(os.environ.get("FT_CLIENT_ID")) or fichier.get("FT_CLIENT_ID", "")
    secret = nettoyer(os.environ.get("FT_CLIENT_SECRET")) or fichier.get("FT_CLIENT_SECRET", "")
    return identifiant, secret
