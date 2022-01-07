import requests
import json
from utils import spotify

def check_label(albumid: str):
    req = f"https://api.spotify.com/v1/albums/{albumid}"
    response = requests.get(req, headers=spotify.auth()).text
    albumdata = json.loads(response)
    if "Firect Music" in albumdata["copyrights"][0]["text"]:
        return False