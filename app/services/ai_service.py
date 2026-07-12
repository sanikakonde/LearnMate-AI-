"""
LearnMate AI – IBM watsonx.ai Service
Core service for all AI interactions using IBM Granite Foundation Models.
"""
import logging
import json
import re
from typing import Optional
from flask import current_app

# ---------------------------------------------------------------------------
# Chat Title Generation  – fast heuristic, no AI call required
# ---------------------------------------------------------------------------

# Stop-words to drop when building a title from a short question
_TITLE_STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "on", "at", "by", "for", "with", "about",
    "from", "into", "through", "during", "before", "after", "above",
    "below", "between", "and", "or", "but", "if", "while", "as",
    "what", "which", "who", "whom", "whose", "when", "where", "why", "how",
    "i", "me", "my", "we", "our", "you", "your", "it", "its",
    "this", "that", "these", "those", "there", "here",
    "please", "just", "like", "get", "give", "make", "let", "tell",
    "me", "us", "can", "you", "please",
}

# Common question-style openers that should be removed before the key terms
_QUESTION_OPENERS = re.compile(
    r"^(?:what\s+(?:is|are|was|were)\s+(?:a\s+|an\s+|the\s+)?|"
    r"how\s+(?:do|does|to|can|would|should)\s+(?:i\s+|you\s+|we\s+)?|"
    r"explain\s+(?:the\s+|a\s+|an\s+)?|"
    r"difference\s+between\s+|"
    r"(?:create|generate|build|write|give\s+me|show\s+me)\s+(?:a\s+|an\s+|the\s+)?|"
    r"(?:help\s+me\s+(?:with\s+)?|can\s+you\s+(?:explain\s+)?|"
    r"i\s+(?:want|need)\s+to\s+(?:learn\s+|understand\s+)?|"
    r"tell\s+me\s+(?:about\s+)?)|"
    r"study\s+plan\s+for\s+|roadmap\s+for\s+|guide\s+(?:to\s+|for\s+)|"
    r"interview\s+(?:questions?\s+)?(?:for\s+|on\s+|about\s+)?|"
    r"best\s+(?:way\s+to\s+|resources?\s+for\s+)?)",
    re.IGNORECASE,
)

# Canonical title suffixes for detected intent keywords
_INTENT_SUFFIX = {
    "roadmap": "Roadmap",
    "plan": "Plan",
    "guide": "Guide",
    "tutorial": "Tutorial",
    "interview": "Interview Prep",
    "interview prep": "Interview Prep",
    "project": "Project Ideas",
    "projects": "Project Ideas",
    "difference": "vs",
    "vs": "vs",
    "compare": "vs",
    "comparison": "Comparison",
    "explain": "",
    "examples": "Examples",
}


