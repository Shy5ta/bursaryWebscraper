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
import re

URL = "https://www.zabursaries.co.za/computer-science-it-bursaries-south-africa/"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def getBursaryDetails(bursaryUrl):
    """
    Trying to find the actual closing date on the bursary page
    """
    try:
        # Preventing spamming their server
        time.sleep(0.5)
        
        page = requests.get(bursaryUrl, headers=HEADERS, timeout=5)
        
        if page.status_code != 200:
            print(f"  Warning: Got status {page.status_code}")
            return "Check Link"

        soup = BeautifulSoup(page.content, 'html.parser')
        
        contentDiv = soup.find('div', class_='entry-content')
        if not contentDiv:
            return "Not Found"

        # grab all the text from the page
        fullText = contentDiv.get_text()
        
        # look for "Closing Date" followed by whatever the actual date is
        # regex pattern: finds "Closing Date" then grabs everything after it until a newline
        closingDatePattern = r'Closing\s+Date\s*:?\s*([^\n]+)'
        match = re.search(closingDatePattern, fullText, re.IGNORECASE)
        
        if match:
            # this should be the actual date text
            dateText = match.group(1).strip()
            
            dateText = dateText.split('\n')[0]  # just first line
            dateText = dateText.split('.')[0]   # remove stuff after period
            dateText = dateText.strip()
            
            if len(dateText) > 3 and len(dateText) < 100:
                return dateText
        
        alternativePatterns = [
            r'Deadline\s*:?\s*([^\n]+)',
            r'Applications\s+close\s*:?\s*([^\n]+)',
            r'Close\s+date\s*:?\s*([^\n]+)'
        ]
        
        for pattern in alternativePatterns:
            match = re.search(pattern, fullText, re.IGNORECASE)
            if match:
                dateText = match.group(1).strip().split('\n')[0].strip()
                if len(dateText) > 3 and len(dateText) < 100:
                    return dateText
        
        return "Open / Unspecified"
        
    except requests.exceptions.Timeout:
        print(f"  Timeout - took too long to load")
        return "Timeout - Check Manually"
    except requests.exceptions.RequestException as e:
        print(f"  Request failed")
        return "Error"
    except Exception as e:
        print(f"  Something went wrong")
        return "Error"

def getBursaryLinks(targetUrl, maxBursaries=20):
    """
    Scrapes the main page for bursary links
    Only processes first 20 to avoid timing out on GitHub Actions
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
                print(f"Found {totalItems} links on the page")
                print(f"Processing up to {maxBursaries} to stay under time limit...\n")
                
                processedCount = 0
                
                for index, item in enumerate(listItems, 1):
                    # stop after we hit the limit
                    if processedCount >= maxBursaries:
                        print(f"\nStopped at {maxBursaries} bursaries (timeout protection)")
                        break
                    
                    linkElement = item.find('a')
                    
                    if linkElement:
                        title = linkElement.text.strip()
                        href = linkElement.get('href')
                        
                        if href and ('bursary' in href or 'scholarship' in href):
                            print(f"[{processedCount+1}/{min(maxBursaries, totalItems)}] {title[:60]}...")
                            deadline = getBursaryDetails(href)
                            
                            bursaryList.append({
                                "Bursary Name": title,
                                "Closing Date": deadline, 
                                "Link": href,
                                "Date Scraped": datetime.now().strftime("%Y-%m-%d")
                            })
                            
                            processedCount += 1
                
                print(f"\nDone - scraped {len(bursaryList)} bursaries")
            else:
                print("Error: Couldn't find the content div")
        else:
            print(f"Error: Server returned status {page.status_code}")

    except requests.exceptions.Timeout:
        print(f"Connection timeout - server took too long")
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

    return bursaryList

def saveToExcel(data, filename="bursaries.xlsx"):
    """
    Saves everything to an Excel file
    """
    if not data:
        print("Warning: No data to save")
        return
        
    df = pd.DataFrame(data)
    # make sure columns are in the right order
    df = df[["Bursary Name", "Closing Date", "Link", "Date Scraped"]]
    df.to_excel(filename, index=False)
    print(f"Saved {len(data)} bursaries to {filename}")

def sendEmail(filename):
    """
    Emails the Excel file to myself
    """
    emailSender = os.environ.get('EMAIL_USER')
    emailPassword = os.environ.get('EMAIL_PASS')
    
    if not emailSender or not emailPassword:
        print("Skipping email - no credentials set (this is fine for local testing)")
        return

    emailReceiver = emailSender
    subject = f"Bursary Report (With Deadlines) - {datetime.now().strftime('%Y-%m-%d')}"
    body = """Here's the latest bursary list with closing dates.

Note: Only showing first 20 to keep things fast and reliable.
Check the full list at: https://www.zabursaries.co.za/computer-science-it-bursaries-south-africa/
"""

    msg = MIMEMultipart()
    msg['From'] = emailSender
    msg['To'] = emailReceiver
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        # attach the excel file
        with open(filename, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={filename}")
        msg.attach(part)
        
        # actually send it
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(emailSender, emailPassword)
        server.sendmail(emailSender, emailReceiver, msg.as_string())
        server.quit()
        print("Email sent successfully")

    except smtplib.SMTPAuthenticationError:
        print("Email auth failed - check your app password")
    except smtplib.SMTPException as e:
        print(f"SMTP error: {e}")
    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == "__main__":
    print("\n" + "="*70)
    print("BURSARY SCRAPER - Starting...")
    print("="*70 + "\n")
    
    startTime = time.time()
    
    # only doing first 20 so this doesn't timeout
    results = getBursaryLinks(URL, maxBursaries=20)
    
    endTime = time.time()
    duration = endTime - startTime
    
    if results:
        excelFilename = "bursaries.xlsx"
        saveToExcel(results, excelFilename)
        sendEmail(excelFilename)
        
        print("\n" + "="*70)
        print(f"COMPLETE - Got {len(results)} bursaries in {duration:.1f} seconds")
        print("Check your email!")
        print("="*70 + "\n")
    else:
        print("\n" + "="*70)
        print("No bursaries found this time")
        print(f"Runtime: {duration:.1f} seconds")
        print("="*70 + "\n")
