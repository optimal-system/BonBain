"""Serveur BonBain pour Raspberry Pico W.

Le Pico W se connecte à ce serveur (sur le réseau local) et interroge :
- GET /bonbain        : état global — meilleure plage, LEDs, aiguille (JSON compact) ;
- GET /bonbain/plages : classement détaillé de toutes les plages (JSON) ;
- GET /bonbain/carte  : carte des plages avec indicateurs (PNG).

Le serveur ne doit être joignable que depuis le réseau local (maison),
jamais exposé sur Internet : il écoute par défaut sur 0.0.0.0 pour être
accessible depuis le Raspberry Pico W du même réseau local. En mode dégradé
(pas de clé API / pas de réseau), des conditions simulées sont utilisées
pour que l'objet reste fonctionnel.
"""

import json
import logging
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer

import bonbain.analyse as analyse
import bonbain.base_plages as base_plages
import bonbain.collecte as collecte
import bonbain.opsys as opsys

LOGGER = logging.getLogger("bonbain.serveur")

PERIODE_DEFAUT = 5
CLE_API_VARIABLE_ENV = "BONBAIN_OPENWEATHERMAP_KEY"


def _conditions_simulees(plage):
    """Conditions de repli déterministes pour une plage, utilisées quand les
    API sont indisponibles : l'objet décoratif reste animé même sans réseau."""
    return {
        "vent_vitesse_ms": 4.2,
        "vent_rafale_ms": 7.8,
        "vent_direction_deg": 315.0,
        "temperature_air_c": 18.5,
        "temperature_mer_c": 16.0,
        "nebulosite_pct": 35.0,
        "ensoleillement_pct": 65.0,
        "source": "simulation",
    }


def collecter_conditions(plage, apikey=None, ouvrir=None, log=None):
    """Collecte les conditions d'une plage en fusionnant OpenWeatherMap,
    Copernicus et, en dernier recours, la simulation."""
    conditions = {}
    meteo = collecte.collecter_openweathermap(plage, apikey=apikey, ouvrir=ouvrir, log=log)
    if meteo:
        conditions.update(meteo)
    mer = collecte.collecter_copernicus(plage, ouvrir=ouvrir, log=log)
    if mer:
        conditions.update(mer)
    if not conditions:
        LOGGER.warning("Sources indisponibles pour %s : conditions simulées", plage["nom"])
        conditions = _conditions_simulees(plage)
    return conditions


def evaluer_toutes_plages(jour=None, periode=PERIODE_DEFAUT, apikey=None, ouvrir=None, log=None):
    """Évalue toutes les plages de la base et retourne le classement."""
    if jour is None:
        jour = date.today()
    coefficient = opsys.coefficient_maree(jour)
    rapports = []
    for plage in base_plages.base_plages():
        conditions = collecter_conditions(plage, apikey=apikey, ouvrir=ouvrir, log=log)
        rapports.append(analyse.evaluer_plage(plage, conditions, coefficient, periode))
    return analyse.classer_plages(rapports), coefficient


def etat_compact(classement, coefficient):
    """État minimal destiné au Pico W : une seule plage, LEDs et aiguille."""
    meilleur = classement[0]
    return {
        "meilleure_plage": meilleur["nom"],
        "score": meilleur["score"],
        "led_score": meilleur["couleur_led"],
        "led_vent": meilleur["led_vent"],
        "aiguille_vent_deg": meilleur["direction_vent_deg"],
        "coefficient_maree": coefficient,
    }


class RequeteHandler(BaseHTTPRequestHandler):
    serveur_options = None

    def do_GET(self):
        if self.path == "/bonbain":
            self._repondre_json(self._etat())
        elif self.path == "/bonbain/plages":
            self._repondre_json(self._classement())
        elif self.path == "/bonbain/carte":
            self._repondre_carte()
        else:
            self.send_error(404, "Route inconnue")

    def _etat(self):
        options = self.serveur_options or {}
        classement, coefficient = evaluer_toutes_plages(
            periode=options.get("periode", PERIODE_DEFAUT),
            apikey=options.get("apikey"),
        )
        return etat_compact(classement, coefficient)

    def _classement(self):
        options = self.serveur_options or {}
        classement, coefficient = evaluer_toutes_plages(
            periode=options.get("periode", PERIODE_DEFAUT),
            apikey=options.get("apikey"),
        )
        return {"coefficient_maree": coefficient, "plages": classement}

    def _repondre_json(self, donnees):
        corps = json.dumps(donnees).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def _repondre_carte(self):
        import io

        import bonbain.affichage as affichage

        options = self.serveur_options or {}
        classement, _coefficient = evaluer_toutes_plages(
            periode=options.get("periode", PERIODE_DEFAUT),
            apikey=options.get("apikey"),
        )
        fig = affichage.afficher_resultats(classement, chemin_image=None)
        tampon = io.BytesIO()
        fig.savefig(tampon, format="png", dpi=100)
        corps = tampon.getvalue()
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def log_message(self, format, *args):
        LOGGER.info("HTTP %s %s", self.address_string(), format % args)


def demarrer(hote="0.0.0.0", port=8266, periode=PERIODE_DEFAUT, apikey=None):
    """Démarre le serveur HTTP pour le Pico W (réseau local uniquement)."""
    import os

    if apikey is None:
        apikey = os.environ.get(CLE_API_VARIABLE_ENV)
    handler = type(
        "HandlerBonBain", (RequeteHandler,), {"serveur_options": {"periode": periode, "apikey": apikey}}
    )
    serveur = HTTPServer((hote, port), handler)
    LOGGER.info("Serveur BonBain sur http://%s:%d (réseau local)", hote, port)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("Arrêt du serveur")
    finally:
        serveur.server_close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s : %(message)s")
    demarrer()
