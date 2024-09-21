import requests

def format_amount(amount: float) -> str:
    amount = float(amount)
    if amount.is_integer():
        return f'{amount:,.0f}'
    return f'{amount:,.2f}'

def get_ens_address(ens_name: str) -> str | None:
    return requests.get(f'https://api.ensdata.net/{ens_name}').json().get('address')

def get_ens_name(address: str) -> str | None:
    return requests.get(f'https://api.ensdata.net/{address}').json().get('ens')