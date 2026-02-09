Bursary Scraper and Email Bot

A Python program to help South African students find Computer Science bursaries online. This script automatically visits the ZA Bursaries website, finds all Computer Science bursaries listed there, filters them by recency, and emails the results as an Excel spreadsheet every month. Instead of manually searching through hundreds of listings, this program does it in seconds.

What it does:
  Scrapes Computer Science bursaries from zabursaries.co.za
  Filters for bursaries updated in the last 6 months (removes outdated listings)
  Exports results to an Excel spreadsheet
  Automatically emails the spreadsheet to you
  Runs monthly via GitHub Actions (completely automated and free)

Tech stack:
  Python 3.9
  BeautifulSoup4 for web scraping
  Pandas for data processing
  GitHub Actions for automation
  SMTP for email delivery

How to use it:

  Option 1: Automated monthly emails (recommended)
    1. Fork this repository
    2. Go to Settings > Secrets and variables > Actions
    3. Add two secrets:
       EMAIL_USER: your Gmail address
       EMAIL_PASS: your Gmail App Password (get it here: https://support.google.com/accounts/answer/185833)
    4. GitHub Actions will automatically run on the 1st of each month and email you the results

  Option 2: Run locally
    1. Clone the repo
       git clone https://github.com/Shy5ta/bursarywebscraper.git
       cd bursarywebscraper

    2. Install the requirements
       pip install -r requirements.txt

    3. Set up your email credentials as environment variables
       Linux/Mac:
         export EMAIL_USER="your-email@gmail.com"
         export EMAIL_PASS="your-app-password"
       
       Windows (Command Prompt):
         set EMAIL_USER=your-email@gmail.com
         set EMAIL_PASS=your-app-password
       
       Windows (PowerShell):
         $env:EMAIL_USER="your-email@gmail.com"
         $env:EMAIL_PASS="your-app-password"

    4. Run the script
       python scraper.py

    You'll receive an Excel file with all bursaries updated in the last 6 months.

What I learned building this:

  Web scraping
    Using BeautifulSoup to parse HTML and extract specific data from websites
    Handling different HTML structures and dealing with inconsistent data
    Implementing rate limiting to be respectful of server resources

  Data processing
    Using Pandas to organize and manipulate scraped data
    Filtering and sorting data based on multiple criteria
    Exporting data to Excel format with proper formatting

  Automation
    Setting up GitHub Actions workflows to run code on a schedule
    Managing environment variables and secrets in CI/CD pipelines
    Understanding cron syntax for scheduling tasks

  Email protocols
    Understanding SMTP and how to send emails programmatically
    Attaching files to emails using MIME types
    Handling authentication with Gmail App Passwords

  Error handling
    Implementing logging to track script execution
    Handling network errors and timeouts
    Managing edge cases in web scraping (missing data, changed HTML structure)

Future plans:

I'm working on expanding this into a web platform where any South African student can search for bursaries by keyword (such as "Accounting", "Engineering", or "Data Science") without needing to set up GitHub Actions or understand code. The goal is to make bursary discovery accessible to everyone, not just developers.

Additional planned features include:
  Web interface with keyword search and filtering
  Support for multiple bursary categories beyond Computer Science
  Individual pages for each bursary (better for search engine optimization)
  Email subscription service where users can set their preferences
  Mobile-friendly design for students accessing on phones

If you're interested in collaborating or have suggestions, feel free to open an issue or submit a pull request.

Contributing:

Contributions are welcome. Some areas where help would be appreciated:
  Improving the scraping reliability
  Writing documentation
  Testing on different platforms
  Suggesting new features

Disclaimer:

This tool is for educational purposes to help students find funding opportunities. Data is scraped from publicly available sources. Always verify bursary details on official websites before applying. Not affiliated with zabursaries.co.za or any bursary providers.

Contact:

For questions or feedback, please open an issue on GitHub.
