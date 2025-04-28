import requests
import config

def create_payment(user_id, zone_id, amount):
    data = {
        "orderId": f"{user_id}_{zone_id}",
        "amount": amount,
        "currency": "KZT",
        "callbackUrl": "https://yourserver.com/payment/callback"
    }
    
    response = requests.post(config.PAYMENT_API, json=data)
    payment_url = response.json().get("paymentUrl")
    
    return payment_url
