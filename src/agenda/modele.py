"""Format pivot : un évènement, quelle que soit sa source.

Les sources produisent des `Evenement`, le tri les annote, les cibles
(fichier .ics, page web, agenda en ligne...) les consomment. Aucun module ne
connaît le format interne d'un autre : c'est ce qui permet d'ajouter une
source ou une cible sans toucher au reste.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime

# Statuts de tri
RETENU = "retenu"
A_VERIFIER = "a_verifier"
ECARTE = "ecarte"
# Statut de cycle de vie
ANNULE = "annule"  # disparu de la source alors qu'il n'avait pas eu lieu


@dataclass
class Evenement:
    source: str                      # ex. "mee"
    id_source: str                   # identifiant dans la source d'origine
    titre: str
    debut: datetime                  # avec fuseau horaire
    fin: datetime | None = None
    ville: str = ""
    code_postal: str = ""
    latitude: float | None = None
    longitude: float | None = None
    description: str = ""
    deroulement: str = ""
    type: str = ""
    modalites: list[str] = field(default_factory=list)
    publics: list[str] = field(default_factory=list)
    objectifs: list[str] = field(default_factory=list)
    benefices: list[str] = field(default_factory=list)
    operations: list[str] = field(default_factory=list)
    intervenants: list[str] = field(default_factory=list)
    organisateur: str = ""
    etablissement: str = ""
    places_total: int | None = None
    places_prises: int | None = None
    url: str = ""

    # Renseignés par le tri et le suivi (pas par les sources)
    statut_tri: str = RETENU
    raisons: list[str] = field(default_factory=list)
    cycle: str = ""                  # "" | "annule"
    nouveau: bool = False
    modifie: bool = False
    sequence: int = 0                # +1 à chaque modification (pour le .ics)

    @property
    def cle(self) -> str:
        return f"{self.source}:{self.id_source}"

    @property
    def places_restantes(self) -> int | None:
        if self.places_total is None or self.places_prises is None:
            return None
        return max(self.places_total - self.places_prises, 0)

    @property
    def complet(self) -> bool:
        reste = self.places_restantes
        return reste is not None and self.places_total and reste == 0

    @property
    def lieu(self) -> str:
        if "distance" in " ".join(self.modalites).lower() and not self.ville:
            return "À distance"
        morceaux = [self.ville, f"({self.code_postal})" if self.code_postal else ""]
        return " ".join(m for m in morceaux if m)

    def empreinte(self) -> str:
        """Signature du contenu utile : change si l'évènement est modifié.

        Les places prises varient en continu : on les exclut pour ne pas
        signaler une « modification » à chaque inscription.
        """
        base = {
            k: v
            for k, v in self.vers_dict().items()
            if k
            not in {
                "statut_tri", "raisons", "cycle", "nouveau", "modifie",
                "sequence", "places_prises",
            }
        }
        brut = json.dumps(base, sort_keys=True, ensure_ascii=False)
        return hashlib.sha1(brut.encode("utf-8")).hexdigest()[:16]

    def vers_dict(self) -> dict:
        d = asdict(self)
        d["debut"] = self.debut.isoformat()
        d["fin"] = self.fin.isoformat() if self.fin else None
        return d

    @classmethod
    def depuis_dict(cls, d: dict) -> "Evenement":
        d = dict(d)
        d["debut"] = datetime.fromisoformat(d["debut"])
        d["fin"] = datetime.fromisoformat(d["fin"]) if d.get("fin") else None
        champs = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in d.items() if k in champs})
