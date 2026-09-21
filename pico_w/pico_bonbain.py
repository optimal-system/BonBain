"""Client Raspberry Pico W pour BonBain (MicroPython).

À installer sur le Pico W avec MicroPython. Le Pico W se connecte au Wi-Fi,
interroge le serveur BonBain sur le réseau local et pilote les indicateurs :
- LED score global (NeoPixel ou GPIO + LED bicolore) : vert/orange/rouge ;
- LED vent : bleu = calme, violet = fort ;
- aiguille direction du vent : servo SG90 sur 0-360°.

Configuration : renseigner WIFI_SSID, WIFI_MDP et SERVEUR_BONBAIN
(l'adresse IP/le nom du serveur sur le réseau local).
"""

import network
import urequests
from machine import Pin, PWM
import time

WIFI_SSID = "MON_WIFI"
WIFI_MDP = "mot_de_passe_wifi"
SERVEUR_BONBAIN = "192.168.1.50:8266"
INTERROGATION_SECONDES = 300

PIN_LED_SCORE_R = 13
PIN_LED_SCORE_V = 14
PIN_LED_VENT_B = 15
PIN_LED_VENT_V = 16
PIN_SERVO_AIGUILLE = 17

COULEURS_LED = {"vert": (0, 1, 0), "orange": (1, 1, 0), "rouge": (1, 0, 0)}
LED_VENT = {"bleu": (1, 0), "violet": (1, 1)}


def connecter_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connexion au Wi-Fi", WIFI_SSID)
        wlan.connect(WIFI_SSID, WIFI_MDP)
        while not wlan.isconnected():
            time.sleep(0.5)
    print("Wi-Fi OK :", wlan.ifconfig()[0])
    return wlan


def etat_bonbain():
    reponse = urequests.get(
        "http://%s/bonbain" % SERVEUR_BONBAIN, timeout=15
    )
    donnees = reponse.json()
    reponse.close()
    return donnees


def allumer_led_score(couleur):
    r, v = COULEURS_LED[couleur]
    Pin(PIN_LED_SCORE_R, Pin.OUT).value(r)
    Pin(PIN_LED_SCORE_V, Pin.OUT).value(v)


def allumer_led_vent(couleur):
    b, v = LED_VENT[couleur]
    Pin(PIN_LED_VENT_B, Pin.OUT).value(b)
    Pin(PIN_LED_VENT_V, Pin.OUT).value(v)


def bouger_aiguille(direction_deg):
    """Déplace l'aiguille du servo sur 0-360° (course 1.0-2.0 ms)."""
    servo = PWM(Pin(PIN_SERVO_AIGUILLE, Pin.OUT), freq=50)
    angle = max(0, min(360, direction_deg))
    impulsion_us = 500 + (angle / 360.0) * 2000
    servo.duty_ns(impulsion_us * 1000)
    time.sleep(0.5)
    servo.deinit()


def boucle():
    connecter_wifi()
    while True:
        try:
            etat = etat_bonbain()
            print("Meilleure plage :", etat["meilleure_plage"], etat["score"], "/100")
            allumer_led_score(etat["led_score"])
            allumer_led_vent(etat["led_vent"])
            bouger_aiguille(etat["aiguille_vent_deg"])
        except Exception as erreur:
            print("Erreur BonBain :", erreur)
        time.sleep(INTERROGATION_SECONDES)


if __name__ == "__main__":
    boucle()
