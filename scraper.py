import requests
from bs4 import BeautifulSoup

def get_html_content(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.content
    else:
        return None  

def parse_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    data = []

    for p_tag in soup.find_all('p'):
        data.append(p_tag.get_text())

    return data

def scrape_website(url):
    html_content = get_html_content(url)
    if html_content:
        data = parse_html(html_content)
        return data
    else:
        print("Failed to retrieve the content")
        return None

if __name__ == "__main__":
    url = 'https://example.com'
    scraped_data = scrape_website(url)
    if scraped_data:
        for item in scraped_data:
            print(item)