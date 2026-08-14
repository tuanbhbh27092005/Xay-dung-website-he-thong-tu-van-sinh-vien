import requests
from bs4 import BeautifulSoup

url = 'https://hcmute.edu.vn/'
response = requests.get(url, verify=False)
response.encoding = 'utf-8'
soup = BeautifulSoup(response.text, 'html.parser')

with open('hcmute_links.txt', 'w', encoding='utf-8') as f:
    for a in soup.find_all('a', href=True):
        f.write(f"{a['href']} | {a.text.strip()}\n")
    
    # Also find some articles or news sections
    f.write("\n\n--- IMAGES ---\n")
    for img in soup.find_all('img', src=True):
        f.write(f"{img['src']} | {img.get('alt', '')}\n")
