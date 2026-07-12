"""
LearnMate AI – Resources & Project Recommendations Routes
"""
import json
import logging
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

logger = logging.getLogger(__name__)
resources_bp = Blueprint("resources", __name__, url_prefix="/resources")

CURATED_RESOURCES = [
    {
        "category": "Programming Languages",
        "icon": "bi-code-slash",
        "color": "blue",
        "links": [
            {"name": "Python Official Docs", "url": "https://docs.python.org/3/", "description": "Official Python 3 documentation and tutorials"},
            {"name": "MDN JavaScript Guide", "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide", "description": "Complete JavaScript reference by Mozilla"},
            {"name": "Java Documentation", "url": "https://docs.oracle.com/en/java/", "description": "Official Oracle Java SE documentation"},
            {"name": "C++ Reference", "url": "https://en.cppreference.com/", "description": "Comprehensive C++ language & standard library reference"},
            {"name": "Go Tour", "url": "https://go.dev/tour/", "description": "Official interactive tour of the Go language"},
            {"name": "Rust Book", "url": "https://doc.rust-lang.org/book/", "description": "The official Rust programming language book"},
        ],
    },
    {
        "category": "Web Development",
        "icon": "bi-browser-chrome",
        "color": "green",
        "links": [
            {"name": "MDN Web Docs", "url": "https://developer.mozilla.org/", "description": "The definitive web development reference"},
            {"name": "freeCodeCamp", "url": "https://www.freecodecamp.org/", "description": "Free interactive full-stack web curriculum"},
            {"name": "The Odin Project", "url": "https://www.theodinproject.com/", "description": "Full-stack open-source curriculum"},
            {"name": "W3Schools", "url": "https://www.w3schools.com/", "description": "Easy tutorials for HTML, CSS, JS and more"},
            {"name": "CSS-Tricks", "url": "https://css-tricks.com/", "description": "CSS tips, tricks and techniques"},
            {"name": "web.dev by Google", "url": "https://web.dev/", "description": "Modern web development guidance by Google"},
        ],
    },
    {
        "category": "AI & Machine Learning",
        "icon": "bi-cpu-fill",
        "color": "purple",
        "links": [
            {"name": "Google ML Crash Course", "url": "https://developers.google.com/machine-learning/crash-course", "description": "Free ML course with TensorFlow — by Google"},
            {"name": "Kaggle Learn", "url": "https://www.kaggle.com/learn", "description": "Free hands-on ML and data science courses"},
            {"name": "fast.ai", "url": "https://www.fast.ai/", "description": "Practical deep learning for coders"},
            {"name": "Hugging Face Learn", "url": "https://huggingface.co/learn", "description": "NLP, Transformers and LLMs hands-on"},
            {"name": "TensorFlow Tutorials", "url": "https://www.tensorflow.org/tutorials", "description": "Official TensorFlow ML tutorials"},
            {"name": "PyTorch Tutorials", "url": "https://pytorch.org/tutorials/", "description": "Official PyTorch deep learning tutorials"},
        ],
    },
    {
        "category": "Data Science",
        "icon": "bi-bar-chart-fill",
        "color": "orange",
        "links": [
            {"name": "Pandas Documentation", "url": "https://pandas.pydata.org/docs/", "description": "Official Pandas data manipulation library docs"},
            {"name": "NumPy Documentation", "url": "https://numpy.org/doc/", "description": "Official NumPy numerical computing docs"},
            {"name": "Scikit-learn Docs", "url": "https://scikit-learn.org/stable/", "description": "Official ML library with examples"},
            {"name": "Kaggle Datasets", "url": "https://www.kaggle.com/datasets", "description": "Thousands of free public datasets"},
            {"name": "Towards Data Science", "url": "https://towardsdatascience.com/", "description": "High-quality DS articles and tutorials"},
            {"name": "Coursera Data Science", "url": "https://www.coursera.org/browse/data-science", "description": "University-level data science courses"},
        ],
    },
    {
        "category": "Cloud Computing",
        "icon": "bi-cloud-fill",
        "color": "sky",
        "links": [
            {"name": "AWS Documentation", "url": "https://docs.aws.amazon.com/", "description": "Official Amazon Web Services documentation"},
            {"name": "Microsoft Azure Learn", "url": "https://learn.microsoft.com/en-us/azure/", "description": "Official Microsoft Azure learning paths"},
            {"name": "Google Cloud Skills Boost", "url": "https://www.cloudskillsboost.google/", "description": "Hands-on Google Cloud labs and courses"},
            {"name": "AWS Skill Builder", "url": "https://skillbuilder.aws/", "description": "Official AWS training and certification prep"},
            {"name": "Kubernetes Docs", "url": "https://kubernetes.io/docs/", "description": "Official Kubernetes container orchestration docs"},
            {"name": "Docker Docs", "url": "https://docs.docker.com/", "description": "Official Docker containerization documentation"},
        ],
    },
    {
        "category": "Cybersecurity",
        "icon": "bi-shield-lock-fill",
        "color": "red",
        "links": [
            {"name": "OWASP Foundation", "url": "https://owasp.org/", "description": "Open Web Application Security Project"},
            {"name": "TryHackMe", "url": "https://tryhackme.com/", "description": "Gamified cybersecurity learning platform"},
            {"name": "Hack The Box", "url": "https://www.hackthebox.com/", "description": "Real-world ethical hacking labs"},
            {"name": "Cybrary", "url": "https://www.cybrary.it/", "description": "Free and open cybersecurity training"},
            {"name": "PortSwigger Web Security", "url": "https://portswigger.net/web-security", "description": "Free Web Security Academy by Burp Suite"},
            {"name": "SANS Reading Room", "url": "https://www.sans.org/reading-room/", "description": "Free cybersecurity research papers and guides"},
        ],
    },
    {
        "category": "DevOps & Tools",
        "icon": "bi-gear-wide-connected",
        "color": "teal",
        "links": [
            {"name": "GitHub Docs", "url": "https://docs.github.com/", "description": "Official GitHub documentation and guides"},
            {"name": "GitHub Actions", "url": "https://docs.github.com/en/actions", "description": "Automate CI/CD workflows with GitHub Actions"},
            {"name": "Terraform Docs", "url": "https://developer.hashicorp.com/terraform/docs", "description": "Infrastructure as Code by HashiCorp"},
            {"name": "Ansible Documentation", "url": "https://docs.ansible.com/", "description": "Official Ansible automation platform docs"},
            {"name": "Linux Command Library", "url": "https://linuxcommandlibrary.com/", "description": "Essential Linux commands reference"},
            {"name": "DevDocs.io", "url": "https://devdocs.io/", "description": "Fast, offline documentation for 100+ APIs"},
        ],
    },
    {
        "category": "DSA & Interview Prep",
        "icon": "bi-lightning-charge-fill",
        "color": "yellow",
        "links": [
            {"name": "LeetCode", "url": "https://leetcode.com/", "description": "Practice coding problems for tech interviews"},
            {"name": "HackerRank", "url": "https://www.hackerrank.com/", "description": "Coding challenges and skill assessments"},
            {"name": "NeetCode", "url": "https://neetcode.io/", "description": "Structured DSA roadmap and video solutions"},
            {"name": "GeeksforGeeks", "url": "https://www.geeksforgeeks.org/", "description": "DSA tutorials, articles and interview questions"},
            {"name": "Visualgo", "url": "https://visualgo.net/", "description": "Visualise data structures and algorithms"},
            {"name": "Big-O Cheat Sheet", "url": "https://www.bigocheatsheet.com/", "description": "Algorithm complexity reference"},
        ],
    },
    {
        "category": "Databases",
        "icon": "bi-database-fill",
        "color": "indigo",
        "links": [
            {"name": "PostgreSQL Docs", "url": "https://www.postgresql.org/docs/", "description": "Official PostgreSQL documentation"},
            {"name": "MySQL Documentation", "url": "https://dev.mysql.com/doc/", "description": "Official MySQL reference manual"},
            {"name": "MongoDB Docs", "url": "https://www.mongodb.com/docs/", "description": "Official MongoDB NoSQL documentation"},
            {"name": "Redis Docs", "url": "https://redis.io/docs/", "description": "Official Redis in-memory data store docs"},
            {"name": "SQLZoo", "url": "https://sqlzoo.net/", "description": "Interactive SQL tutorials and exercises"},
            {"name": "db-fiddle", "url": "https://www.db-fiddle.com/", "description": "Online SQL sandbox for PostgreSQL, MySQL, SQLite"},
        ],
    },
]


@resources_bp.route("/")
@login_required
def index():
    career_goal = current_user.career_goal or "Software Engineer"
    # Render the page immediately with static curated resources.
    # Project recommendations are loaded asynchronously by the page's
    # own JS after the HTML is painted, so the tab opens instantly.
    return render_template(
        "resources/index.html",
        curated_resources=CURATED_RESOURCES,
        projects=[],          # loaded client-side after paint
        project_error=None,
        career_goal=career_goal,
    )


@resources_bp.route("/api/projects", methods=["POST"])
@login_required
def api_projects():
    """Get AI project recommendations for a specific goal/level."""
    data = request.get_json(silent=True) or {}
    career_goal = (data.get("career_goal") or current_user.career_goal or "Software Engineer").strip()
    skill_level = (data.get("skill_level") or current_user.current_skill_level or "beginner").strip()

    try:
        from app.services.roadmap_service import get_project_recommendations
        projects = get_project_recommendations(career_goal, skill_level, count=6)
        return jsonify({"projects": projects})
    except Exception as exc:
        logger.error("Project recommendations error: %s", exc)
        return jsonify({"error": str(exc)}), 500
