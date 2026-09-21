# BonBain

Objet décoratif pour les résidences en bord de mer : il indique la meilleure
plage où aller se baigner, grâce à une carte et des indicateurs (LEDs, aiguille).

## Architecture

```
+-------------------+   Wi-Fi / HTTP (réseau local)   +---------------------------+
| Raspberry Pico W  | <------------------------------ | Serveur BonBain (Python)  |
| - LED score       |    GET /bonbain (JSON compact)    |  - base des plages        |
| - LED vent        |    GET /bonbain/plages            |  - collecte météo (API)   |
| - aiguille vent   |    GET /bonbain/carte (PNG)       |  - algorithme OPSYS       |
+-------------------+                                  |  - analyse / classement   |
                                                       |  - affichage carte        |
                                                       +---------------------------+
```

- **Base de données des plages** (`bonbain/base_plages.py`) : nom, mer,
  longitude/latitude, orientation par rapport à la mer (en degrés), hauteurs
  d'eau selon coefficient de marée, type de plage selon coefficient,
  fréquentation selon période, description. Exemple de Tourony (Manche,
  48.829571, -3.498734, orientation (340, 30)).
- **Collecte** (`bonbain/collecte.py`) :
  - API **OpenWeatherMap** (météo : vent, température, nuages, lever/coucher
    du soleil) — nécessite une clé API ;
  - API **Copernicus Marine** (température de surface de la mer) ;
  - en mode dégradé (pas de clé / pas de réseau), conditions simulées pour
    que l'objet reste fonctionnel.
- **Algorithme OPSYS** (`bonbain/opsys.py`) : horaire des marées, coefficient
  (20 à 120) et hauteur d'eau à partir d'un modèle harmonique simplifié calé
  sur le port de référence de Brest.
- **Analyse** (`bonbain/analyse.py`) : note de 0 à 100 par plage selon les
  critères (hauteur d'eau, force du vent, orientation du vent, type de plage,
  température, ensoleillement, fréquentation), puis classement des plages.
- **Affichage** (`bonbain/affichage.py`) : carte des plages avec :
  - LED score global : vert = bon, orange = correct, rouge = mauvais ;
  - LED vent : bleu = calme, violet = fort ;
  - aiguille de direction du vent de 0 à 360°.
- **Serveur** (`bonbain/serveur.py`) : serveur HTTP pour le Raspberry Pico W,
  à utiliser **sur le réseau local uniquement** (jamais exposé sur Internet).
- **Client Pico W** (`pico_w/pico_bonbain.py`) : client MicroPython qui
  interroge le serveur et pilote LEDs et servo.

## Installation

```bash
pip install matplotlib
```

Aucune autre dépendance (tout le reste utilise la bibliothèque standard).

## Utilisation

Analyse ponctuelle + génération de la carte (mode dégradé si pas de clé API) :

```bash
python -m bonbain
```

Démarrer le serveur pour le Pico W (réseau local) :

```bash
python -m bonbain --serveur --port 8266
```

Clé OpenWeatherMap (facultative, sinon mode dégradé simulé) :

```bash
export BONBAIN_OPENWEATHERMAP_KEY="votre_cle"
```

Sur le Pico W : copier `pico_w/pico_bonbain.py`, renseigner `WIFI_SSID`,
`WIFI_MDP` et `SERVEUR_BONBAIN` (adresse IP du serveur sur le réseau local).

## Tests

```bash
python -m pytest tests/ -v
```
