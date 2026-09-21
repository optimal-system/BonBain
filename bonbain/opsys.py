"""Algorithme OPSYS : horaire des marées, coefficient, hauteur d'eau.

Modèle harmonique simplifié calé sur le port de référence de Brest.
Quatre constituantes semi-diurnes suffisent pour la Manche :
- M2  (lunaire principal,        période 12.4206 h),
- S2  (solaire principal,       période 12.0000 h),
- N2  (lunaire elliptique,      période 12.6583 h),
- K2  (luni-solaire,            période 11.9677 h).

La hauteur de mer s'écrit  h(t) = N0 + Σ Hi·cos(ωi·(t − t0) − φi).
Les heures de pleine mer (PM) et basse mer (BM) sont obtenues en balayant
la journée au pas de 10 minutes et en repérant les maxima/minima locaux.
Le coefficient de marée vaut  c = 100 · (PM − BM) / (2·U)  où U est
l'unité de hauteur du port (Brest : U = 3.45 m, marnage moyen de
vives-eaux 6.90 m). Il est borné à [20, 120].
"""

import math
from datetime import datetime, timedelta, timezone

PORTS_REFERENCE = {
    "Brest": {
        "unite_hauteur_m": 3.45,
        "niveau_moyen_m": 3.10,
        "constituantes": (
            ("M2", 2.11, 0.00, 12.4206),
            ("S2", 0.75, 1.90, 12.0000),
            ("N2", 0.42, 1.20, 12.6583),
            ("K2", 0.20, 2.40, 11.9677),
        ),
    },
}

PORT_DEFAUT = "Brest"
PAS_MINUTES = 10


def hauteur_mer(instant, port=PORT_DEFAUT):
    """Hauteur de mer (m) au-dessus du zéro hydrographique à un instant donné."""
    params = PORTS_REFERENCE[port]
    t = instant.timestamp()
    hauteur = params["niveau_moyen_m"]
    for _nom, amplitude, phase, periode_h in params["constituantes"]:
        pulsation = 2.0 * math.pi / (periode_h * 3600.0)
        hauteur += amplitude * math.cos(pulsation * t - phase)
    return hauteur


def _extremas(jour, port):
    """Liste des (instant, hauteur, 'PM'|'BM') d'une journée, triée par instant."""
    debut = datetime(jour.year, jour.month, jour.day, tzinfo=timezone.utc)
    points = []
    for i in range(24 * 60 // PAS_MINUTES + 1):
        instant = debut + timedelta(minutes=i * PAS_MINUTES)
        points.append((instant, hauteur_mer(instant, port)))
    extremas = []
    for i in range(1, len(points) - 1):
        precedant, courant, suivant = points[i - 1][1], points[i][1], points[i + 1][1]
        if courant > precedant and courant >= suivant:
            extremas.append((points[i][0], courant, "PM"))
        elif courant < precedant and courant <= suivant:
            extremas.append((points[i][0], courant, "BM"))
    return extremas


def horaire_marees(jour, port=PORT_DEFAUT):
    """Horaire des marées d'un jour : liste de dict (instant, hauteur, type)."""
    return [
        {
            "instant": instant.strftime("%H:%M"),
            "hauteur_m": round(hauteur, 2),
            "type": type_maree,
        }
        for instant, hauteur, type_maree in _extremas(jour, port)
    ]


def coefficient_maree(jour, port=PORT_DEFAUT):
    """Coefficient de marée du jour (20 à 120), à partir du plus grand marnage."""
    params = PORTS_REFERENCE[port]
    extremas = _extremas(jour, port)
    marnages = []
    for i in range(len(extremas) - 1):
        marnages.append(abs(extremas[i + 1][1] - extremas[i][1]))
    if not marnages:
        return 70
    marnage = max(marnages)
    coefficient = 100.0 * marnage / (2.0 * params["unite_hauteur_m"])
    return int(round(min(120.0, max(20.0, coefficient))))


def hauteur_eau_plage(plage, coefficient):
    """Hauteur d'eau disponible sur la plage, interpolation depuis la table
    ((coef, hauteur), ...) de la plage. Retourne (hauteur_m, type_plage)."""
    hauteurs = list(plage["hauteurs_eau_coef"])
    hauteurs.sort(key=lambda point: point[0])
    coef = min(max(coefficient, hauteurs[0][0]), hauteurs[-1][0])
    for i in range(len(hauteurs) - 1):
        c1, h1 = hauteurs[i]
        c2, h2 = hauteurs[i + 1]
        if c1 <= coef <= c2:
            if c2 == c1:
                return h1, type_plage(plage, coefficient)
            ratio = (coef - c1) / (c2 - c1)
            return h1 + ratio * (h2 - h1), type_plage(plage, coefficient)
    return hauteurs[-1][1], type_plage(plage, coefficient)


def type_plage(plage, coefficient):
    """Type de plage pour un coefficient donné, selon la table ((coef, type), ...).
    La valeur s'applique au-dessus du seuil du même rang que le coefficient."""
    table = list(plage["type_plage_coef"])
    table.sort(key=lambda point: point[0])
    for i, (c, _t) in enumerate(table):
        if coefficient <= c:
            return table[min(i, len(table) - 1)][1]
    return table[-1][1]
