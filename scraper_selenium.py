from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

def setup_selenium_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    service = Service("C:\Users\user\Desktop\Python\chromedriver.exe")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def get_html_content_selenium(url, driver):
    driver.get(url)
    return driver.page_source

def parse_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    data = []
    # divs = soup.find_all(divs,class_=" specific-class ")
    # for div in divs:
    #     product = div.find('h').text.strip
    #     data.append(div.text.strip())
    #     return data
    for elements in soup.find_all(True):
        data.append(elements.get_text())

    return data

def scrape_website(url):
    driver = setup_selenium_driver()
    html_content = get_html_content_selenium(url, driver)
    driver.quit()
    data = parse_html(html_content)
    return data

if __name__ == "__main__":
    url = 'https://example.com'
    scraped_data = scrape_website(url)
    if scraped_data:
        for item in scraped_data:
            print(item)