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

URL = "https://www.zabursaries.co.za/computer-science-it-bursaries-south-africa/"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def getBursaryDetails(bursaryUrl):
    """
    Only extracts 'dateModified' (Last Updated).
    """
    result = {
        "lastUpdated": "Unknown"
    }

    try:
        time.sleep(0.5) 
        page = requests.get(bursaryUrl, headers=HEADERS)
        if page.status_code != 200:
            return result 

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
                                return result # Found it, return immediately
            except:
                continue
        
        # Otherwise find Meta tag
        if result["lastUpdated"] == "Unknown":
            metaDate = soup.find("meta", property="article:modified_time")
            if metaDate:
                result["lastUpdated"] = metaDate.get("content", "")[:10]

    except Exception:
        pass

    return result

def getBursaryLinks(targetUrl):
    bursaryList = []
    seen_urls = set() # checking there are no duplicates
    
    print(f"Connecting to {targetUrl}...")

    # the 6-Month Cutoff
    sixMonthsAgo = datetime.now() - timedelta(days=180)
    print(f"Filtering: Only keeping bursaries updated after {sixMonthsAgo.strftime('%Y-%m-%d')}")
    print("-" * 50)

    try:
        page = requests.get(targetUrl, headers=HEADERS)

        if page.status_code == 200:
            soup = BeautifulSoup(page.content, 'html.parser')
            contentArea = soup.find('div', class_='entry-content')
            
            if contentArea:
                listItems = contentArea.find_all('li')
                totalCount = len(listItems)
                
                for index, item in enumerate(listItems):
                    linkElement = item.find('a')
                    
                    if linkElement:
                        title = linkElement.text.strip()
                        href = linkElement.get('href')
                        
                        # Duplication check
                        if href in seen_urls:
                            continue # Skip if the link was already checked
                        
                        if href and ('bursary' in href or 'scholarship' in href):
                            # Add to seen list
                            seen_urls.add(href)
                            
                            print(f"Scanning [{index+1}/{totalCount}]: {title} ... ", end="", flush=True)
                            
                            details = getBursaryDetails(href)
                            lastUpdatedStr = details["lastUpdated"]
                            
                            # Checking for bursaries within the last 6 months
                            isFresh = False
                            if lastUpdatedStr != "Unknown":
                                try:
                                    updateDate = datetime.strptime(lastUpdatedStr, "%Y-%m-%d")
                                    if updateDate > sixMonthsAgo:
                                        isFresh = True
                                except:
                                    pass
                            
                            if isFresh:
                                print(f"KEEP (Updated {lastUpdatedStr})")
                                bursaryList.append({
                                    "Bursary Name": title,
                                    "Last Updated": details["lastUpdated"], 
                                    "Link": href
                                })
                            else:
                                print(f"SKIP (Old: {lastUpdatedStr})")

            else:
                print("Error: Could not find list.")
        else:
            print(f"Error: Server code {page.status_code}")

    except Exception as e:
        print(f"Critical Error: {e}")

    return bursaryList

def sortBursariesByFreshness(data):
    def getSortDate(item):
        try:
            return datetime.strptime(item["Last Updated"], "%Y-%m-%d")
        except:
            return datetime(2000, 1, 1)

    data.sort(key=getSortDate, reverse=True)
    return data

def saveToExcel(data, filename="ZABursaries_List.xlsx"):
    if not data: 
        print("No fresh bursaries found.")
        return
    
    df = pd.DataFrame(data)
    df = df[["Bursary Name", "Last Updated", "Link"]]
    df.to_excel(filename, index=False)
    print(f"\nSuccess! Saved {len(data)} fresh bursaries to {filename}")

def sendEmail(filename):
    emailSender = os.environ.get('EMAIL_USER')
    emailPassword = os.environ.get('EMAIL_PASS')
    
    if not emailSender:
        print("Skipping email: No environment variables set.")
        return

    emailReceiver = emailSender
    
    msg = MIMEMultipart()
    msg['From'] = emailSender
    msg['To'] = emailReceiver
    msg['Subject'] = f"Fresh Bursaries (Last 6 Months) - {datetime.now().strftime('%Y-%m-%d')}"
    
    body = "Here are the bursaries updated in the last 6 months."
    msg.attach(MIMEText(body, 'plain'))

    try:
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
        print("Email sent successfully.")

    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == "__main__":
    results = getBursaryLinks(URL)
    
    if results:
        sortedResults = sortBursariesByFreshness(results)
        saveToExcel(sortedResults)
        sendEmail("ZABursaries_List.xlsx")

