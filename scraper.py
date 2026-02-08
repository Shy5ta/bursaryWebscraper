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
    try:
        time.sleep(0.5)
        
        page = requests.get(bursaryUrl, headers=HEADERS, timeout=5)
        
        if page.status_code != 200:
            print(f"  Warning: Got status {page.status_code}")
            return "Check Link"

        soup = BeautifulSoup(page.content, 'html.parser')
        
        contentDiv = soup.find('div', class_='entry-content')
        if not contentDiv:
            return "Not Found"

        Look for <strong> or <b> tags containing "Closing Date"
        # then grab the text right after it
        strongTags = contentDiv.find_all(['strong', 'b'])
        for tag in strongTags:
            tagText = tag.get_text().strip()
            if 'closing date' in tagText.lower() or 'deadline' in tagText.lower():
                # the date might be in the same tag after a colon
                if ':' in tagText:
                    datePart = tagText.split(':', 1)[1].strip()
                    if datePart and len(datePart) > 3:
                        return datePart
                
                # or it might be in the next sibling element
                nextElement = tag.next_sibling
                if nextElement:
                    dateText = nextElement.strip() if isinstance(nextElement, str) else nextElement.get_text().strip()
                    if dateText and len(dateText) > 3 and len(dateText) < 100:
                        # clean up common prefixes
                        dateText = dateText.lstrip(':').strip()
                        return dateText
                
                # or maybe in the parent's next sibling
                parent = tag.parent
                if parent and parent.next_sibling:
                    nextSib = parent.next_sibling
                    dateText = nextSib.strip() if isinstance(nextSib, str) else nextSib.get_text().strip()
                    if dateText and len(dateText) > 3 and len(dateText) < 100:
                        return dateText.lstrip(':').strip()
        
        # METHOD 2
        tables = contentDiv.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                for i, cell in enumerate(cells):
                    cellText = cell.get_text().strip()
                    if 'closing date' in cellText.lower() or 'deadline' in cellText.lower():
                        # date is probably in the next cell
                        if i + 1 < len(cells):
                            dateText = cells[i + 1].get_text().strip()
                            if dateText and len(dateText) > 3:
                                return dateText
        
        # Look for paragraph with "Closing Date:" and grab what's after
        paragraphs = contentDiv.find_all('p')
        for para in paragraphs:
            paraText = para.get_text()
            if 'closing date' in paraText.lower() or 'deadline' in paraText.lower():
                # try to extract just the date part
                match = re.search(r'(?:closing date|deadline)\s*:?\s*([^\n\.]+)', paraText, re.IGNORECASE)
                if match:
                    dateText = match.group(1).strip()
                    if len(dateText) > 3 and len(dateText) < 100:
                        return dateText
        
        # Look in list items
        listItems = contentDiv.find_all('li')
        for li in listItems:
            liText = li.get_text()
            if 'closing date' in liText.lower() or 'deadline' in liText.lower():
                match = re.search(r'(?:closing date|deadline)\s*:?\s*([^\n]+)', liText, re.IGNORECASE)
                if match:
                    dateText = match.group(1).strip()
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
