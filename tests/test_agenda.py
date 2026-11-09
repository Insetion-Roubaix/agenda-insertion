"""Lancer : python -m unittest discover -s tests -v"""

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agenda import demo, etat as suivi, identifiants, tri  # noqa: E402
from agenda.cibles import ics, page_web  # noqa: E402
from agenda.main import main  # noqa: E402
from agenda.modele import A_VERIFIER, ANNULE, ECARTE, RETENU, Evenement  # noqa: E402
from agenda.sources import mee  # noqa: E402

PARIS = ZoneInfo("Europe/Paris")
MAINTENANT = datetime(2026, 11, 5, 8, 0, tzinfo=PARIS)


def brut(**champs):
    base = {
        "id": 1, "titre": "Atelier CV", "ville": "Ville", "codePostal": "00000",
        "heureDebut": "08:00:00", "heureFin": "11:00:00", "timezone": "Europe/Paris",
        "dateEvenement": "2026-11-10T08:00:00.000+00:00", "type": "Atelier",
        "modalites": ["en physique"], "publics": [], "objectifs": [], "benefices": [],
        "operations": [], "nombrePlaceTotalPresentiel": 10, "nombreInscritPresentiel": 4,
        "description": "", "deroulement": "", "urlDetailEvenement": "https://exemple.invalid/1",
    }
    base.update(champs)
    return base


def evt(**champs) -> Evenement:
    e = mee.normaliser(brut(**champs))
    assert e is not None
    return e


def regles(**sections) -> tri.Regles:
    return tri.Regles.depuis_config(sections)


class TestNormalisation(unittest.TestCase):
    def test_heure_locale_depuis_utc(self):
        e = evt()  # 08:00 UTC en novembre = 09:00 à Paris
        self.assertEqual(e.debut.strftime("%H:%M"), "09:00")
        self.assertEqual(e.fin.strftime("%H:%M"), "12:00")

    def test_fuseau_du_createur(self):
        e = evt(timezone="Indian/Mauritius", heureDebut="05:00:00", heureFin="08:00:00",
                dateEvenement="2026-11-10T05:00:00.000+00:00")
        self.assertEqual(e.debut.strftime("%H:%M"), "09:00")

    def test_fin_apres_minuit_utc(self):
        e = evt(heureDebut="23:00:00", heureFin="01:00:00", dateEvenement="2026-11-10T23:00:00.000+00:00")
        self.assertGreater(e.fin, e.debut)

    def test_places_et_complet(self):
        self.assertEqual(evt().places_restantes, 6)
        self.assertTrue(evt(nombreInscritPresentiel=10).complet)
        sans_jauge = evt(nombrePlaceTotalPresentiel=0, nombreInscritPresentiel=0)
        self.assertIsNone(sans_jauge.places_restantes)
        self.assertFalse(sans_jauge.complet)

    def test_html_nettoye(self):
        e = evt(description="<p>Bonjour&nbsp;<b>tous</b></p><p>Suite</p>")
        self.assertEqual(e.description, "Bonjour tous\n\nSuite")

    def test_evenement_sans_date_ignore(self):
        self.assertIsNone(mee.normaliser({"id": 5, "titre": "x"}))

    def test_empreinte_stable_malgre_les_inscriptions(self):
        self.assertEqual(evt().empreinte(), evt(nombreInscritPresentiel=9).empreinte())
        self.assertNotEqual(evt().empreinte(), evt(titre="Autre titre").empreinte())


