Bursary Scraper and Email Bot

A Python program I wrote to help me find Computer Science bursaries online. This is a simple Python script that visits the ZA Bursaries website and finds all the Computer Science bursaries listed there. Instead of having to search through the website manually, this program does it for me in a few seconds and emails them to me as an Excel spreadsheet every month. 

What I used:
  Python 3.9
  Pandas
  BeautifulSoup4
  GitHub Actions

How to run it locally:
  1. Clone the repo
     git clone (https://github.com/Shy5ta/bursarywebscraper.git)


  2. Install the requirements
     pip install -r requirements.txt

  3. Set up your email (Environment Variables)
      Set "EMAIL_USER" (your Gmail address) and "EMAIL_PASS" (your Gmail App Password - NOT your regular password).
      To create an App Password: https://support.google.com/accounts/answer/185833

  4. Run the script
     python scraper.py

What I learnt:
  Web scraping- How to use BeautifulSoup to parse HTML and extract specific data from websites
  
  APIs and libraries- Integrating Python libraries (requests, pandas)
  
  Automation with GitHub Actions- Setting up scheduled workflows to run code automatically
  
  Email protocols- Understanding SMTP and how to send emails with attachments
