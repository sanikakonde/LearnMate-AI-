"""
LearnMate AI – Learning Roadmap Service
Generates personalized learning roadmaps using IBM watsonx.ai Granite.
"""
import json
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Verified Learning Resources by Domain
# ---------------------------------------------------------------------------
VERIFIED_RESOURCES = {
    "python": [
        {"name": "Python Official Documentation", "url": "https://docs.python.org/3/"},
        {"name": "Python Tutorial – freeCodeCamp", "url": "https://www.freecodecamp.org/learn/scientific-computing-with-python/"},
        {"name": "IBM SkillsBuild – Python", "url": "https://skillsbuild.org/"},
        {"name": "Kaggle Python Course", "url": "https://www.kaggle.com/learn/python"},
    ],
    "javascript": [
        {"name": "MDN Web Docs – JavaScript", "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript"},
        {"name": "freeCodeCamp – JavaScript", "url": "https://www.freecodecamp.org/learn/javascript-algorithms-and-data-structures/"},
        {"name": "The Odin Project", "url": "https://www.theodinproject.com/"},
    ],
    "machine learning": [
        {"name": "Kaggle Machine Learning", "url": "https://www.kaggle.com/learn/intro-to-machine-learning"},
        {"name": "Coursera – Machine Learning (Stanford)", "url": "https://www.coursera.org/learn/machine-learning"},
        {"name": "IBM SkillsBuild – AI Fundamentals", "url": "https://skillsbuild.org/"},
        {"name": "fast.ai", "url": "https://www.fast.ai/"},
        {"name": "Scikit-learn Docs", "url": "https://scikit-learn.org/stable/"},
    ],
    "data science": [
        {"name": "Kaggle Learn", "url": "https://www.kaggle.com/learn"},
        {"name": "Coursera – IBM Data Science", "url": "https://www.coursera.org/professional-certificates/ibm-data-science"},
        {"name": "edX – Data Science", "url": "https://www.edx.org/learn/data-science"},
        {"name": "IBM SkillsBuild", "url": "https://skillsbuild.org/"},
    ],
    "web development": [
        {"name": "MDN Web Docs", "url": "https://developer.mozilla.org/"},
        {"name": "freeCodeCamp", "url": "https://www.freecodecamp.org/"},
        {"name": "The Odin Project", "url": "https://www.theodinproject.com/"},
        {"name": "W3Schools", "url": "https://www.w3schools.com/"},
    ],
    "cloud computing": [
        {"name": "AWS Training & Certification", "url": "https://aws.amazon.com/training/"},
        {"name": "Microsoft Learn – Azure", "url": "https://learn.microsoft.com/en-us/azure/"},
        {"name": "Google Cloud Training", "url": "https://cloud.google.com/training"},
        {"name": "IBM SkillsBuild – Cloud", "url": "https://skillsbuild.org/"},
    ],
    "devops": [
        {"name": "Docker Official Docs", "url": "https://docs.docker.com/"},
        {"name": "Kubernetes Official Docs", "url": "https://kubernetes.io/docs/"},
        {"name": "GitHub Actions Docs", "url": "https://docs.github.com/en/actions"},
        {"name": "freeCodeCamp – DevOps", "url": "https://www.freecodecamp.org/"},
    ],
    "cybersecurity": [
        {"name": "OWASP Foundation", "url": "https://owasp.org/"},
        {"name": "Cybrary", "url": "https://www.cybrary.it/"},
        {"name": "IBM SkillsBuild – Cybersecurity", "url": "https://skillsbuild.org/"},
        {"name": "CompTIA Study Resources", "url": "https://www.comptia.org/training"},
    ],
    "default": [
        {"name": "IBM SkillsBuild", "url": "https://skillsbuild.org/"},
        {"name": "Coursera", "url": "https://www.coursera.org/"},
        {"name": "edX", "url": "https://www.edx.org/"},
        {"name": "freeCodeCamp", "url": "https://www.freecodecamp.org/"},
        {"name": "MIT OpenCourseWare", "url": "https://ocw.mit.edu/"},
    ],
}


def get_resources_for_topic(topic: str) -> list:
    """Get verified learning resources for a topic."""
    topic_lower = topic.lower()
    for key, resources in VERIFIED_RESOURCES.items():
        if key in topic_lower or topic_lower in key:
            return resources
    return VERIFIED_RESOURCES["default"]


# ---------------------------------------------------------------------------
# Roadmap Generation
# ---------------------------------------------------------------------------
ROADMAP_GENERATION_PROMPT = """You are LearnMate AI's agentic learning path designer. Generate a comprehensive, personalized learning roadmap.

Student Profile:
- Career Goal: {career_goal}
- Current Skill Level: {skill_level}
- Available Study Time: {study_hours} hours/day
- Interests: {interests}
- Learning Preferences: {preferences}

Generate a detailed, phase-by-phase learning roadmap for {career_goal} tailored to a {skill_level} student.

Requirements:
1. Include ONLY technologies relevant to {career_goal} — no unrelated tools
2. Organize into phases (Foundation → Core Skills → Advanced → Projects → Career Prep)
3. Each phase should have 3-6 milestones/topics
4. Include realistic time estimates based on {study_hours} hours/day
5. Include specific project ideas for the Projects phase
6. Include certification recommendations
7. Include interview preparation as a final phase

Respond ONLY with a valid JSON object in this exact format:
{{
  "career_goal": "{career_goal}",
  "total_duration_weeks": <number>,
  "overview": "2-3 sentence description of this learning path",
  "phases": [
    {{
      "phase_number": 1,
      "phase_name": "Foundation",
      "duration_weeks": <number>,
      "description": "What this phase covers",
      "milestones": [
        {{
          "title": "Topic/Skill name",
          "description": "What to learn and why",
          "estimated_hours": <number>,
          "resources": ["Resource 1", "Resource 2"],
          "deliverable": "What you'll be able to do after"
        }}
      ]
    }}
  ],
  "key_projects": [
    {{
      "title": "Project name",
      "description": "Project description",
      "skills_used": ["skill1", "skill2"],
      "difficulty": "beginner/intermediate/advanced"
    }}
  ],
  "certifications": [
    {{
      "name": "Certification name",
      "provider": "Provider",
      "relevance": "Why this certification matters",
      "when_to_take": "After Phase X"
    }}
  ],
  "interview_prep": {{
    "topics": ["topic1", "topic2"],
    "practice_platforms": ["LeetCode", "HackerRank"],
    "tips": ["tip1", "tip2"]
  }}
}}

Generate a complete, professional roadmap. Only output JSON.
"""


