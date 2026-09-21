"""Tests du projet BonBain."""

import json
import unittest
from datetime import date, datetime, timezone

import bonbain.analyse as analyse
import bonbain.base_plages as base_plages
import bonbain.collecte as collecte
import bonbain.opsys as opsys
import bonbain.serveur as serveur


class _Reponse:
    def __init__(self, contenu):
        self._contenu = contenu

    def read(self):
        return self._contenu

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def fabriquer_ouvrir(reponses):
    """Retourne une fausse fonction ouvrir(url, timeout) par URL contenant une clé."""
    def ouvrir(url, timeout=10):
        for cle, contenu in reponses.items():
            if cle in url:
                return _Reponse(contenu)
        raise OSError("URL inconnue : " + url)
    return ouvrir


class TestBasePlages(unittest.TestCase):
    def test_tourony(self):
        plage = base_plages.plage_tourony()
        self.assertEqual(plage["nom"], "Tourony")
        self.assertEqual(plage["mer"], "Manche")
        self.assertAlmostEqual(plage["latitude"], 48.829571)
        self.assertAlmostEqual(plage["longitude"], -3.498734)
        self.assertEqual(plage["orientation_mer"], (340, 30))
        self.assertEqual(plage["hauteurs_eau_coef"], ((20, 0), (50, 5), (70, 7), (120, 10)))
        self.assertIn("château", plage["description"])

    def test_base_non_vide(self):
        plages = base_plages.base_plages()
        self.assertGreaterEqual(len(plages), 1)
        for plage in plages:
            self.assertIn("nom", plage)
            self.assertIn("hauteurs_eau_coef", plage)


class TestOPSYS(unittest.TestCase):
    def test_hauteur_mer_positive(self):
        for heure in range(24):
            instant = datetime(2025, 7, 15, heure, tzinfo=timezone.utc)
            self.assertGreaterEqual(opsys.hauteur_mer(instant), 0.0)

    def test_deux_marees_par_jour(self):
        horaire = opsys.horaire_marees(date(2025, 7, 15))
        self.assertGreaterEqual(len(horaire), 2)
        types = [entree["type"] for entree in horaire]
        self.assertIn("PM", types)
        self.assertIn("BM", types)

    def test_coefficient_borne(self):
        for jour in (date(2025, 1, 1), date(2025, 7, 15), date(2025, 10, 5)):
            coefficient = opsys.coefficient_maree(jour)
            self.assertGreaterEqual(coefficient, 20)
            self.assertLessEqual(coefficient, 120)

    def test_hauteur_eau_plage_interpolation(self):
        plage = base_plages.plage_tourony()
        self.assertEqual(opsys.hauteur_eau_plage(plage, 20)[0], 0)
        self.assertEqual(opsys.hauteur_eau_plage(plage, 50)[0], 5)
        self.assertEqual(opsys.hauteur_eau_plage(plage, 70)[0], 7)
        self.assertEqual(opsys.hauteur_eau_plage(plage, 120)[0], 10)
        self.assertAlmostEqual(opsys.hauteur_eau_plage(plage, 60)[0], 6.0)

    def test_type_plage_selon_coef(self):
        plage = base_plages.plage_tourony()
        self.assertEqual(opsys.type_plage(plage, 20), "boue")
        self.assertEqual(opsys.type_plage(plage, 50), "galets")
        self.assertEqual(opsys.type_plage(plage, 100), "sable")
        self.assertEqual(opsys.type_plage(plage, 120), "sable")


