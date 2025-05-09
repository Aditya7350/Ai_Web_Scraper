import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pandas as pd
import json
import base64
from urllib.parse import urljoin
import re
import time
from collections import Counter

st.set_page_config(page_title="Web Scraper", layout="wide")

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
    """Set up and return a Selenium WebDriver with Chrome."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36")
    service = Service(r'C:\Users\user\Desktop\Python\chromedriver.exe')
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def get_html_content(url, driver):
    """Get HTML content of a webpage using Selenium."""
    try:
        driver.get(url)
        # Wait for dynamic content to load
        time.sleep(3)
        return driver.page_source
    except Exception as e:
        st.error(f"Error accessing the URL: {e}")
        return None

def detect_content_type(soup):
    """Detect the primary content type of the page."""
    # Count different element types to determine the main content type
    type_counts = {
        "job_listing": len(soup.find_all("div", class_=lambda x: x and any(job_term in x.lower() for job_term in ["job", "career", "position", "listing", "vacancy"]))),
        "product": len(soup.find_all("div", class_=lambda x: x and any(prod_term in x.lower() for prod_term in ["product", "item", "goods", "merchandise"]))),
        "article": len(soup.find_all(["article", "div"], class_=lambda x: x and any(art_term in x.lower() for art_term in ["article", "post", "blog", "news"]))),
        "table_data": len(soup.find_all("table")),
        "image_gallery": len(soup.find_all("img")) > 10,
    }
    
    # Check for tables with multiple rows
    for table in soup.find_all("table"):
        if len(table.find_all("tr")) > 3:
            type_counts["table_data"] += 5  # Give more weight to data tables
    
    # Check for forms
    if len(soup.find_all("form")) > 0:
        type_counts["form"] = len(soup.find_all("form")) * 3
    
    # Count links to determine if it's a directory or navigation page
    link_count = len(soup.find_all("a", href=True))
    if link_count > 30:
        type_counts["directory"] = link_count
    
    # Return the type with the highest count
    if not type_counts:
        return "general"
    
    main_type = max(type_counts.items(), key=lambda x: x[1])
    return main_type[0] if main_type[1] > 0 else "general"

def extract_schema_data(soup):
    """Extract structured data from schema.org markup if available."""
    schema_data = []
    
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(script.string)
            if data:
                schema_data.append(data)
        except:
            pass
    
    return schema_data if schema_data else None

def clean_text(text):
    """Clean text by removing extra whitespace and special characters."""
    if not text:
        return ""
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing whitespace
    return text.strip()

def extract_job_listings(soup, base_url):
    """Extract job listings from the page."""
    jobs = []
    # Common job container classes
    job_containers = soup.find_all("div", class_=lambda x: x and any(job_term in x.lower() for job_term in ["job", "career", "position", "listing", "vacancy"]))
    
    # If no specific job containers found, look for generic listings
    if not job_containers:
        job_containers = soup.find_all(["div", "li"], class_=lambda x: x and any(list_term in x.lower() for list_term in ["item", "result", "card", "listing", "post"]))
    
    for container in job_containers:
        # Try to find the job title, company, location
        title_elem = container.find(["h1", "h2", "h3", "h4", "a"], class_=lambda x: x and any(title_term in x.lower() for title_term in ["title", "name", "position"]) if x else False) or container.find(["h1", "h2", "h3", "h4", "a"])
        company_elem = container.find(["span", "div", "p"], class_=lambda x: x and any(comp_term in x.lower() for comp_term in ["company", "employer", "organization"]) if x else False)
        location_elem = container.find(["span", "div", "p"], class_=lambda x: x and any(loc_term in x.lower() for loc_term in ["location", "place", "address", "city"]) if x else False)
        description_elem = container.find(["p", "div"], class_=lambda x: x and any(desc_term in x.lower() for desc_term in ["description", "summary", "detail"]) if x else False)
        link_elem = container.find("a", href=True)
        
        title = clean_text(title_elem.get_text()) if title_elem else ""
        company = clean_text(company_elem.get_text()) if company_elem else ""
        location = clean_text(location_elem.get_text()) if location_elem else ""
        description = clean_text(description_elem.get_text()) if description_elem else ""
        
        # If we found a title or link, consider it a valid job listing
        if title or (link_elem and link_elem.get("href")):
            link = urljoin(base_url, link_elem.get("href")) if link_elem else ""
            jobs.append({
                "title": title,
                "company": company,
                "location": location,
                "description": description,
                "link": link
            })
    
    return jobs

def extract_products(soup, base_url):
    """Extract product information from the page."""
    products = []
    # Common product container classes
    product_containers = soup.find_all("div", class_=lambda x: x and any(prod_term in x.lower() for prod_term in ["product", "item", "goods", "merchandise"]))
    
    # If no specific product containers found, look for generic listings
    if not product_containers:
        product_containers = soup.find_all(["div", "li"], class_=lambda x: x and any(list_term in x.lower() for list_term in ["item", "card", "listing", "post"]))
    
    for container in product_containers:
        # Try to find the product name, price, image
        name_elem = container.find(["h1", "h2", "h3", "h4", "a"], class_=lambda x: x and any(name_term in x.lower() for name_term in ["name", "title", "product"]) if x else False) or container.find(["h1", "h2", "h3", "h4", "a"])
        price_elem = container.find(["span", "div", "p"], class_=lambda x: x and any(price_term in x.lower() for price_term in ["price", "cost", "amount"]) if x else False)
        image_elem = container.find("img")
        link_elem = container.find("a", href=True)
        
        name = clean_text(name_elem.get_text()) if name_elem else ""
        price = clean_text(price_elem.get_text()) if price_elem else ""
        image = image_elem.get("src") if image_elem else ""
        
        # If we found a name or image, consider it a valid product
        if name or image:
            link = urljoin(base_url, link_elem.get("href")) if link_elem else ""
            product = {
                "name": name,
                "price": price,
                "link": link
            }
            # Add image URL only if it exists and is not a data URI
            if image and not image.startswith("data:"):
                product["image_url"] = urljoin(base_url, image)
            
            products.append(product)
    
    return products

def extract_articles(soup, base_url):
    """Extract articles or blog posts from the page."""
    articles = []
    # Common article container elements
    article_containers = soup.find_all(["article", "div"], class_=lambda x: x and any(art_term in x.lower() for art_term in ["article", "post", "blog", "news", "entry"]))
    
    # If no specific article containers found, look for headings with text
    if not article_containers:
        article_containers = []
        for heading in soup.find_all(["h1", "h2", "h3"]):
            if heading.get_text(strip=True) and len(heading.get_text(strip=True)) > 15:
                article_containers.append(heading.parent)
    
    for container in article_containers:
        # Try to find the article title, summary, date, author
        title_elem = container.find(["h1", "h2", "h3", "h4"], class_=lambda x: x and any(title_term in x.lower() for title_term in ["title", "heading"]) if x else False) or container.find(["h1", "h2", "h3", "h4"])
        summary_elem = container.find(["p", "div"], class_=lambda x: x and any(summ_term in x.lower() for summ_term in ["summary", "excerpt", "description", "content"]) if x else False) or container.find("p")
        date_elem = container.find(["span", "time", "div"], class_=lambda x: x and any(date_term in x.lower() for date_term in ["date", "time", "published"]) if x else False)
        author_elem = container.find(["span", "div", "a"], class_=lambda x: x and any(auth_term in x.lower() for auth_term in ["author", "by", "writer"]) if x else False)
        link_elem = container.find("a", href=True) or title_elem.find("a", href=True) if title_elem else None
        
        title = clean_text(title_elem.get_text()) if title_elem else ""
        summary = clean_text(summary_elem.get_text()) if summary_elem else ""
        date = clean_text(date_elem.get_text()) if date_elem else ""
        author = clean_text(author_elem.get_text()) if author_elem else ""
        
        # If we found a title or summary, consider it a valid article
        if title or summary:
            link = urljoin(base_url, link_elem.get("href")) if link_elem else ""
            articles.append({
                "title": title,
                "summary": summary,
                "date": date,
                "author": author,
                "link": link
            })
    
    return articles

def extract_table_data(soup):
    """Extract data from tables on the page."""
    tables_data = []
    
    for table in soup.find_all("table"):
        headers = []
        rows = []
        
        # Extract headers
        header_row = table.find("tr")
        if header_row:
            headers = [clean_text(th.get_text()) for th in header_row.find_all(["th", "td"])]
        
        # Extract rows
        for row in table.find_all("tr")[1:] if headers else table.find_all("tr"):
            cells = [clean_text(cell.get_text()) for cell in row.find_all(["td", "th"])]
            if cells:
                if headers and len(headers) == len(cells):
                    rows.append(dict(zip(headers, cells)))
                else:
                    rows.append({"cells": cells})
        
        if rows:
            tables_data.append({
                "headers": headers,
                "rows": rows,
                "row_count": len(rows)
            })
    
    return tables_data

def extract_links(soup, base_url):
    """Extract important links from the page."""
    links = []
    
    for link in soup.find_all("a", href=True):
        href = link.get("href")
        absoulute_url = urljoin(base_url,href)
        text = clean_text(link.get_text())
        
        # Skip empty links, anchors, and javascript
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue
            
        # Make link absolute
        full_url = urljoin(base_url, href)
        
        # Only include links with text
        if text:
            links.append({
                "text": text,
                "url": full_url
            })
    
    return links

def extract_images(soup, base_url):
    """Extract important images from the page."""
    images = []
    
    for img in soup.find_all("img"):
        src = img.get("src")
        alt = img.get("alt", "")
        
        # Skip data URIs and empty sources
        if not src or src.startswith("data:"):
            continue
            
        # Make image URL absolute
        full_url = urljoin(base_url, src)
        
        images.append({
            "url": full_url,
            "alt": alt
        })
    
    return images

def extract_headings(soup):
    """Extract hierarchical headings from the page."""
    headings = []
    
    for level in range(1, 7):
        for heading in soup.find_all(f"h{level}"):
            text = clean_text(heading.get_text())
            if text:
                headings.append({
                    "level": level,
                    "text": text
                })
    
    return headings

def extract_main_content(soup):
    """Extract what appears to be the main content from the page."""
    # Try to find main content containers
    main_containers = soup.find_all(["main", "article", "div"], class_=lambda x: x and any(main_term in x.lower() for main_term in ["main", "content", "article", "body"]) if x else False)
    
    if main_containers:
        # Use the container with the most text content
        main_container = max(main_containers, key=lambda x: len(x.get_text(strip=True)))
        
        # Extract paragraphs from the main container
        paragraphs = [clean_text(p.get_text()) for p in main_container.find_all("p")]
        return [p for p in paragraphs if p and len(p) > 20]  # Filter out very short paragraphs
    
    # Fallback: extract all paragraphs from the page
    paragraphs = [clean_text(p.get_text()) for p in soup.find_all("p")]
    return [p for p in paragraphs if p and len(p) > 20]  # Filter out very short paragraphs

def remove_redundant_data(data_list):
    """Remove duplicate or nearly duplicate entries from a list of dictionaries."""
    unique_data = []
    seen_titles = set()
    
    for item in data_list:
        if "title" in item and item["title"]:
            title = item["title"].lower()
            if title not in seen_titles:
                seen_titles.add(title)
                unique_data.append(item)
        else:
            unique_data.append(item)
    
    return unique_data

def smart_scrape(url):
    """Intelligently scrape a website based on its content type."""
    driver = setup_selenium_driver()
    
    try:
        html_content = get_html_content(url, driver)
        if not html_content:
            return {"error": "Failed to retrieve content from the URL"}
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove unwanted elements
        for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
            tag.decompose()
        
        # Try to get structured data first
        schema_data = extract_schema_data(soup)
        
        # Detect content type
        content_type = detect_content_type(soup)
        
        # Extract data based on content type
        result = {
            "page_title": soup.title.get_text() if soup.title else "",
            "content_type": content_type,
            "url": url
        }
        
        # Add schema data if available
        if schema_data:
            result["schema_data"] = schema_data
        
        # Extract specific data based on content type
        if content_type == "job_listing":
            jobs = extract_job_listings(soup, url)
            result["jobs"] = remove_redundant_data(jobs)
        
        elif content_type == "product":
            products = extract_products(soup, url)
            result["products"] = remove_redundant_data(products)
        
        elif content_type == "article":
            articles = extract_articles(soup, url)
            result["articles"] = remove_redundant_data(articles)
        
        elif content_type == "table_data":
            tables = extract_table_data(soup)
            result["tables"] = tables
        
        elif content_type == "directory":
            links = extract_links(soup, url)
            result["links"] = links
        
        elif content_type == "image_gallery":
            images = extract_images(soup, url)
            result["images"] = images
        
        else:
            # General content extraction
            result["headings"] = extract_headings(soup)
            result["main_content"] = extract_main_content(soup)
            result["links"] = extract_links(soup, url)[:20]  # Limit to top 20 links
        
        return result
    
    except Exception as e:
        return {"error": str(e)}
    
    finally:
        driver.quit()

def create_download_link(data, file_format):
    """Create a download link for the scraped data."""
    if file_format == 'JSON':
        json_data = json.dumps(data, indent=4)
        b64 = base64.b64encode(json_data.encode()).decode()
        href = f'<a href="data:file/json;base64,{b64}" download="scraped_data.json">Download JSON File</a>'
    elif file_format == 'CSV':
        # Convert to DataFrame based on content type
        content_type = data.get("content_type", "general")
        
        if content_type == "job_listing" and "jobs" in data:
            df = pd.DataFrame(data["jobs"])
        elif content_type == "product" and "products" in data:
            df = pd.DataFrame(data["products"])
        elif content_type == "article" and "articles" in data:
            df = pd.DataFrame(data["articles"])
        elif content_type == "table_data" and "tables" in data and data["tables"]:
            # Use the first table with headers
            for table in data["tables"]:
                if table["headers"]:
                    df = pd.DataFrame(table["rows"])
                    break
            else:
                # Fallback to a simple representation
                df = pd.DataFrame([{"table_count": len(data["tables"])}])
        else:
            # Create a simple DataFrame for other content types
            if "main_content" in data and data["main_content"]:
                df = pd.DataFrame({"content": data["main_content"]})
            elif "links" in data and data["links"]:
                df = pd.DataFrame(data["links"])
            else:
                df = pd.DataFrame([{"page_title": data.get("page_title", "")}])
        
        csv_data = df.to_csv(index=False)
        b64 = base64.b64encode(csv_data.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="scraped_data.csv">Download CSV File</a>'
    
    return href

def display_scraped_data(data):
    """Display the scraped data in an organized way."""
    if "error" in data:
        st.error(f"Error: {data['error']}")
        return
    
    st.success(f"✅ Successfully scraped the website!")
    
    st.markdown(f"### Page Title: {data['page_title']}")
    st.markdown(f"**Content Type Detected:** {data['content_type'].replace('_', ' ').title()}")
    
    # Display data based on content type
    if data["content_type"] == "job_listing" and "jobs" in data:
        st.markdown("### 💼 Job Listings")
        for i, job in enumerate(data["jobs"]):
            with st.expander(f"{job.get('title', 'Job')} at {job.get('company', 'Company')}"):
                st.write(f"**Title:** {job.get('title', 'N/A')}")
                st.write(f"**Company:** {job.get('company', 'N/A')}")
                st.write(f"**Location:** {job.get('location', 'N/A')}")
                if job.get('description'):
                    st.write(f"**Description:** {job.get('description')}")
                if job.get('link'):
                    st.write(f"**Link:** [{job.get('link')}]({job.get('link')})")
    
    elif data["content_type"] == "product" and "products" in data:
        st.markdown("### 🛍️ Products")
        
        # Create rows of 3 products
        for i in range(0, len(data["products"]), 3):
            cols = st.columns(3)
            for j in range(3):
                if i+j < len(data["products"]):
                    product = data["products"][i+j]
                    with cols[j]:
                        st.subheader(product.get('name', 'Product'))
                        st.write(f"**Price:** {product.get('price', 'N/A')}")
                        if product.get('link'):
                            st.write(f"[View Product]({product.get('link')})")
    
    elif data["content_type"] == "article" and "articles" in data:
        st.markdown("### 📰 Articles")
        for article in data["articles"]:
            with st.expander(article.get('title', 'Article')):
                st.write(f"**Title:** {article.get('title', 'N/A')}")
                if article.get('date'):
                    st.write(f"**Date:** {article.get('date')}")
                if article.get('author'):
                    st.write(f"**Author:** {article.get('author')}")
                if article.get('summary'):
                    st.write(f"**Summary:** {article.get('summary')}")
                if article.get('link'):
                    st.write(f"**Link:** [{article.get('link')}]({article.get('link')})")
    
    elif data["content_type"] == "table_data" and "tables" in data:
        st.markdown("### 📊 Tables")
        for i, table in enumerate(data["tables"]):
            st.subheader(f"Table {i+1}")
            if table["headers"]:
                df = pd.DataFrame(table["rows"])
                st.dataframe(df)
            else:
                # Display tables without headers
                rows_data = [row.get("cells", []) for row in table["rows"]]
                df = pd.DataFrame(rows_data)
                st.dataframe(df)
    
    elif data["content_type"] == "directory" and "links" in data:
        st.markdown("### 🔗 Directory Links")
        links_df = pd.DataFrame(data["links"])
        st.dataframe(links_df)
    
    elif data["content_type"] == "image_gallery" and "images" in data:
        st.markdown("### 🖼️ Image Gallery")
        image_count = len(data["images"])
        st.write(f"Found {image_count} images on the page")
        
        # Display a sample of images
        for i, img in enumerate(data["images"][:10]):  # Show max 10 images
            st.write(f"**Image {i+1}:** {img.get('alt', 'No description')}")
            st.write(f"URL: {img.get('url')}")
    
    else:
        # General content display
        if "headings" in data and data["headings"]:
            st.markdown("### 📑 Main Headings")
            for heading in data["headings"]:
                if heading["level"] <= 3:  # Only show h1-h3 to keep it clean
                    st.write(f"{'#' * heading['level']} {heading['text']}")
        
        if "main_content" in data and data["main_content"]:
            st.markdown("### 📝 Main Content")
            for i, paragraph in enumerate(data["main_content"][:5]):  # Show max 5 paragraphs
                st.write(paragraph)
            if len(data["main_content"]) > 5:
                st.write(f"... and {len(data['main_content']) - 5} more paragraphs")
        
        if "links" in data and data["links"]:
            st.markdown("### 🔗 Important Links")
            links_df = pd.DataFrame(data["links"][:10])  # Show max 10 links
            st.dataframe(links_df)
    
    return True

# Main Streamlit app
def main():
    st.markdown("<div class='main-title'>🕸️ Web Scraper</div>", unsafe_allow_html=True)
    
    st.write("Enter the URL of the website you want to scrape:")
    
    url = st.text_input("URL")
    file_format = st.selectbox("Select file format to save data:", ["JSON", "CSV"])
    
    if st.button("Scrape", key="scrape_button", help="Click to start scraping"):
        if not url:
            st.error("Please enter a URL to scrape")
            return
        
        with st.spinner("Analyzing and scraping the website..."):
            try:
                scraped_data = smart_scrape(url)
                
                if scraped_data and "error" not in scraped_data:
                    display_scraped_data(scraped_data)
                    download_link = create_download_link(scraped_data, file_format)
                    st.markdown("### Download Data")
                    st.markdown(download_link, unsafe_allow_html=True)
                else:
                    st.error(f"Failed to scrape the website: {scraped_data.get('error', 'Unknown error')}")
            except Exception as e:
                st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()


