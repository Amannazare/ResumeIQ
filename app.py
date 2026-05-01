"""
Resume Analyser - Backend Server
=================================
This is the main server file. It handles three things:
  1. Serving the HTML page to the user's browser
  2. Extracting text from uploaded PDF or TXT files
  3. Sending that text to Google Gemini AI for analysis

We're using Flask (a lightweight Python web framework) because it's
easy to understand and well-documented. Think of Flask as a traffic
controller - it listens for requests and sends back the right response.

To run this:
    pip install -r requirements.txt
    python app.py
"""

import os
import json
import io

from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from google import genai
import pdfplumber


# ─────────────────────────────────────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────────────────────────────────────

# Load environment variables from our .env file (where we store the API key).
# This keeps secrets out of the source code — a basic security best practice.
load_dotenv(override=True)

# Create the Flask app. __name__ tells Flask where to look for templates/static files.
app = Flask(__name__)

# Cap uploaded files at 10 MB to prevent abuse or accidental giant uploads.
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB in bytes

# Read the Gemini API key from environment. If it's missing, we warn the user
# immediately rather than failing silently later at analysis time.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY not found in .env — analysis will fail.")

# Configure the Gemini client with our API key.
#genai.configure(api_key=GEMINI_API_KEY)


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Extract text from uploaded file
# ─────────────────────────────────────────────────────────────────────────────

def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """
    Pull plain text out of a PDF or TXT file.

    Why pdfplumber?
    ---------------
    pdfplumber is one of the most reliable Python PDF libraries for
    extracting readable text from a wide range of PDF styles. Unlike
    PyPDF2 (which can mangle spacing), pdfplumber preserves layout
    much better, giving Gemini cleaner input to work with.

    Args:
        file_bytes : raw bytes of the uploaded file
        filename   : original filename (used to decide how to parse it)

    Returns:
        A plain-text string with the resume content.
    """
    filename_lower = filename.lower()

    if filename_lower.endswith(".pdf"):
        # Wrap the bytes in a BytesIO stream so pdfplumber can treat it
        # like a regular file — no need to save to disk.
        pdf_stream = io.BytesIO(file_bytes)
        extracted_pages = []

        with pdfplumber.open(pdf_stream) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:  # Some pages (e.g. scanned images) return None
                    extracted_pages.append(page_text)

        return "\n".join(extracted_pages)

    elif filename_lower.endswith(".txt"):
        # TXT files are just raw text — decode bytes to a Python string.
        # We try UTF-8 first (standard), fall back to latin-1 for older files.
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return file_bytes.decode("latin-1")

    else:
        raise ValueError("Unsupported file type. Please upload a PDF or TXT file.")


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Build the Gemini prompt
# ─────────────────────────────────────────────────────────────────────────────

def build_analysis_prompt(resume_text: str, job_description: str) -> str:
    """
    Construct the instruction we send to Gemini.

    Prompt engineering is surprisingly important — small changes in how
    you phrase the instruction can significantly affect output quality.
    Here we:
      - Tell the model exactly what role to play ("expert resume analyst")
      - Give it the resume (and optionally a job description)
      - Demand a strict JSON structure so we can parse the result reliably
      - Ask for ONLY JSON — no preamble or markdown fences

    Args:
        resume_text     : the candidate's resume as plain text
        job_description : optional job posting text (empty string if not given)

    Returns:
        A ready-to-send prompt string.
    """

    # Trim inputs to stay within Gemini's context window limits.
    # The free tier has generous limits, but we cap anyway to keep costs low.
    trimmed_resume = resume_text[:5000]
    trimmed_jd = job_description[:2000] if job_description else ""

    # Decide whether this is a general review or a job-specific match.
    if trimmed_jd:
        jd_section = f"""
Job Description / Target Role:
\"\"\"
{trimmed_jd}
\"\"\"
"""
        analysis_instruction = "Analyze the resume against the job description above."
    else:
        jd_section = ""
        analysis_instruction = "No job description provided — do a general resume quality analysis."

    prompt = f"""
You are an expert resume analyst and career coach with 15 years of experience
in technical recruitment. {analysis_instruction}

Resume:
\"\"\"
{trimmed_resume}
\"\"\"
{jd_section}

Return ONLY valid JSON — no markdown, no explanation, no extra text.
The JSON must follow this exact structure:

{{
  "overallScore": <integer 0-100>,
  "grade": "<Excellent | Good | Fair | Needs Work>",
  "summary": "<2-3 sentence plain-English summary of resume quality and job fit>",
  "breakdown": {{
    "skillsMatch": <integer 0-100>,
    "experienceDepth": <integer 0-100>,
    "keywordsOptimization": <integer 0-100>,
    "formatting": <integer 0-100>,
    "atsCompatibility": <integer 0-100>
  }},
  "extractedInfo": {{
    "name": "<candidate name, or Unknown>",
    "currentRole": "<most recent or target job title>",
    "yearsExperience": "<e.g. 3-5 years>",
    "topSkills": ["skill1", "skill2", "skill3", "skill4", "skill5"]
  }},
  "skillsFound": ["skill1", "skill2", "skill3", "skill4", "skill5", "skill6"],
  "skillsMissing": ["skill1", "skill2", "skill3", "skill4", "skill5"],
  "suggestions": [
    {{"priority": "critical",  "text": "<specific actionable suggestion>"}},
    {{"priority": "critical",  "text": "<specific actionable suggestion>"}},
    {{"priority": "important", "text": "<specific actionable suggestion>"}},
    {{"priority": "important", "text": "<specific actionable suggestion>"}},
    {{"priority": "nice",      "text": "<specific actionable suggestion>"}},
    {{"priority": "nice",      "text": "<specific actionable suggestion>"}}
  ]
}}
""".strip()

    return prompt


