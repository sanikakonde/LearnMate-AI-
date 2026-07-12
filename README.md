# LearnMate AI

A production-ready AI-powered personalized learning and career coaching platform built with Python Flask and IBM watsonx.ai Granite Foundation Models.

## Features

- **Agentic AI Learning Coach** – Understands your career goals and adapts recommendations
- **Personalized Roadmaps** – AI-generated learning paths tailored to your goals
- **AI Tutor** – Domain-aware chat powered by IBM Granite (technology topics only)
- **Skill Quizzes** – 5 AI-generated MCQs with explanations per session
- **Progress Tracker** – Track topics, milestones, and study time
- **Pomodoro Timer** – Built-in study timer with session logging
- **Project Recommendations** – AI-suggested projects for your career goal
- **Curated Resources** – Verified learning resources from IBM SkillsBuild, Coursera, etc.
- **Quiz History** – Complete quiz record with detailed reviews
- **Dark & Light Mode** – Premium glassmorphism UI

## Quick Start

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd learnmate-ai
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your IBM watsonx.ai credentials
```

### 3. Set IBM watsonx.ai credentials

In your `.env` file:
```
WATSONX_API_KEY=your-ibm-watsonx-api-key
WATSONX_PROJECT_ID=your-watsonx-project-id
WATSONX_URL=https://us-south.ml.cloud.ibm.com
SECRET_KEY=your-random-secret-key
```

Get your credentials from [IBM Cloud](https://cloud.ibm.com/):
1. Create an IBM Cloud account (Lite tier is free)
2. Create a watsonx.ai project
3. Generate an API key from IAM
4. Copy your Project ID from the watsonx.ai project settings

### 4. Run the application

```bash
python run.py
```

Visit `http://localhost:5000`

## Project Structure

```
learnmate-ai/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration classes
│   ├── extensions.py        # Flask extensions
│   ├── models.py            # SQLAlchemy models
│   ├── routes/
│   │   ├── auth.py          # Auth routes
│   │   ├── dashboard.py     # Dashboard
│   │   ├── tutor.py         # AI Tutor
│   │   ├── roadmap.py       # Learning Roadmap
│   │   ├── quiz.py          # Skill Quiz
│   │   ├── progress.py      # Progress & Timer
│   │   └── resources.py     # Resources & Projects
│   ├── services/
│   │   ├── ai_service.py    # IBM watsonx.ai integration
│   │   ├── quiz_service.py  # Quiz generation & validation
│   │   └── roadmap_service.py # Roadmap generation
│   ├── static/
│   │   ├── css/main.css     # Premium SaaS styling
│   │   └── js/main.js       # Client-side logic
│   └── templates/           # Jinja2 HTML templates
├── requirements.txt
├── run.py                   # Entry point
├── Procfile                 # Heroku/Railway deployment
└── .env.example
```

## AI Models Used

- **IBM Granite 3 8B Instruct** (`ibm/granite-3-8b-instruct`)
  - AI Tutoring conversations
  - Learning roadmap generation
  - Quiz generation (5 MCQs per session)
  - Quiz feedback & evaluation
  - Project recommendations
  - Domain classification (tech vs non-tech)
  - Onboarding analysis

## Deployment

### Heroku
```bash
heroku create
heroku config:set WATSONX_API_KEY=... WATSONX_PROJECT_ID=... SECRET_KEY=...
git push heroku main
```

### Railway / Render
Set environment variables in the platform dashboard and deploy from Git.

### Docker
```bash
docker build -t learnmate-ai .
docker run -p 5000:5000 --env-file .env learnmate-ai
```

## License

MIT License — Built for AICTE Problem Statement No. 12 using IBM watsonx.ai Granite.
