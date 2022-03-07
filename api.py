import requests
from ratelimit import limits, sleep_and_retry
import json

apikey = 'XXXXXXXXX'

LIMIT = 5

@sleep_and_retry
@limits(calls=5, period=1)
def api_request(params):
    payload={}
    headers = {}

    url = "https://api.etherscan.io/api?"

    try:
        response = requests.request("GET", url, params=params, headers=headers, data=payload)
        return response.json()

    except json.decoder.JSONDecodeError:
        print('[ERROR] API Error')
        print(response.json())
        return { "status": "0"}


def get_transactions_by_account(address, internal=False, startblock='1', endblock='99999999', page='1'):
    if internal == True:
        action = 'txlistinternal'
    else:
        action = 'txlist'

    params={
        'module':       'account',
        'action':       action,
        'address':      address,
        'apikey':       apikey,
        'startblock':   startblock,
        'endblock':     endblock,
        'page':         page
    }

    result = api_request(params)
    if result['status'] != "1":
        return []
    return result['result']


