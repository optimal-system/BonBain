"""Collecte des données océanographiques et météorologiques.

Deux sources :
- OpenWeatherMap : météo courante (vent, température, nuages, soleil levé/couché),
- Copernicus Marine : température de surface de la mer (SST).

Chaque collecteur retourne un dictionnaire de conditions normalisées pour une
plage, ou None si la source est indisponible (pas de clé API, pas de réseau).
Les collecteurs ne lèvent jamais d'exception : le serveur renvoie toujours une
réponse au Raspberry Pico W, même en mode dégradé.
"""

import json
import logging
import urllib.error
import urllib.request

LOGGER = logging.getLogger("bonbain.collecte")

OPENWEATHERMAP_URL = (
    "https://api.openweathermap.org/data/2.5/weather"
    "?lat={lat}&lon={lon}&appid={apikey}&units=metric&lang=fr"
)

COPERNICUS_URL = (
    "https://marine-api.open-meteo.com/v1/marine"
    "?latitude={lat}&longitude={lon}&current=sea_surface_temperature"
)

REQUETE_TIMEOUT = 10


def collecter_openweathermap(plage, apikey=None, ouvrir=None, log=None):
    """Collecte la météo OpenWeatherMap pour une plage.

    `ouvrir` permet d'injecter une fonction d'ouverture d'URL (pour les tests).
    Retourne un dictionnaire de conditions normalisées, ou None.
    """
    if ouvrir is None:
        ouvrir = _ouvrir_url
    if not apikey:
        LOGGER.warning("OpenWeatherMap : pas de clé API, source ignorée")
        return None
    url = OPENWEATHERMAP_URL.format(
        lat=plage["latitude"], lon=plage["longitude"], apikey=apikey
    )
    try:
        donnees = _telecharger_json(url, ouvrir, log)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        LOGGER.warning("OpenWeatherMap : source indisponible")
        return None
    if not donnees or donnees.get("cod") not in (200, "200"):
        LOGGER.warning("OpenWeatherMap : réponse inattendue")
        return None
    return normaliser_openweathermap(donnees)


def normaliser_openweathermap(donnees):
    """Transforme une réponse OpenWeatherMap en conditions normalisées."""
    vent = donnees.get("wind", {})
    nuages = donnees.get("clouds", {}).get("all", 0)
    principal = donnees.get("main", {})
    sys_donnees = donnees.get("sys", {})
    return {
        "vent_vitesse_ms": float(vent.get("speed", 0.0)),
        "vent_rafale_ms": float(vent.get("gust", vent.get("speed", 0.0))),
        "vent_direction_deg": float(vent.get("deg", 0.0)) % 360.0,
        "temperature_air_c": float(principal.get("temp", 0.0)),
        "temperature_ressentie_c": float(principal.get("feels_like", principal.get("temp", 0.0))),
        "pression_hpa": float(principal.get("pressure", 1015.0)),
        "humidite_pct": float(principal.get("humidity", 0.0)),
        "nebulosite_pct": float(nuages),
        "ensoleillement_pct": max(0.0, 100.0 - float(nuages)),
        "lever_soleil": int(sys_donnees.get("sunrise", 0)),
        "coucher_soleil": int(sys_donnees.get("sunset", 0)),
        "source": "openweathermap",
    }


def collecter_copernicus(plage, ouvrir=None, log=None):
    """Collecte la température de surface de la mer (SST) via l'API Copernicus Marine.

    `ouvrir` permet d'injecter une fonction d'ouverture d'URL (pour les tests).
    Retourne un dictionnaire de conditions normalisées, ou None.
    """
    if ouvrir is None:
        ouvrir = _ouvrir_url
    url = COPERNICUS_URL.format(lat=plage["latitude"], lon=plage["longitude"])
    try:
        donnees = _telecharger_json(url, ouvrir, log)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        LOGGER.warning("Copernicus : source indisponible")
        return None
    if not donnees:
        return None
    try:
        sst = float(donnees["current"]["sea_surface_temperature"])
    except (KeyError, IndexError, TypeError, ValueError):
        LOGGER.warning("Copernicus : format de réponse inattendu")
        return None
    return {
        "temperature_mer_c": sst,
        "source": "copernicus",
    }


def _telecharger_json(url, ouvrir, log):
    if log:
        log(f"Requête : {url}")
    with ouvrir(url, timeout=REQUETE_TIMEOUT) as reponse:
        return json.loads(reponse.read().decode("utf-8"))


def _ouvrir_url(url, timeout=REQUETE_TIMEOUT):
    requete = urllib.request.Request(url, headers={"User-Agent": "BonBain/1.0"})
    return urllib.request.urlopen(requete, timeout=timeout)
