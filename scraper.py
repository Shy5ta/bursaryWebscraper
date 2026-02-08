import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import time

URL = "https://www.zabursaries.co.za/computer-science-it-bursaries-south-africa/"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def getBursaryDetails(bursaryUrl):
   
    result = {
        "closingDate": "Open / Unspecified",
        "lastUpdated": "Unknown"
    }
    
    try:
        time.sleep(0.5) # Be polite
        page = requests.get(bursaryUrl, headers=HEADERS)
        if page.status_code != 200:
            return result

        soup = BeautifulSoup(page.content, 'html.parser')

        #Find Hidden "Last Updated" Meta Tag
        metaDate = soup.find("meta", property="article:modified_time")
        
        if not metaDate:
            metaDate = soup.find("meta", property="og:updated_time")
            
        if metaDate:
            rawTime = metaDate.get("content", "")
            if len(rawTime) >= 10:
                result["lastUpdated"] = rawTime[:10]

        # Find "Closing Date"
        contentDiv = soup.find('div', class_='entry-content')
        if contentDiv:
            allText = contentDiv.get_text(separator="\n").split("\n")
            keywords = ["Closing Date", "Deadline", "Applications close"]
            
            for line in allText:
                cleanLine = line.strip()
                if not cleanLine: continue
                
                for key in keywords:
                    if key.lower() in cleanLine.lower():
                        rawDate = cleanLine.lower().replace(key.lower(), "").replace(":", "").strip()
                        if len(rawDate) > 2:
                            result["closingDate"] = rawDate.title()
                            break # Stop searching if we found it
                if result["closingDate"] != "Open / Unspecified":
                    break

    except Exception as e:
        print(f"Error scraping details: {e}")

    return result

def getBursaryLinks(targetUrl):
    bursaryList = []
    print(f"Connecting to {targetUrl}...")

    try:
        page = requests.get(targetUrl, headers=HEADERS)

        if page.status_code == 200:
            soup = BeautifulSoup(page.content, 'html.parser')
            contentArea = soup.find('div', class_='entry-content')
            
            if contentArea:
                listItems = contentArea.find_all('li')
                totalCount = len(listItems)
                print(f"Found {totalCount} bursaries. Checking for recent updates...")
                print("-" * 50)
                
                for index, item in enumerate(listItems):
                    linkElement = item.find('a')
                    
                    if linkElement:
                        title = linkElement.text.strip()
                        href = linkElement.get('href')
                        
                        if href and ('bursary' in href or 'scholarship' in href):
                            print(f"Scanning [{index+1}/{totalCount}]: {title}")
                            
                            # Get BOTH details
                            details = getBursaryDetails(href)
                            
                            bursaryList.append({
                                "Bursary Name": title,
                                "Closing Date": details["closingDate"],
                                "Last Updated": details["lastUpdated"], # <--- New Field
                                "Link": href
                            })
            else:
                print("Error: Could not find list.")
        else:
            print(f"Error: Server code {page.status_code}")

    except Exception as e:
        print(f"Critical Error: {e}")

    return bursaryList

def sortBursariesByFreshness(data):
    """
    Sorts bursaries so the ones updated RECENTLY appear first.
    """
    print("\nSorting by Last Updated (Freshness)...")
    
    def getSortDate(item):
        dateStr = item["Last Updated"]
        # If unknown, put it at the bottom (year 2000)
        if dateStr == "Unknown":
            return datetime(2000, 1, 1)
        try:
            return datetime.strptime(dateStr, "%Y-%m-%d")
        except:
            return datetime(2000, 1, 1)

    # DESCENDING order (Newest dates first)
    data.sort(key=getSortDate, reverse=True)
    return data

def saveToExcel(data, filename="bursaries_fresh.xlsx"):
    if not data: return
    
    df = pd.DataFrame(data)
    # Order columns nicely
    df = df[["Bursary Name", "Last Updated", "Closing Date", "Link"]]
    
    df.to_excel(filename, index=False)
    print(f"Success! Saved {len(data)} bursaries to {filename}")

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
    msg['Subject'] = f"Bursary Intelligence Report - {datetime.now().strftime('%Y-%m-%d')}"
    
    body = "Here is the list of bursaries, sorted by most recently updated."
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
    # 1. Scrape
    results = getBursaryLinks(URL)
    
    if results:
        # 2. Sort by Update Time
        sortedResults = sortBursariesByFreshness(results)
        
        # 3. Save
        saveToExcel(sortedResults)
        # sendEmail("bursaries_fresh.xlsx")