class TestTri(unittest.TestCase):
    def test_inclure_sans_accent_ni_casse(self):
        r = regles(inclure={"mots": ["numérique"]})
        e = evt(titre="Salon du NUMERIQUE")
        tri.classer(e, r)
        self.assertEqual(e.statut_tri, RETENU)

    def test_mot_entier_et_joker(self):
        r = regles(inclure={"mots": ["FLE", "recrut*"]}, defaut={"sans_correspondance": "ecarte"})
        for titre, attendu in [("Cours de FLE", RETENU), ("Bureau flexible", ECARTE),
                               ("Les recruteurs vous attendent", RETENU)]:
            e = evt(titre=titre)
            tri.classer(e, r)
            self.assertEqual(e.statut_tri, attendu, titre)

    def test_exclure_seulement_dans_le_titre(self):
        r = regles(inclure={"mots": ["atelier"], "champs": ["titre"]},
                   exclure={"mots": ["cadres"], "champs": ["titre"]})
        ouvert_aux_cadres = evt(titre="Atelier CV", publics=["Ouvert aux jeunes", "Ouvert aux cadres"])
        tri.classer(ouvert_aux_cadres, r)
        self.assertEqual(ouvert_aux_cadres.statut_tri, RETENU)
        pour_cadres = evt(titre="Atelier pour cadres")
        tri.classer(pour_cadres, r)
        self.assertEqual(pour_cadres.statut_tri, ECARTE)

    def test_a_verifier_et_defaut(self):
        r = regles(inclure={"mots": ["job dating"]}, a_verifier={"mots": ["forum"], "champs": ["titre"]})
        forum = evt(titre="Forum des métiers")
        autre = evt(titre="Visite de musée")
        tri.classer(forum, r)
        tri.classer(autre, r)
        self.assertEqual(forum.statut_tri, A_VERIFIER)
        self.assertEqual(autre.statut_tri, A_VERIFIER)  # défaut

    def test_sans_liste_inclure_tout_est_retenu(self):
        e = evt()
        tri.classer(e, regles())
        self.assertEqual(e.statut_tri, RETENU)

    def test_exclure_complets(self):
        r = regles(filtres={"exclure_complets": True})
        complet = evt(nombreInscritPresentiel=10)
        tri.classer(complet, r)
        self.assertEqual(complet.statut_tri, ECARTE)

    def test_champ_inconnu_refuse(self):
        with self.assertRaises(ValueError):
            regles(inclure={"mots": ["a"], "champs": ["inexistant"]})


REGLES_TYPES = dict(
    types={"accepter": ["atelier*", "forum*", "job dating", "porte*", "reunion*", "visite*"],
           "ecarter": ["conference*", "permanence*", "salon en ligne"], "autres": "a_verifier"},
)


class TestTypesEtVilles(unittest.TestCase):
    def statut(self, r, **champs):
        e = evt(**champs)
        tri.classer(e, r)
        return e

    def test_types_souhaites_retenus(self):
        r = regles(**REGLES_TYPES)
        for t in ("Atelier", "Forum", "Job dating", "Job dating inversé", "Portes ouvertes",
                  "Porte ouverte", "Réunion d'information", "Visites d'entreprise", "Ateliers"):
            self.assertEqual(self.statut(r, type=t).statut_tri, RETENU, t)

    def test_types_non_souhaites_ecartes(self):
        r = regles(**REGLES_TYPES)
        for t in ("Conférence", "Permanence", "Permanence emploi", "Salon en ligne"):
            e = self.statut(r, type=t)
            self.assertEqual(e.statut_tri, ECARTE, t)
            self.assertIn("type non souhaité", e.raisons[0])

    def test_type_inhabituel_ou_vide_a_verifier(self):
        r = regles(**REGLES_TYPES)
        for t in ("Café rencontre", ""):
            e = self.statut(r, type=t)
            self.assertEqual(e.statut_tri, A_VERIFIER, t)
            self.assertIn("type à confirmer", e.raisons[0])

    def test_type_ecarte_prime_sur_type_accepte(self):
        r = regles(**REGLES_TYPES)
        self.assertEqual(self.statut(r, type="Atelier salon en ligne").statut_tri, ECARTE)

    def test_villes_ecartees(self):
        r = regles(villes={"exclues": ["Wavrin", "Haubourdin", "Seclin", "Halluin", "Armentières"]})
        for v in ("Haubourdin", "HAUBOURDIN", "Armentieres", "Seclin"):
            self.assertEqual(self.statut(r, ville=v).statut_tri, ECARTE, v)
        for v in ("Roubaix", "Lille", "Lys-lez-Lannoy", "Villeneuve-d'Ascq", ""):
            self.assertEqual(self.statut(r, ville=v).statut_tri, RETENU, v)

    def test_villes_acceptees_liste_blanche(self):
        r = regles(villes={"acceptees": ["Roubaix", "Lys-lez-Lannoy"]})
        self.assertEqual(self.statut(r, ville="Lys-lez-Lannoy").statut_tri, RETENU)
        self.assertEqual(self.statut(r, ville="LYS LEZ LANNOY").statut_tri, RETENU)
        self.assertEqual(self.statut(r, ville="Lille").statut_tri, ECARTE)

    def test_evenement_possiblement_reserve_a_verifier(self):
        r = regles(a_verifier={"mots": ["uniquement", "reserve*"],
                               "champs": ["titre", "description", "publics"]})
        e = self.statut(r, titre="Café Langue - uniquement public de Vaucanson")
        self.assertEqual(e.statut_tri, A_VERIFIER)
        self.assertEqual(self.statut(r, titre="Café Langue").statut_tri, RETENU)


