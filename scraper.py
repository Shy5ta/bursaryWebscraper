import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import time
import json
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

URL = "https://www.zabursaries.co.za/computer-science-it-bursaries-south-africa/"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def getBursaryDetails(bursaryUrl):
    #Get the bursary details but only if they were updated within the last 6 months
    
    result = {
        "lastUpdated": "Unknown"
    }

    try:
        time.sleep(0.5)  # A pause so that the server is not flooded by my reqs
        page = requests.get(bursaryUrl, headers=HEADERS, timeout=10)
        page.raise_for_status()  # Raises exception for 4xx/5xx status codes

        soup = BeautifulSoup(page.content, 'html.parser')

        # Find Hidden JSON-LD Date
        schemaTags = soup.find_all("script", type="application/ld+json")
        for tag in schemaTags:
            try:
                data = json.loads(tag.string)
                if "@graph" in data:
                    for item in data["@graph"]:
                        if item.get("@type") == "WebPage" and "dateModified" in item:
                            rawTime = item["dateModified"]
                            if len(rawTime) >= 10:
                                result["lastUpdated"] = rawTime[:10]
                                return result  # Found it, return immediately
                            
            except json.JSONDecodeError:
                logging.warning(f"Invalid JSON in schema tag for {bursaryUrl}")
                continue
            except Exception as e:
                logging.warning(f"Error parsing schema tag: {e}")
                continue
        
        # Otherwise find Meta tag
        if result["lastUpdated"] == "Unknown":
            metaDate = soup.find("meta", property="article:modified_time")
            if metaDate:
                result["lastUpdated"] = metaDate.get("content", "")[:10]

    except requests.Timeout:
        logging.warning(f"Timeout fetching {bursaryUrl}")
    except requests.RequestException as e:
        logging.error(f"Network error fetching {bursaryUrl}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error processing {bursaryUrl}: {e}")

    return result

def getBursaryLinks(targetUrl):
    #Scrape the main bursary listing page and filter by recent
    bursaryList = []
    seen_urls = set()  # checking there are no duplicates
    
    logging.info(f"Connecting to {targetUrl}...")

    # the 6-Month Cutoff
    sixMonthsAgo = datetime.now() - timedelta(days=180)
    logging.info(f"Filtering: Only keeping bursaries updated after {sixMonthsAgo.strftime('%Y-%m-%d')}")
    print("-" * 50)

    try:
        page = requests.get(targetUrl, headers=HEADERS, timeout=15)
        page.raise_for_status()

        soup = BeautifulSoup(page.content, 'html.parser')
        contentArea = soup.find('div', class_='entry-content')
        
        if not contentArea:
            logging.error("Could not find content area on page")
            return bursaryList
            
        listItems = contentArea.find_all('li')
        totalCount = len(listItems)
        logging.info(f"Found {totalCount} bursary listings to check")
        
        for index, item in enumerate(listItems):
            linkElement = item.find('a')
            
            if linkElement:
                title = linkElement.text.strip()
                href = linkElement.get('href')
                
                # Duplication check
                if href in seen_urls:
                    continue  # Skip if the link was already checked
                
                if href and ('bursary' in href or 'scholarship' in href):
                    # Add to seen list
                    seen_urls.add(href)
                    
                    print(f"Scanning [{index+1}/{totalCount}]: {title} ... ", end="", flush=True)
                    
                    details = getBursaryDetails(href)
                    lastUpdatedStr = details["lastUpdated"]
                    
                    # Checking for bursaries within the last 6 months
                    isNew = False
                    if lastUpdatedStr != "Unknown":
                        try:
                            updateDate = datetime.strptime(lastUpdatedStr, "%Y-%m-%d")
                            if updateDate > sixMonthsAgo:
                                isNew = True
                        except ValueError as e:
                            logging.warning(f"Invalid date format '{lastUpdatedStr}' for {title}: {e}")
                    
                    if isNew:
                        print(f"KEEP (Updated {lastUpdatedStr})")
                        bursaryList.append({
                            "Bursary Name": title,
                            "Last Updated": details["lastUpdated"], 
                            "Link": href
                        })
                    else:
                        print(f"SKIP (Old: {lastUpdatedStr})")

    except requests.Timeout:
        logging.error(f"Timeout connecting to {targetUrl}")
    except requests.RequestException as e:
        logging.error(f"Network error: {e}")
    except Exception as e:
        logging.error(f"Critical error during scraping: {e}")

    return bursaryList

def sortBursariesByDate(data):
    #Sort bursaries by last updated date, newest
    def getSortDate(item):
        try:
            return datetime.strptime(item["Last Updated"], "%Y-%m-%d")
        except (ValueError, KeyError):
            return datetime(2000, 1, 1)

    data.sort(key=getSortDate, reverse=True)
    return data

def saveToExcel(data, filename="ZABursaries_List.xlsx"):
    #Save bursary data to Excel file
    if not data: 
        logging.warning("No bursaries to save")
        return False
    
    try:
        df = pd.DataFrame(data)
        df = df[["Bursary Name", "Last Updated", "Link"]]
        df.to_excel(filename, index=False)
        logging.info(f"Successfully saved {len(data)} bursaries to {filename}")
        return True
    except PermissionError:
        logging.error(f"Permission denied: Cannot write to {filename}")
        return False
    except Exception as e:
        logging.error(f"Error saving Excel file: {e}")
        return False

def sendEmail(filename):
    #Send the Excel file via email
    emailSender = os.environ.get('EMAIL_USER')
    emailPassword = os.environ.get('EMAIL_PASS')
    
    if not emailSender or not emailPassword:
        logging.error("Missing EMAIL_USER or EMAIL_PASS environment variables")
        return False

    emailReceiver = emailSender
    
    msg = MIMEMultipart()
    msg['From'] = emailSender
    msg['To'] = emailReceiver
    msg['Subject'] = f"Bursaries (Last 6 Months) - {datetime.now().strftime('%Y-%m-%d')}"
    
    body = "Here are the bursaries updated in the last 6 months."
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Check if file exists
        if not os.path.exists(filename):
            logging.error(f"Attachment file {filename} not found")
            return False
            
        with open(filename, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename= {filename}")
        msg.attach(part)
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(emailSender, emailPassword)
        server.sendmail(emailSender, emailReceiver, msg.as_string())
        server.quit()
        
        logging.info("Email sent successfully")
        return True

    except smtplib.SMTPAuthenticationError:
        logging.error("Email authentication failed - check your app password")
        return False
    except smtplib.SMTPException as e:
        logging.error(f"SMTP error: {e}")
        return False
    except FileNotFoundError:
        logging.error(f"Attachment file {filename} not found")
        return False
    except Exception as e:
        logging.error(f"Unexpected error sending email: {e}")
        return False

if __name__ == "__main__":
    logging.info("Starting bursary scraper...")
    
    results = getBursaryLinks(URL)
    
    if results:
        logging.info(f"Found {len(results)} new bursaries")
        sortedResults = sortBursariesByDate(results)
        
        if saveToExcel(sortedResults):
            sendEmail("ZABursaries_List.xlsx")
        else:
            logging.error("Failed to save Excel file, skipping email")
    else:
        logging.info("No new bursaries found in the last 6 months")
    
    logging.info("Scraper finished")


