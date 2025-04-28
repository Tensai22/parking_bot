import requests
import config

def get_free_parking():
    response = requests.get(f"{config.PARKING_API}/free")
    return response.json() if response.status_code == 200 else []
