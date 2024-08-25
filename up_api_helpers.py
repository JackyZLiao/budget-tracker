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

def make_dataframe(transactions):
    cur = transactions
    data = {
        'description' : [],
        'amount' : [],
        'date' : [],
        'category' : [] 
    }

    while True:
        next_url = cur["links"]["next"]
        for t in cur["data"]:
            if not extract_data(t): continue
            description, amount, category, date = extract_data(t)
            data['description'].append(description)
            data['amount'].append(amount)
            data['category'].append(category)
            data['date'].append(date)
        if not next_url: break
        cur = get_transactions(next_url)

    df = pd.DataFrame(data)
    return df

def extract_data(transaction):
    description = transaction["attributes"]["description"]
    amount = float(transaction["attributes"]["amount"]["value"])
    category = recategorise(transaction["relationships"]["category"]["data"]["id"]) if transaction["relationships"]["category"]["data"] else None
    date = transaction["attributes"]["createdAt"]

    if amount >= 0 : return None # Ignore positive amounts i.e. money coming in 
    if transaction["attributes"]["transactionType"] in ("Transfer", "Scheduled Transfer") : return None # Ignore transfers across accounts
    return description, -amount, category, date

def recategorise(original_category):
    category_mapping = {
        "clothing-and-accesories" : "Clothing and Accessories",
        "events-and-gigs" : "Entertainment and Recreation",
        "hobbies" : "Entertainment and Recreation",
        "holidays-and-travel" : "Entertainment and Recreation",
        "restaurants-and-cafes" : "Food",
        "pubs-and-bars" : "Food",
        "takeaway" : "Food",
        "hair-and-beauty" : "Health and Beauty",
        "health-and-medical" : "Health and Beauty",
        "fitness-and-wellbeing" : "Subscriptions and Memberships",
        "tv-and-music" : "Subscriptions and Memberships",
        "technology" : "Subscriptions and Memberships",
        "internet" : "Subscriptions and Memberships",
        "games-and-software": "Subscriptions and Memberships",
        "groceries" : "Groceries",
        "fuel" : "Transportation",
        "public-transport" : "Transportation",
        "cycling" : "Transportation",
        "homeware-and-appliances" : "Shopping",
        "home-maintenance-and-improvements" : "Shopping",
        "car-insurance-and-maintenance" : "Life Admin",
    }
    if original_category not in category_mapping:
        return "Other"
    else:
        return category_mapping[original_category]

# For debugging purposes
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
    df = make_dataframe(transactions)
    print(df)
