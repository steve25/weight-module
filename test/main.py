# Aplication only for testing weight module


import urllib.parse
import threading
import time
import requests
import asyncio
import platform

API_URL = "http://192.168.1.165/api"

last_weight = None
session = requests.Session()

def send_to_api(weight):
    if not session.cookies.get('XSRF-TOKEN'):
        r = session.get(f"{API_URL}/csrf-token")
        print(f"GET /csrf-token status: {r.status_code}")
        print("Cookies po GET:", session.cookies.get_dict())

    csrf_token = session.cookies.get('XSRF-TOKEN')
    laravel_session = session.cookies.get('harvestsystem_session')

    if not csrf_token or not laravel_session:
        print("Chýba CSRF token alebo session cookie.")
        return

    csrf_token = urllib.parse.unquote(csrf_token)

    
    payload = {
        "weight_kg": weight,
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-XSRF-TOKEN": csrf_token,
        "Cookie": f"XSRF-TOKEN={csrf_token}; harvestsystem_session={laravel_session}",
    }

    r = session.post(f"{API_URL}/weight", headers=headers, json=payload)
    print(f"POST status: {r.status_code}")
    print("Response:", r.text)

def get_user_input():
    try:
        weight = input("Zadaj váhu v kg (alebo 'q' pre ukončenie): ")
        if weight.lower() == 'q':
            return None
        return float(weight)
    except ValueError:
        print("Neplatný vstup, skús znova.")
        return None

def check_weight_change():
    global last_weight
    while True:
        current_weight = get_user_input()
        if current_weight is None:
            print("Ukončujem...")
            break
        if current_weight != last_weight:
            print(f"Zmena váhy zistená: {current_weight} kg")
            send_to_api(current_weight)
            last_weight = current_weight
        time.sleep(1)

async def main():
    thread = threading.Thread(target=check_weight_change)
    thread.daemon = True
    thread.start()

    while thread.is_alive():
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
