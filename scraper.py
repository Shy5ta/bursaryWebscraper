"""
Bursary Web Scraper
Automated system that finds Computer Science bursaries
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
    Find the 'Closing Date' by scanning all text on the page.
    """
    try:
        # Pausing not to overload server
        time.sleep(0.5)
        
        page = requests.get(bursaryUrl, headers=HEADERS)
        if page.status_code != 200:
            return "Check Link"

        soup = BeautifulSoup(page.content, 'html.parser')
        
        contentDiv = soup.find('div', class_='entry-content')
        if not contentDiv:
            return "Not Found"

        # --- NEW LOGIC: Scan line-by-line instead of tag-by-tag ---
        # separator="\n" ensures we don't merge text from different lines
        pageText = contentDiv.get_text(separator="\n").split("\n")
        
        dateKeywords = ["Closing Date", "Deadline", "Applications close"]
        
        for line in pageText:
            # Clean the line for checking
            cleanLine = line.strip()
            
            # Skip empty lines
            if not cleanLine:
                continue
                
            # Check if any keyword is in this line (Case Insensitive)
            for keyword in dateKeywords:
                if keyword.lower() in cleanLine.lower():
                    # Remove the keyword (e.g. "Closing Date:") to get just the date
                    # We use a case-insensitive replace logic here
                    lowerLine = cleanLine.lower()
                    startIndex = lowerLine.find(keyword.lower()) + len(keyword)
                    
                    finalDate = cleanLine[startIndex:].replace(":", "").strip()
                    
                    # If the line was just "Closing Date:", the date might be on the NEXT line.
                    # But usually, get_text combines them if they are in the same block.
                    if len(finalDate) > 2:
                        return finalDate
                    
        return "Open / Unspecified"
        
    except Exception as e:
        return "Error loading page"

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
                totalItems = len(listItems)
                print(f"Found {totalItems} potential links. Scraping details...")
                
                for index, item in enumerate(listItems):
                    linkElement = item.find('a')
                    
                    if linkElement:
                        title = linkElement.text.strip()
                        href = linkElement.get('href')
                        
                        # Filter for bursary links
                        if href and ('bursary' in href or 'scholarship' in href):
                            # Get the deadline 
                            print(f"[{index+1}/{totalItems}] Fetching details for: {title}")
                            deadline = getBursaryDetails(href)
                            
                            bursaryList.append({
                                "Bursary Name": title,
                                "Closing Date": deadline, 
                                "Link": href,
                                "Date Scraped": datetime.now().strftime("%Y-%m-%d")
                            })
            else:
                print("Error: The 'entry-content' div was not found.")
        else:
            print(f"Error: The server returned status code {page.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

    return bursaryList

def saveToExcel(data, filename="bursaries.xlsx"):
    df = pd.DataFrame(data)
    df = df[["Bursary Name", "Closing Date", "Link", "Date Scraped"]]
    df.to_excel(filename, index=False)
    print(f"Success: {len(data)} bursaries saved to {filename}")

def sendEmail(filename):
    emailSender = os.environ.get('EMAIL_USER')
    emailPassword = os.environ.get('EMAIL_PASS')
    
    if not emailSender:
        print("Skipping email: No environment variables set (EMAIL_USER/EMAIL_PASS)")
        return

    emailReceiver = emailSender
    subject = f"Bursary Report (With Deadlines) - {datetime.now().strftime('%Y-%m-%d')}"
    body = "Please find attached the latest list of bursaries including closing dates."

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
        part.add_header("Content-Disposition", f"attachment; filename= {filename}")
        msg.attach(part)
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(emailSender, emailPassword)
        server.sendmail(emailSender, emailReceiver, msg.as_string())
        server.quit()
        print("Success: Email sent successfully.")

    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == "__main__":
    results = getBursaryLinks(URL)
    
    if results:
        excelFilename = "bursaries.xlsx"
        saveToExcel(results, excelFilename)
        sendEmail(excelFilename)
    else:
        print("No bursaries were found.")