class TestCollecte(unittest.TestCase):
    def test_normaliser_openweathermap(self):
        echantillon = {
            "cod": 200,
            "wind": {"speed": 8.95, "deg": 310, "gust": 15.66},
            "main": {"temp": 18.4, "feels_like": 17.9, "pressure": 1015, "humidity": 87},
            "clouds": {"all": 47},
            "sys": {"sunrise": 1789963746, "sunset": 1790008065},
        }
        conditions = collecte.normaliser_openweathermap(echantillon)
        self.assertAlmostEqual(conditions["vent_vitesse_ms"], 8.95)
        self.assertAlmostEqual(conditions["vent_direction_deg"], 310.0)
        self.assertAlmostEqual(conditions["nebulosite_pct"], 47.0)
        self.assertAlmostEqual(conditions["ensoleillement_pct"], 53.0)
        self.assertEqual(conditions["source"], "openweathermap")

    def test_collecte_openweathermap_sans_cle(self):
        plage = base_plages.plage_tourony()
        self.assertIsNone(collecte.collecter_openweathermap(plage))

    def test_collecte_openweathermap_ok(self):
        plage = base_plages.plage_tourony()
        reponse = json.dumps({
            "cod": 200,
            "wind": {"speed": 5.0, "deg": 200.0},
            "main": {"temp": 20.0},
            "clouds": {"all": 20},
            "sys": {"sunrise": 1, "sunset": 2},
        }).encode("utf-8")
        ouvrir = fabriquer_ouvrir({"data/2.5/weather": reponse})
        conditions = collecte.collecter_openweathermap(
            plage, apikey="test", ouvrir=ouvrir
        )
        self.assertAlmostEqual(conditions["vent_vitesse_ms"], 5.0)

    def test_collecte_openweathermap_erreur_reseau(self):
        plage = base_plages.plage_tourony()

        def ouvrir(url, timeout=10):
            raise OSError("pas de réseau")

        self.assertIsNone(
            collecte.collecter_openweathermap(plage, apikey="test", ouvrir=ouvrir)
        )

    def test_collecte_copernicus_ok(self):
        plage = base_plages.plage_tourony()
        reponse = json.dumps({
            "current": {"time": "2026-09-21T09:00", "interval": 900,
                        "sea_surface_temperature": 16.4}
        }).encode("utf-8")
        ouvrir = fabriquer_ouvrir({"marine": reponse})
        conditions = collecte.collecter_copernicus(plage, ouvrir=ouvrir)
        self.assertAlmostEqual(conditions["temperature_mer_c"], 16.4)
        self.assertEqual(conditions["source"], "copernicus")