class TestReponseReelle(unittest.TestCase):
    """Cinq évènements réels renvoyés par l'API (Roubaix + 25 km)."""

    @classmethod
    def setUpClass(cls):
        import tomllib
        chemin = Path(__file__).parent / "fixtures" / "reponse_reelle_exemple.json"
        cls.evs = {e.id_source: e for e in mee.recuperer({}, MAINTENANT, fichier=str(chemin))}
        with open(Path(__file__).parent.parent / "config" / "regles.toml", "rb") as f:
            tri.trier(list(cls.evs.values()), tri.Regles.depuis_config(tomllib.load(f)))

    def test_tous_lus(self):
        self.assertEqual(len(self.evs), 5)

    def test_heures_locales(self):
        e = self.evs["799316"]  # 08:00 UTC en novembre = 09:00 à Paris
        self.assertEqual((e.debut.strftime("%H:%M"), e.fin.strftime("%H:%M")), ("09:00", "12:00"))
        self.assertEqual(e.ville, "Tourcoing")

    def test_classement_avec_la_configuration_livree(self):
        statuts = {i: (e.statut_tri, e.raisons) for i, e in self.evs.items()}
        self.assertEqual(statuts["799316"][0], RETENU)    # job dating, Tourcoing
        self.assertEqual(statuts["758625"][0], RETENU)    # forum, Lille
        self.assertEqual(statuts["788985"][0], RETENU)    # job dating, Lille
        self.assertEqual(statuts["734169"][0], ECARTE)    # atelier à Haubourdin
        self.assertIn("Haubourdin", statuts["734169"][1][0])
        self.assertEqual(statuts["779151"][0], ECARTE)    # atelier à distance
        self.assertEqual(statuts["779151"][1], ["à distance uniquement"])


class TestEvenementsReelsReserves(unittest.TestCase):
    """Échantillon de vrais évènements (Roubaix + 15 km) : réservés, normaux, écartés."""

    A_VERIFIER = ["770903", "731897", "777826", "758349", "773545", "713114", "769171", "721651", "785244", "800171"]
    RETENUS = ["772284", "799316", "782962", "758625", "801121", "789076"]
    ECARTES = {"731829": "type non souhaité", "794139": "à distance", "782668": "ville écartée", "779151": "à distance"}

    @classmethod
    def setUpClass(cls):
        import tomllib
        chemin = Path(__file__).parent / "fixtures" / "reponse_reelle_reserves.json"
        cls.evs = {e.id_source: e for e in mee.recuperer({}, MAINTENANT, fichier=str(chemin))}
        with open(Path(__file__).parent.parent / "config" / "regles.toml", "rb") as f:
            tri.trier(list(cls.evs.values()), tri.Regles.depuis_config(tomllib.load(f)))

    def test_evenements_reserves_signales(self):
        for i in self.A_VERIFIER:
            e = self.evs[i]
            self.assertEqual(e.statut_tri, A_VERIFIER, f"{e.titre} {e.raisons}")
            self.assertTrue(e.raisons[0].startswith("à regarder"))

    def test_evenements_ordinaires_retenus(self):
        for i in self.RETENUS:
            self.assertEqual(self.evs[i].statut_tri, RETENU, self.evs[i].titre)

    def test_evenements_ecartes_avec_la_bonne_raison(self):
        for i, raison in self.ECARTES.items():
            self.assertEqual(self.evs[i].statut_tri, ECARTE, i)
            self.assertIn(raison, self.evs[i].raisons[0])

    def test_faux_positif_de_la_creation_pour_tous_evite(self):
        # « réservé à une élite » n'a rien d'une restriction de public
        r = regles(a_verifier={"mots": ["reserve aux", "reserve au"], "champs": ["description"]})
        e = evt(description="trop complexe, trop risqué ou réservé à une élite ?")
        tri.classer(e, r)
        self.assertEqual(e.statut_tri, RETENU)


