import requests
from bs4 import BeautifulSoup
import json

def get_job_description(url):
    # Intha function antha link-kulla poyi JD-a edukkum
    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.text, 'html.parser')
        desc_div = soup.find('div', class_='job-description')
        if desc_div:
            # Full description venam, AI-kku anuppa oru 500 words mattum edukurom
            return desc_div.text.strip()[:500] + "... [Read More]"
        return "Description not found."
    except:
        return "Error loading description."

def scrape_python_jobs():
    print("🤖 Advanced AI Bot is fetching Job Descriptions...\n")
    url = "https://www.python.org/jobs/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    jobs = []
    job_list = soup.find('ol', class_='list-recent-jobs')
    
    # Top 2 jobs-a mattum ippo eduppom (Time save panna)
    for li in job_list.find_all('li')[:2]:
        title_element = li.find('h2').find('a')
        title = title_element.text.strip()
        link = "https://www.python.org" + title_element['href']
        
        # Bug Fix: "New" tag-a remove panrom
        company_raw = li.find('span', class_='listing-company-name').text.strip()
        company_name = company_raw.split('\n')[-1].strip() 
        
        # Puthu function-a call panni JD edukurom
        description = get_job_description(link)
        
        jobs.append({
            "Job Title": title,
            "Company": company_name,
            "Description Snippet": description,
            "Apply Link": link
        })
        
    print(json.dumps(jobs, indent=4))

if __name__ == "__main__":
    scrape_python_jobs()