def generate_chat_title(first_message: str) -> str:
    """
    Generate a concise, meaningful 3–6 word chat title from the user's first
    message using fast regex/heuristic rules — no extra AI API call.

    Examples:
      "What is React?"                           → "What is React?"
      "Create a roadmap for Machine Learning"    → "Machine Learning Roadmap"
      "Explain Python lists"                     → "Python Lists"
      "Difference between CNN and RNN"           → "CNN vs RNN"
      "How to prepare for AWS interview?"        → "AWS Interview Prep"
    """
    msg = first_message.strip()
    if not msg:
        return "New Conversation"

    # Truncate very long messages to the first sentence / first 120 chars
    # before any processing so we work with the core intent only
    for sep in (".", "?", "!", "\n"):
        idx = msg.find(sep)
        if 0 < idx <= 120:
            msg = msg[:idx]
            break
    msg = msg[:120].strip()

    # --- Special case: "Difference between X and Y" → "X vs Y" ---
    diff_match = re.match(
        r"difference\s+between\s+(.+?)\s+and\s+(.+?)[\s?.!]*$",
        msg, re.IGNORECASE
    )
    if diff_match:
        def _smart_title(s):
            # Preserve all-uppercase acronyms (e.g. CNN, RNN, AWS)
            return " ".join(w if w.isupper() and len(w) > 1 else w.capitalize() for w in s.split())
        a = _smart_title(diff_match.group(1).strip())
        b = _smart_title(diff_match.group(2).strip())
        return f"{a} vs {b}"

    # --- Detect intent suffix (roadmap, guide, interview prep …) ---
    suffix = ""
    detected_suffix_kw = ""
    msg_lower = msg.lower()
    for kw, sfx in _INTENT_SUFFIX.items():
        if kw in msg_lower:
            suffix = sfx
            detected_suffix_kw = kw
            break

    # --- Strip question opener to expose key noun phrase ---
    core = _QUESTION_OPENERS.sub("", msg).strip(" ?.!")

    # If stripping removed everything fall back to original
    if not core:
        core = msg.strip(" ?.!")

    # Also strip the detected intent keyword itself from the core so it
    # doesn't appear in the middle of the title (e.g. "roadmap for ML" → "ML")
    if detected_suffix_kw:
        core = re.sub(
            r"\b" + re.escape(detected_suffix_kw) + r"\b\s*(?:for\s+|to\s+|of\s+|on\s+)?",
            "", core, flags=re.IGNORECASE
        ).strip(" ?.!")
    if not core:
        core = msg.strip(" ?.!")

    words = core.split()

    # Keep only meaningful words (drop stop-words) to build a compact title
    key_words = [w for w in words if w.lower().rstrip("?!.,;:") not in _TITLE_STOP_WORDS]

    # If filtering left too few meaningful words, keep the first 6 original words
    if len(key_words) < 2:
        key_words = words[:6]

    # Cap at 5 key words
    key_words = key_words[:5]

    # Build title string — preserve existing uppercase acronyms, title-case the rest
    def _fmt(w):
        bare = w.rstrip("?!.,;:")
        if bare.isupper() and len(bare) > 1:
            return w  # keep acronyms as-is: AWS, CNN, REST
        return w.title() if w == w.lower() else w

    title_core = " ".join(_fmt(w) for w in key_words)

    # Append intent suffix if it isn't already present and adds meaning
    if suffix and suffix.lower() not in title_core.lower():
        title = f"{title_core} {suffix}".strip()
    else:
        title = title_core

    # Final safety trim — never exceed 60 chars
    if len(title) > 60:
        title = title[:57].rstrip() + "..."

    return title or "New Conversation"

logger = logging.getLogger(__name__)


def _get_client():
    """Lazily initialise the watsonx.ai ModelInference client."""
    try:
        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference

        api_key = current_app.config.get("WATSONX_API_KEY", "")
        project_id = current_app.config.get("WATSONX_PROJECT_ID", "")
        url = current_app.config.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
        model_id = current_app.config.get("GRANITE_CHAT_MODEL", "ibm/granite-3-1-8b-base")

        if not api_key or not project_id:
            raise ValueError("IBM watsonx.ai credentials not configured. "
                             "Please set WATSONX_API_KEY and WATSONX_PROJECT_ID in .env")

        credentials = Credentials(url=url, api_key=api_key)
        client = ModelInference(
            model_id=model_id,
            credentials=credentials,
            project_id=project_id,
            params={
                "max_new_tokens": 2048,
                "temperature": 0.7,
                "top_p": 0.9,
                "repetition_penalty": 1.1,
            },
        )
        return client
    except ImportError as exc:
        raise RuntimeError("ibm-watsonx-ai package not installed. Run: pip install ibm-watsonx-ai") from exc


# ---------------------------------------------------------------------------
# Domain Classification  – keyword-first, AI-assisted fallback
# ---------------------------------------------------------------------------

