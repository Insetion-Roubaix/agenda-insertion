"""Premier contact avec l'API : récupère quelques évènements réels et les
enregistre dans reponse_brute.json (à transmettre pour ajuster le projet).

Lancer depuis le dossier du projet (ou double-cliquer sur tester_api.bat) :
    python outils/test_api.py --tester-pagination

La recherche reprend la première requête de config/sources.toml (par exemple
Roubaix + 15 km), pour tester exactement ce que le programme fera chaque jour.
Avec --tout, tous les évènements de la période de config/sources.toml sont
récupérés (comme le programme quotidien) et un bilan par type et par ville
est affiché.

Identifiant et clé secrète : fichier identifiants.txt (ou variables
FT_CLIENT_ID / FT_CLIENT_SECRET), sinon demandés au clavier. Ils ne sont
écrits nulle part ailleurs : reponse_brute.json ne contient que des
évènements publics.
"""

import argparse
import collections
import json
import sys
import tomllib
from datetime import date, datetime, timedelta
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "src"))

from agenda import identifiants  # noqa: E402
from agenda.sources import mee  # noqa: E402

AIDE_INVALID_CLIENT = """
Le serveur d'authentification n'a pas reconnu cet identifiant / cette clé.
Vérifiez dans l'ordre :
  1. Les deux valeurs sont copiées EN ENTIER depuis la page de votre application
     sur francetravail.io (bouton « copier » si disponible), sans rien ajouter.
  2. L'identifiant et la clé secrète ne sont pas inversés.
  3. Ce sont bien ceux de l'application associée à « Mes évènements emploi ».
  4. En cas de doute, générez une nouvelle clé secrète sur la page de
     l'application, puis remplacez-la dans identifiants.txt.
Modifiez ensuite le fichier identifiants.txt (Bloc-notes) et relancez."""


def corps_depuis_config() -> dict:
    chemin = RACINE / "config" / "sources.toml"
    with open(chemin, "rb") as f:
        cfg = tomllib.load(f)
    requetes = cfg.get("sources", {}).get("mee", {}).get("requetes") or [{}]
    return {k: v for k, v in requetes[0].items() if k != "nom"}


def bilan(evenements: list[dict]) -> None:
    print(f"\n{len(evenements)} évènements récupérés.")
    for titre, cle in (("Types", "type"), ("Villes", "ville")):
        compte = collections.Counter((e.get(cle) or "(vide)").strip() for e in evenements)
        print(f"\n{titre} :")
        for valeur, n in compte.most_common(25 if cle == "ville" else None):
            print(f"  {n:4d}  {valeur}")
    modalites = collections.Counter(m for e in evenements for m in (e.get("modalites") or ["(vide)"]))
    print("\nModalités :")
    for valeur, n in modalites.most_common():
        print(f"  {n:4d}  {valeur}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--departement", action="append",
                   help="remplace la zone de config/sources.toml par ce département (répétable)")
    p.add_argument("--jours", type=int, default=30, help="fenêtre de recherche (défaut 30)")
    p.add_argument("--taille", type=int, default=5, help="évènements par page (défaut 5)")
    p.add_argument("--sortie", default="reponse_brute.json")
    p.add_argument("--tout", action="store_true",
                   help="récupère tous les évènements (toutes les pages et toutes les requêtes de la configuration)")
    p.add_argument("--tester-pagination", action="store_true",
                   help="compare les pages 0 et 1 pour savoir où commence la numérotation")
    args = p.parse_args()

    client_id, secret = identifiants.lire()
    if not client_id:
        client_id = identifiants.nettoyer(input("Identifiant client : "))
    if not secret:
        secret = identifiants.nettoyer(input("Clé secrète (visible à l'écran) : "))

    # Contrôle visuel sans afficher les secrets en entier
    print(f"Identifiant lu : {client_id[:8]}... ({len(client_id)} caractères)")
    print(f"Clé secrète lue : {len(secret)} caractères")

    try:
        jeton = mee.obtenir_jeton(client_id, secret)
        print("Jeton obtenu : l'identifiant et la clé fonctionnent.")
        corps = {"departements": args.departement} if args.departement else corps_depuis_config()
        corps["dateDebut"] = date.today().isoformat()
        corps["dateFin"] = (date.today() + timedelta(days=args.jours)).isoformat()
        print("Corps de la requête :", json.dumps(corps, ensure_ascii=False))

        rep = mee.rechercher(jeton, corps, page=0, taille=args.taille)
        if args.tester_pagination:
            rep1 = mee.rechercher(jeton, corps, page=1, taille=args.taille)
            ids0 = [e["id"] for e in rep.get("content", [])]
            ids1 = [e["id"] for e in rep1.get("content", [])]
            if ids0 and ids0 == ids1:
                print("Pages 0 et 1 identiques : la numérotation commence à 1 (mettre page_depart = 1).")
            elif ids0 and ids1:
                print("Pages 0 et 1 différentes : la numérotation commence à 0 (réglage par défaut).")
            else:
                print("Pagination non concluante (pas assez de résultats ?).")
    except mee.ErreurSource as e:
        print(f"\nÉCHEC : {e}", file=sys.stderr)
        if "invalid_client" in str(e):
            print(AIDE_INVALID_CLIENT, file=sys.stderr)
        return 1

    if args.tout:
        try:
            with open(RACINE / "config" / "sources.toml", "rb") as f:
                cfg_src = tomllib.load(f)
            cfg = {**cfg_src.get("general", {}), **cfg_src.get("sources", {}).get("mee", {})}
            print("\nRécupération de tous les évènements (cela peut prendre un moment)...")
            tous = mee._recuperer_brut(cfg, datetime.now().astimezone())
        except mee.ErreurSource as e:
            print(f"\nÉCHEC : {e}", file=sys.stderr)
            return 1
        rep = {"totalElements": len(tous), "content": tous}
        Path(args.sortie).write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
        bilan(tous)
        print(f"\nRéponse brute enregistrée dans : {args.sortie}")
        return 0

    Path(args.sortie).write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    contenu = rep.get("content", [])
    print(f"\n{rep.get('totalElements')} évènements au total pour cette recherche, "
          f"{len(contenu)} dans la réponse enregistrée.")
    for e in contenu:
        print(f" - {e.get('dateEvenement', '?')[:10]}  {e.get('titre')}  ({e.get('ville')})")
    print(f"\nRéponse brute enregistrée dans : {args.sortie}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