# ─────────────────────────────────────────────────────────────────────────────
# Route 1 — Serve the main page
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """
    Serve the main HTML page.

    Flask's render_template() looks inside the /templates folder for index.html
    and returns it as a complete HTTP response with the correct content type.
    """
    return render_template("index.html")


# ─────────────────────────────────────────────────────────────────────────────
# Route 2 — Parse uploaded PDF or TXT file
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/parse-file", methods=["POST"])
def parse_file():
    """
    Receive an uploaded file, extract its text, and return it as JSON.

    The frontend sends a multipart/form-data POST request with the file
    attached under the key "resume". We read the raw bytes from memory
    (never saving to disk — safer and faster), extract text, and send
    back the first 8,000 characters. That's enough for any normal resume.
    """

    # Check that a file was actually included in the request.
    if "resume" not in request.files:
        return jsonify({"error": "No file was uploaded. Please attach a file."}), 400

    uploaded_file = request.files["resume"]

    # An empty filename means the user submitted without selecting a file.
    if uploaded_file.filename == "":
        return jsonify({"error": "The uploaded file has no name."}), 400

    try:
        # Read the entire file into memory as bytes.
        file_bytes = uploaded_file.read()

        # Use our helper to pull out plain text.
        raw_text = extract_text_from_file(file_bytes, uploaded_file.filename)

        # Cap at 8,000 characters — more than enough for even a 3-page resume.
        return jsonify({"text": raw_text[:8000]})

    except ValueError as e:
        # Known errors (e.g. unsupported file type) — tell the user clearly.
        return jsonify({"error": str(e)}), 400

    except Exception as e:
        # Unexpected errors — log for debugging, return a generic message.
        print(f"[parse-file] Unexpected error: {e}")
        return jsonify({"error": "Failed to extract text from the file. Please try pasting your resume instead."}), 500


# ─────────────────────────────────────────────────────────────────────────────
# Route 3 — Analyse resume using Gemini AI
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/analyze", methods=["POST"])
def analyze_resume():
    """
    Send resume text (and optionally a job description) to Gemini for analysis.

    Flow:
      1. Validate inputs
      2. Build a structured prompt
      3. Call Gemini API
      4. Parse the JSON response
      5. Return the structured result to the frontend

    We use gemini-1.5-flash because it's:
      - Free tier friendly (1,500 requests/day at no cost)
      - Fast enough for real-time web use (usually < 5 seconds)
      - Smart enough for resume analysis tasks
    """

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400

    resume_text = data.get("resumeText", "").strip()
    job_description = data.get("jobDesc", "").strip()

    # Basic validation — a resume shorter than 50 chars is clearly not real content.
    if len(resume_text) < 50:
        return jsonify({"error": "Resume text is too short. Please provide more content."}), 400

    try:
        # Build the prompt using our helper function.
        prompt = build_analysis_prompt(resume_text, job_description)

        # Initialise the Gemini model.
        # gemini-1.5-flash is the free, fast model — perfect for this use cas

        client = genai.Client(api_key=GEMINI_API_KEY)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        # Send the prompt and wait for the response.
        # generate_content() is a blocking call — it waits until Gemini is done.

        # Extract the raw text from the response object.
        raw_text = response.text.strip()

        # Gemini sometimes wraps its output in markdown code fences like ```json ... ```
        # even when told not to. We strip those fences to get clean JSON.
        clean_text = (
            raw_text
            .removeprefix("```json").removeprefix("```")  # strip opening fence
            .removesuffix("```")                           # strip closing fence
            .strip()
        )

        # Parse the JSON string into a Python dictionary.
        # If parsing fails, it means Gemini returned something unexpected.
        result = json.loads(clean_text)

        return jsonify(result)

    except json.JSONDecodeError as e:
        # The AI didn't return valid JSON — log the raw output to help debug.
        print(f"[analyze] JSON parse error: {e}")
        print(f"[analyze] Raw Gemini output: {raw_text[:500]}")
        return jsonify({"error": "AI returned an unexpected format. Please try again."}), 500

    except Exception as e:
        print(f"[analyze] Unexpected error: {e}")
        return jsonify({"error": str(e) or "Analysis failed. Please try again."}), 500


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Read port from environment (useful for deployment), default to 5000.
    port = int(os.getenv("PORT", 5000))

    # debug=True enables:
    #   - Auto-reload when you save a file (huge during development)
    #   - Detailed error pages in the browser
    # Never use debug=True in production!
    app.run(debug=True, port=port)
