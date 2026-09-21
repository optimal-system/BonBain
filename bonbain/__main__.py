"""Point d'entrée du projet BonBain.

Collecte les données météo/océanographiques, analyse les plages, affiche
les résultats (carte + LEDs + aiguille) et lance le serveur pour le Pico W.
"""

import argparse
import logging
import os
import sys

import matplotlib

if not os.environ.get("BONBAIN_INTERACTIF"):
    matplotlib.use("Agg")

import bonbain.affichage as affichage
import bonbain.analyse as analyse
import bonbain.base_plages as base_plages
import bonbain.opsys as opsys
import bonbain.serveur as serveur
from datetime import date

LOGGER = logging.getLogger("bonbain")


def analyser(jour=None, periode=5, apikey=None, ouvrir=None):
    """Pipeline complet : marées (OPSYS) + collecte + notes + classement."""
    if jour is None:
        jour = date.today()
    coefficient = opsys.coefficient_maree(jour)
    rapports = []
    for plage in base_plages.base_plages():
        conditions = serveur.collecter_conditions(plage, apikey=apikey, ouvrir=ouvrir)
        rapports.append(analyse.evaluer_plage(plage, conditions, coefficient, periode))
    return analyse.classer_plages(rapports), coefficient


def afficher_classement(classement, coefficient):
    print("Coefficient de marée du jour : %d" % coefficient)
    print()
    for i, rapport in enumerate(classement, start=1):
        print(
            "%d. %-24s %5.1f/100  LED %s  vent %s (%.0f°, %.1f m/s)"
            % (
                i,
                rapport["nom"],
                rapport["score"],
                rapport["couleur_led"],
                rapport["led_vent"],
                rapport["direction_vent_deg"],
                rapport["vitesse_vent_ms"],
            )
        )
    print()
    meilleur = classement[0]
    print("Meilleure plage : %s" % meilleur["nom"])
    print(meilleur["description"])


def main(argv=None):
    parseur = argparse.ArgumentParser(
        prog="bonbain",
        description="BonBain : trouve la meilleure plage pour se baigner.",
    )
    parseur.add_argument(
        "--serveur", action="store_true",
        help="démarre le serveur HTTP pour le Raspberry Pico W (réseau local)",
    )
    parseur.add_argument("--port", type=int, default=8266, help="port du serveur")
    parseur.add_argument("--periode", type=int, default=5, help="indice de fréquentation (1-9)")
    parseur.add_argument(
        "--carte", default="resultats/carte_bonbain.png",
        help="chemin de l'image de la carte générée",
    )
    parseur.add_argument(
        "--sans-carte", action="store_true", help="ne pas générer la carte",
    )
    arguments = parseur.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s : %(message)s")

    if arguments.serveur:
        serveur.demarrer(port=arguments.port, periode=arguments.periode)
        return 0

    classement, coefficient = analyser(periode=arguments.periode)
    afficher_classement(classement, coefficient)
    if not arguments.sans_carte:
        figure = affichage.afficher_resultats(classement, chemin_image=arguments.carte)
        LOGGER.info("Carte générée : %s", arguments.carte)
        if os.environ.get("BONBAIN_INTERACTIF"):
            import matplotlib.pyplot as plt

            plt.show()
    return 0


if __name__ == "__main__":
    sys.exit(main())