class TestAnalyse(unittest.TestCase):
    def test_note_hauteur_eau(self):
        self.assertEqual(analyse.note_hauteur_eau(0.0), 0.0)
        self.assertEqual(analyse.note_hauteur_eau(5.0), 100.0)
        self.assertLess(analyse.note_hauteur_eau(1.5), analyse.note_hauteur_eau(5.0))

    def test_note_vent_force(self):
        self.assertEqual(analyse.note_vent_force(2.0), 100.0)
        self.assertEqual(analyse.note_vent_force(15.0), 0.0)
        self.assertGreater(analyse.note_vent_force(4.0), analyse.note_vent_force(9.0))

    def test_note_vent_orientation(self):
        # Tourony : plage orientée nord (340-30), un vent de 0° vient de la mer.
        self.assertLess(analyse.note_vent_orientation(0.0, (340, 30)), 50.0)
        # Un vent de sud (180°) vient de la terre : idéal.
        self.assertGreater(analyse.note_vent_orientation(180.0, (340, 30)), 80.0)
        # Un cas où l'orientation ne boucle pas autour du nord.
        self.assertLess(analyse.note_vent_orientation(265.0, (240, 290)), 50.0)
        self.assertGreater(analyse.note_vent_orientation(65.0, (240, 290)), 50.0)

    def test_note_temperature(self):
        self.assertEqual(analyse.note_temperature(28.0), 100.0)
        self.assertEqual(analyse.note_temperature(10.0), 0.0)
        self.assertGreater(analyse.note_temperature(22.0, 20.0), analyse.note_temperature(22.0, 16.0))

    def test_couleur_score(self):
        self.assertEqual(analyse.couleur_score(80.0), "vert")
        self.assertEqual(analyse.couleur_score(60.0), "orange")
        self.assertEqual(analyse.couleur_score(30.0), "rouge")

    def test_couleur_vent(self):
        self.assertEqual(analyse.couleur_vent(3.0), "bleu")
        self.assertEqual(analyse.couleur_vent(9.0), "violet")

    def test_note_globale_ponderee(self):
        notes = {critere: 100.0 for critere in analyse.POIDS_CRITERES}
        self.assertEqual(analyse.note_globale(notes), 100.0)
        notes = {critere: 0.0 for critere in analyse.POIDS_CRITERES}
        self.assertEqual(analyse.note_globale(notes), 0.0)

    def test_frequentation(self):
        plage = base_plages.plage_tourony()
        self.assertEqual(analyse.niveau_frequentation(plage, 1), "faible")
        self.assertEqual(analyse.niveau_frequentation(plage, 5), "moyen")
        self.assertEqual(analyse.niveau_frequentation(plage, 8), "bondé")

    def test_evaluer_plage_complete(self):
        plage = base_plages.plage_tourony()
        conditions = {
            "vent_vitesse_ms": 2.5,
            "vent_direction_deg": 180.0,
            "temperature_air_c": 22.0,
            "temperature_mer_c": 18.0,
            "ensoleillement_pct": 90.0,
        }
        rapport = analyse.evaluer_plage(plage, conditions, coefficient=100, periode=2)
        self.assertEqual(rapport["nom"], "Tourony")
        self.assertEqual(rapport["couleur_led"], "vert")
        self.assertEqual(rapport["led_vent"], "bleu")
        self.assertEqual(rapport["type_plage"], "sable")
        self.assertGreater(rapport["score"], 75.0)

    def test_classer_plages(self):
        rapports = [
            {"nom": "a", "score": 40.0},
            {"nom": "b", "score": 90.0},
            {"nom": "c", "score": 65.0},
        ]
        classement = analyse.classer_plages(rapports)
        self.assertEqual([r["nom"] for r in classement], ["b", "c", "a"])


class TestServeur(unittest.TestCase):
    def test_etat_compact(self):
        classement = [
            {"nom": "Tourony", "score": 80.0, "couleur_led": "vert",
             "led_vent": "bleu", "direction_vent_deg": 180.0,
             "vitesse_vent_ms": 2.0},
        ]
        etat = serveur.etat_compact(classement, 70)
        self.assertEqual(etat["meilleure_plage"], "Tourony")
        self.assertEqual(etat["led_score"], "vert")
        self.assertEqual(etat["led_vent"], "bleu")
        self.assertEqual(etat["aiguille_vent_deg"], 180.0)
        self.assertEqual(etat["coefficient_maree"], 70)

    def test_collecte_degradee_simulation(self):
        plage = base_plages.plage_tourony()

        def ouvrir(url, timeout=10):
            raise OSError("pas de réseau")

        conditions = serveur.collecter_conditions(plage, ouvrir=ouvrir)
        self.assertEqual(conditions["source"], "simulation")

    def test_pipeline_complet_serveur(self):
        classement, coefficient = serveur.evaluer_toutes_plages(
            jour=date(2025, 7, 15), periode=5
        )
        self.assertGreaterEqual(len(classement), 1)
        self.assertGreaterEqual(coefficient, 20)
        scores = [r["score"] for r in classement]
        self.assertEqual(scores, sorted(scores, reverse=True))
        for rapport in classement:
            self.assertIn(rapport["couleur_led"], ("vert", "orange", "rouge"))
            self.assertIn(rapport["led_vent"], ("bleu", "violet"))
            self.assertGreaterEqual(rapport["direction_vent_deg"], 0.0)
            self.assertLessEqual(rapport["direction_vent_deg"], 360.0)


if __name__ == "__main__":
    unittest.main()
