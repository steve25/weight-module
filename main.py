import argparse
import time
import requests
import sys
import serial
import logging
import configparser

# --- Konštanty ---
config = configparser.ConfigParser()
config.read("config.ini")

API_URL = config.get("api", "url", fallback="http://192.168.1.165/api")
API_EMAIL = config.get("api", "email", fallback="weight.device@example.com")
API_PASSWORD = config.get("api", "password", fallback="password")
SERIAL_PORT = config.get("serial", "port", fallback="/dev/ttyUSB0")
BAUD_RATE = config.get("serial", "baud_rate", fallback=9600)
READ_TIMEOUT = config.get("serial", "read_timeout", fallback=1)


# --- Konfigurácia logovania ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

# --- HTTP Session ---
session = requests.Session()

def log_to_api():
    logger.info(f"Prihlasovanie sa na api.")
    payload = {
        "email": API_EMAIL,
        "password": API_PASSWORD
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    while True:
        try:
            response = session.post(f"{API_URL}/auth/login", headers=headers, json=payload, timeout=5)
            logger.info(f"API odpoveď: {response.status_code}")

            if response.status_code == 200:
                token = response.json().get("token")
                if token:
                    return token
                else:
                    logger.warning("Token nebol nájdený v odpovedi.")
            else:
                logger.warning(f"Neúspešné prihlásenie: {response.status_code}")
        except requests.RequestException as e:
            logger.error(f"Chyba pri prihlásení na API: {e}")

        time.sleep(3)  # krátka pauza medzi pokusmi

API_TOKEN = log_to_api()

def send_to_api(weight: float):
    """Odošle váhu na API."""
    payload = {"weight_kg": weight}
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": "Bearer " + API_TOKEN
    }

    try:
        response = session.put(f"{API_URL}/weight", headers=headers, json=payload, timeout=5)
        logger.info(f"API odpoveď: {response.status_code} {response.text.strip()}")
    except requests.RequestException as e:
        logger.error(f"Chyba pri odosielaní na API: {e}")


def get_user_input() -> float | None:
    """Získanie váhy od používateľa."""
    try:
        value = input("Zadaj váhu v kg (alebo 'Ctrl + C' pre ukončenie): ").strip()
        if value.lower() == "q":
            return None
        return float(value)
    except ValueError as e:
        logger.warning("Neplatný vstup od používateľa.")
        return None


def get_device_input() -> float | None:
    """Získanie váhy zo sériového portu."""
    try:
        line = read_serial_line()
        return float(line)
    except (serial.SerialException, ValueError) as e:
        logger.error(f"Chyba zo sériového portu: {e}")
        return None


def read_serial_line() -> str:
    """Čítanie jednej hodnoty zo sériového portu."""
    with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=READ_TIMEOUT) as ser:
        logger.info("Čakám na dáta z váhy...")
        line = ser.readline().decode("utf-8").strip()
        logger.info(f"Prijaté raw dáta: {line}")
        return line


def read_weight(test_mode: bool) -> float | None:
    """Hlavný bod na čítanie váhy (buď manuálne alebo z váhy)."""
    return get_user_input() if test_mode else get_device_input()


def has_weight_changed(new: float, old: float, threshold: float = 20.0) -> bool:
    """Zistí, či sa váha zmenila výrazne."""
    try:
        return abs(float(new) - float(old)) > threshold
    except Exception as e:
        logger.warning(f"Porovnanie zlyhalo: {e}")
        return new != old

def main():
    parser = argparse.ArgumentParser(description="Skript na čítanie váhy")
    parser.add_argument('--test', action='store_true', help='Testovací režim - manuálny vstup')
    args = parser.parse_args()

    last_weight = None

    try:
        while True:
            weight = read_weight(args.test)

            if weight is None:
                logger.warning("Nevalidné dáta... čakám 5s.")
                time.sleep(5)
                continue

            if last_weight is None or has_weight_changed(weight, last_weight):
                logger.info(f"Zmena váhy zistená: {weight} kg")
                send_to_api(weight)
                last_weight = weight

            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Prerušené používateľom (Ctrl+C). Ukončujem...")
    except Exception as e:
        logger.critical(f"Neočakávaná chyba v hlavnej slučke: {e}", exc_info=True)
    finally:
        sys.exit(0)


if __name__ == "__main__":
    main()
