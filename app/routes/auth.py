"""
LearnMate AI – Authentication Routes
Register, Login, Logout, Profile, Onboarding.
"""
import json
import logging
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db, bcrypt
from app.models import User


logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        full_name = request.form.get("full_name", "").strip()

        # Validation
        errors = []
        if not username or len(username) < 3:
            errors.append("Username must be at least 3 characters.")
        if not email or "@" not in email:
            errors.append("A valid email address is required.")
        if not password or len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if password != confirm_password:
            errors.append("Passwords do not match.")
        if User.query.filter_by(username=username).first():
            errors.append("Username already taken.")
        if User.query.filter_by(email=email).first():
            errors.append("Email already registered.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("auth/register.html", form_data=request.form)

        try:
            pw_hash = bcrypt.generate_password_hash(password).decode("utf-8")
            user = User(
                username=username,
                email=email,
                password_hash=pw_hash,
                full_name=full_name or username,
            )
            db.session.add(user)
            db.session.commit()
            login_user(user, remember=True)
            flash("Account created! Let's personalize your learning journey.", "success")
            return redirect(url_for("auth.onboarding"))
        except Exception as exc:
            db.session.rollback()
            logger.error("Registration error: %s", exc)
            flash("Registration failed. Please try again.", "danger")

    return render_template("auth/register.html", form_data={})


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = User.query.filter(
            (User.email == identifier.lower()) | (User.username == identifier)
        ).first()

        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash(f"Welcome back, {user.get_display_name()}!", "success")
            next_page = request.args.get("next")
            if next_page and next_page.startswith("/"):
                return redirect(next_page)
            if not user.onboarding_complete:
                return redirect(url_for("auth.onboarding"))
            return redirect(url_for("dashboard.index"))
        else:
            flash("Invalid credentials. Please check your username/email and password.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/api/theme", methods=["POST"])
@login_required
def api_theme():
    """Save theme preference via AJAX."""
    data = request.get_json(silent=True) or {}
    theme = data.get("theme", "dark")
    if theme in ("dark", "light"):
        current_user.theme_preference = theme
        db.session.commit()
    return jsonify({"success": True})


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/onboarding", methods=["GET", "POST"])
@login_required
def onboarding():
    if current_user.onboarding_complete:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        career_goal = request.form.get("career_goal", "").strip()
        skill_level = request.form.get("skill_level", "beginner").strip()
        study_hours = float(request.form.get("study_hours", 2) or 2)
        interests = request.form.get("interests", "").strip()
        preferences_list = request.form.getlist("learning_preferences")

        if not career_goal:
            flash("Please select or enter your career goal.", "warning")
            return render_template("auth/onboarding.html")

        current_user.career_goal = career_goal
        current_user.current_skill_level = skill_level
        current_user.available_study_hours = study_hours
        current_user.interests = interests
        current_user.learning_preferences = json.dumps(preferences_list)
        current_user.onboarding_complete = True
        db.session.commit()

        # Auto-generate initial roadmap
        try:
            _auto_generate_roadmap(current_user)
        except Exception as exc:
            logger.warning("Auto roadmap generation failed: %s", exc)

        flash("Profile set up! Your personalized roadmap is ready.", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("auth/onboarding.html")


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        bio = request.form.get("bio", "").strip()
        career_goal = request.form.get("career_goal", "").strip()
        skill_level = request.form.get("skill_level", "beginner")
        study_hours = float(request.form.get("study_hours", 2) or 2)
        interests = request.form.get("interests", "").strip()
        theme = request.form.get("theme_preference", "dark")
        old_career_goal = current_user.career_goal

        current_user.full_name = full_name
        current_user.bio = bio
        current_user.career_goal = career_goal
        current_user.current_skill_level = skill_level
        current_user.available_study_hours = study_hours
        current_user.interests = interests
        current_user.theme_preference = theme
        db.session.commit()

        # If career goal changed, regenerate roadmap
        if career_goal and career_goal != old_career_goal:
            try:
                _auto_generate_roadmap(current_user)
                flash("Career goal updated! A new personalized roadmap has been generated.", "success")
            except Exception as exc:
                logger.warning("Roadmap regeneration failed: %s", exc)
                flash("Profile updated. Roadmap generation encountered an issue.", "warning")
        else:
            flash("Profile updated successfully.", "success")

        return redirect(url_for("auth.profile"))

    return render_template("auth/profile.html")


def _auto_generate_roadmap(user):
    """Helper: generate and save a roadmap for the user."""
    from app.services.roadmap_service import generate_roadmap
    from app.models import LearningRoadmap, RoadmapMilestone

    if not user.career_goal:
        return

    # Deactivate old roadmaps
    LearningRoadmap.query.filter_by(user_id=user.id, is_active=True).update({"is_active": False})
    db.session.flush()

    preferences = ""
    try:
        prefs_list = json.loads(user.learning_preferences or "[]")
        preferences = ", ".join(prefs_list)
    except Exception:
        pass

    roadmap_data = generate_roadmap(
        career_goal=user.career_goal,
        skill_level=user.current_skill_level or "beginner",
        study_hours=user.available_study_hours or 2,
        interests=user.interests or "",
        preferences=preferences,
    )

    roadmap = LearningRoadmap(
        user_id=user.id,
        career_goal=user.career_goal,
        skill_level=user.current_skill_level or "beginner",
        roadmap_data=json.dumps(roadmap_data),
        is_active=True,
        version=1,
    )
    db.session.add(roadmap)
    db.session.flush()

    # Create milestones
    order = 0
    for phase in roadmap_data.get("phases", []):
        for ms in phase.get("milestones", []):
            milestone = RoadmapMilestone(
                roadmap_id=roadmap.id,
                title=ms.get("title", "Topic"),
                description=ms.get("description", ""),
                phase=phase.get("phase_number", 1),
                order_index=order,
                estimated_weeks=max(1, ms.get("estimated_hours", 10) // (user.available_study_hours or 2) // 7),
                resources=json.dumps(ms.get("resources", [])),
            )
            db.session.add(milestone)
            order += 1

    db.session.commit()
    logger.info("Roadmap generated for user %s: %s", user.id, user.career_goal)
