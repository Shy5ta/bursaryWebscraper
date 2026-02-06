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

URL = "https://www.zabursaries.co.za/computer-science-it-bursaries-south-africa/"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def getBursaryLinks(targetUrl):
    """
    Fetches the page and extracts relevant bursary links.
    """
    bursaryList = []

    try:
        page = requests.get(targetUrl, headers=HEADERS)

        if page.status_code == 200:
            soup = BeautifulSoup(page.content, 'html.parser')
            contentArea = soup.find('div', class_='entry-content')
            
            if contentArea:
                listItems = contentArea.find_all('li')
                
                for item in listItems:
                    linkElement = item.find('a')
                    
                    if linkElement:
                        title = linkElement.text.strip()
                        href = linkElement.get('href')
                        
                        # Filter for bursary links
                        if href and ('bursary' in href or 'scholarship' in href):
                            currentDate = datetime.now().strftime("%Y-%m-%d")
                            bursaryList.append({
                                "Bursary Name": title,
                                "Link": href,
                                "Date Scraped": currentDate
                            })
            else:
                print("Error: The 'entry-content' div was not found.")
        else:
            print(f"Error: The server returned status code {page.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

    return bursaryList

def saveToExcel(data, filename="bursaries.xlsx"):
    """
    Saves the data to a real Excel file.
    """
    df = pd.DataFrame(data)

    df.to_excel(filename, index=False)
    
    print(f"Success: {len(data)} bursaries saved to {filename}")

def sendEmail(filename):
    """
    Sends the Excel file via email.
    """
    emailSender = os.environ.get('EMAIL_USER')
    emailPassword = os.environ.get('EMAIL_PASS')
    emailReceiver = emailSender 

    if not emailSender or not emailPassword:
        print("Error: Email credentials not found.")
        return

    subject = f"Monthly Bursary Excel Report - {datetime.now().strftime('%Y-%m-%d')}"
    body = "Please find attached the latest list of bursaries in Excel format."

    msg = MIMEMultipart()
    msg['From'] = emailSender
    msg['To'] = emailReceiver
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # Attach the Excel file
    try:
        with open(filename, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {filename}",
        )
        msg.attach(part)
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(emailSender, emailPassword)
        text = msg.as_string()
        server.sendmail(emailSender, emailReceiver, text)
        server.quit()
        print("Success: Email sent successfully.")

    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == "__main__":
    print("Starting scraper...")
    results = getBursaryLinks(URL)
    
    if results:
        excelFilename = "bursaries.xlsx"
        saveToExcel(results, excelFilename)
        sendEmail(excelFilename)
    else:
        print("No bursaries were found during this run.")