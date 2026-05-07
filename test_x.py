import requests

BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAAKbI9QEAAAAA2MIe1QG90EmB4IfOr6t5Ydlf7Nc%3DE2oSgFIjtLpEPafu3JdSOFyl1q8yKIoyhlzfYmrB0NPcgEWt5Z"

headers = {
    "Authorization": f"Bearer {BEARER_TOKEN}"
}

url = "https://api.x.com/2/tweets/search/recent?query=IA OR intelligence artificielle&tweet.fields=created_at,author_id,lang"

response = requests.get(url, headers=headers)

print(response.status_code)
if response.status_code == 200:
    print(response.json())
else:
    print(response.text)