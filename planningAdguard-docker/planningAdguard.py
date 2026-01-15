# Plannification de desactivation de filtre Adguard
# Ex : autoriser l'IA durant les heures de TP de projets
# S. Delbosc
# 15/01/2026


import yaml
import requests
import datetime
import time
import os

DAYS_MAP = {
    "mon": 0, "tue": 1, "wed": 2,
    "thu": 3, "fri": 4, "sat": 5, "sun": 6
}

def load_config_with_mtime(path):
    with open(path, "r") as f:
        return yaml.safe_load(f), os.path.getmtime(path)


def load_config():
    with open("confPlanning.yml", "r") as f:
        return yaml.safe_load(f)

def login(session, cfg):
    session.post(
        f"{cfg['url']}/control/login",
        json={
            "name": cfg["username"],
            "password": cfg["password"]
        }
    )

    if "agh_session" not in session.cookies:
        raise Exception("❌ Échec de l'authentification AdGuard")

def set_filter_state(cfg, enabled):
    session = requests.Session()
    login(session, cfg)

    response = session.post(
        f"{cfg['url']}/control/filtering/set_url",
        json={
            "url": cfg["filter_url"],
            "data": {
                "name": cfg["filter_name"],
                "url": cfg["filter_url"],
                "enabled": enabled
            },
            "whitelist": False
        }
    )

    if response.status_code != 200:
        raise Exception(f"Erreur API AdGuard: {response.text}")

    print(
        f"[{datetime.datetime.now()}] "
        f"Filtre {'ACTIVÉ' if enabled else 'DÉSACTIVÉ'}"
    )

def is_now_in_range(start, end, now):
    start = datetime.datetime.strptime(start, "%H:%M").time()
    end = datetime.datetime.strptime(end, "%H:%M").time()
    return start <= now < end

def should_be_disabled(now, weekday, schedule):
    for rule in schedule:
        if weekday in [DAYS_MAP[d] for d in rule["days"]]:
            if is_now_in_range(rule["start"], rule["end"], now):
                return True
    return False

def main():
    CONFIG_FILE = "confPlanning.yml"

    config, last_mtime = load_config_with_mtime(CONFIG_FILE)

    #config = load_config()
    adg = config["adguard"]
    schedule = config["schedule"]

    filter_currently_enabled = True  # état local supposé au démarrage

    while True:

        current_mtime = os.path.getmtime(CONFIG_FILE)

        if current_mtime != last_mtime:
           print("\n🔄 Rechargement du planning détecté", flush=True)
           config, last_mtime = load_config_with_mtime(CONFIG_FILE)
           adg = config["adguard"]
           schedule = config["schedule"]


        now = datetime.datetime.now()
        weekday = now.weekday()
        current_time = now.time()

        disabled_now = should_be_disabled(current_time, weekday, schedule)

        # Début plage → désactivation
        if disabled_now and filter_currently_enabled:
            set_filter_state(adg, enabled=False)
            filter_currently_enabled = False

        # Fin plage → réactivation
        if not disabled_now and not filter_currently_enabled:
            set_filter_state(adg, enabled=True)
            filter_currently_enabled = True

        print("*", end="", flush=True)
        time.sleep(60)

if __name__ == "__main__":
    main()