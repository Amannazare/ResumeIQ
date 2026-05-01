# ResumeIQ — AI Resume Analyser (Python Edition)

An AI-powered resume analyser built with **Python + Flask**, using Google Gemini AI
to score your resume, identify skill gaps, and give actionable improvement tips.

---

## Tech Stack

| Layer    | Technology                          |
|----------|-------------------------------------|
| Backend  | Python 3.10+ · Flask                |
| Frontend | Vanilla HTML / CSS / JavaScript     |
| AI       | Google Gemini 1.5 Flash (free tier) |
| PDF      | pdfplumber                          |

---

## Project Structure

```
resume_analyser/
├── app.py              ← Flask server (all backend logic lives here)
├── requirements.txt    ← Python dependencies
├── .env.example        ← Template for your API key
├── .env                ← Your actual secrets (never commit this!)
└── templates/
    └── index.html      ← Full frontend (HTML + CSS + JS in one file)
```

---

## Quick Start

### Step 1 — Get a FREE Gemini API Key

1. Go to https://aistudio.google.com/apikey
2. Sign in with Google
3. Click **Create API Key** — copy it (looks like `AIzaSy...`)

### Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 3 — Set up your API key

```bash
cp .env.example .env
```

Open `.env` and replace the placeholder:

```
GEMINI_API_KEY=AIzaSyYourActualKeyHere
PORT=5000
```

### Step 4 — Run the server

```bash
python app.py
```

Then open your browser at **http://localhost:5000** ✅

---

## How it works (for your presentation)

1. User pastes or uploads their resume → browser sends it to `/api/parse-file`
2. Flask uses **pdfplumber** to extract text from the PDF
3. User clicks "Analyse" → browser sends text to `/api/analyze`
4. Flask builds a structured prompt and sends it to **Gemini 1.5 Flash**
5. Gemini returns a JSON object with scores, skills, suggestions
6. The frontend renders everything — score ring, bar charts, skill tags

---

## Environment Variables

| Variable        | Required | Description                  |
|-----------------|----------|------------------------------|
| `GEMINI_API_KEY`| ✅ Yes   | From aistudio.google.com     |
| `PORT`          | Optional | Defaults to 5000             |
