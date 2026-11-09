"""Mémoire entre deux exécutions (data/etat.json).

Elle sert à :
  - repérer les évènements NOUVEAUX et MODIFIÉS (badges sur la page) ;
  - garder un numéro de version stable par évènement (SEQUENCE du .ics), pour
    que les agendas mettent à jour l'existant au lieu de créer un doublon ;
  - signaler les évènements ANNULÉS : disparus de la source alors qu'ils
    n'avaient pas encore eu lieu.

Le fichier ne contient que des données d'évènements publics.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

from .modele import ANNULE, Evenement

VERSION = 1
JOURS_BADGE = 7        # durée d'affichage de « Nouveau » / « Modifié »
JOURS_CONSERVATION = 7  # on garde un évènement passé ce nombre de jours


def charger(chemin: str) -> dict:
    if os.path.exists(chemin):
        with open(chemin, encoding="utf-8") as f:
            etat = json.load(f)
        if etat.get("version") == VERSION:
            return etat
    return {"version": VERSION, "signature": "", "evenements": {}}


def sauver(chemin: str, etat: dict) -> None:
    os.makedirs(os.path.dirname(chemin) or ".", exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(etat, f, ensure_ascii=False, indent=1, sort_keys=True)


def mettre_a_jour(
    etat: dict,
    courants: list[Evenement],
    maintenant: datetime,
    sources_ok: set[str],
    fenetre_fin: datetime,
    signature: str,
) -> list[Evenement]:
    """Compare l'état précédent aux évènements du jour.

    Renvoie tous les évènements à publier (courants + annulés récents) avec
    leurs indicateurs nouveau / modifie / sequence / cycle renseignés.
    Modifie `etat` en place.
    """
    memoire: dict = etat["evenements"]
    premiere_execution = not memoire
    config_changee = etat.get("signature", "") != signature
    iso = maintenant.isoformat()
    jusqu = (maintenant + timedelta(days=JOURS_BADGE)).isoformat()
    cles_courantes = set()

    for ev in courants:
        cles_courantes.add(ev.cle)
        fiche = memoire.get(ev.cle)
        empreinte = ev.empreinte()
        if fiche is None:
            fiche = {
                "empreinte": empreinte, "sequence": 0,
                # au tout premier import, tout serait « nouveau » : on évite
                "nouveau_jusqu": iso if premiere_execution else jusqu,
                "modifie_jusqu": iso,
            }
        else:
            if fiche["empreinte"] != empreinte:
                fiche["empreinte"] = empreinte
                fiche["sequence"] += 1
                fiche["modifie_jusqu"] = jusqu
            if fiche.get("cycle") == ANNULE:  # réapparu : on le réactive
                fiche["sequence"] += 1
                fiche["modifie_jusqu"] = jusqu
        fiche["cycle"] = ""
        ev.sequence = fiche["sequence"]
        ev.nouveau = maintenant < datetime.fromisoformat(fiche["nouveau_jusqu"])
        ev.modifie = maintenant < datetime.fromisoformat(fiche["modifie_jusqu"])
        ev.cycle = ""
        fiche["snapshot"] = ev.vers_dict()
        memoire[ev.cle] = fiche

    a_publier = list(courants)
    deja_vus_par_source = {
        s: sum(1 for c in cles_courantes if c.startswith(s + ":")) for s in sources_ok
    }

    for cle, fiche in list(memoire.items()):
        if cle in cles_courantes:
            continue
        snap = Evenement.depuis_dict(fiche["snapshot"])
        # Évènement passé : on le garde quelques jours puis on l'oublie
        reference = snap.fin or snap.debut
        if maintenant - reference > timedelta(days=JOURS_CONSERVATION):
            del memoire[cle]
            continue
        if reference < maintenant:
            continue  # terminé : ni annulé ni à publier
        source = cle.split(":", 1)[0]

        detection_fiable = (
            source in sources_ok
            and not config_changee
            and deja_vus_par_source.get(source, 0) > 0  # source muette = suspect
            and snap.debut <= fenetre_fin
        )
        if fiche.get("cycle") == ANNULE:
            pass  # déjà annulé : reste annulé
        elif detection_fiable:
            fiche["cycle"] = ANNULE
            fiche["sequence"] += 1
            fiche["modifie_jusqu"] = (maintenant + timedelta(days=JOURS_BADGE)).isoformat()
        elif config_changee:
            del memoire[cle]  # on ne sait plus : on oublie plutôt que d'annoncer à tort
            continue
        else:
            continue  # on garde en mémoire sans rien annoncer

        if fiche.get("cycle") == ANNULE:
            snap.cycle = ANNULE
            snap.sequence = fiche["sequence"]
            snap.modifie = maintenant < datetime.fromisoformat(fiche["modifie_jusqu"])
            a_publier.append(snap)

    etat["signature"] = signature
    return a_publier
