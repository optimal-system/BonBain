"""Fond de carte OpenStreetMap pour l'affichage BonBain.

Télécharge les tuiles OSM couvrant les plages, les assemble en une image
continue et fournit les bornes géographiques correspondantes.

- Cache : les tuiles sont stockées dans fond_carte_cache/ pour ne pas
  re-télécharger à chaque exécution (respect des serveurs OSM).
- Repli : si le réseau est indisponible et le cache vide, la carte est
  dessinée sans fond (fond bleu), l'objet reste fonctionnel.
- Licence : tuiles © OpenStreetMap contributors, ODbL.
"""

import hashlib
import logging
import os
import urllib.request

import matplotlib.pyplot as plt
import numpy as np

LOGGER = logging.getLogger("bonbain.fond_carte")

URL_TUILE = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
TAILLE_TUILE = 256
DOSSIER_CACHE = "fond_carte_cache"
ZOOM_DEFAUT = 13
ZOOM_MINIMUM = 9
MARGE_PIXELS = 96


def _lat_lon_vers_tuile(latitude, longitude, zoom):
    """Coordonnées (x, y) flottantes de la tuile contenant un point."""
    n = 2 ** zoom
    x = (longitude + 180.0) / 360.0 * n
    lat_rad = np.radians(latitude)
    y = (1.0 - np.arcsinh(np.tan(lat_rad)) / np.pi) / 2.0 * n
    return x, y


def _tuile_vers_lat_lon(x, y, zoom):
    """Latitude/longitude du coin nord-ouest d'une tuile."""
    n = 2 ** zoom
    longitude = x / n * 360.0 - 180.0
    lat_rad = np.arctan(np.sinh(np.pi * (1.0 - 2.0 * y / n)))
    return float(np.degrees(lat_rad)), longitude


def _telecharger_tuile(zoom, x, y):
    """Télécharge une tuile (cache disque d'abord, OSM sinon). Retourne
    un tableau image ou None si indisponible."""
    chemin = os.path.join(DOSSIER_CACHE, f"osm_{zoom}_{x}_{y}.png")
    if os.path.exists(chemin):
        return _lire_image(chemin)
    os.makedirs(DOSSIER_CACHE, exist_ok=True)
    url = URL_TUILE.format(z=zoom, x=x, y=y)
    requete = urllib.request.Request(
        url, headers={"User-Agent": "BonBain/1.0 (projet pedagogique)"}
    )
    try:
        with urllib.request.urlopen(requete, timeout=10) as reponse:
            donnees = reponse.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        LOGGER.warning("Tuile OSM indisponible : %s", url)
        return None
    with open(chemin, "wb") as fichier:
        fichier.write(donnees)
    LOGGER.info("Tuile téléchargée : %s", url)
    return _lire_image(chemin)


def _lire_image(chemin):
    try:
        image = plt.imread(chemin)
    except (OSError, ValueError):
        return None
    if image is None or image.size == 0:
        return None
    if image.dtype != np.uint8:
        image = (255 * image).astype(np.uint8)
    return image


def fond_carte(latitude_min, latitude_max, longitude_min, longitude_max,
               zoom=ZOOM_DEFAUT):
    """Assemble le fond de carte pour une zone géographique.

    Retourne (image, lat_min, lat_max, lon_min, lon_max) où image est un
    tableau (hauteur, largeur, 3) ou None si aucune tuile disponible.
    """
    x_min_flottant, y_min_flottant = _lat_lon_vers_tuile(latitude_max, longitude_min, zoom)
    x_max_flottant, y_max_flottant = _lat_lon_vers_tuile(latitude_min, longitude_max, zoom)
    x_min, x_max = int(np.floor(x_min_flottant)), int(np.ceil(x_max_flottant))
    y_min, y_max = int(np.floor(y_min_flottant)), int(np.ceil(y_max_flottant))
    colonnes = x_max - x_min
    lignes = y_max - y_min
    if colonnes <= 0 or lignes <= 0 or colonnes * lignes > 36:
        LOGGER.warning("Zone de carte trop grande ou vide : fond ignoré")
        return None
    largeur = colonnes * TAILLE_TUILE
    hauteur = lignes * TAILLE_TUILE
    fond = np.zeros((hauteur, largeur, 3), dtype=np.uint8)
    au_moins_une = False
    for i in range(colonnes):
        for j in range(lignes):
            tuile = _telecharger_tuile(zoom, x_min + i, y_min + j)
            if tuile is None:
                continue
            tuile = tuile[:, :, :3]
            if tuile.shape[0] < TAILLE_TUILE or tuile.shape[1] < TAILLE_TUILE:
                tuile = tuile[:TAILLE_TUILE, :TAILLE_TUILE]
            fond[j * TAILLE_TUILE:(j + 1) * TAILLE_TUILE,
             i * TAILLE_TUILE:(i + 1) * TAILLE_TUILE, :] = tuile
            au_moins_une = True
    if not au_moins_une:
        return None
    lat_max, lon_min = _tuile_vers_lat_lon(x_min, y_min, zoom)
    lat_min, lon_max = _tuile_vers_lat_lon(x_max, y_max, zoom)
    return fond, lat_min, lat_max, lon_min, lon_max


def afficher_fond(ax, rapports, zoom=ZOOM_DEFAUT):
    """Dessine le fond de carte couvrant les plages sur un axe matplotlib.
    Si la zone des plages est trop étendue pour ce zoom, le zoom est réduit
    automatiquement jusqu'à ce que la zone tienne (jusqu'à ZOOM_MINIMUM).
    Retourne True si un fond a été affiché."""
    if not rapports:
        return False
    latitudes = [r["latitude"] for r in rapports]
    longitudes = [r["longitude"] for r in rapports]
    resultat = None
    for zoom_essai in range(min(zoom, ZOOM_DEFAUT), ZOOM_MINIMUM - 1, -1):
        resultat = fond_carte(
            min(latitudes), max(latitudes),
            min(longitudes), max(longitudes), zoom=zoom_essai,
        )
        if resultat is not None:
            break
    if resultat is None:
        return False
    image, lat_min, lat_max, lon_min, lon_max = resultat
    ax.imshow(
        image, extent=[lon_min, lon_max, lat_min, lat_max],
        origin="upper", zorder=0, interpolation="bilinear",
    )
    ax.set_xlim(lon_min, lon_max)
    ax.set_ylim(lat_min, lat_max)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    return True
