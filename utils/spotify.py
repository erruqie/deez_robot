import requests
import json
import os

def auth():
    auth_url = 'https://accounts.spotify.com/api/token'
    auth_response = requests.post(auth_url, {
        'grant_type': 'client_credentials',
        'client_id': os.environ.get('spotify_client_id'),
        'client_secret': os.environ.get('spotify_client_secret'),
    })
    auth_response_data = auth_response.json()
    access_token = auth_response_data['access_token']
    headers = {'Authorization': 'Bearer {token}'.format(token=access_token)}
    return headers