# Tech keywords: if ANY of these appear in the question → allow it immediately
_TECH_KEYWORDS = {
    # languages
    "python", "javascript", "java", "typescript", "c++", "c#", "golang", "go lang",
    "rust", "kotlin", "swift", "ruby", "php", "scala", "perl", "r programming",
    "matlab", "julia", "dart", "elixir", "haskell", "lua", "groovy", "bash", "shell",
    "powershell", "assembly", "cobol", "fortran", "vba", "objective-c",
    # web
    "html", "css", "react", "angular", "vue", "svelte", "next.js", "nextjs",
    "nuxt", "gatsby", "django", "flask", "fastapi", "spring", "express", "node.js",
    "nodejs", "rails", "laravel", "asp.net", "graphql", "rest api", "restful",
    "websocket", "tailwind", "bootstrap", "sass", "webpack", "vite", "babel",
    # mobile
    "android", "ios", "flutter", "react native", "xamarin", "ionic", "swift ui",
    "jetpack compose", "kotlin multiplatform",
    # data / ai / ml
    "machine learning", "deep learning", "neural network", "artificial intelligence",
    "data science", "data analysis", "data engineering", "data pipeline",
    "nlp", "natural language processing", "computer vision", "reinforcement learning",
    "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn", "xgboost",
    "pandas", "numpy", "matplotlib", "seaborn", "plotly", "spark", "hadoop",
    "tableau", "power bi", "data warehouse", "etl", "feature engineering",
    "model training", "overfitting", "gradient descent", "backpropagation",
    "transformer", "llm", "large language model", "fine-tuning", "embeddings",
    "vector database", "rag", "prompt engineering", "langchain", "openai",
    "hugging face", "bert", "gpt", "stable diffusion",
    # cloud / devops
    "aws", "azure", "gcp", "google cloud", "ibm cloud", "cloud computing",
    "docker", "kubernetes", "k8s", "terraform", "ansible", "jenkins",
    "github actions", "ci/cd", "devops", "devsecops", "microservices",
    "serverless", "lambda", "ec2", "s3", "rds", "cloud native",
    "infrastructure as code", "helm", "prometheus", "grafana",
    # databases
    "sql", "mysql", "postgresql", "sqlite", "mongodb", "redis", "cassandra",
    "dynamodb", "elasticsearch", "neo4j", "nosql", "database design",
    "indexing", "query optimization", "orm", "acid", "transaction",
    # cybersecurity
    "cybersecurity", "ethical hacking", "penetration testing", "owasp",
    "cryptography", "ssl", "tls", "firewall", "vpn", "authentication",
    "authorization", "jwt", "oauth", "xss", "sql injection", "ddos",
    "network security", "zero trust", "siem", "vulnerability",
    # cs fundamentals
    "algorithm", "data structure", "linked list", "binary tree", "graph",
    "dynamic programming", "sorting", "searching", "big o", "complexity",
    "recursion", "stack", "queue", "heap", "hash map", "system design",
    "design pattern", "solid principles", "oop", "functional programming",
    "concurrency", "multithreading", "asynchronous", "api", "sdk",
    "compiler", "interpreter", "operating system", "linux", "unix",
    "networking", "tcp/ip", "http", "https", "dns", "load balancer",
    # career / learning
    "coding interview", "technical interview", "leetcode", "hackerrank",
    "resume", "portfolio", "career", "job", "software engineer",
    "full stack", "frontend", "backend", "data scientist", "ml engineer",
    "devops engineer", "roadmap", "certification", "bootcamp",
    "open source", "git", "github", "version control",
    # tools / platforms
    "vs code", "visual studio", "intellij", "pycharm", "jupyter",
    "postman", "figma", "jira", "confluence", "slack api",
    "firebase", "supabase", "vercel", "netlify", "heroku",
}

