import requests
# Your LINE Channel Access Token
access_token = 'fVCoNO0ngCzftfIarmDem5zXiGaGRQ5hDxO/LKatg3eVgo9VdZgVY9SnM9LLDkMxiyQId1o5h/k826cebvr/iUhF8gpJjV/fDL89/zYG23L0WS1S4xB6uSDvS5O7Owwoy7NCVyfiVXzz1pNHEGm7YAdB04t89/1O/w1cDnyilFU='

# The recipient user ID (This could be the user ID of the person you want to send the message to)
user_id='U0b30c29839edf867f6a6212abe6648f5'

#user_id = 'Uc4b86aa5f51662ea50f375b97c237df1'

# The URL for sending a message via the LINE Messaging API
url = 'https://api.line.me/v2/bot/message/push'

# The headers required for authentication
headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + access_token
}

# The payload with the message to send
payload = {
    'to': user_id,
    'messages': [
        {
            'type': 'text',
            'text': 'Hello, this is a message sent from the LINE Messaging API using Python!'
        }
    ]
}

# Send the POST request
response = requests.post(url, headers=headers, json=payload)

# Check if the request was successful
if response.status_code == 200:
    print('Message sent successfully!')
else:
    print('Failed to send message:', response.status_code, response.text)