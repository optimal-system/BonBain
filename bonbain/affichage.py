"""Affichage des résultats : carte des plages, LEDs (score, vent) et aiguille.

Les indicateurs de l'objet décoratif :
- LED score global : vert = bon, orange = correct, rouge = mauvais ;
- LED vent : bleu = calme, violet = fort ;
- aiguille de direction du vent : de 0 à 360° (boussole à 16 pointes).

Fonctionne en mode interactif si un backend graphique est disponible, sinon
génère une image PNG (backend Agg) — typiquement sur un Raspberry Pico W.
"""

import logging

import matplotlib
import matplotlib.pyplot as plt

LOGGER = logging.getLogger("bonbain.affichage")

COULEURS_LED = {
    "vert": "#22c55e",
    "orange": "#f97316",
    "rouge": "#ef4444",
    "bleu": "#3b82f6",
    "violet": "#8b5cf6",
}

POINTES = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
           "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO"]


def carte_plages(rapports, chemin_image=None):
    """Carte des plages avec marqueurs colorés selon le score, LEDs et aiguille
    du vent de la meilleure plage. Retourne la figure matplotlib."""
    fig = plt.figure(figsize=(12, 8))
    ax_carte = fig.add_axes([0.05, 0.35, 0.6, 0.6])
    longueurs = [r["longitude"] for r in rapports]
    latitudes = [r["latitude"] for r in rapports]
    marge_lon = max(0.05, (max(longueurs) - min(longueurs)) * 0.3)
    marge_lat = max(0.05, (max(latitudes) - min(latitudes)) * 0.3)
    ax_carte.set_xlim(min(longueurs) - marge_lon, max(longueurs) + marge_lon)
    ax_carte.set_ylim(min(latitudes) - marge_lat, max(latitudes) + marge_lat)
    ax_carte.set_facecolor("#bae6fd")
    ax_carte.set_title("BonBain — où se baigner aujourd'hui ?")
    ax_carte.set_xlabel("Longitude")
    ax_carte.set_ylabel("Latitude")
    for i, rapport in enumerate(rapports, start=1):
        couleur = COULEURS_LED[rapport["couleur_led"]]
        ax_carte.scatter(
            rapport["longitude"], rapport["latitude"],
            s=300 + 20 * rapport["score"], c=couleur,
            edgecolors="black", linewidths=1.2, zorder=3,
        )
        ax_carte.annotate(
            f"{i}. {rapport['nom']}\n{rapport['score']}/100",
            (rapport["longitude"], rapport["latitude"]),
            xytext=(12, 12), textcoords="offset points", fontsize=9,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.85),
        )
    if chemin_image:
        fig.savefig(chemin_image, dpi=100)
        LOGGER.info("Carte enregistrée : %s", chemin_image)
    return fig


def _disque_led(ax, x, y, couleur, label, etat):
    ax.add_patch(plt.Circle((x, y), 0.12, color=couleur, ec="black", lw=1.5))
    ax.text(x, y - 0.30, f"{label} : {etat}", ha="center", va="top", fontsize=9)


def tableau_leds(fig, meilleur):
    """Ajoute au bas de la figure les LEDs score global et vent, ainsi que
    l'aiguille de direction du vent (meilleure plage)."""
    ax_led = fig.add_axes([0.05, 0.05, 0.6, 0.22])
    ax_led.set_xlim(0, 3)
    ax_led.set_ylim(0, 1)
    ax_led.axis("off")
    ax_led.set_title("Indicateurs (meilleure plage : %s)" % meilleur["nom"])
    _disque_led(ax_led, 0.4, 0.55, COULEURS_LED[meilleur["couleur_led"]], "Score", "%s (%d/100)" % (meilleur["couleur_led"], meilleur["score"]))
    _disque_led(ax_led, 1.1, 0.55, COULEURS_LED[meilleur["led_vent"]], "Vent", "%s (%.1f m/s)" % (meilleur["led_vent"], meilleur["vitesse_vent_ms"]))
    return ax_led


def aiguille_vent(fig, direction_deg, vitesse_ms=None):
    """Ajoute une boussole avec l'aiguille de direction du vent (0-360°)."""
    ax_boussole = fig.add_axes([0.70, 0.05, 0.26, 0.9])
    ax_boussole.set_aspect("equal")
    ax_boussole.axis("off")
    ax_boussole.set_title("Direction du vent")
    ax_boussole.add_patch(plt.Circle((0, 0), 1.0, fc="#f8fafc", ec="black", lw=1.5))
    for i, pointe in enumerate(POINTES):
        angle = float(i) * 360.0 / len(POINTES)
        x, y = _polaires_vers_xy(angle, 0.85)
        ax_boussole.text(x, y, pointe, ha="center", va="center", fontsize=8)
    for angle in range(0, 360, 45):
        x1, y1 = _polaires_vers_xy(angle, 0.95)
        x2, y2 = _polaires_vers_xy(angle, 1.05)
        ax_boussole.plot([x1, x2], [y1, y2], color="black", lw=1)
    x_pointe, y_pointe = _polaires_vers_xy(direction_deg, 0.75)
    ax_boussole.annotate(
        "",
        xy=(x_pointe, y_pointe), xytext=(0, 0),
        arrowprops=dict(arrowstyle="-|>", color="#dc2626", lw=2.5),
    )
    texte = "Vent %.0f°" % direction_deg
    if vitesse_ms is not None:
        texte += " — %.1f m/s" % vitesse_ms
    ax_boussole.text(0, -1.25, texte, ha="center", fontsize=10)
    return ax_boussole


def _polaires_vers_xy(angle_deg, rayon):
    import math
    angle_rad = math.radians(angle_deg)
    return rayon * math.sin(angle_rad), rayon * math.cos(angle_rad)


def afficher_resultats(rapports, chemin_image="resultats/carte_bonbain.png"):
    """Génère l'affichage complet et sauvegarde l'image. Retourne la figure."""
    rapports_classes = sorted(rapports, key=lambda r: r["score"], reverse=True)
    meilleur = rapports_classes[0]
    fig = carte_plages(rapports_classes, chemin_image=None)
    tableau_leds(fig, meilleur)
    aiguille_vent(fig, meilleur["direction_vent_deg"], meilleur["vitesse_vent_ms"])
    if chemin_image:
        fig.savefig(chemin_image, dpi=100)
        LOGGER.info("Affichage généré : %s", chemin_image)
    return fig
