"""
LearnMate AI – Quiz Service
Generates AI-powered quizzes using IBM watsonx.ai Granite.
"""
import json
import re
import logging
from typing import Optional, Tuple
from flask import current_app

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Topic Validation
# ---------------------------------------------------------------------------
TOPIC_ALIASES = {
    "js": "JavaScript",
    "ts": "TypeScript",
    "py": "Python",
    "ml": "Machine Learning",
    "ai": "Artificial Intelligence",
    "dl": "Deep Learning",
    "nlp": "Natural Language Processing",
    "cv": "Computer Vision",
    "ds": "Data Science",
    "de": "Data Engineering",
    "da": "Data Analytics",
    "dsa": "Data Structures and Algorithms",
    "oop": "Object-Oriented Programming",
    "os": "Operating Systems",
    "db": "Databases",
    "sql": "SQL",
    "nosql": "NoSQL Databases",
    "ci/cd": "CI/CD and DevOps",
    "aws": "Amazon Web Services",
    "gcp": "Google Cloud Platform",
    "k8s": "Kubernetes",
    "c++": "C++",
    "c#": "C#",
    "c": "C Programming",
    "css": "CSS",
    "html": "HTML",
    "api": "REST APIs",
    "rest": "REST APIs",
    "graphql": "GraphQL",
    "llm": "Large Language Models",
    "sd": "System Design",
}

TOPIC_VALIDATION_PROMPT = """You are a technical topic validator for LearnMate AI.

Determine if the following topic is a valid technology/programming/software engineering topic that a student could be quizzed on.

Valid topics include:
- Programming languages (Python, Java, JavaScript, C, C++, Go, Rust, TypeScript, Kotlin, Swift, R, etc.)
- Frameworks and libraries (React, Angular, Vue, Django, Flask, Spring, Node.js, TensorFlow, PyTorch, etc.)
- AI/ML concepts (Machine Learning, Deep Learning, NLP, Computer Vision, Reinforcement Learning, etc.)
- Data topics (Data Science, Data Analysis, Data Engineering, SQL, NoSQL, Pandas, NumPy, etc.)
- Cloud platforms (AWS, Azure, GCP, IBM Cloud, Kubernetes, Docker, Terraform, etc.)
- DevOps and tools (CI/CD, Git, Jenkins, Ansible, etc.)
- Cybersecurity concepts
- Networking and operating systems
- Databases (PostgreSQL, MySQL, MongoDB, Redis, Cassandra, etc.)
- Software engineering (OOP, Design Patterns, System Design, Microservices, etc.)
- Algorithms and data structures
- Web development technologies
- Mobile development
- Technical certifications
- Career roles (Software Engineer, Data Scientist, etc. — quiz on the core skills for that role)

Topic to validate: "{topic}"

Respond ONLY with JSON:
{{"is_valid": true/false, "normalized_topic": "proper full name", "reason": "brief reason if invalid"}}
"""


