"""Base de données des plages du projet BonBain.

Chaque plage décrit ses conditions optimales de baignade :
- mer, longitude/latitude (WGS84),
- orientation par rapport à la mer en degrés (ex. (340, 30) pour une plage orientée nord),
- hauteurs d'eau selon coefficients de marée (liste (coef, hauteur)),
- type de plage selon coef (liste (coef, type)) : la valeur s'applique au-dessus du seuil,
- fréquentation selon période (liste (période, niveau)) : la valeur s'applique au-dessus du seuil,
- description textuelle.
"""

MER_MANCHE = "Manche"


def tourony():
    return {
        "nom": "Tourony",
        "mer": MER_MANCHE,
        "longitude": -3.495338,
        "latitude": 48.829045,
        "orientation_mer": (340, 30),
        "hauteurs_eau_coef": ((20, 0), (50, 5), (70, 7), (120, 10)),
        "type_plage_coef": ((20, "boue"), (50, "galets"), (100, "sable")),
        "frequentation_periode": ((1, "faible"), (5, "moyen"), (8, "bondé")),
        "description": (
            "La plage de Tourony se caractérise par la vue du château de Costaéres. "
            "Elle est très calme et accueille un public plutôt familial."
        ),
    }

def greve_blanche():
    return {
        "nom": "Grève blanche",
        "mer": MER_MANCHE,
        "longitude": -3.520,
        "latitude": 48.830,
        "orientation_mer": (320, 20),
        "hauteurs_eau_coef": ((20, 1), (50, 6), (70, 8), (120, 11)),
        "type_plage_coef": ((20, "boue"), (50, "sable"), (100, "sable")),
        "frequentation_periode": ((1, "faible"), (4, "moyen"), (9, "bondé")),
        "description": "Grande plage de sable exposée aux vents d'ouest.",
    }



def toull_bihan():
    return {
        "nom": "Toull Bihan",
        "mer": MER_MANCHE,
        "longitude": -3.524,
        "latitude": 48.824,
        "orientation_mer": (320, 20),
        "hauteurs_eau_coef": ((20, 1), (50, 6), (70, 8), (120, 11)),
        "type_plage_coef": ((20, "boue"), (50, "sable"), (100, "sable")),
        "frequentation_periode": ((1, "faible"), (4, "moyen"), (9, "bondé")),
        "description": "Grande plage de sable exposée aux vents d'ouest.",
    }




def saint_michel_en_grève():
    return {
        "nom": "Saint-Michel-en-Grève",
        "mer": MER_MANCHE,
        "longitude": -3.568,
        "latitude": 48.681,
        "orientation_mer": (300, 40),
        "hauteurs_eau_coef": ((20, 1), (50, 6), (70, 8), (120, 11)),
        "type_plage_coef": ((20, "sable"), (50, "sable"), (100, "sable")),
        "frequentation_periode": ((1, "faible"), (4, "moyen"), (9, "bondé")),
        "description": "Grande plage de sable exposée aux vents du nord.",
    }


# def _plage_st_evette():
#     return {
#         "nom": "Sainte-Évette",
#         "mer": MER_MANCHE,
#         "longitude": -4.738,
#         "latitude": 48.403,
#         "orientation_mer": (240, 290),
#         "hauteurs_eau_coef": ((20, 0), (50, 4), (70, 6), (120, 9)),
#         "type_plage_coef": ((20, "galets"), (50, "galets"), (100, "sable")),
#         "frequentation_periode": ((1, "faible"), (5, "moyen"), (8, "bondé")),
#         "description": "Petite anse abritée du vent de nord-est.",
#     }
# 
# 
# def _plage_caroual():
#     return {
#         "nom": "Caroual",
#         "mer": MER_MANCHE,
#         "longitude": -2.371,
#         "latitude": 48.643,
#         "orientation_mer": (300, 20),
#         "hauteurs_eau_coef": ((20, 0), (50, 4), (70, 6), (120, 9)),
#         "type_plage_coef": ((20, "sable"), (50, "sable"), (100, "sable")),
#         "frequentation_periode": ((1, "faible"), (5, "moyen"), (7, "bondé")),
#         "description": "Plage de sable au fond d'une baie très abritée.",
#     }


def base_plages():
    return [
        tourony(),
        greve_blanche(),
        toull_bihan(),
#         saint_michel_en_grève(),
#         _plage_st_evette(),
#         _plage_caroual(),
    ]