# Hard-reject patterns: if question clearly belongs to one of these → reject
_NON_TECH_PATTERNS = [
    r'\b(cricket|football|soccer|tennis|hockey|basketball|baseball|golf|rugby|sport|ipl|fifa|olympics)\b',
    r'\b(movie|film|actor|actress|bollywood|hollywood|celebrity|singer|music|song|album|concert)\b',
    r'\b(politics|election|president|prime minister|modi|biden|trump|government|parliament|congress|senate)\b',
    r'\b(religion|god|allah|jesus|bible|quran|temple|mosque|church|prayer|worship|spiritual)\b',
    r'\b(recipe|cook|cooking|food|restaurant|cuisine|dish|meal|ingredient|calorie)\b',
    r'\b(weather|temperature|rain|humidity|forecast|climate change|global warming)\b',
    r'\b(history|war|world war|independence|revolution|king|queen|emperor|dynasty|ancient)\b',
    r'\b(relationship|love|marriage|divorce|dating|boyfriend|girlfriend|breakup|romantic)\b',
    r'\b(medicine|doctor|hospital|disease|symptom|treatment|drug|vaccine|health|fitness|yoga)\b',
    r'\b(astrology|horoscope|zodiac|numerology|tarot|crystal|supernatural|ghost|alien)\b',
    r'\b(stock market|mutual fund|insurance|loan|mortgage|real estate|property|finance)\b',
    r'\b(travel|tourism|hotel|flight|visa|passport|country|city|tourism)\b',
]


def _keyword_check(question: str) -> str:
    """
    Returns 'tech', 'non_tech', or 'unknown'.
    'tech'     → matched a tech keyword → allow
    'non_tech' → matched a hard-reject pattern → reject
    'unknown'  → no clear signal → defer to AI
    """
    q_lower = question.lower()

    # 1. Check tech keywords first (fast allow)
    for kw in _TECH_KEYWORDS:
        if kw in q_lower:
            return "tech"

    # 2. Check hard-reject patterns
    for pattern in _NON_TECH_PATTERNS:
        if re.search(pattern, q_lower, re.IGNORECASE):
            return "non_tech"

    return "unknown"


_AI_CLASSIFIER_PROMPT = """You are a strict domain classifier for LearnMate AI, a technology learning platform.

Determine if the question is about technology, programming, software engineering, AI/ML, data science, cloud computing, cybersecurity, databases, networking, career guidance in tech, or any computer science topic.

Question: "{question}"

Respond ONLY with JSON: {{"is_tech_domain": true/false}}
Answer true ONLY for genuine technology/CS topics. Answer false for sports, politics, movies, food, religion, history, relationships, medicine, weather, or any non-technology topic."""


