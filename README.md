Web Scraper for Finding Bursaries

A Python program I wrote to help me find Computer Science bursaries online. This is a simple Python script that visits the ZA Bursaries website and finds all the Computer Science bursaries listed there. Instead of having to search through the website manually, this program does it for me in a few seconds. 

What I used:
- Python 3
- requests library (to get the webpage)
- BeautifulSoup library (to read the webpage)

How to run it: 
First install the libraries pip install requests beautifulsoup4. Then run the program.

What I learned
--------------
I built this because I was looking for bursaries and found it took too much time to check websites regularly. Here's what I learned while making it:

1. I learned that when you visit a website, your browser downloads HTML code. This program does the same thing.

2. Websites are built with HTML that has a structure. I learned how to find the specific parts I needed (the bursary links).

3. I learned how to make Python act like a browser to get webpages.

4. Sometimes websites don't load properly. I learned how to handle those errors so the program doesn't crash.


At first, the website blocked my program because it could tell it wasn't a real browser. I fixed this by adding a "User-Agent" header. Finding the exact part of the webpage with the bursaries was tricky. I had to look at the HTML structure carefully. Some links weren't actually bursaries. I added a check to only show links with "bursary" or "scholarship" in them.

