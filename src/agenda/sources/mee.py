"""Source « Mes évènements emploi » (API francetravail.io, v1).

Documentation : POST /mee/evenements, authentification OAuth2
« client credentials » avec les scopes `api_evenementsv1` et `evenements`.

Les identifiants sont lus par `identifiants.py` : variables d'environnement
FT_CLIENT_ID et FT_CLIENT_SECRET, ou fichier local `identifiants.txt`
(jamais versionné).
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

from .. import identifiants
from ..modele import Evenement

NOM = "mee"

URL_API = "https://api.francetravail.io/partenaire/evenements/v1"
URL_JETON = (
    "https://authentification-partenaire.francetravail.io"
    "/connexion/oauth2/access_token?realm=/partenaire"
)
SCOPES = ["api_evenementsv1", "evenements"]
PAGES_MAX = 50  # garde-fou contre une boucle infinie


class ErreurSource(RuntimeError):
    pass


# --------------------------------------------------------------------------
# Accès à l'API
# --------------------------------------------------------------------------

def _appel(requete: urllib.request.Request, tentatives: int = 3) -> dict | list | None:
    for essai in range(1, tentatives + 1):
        try:
            with urllib.request.urlopen(requete, timeout=30) as rep:
                if rep.status == 204:
                    return None
                corps = rep.read()
                return json.loads(corps) if corps.strip() else None
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            if e.code == 429 and essai < tentatives:
                attente = int(e.headers.get("Retry-After", "2"))
                time.sleep(min(attente, 30))
                continue
            if e.code in (500, 502, 503, 504) and essai < tentatives:
                time.sleep(2 * essai)
                continue
            if e.code in (401, 403):
                raise ErreurSource(
                    f"Accès refusé ({e.code}). Vérifiez l'identifiant, la clé "
                    f"secrète et l'association de l'API à l'application. {detail}"
                ) from e
            raise ErreurSource(f"Erreur HTTP {e.code} : {detail}") from e
        except urllib.error.URLError as e:
            if essai < tentatives:
                time.sleep(2 * essai)
                continue
            raise ErreurSource(f"Réseau indisponible : {e.reason}") from e
    return None


def obtenir_jeton(client_id: str, client_secret: str, url_jeton: str = URL_JETON,
                  scopes: list[str] | None = None) -> str:
    donnees = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": " ".join(scopes or SCOPES),
    }).encode()
    requete = urllib.request.Request(
        url_jeton, data=donnees, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    rep = _appel(requete)
    if not rep or "access_token" not in rep:
        raise ErreurSource("Pas de jeton d'accès dans la réponse.")
    return rep["access_token"]


def rechercher(jeton: str, corps: dict, page: int | None = None,
               taille: int | None = None, url_api: str = URL_API) -> dict:
    """Un appel POST /mee/evenements. Renvoie {"totalElements", "content"}."""
    params = {}
    if taille is not None:
        params["size"] = taille
    if page is not None:
        params["page"] = page
    url = f"{url_api}/mee/evenements"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    requete = urllib.request.Request(
        url, data=json.dumps(corps).encode("utf-8"), method="POST",
        headers={
            "Authorization": f"Bearer {jeton}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    return _appel(requete) or {"totalElements": 0, "content": []}


# --------------------------------------------------------------------------
# Récupération (toutes les requêtes configurées, toutes les pages)
# --------------------------------------------------------------------------

def _recuperer_brut(cfg: dict, maintenant: datetime) -> list[dict]:
    client_id, client_secret = identifiants.lire()
    if not client_id or not client_secret:
        raise ErreurSource(
            "Identifiant ou clé secrète introuvable : renseignez-les dans le fichier "
            "identifiants.txt (ou dans les variables FT_CLIENT_ID et FT_CLIENT_SECRET)."
        )
    jeton = obtenir_jeton(
        client_id, client_secret,
        cfg.get("url_jeton", URL_JETON), cfg.get("scopes", SCOPES),
    )
    url_api = cfg.get("url_api", URL_API)
    taille = min(int(cfg.get("taille_page", 100)), 100)
    page_depart = int(cfg.get("page_depart", 0))
    jours = int(cfg.get("fenetre_jours", 90))
    debut = maintenant.date()
    fin = debut + timedelta(days=jours)

    requetes = cfg.get("requetes") or [{"nom": "toutes"}]
    par_id: dict[int, dict] = {}
    for req in requetes:
        corps = {k: v for k, v in req.items() if k != "nom"}
        corps.setdefault("dateDebut", debut.isoformat())
        corps.setdefault("dateFin", fin.isoformat())
        page = page_depart
        vus_requete: set[int] = set()
        for _ in range(PAGES_MAX):
            rep = rechercher(jeton, corps, page=page, taille=taille, url_api=url_api)
            contenu = rep.get("content") or []
            nouveaux = [e for e in contenu if e.get("id") not in vus_requete]
            for e in nouveaux:
                vus_requete.add(e["id"])
                par_id[e["id"]] = e
            total = rep.get("totalElements") or 0
            # On s'arrête quand cette requête est entièrement récupérée, ou
            # quand la page ne rapporte plus rien de nouveau (la numérotation
            # des pages n'est pas précisée dans la documentation).
            if not nouveaux or (total and len(vus_requete) >= total):
                break
            page += 1
    return list(par_id.values())


def _brut_depuis_fichier(chemin: str) -> list[dict]:
    with open(chemin, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data.get("content", [])
    if data and isinstance(data[0], dict) and "content" in data[0]:
        return [e for rep in data for e in rep.get("content", [])]
    return data


def recuperer(cfg: dict, maintenant: datetime, fichier: str | None = None,
              brut: list[dict] | None = None) -> list[Evenement]:
    """Point d'entrée commun à toutes les sources.

    `fichier` (réponse enregistrée) ou `brut` (liste déjà en mémoire) permettent
    de tester sans appeler l'API.
    """
    if brut is None:
        brut = _brut_depuis_fichier(fichier) if fichier else _recuperer_brut(cfg, maintenant)
    fuseau_defaut = cfg.get("fuseau_defaut", "Europe/Paris")
    resultat = []
    for e in brut:
        ev = normaliser(e, fuseau_defaut)
        if ev is not None:
            resultat.append(ev)
    return resultat


# --------------------------------------------------------------------------
# Normalisation
# --------------------------------------------------------------------------

class _Texte(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.morceaux: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in {"br", "p", "li", "div", "tr"}:
            self.morceaux.append("\n")

    def handle_endtag(self, tag):
        if tag in {"p", "li", "div", "tr"}:
            self.morceaux.append("\n")

    def handle_data(self, data):
        self.morceaux.append(data)


def nettoyer_texte(texte: str | None) -> str:
    """Retire un éventuel HTML et normalise les espaces, en gardant les retours à la ligne."""
    if not texte:
        return ""
    p = _Texte()
    p.feed(texte)
    t = "".join(p.morceaux).replace("\xa0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r" *\n *", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def _fuseau(nom: str | None, defaut: str) -> ZoneInfo:
    for candidat in (nom, defaut, "Europe/Paris"):
        if not candidat:
            continue
        try:
            return ZoneInfo(candidat)
        except Exception:  # fuseau inconnu ou base tzdata absente
            continue
    return ZoneInfo("UTC")


def _heure(valeur: str | None):
    if not valeur:
        return None
    try:
        return datetime.strptime(valeur[:8], "%H:%M:%S").time()
    except ValueError:
        return None


def normaliser(e: dict, fuseau_defaut: str = "Europe/Paris") -> Evenement | None:
    """Réponse brute de l'API -> Evenement.

    Les horaires de l'API sont en UTC ; le champ `timezone` est celui du
    créateur de l'évènement. On convertit donc vers ce fuseau pour obtenir
    l'heure locale réelle.
    """
    if not e.get("dateEvenement") or e.get("id") is None:
        return None
    try:
        debut_utc = datetime.fromisoformat(e["dateEvenement"].replace("Z", "+00:00"))
    except ValueError:
        return None
    if debut_utc.tzinfo is None:
        debut_utc = debut_utc.replace(tzinfo=timezone.utc)
    debut_utc = debut_utc.astimezone(timezone.utc)

    h_debut = _heure(e.get("heureDebut"))
    if h_debut is not None and debut_utc.time() == datetime.min.time():
        # dateEvenement sans heure : on la reconstruit à partir de heureDebut
        debut_utc = datetime.combine(debut_utc.date(), h_debut, tzinfo=timezone.utc)

    fin_utc = None
    h_fin = _heure(e.get("heureFin"))
    if h_fin is not None:
        fin_utc = datetime.combine(debut_utc.date(), h_fin, tzinfo=timezone.utc)
        if fin_utc <= debut_utc:
            fin_utc += timedelta(days=1)

    tz = _fuseau(e.get("timezone"), fuseau_defaut)
    places_total = (e.get("nombrePlaceTotalPresentiel") or 0) + (e.get("nombrePlaceTotalDistance") or 0)
    places_prises = (e.get("nombreInscritPresentiel") or 0) + (e.get("nombreInscritDistance") or 0)

    return Evenement(
        source=NOM,
        id_source=str(e["id"]),
        titre=(e.get("titre") or "").strip() or "(sans titre)",
        debut=debut_utc.astimezone(tz),
        fin=fin_utc.astimezone(tz) if fin_utc else None,
        ville=e.get("ville") or "",
        code_postal=e.get("codePostal") or "",
        latitude=e.get("latitude"),
        longitude=e.get("longitude"),
        description=nettoyer_texte(e.get("description")),
        deroulement=nettoyer_texte(e.get("deroulement")),
        type=e.get("type") or "",
        modalites=list(e.get("modalites") or []),
        publics=list(e.get("publics") or []),
        objectifs=list(e.get("objectifs") or []),
        benefices=list(e.get("benefices") or []),
        operations=list(e.get("operations") or []),
        intervenants=[i.get("raisonSociale", "") for i in (e.get("intervenants") or []) if i.get("raisonSociale")],
        organisateur=e.get("libelleOrganisateurPrincipal") or "",
        etablissement=e.get("libelleEtablissement") or "",
        # 0 place déclarée = pas d'information de jauge, pas « complet »
        places_total=places_total or None,
        places_prises=places_prises if places_total else None,
        url=e.get("urlDetailEvenement") or "",
    )
