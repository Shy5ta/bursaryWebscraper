import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# The target URL for the bursary list
URL = "https://www.zabursaries.co.za/computer-science-it-bursaries-south-africa/"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def getLinks(targetURL):
    """
    Fetches the page and extracts relevant bursary links.
    """
    bursaryList = []

    try:
        page = requests.get(targetURL, headers=HEADERS)

        if page.statusCode == 200:
            soup = BeautifulSoup(page.content, 'html.parser')
            contentArea = soup.find('div', class_='entry-content')
            
            if contentArea:
                list_items = contentArea.find_all('li')
                
                for item in list_items:
                    linkElement = item.find('a')
                    
                    if linkElement:
                        title = linkElement.text.strip()
                        href = linkElement.get('href')
                        
                        if href and ('bursary' in href or 'scholarship' in href):
                            currentDate = datetime.now().strftime("%Y-%m-%d")
                            bursaryList.append([title, href, currentDate])
            else:
                print("Error: The 'entry-content' div was not found.")
        else:
            print(f"Error: The server returned status code {page.statusCode}")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

    return bursaryList

def saveToCSV(data, filename="bursaries.csv"):
    """
    Writes the list of bursaries to a CSV file.
    """
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Bursary Name", "Link", "Date Scraped"])
        writer.writerows(data)
    
    print(f"Success: {len(data)} bursaries saved to {filename}")

def sendEmail(filename):
    """
    Sends the CSV file via email using credentials from environment variables.
    """
    # Credentials are retrieved from the environment for security
    emailSender = os.environ.get('EMAIL_USER')
    emailPassword = os.environ.get('EMAIL_PASS')
    emailReceiver = emailSender # Sending to yourself

    if not emailSender or not emailPassword:
        print("Error: Email credentials not found in environment variables.")
        return

    subject = f"Monthly Bursary Scraper Report - {datetime.now().strftime('%Y-%m-%d')}"
    body = "Please find attached the latest list of Computer Science bursaries in South Africa."

    # The email container is created
    msg = MIMEMultipart()
    msg['From'] = emailSender
    msg['To'] = emailReceiver
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        with open(filename, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        
        # The file is encoded to base64 for transmission
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {filename}",
        )

        msg.attach(part)
        
        # The connection to Gmail's SMTP server is established
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls() # The connection is upgraded to secure TLS
        server.login(emailSender, emailPassword)
        text = msg.as_string()
        server.sendmail(emailSender, emailReceiver, text)
        server.quit()

        print("Success: Email sent successfully.")

    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == "__main__":
    print("Starting scraper...")
    results = getLinks(URL)
    
    if results:
        csv_filename = "bursaries.csv"
        saveToCSV(results, csv_filename)
        
        #The email function is called after saving
        sendEmail(csv_filename)
    else:
        print("No bursaries were found during this run.")