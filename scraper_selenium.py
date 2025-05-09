from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time


def setup_selenium_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    service = Service("C:\\Users\\user\\Desktop\\Python\\chromedriver.exe")  # Adjust path as needed
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def get_html_content_selenium(url, driver):
    driver.get(url)
    time.sleep(2)  # wait for content to load
    return driver.page_source


def parse_html(html_content, base_url):
    from urllib.parse import urljoin
    soup = BeautifulSoup(html_content, 'html.parser')

    # Clean soup by removing all non-content tags
    for tag in soup(["script", "style", "svg", "noscript", "meta", "link", "footer", "header"]):
        tag.decompose()

    data = []
    job_cards = []

    # Common job classes — update as needed for better targeting
    common_classes = ["job", "job-card", "job-listing", "listing", "job-result", "result", "serp-item", "cm-posts", "post"]

    for cls in common_classes:
        job_cards += soup.find_all("div", class_=lambda x: x and cls in x)

    seen = set()

    for card in job_cards:
        title = card.find(["h1", "h2", "h3"])
        company = card.find(["span", "div"], class_=lambda x: x and "company" in x.lower()) or ""
        location = card.find(["span", "div"], class_=lambda x: x and "location" in x.lower()) or ""
        desc = card.find("p") or card.find("div", class_=lambda x: x and "description" in x.lower())
        link = card.find("a", href=True)

        job_data = {
            "title": title.get_text(strip=True) if title else "",
            "company": company.get_text(strip=True) if company else "",
            "location": location.get_text(strip=True) if location else "",
            "description": desc.get_text(strip=True) if desc else "",
            "apply_link": urljoin(base_url, link["href"]) if link and "apply" in link.get_text(strip=True).lower() else ""
        }

        # Prevent duplicates
        job_id = (job_data["title"], job_data["apply_link"])
        if job_data["title"] and job_id not in seen:
            seen.add(job_id)
            data.append(job_data)

    return data



def scrape_paginated_jobs(base_url, max_pages=5):
    driver = setup_selenium_driver()
    all_data = []

    for page_num in range(1, max_pages + 1):
        if "?page=" in base_url:
            url = base_url.split("?page=")[0] + f"?page={page_num}"
        else:
            url = f"{base_url}?page={page_num}"

        print(f"Scraping: {url}")
        html_content = get_html_content_selenium(url, driver)
        jobs = parse_html(html_content, base_url)

        if not jobs:
            print("No more jobs found, stopping.")
            break

        all_data.extend(jobs)

    driver.quit()
    return all_data


if __name__ == "__main__":
    url = 'https://example.com/jobs'  # Change to your target site
    jobs = scrape_paginated_jobs(url, max_pages=3)
    for job in jobs:
        print(job)