class TestFiltreDistanciel(unittest.TestCase):
    def classer(self, modalites, active=True):
        e = evt(modalites=modalites)
        tri.classer(e, regles(filtres={"exclure_distanciel": active}))
        return e.statut_tri

    def test_a_distance_seulement_est_ecarte(self):
        for m in (["à distance"], ["A DISTANCE"], ["Distanciel"], ["en ligne"], ["ADIST"]):
            self.assertEqual(self.classer(m), ECARTE, m)

    def test_physique_et_hybride_sont_gardes(self):
        for m in (["en physique"], ["en physique", "à distance"], []):
            self.assertEqual(self.classer(m), RETENU, m)

    def test_desactive_par_defaut(self):
        self.assertEqual(self.classer(["à distance"], active=False), RETENU)


class TestIdentifiants(unittest.TestCase):
    def test_nettoyage_des_collages_malheureux(self):
        self.assertEqual(identifiants.nettoyer('  "PAR_abc 123"\r\n'), "PAR_abc123")
        self.assertEqual(identifiants.nettoyer("ab\u200bcd\x16"), "abcd")  # invisibles, Ctrl+V
        self.assertEqual(identifiants.nettoyer(None), "")

    def test_lecture_du_fichier(self):
        import os
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "identifiants.txt"
            f.write_text("# commentaire\nFT_CLIENT_ID = \"abc\"\nFT_CLIENT_SECRET=def \n", encoding="utf-8")
            sauvegarde = {k: os.environ.pop(k, None) for k in ("FT_CLIENT_ID", "FT_CLIENT_SECRET")}
            try:
                self.assertEqual(identifiants.lire(f), ("abc", "def"))
                os.environ["FT_CLIENT_ID"] = "depuis-env"
                self.assertEqual(identifiants.lire(f), ("depuis-env", "def"))  # l'environnement prime
            finally:
                for k, v in sauvegarde.items():
                    os.environ.pop(k, None)
                    if v is not None:
                        os.environ[k] = v

    def test_fichier_absent(self):
        import os
        sauvegarde = {k: os.environ.pop(k, None) for k in ("FT_CLIENT_ID", "FT_CLIENT_SECRET")}
        try:
            self.assertEqual(identifiants.lire(Path("/inexistant/identifiants.txt")), ("", ""))
        finally:
            for k, v in sauvegarde.items():
                if v is not None:
                    os.environ[k] = v


class TestConfigurationLivree(unittest.TestCase):
    def test_la_requete_par_defaut_est_roubaix_15_km(self):
        import tomllib
        with open("config/sources.toml", "rb") as f:
            req = tomllib.load(f)["sources"]["mee"]["requetes"][0]
        self.assertEqual(req["rayon"], 15)
        self.assertAlmostEqual(req["latitude"], 50.69, delta=0.05)
        self.assertAlmostEqual(req["longitude"], 3.17, delta=0.05)

    def test_villes_ecartees_par_defaut(self):
        import tomllib
        with open("config/regles.toml", "rb") as f:
            r = tri.Regles.depuis_config(tomllib.load(f))
        for ville in ("Wavrin", "Haubourdin", "Seclin", "Halluin", "Armentières", "Pérenchies",
                      "Wervicq-Sud", "Lesquin", "Lezennes", "Loos", "Lambersart"):
            e = evt(ville=ville)
            tri.classer(e, r)
            self.assertEqual(e.statut_tri, ECARTE, ville)
        for ville in ("Roubaix", "Tourcoing", "Wattrelos", "Hem", "Croix", "Wasquehal",
                      "Lys-lez-Lannoy", "Lille", "La Madeleine", "Villeneuve-d'Ascq"):
            e = evt(ville=ville)
            tri.classer(e, r)
            self.assertEqual(e.statut_tri, RETENU, ville)

    def test_distanciel_ecarte_par_defaut(self):
        import tomllib
        with open("config/regles.toml", "rb") as f:
            self.assertTrue(tri.Regles.depuis_config(tomllib.load(f)).exclure_distanciel)


