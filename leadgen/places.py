import time

import requests

PLACES_TEXTSEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"


def search_places(query, api_key, max_results=20):
    results = []
    params = {"query": query, "key": api_key}
    while len(results) < max_results:
        resp = requests.get(PLACES_TEXTSEARCH_URL, params=params).json()
        results.extend(resp.get("results", []))
        token = resp.get("next_page_token")
        if not token:
            break
        time.sleep(2)
        params = {"pagetoken": token, "key": api_key}
    return results[:max_results]


def get_place_details(place_id, api_key):
    params = {
        "place_id": place_id,
        "fields": "name,formatted_phone_number,international_phone_number,website,formatted_address",
        "key": api_key,
    }
    resp = requests.get(PLACES_DETAILS_URL, params=params).json()
    return resp.get("result", {})
