import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pandas as pd
import json
import base64
import sys
from urllib.parse import urljoin

st.set_page_config(page_title=" Web Scraper", layout="wide")

st.markdown(
    """
    <style>
        body {
            background: linear-gradient(135deg, #1e3c72, #2a5298);
            color: #ffffff;
            font-family: 'Segoe UI', sans-serif;
        }
        .stApp {
            background: rgba(255, 255, 255, 0.05);
            padding: 30px;
            border-radius: 20px;
            box-shadow: 0 0 30px rgba(0, 0, 0, 0.4);
        }
        .main-title {
            font-size: 3.2em;
            font-weight: bold;
            text-align: center;
            color: #00ffff;
            margin-bottom: 20px;
            text-shadow: 2px 2px 8px #000000;
        }
        .stTextInput input, .stSelectbox div, .stSlider > div {
            background-color: #1a1a1a;
            color: #ffffff;
            border-radius: 8px;
            padding: 10px;
            border: 1px solid #444;
        }
        .stButton button {
            background-color: #00ffff;
            color: #000000;
            font-weight: bold;
            border-radius: 10px;
            padding: 10px 20px;
            transition: all 0.3s ease-in-out;
        }
        .stButton button:hover {
            background-color: #00cccc;
            transform: scale(1.05);
        }
    </style>
    """,
    unsafe_allow_html=True
)
def setup_selenium_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    service = Service(r'C:\Users\user\Desktop\Python\chromedriver.exe') 
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def get_html_content_selenium(url, driver):
    driver.get(url)
    return driver.page_source

def parse_html(html_content, prompt):
    from urllib.parse import urljoin
    soup = BeautifulSoup(html_content, 'html.parser')
    data = []
    prompt_lower = prompt.lower()
    if "job" in prompt_lower or "job listings" in prompt_lower:
        job_cards = []
        common_classes = ["job", "job-card", "listing", "job-listing", "job-result", "result", "serp-item"]

        for cls in common_classes:
            job_cards += soup.find_all("div", class_=lambda x: x and cls in x)

        for card in job_cards:
            title = card.find(["h1", "h2", "h3"])
            company = card.find(["span", "div"], class_=lambda x: x and "company" in x)
            location = card.find(["span", "div"], class_=lambda x: x and "location" in x)
            link = card.find("a", href=True)

            job_data = {
                "title": title.get_text(strip=True) if title else "",
                "company": company.get_text(strip=True) if company else "",
                "location": location.get_text(strip=True) if location else "",
                "link": urljoin("https://example.com", link["href"]) if link else ""
            }
    
    if "product names and prices" in prompt.lower():
        for product in soup.select('.product'):
            name = product.select_one('.product-name').text.strip()
            price = product.select_one('.product-price').text.strip()
            data.append({'name': name, 'price': price})
    elif "headlines" in prompt.lower():
        for headline in soup.select('h1, h2, h3'):
            data.append({'headline': headline.text.strip()})
    elif "links" in prompt.lower():
        for link in soup.find_all("a", href=True):
            text = link.get_text(strip=True) or "No Text"
            absolute_link = urljoin(url, link["href"])  
            data.append({"text": text, "link": absolute_link})

        return data
    elif "images" in prompt.lower():
            for img in soup.select('img'):
                src = img.get('src')
                alt = img.get('alt', '').strip()
                data.append({'src': src, 'alt': alt})
    else:
        for element in soup.find_all(text=True):
                data.append(element.strip())

        data = [item for item in data if item]

        return data
def scrape_website(url, prompt):
    driver = setup_selenium_driver()
    html_content = get_html_content_selenium(url, driver)
    driver.quit()
    data = parse_html(html_content, prompt)
    return data

def create_download_link(data, file_format):
    if file_format == 'JSON':
        json_data = json.dumps(data, indent=4)
        b64 = base64.b64encode(json_data.encode()).decode()
        href = f'<a href="data:file/json;base64,{b64}" download="scraped_data.json">Download JSON File</a>'
    elif file_format == 'CSV':
        if isinstance(data[0], dict):
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame(data, columns=['Text'])
        csv_data = df.to_csv(index=False)
        b64 = base64.b64encode(csv_data.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="scraped_data.csv">Download CSV File</a>'
    return href

# with st.sidebar:
#     st.header("🔧 Scraper Settings")
#     url = st.text_input("Enter job portal URL")
#     num_pages = st.slider("Number of pages to scrape", 1, 10, 3)
#     file_format = st.selectbox("Export Format", ["JSON", "CSV"])
#     start_button = st.button("Start Scraping")
st.markdown("<div class='main-title'>🕸️ AI Web Scraper</div>", unsafe_allow_html=True)

st.write("Enter the URL of the website you want to scrape:")

if __name__ == "__main__":

    st.title("AI Web Scraper")
    st.write("Enter the URL of the website you want to scrape:")

    url = st.text_input("URL")
    prompt = st.text_input("Prompt")
    file_format = st.selectbox("Select file format to save data:", ["JSON", "CSV"])
    max_pages = st.slider("Number of pages to scrape", 1, 10, 1)

    if st.button("Scrape", key="scrape_button", help="Click to start scraping"):
        with st.spinner("Scraping the website..."):
            try:
                st.write(f"Scraping URL: {url} with prompt: {prompt}")
                scraped_data = scrape_website(url, prompt)
                st.write(f"Scraped Data: {scraped_data}")
                if scraped_data:
                    st.success("Data scraped successfully!")
                    st.markdown("### Scraped Data Preview:")
                    st.dataframe(scraped_data if isinstance(scraped_data, pd.DataFrame) else pd.DataFrame(scraped_data))
                    for item in scraped_data:
                        st.write(item)
                    
                    download_link = create_download_link(scraped_data, file_format)
                    st.markdown(download_link, unsafe_allow_html=True)
                else:
                    st.error("Failed to retrieve the content")
            except Exception as e:
                st.error(f"An error occurred: {e}")