class TestSuivi(unittest.TestCase):
    def setUp(self):
        self.fin = MAINTENANT + timedelta(days=90)

    def passe(self, etat, evenements, jours=0, ok=("mee",), signature="s"):
        for e in evenements:
            e.statut_tri = RETENU
        return suivi.mettre_a_jour(etat, evenements, MAINTENANT + timedelta(days=jours),
                                   set(ok), self.fin, signature)

    def test_premier_import_sans_badge_nouveau_puis_nouveau(self):
        etat = {"version": 1, "signature": "", "evenements": {}}
        r1 = self.passe(etat, [evt(id=1)])
        self.assertFalse(r1[0].nouveau)
        r2 = self.passe(etat, [evt(id=1), evt(id=2)], jours=1)
        self.assertEqual({e.id_source: e.nouveau for e in r2}, {"1": False, "2": True})

    def test_modification_incremente_la_sequence(self):
        etat = {"version": 1, "signature": "", "evenements": {}}
        self.passe(etat, [evt(id=1)])
        r = self.passe(etat, [evt(id=1, titre="Nouveau titre")], jours=1)
        self.assertEqual(r[0].sequence, 1)
        self.assertTrue(r[0].modifie)
        r = self.passe(etat, [evt(id=1, titre="Nouveau titre")], jours=2)
        self.assertEqual(r[0].sequence, 1)  # inchangé : pas de nouvelle version

    def test_disparition_signalee_annulee_puis_reactivee(self):
        etat = {"version": 1, "signature": "", "evenements": {}}
        self.passe(etat, [evt(id=1), evt(id=2)])
        r = self.passe(etat, [evt(id=2)], jours=1)
        annule = [e for e in r if e.id_source == "1"][0]
        self.assertEqual(annule.cycle, ANNULE)
        r = self.passe(etat, [evt(id=1), evt(id=2)], jours=2)
        self.assertTrue(all(e.cycle == "" for e in r))

    def test_pas_d_annulation_si_source_en_panne_ou_muette_ou_filtres_changes(self):
        for kwargs, liste in [
            ({"ok": ()}, [evt(id=2)]),            # source en erreur
            ({}, []),                              # source muette
            ({"signature": "autre"}, [evt(id=2)]),  # filtres modifiés
        ]:
            etat = {"version": 1, "signature": "", "evenements": {}}
            self.passe(etat, [evt(id=1), evt(id=2)])
            r = self.passe(etat, liste, jours=1, **kwargs)
            self.assertFalse(any(e.cycle == ANNULE for e in r), kwargs)


class TestSorties(unittest.TestCase):
    def test_ics_plie_les_lignes_et_marque_les_annules(self):
        e = evt(titre="Un titre vraiment très long " * 6, description="a, b; c\nligne 2")
        e.statut_tri = RETENU
        a = evt(id=2, titre="Annulé")
        a.statut_tri, a.cycle = RETENU, ANNULE
        with tempfile.TemporaryDirectory() as d:
            chemin = ics.publier([e, a], {}, d, MAINTENANT)
            brut_ics = Path(chemin).read_bytes()
        for ligne in brut_ics.split(b"\r\n"):
            self.assertLessEqual(len(ligne), 75)
        texte = brut_ics.decode("utf-8")
        self.assertIn("STATUS:CANCELLED", texte)
        self.assertIn("a\\, b\\; c\\nligne 2", texte)
        self.assertIn("UID:mee-1@agenda-insertion", texte)

    def test_page_echappe_les_balises_script(self):
        e = evt(titre="</script><script>alert(1)</script>")
        e.statut_tri = RETENU
        with tempfile.TemporaryDirectory() as d:
            html = Path(page_web.publier([e], {}, d, MAINTENANT)).read_text(encoding="utf-8")
        donnees = html.split('id="donnees">')[1].split("</script>")[0]
        self.assertNotIn("<", donnees)
        self.assertEqual(json.loads(donnees)[0]["titre"], "</script><script>alert(1)</script>")


class TestExecutionComplete(unittest.TestCase):
    def test_demo_de_bout_en_bout(self):
        with tempfile.TemporaryDirectory() as d:
            code = main(["--demo", "--config", "config", "--sortie", d, "--etat", f"{d}/etat.json"])
            self.assertEqual(code, 0)
            self.assertTrue((Path(d) / "agenda.ics").exists())
            self.assertTrue((Path(d) / "index.html").exists())
            etat = json.loads((Path(d) / "etat.json").read_text(encoding="utf-8"))
            self.assertEqual(len(etat["evenements"]), 7)

    def test_donnees_de_demo_valides(self):
        evs = [mee.normaliser(b) for b in demo.exemple_brut(MAINTENANT)]
        self.assertTrue(all(evs))


if __name__ == "__main__":
    unittest.main()
