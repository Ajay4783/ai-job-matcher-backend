from fastapi import FastAPI, Depends, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError 
import requests
import shutil
import os
import json
from bs4 import BeautifulSoup
from pypdf import PdfReader
from typing import Optional

from scraper import get_job_description
from ai_engine import evaluate_job_match
from database import SessionLocal, Job
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def home():
    return {"message": "AI Job Matcher API is Running! 🚀"}

@app.post("/api/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    reader = PdfReader(file_path)
    resume_text = ""
    for page in reader.pages:
        resume_text += page.extract_text()
    
    with open("current_resume.txt", "w", encoding="utf-8") as f:
        f.write(resume_text)
        
    return {"message": "Resume uploaded successfully!", "filename": file.filename}

# Unga API Key Theliva Inga Irukku
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")

@app.get("/api/scan-jobs")
def scan_jobs(
    source: Optional[str] = "all", 
    job_title: Optional[str] = "Python Developer", # Default Job Title
    location: Optional[str] = "India",             # Default Location
    experience: Optional[str] = "",                # under_3_years_experience, etc.
    job_type: Optional[str] = "",                  # FULLTIME, CONTRACTOR, etc.
    db: Session = Depends(get_db)
):
    print(f"🚀 Real API Scan Started: {source.upper()} | Role: {job_title} | Loc: {location}")
    
    senior_keywords = ["senior", "lead", "principal", "manager", "sr", "director", "head", "architect", "staff"]
    
    # 1. Python.org (Real Scraper)
    if source in ["all", "python"]:
        try:
            res = requests.get("https://www.python.org/jobs/", timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            job_list = soup.find('ol', class_='list-recent-jobs')
            
            if job_list:
                for li in job_list.find_all('li')[:10]: # Increased to 10
                    title = li.find('h2').find('a').text.strip()
                    link = "https://www.python.org" + li.find('h2').find('a')['href']
                    
                    if not any(k in title.lower() for k in senior_keywords):
                        if not db.query(Job).filter(Job.link == link).first():
                            company = li.find('span', class_='listing-company-name').text.strip().split('\n')[-1].strip()
                            desc = get_job_description(link)
                            
                            try:
                                ai = evaluate_job_match(title, desc)
                                db.add(Job(title=title, company=company, link=link, score=ai.get("match_percentage", 0), missing_skills=json.dumps(ai.get("missing_skills", [])), recommendation=ai.get("recommendation", ""), status="Pending"))
                                db.commit()
                            except IntegrityError: db.rollback()
                            except Exception as e: print(f"AI Error on Python.org: {e}")
        except Exception as e:
            print("Python.org Scrape Error:", e)

    # 2. THE REAL JOBS API (JSearch via RapidAPI)
    if source in ["all", "naukri", "indeed", "linkedin"]:
        print(f"🌐 Calling RapidAPI (JSearch) for: {source.upper()}")
        
        # SEARCH QUERY LOGIC:
        # User title & location vachu theduroam. 
        # Source 'all' illana mattum, 'site:portal.com' sethu strict-ah theduroam.
        search_query = f"{job_title} in {location}"
        
        if source == "naukri":
            search_query += " site:naukri.com"
        elif source == "indeed":
            search_query += " site:indeed.com"
        elif source == "linkedin":
            search_query += " site:linkedin.com"
        # 'all' ah iruntha specific site thara vendam, Google Jobs-ey ellathaiyum eduthu varum.

        url = "https://jsearch.p.rapidapi.com/search"
        querystring = {
            "query": search_query, 
            "page": "1", 
            "num_pages": "3", 
            "date_posted": "today" 
        }
        
        # Other filters (Employment types, etc.)
        if job_type:
            querystring["employment_types"] = job_type
        if experience:
            querystring["job_requirements"] = experience
            
        headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }
        
        try:
            api_res = requests.get(url, headers=headers, params=querystring, timeout=30)
            data = api_res.json()
            jobs_results = data.get("data", []) 
            
            print(f"✅ API returned {len(jobs_results)} jobs for {source}")

            for job in jobs_results[:30]:
                title = job.get("job_title", "Python Developer")
                company = job.get("employer_name", "Unknown Company")
                desc = job.get("job_description", "")
                
                # Senior keywords filter
                if not any(k in title.lower() for k in senior_keywords):
                    link = job.get("job_apply_link") 
                    if not link: link = job.get("job_google_link", "https://google.com")
                    
                    # Database-la check panni add panroam
                    if not db.query(Job).filter(Job.link == link).first():
                        try:
                            ai = evaluate_job_match(title, desc)
                            db.add(Job(title=title, company=company, link=link, 
                                       score=ai.get("match_percentage", 0), 
                                       missing_skills=json.dumps(ai.get("missing_skills", [])), 
                                       recommendation=ai.get("recommendation", ""), 
                                       status="Pending"))
                            db.commit()
                        except Exception as ai_e:
                            db.rollback()
                            print(f"AI Match Error: {ai_e}")
        except Exception as e:
            print(f"RapidAPI Error for {source}: {e}")

    # Database Filter & Sort
    if source == "all":
        all_jobs = db.query(Job).order_by(Job.score.desc()).all()
    else:
        all_jobs = db.query(Job).filter(Job.link.contains(source)).order_by(Job.score.desc()).all()

    for j in all_jobs:
        if isinstance(j.missing_skills, str): 
            j.missing_skills = json.loads(j.missing_skills)
            
    return {"jobs": all_jobs}


@app.patch("/api/jobs/{job_id}")
def update_job_status(job_id: int, status_update: dict, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if job:
        job.status = status_update.get("status")
        db.commit()
        return {"message": "Success", "job": job}
    return {"error": "Not found"}, 404

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)