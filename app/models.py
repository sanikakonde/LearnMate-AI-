"""
LearnMate AI – Database Models
SQLAlchemy ORM models for all application entities.
"""
from datetime import datetime
from flask_login import UserMixin
from app.extensions import db, login_manager


# ---------------------------------------------------------------------------
# User Loader
# ---------------------------------------------------------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(128), nullable=True)
    avatar_initials = db.Column(db.String(4), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    career_goal = db.Column(db.String(128), nullable=True)
    current_skill_level = db.Column(db.String(32), nullable=True)  # beginner/intermediate/advanced
    learning_preferences = db.Column(db.Text, nullable=True)       # JSON string
    available_study_hours = db.Column(db.Float, nullable=True)
    interests = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    theme_preference = db.Column(db.String(16), default="dark")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    onboarding_complete = db.Column(db.Boolean, default=False)

    # Relationships
    roadmaps = db.relationship("LearningRoadmap", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    quiz_sessions = db.relationship("QuizSession", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    study_sessions = db.relationship("StudySession", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    chat_sessions = db.relationship("ChatSession", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    progress_logs = db.relationship("ProgressLog", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username}>"

    def get_display_name(self):
        return self.full_name or self.username

    def get_initials(self):
        if self.full_name:
            parts = self.full_name.strip().split()
            if len(parts) >= 2:
                return (parts[0][0] + parts[-1][0]).upper()
            return parts[0][:2].upper()
        return self.username[:2].upper()

    def total_quiz_score(self):
        sessions = self.quiz_sessions.all()
        if not sessions:
            return 0
        return sum(s.score for s in sessions) // len(sessions)

    def total_study_minutes(self):
        return sum(s.duration_minutes for s in self.study_sessions.all())

    def completed_topics_count(self):
        return ProgressLog.query.filter_by(user_id=self.id, status="completed").count()


# ---------------------------------------------------------------------------
# Learning Roadmap
# ---------------------------------------------------------------------------
class LearningRoadmap(db.Model):
    __tablename__ = "learning_roadmaps"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    career_goal = db.Column(db.String(128), nullable=False)
    skill_level = db.Column(db.String(32), nullable=False)
    roadmap_data = db.Column(db.Text, nullable=False)   # JSON
    is_active = db.Column(db.Boolean, default=True)
    version = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    milestones = db.relationship("RoadmapMilestone", backref="roadmap", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Roadmap {self.career_goal} v{self.version}>"


# ---------------------------------------------------------------------------
# Roadmap Milestone
# ---------------------------------------------------------------------------
class RoadmapMilestone(db.Model):
    __tablename__ = "roadmap_milestones"

    id = db.Column(db.Integer, primary_key=True)
    roadmap_id = db.Column(db.Integer, db.ForeignKey("learning_roadmaps.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    phase = db.Column(db.Integer, nullable=False, default=1)
    order_index = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(32), default="pending")  # pending/in_progress/completed
    estimated_weeks = db.Column(db.Integer, nullable=True)
    resources = db.Column(db.Text, nullable=True)   # JSON list
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Milestone {self.title}>"


# ---------------------------------------------------------------------------
# Quiz Session
# ---------------------------------------------------------------------------
class QuizSession(db.Model):
    __tablename__ = "quiz_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    topic = db.Column(db.String(128), nullable=False)
    difficulty = db.Column(db.String(32), nullable=False)
    score = db.Column(db.Integer, default=0)        # 0-100
    correct_count = db.Column(db.Integer, default=0)
    total_questions = db.Column(db.Integer, default=5)
    time_taken_seconds = db.Column(db.Integer, default=0)
    questions_data = db.Column(db.Text, nullable=True)   # JSON
    answers_data = db.Column(db.Text, nullable=True)     # JSON
    feedback = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<QuizSession {self.topic} {self.score}%>"

    def grade_label(self):
        if self.score >= 90:
            return "Excellent"
        elif self.score >= 75:
            return "Good"
        elif self.score >= 60:
            return "Average"
        return "Needs Work"

    def grade_color(self):
        if self.score >= 90:
            return "success"
        elif self.score >= 75:
            return "info"
        elif self.score >= 60:
            return "warning"
        return "danger"


# ---------------------------------------------------------------------------
# Study Session (Timer)
# ---------------------------------------------------------------------------
class StudySession(db.Model):
    __tablename__ = "study_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    topic = db.Column(db.String(200), nullable=True)
    duration_minutes = db.Column(db.Integer, default=0)
    session_type = db.Column(db.String(32), default="focus")  # focus/break
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<StudySession {self.topic} {self.duration_minutes}m>"


# ---------------------------------------------------------------------------
# Chat Session (AI Tutor)
# ---------------------------------------------------------------------------
class ChatSession(db.Model):
    __tablename__ = "chat_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = db.relationship("ChatMessage", backref="session", lazy="dynamic",
                                order_by="ChatMessage.created_at", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ChatSession {self.id}>"


# ---------------------------------------------------------------------------
# Chat Message
# ---------------------------------------------------------------------------
class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role = db.Column(db.String(16), nullable=False)   # user / assistant
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ChatMessage {self.role}>"


# ---------------------------------------------------------------------------
# Progress Log
# ---------------------------------------------------------------------------
class ProgressLog(db.Model):
    __tablename__ = "progress_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    topic = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(32), default="in_progress")  # in_progress/completed/paused
    progress_percent = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ProgressLog {self.topic} {self.progress_percent}%>"
