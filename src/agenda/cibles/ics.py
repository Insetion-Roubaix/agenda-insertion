"""Cible : flux iCalendar (.ics).

Publié à une adresse fixe, ce fichier est un abonnement valable pour
n'importe quel agenda (Outlook, Google Agenda, Apple, téléphone...).
Changer d'agenda ne demande aucun développement : on s'abonne à la même URL.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from ..modele import A_VERIFIER, ANNULE, Evenement

NOM = "ics"

LIBELLE_STATUT = {"retenu": "Retenu", "a_verifier": "À vérifier"}


def _echapper(texte: str) -> str:
    return (
        texte.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
        .replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n")
    )


def _plier(ligne: str) -> str:
    """Pliage RFC 5545 : 75 octets max par ligne, suite précédée d'une espace."""
    lignes, courante, taille = [], "", 0
    for car in ligne:
        n = len(car.encode("utf-8"))
        if taille + n > 75:
            lignes.append(courante)
            courante, taille = car, 1 + n  # l'espace de continuation compte
        else:
            courante += car
            taille += n
    lignes.append(courante)
    return "\r\n ".join(lignes)


def _utc(d: datetime) -> str:
    return d.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _description(ev: Evenement) -> str:
    lignes = []
    if ev.cycle == ANNULE:
        lignes.append("⚠ Évènement retiré de la source : probablement annulé.")
    if ev.statut_tri == A_VERIFIER:
        lignes.append("À vérifier : " + "; ".join(ev.raisons))
    if ev.type:
        lignes.append(f"Type : {ev.type}")
    if ev.modalites:
        lignes.append("Modalité : " + ", ".join(ev.modalites))
    if ev.organisateur or ev.etablissement:
        lignes.append("Organisé par : " + " – ".join(x for x in (ev.organisateur, ev.etablissement) if x))
    if ev.publics:
        lignes.append("Publics : " + ", ".join(ev.publics))
    if ev.objectifs:
        lignes.append("Objectifs : " + ", ".join(ev.objectifs))
    if ev.benefices:
        lignes.append("Bénéfices : " + ", ".join(ev.benefices))
    if ev.intervenants:
        lignes.append("Intervenants : " + ", ".join(ev.intervenants))
    reste = ev.places_restantes
    if reste is not None:
        lignes.append("COMPLET" if ev.complet else f"Places restantes : {reste} / {ev.places_total}")
    if ev.description:
        lignes += ["", ev.description]
    if ev.deroulement:
        lignes += ["", "Déroulement :", ev.deroulement]
    if ev.url:
        lignes += ["", f"Détail et inscription : {ev.url}"]
    return "\n".join(lignes)


def _vevent(ev: Evenement, maintenant: datetime) -> list[str]:
    titre = ev.titre
    if ev.cycle == ANNULE:
        titre = f"[ANNULÉ ?] {titre}"
    elif ev.statut_tri == A_VERIFIER:
        titre = f"[?] {titre}"
    fin = ev.fin or ev.debut
    lignes = [
        "BEGIN:VEVENT",
        f"UID:{ev.source}-{ev.id_source}@agenda-insertion",
        f"DTSTAMP:{_utc(maintenant)}",
        f"DTSTART:{_utc(ev.debut)}",
        f"DTEND:{_utc(fin)}",
        f"SEQUENCE:{ev.sequence}",
        f"SUMMARY:{_echapper(titre)}",
        f"DESCRIPTION:{_echapper(_description(ev))}",
        "STATUS:CANCELLED" if ev.cycle == ANNULE else "STATUS:CONFIRMED",
        "TRANSP:TRANSPARENT",  # ne bloque pas le créneau dans l'agenda
    ]
    if ev.lieu:
        lignes.append(f"LOCATION:{_echapper(ev.lieu)}")
    if ev.latitude is not None and ev.longitude is not None:
        lignes.append(f"GEO:{ev.latitude:.6f};{ev.longitude:.6f}")
    if ev.url:
        lignes.append(f"URL:{ev.url}")
    if ev.type:
        lignes.append(f"CATEGORIES:{_echapper(ev.type)}")
    lignes.append("END:VEVENT")
    return lignes


def publier(evenements: list[Evenement], cfg: dict, dossier: str, maintenant: datetime) -> str:
    statuts = set(cfg.get("statuts_publies", ["retenu", "a_verifier"]))
    nom = cfg.get("nom_calendrier", "Évènements insertion")
    a_ecrire = sorted(
        (e for e in evenements if e.statut_tri in statuts), key=lambda e: e.debut
    )
    lignes = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//agenda-insertion//FR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_echapper(nom)}",
        "X-WR-TIMEZONE:Europe/Paris",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
        "X-PUBLISHED-TTL:PT12H",
    ]
    for ev in a_ecrire:
        lignes += _vevent(ev, maintenant)
    lignes.append("END:VCALENDAR")

    os.makedirs(dossier, exist_ok=True)
    chemin = os.path.join(dossier, cfg.get("fichier", "agenda.ics"))
    with open(chemin, "w", encoding="utf-8", newline="") as f:
        f.write("\r\n".join(_plier(l) for l in lignes) + "\r\n")
    return chemin
