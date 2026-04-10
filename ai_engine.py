import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

def get_current_resume():
    """PDF-la irunthu extract panni save panna text-a edukurom"""
    try:
        with open("current_resume.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Python Full Stack Developer with experience in React and FastAPI."

def evaluate_job_match(job_title, job_description):
    print(f"🧠 AI is analyzing match for: {job_title}...")
    
    resume_content = get_current_resume()
    
    # Updated Prompt with STRICT Location Logic
    prompt = f"""
    You are an expert Technical Recruiter. Your task is to match a Resume with a Job Description.

    CRITICAL LOCATION FILTER:
    - User Location: India.
    - Check if the job description EXPLICITLY restricts the role to specific countries like "US Only", "Canada Only", "Europe Only", or "Western Europe Only".
    - If the job is restricted to those regions and NOT open to candidates from India/Global, you MUST set the "match_percentage" to 0.

    Resume Content:
    {resume_content}

    Job Title: {job_title}
    
    Job Description:
    {job_description}

    Strictly return the result in this JSON format:
    {{
        "match_percentage": <number>,
        "missing_skills": ["skill1", "skill2"],
        "recommendation": "Short advice for the candidate"
    }}
    """

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
        )

        result = chat_completion.choices[0].message.content
        return json.loads(result)
    except Exception as e:
        print(f"❌ AI Engine Error: {e}")
        return {
            "match_percentage": 0,
            "missing_skills": ["Error processing AI"],
            "recommendation": "Check backend logs."
        }

if __name__ == "__main__":
    test_title = "DevOps Engineer - US Only"
    test_jd = "MUST BE LOCATED IN THE US. Strong Python skills required."
    print(evaluate_job_match(test_title, test_jd))