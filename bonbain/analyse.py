"""Analyse des données : note de baignade par plage, puis classement.

Chaque plage reçoit une note de 0 à 100 par critère, puis une note globale
sur 100 (moyenne pondérée) :
- hauteur d'eau disponible (25 %),
- force du vent (20 %),
- orientation du vent par rapport à la plage (15 %),
- type de plage (10 %),
- température (15 %),
- ensoleillement (10 %),
- fréquentation (5 %).
"""

SEUILS_COULEURS = ((50.0, "rouge"), (75.0, "orange"), (101.0, "vert"))
SEUILS_VENT = ((8.0, "bleu"), (101.0, "violet"))
TYPES_PLAGE_SCORE = {"sable": 100.0, "galets": 70.0, "boue": 30.0}
FREQUENTATION_SCORE = {"faible": 100.0, "moyen": 80.0, "bondé": 40.0}

POIDS_CRITERES = {
    "hauteur_eau": 0.25,
    "vent_force": 0.20,
    "vent_orientation": 0.15,
    "type_plage": 0.10,
    "temperature": 0.15,
    "ensoleillement": 0.10,
    "frequentation": 0.05,
}


def _borne(valeur, minimum=0.0, maximum=100.0):
    return max(minimum, min(maximum, valeur))


def note_hauteur_eau(hauteur_m):
    """Note selon la hauteur d'eau disponible (m). Croissante : plus d'eau
    disponible = meilleure baignade (0 m = impossible, 5 m et plus = parfait)."""
    if hauteur_m <= 0.0:
        return 0.0
    return _borne(20.0 * hauteur_m)


def note_vent_force(vitesse_ms, rafale_ms=None):
    """Note selon la force du vent. Moins de 3 m/s = parfait, au-delà de
    10 m/s = baignade déplaisante."""
    vitesse = float(vitesse_ms)
    if rafale_ms is not None:
        vitesse = max(vitesse, 0.6 * float(rafale_ms))
    if vitesse <= 3.0:
        return 100.0
    if vitesse >= 12.0:
        return 0.0
    return _borne(100.0 * (12.0 - vitesse) / 9.0)


def note_vent_orientation(vent_deg, orientation_mer):
    """Note selon l'orientation du vent par rapport à la plage.

    `orientation_mer` est un couple (min, max) délimitant les directions où
    la plage fait face à la mer. Un vent de terre (offshore) est idéal pour
    la nage (mer calme), un vent de mer (onshore) apporte houle et déferlantes.
    La note vaut 100 pour un vent offshore et décroît vers 0 à l'onshore.
    """
    min_mer, max_mer = orientation_mer
    vent = float(vent_deg) % 360.0
    if min_mer <= max_mer:
        dans_mer = min_mer <= vent <= max_mer
        centre_mer = (min_mer + max_mer) / 2.0
    else:
        dans_mer = vent >= min_mer or vent <= max_mer
        centre_mer = ((min_mer + max_mer + 360.0) / 2.0) % 360.0
    ecart = abs(((vent - centre_mer) + 180.0) % 360.0 - 180.0)
    if dans_mer:
        return _borne(100.0 * (ecart / (180.0 * 0.5)))
    if ecart <= 90.0:
        return _borne(100.0 - (100.0 * ecart) / 90.0)
    return 100.0


def note_type_plage(type_plage_str):
    return _borne(TYPES_PLAGE_SCORE.get(type_plage_str, 50.0))


def note_temperature(air_c, mer_c=None):
    """Note selon la température de l'air, pondérée par celle de la mer
    (la moyenne air/mer compte pour 60 % si la donnée mer est disponible)."""
    note_air = _borne((float(air_c) - 15.0) * (100.0 / 13.0))
    if mer_c is None:
        return note_air
    note_mer = _borne((float(mer_c) - 14.0) * (100.0 / 8.0))
    return _borne(0.4 * note_air + 0.6 * note_mer)


def note_ensoleillement(pct):
    return _borne(float(pct))


def note_frequentation(niveau):
    return _borne(FREQUENTATION_SCORE.get(niveau, 50.0))


def note_globale(notes):
    """Note globale sur 100 : moyenne pondérée des critères."""
    total = sum(POIDS_CRITERES[critere] * notes[critere] for critere in POIDS_CRITERES)
    return round(total, 1)


def couleur_score(score):
    """Couleur LED score global : vert si bon, orange si correct, rouge si mauvais."""
    for seuil, couleur in SEUILS_COULEURS:
        if score < seuil:
            return couleur
    return "vert"


def couleur_vent(vitesse_ms):
    """Couleur LED vent : bleu si calme, violet si fort."""
    for seuil, couleur in SEUILS_VENT:
        if vitesse_ms < seuil:
            return couleur
    return "violet"


def niveau_frequentation(plage, periode):
    """Niveau de fréquentation selon la période, depuis la table de la plage.
    La valeur s'applique au-dessus du seuil du même rang que la période."""
    table = list(plage["frequentation_periode"])
    table.sort(key=lambda point: point[0])
    for seuil, niveau in table:
        if periode <= seuil:
            return niveau
    return table[-1][1]


def evaluer_plage(plage, conditions, coefficient, periode):
    """Évalue une plage complète et retourne un rapport détaillé.

    `conditions` regroupe les données collectées (openweathermap/copernicus),
    `coefficient` est le coefficient de marée du jour et `periode` l'indice de
    fréquentation de la période (1 = très calme, 9 = très fréquentée).
    """
    import bonbain.opsys as opsys

    hauteur_eau, type_plage_str = opsys.hauteur_eau_plage(plage, coefficient)
    vitesse_vent = conditions.get("vent_vitesse_ms", 0.0)
    rafale = conditions.get("vent_rafale_ms")
    direction_vent = conditions.get("vent_direction_deg", 0.0)
    notes = {
        "hauteur_eau": note_hauteur_eau(hauteur_eau),
        "vent_force": note_vent_force(vitesse_vent, rafale),
        "vent_orientation": note_vent_orientation(direction_vent, plage["orientation_mer"]),
        "type_plage": note_type_plage(type_plage_str),
        "temperature": note_temperature(
            conditions.get("temperature_air_c", 0.0),
            conditions.get("temperature_mer_c"),
        ),
        "ensoleillement": note_ensoleillement(conditions.get("ensoleillement_pct", 0.0)),
        "frequentation": note_frequentation(niveau_frequentation(plage, periode)),
    }
    score = note_globale(notes)
    return {
        "nom": plage["nom"],
        "score": score,
        "couleur_led": couleur_score(score),
        "led_vent": couleur_vent(vitesse_vent),
        "direction_vent_deg": round(direction_vent, 1),
        "vitesse_vent_ms": round(vitesse_vent, 1),
        "hauteur_eau_m": round(hauteur_eau, 2),
        "type_plage": type_plage_str,
        "frequentation": niveau_frequentation(plage, periode),
        "notes_detail": {critere: round(valeur, 1) for critere, valeur in notes.items()},
        "description": plage["description"],
        "longitude": plage["longitude"],
        "latitude": plage["latitude"],
    }


def classer_plages(rapports):
    """Classe les plages par note globale décroissante."""
    return sorted(rapports, key=lambda rapport: rapport["score"], reverse=True)
