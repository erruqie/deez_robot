import config
import requests
import json

def auth():
    auth_url = 'https://accounts.spotify.com/api/token'
    auth_response = requests.post(auth_url, {
        'grant_type': 'client_credentials',
        'client_id': config.spotify_client_id,
        'client_secret': config.spotify_client_secret,
    })
    auth_response_data = auth_response.json()
    access_token = auth_response_data['access_token']
    headers = {'Authorization': 'Bearer {token}'.format(token=access_token)}
    return headers

def check_label(albumid: str):
    req = f"https://api.spotify.com/v1/albums/{albumid}"
    response = requests.get(req, headers=auth()).text
    albumdata = json.loads(response)
    label = albumdata["copyrights"][0]["text"]
    dmca = False
    if label in config.dmca_labels:
        return label, dmca
    else:
        return label, True