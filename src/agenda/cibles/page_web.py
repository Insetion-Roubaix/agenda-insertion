"""Cible : page web de consultation (docs/index.html).

Une seule page, autonome (aucune police ni script externe) : les évènements
sont embarqués en JSON et filtrés dans le navigateur (recherche par mot-clé,
statut, type, période). Hébergeable telle quelle sur GitHub Pages.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

from ..modele import Evenement

NOM = "page_web"


def _fiche(ev: Evenement) -> dict:
    return {
        "cle": ev.cle,
        "titre": ev.titre,
        "jour": ev.debut.date().isoformat(),
        "h_debut": ev.debut.strftime("%H:%M"),
        "h_fin": ev.fin.strftime("%H:%M") if ev.fin else "",
        "lieu": ev.lieu,
        "type": ev.type,
        "modalites": ev.modalites,
        "publics": ev.publics,
        "objectifs": ev.objectifs,
        "benefices": ev.benefices,
        "operations": ev.operations,
        "intervenants": ev.intervenants,
        "organisateur": ev.organisateur,
        "etablissement": ev.etablissement,
        "description": ev.description,
        "deroulement": ev.deroulement,
        "places_restantes": ev.places_restantes,
        "places_total": ev.places_total,
        "complet": bool(ev.complet),
        "url": ev.url if ev.url.startswith(("http://", "https://")) else "",
        "statut": ev.statut_tri,
        "raisons": ev.raisons,
        "nouveau": ev.nouveau,
        "modifie": ev.modifie,
        "annule": ev.cycle == "annule",
    }


def publier(evenements: list[Evenement], cfg: dict, dossier: str, maintenant: datetime) -> str:
    inclure_ecartes = cfg.get("inclure_ecartes", True)
    fiches = [
        _fiche(e)
        for e in sorted(evenements, key=lambda e: e.debut)
        if inclure_ecartes or e.statut_tri != "ecarte"
    ]
    # Tout « < » est écrit \u003c : un texte d'évènement ne peut alors ni refermer
    # la balise <script> ni y ouvrir autre chose. Le navigateur le relit à l'identique.
    donnees = json.dumps(fiches, ensure_ascii=False).replace("<", "\\u003c")
    maj = maintenant.strftime("%d/%m/%Y à %H:%M")
    html = (
        MODELE.replace("__TITRE__", _echapper_html(cfg.get("titre", "Évènements emploi à relayer")))
        .replace("__MAJ__", maj)
        .replace("__FICHIER_ICS__", _echapper_html(cfg.get("fichier_ics", "agenda.ics")))
        .replace("__DONNEES__", donnees)
    )
    os.makedirs(dossier, exist_ok=True)
    chemin = os.path.join(dossier, cfg.get("fichier", "index.html"))
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(html)
    return chemin


def _echapper_html(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


MODELE = r"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>__TITRE__</title>
<style>
:root{
  --fond:#eef2f6; --surface:#ffffff; --encre:#14213d; --discret:#4d586c; --trait:#d3dbe6;
  --retenu:#0b6b66; --verif:#9a5200; --annule:#b42318; --info:#1d4ed8; --ecarte:#6b7385;
  color-scheme:light dark;
}
@media (prefers-color-scheme:dark){
  :root{
    --fond:#0f1724; --surface:#17212f; --encre:#e8edf4; --discret:#a3afc2; --trait:#2d3a4d;
    --retenu:#58c9c0; --verif:#f2b765; --annule:#ff9484; --info:#8fb4ff; --ecarte:#8c96a9;
  }
}
*{box-sizing:border-box}
html{font-size:17px}
body{margin:0;background:var(--fond);color:var(--encre);
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;line-height:1.5}
.page{max-width:60rem;margin:0 auto;padding:1.25rem 1rem 4rem}
h1{font-size:1.6rem;line-height:1.2;margin:.5rem 0 .25rem}
.maj{margin:0;color:var(--discret);font-size:.9rem}

.filtres{display:grid;grid-template-columns:repeat(auto-fit,minmax(11rem,1fr));gap:.75rem 1rem;
  margin:1.25rem 0 .5rem;padding:1rem;background:var(--surface);border:1px solid var(--trait);border-radius:.5rem}
.filtres label{display:flex;flex-direction:column;gap:.25rem;font-size:.9rem;color:var(--discret)}
.filtres .large{grid-column:1/-1}
input[type=search],select,.copie input{font:inherit;color:var(--encre);background:var(--fond);
  border:1px solid var(--trait);border-radius:.35rem;padding:.5rem .6rem;min-height:2.6rem;width:100%}
.case{flex-direction:row!important;align-items:center;gap:.5rem!important;color:var(--encre)!important}
.case input{width:1.15rem;height:1.15rem}
button{font:inherit;cursor:pointer;color:var(--encre);background:var(--surface);
  border:1px solid var(--encre);border-radius:.35rem;padding:.45rem .8rem;min-height:2.6rem}
:focus-visible{outline:3px solid var(--info);outline-offset:2px}
.compte{margin:.75rem 0 1rem;font-weight:600}

h2.semaine{font-size:1rem;font-weight:600;color:var(--discret);margin:2rem 0 .5rem;
  padding-bottom:.3rem;border-bottom:1px solid var(--trait)}
.jour-groupe{display:grid;grid-template-columns:4.6rem 1fr;gap:0 1rem;margin:.75rem 0}
.date{position:sticky;top:.75rem;align-self:start;text-align:center;line-height:1.1;padding-top:.2rem}
.date .sem{display:block;font-size:.9rem;color:var(--discret)}
.date .num{display:block;font-size:2.4rem;font-weight:700;letter-spacing:-.02em}
.date .mois{display:block;font-size:.9rem;color:var(--discret)}
.date.aujourdhui .num{color:var(--info)}
.evs{display:flex;flex-direction:column;gap:.75rem;min-width:0}

.ev{background:var(--surface);border:1px solid var(--trait);border-left:6px solid var(--retenu);
  border-radius:.4rem;padding:.8rem 1rem}
.ev.a_verifier{border-left-color:var(--verif)}
.ev.ecarte{border-left-color:var(--ecarte);opacity:.8}
.ev.annule{border-left-color:var(--annule)}
.ev.annule h3{text-decoration:line-through}
.heure{font-weight:700;font-variant-numeric:tabular-nums}
.ev h3{font-size:1.1rem;line-height:1.3;margin:.1rem 0 .4rem;overflow-wrap:anywhere}
.infos{display:flex;flex-wrap:wrap;gap:.25rem 1rem;color:var(--discret);font-size:.95rem}
.badges{display:flex;flex-wrap:wrap;gap:.4rem;margin:.45rem 0 0}
.badge{font-size:.85rem;border:1px solid currentColor;border-radius:.25rem;padding:0 .4rem}
.b-type{color:var(--encre)}
.b-verif{color:var(--verif);font-weight:600}
.b-ecarte{color:var(--ecarte)}
.b-annule,.b-complet{color:var(--annule);font-weight:600}
.b-nouveau,.b-modifie{color:var(--info);font-weight:600}
.places{color:var(--discret);font-size:.95rem;margin-top:.4rem}
details{margin-top:.6rem}
summary{cursor:pointer;color:var(--info);padding:.2rem 0;min-height:2rem}
.detail{font-size:.95rem}
.detail dt{font-weight:600;margin-top:.5rem}
.detail dd{margin:0;white-space:pre-line;overflow-wrap:anywhere}
.lien{display:inline-block;margin-top:.6rem;font-weight:600;color:var(--info)}

.seances{list-style:none;margin:.6rem 0 0;padding:0;display:flex;flex-direction:column;gap:.35rem}
.seance{display:flex;flex-wrap:wrap;gap:.2rem .9rem;align-items:baseline;padding:.4rem .6rem;
  background:var(--fond);border:1px solid var(--trait);border-radius:.3rem}
.quand{font-weight:600;font-variant-numeric:tabular-nums}
.pl{color:var(--discret);font-size:.95rem}
.pl.complet{color:var(--annule);font-weight:600}
.lien-seance{margin-left:auto;font-weight:600;color:var(--info)}
.seance.annule .quand{text-decoration:line-through}
.vide{padding:2rem 1rem;text-align:center;background:var(--surface);border:1px dashed var(--trait);border-radius:.5rem}
.abo{margin-top:2.5rem;background:var(--surface);border:1px solid var(--trait);border-radius:.5rem;padding:.5rem 1rem}
.copie{display:flex;gap:.5rem;margin:.5rem 0}
@media (max-width:34rem){
  .jour-groupe{grid-template-columns:1fr}
  .date{position:static;display:flex;gap:.4rem;align-items:baseline;text-align:left}
  .date .num{font-size:1.6rem}
}
@media print{.filtres,.abo{display:none}.ev{break-inside:avoid}}
</style>
</head>
<body>
<div class="page">
  <header>
    <h1>__TITRE__</h1>
    <p class="maj">Mis à jour le __MAJ__</p>
  </header>

  <form class="filtres" role="search" onsubmit="return false">
    <label class="large">Mot-clé
      <input type="search" id="q" placeholder="Ex. numérique, job dating, FLE, nom d'une entreprise" autocomplete="off">
    </label>
    <label>Statut
      <select id="statut">
        <option value="actifs">Retenus et à vérifier</option>
        <option value="retenu">Retenus seulement</option>
        <option value="a_verifier">À vérifier seulement</option>
        <option value="ecarte">Écartés par le tri</option>
        <option value="tous">Tous</option>
      </select>
    </label>
    <label>Type
      <select id="type"><option value="">Tous les types</option></select>
    </label>
    <label>Modalité
      <select id="modalite"><option value="">Toutes</option></select>
    </label>
    <label>Période
      <select id="periode">
        <option value="7">7 prochains jours</option>
        <option value="30" selected>30 prochains jours</option>
        <option value="90">3 prochains mois</option>
        <option value="0">Tout ce qui est à venir</option>
      </select>
    </label>
    <label class="case"><input type="checkbox" id="complets"> Masquer les évènements complets</label>
    <div><button type="button" id="raz">Réinitialiser</button></div>
  </form>

  <p class="compte" id="compte" aria-live="polite"></p>
  <main id="liste"></main>

  <details class="abo">
    <summary>Voir ces évènements dans mon agenda (Outlook, Google, téléphone)</summary>
    <p>Abonnez-vous à cette adresse : l'agenda se met à jour tout seul. Dans Outlook, choisissez
       « Ajouter un calendrier », puis « S'abonner à partir du web ».</p>
    <div class="copie">
      <input type="text" id="urlics" readonly aria-label="Adresse de l'abonnement">
      <button type="button" id="copier">Copier</button>
    </div>
  </details>
</div>

<script type="application/json" id="donnees">__DONNEES__</script>
<script>
(function(){
  var evs = JSON.parse(document.getElementById('donnees').textContent);
  var $ = function(id){ return document.getElementById(id); };
  var norm = function(s){ return (s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase(); };
  var jourLocal = function(d){ return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'); };
  var aujourdhui = jourLocal(new Date());
  var fmtSem = new Intl.DateTimeFormat('fr-FR',{weekday:'short'});
  var fmtMois = new Intl.DateTimeFormat('fr-FR',{month:'short'});
  var fmtLong = new Intl.DateTimeFormat('fr-FR',{day:'numeric',month:'long'});
  var dateDe = function(iso){ var p = iso.split('-'); return new Date(+p[0], +p[1]-1, +p[2]); };

  evs.forEach(function(e){
    e._txt = norm([e.titre,e.type,e.lieu,e.organisateur,e.etablissement,e.description,e.deroulement,
      e.publics.join(' '),e.objectifs.join(' '),e.benefices.join(' '),e.operations.join(' '),e.intervenants.join(' ')].join(' '));
  });

  function remplirListe(sel, valeurs){
    Array.from(new Set(valeurs.filter(Boolean))).sort().forEach(function(v){
      var o = document.createElement('option'); o.value = v; o.textContent = v; sel.appendChild(o);
    });
  }
  remplirListe($('type'), evs.map(function(e){ return e.type; }));
  remplirListe($('modalite'), [].concat.apply([], evs.map(function(e){ return e.modalites; })));

  function el(tag, cls, texte){
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (texte !== undefined) n.textContent = texte;
    return n;
  }
  function badge(cls, texte){ return el('span','badge '+cls,texte); }
  function def(dl, terme, valeur){
    if (!valeur || (Array.isArray(valeur) && !valeur.length)) return;
    dl.appendChild(el('dt',null,terme));
    dl.appendChild(el('dd',null,Array.isArray(valeur) ? valeur.join(', ') : valeur));
  }

  var fmtJour = new Intl.DateTimeFormat('fr-FR',{weekday:'short',day:'numeric',month:'short'});
  var cle = function(e){ return norm(e.titre)+'|'+norm(e.ville)+'|'+norm(e.type); };
  var quand = function(e){ return e.jour + ' ' + e.h_debut; };

  // Regroupe les séances d'un même évènement (même titre, même ville, même type)
  function grouper(seances){
    var index = {}, groupes = [];
    seances.forEach(function(e){
      var k = cle(e);
      if (!index[k]){ index[k] = {seances:[]}; groupes.push(index[k]); }
      index[k].seances.push(e);
    });
    groupes.forEach(function(g){
      g.seances.sort(function(a,b){ return quand(a) < quand(b) ? -1 : 1; });
      g.tete = g.seances[0];
    });
    groupes.sort(function(a,b){ return quand(a.tete) < quand(b.tete) ? -1 : 1; });
    return groupes;
  }

  function ligneSeance(s, premierJour){
    var li = el('li','seance'+(s.annule?' annule':''));
    var horaire = (s.jour !== premierJour ? fmtJour.format(dateDe(s.jour)) + ', ' : '') +
      s.h_debut + (s.h_fin ? ' à ' + s.h_fin : '');
    li.appendChild(el('span','quand',horaire));
    if (s.complet) li.appendChild(el('span','pl complet','Complet'));
    else if (s.places_restantes !== null) li.appendChild(el('span','pl',s.places_restantes + ' places restantes sur ' + s.places_total));
    if (s.annule) li.appendChild(badge('b-annule','annulé ?'));
    if (s.nouveau) li.appendChild(badge('b-nouveau','Nouveau'));
    if (s.url){
      var l = el('a','lien-seance','Fiche et inscription');
      l.href = s.url; l.target = '_blank'; l.rel = 'noopener noreferrer';
      li.appendChild(l);
    }
    return li;
  }

  function carte(g){
    var e = g.tete, multi = g.seances.length > 1;
    var tousAnnules = g.seances.every(function(s){ return s.annule; });
    var a = el('article','ev '+e.statut+(tousAnnules?' annule':''));
    a.appendChild(el('div','heure', multi ? g.seances.length + ' séances'
      : e.h_debut + (e.h_fin ? ' à ' + e.h_fin : '')));
    a.appendChild(el('h3',null,e.titre));
    var infos = el('div','infos');
    if (e.lieu) infos.appendChild(el('span',null,e.lieu));
    if (e.organisateur) infos.appendChild(el('span',null,e.organisateur));
    a.appendChild(infos);

    var b = el('div','badges');
    if (tousAnnules) b.appendChild(badge('b-annule','Retiré de la source : annulé ?'));
    if (!multi && e.nouveau) b.appendChild(badge('b-nouveau','Nouveau'));
    if (e.modifie && !tousAnnules) b.appendChild(badge('b-modifie','Modifié'));
    if (e.type) b.appendChild(badge('b-type',e.type));
    e.modalites.forEach(function(m){ b.appendChild(badge('b-type',m)); });
    if (e.statut === 'a_verifier') b.appendChild(badge('b-verif','À vérifier'));
    if (e.statut === 'ecarte') b.appendChild(badge('b-ecarte','Écarté'));
    if (!multi && e.complet) b.appendChild(badge('b-complet','Complet'));
    if (b.children.length) a.appendChild(b);

    if (multi){
      var ul = el('ul','seances');
      g.seances.forEach(function(s){ ul.appendChild(ligneSeance(s, e.jour)); });
      a.appendChild(ul);
    } else if (e.places_restantes !== null && !e.complet){
      a.appendChild(el('div','places', e.places_restantes + ' places restantes sur ' + e.places_total));
    }

    var d = document.createElement('details');
    d.appendChild(el('summary',null,'Détails'));
    var dl = el('dl','detail');
    if (e.raisons.length) def(dl,'Pourquoi ce classement', e.raisons.join(' ; '));
    def(dl,'Publics', e.publics);
    def(dl,'Objectifs', e.objectifs);
    def(dl,'Bénéfices', e.benefices);
    def(dl,'Opérations', e.operations);
    def(dl,'Intervenants', e.intervenants);
    def(dl,'Établissement', e.etablissement);
    def(dl,'Description', e.description);
    def(dl,'Déroulement', e.deroulement);
    d.appendChild(dl);
    if (!multi && e.url){
      var l = el('a','lien','Fiche de l\u2019évènement et inscription');
      l.href = e.url; l.target = '_blank'; l.rel = 'noopener noreferrer';
      d.appendChild(l);
    }
    a.appendChild(d);
    return a;
  }

  function lundi(d){ var x = new Date(d); var j = (x.getDay()+6)%7; x.setDate(x.getDate()-j); return jourLocal(x); }

  function filtrer(){
    var mots = norm($('q').value).split(/\s+/).filter(Boolean);
    var statut = $('statut').value, type = $('type').value, modalite = $('modalite').value;
    var jours = +$('periode').value, masquerComplets = $('complets').checked;
    var limite = null;
    if (jours){ var l = new Date(); l.setDate(l.getDate()+jours); limite = jourLocal(l); }
    return evs.filter(function(e){
      if (e.jour < aujourdhui) return false;
      if (limite && e.jour > limite) return false;
      if (statut === 'actifs' && e.statut === 'ecarte') return false;
      if (statut !== 'actifs' && statut !== 'tous' && e.statut !== statut) return false;
      if (type && e.type !== type) return false;
      if (modalite && e.modalites.indexOf(modalite) < 0) return false;
      if (masquerComplets && e.complet) return false;
      return mots.every(function(m){ return e._txt.indexOf(m) >= 0; });
    });
  }

  function afficher(){
    var liste = $('liste'); liste.textContent = '';
    var res = filtrer();
    var groupes = grouper(res);
    var avenir = evs.filter(function(e){ return e.jour >= aujourdhui; });
    var ecartes = avenir.filter(function(e){ return e.statut === 'ecarte'; }).length;
    var voirEcartes = $('statut').value === 'ecarte' || $('statut').value === 'tous';
    var total = voirEcartes ? avenir.length : avenir.length - ecartes;
    var texte = groupes.length + (groupes.length > 1 ? ' évènements affichés' : ' évènement affiché');
    if (res.length !== groupes.length) texte += ' (' + res.length + ' séances)';
    texte += ' sur ' + total + ' à venir';
    if (ecartes && !voirEcartes) texte += ' ; ' + ecartes + ' écartés par le tri, visibles avec le statut « Écartés »';
    $('compte').textContent = texte;
    if (!groupes.length){
      var v = el('div','vide');
      v.appendChild(el('p',null,'Aucun évènement ne correspond. Élargissez la période, changez de statut ou videz la recherche.'));
      liste.appendChild(v); return;
    }
    var semaine = null, jour = null, bloc = null;
    groupes.forEach(function(g){
      var e = g.tete;
      var s = lundi(dateDe(e.jour));
      if (s !== semaine){
        semaine = s; jour = null;
        liste.appendChild(el('h2','semaine','Semaine du ' + fmtLong.format(dateDe(s))));
      }
      if (e.jour !== jour){
        jour = e.jour;
        var gr = el('section','jour-groupe');
        var d = dateDe(jour);
        var dt = el('div','date' + (jour === aujourdhui ? ' aujourdhui' : ''));
        dt.appendChild(el('span','sem',fmtSem.format(d)));
        dt.appendChild(el('span','num',String(d.getDate())));
        dt.appendChild(el('span','mois',fmtMois.format(d)));
        bloc = el('div','evs');
        gr.appendChild(dt); gr.appendChild(bloc); liste.appendChild(gr);
      }
      bloc.appendChild(carte(g));
    });
  }

  ['q','statut','type','modalite','periode','complets'].forEach(function(id){
    $(id).addEventListener(id === 'q' ? 'input' : 'change', afficher);
  });
  $('raz').addEventListener('click', function(){
    $('q').value=''; $('statut').value='actifs'; $('type').value=''; $('modalite').value='';
    $('periode').value='30'; $('complets').checked=false; afficher();
  });

  $('urlics').value = new URL('__FICHIER_ICS__', location.href).href;
  $('copier').addEventListener('click', function(){
    var champ = $('urlics'); champ.select();
    if (navigator.clipboard) navigator.clipboard.writeText(champ.value);
    else document.execCommand('copy');
    $('copier').textContent = 'Copié';
    setTimeout(function(){ $('copier').textContent = 'Copier'; }, 2000);
  });

  afficher();
})();
</script>
</body>
</html>
"""
