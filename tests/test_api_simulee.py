"""Teste le client de l'API contre un faux serveur local (aucun accès réseau externe)."""

import json
import os
import sys
import threading
import unittest
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agenda.sources import mee  # noqa: E402

TOTAL = 250


def faux_evenement(i: int) -> dict:
    return {"id": i, "titre": f"Évènement {i}", "dateEvenement": "2026-12-01T08:00:00.000+00:00",
            "heureDebut": "08:00:00", "heureFin": "10:00:00", "timezone": "Europe/Paris"}


def fabriquer_serveur(base_page: int, ignore_page: bool = False):
    appels = {"jeton": [], "recherches": []}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, code, data):
            corps = json.dumps(data).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(corps)))
            self.end_headers()
            self.wfile.write(corps)

        def do_POST(self):
            longueur = int(self.headers.get("Content-Length", 0))
            corps = self.rfile.read(longueur).decode()
            url = urllib.parse.urlparse(self.path)
            if url.path.endswith("/access_token"):
                appels["jeton"].append(urllib.parse.parse_qs(corps))
                return self._json(200, {"access_token": "JETON-BIDON", "expires_in": 1499})
            if self.headers.get("Authorization") != "Bearer JETON-BIDON":
                return self._json(401, {"erreur": "non autorisé"})
            q = urllib.parse.parse_qs(url.query)
            taille = int(q.get("size", ["10"])[0])
            page = 0 if ignore_page else int(q.get("page", [str(base_page)])[0]) - base_page
            filtres = json.loads(corps)
            appels["recherches"].append((page, taille, filtres))
            debut = page * taille
            ids = range(1, TOTAL + 1)
            sel = [faux_evenement(i) for i in ids][debut:debut + taille]
            self._json(200, {"totalElements": TOTAL, "content": sel})

    serveur = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=serveur.serve_forever, daemon=True).start()
    return serveur, appels


class TestClientApi(unittest.TestCase):
    def setUp(self):
        os.environ["FT_CLIENT_ID"] = "id"
        os.environ["FT_CLIENT_SECRET"] = "secret"
        self.maintenant = datetime(2026, 11, 5, 8, 0, tzinfo=ZoneInfo("Europe/Paris"))

    def cfg(self, serveur, **plus):
        port = serveur.server_address[1]
        return {"url_api": f"http://127.0.0.1:{port}", "url_jeton": f"http://127.0.0.1:{port}/connexion/oauth2/access_token",
                "fenetre_jours": 30, **plus}

    def lancer(self, base_page=0, ignore_page=False, **plus):
        serveur, appels = fabriquer_serveur(base_page, ignore_page)
        self.addCleanup(lambda: (serveur.shutdown(), serveur.server_close()))
        evs = mee.recuperer(self.cfg(serveur, page_depart=base_page, **plus), self.maintenant)
        return evs, appels

    def test_pagination_complete_numerotation_depuis_0(self):
        evs, appels = self.lancer(base_page=0, requetes=[{"nom": "a", "departements": ["59"]}])
        self.assertEqual(len(evs), TOTAL)
        self.assertEqual(len(appels["recherches"]), 3)  # 100 + 100 + 50
        self.assertEqual(appels["recherches"][0][2]["departements"], ["59"])
        self.assertIn("dateDebut", appels["recherches"][0][2])

    def test_pagination_numerotation_depuis_1(self):
        evs, _ = self.lancer(base_page=1)
        self.assertEqual(len(evs), TOTAL)

    def test_scopes_et_grant_envoyes(self):
        _, appels = self.lancer()
        envoi = appels["jeton"][0]
        self.assertEqual(envoi["grant_type"], ["client_credentials"])
        self.assertEqual(envoi["scope"], ["api_evenementsv1 evenements"])

    def test_requetes_multiples_sans_doublon(self):
        evs, appels = self.lancer(requetes=[{"nom": "a"}, {"nom": "b", "typeEvenement": 18}])
        self.assertEqual(len(evs), TOTAL)
        self.assertEqual(len(appels["recherches"]), 6)

    def test_serveur_qui_ignore_la_page_ne_boucle_pas(self):
        evs, appels = self.lancer(ignore_page=True)
        self.assertEqual(len(evs), 100)
        self.assertLessEqual(len(appels["recherches"]), 2)

    def test_mauvais_identifiants_message_clair(self):
        serveur, _ = fabriquer_serveur(0)
        self.addCleanup(lambda: (serveur.shutdown(), serveur.server_close()))
        cfg = self.cfg(serveur)
        with self.assertRaises(mee.ErreurSource):
            mee.rechercher("MAUVAIS", {}, url_api=cfg["url_api"])


if __name__ == "__main__":
    unittest.main()
