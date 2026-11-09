"""Évènements FICTIFS au format brut de l'API MEE (d'après les exemples de la
documentation), datés par rapport à aujourd'hui.

Servent aux tests et à `python lancer.py --demo`, pour voir le résultat sans
accès à l'API. Ne pas utiliser en production.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone


def _evt(maintenant: datetime, jours: int, h_debut: str, h_fin: str, **champs) -> dict:
    """h_debut / h_fin en UTC, comme l'API."""
    jour = (maintenant + timedelta(days=jours)).astimezone(timezone.utc).date()
    h = time.fromisoformat(h_debut)
    base = {
        "ville": "Ville-Exemple", "codePostal": "00000", "codeInsee": "00000",
        "longitude": 2.35, "latitude": 48.85, "description": "", "deroulement": "",
        "heureDebut": h_debut, "heureFin": h_fin, "timezone": "Europe/Paris",
        "operations": [], "diplomes": None, "objectifs": [], "publics": [],
        "type": "Atelier", "benefices": [], "modalites": ["en physique"],
        "nombrePlaceTotalDistance": 0, "nombrePlaceTotalPresentiel": 0,
        "nombreInscritDistance": 0, "nombreInscritPresentiel": 0,
        "dateEvenement": datetime.combine(jour, h, tzinfo=timezone.utc).isoformat(timespec="milliseconds"),
        "codesRome": [], "multisectoriel": False, "offresId": None,
        "libelleEtablissement": "Agence EXEMPLE", "libelleOrganisateurPrincipal": "France Travail",
    }
    base.update(champs)
    base["urlDetailEvenement"] = f"https://exemple.invalid/evenement/{base['id']}"
    return base


def exemple_brut(maintenant: datetime) -> list[dict]:
    return [
        # D'après l'exemple 1 de la documentation (fuseau de La Réunion/Maurice)
        _evt(maintenant, 3, "05:00:00", "08:00:00", id=900001,
             titre="FORUM DE L'ALTERNANCE", ville="Saint-Pierre", codePostal="97432",
             timezone="Indian/Mauritius", type="Forum",
             description="Rencontre avec les centres de formation et découverte des métiers en alternance.",
             deroulement="Ouverture du forum et réception des candidats à partir de 9h00 - Ramenez vos CV.",
             operations=["La semaine de l'alternance", "1 jeune 1 solution"],
             objectifs=["Découverte formation"],
             publics=["Ouvert aux personnes en situation de handicap", "Ouvert aux jeunes"],
             benefices=["Contrat en alternance"], nombrePlaceTotalPresentiel=300),
        # D'après l'exemple 2
        _evt(maintenant, 5, "06:30:00", "10:00:00", id=900002,
             titre="Etes-vous faits pour les métiers du commerce", ville="La Garde",
             codePostal="83130", type="Atelier",
             description="Session de détection de potentiel : rencontrez des professionnels du secteur "
                         "et testez vos aptitudes avec des exercices de mise en situation.",
             objectifs=["Marché du travail", "Découverte secteur / métier"],
             publics=["Ouvert à tous"], benefices=["Opportunité d'emploi", "Rencontre recruteur"],
             nombrePlaceTotalPresentiel=20, nombreInscritPresentiel=8),
        # Évènement complet, public insertion par l'activité économique
        _evt(maintenant, 2, "13:00:00", "16:00:00", id=900003,
             titre="Job dating propreté et services", ville="Lyon", codePostal="69003",
             type="Job Dating", objectifs=["Recrutement"],
             publics=["Ouvert au public insertion par l'activité économique",
                      "Ouvert aux bénéficiaires du RSA"],
             benefices=["Opportunité d'emploi", "Rencontre recruteur"],
             description="Entretiens courts avec des employeurs. Apportez un CV.",
             nombrePlaceTotalPresentiel=30, nombreInscritPresentiel=30,
             intervenants=[{"raisonSociale": "Entreprise Exemple Propreté", "siret": "00000000000000"}]),
        # À distance
        _evt(maintenant, 9, "08:00:00", "16:00:00", id=900004,
             titre="Salon en ligne des métiers du numérique", ville="", codePostal="",
             type="Salon en ligne", modalites=["à distance"], objectifs=["Recrutement", "Découverte secteur / métier"],
             publics=["Ouvert à tous"], nombrePlaceTotalDistance=500, nombreInscritDistance=120,
             description="Chat en direct avec des recruteurs du secteur numérique."),
        # Doit être écarté par le mot « cadres » dans le titre
        _evt(maintenant, 4, "08:00:00", "12:00:00", id=900005,
             titre="Rencontre des cadres dirigeants", ville="Nantes", codePostal="44000",
             type="Conférence", objectifs=["S'informer"], publics=["Ouvert aux cadres"]),
        # Aucun mot-clé : « à vérifier » par défaut
        _evt(maintenant, 15, "13:30:00", "15:30:00", id=900006,
             titre="Portes ouvertes du centre de formation", ville="Rennes", codePostal="35000",
             type="Portes ouvertes", objectifs=["Découverte formation"], publics=["Ouvert à tous"]),
        # Hors de la période de 30 jours de la page
        _evt(maintenant, 45, "09:00:00", "12:00:00", id=900007,
             titre="Réunion d'information : métiers de l'aide à domicile", ville="Marseille",
             codePostal="13001", type="Réunion d'information", objectifs=["S'informer", "Recrutement"],
             publics=["Ouvert à tous"]),
    ]
