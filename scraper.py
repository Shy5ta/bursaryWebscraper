"""
Bursary Web Scraper - Actually works now
"""

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
    """
    Find closing date - it's in an h3 tag followed by a p tag
    """
    try:
        time.sleep(0.5)
        
        page = requests.get(bursaryUrl, headers=HEADERS, timeout=5)
        
        if page.status_code != 200:
            print(f"  Warning: Status {page.status_code}")
            return "Check Link"

        soup = BeautifulSoup(page.content, 'html.parser')
        
        contentDiv = soup.find('div', class_='entry-content')
        if not contentDiv:
            return "Not Found"

        # look for h3 tags that mention "closing date"
        h3Tags = contentDiv.find_all('h3')
        
        for h3 in h3Tags:
            h3Text = h3.get_text().strip()
            
            # check if this h3 is about closing date
            if 'closing date' in h3Text.lower():
                # the actual date should be in the next p tag
                nextP = h3.find_next('p')
                
                if nextP:
                    dateText = nextP.get_text().strip()
                    
                    # clean it up - remove extra whitespace and newlines
                    dateText = ' '.join(dateText.split())
                    
                    # sometimes there's extra junk, just take the first line/sentence
                    dateText = dateText.split('\n')[0].strip()
                    
                    if len(dateText) > 3 and len(dateText) < 100:
                        return dateText
        
        # if we didn't find it in h3, maybe try h2 or h4
        for heading in contentDiv.find_all(['h2', 'h4', 'h5']):
            headingText = heading.get_text().strip()
            if 'closing date' in headingText.lower() or 'deadline' in headingText.lower():
                nextP = heading.find_next('p')
                if nextP:
                    dateText = nextP.get_text().strip()
                    dateText = ' '.join(dateText.split())
                    if len(dateText) > 3 and len(dateText) < 100:
                        return dateText
        
        return "Open / Unspecified"
        
    except requests.exceptions.Timeout:
        print(f"  Timeout")
        return "Timeout - Check Manually"
    except Exception as e:
        print(f"  Error: {str(e)[:50]}")
        return "Error"

def getBursaryLinks(targetUrl, maxBursaries=20):
    """
    Gets the list of bursary links from the main page
    """
    bursaryList = []
    print(f"Connecting to {targetUrl}...")

    try:
        page = requests.get(targetUrl, headers=HEADERS, timeout=15)

        if page.status_code == 200:
            soup = BeautifulSoup(page.content, 'html.parser')
            contentArea = soup.find('div', class_='entry-content')
            
            if contentArea:
                listItems = contentArea.find_all('li')
                totalItems = len(listItems)
                print(f"Found {totalItems} links")
                print(f"Processing first {maxBursaries}...\n")
                
                processedCount = 0
                
                for index, item in enumerate(listItems, 1):
                    if processedCount >= maxBursaries:
                        print(f"\nStopped at {maxBursaries}")
                        break
                    
                    linkElement = item.find('a')
                    
                    if linkElement:
                        title = linkElement.text.strip()
                        href = linkElement.get('href')
                        
                        if href and ('bursary' in href or 'scholarship' in href):
                            print(f"[{processedCount+1}/{maxBursaries}] {title[:60]}...")
                            deadline = getBursaryDetails(href)
                            print(f"  -> {deadline}")
                            
                            bursaryList.append({
                                "Bursary Name": title,
                                "Closing Date": deadline, 
                                "Link": href,
                                "Date Scraped": datetime.now().strftime("%Y-%m-%d")
                            })
                            
                            processedCount += 1
                
                print(f"\nScraped {len(bursaryList)} bursaries")
            else:
                print("Error: Content div not found")
        else:
            print(f"Error: Status {page.status_code}")

    except Exception as e:
        print(f"Error: {e}")

    return bursaryList

def saveToExcel(data, filename="bursaries.xlsx"):
    """
    Saves to Excel file
    """
    if not data:
        print("No data to save")
        return
        
    df = pd.DataFrame(data)
    df = df[["Bursary Name", "Closing Date", "Link", "Date Scraped"]]
    df.to_excel(filename, index=False)
    print(f"Saved {len(data)} bursaries to {filename}")

def sendEmail(filename):
    """
    Sends email with the Excel attachment
    """
    emailSender = os.environ.get('EMAIL_USER')
    emailPassword = os.environ.get('EMAIL_PASS')
    
    if not emailSender or not emailPassword:
        print("Skipping email - no credentials")
        return

    emailReceiver = emailSender
    subject = f"Bursary Report - {datetime.now().strftime('%Y-%m-%d')}"
    body = "Latest bursary list with closing dates attached."

    msg = MIMEMultipart()
    msg['From'] = emailSender
    msg['To'] = emailReceiver
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with open(filename, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={filename}")
        msg.attach(part)
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(emailSender, emailPassword)
        server.sendmail(emailSender, emailReceiver, msg.as_string())
        server.quit()
        print("Email sent")

    except Exception as e:
        print(f"Email failed: {e}")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("BURSARY SCRAPER")
    print("="*60 + "\n")
    
    startTime = time.time()
    
    results = getBursaryLinks(URL, maxBursaries=20)
    
    duration = time.time() - startTime
    
    if results:
        excelFilename = "bursaries.xlsx"
        saveToExcel(results, excelFilename)
        sendEmail(excelFilename)
        
        print(f"\nDone - {len(results)} bursaries in {duration:.1f}s")
    else:
        print(f"\nNo results - {duration:.1f}s")
