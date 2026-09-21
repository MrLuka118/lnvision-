from django.test import Client

client = Client()
urls = [
    "/nastavitve/",
    "/nastavitve/studio/",
    "/nastavitve/paketi/",
    "/nastavitve/paketi/nov/",
    "/nastavitve/lokacije/",
    "/nastavitve/lokacije/nova/",
]

for url in urls:
    response = client.get(url)
    print(f"{url}: {response.status_code}")
