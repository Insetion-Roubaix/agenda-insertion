"""Orchestration : sources -> tri -> suivi -> cibles.

    python lancer.py                 # exécution normale (API réelle)
    python lancer.py --demo          # évènements fictifs, sortie dans demo/
    python lancer.py --fichier-mee reponse_brute.json   # réponse API enregistrée
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tomllib
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import demo, etat as suivi, tri
from .cibles import ics, page_web
from .modele import A_VERIFIER, ECARTE, RETENU, Evenement
from .sources import mee

# Registres : pour ajouter une source ou une cible, l'inscrire ici
# (et écrire le module correspondant).
SOURCES = {"mee": mee}
CIBLES = {"ics": ics, "page_web": page_web}


def _toml(chemin: Path) -> dict:
    with open(chemin, "rb") as f:
        return tomllib.load(f)


def _signature(cfg_sources: dict) -> str:
    """Empreinte des réglages de collecte : si elle change, on ne déduit pas
    d'« annulations » de simples changements de filtres."""
    brut = json.dumps(cfg_sources, sort_keys=True, default=str)
    return hashlib.sha1(brut.encode()).hexdigest()[:12]


def executer(args: argparse.Namespace) -> int:
    dossier_cfg = Path(args.config)
    cfg_sources = _toml(dossier_cfg / "sources.toml")
    cfg_cibles = _toml(dossier_cfg / "cibles.toml")
    regles = tri.Regles.depuis_config(_toml(dossier_cfg / "regles.toml"))

    general = cfg_sources.get("general", {})
    try:
        fuseau = ZoneInfo(general.get("fuseau", "Europe/Paris"))
    except ZoneInfoNotFoundError:
        print(
            "\nLa liste des fuseaux horaires est absente de cet ordinateur (fréquent sous Windows).\n"
            "Installez-la une fois pour toutes avec cette commande, puis relancez :\n\n"
            "    python -m pip install tzdata\n",
            file=sys.stderr,
        )
        return 1
    maintenant = datetime.now(fuseau).replace(microsecond=0)
    fenetre_fin = maintenant + timedelta(days=int(general.get("fenetre_jours", 90)))

    sortie = args.sortie or ("demo" if args.demo else "docs")
    chemin_etat = args.etat or ("demo/etat-demo.json" if args.demo else "data/etat.json")

    # 1. Collecte -----------------------------------------------------------
    tous: dict[str, Evenement] = {}
    sources_ok: set[str] = set()
    erreurs: list[str] = []
    actives = {
        nom: {**general, **cfg}
        for nom, cfg in cfg_sources.get("sources", {}).items()
        if cfg.get("actif", True) and nom in SOURCES
    }
    for nom, cfg in actives.items():
        try:
            if args.demo and nom == "mee":
                evs = mee.recuperer(cfg, maintenant, brut=demo.exemple_brut(maintenant))
            elif args.fichier_mee and nom == "mee":
                evs = mee.recuperer(cfg, maintenant, fichier=args.fichier_mee)
            else:
                evs = SOURCES[nom].recuperer(cfg, maintenant)
        except Exception as e:  # une source en panne ne doit pas bloquer les autres
            erreurs.append(f"Source « {nom} » : {e}")
            continue
        sources_ok.add(nom)
        for ev in evs:
            tous.setdefault(ev.cle, ev)
        print(f"[{nom}] {len(evs)} évènements récupérés")

    for e in erreurs:
        print(f"::warning::{e}", file=sys.stderr)
    if actives and not sources_ok:
        print("Aucune source n'a répondu : sorties inchangées.", file=sys.stderr)
        return 1

    # 2. Évènements déjà terminés : inutiles ---------------------------------
    courants = [e for e in tous.values() if (e.fin or e.debut) >= maintenant]

    # 3. Tri par mots-clés ----------------------------------------------------
    tri.trier(courants, regles)

    # 4. Suivi : nouveau / modifié / annulé -----------------------------------
    memoire = suivi.charger(chemin_etat)
    a_publier = suivi.mettre_a_jour(
        memoire, courants, maintenant, sources_ok, fenetre_fin, _signature(actives)
    )
    suivi.sauver(chemin_etat, memoire)

    # 5. Sorties --------------------------------------------------------------
    for nom, module in CIBLES.items():
        cfg = cfg_cibles.get(nom, {})
        if not cfg.get("actif", True):
            continue
        chemin = module.publier(a_publier, cfg, sortie, maintenant)
        print(f"[{nom}] écrit : {chemin}")

    compte = {s: sum(1 for e in a_publier if e.statut_tri == s) for s in (RETENU, A_VERIFIER, ECARTE)}
    print(
        f"Bilan : {compte[RETENU]} retenus, {compte[A_VERIFIER]} à vérifier, {compte[ECARTE]} écartés, "
        f"{sum(e.nouveau for e in a_publier)} nouveaux, {sum(e.modifie for e in a_publier)} modifiés, "
        f"{sum(e.cycle == 'annule' for e in a_publier)} annulés."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Agenda automatisé des évènements emploi")
    p.add_argument("--config", default="config", help="dossier des fichiers .toml")
    p.add_argument("--sortie", help="dossier de sortie (docs par défaut)")
    p.add_argument("--etat", help="fichier de mémoire (data/etat.json par défaut)")
    p.add_argument("--demo", action="store_true", help="données fictives, sortie dans demo/")
    p.add_argument("--fichier-mee", help="lire une réponse enregistrée au lieu d'appeler l'API")
    return executer(p.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
