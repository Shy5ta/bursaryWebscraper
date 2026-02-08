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
    Find the 'Closing Date' by scanning all text on the page.
    Includes timeout protection to prevent hanging.
    """
    try:
        # Rate limiting
        time.sleep(0.5)
        
        #5 second timeout to prevent hanging
        page = requests.get(bursaryUrl, headers=HEADERS, timeout=5)
        
        if page.status_code != 200:
            print(f"Status {page.status_code}")
            return "Check Link"

        soup = BeautifulSoup(page.content, 'html.parser')
        
        contentDiv = soup.find('div', class_='entry-content')
        if not contentDiv:
            return "Not Found"

        # Scan line by line for closing date
        pageText = contentDiv.get_text(separator="\n").split("\n")
        
        dateKeywords = ["Closing Date", "Deadline", "Applications close", "Close date", "Closing date"]
        
        for i, line in enumerate(pageText):
            cleanLine = line.strip()
            
            if not cleanLine:
                continue
                
            # Check if any keyword is in this line 
            for keyword in dateKeywords:
                if keyword.lower() in cleanLine.lower():
                    # Extract date from same line
                    lowerLine = cleanLine.lower()
                    startIndex = lowerLine.find(keyword.lower()) + len(keyword)
                    finalDate = cleanLine[startIndex:].replace(":", "").strip()
                    
                    # If date is too short, it might be on the next line
                    if len(finalDate) < 3 and i + 1 < len(pageText):
                        finalDate = pageText[i + 1].strip()
                    
                    if len(finalDate) > 2:
                        return finalDate
                    
        return "Open / Unspecified"
        
    except requests.exceptions.Timeout:
        print(f"Timeout (5s exceeded)")
        return "Timeout - Check Manually"
    except requests.exceptions.RequestException as e:
        print(f"Request error: {str(e)[:50]}")
        return "Error"
    except Exception as e:
        print(f"Unexpected error: {str(e)[:50]}")
        return "Error"

def getBursaryLinks(targetUrl, maxBursaries=20):
    """
    Scrapes bursary listings with a maximum limit to prevent timeouts.
    Default: processes first 20 bursaries.
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
                print(f"Found {totalItems} potential links on page")
                print(f"Processing up to {maxBursaries} bursaries to avoid timeout...\n")
                
                processedCount = 0
                
                for index, item in enumerate(listItems, 1):
                    # STOP after maxBursaries to prevent timeout
                    if processedCount >= maxBursaries:
                        print(f"\n Stopped at {maxBursaries} bursaries (timeout protection)")
                        break
                    
                    linkElement = item.find('a')
                    
                    if linkElement:
                        title = linkElement.text.strip()
                        href = linkElement.get('href')
                        
                        # Filter for bursary links
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
                
                print(f"\nSuccessfully scraped {len(bursaryList)} bursaries")
            else:
                print(" Error: The 'entry-content' div was not found.")
        else:
            print(f" Error: The server returned status code {page.status_code}")

    except requests.exceptions.Timeout:
        print(f"Connection timeout - server took too long to respond")
    except requests.exceptions.RequestException as e:
        print(f" Network error: {e}")
    except Exception as e:
        print(f" Unexpected error: {e}")

    return bursaryList

def saveToExcel(data, filename="bursaries.xlsx"):
    """
    Saves the data to an Excel file with consistent column ordering.
    """
    if not data:
        print(" No data to save")
        return
        
    df = pd.DataFrame(data)
    df = df[["Bursary Name", "Closing Date", "Link", "Date Scraped"]]
    df.to_excel(filename, index=False)
    print(f" Success: {len(data)} bursaries saved to {filename}")

def sendEmail(filename):
    """
    Sends the Excel file via email.
    """
    emailSender = os.environ.get('EMAIL_USER')
    emailPassword = os.environ.get('EMAIL_PASS')
    
    if not emailSender or not emailPassword:
        print(" Skipping email: EMAIL_USER or EMAIL_PASS not set")
        print("  (local testing procedure)")
        return

    emailReceiver = emailSender
    subject = f"Bursary Report (With Deadlines) - {datetime.now().strftime('%Y-%m-%d')}"
    body = """Please find attached the latest list of bursaries including closing dates.

Note: This report includes the first 20 bursaries to ensure reliable delivery.
If you need more, check the full list at: https://www.zabursaries.co.za/computer-science-it-bursaries-south-africa/
"""

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
        print("Success: Email sent successfully.")

    except smtplib.SMTPAuthenticationError:
        print("Email authentication failed - check your EMAIL_PASS (App Password)")
    except smtplib.SMTPException as e:
        print(f" SMTP error: {e}")
    except Exception as e:
        print(f" Error sending email: {e}")

if __name__ == "__main__":
    print("\n" + "="*70)
    print(" "*15 + "BURSARY SCRAPER - Starting...")
    print("="*70 + "\n")
    
    startTime = time.time()
    
    # Process only first 20 bursaries to stay under 5 minutes because previous code was 28+ min
    # This ensures reliable execution in GitHub Actions
    results = getBursaryLinks(URL, maxBursaries=20)
    
    endTime = time.time()
    duration = endTime - startTime
    
    if results:
        excelFilename = "bursaries.xlsx"
        saveToExcel(results, excelFilename)
        sendEmail(excelFilename)
        
        print("\n" + "="*70)
        print(f" COMPLETE - Processed {len(results)} bursaries in {duration:.1f} seconds")
        print("   Check your email for the report!")
        print("="*70 + "\n")
    else:
        print("\n" + "="*70)
        print(" No bursaries were found during this run.")
        print(f"   Runtime: {duration:.1f} seconds")
        print("="*70 + "\n")