def generate_roadmap(career_goal: str, skill_level: str, study_hours: float,
                     interests: str = "", preferences: str = "") -> dict:
    """
    Generate a personalized learning roadmap using IBM watsonx.ai Granite.
    Returns parsed roadmap dict.
    """
    from app.services.ai_service import _get_client

    try:
        client = _get_client()
        prompt = ROADMAP_GENERATION_PROMPT.format(
            career_goal=career_goal,
            skill_level=skill_level,
            study_hours=study_hours,
            interests=interests or "General technology",
            preferences=preferences or "Balanced learning",
        )

        response_text = client.generate_text(
            prompt=prompt,
            params={
                "max_new_tokens": 4096,
                "temperature": 0.4,
                "top_p": 0.9,
                "repetition_penalty": 1.05,
            },
        )

        text = response_text.strip() if isinstance(response_text, str) else str(response_text)
        roadmap = _extract_json_object(text)

        if roadmap is None:
            raise ValueError("Could not extract valid JSON from AI response")

        # Validate and enrich
        roadmap = _validate_and_enrich_roadmap(roadmap, career_goal, skill_level)
        return roadmap

    except Exception as exc:
        logger.error("Roadmap generation error: %s", exc)
        raise RuntimeError(f"Failed to generate roadmap: {exc}") from exc


def _extract_json_object(text: str) -> Optional[dict]:
    """Extract JSON object from text."""
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    fence_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', text)
    if fence_match:
        try:
            data = json.loads(fence_match.group(1))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    return None


def _validate_and_enrich_roadmap(roadmap: dict, career_goal: str, skill_level: str) -> dict:
    """Validate and enrich the generated roadmap with defaults."""
    roadmap.setdefault("career_goal", career_goal)
    roadmap.setdefault("total_duration_weeks", 24)
    roadmap.setdefault("overview", f"Personalized roadmap for {career_goal} at {skill_level} level.")
    roadmap.setdefault("phases", [])
    roadmap.setdefault("key_projects", [])
    roadmap.setdefault("certifications", [])
    roadmap.setdefault("interview_prep", {"topics": [], "practice_platforms": [], "tips": []})

    # Ensure phases have required fields
    for i, phase in enumerate(roadmap["phases"]):
        phase.setdefault("phase_number", i + 1)
        phase.setdefault("phase_name", f"Phase {i + 1}")
        phase.setdefault("duration_weeks", 4)
        phase.setdefault("description", "")
        phase.setdefault("milestones", [])
        for milestone in phase["milestones"]:
            milestone.setdefault("title", "Topic")
            milestone.setdefault("description", "")
            milestone.setdefault("estimated_hours", 10)
            milestone.setdefault("resources", [])
            milestone.setdefault("deliverable", "")

    return roadmap


# ---------------------------------------------------------------------------
# Project Recommendations
# ---------------------------------------------------------------------------
PROJECT_RECOMMENDATION_PROMPT = """You are LearnMate AI. Recommend {count} hands-on projects for a student pursuing {career_goal} at {skill_level} level.

Requirements:
1. Projects must be directly relevant to {career_goal}
2. Mix of difficulty levels ({difficulty_focus})
3. Each project should build a portfolio piece
4. Include specific technologies to use
5. Include learning outcomes

Respond ONLY with a JSON array:
[
  {{
    "title": "Project title",
    "description": "Detailed project description (2-3 sentences)",
    "technologies": ["tech1", "tech2", "tech3"],
    "difficulty": "beginner/intermediate/advanced",
    "duration_hours": <number>,
    "learning_outcomes": ["outcome1", "outcome2"],
    "steps": ["step1", "step2", "step3"],
    "github_starter": "Brief suggestion for repo structure"
  }}
]
"""


def get_project_recommendations(career_goal: str, skill_level: str, count: int = 6) -> list:
    """Get AI-powered project recommendations."""
    from app.services.ai_service import _get_client
    from app.services.quiz_service import _extract_json_array

    difficulty_map = {
        "beginner": "mostly beginner with 1-2 intermediate",
        "intermediate": "mix of beginner, intermediate, and 1-2 advanced",
        "advanced": "mostly intermediate and advanced",
    }

    try:
        client = _get_client()
        prompt = PROJECT_RECOMMENDATION_PROMPT.format(
            count=count,
            career_goal=career_goal,
            skill_level=skill_level,
            difficulty_focus=difficulty_map.get(skill_level.lower(), "varied difficulty"),
        )
        response = client.generate_text(
            prompt=prompt,
            params={"max_new_tokens": 2048, "temperature": 0.6, "top_p": 0.9},
        )
        text = response.strip() if isinstance(response, str) else str(response)
        projects = _extract_json_array(text)
        if projects and isinstance(projects, list):
            return projects[:count]
    except Exception as exc:
        logger.error("Project recommendation error: %s", exc)

    return []
