"""Tri des évènements par mots-clés (en complément des filtres appliqués à
l'API). Les règles vivent dans config/regles.toml : on les modifie sans
toucher au code.

Chaque évènement reçoit un statut :
  retenu      -> un mot « à inclure » a été trouvé
  a_verifier  -> un mot « à vérifier » a été trouvé, ou aucune correspondance
  ecarte      -> un mot « à exclure » a été trouvé (ou un filtre local l'écarte)
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from .modele import A_VERIFIER, ECARTE, RETENU, Evenement

CHAMPS_CONNUS = {
    "titre", "description", "deroulement", "type", "objectifs", "publics",
    "benefices", "operations", "intervenants", "organisateur",
    "etablissement", "ville",
}


MOTS_DISTANCE = ("distance", "distanciel", "visio", "en ligne", "adist")


def uniquement_a_distance(ev: Evenement) -> bool:
    """Vrai si toutes les modalités sont à distance (un évènement « hybride »,
    à la fois en physique et à distance, n'est donc pas concerné)."""
    modalites = [normaliser_texte(m) for m in ev.modalites if m]
    return bool(modalites) and all(any(k in m for k in MOTS_DISTANCE) for m in modalites)


def normaliser_texte(texte: str) -> str:
    """Minuscules, sans accents, apostrophes unifiées, espaces simples."""
    t = unicodedata.normalize("NFD", texte or "")
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = t.lower().replace("’", "'").replace("`", "'")
    return re.sub(r"\s+", " ", t).strip()


def _motif(terme: str) -> re.Pattern:
    """Mot ou expression entière ; « recrut* » accepte toute fin de mot."""
    prefixe = terme.endswith("*")
    brut = normaliser_texte(terme.rstrip("*"))
    fin = r"\w*" if prefixe else r"(?!\w)"
    return re.compile(r"(?<!\w)" + re.escape(brut) + fin)


@dataclass
class ListeMots:
    mots: list[str] = field(default_factory=list)
    champs: list[str] = field(default_factory=list)
    _motifs: list[tuple[str, re.Pattern]] = field(default_factory=list, repr=False)

    @classmethod
    def depuis_config(cls, cfg: dict, champs_defaut: list[str]) -> "ListeMots":
        mots = [m for m in cfg.get("mots", []) if m and m.strip()]
        champs = cfg.get("champs", champs_defaut)
        inconnus = set(champs) - CHAMPS_CONNUS
        if inconnus:
            raise ValueError(
                f"Champs inconnus dans regles.toml : {sorted(inconnus)}. "
                f"Champs possibles : {sorted(CHAMPS_CONNUS)}"
            )
        return cls(mots=mots, champs=champs, _motifs=[(m, _motif(m)) for m in mots])

    def trouver(self, ev: Evenement) -> list[str]:
        if not self._motifs:
            return []
        texte = normaliser_texte(" \n ".join(_valeur(ev, c) for c in self.champs))
        return [m for m, motif in self._motifs if motif.search(texte)]


def _valeur(ev: Evenement, champ: str) -> str:
    v = {
        "titre": ev.titre, "description": ev.description,
        "deroulement": ev.deroulement, "type": ev.type,
        "objectifs": ev.objectifs, "publics": ev.publics,
        "benefices": ev.benefices, "operations": ev.operations,
        "intervenants": ev.intervenants, "organisateur": ev.organisateur,
        "etablissement": ev.etablissement, "ville": ev.ville,
    }[champ]
    return " ; ".join(v) if isinstance(v, list) else (v or "")


def _compiler(mots: list[str], ville: bool = False) -> list[tuple[str, re.Pattern]]:
    """Compile une liste de mots. Pour les villes, les tirets valent des espaces
    (« Lys-lez-Lannoy » = « lys lez lannoy »)."""
    res = []
    for m in mots or []:
        if m and m.strip():
            res.append((m, _motif(m.replace("-", " ") if ville else m)))
    return res


def _chercher(texte: str, motifs: list[tuple[str, re.Pattern]], ville: bool = False) -> list[str]:
    t = normaliser_texte(texte)
    if ville:
        t = t.replace("-", " ")
    return [m for m, motif in motifs if motif.search(t)]


@dataclass
class Regles:
    inclure: ListeMots
    exclure: ListeMots
    a_verifier: ListeMots
    sans_correspondance: str
    types_accepter: list = field(default_factory=list)
    types_ecarter: list = field(default_factory=list)
    types_autres: str = A_VERIFIER
    villes_exclues: list = field(default_factory=list)
    villes_acceptees: list = field(default_factory=list)
    exclure_complets: bool = False
    exclure_distanciel: bool = False

    @classmethod
    def depuis_config(cls, cfg: dict) -> "Regles":
        large = ["titre", "description", "deroulement", "objectifs", "benefices",
                 "operations", "intervenants"]
        inclure = ListeMots.depuis_config(cfg.get("inclure", {}), large)
        exclure = ListeMots.depuis_config(cfg.get("exclure", {}), ["titre"])
        a_verifier = ListeMots.depuis_config(cfg.get("a_verifier", {}), large)
        defaut = cfg.get("defaut", {}).get("sans_correspondance", "a_verifier")
        if defaut not in {RETENU, A_VERIFIER, ECARTE}:
            raise ValueError("defaut.sans_correspondance doit valoir retenu, a_verifier ou ecarte")
        types = cfg.get("types", {})
        autres = types.get("autres", "a_verifier")
        if autres not in {RETENU, A_VERIFIER, ECARTE}:
            raise ValueError("types.autres doit valoir retenu, a_verifier ou ecarte")
        villes = cfg.get("villes", {})
        filtres = cfg.get("filtres", {})
        return cls(
            inclure=inclure, exclure=exclure, a_verifier=a_verifier,
            sans_correspondance=defaut,
            types_accepter=_compiler(types.get("accepter", [])),
            types_ecarter=_compiler(types.get("ecarter", [])),
            types_autres=autres,
            villes_exclues=_compiler(villes.get("exclues", []), ville=True),
            villes_acceptees=_compiler(villes.get("acceptees", []), ville=True),
            exclure_complets=bool(filtres.get("exclure_complets", False)),
            exclure_distanciel=bool(filtres.get("exclure_distanciel", False)),
        )


def classer(ev: Evenement, r: Regles) -> None:
    ev.raisons = []

    # --- Filtres « durs » (ne dépendent pas des mots-clés) -------------------
    if r.exclure_distanciel and uniquement_a_distance(ev):
        ev.statut_tri, ev.raisons = ECARTE, ["à distance uniquement"]
        return
    if r.exclure_complets and ev.complet:
        ev.statut_tri, ev.raisons = ECARTE, ["évènement complet"]
        return

    villes = _chercher(ev.ville, r.villes_exclues, ville=True)
    if villes:
        ev.statut_tri, ev.raisons = ECARTE, [f"ville écartée : {ev.ville}"]
        return
    if r.villes_acceptees and ev.ville and not _chercher(ev.ville, r.villes_acceptees, ville=True):
        ev.statut_tri, ev.raisons = ECARTE, [f"ville hors zone : {ev.ville}"]
        return

    type_a_confirmer = False
    if ev.type and _chercher(ev.type, r.types_ecarter):
        ev.statut_tri, ev.raisons = ECARTE, [f"type non souhaité : {ev.type}"]
        return
    if r.types_accepter and not _chercher(ev.type, r.types_accepter):
        if r.types_autres == ECARTE:
            ev.statut_tri, ev.raisons = ECARTE, [f"type non souhaité : {ev.type or 'non précisé'}"]
            return
        type_a_confirmer = r.types_autres == A_VERIFIER

    # --- Mots-clés -------------------------------------------------------------
    exclus = r.exclure.trouver(ev)
    if exclus:
        ev.statut_tri, ev.raisons = ECARTE, [f"exclu : {', '.join(exclus)}"]
        return

    raisons: list[str] = []
    statut = None
    inclus = r.inclure.trouver(ev)
    if inclus:
        statut, raisons = RETENU, [f"mot-clé : {', '.join(inclus)}"]
    else:
        verif = r.a_verifier.trouver(ev)
        if verif:
            statut, raisons = A_VERIFIER, [f"à regarder : {', '.join(verif)}"]
        elif not r.inclure.mots:
            statut = RETENU  # aucune liste « inclure » : pas de tri par mot-clé
        else:
            statut, raisons = r.sans_correspondance, ["aucun mot-clé trouvé"]

    if type_a_confirmer and statut == RETENU:
        statut = A_VERIFIER
        raisons = [f"type à confirmer : {ev.type or 'non précisé'}"] + raisons
    ev.statut_tri, ev.raisons = statut, raisons


def trier(evenements: list[Evenement], r: Regles) -> None:
    for ev in evenements:
        classer(ev, r)