def classify_domain(question: str) -> dict:
    """
    Classify whether a question belongs to the technology education domain.
    Step 1: Keyword check (fast, no AI call needed for clear cases).
    Step 2: AI check only for ambiguous questions.
    Returns dict with keys: is_tech_domain, confidence, category.
    """
    result = _keyword_check(question)

    if result == "tech":
        return {"is_tech_domain": True, "confidence": 0.99, "category": "Technology"}

    if result == "non_tech":
        return {"is_tech_domain": False, "confidence": 0.99, "category": "Non-Technology"}

    # Ambiguous — try AI classifier
    try:
        client = _get_client()
        prompt = _AI_CLASSIFIER_PROMPT.format(question=question[:400])
        response = client.generate_text(
            prompt=prompt,
            params={"max_new_tokens": 50, "temperature": 0.0, "top_p": 1.0},
        )
        text = response.strip() if isinstance(response, str) else str(response)
        json_match = re.search(r'\{[^{}]+\}', text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            is_tech = bool(data.get("is_tech_domain", False))
            return {
                "is_tech_domain": is_tech,
                "confidence": 0.85,
                "category": "Technology" if is_tech else "General",
            }
    except Exception as exc:
        logger.warning("AI domain classification failed: %s — rejecting ambiguous question.", exc)
        # On AI failure for ambiguous questions → reject to be safe
        return {"is_tech_domain": False, "confidence": 0.5, "category": "Unknown"}

    # If AI gave no parseable result → reject ambiguous
    return {"is_tech_domain": False, "confidence": 0.5, "category": "Unknown"}


# ---------------------------------------------------------------------------
# AI Tutor
# ---------------------------------------------------------------------------
TUTOR_SYSTEM_PROMPT = """You are LearnMate AI, an expert AI learning coach and mentor specializing exclusively in technology education and career guidance. You have deep expertise in:

- All programming languages and frameworks
- Software engineering principles and best practices  
- AI, ML, Data Science, and Data Engineering
- Cloud computing, DevOps, cybersecurity, and databases
- System design and software architecture
- Technical interview preparation and career guidance
- Learning roadmaps and certifications

User Profile:
- Name: {name}
- Career Goal: {career_goal}
- Skill Level: {skill_level}
- Interests: {interests}

Your behavior:
1. Be a proactive, encouraging, and knowledgeable mentor
2. Provide detailed, accurate, and practical explanations
3. Use code examples when appropriate (properly formatted in markdown code blocks)
4. Relate answers to the user's career goal when relevant
5. Suggest next learning steps proactively
6. Be concise yet comprehensive
7. Use structured formatting (headings, bullet points, code blocks) for clarity

Always format code with proper markdown syntax highlighting.
"""


def get_tutor_response(
    question: str,
    conversation_history: list,
    user_profile: dict,
) -> str:
    """
    Generate an AI tutor response for the given question.
    conversation_history: list of {"role": "user"/"assistant", "content": "..."}
    """
    try:
        client = _get_client()
        system = TUTOR_SYSTEM_PROMPT.format(
            name=user_profile.get("name", "Student"),
            career_goal=user_profile.get("career_goal", "Software Engineering"),
            skill_level=user_profile.get("skill_level", "Beginner"),
            interests=user_profile.get("interests", "Technology"),
        )

        # Build conversation prompt
        prompt_parts = [f"[SYSTEM]\n{system}\n"]
        for msg in conversation_history[-10:]:  # keep last 10 messages for context
            role_label = "User" if msg["role"] == "user" else "LearnMate AI"
            prompt_parts.append(f"[{role_label}]\n{msg['content']}\n")
        prompt_parts.append(f"[User]\n{question}\n[LearnMate AI]\n")

        full_prompt = "\n".join(prompt_parts)
        response = client.generate_text(prompt=full_prompt)
        return response.strip() if isinstance(response, str) else str(response)

    except Exception as exc:
        logger.error("Tutor response error: %s", exc)
        raise RuntimeError(f"AI service error: {exc}") from exc


# ---------------------------------------------------------------------------
# Onboarding / Profile Analysis
# ---------------------------------------------------------------------------
ONBOARDING_ANALYSIS_PROMPT = """You are LearnMate AI's onboarding agent. Analyze the student profile and provide a warm, personalized welcome message with:
1. A brief assessment of their current position
2. Why their career goal is achievable
3. Key strengths to leverage
4. 3-5 immediate next steps to start their journey
5. Estimated timeline to reach their goal

Student Profile:
- Name: {name}
- Career Goal: {career_goal}
- Current Skill Level: {skill_level}
- Interests: {interests}
- Available Study Time: {study_hours} hours/day
- Learning Preferences: {preferences}

Provide an encouraging, detailed, personalized response. Use markdown formatting.
"""


def generate_onboarding_analysis(user_profile: dict) -> str:
    """Generate personalized onboarding analysis for a new user."""
    try:
        client = _get_client()
        prompt = ONBOARDING_ANALYSIS_PROMPT.format(
            name=user_profile.get("name", "Student"),
            career_goal=user_profile.get("career_goal", "Software Engineer"),
            skill_level=user_profile.get("skill_level", "Beginner"),
            interests=user_profile.get("interests", "Technology"),
            study_hours=user_profile.get("study_hours", 2),
            preferences=user_profile.get("preferences", "Visual learning"),
        )
        response = client.generate_text(prompt=prompt)
        return response.strip() if isinstance(response, str) else str(response)
    except Exception as exc:
        logger.error("Onboarding analysis error: %s", exc)
        raise RuntimeError(f"AI service error: {exc}") from exc


# ---------------------------------------------------------------------------
# Next Step Recommendation (Agentic)
# ---------------------------------------------------------------------------
NEXT_STEP_PROMPT = """You are LearnMate AI's agentic learning advisor. Based on the student's current progress, recommend the most important next learning action.

Student Profile:
- Career Goal: {career_goal}
- Skill Level: {skill_level}
- Completed Topics: {completed_topics}
- Recent Quiz Performance: {quiz_performance}
- Current Roadmap Phase: {current_phase}
- Study Hours/Day: {study_hours}

Provide a specific, actionable recommendation as a JSON object:
{{
  "next_topic": "Topic name",
  "why": "Brief reason this is the next best step",
  "action": "Specific action to take right now",
  "resources": ["resource1", "resource2"],
  "estimated_time": "X hours/days",
  "encouragement": "Brief motivational message"
}}

Respond ONLY with the JSON object.
"""


def get_next_step_recommendation(profile_data: dict) -> dict:
    """Get AI-powered next step recommendation for the user's learning journey."""
    try:
        client = _get_client()
        prompt = NEXT_STEP_PROMPT.format(
            career_goal=profile_data.get("career_goal", "Software Engineer"),
            skill_level=profile_data.get("skill_level", "Beginner"),
            completed_topics=", ".join(profile_data.get("completed_topics", [])) or "None yet",
            quiz_performance=profile_data.get("quiz_performance", "Not started"),
            current_phase=profile_data.get("current_phase", "Foundation"),
            study_hours=profile_data.get("study_hours", 2),
        )
        response = client.generate_text(prompt=prompt)
        text = response.strip() if isinstance(response, str) else str(response)

        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception as exc:
        logger.error("Next step recommendation error: %s", exc)

    return {
        "next_topic": "Continue your current roadmap",
        "why": "Keep building on your current progress",
        "action": "Review your roadmap and pick the next pending topic",
        "resources": [],
        "estimated_time": "Varies",
        "encouragement": "Every step forward brings you closer to your goal!",
    }


# ---------------------------------------------------------------------------
# Quiz Feedback
# ---------------------------------------------------------------------------
QUIZ_FEEDBACK_PROMPT = """You are LearnMate AI. A student just completed a quiz. Provide personalized feedback.

Quiz Details:
- Topic: {topic}
- Difficulty: {difficulty}
- Score: {score}%
- Correct: {correct}/{total}
- Weak Areas: {weak_areas}

Provide:
1. Score assessment (2-3 sentences)
2. What they did well
3. Specific areas to improve
4. 3 concrete study recommendations for weak areas
5. Motivational closing

Use markdown formatting. Keep it concise and actionable.
"""


def generate_quiz_feedback(quiz_data: dict) -> str:
    """Generate personalized feedback after a quiz."""
    try:
        client = _get_client()
        prompt = QUIZ_FEEDBACK_PROMPT.format(
            topic=quiz_data.get("topic", "Technology"),
            difficulty=quiz_data.get("difficulty", "Intermediate"),
            score=quiz_data.get("score", 0),
            correct=quiz_data.get("correct", 0),
            total=quiz_data.get("total", 5),
            weak_areas=", ".join(quiz_data.get("weak_areas", [])) or "Review all concepts",
        )
        response = client.generate_text(prompt=prompt)
        return response.strip() if isinstance(response, str) else str(response)
    except Exception as exc:
        logger.error("Quiz feedback error: %s", exc)
        return "Great effort! Review the explanations for incorrect answers to strengthen your understanding."