def validate_and_normalize_topic(topic: str) -> dict:
    """Validate topic and return normalized name. Uses alias map first, then AI validation."""
    cleaned = topic.strip().lower()

    # Check alias map first
    if cleaned in TOPIC_ALIASES:
        return {"is_valid": True, "normalized_topic": TOPIC_ALIASES[cleaned], "reason": ""}

    # Use AI to validate
    try:
        from app.services.ai_service import _get_client
        client = _get_client()
        prompt = TOPIC_VALIDATION_PROMPT.format(topic=topic[:100])
        response = client.generate_text(prompt=prompt)
        text = response.strip() if isinstance(response, str) else str(response)

        json_match = re.search(r'\{[^{}]+\}', text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return {
                "is_valid": bool(result.get("is_valid", True)),
                "normalized_topic": result.get("normalized_topic", topic.title()),
                "reason": result.get("reason", ""),
            }
    except Exception as exc:
        logger.warning("Topic validation failed: %s — allowing topic.", exc)

    # Permissive fallback
    return {"is_valid": True, "normalized_topic": topic.title(), "reason": ""}


# ---------------------------------------------------------------------------
# Quiz Generation
# ---------------------------------------------------------------------------
QUIZ_GENERATION_PROMPT = """You are LearnMate AI's quiz generator. Generate a high-quality technical quiz.

Topic: {topic}
Difficulty: {difficulty}
Number of Questions: 5

Difficulty Guidelines:
- Beginner: Definitions, basic syntax, fundamental concepts, introductory ideas
- Intermediate: Practical implementation, output prediction, debugging, comparisons, scenario-based
- Advanced: Interview-level, production scenarios, architecture, optimization, edge cases, complex debugging, multi-step reasoning

Requirements:
1. ALL 5 questions must be about {topic} ONLY — no other technologies
2. Each question must test a DIFFERENT concept
3. Questions at {difficulty} level must NOT overlap with other difficulty levels
4. Use proper formatting for any code snippets (use backticks)
5. Each question must have EXACTLY 4 unique options
6. One correct answer per question
7. Include a clear explanation for the correct answer
8. Options must be clearly distinct and non-trivial

{code_instruction}

Respond ONLY with a valid JSON array of exactly 5 questions in this format:
[
  {{
    "question": "Question text here (include code block if relevant using ```language\\ncode\\n```)",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer": "Option A",
    "explanation": "Detailed explanation of why this is correct and why others are wrong"
  }},
  ...
]

Generate exactly 5 questions. No additional text, only the JSON array.
"""

CODE_INSTRUCTION = "For programming topics, include at least 2-3 questions with relevant code snippets formatted as markdown code blocks."
NO_CODE_INSTRUCTION = "Focus on conceptual, architectural, and practical questions appropriate for this topic."


def _is_programming_topic(topic: str) -> bool:
    """Check if the topic involves code."""
    code_topics = {
        "python", "javascript", "java", "c++", "c programming", "typescript", "go", "rust",
        "kotlin", "swift", "ruby", "php", "scala", "r programming", "matlab",
        "react", "angular", "vue", "django", "flask", "spring", "node", "express",
        "html", "css", "sql", "mongodb", "data structures", "algorithms", "dsa",
        "machine learning", "deep learning", "tensorflow", "pytorch", "scikit-learn",
        "numpy", "pandas", "shell scripting", "bash", "powershell",
    }
    return any(kw in topic.lower() for kw in code_topics)


def _validate_quiz_response(questions: list, topic: str, difficulty: str) -> Tuple[bool, str]:
    """Validate the quiz response for correctness."""
    if not isinstance(questions, list):
        return False, "Response is not a list"
    if len(questions) != 5:
        return False, f"Expected 5 questions, got {len(questions)}"

    seen_questions = set()
    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            return False, f"Question {i+1} is not a dict"
        for field in ("question", "options", "correct_answer", "explanation"):
            if field not in q:
                return False, f"Question {i+1} missing field: {field}"
        if not isinstance(q["options"], list) or len(q["options"]) != 4:
            return False, f"Question {i+1} must have exactly 4 options"
        if q["correct_answer"] not in q["options"]:
            return False, f"Question {i+1} correct_answer not in options"
        if len(set(q["options"])) != 4:
            return False, f"Question {i+1} has duplicate options"
        q_text = q["question"].strip().lower()[:80]
        if q_text in seen_questions:
            return False, f"Duplicate question at index {i+1}"
        seen_questions.add(q_text)
        if not q["explanation"].strip():
            return False, f"Question {i+1} has empty explanation"

    return True, "OK"


def generate_quiz(topic: str, difficulty: str, max_retries: Optional[int] = None) -> list:
    """
    Generate 5 AI-powered MCQs for the given topic and difficulty.
    Retries up to max_retries times if validation fails.
    Raises RuntimeError if all retries fail.
    """
    from app.services.ai_service import _get_client

    if max_retries is None:
        from flask import current_app
        max_retries = current_app.config.get("MAX_QUIZ_RETRIES", 3)

    code_instruction = CODE_INSTRUCTION if _is_programming_topic(topic) else NO_CODE_INSTRUCTION

    prompt = QUIZ_GENERATION_PROMPT.format(
        topic=topic,
        difficulty=difficulty.capitalize(),
        code_instruction=code_instruction,
    )

    last_error = "Unknown error"
    for attempt in range(1, max_retries + 1):
        try:
            client = _get_client()
            response_text = client.generate_text(
                prompt=prompt,
                params={
                    "max_new_tokens": 3000,
                    "temperature": 0.3 + (attempt - 1) * 0.15,
                    "top_p": 0.9,
                    "repetition_penalty": 1.05,
                },
            )

            text = response_text.strip() if isinstance(response_text, str) else str(response_text)

            # Extract JSON array
            questions = _extract_json_array(text)
            if questions is None:
                last_error = "Could not extract JSON array from response"
                logger.warning("Attempt %d: %s", attempt, last_error)
                continue

            valid, reason = _validate_quiz_response(questions, topic, difficulty)
            if valid:
                logger.info("Quiz generated successfully on attempt %d for topic=%s difficulty=%s",
                            attempt, topic, difficulty)
                return questions

            last_error = reason
            logger.warning("Attempt %d validation failed: %s", attempt, reason)

        except Exception as exc:
            last_error = str(exc)
            logger.error("Attempt %d error: %s", attempt, exc)

    raise RuntimeError(
        f"Failed to generate valid quiz for '{topic}' ({difficulty}) after {max_retries} attempts. "
        f"Last error: {last_error}"
    )


def _extract_json_array(text: str) -> Optional[list]:
    """Extract a JSON array from a text response."""
    # Direct parse
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # Find array in text
    bracket_match = re.search(r'\[[\s\S]*\]', text)
    if bracket_match:
        try:
            data = json.loads(bracket_match.group())
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    # Try to find array between code fences
    fence_match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', text)
    if fence_match:
        try:
            data = json.loads(fence_match.group(1))
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    return None


def calculate_score(questions: list, user_answers: dict) -> dict:
    """
    Calculate quiz score.
    user_answers: {str(question_index): "selected_option"}
    Returns: {score, correct_count, total, results, weak_areas}
    """
    results = []
    correct_count = 0
    weak_areas = []

    for i, q in enumerate(questions):
        user_answer = user_answers.get(str(i), "")
        is_correct = user_answer == q.get("correct_answer", "")
        if is_correct:
            correct_count += 1
        else:
            weak_areas.append(q.get("question", "")[:60])

        results.append({
            "question": q.get("question", ""),
            "options": q.get("options", []),
            "user_answer": user_answer,
            "correct_answer": q.get("correct_answer", ""),
            "is_correct": is_correct,
            "explanation": q.get("explanation", ""),
        })

    total = len(questions)
    score = round((correct_count / total) * 100) if total > 0 else 0

    return {
        "score": score,
        "correct_count": correct_count,
        "total": total,
        "results": results,
        "weak_areas": weak_areas[:3],
    }
