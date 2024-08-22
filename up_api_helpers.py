import pandas as pd 
import requests
import pprint as pp

UP_API_URL = "https://api.up.com.au/api/v1"
API_TOKEN = "up:yeah:j4R4B0ywNquo7tNofN11yDButVS1h3VfBb8DpCAk1PBKrQuOAjceOCLhe9MPf8mCsUJQlAeYDepg2hnXJM7ij6dq7utyxzFHDzMuEIWxId9mnACpTbxrmuTIgvXPFN8w"

def get_transactions(url, since=None):
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    params = {}
    if since:
        params["filter[since]"] = since;

    params["page[size]"] = 100;
    response = requests.get(url + "/transactions", headers=headers, params=params);

    if response.status_code == 200:
        return response.json()
    else:
        print(response.status_code)
        return [];

def print_transactions(transactions):
    for transaction in transactions["data"]:
        print(transaction["attributes"]["description"])
        print(transaction["attributes"]["amount"]["value"])
        print(transaction["attributes"]["createdAt"])
        if (transaction["relationships"]["category"]["data"]):
            print(transaction["relationships"]["category"]["data"]["id"])
        print();
        


if __name__ == "__main__":
    transactions = get_transactions(UP_API_URL)

    while True:
        next_url = transactions["links"]["next"]
        if not next_url: break
        transactions = get_transactions(next_url)
        print_transactions(transactions)
    