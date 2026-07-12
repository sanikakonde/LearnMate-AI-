"""
LearnMate AI – Roadmap Routes
Personalized learning roadmap generation, viewing, and milestone management.
"""
import json
import logging
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import db
from app.models import LearningRoadmap, RoadmapMilestone

logger = logging.getLogger(__name__)
roadmap_bp = Blueprint("roadmap", __name__, url_prefix="/roadmap")


@roadmap_bp.route("/")
@login_required
def index():
    active_roadmap = LearningRoadmap.query.filter_by(
        user_id=current_user.id, is_active=True
    ).order_by(LearningRoadmap.created_at.desc()).first()

    roadmap_data = None
    milestones = []
    phases = []

    if active_roadmap:
        try:
            roadmap_data = json.loads(active_roadmap.roadmap_data)
        except Exception:
            roadmap_data = {}
        milestones = RoadmapMilestone.query.filter_by(
            roadmap_id=active_roadmap.id
        ).order_by(RoadmapMilestone.phase, RoadmapMilestone.order_index).all()

        # Group milestones by phase
        phase_map = {}
        for m in milestones:
            if m.phase not in phase_map:
                phase_map[m.phase] = []
            phase_map[m.phase].append(m)
        phases = sorted(phase_map.items())

    all_roadmaps = LearningRoadmap.query.filter_by(
        user_id=current_user.id
    ).order_by(LearningRoadmap.created_at.desc()).all()

    return render_template(
        "roadmap/index.html",
        active_roadmap=active_roadmap,
        roadmap_data=roadmap_data,
        milestones=milestones,
        phases=phases,
        all_roadmaps=all_roadmaps,
    )


@roadmap_bp.route("/generate", methods=["POST"])
@login_required
def generate():
    """Generate a new personalized roadmap."""
    data = request.get_json(silent=True) or request.form
    career_goal = (data.get("career_goal") or "").strip()
    skill_level = (data.get("skill_level") or "beginner").strip()
    study_hours = float(data.get("study_hours") or current_user.available_study_hours or 2)
    interests = (data.get("interests") or current_user.interests or "").strip()

    if not career_goal:
        if request.is_json:
            return jsonify({"error": "Career goal is required."}), 400
        flash("Please enter your career goal.", "warning")
        return redirect(url_for("roadmap.index"))

    try:
        from app.services.roadmap_service import generate_roadmap
        roadmap_data = generate_roadmap(
            career_goal=career_goal,
            skill_level=skill_level,
            study_hours=study_hours,
            interests=interests,
        )

        # Deactivate old roadmaps
        LearningRoadmap.query.filter_by(user_id=current_user.id, is_active=True).update({"is_active": False})
        db.session.flush()

        # Save new roadmap
        roadmap = LearningRoadmap(
            user_id=current_user.id,
            career_goal=career_goal,
            skill_level=skill_level,
            roadmap_data=json.dumps(roadmap_data),
            is_active=True,
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
                    estimated_weeks=max(1, ms.get("estimated_hours", 10) // max(1, int(study_hours * 7))),
                    resources=json.dumps(ms.get("resources", [])),
                )
                db.session.add(milestone)
                order += 1

        # Update user profile
        current_user.career_goal = career_goal
        current_user.current_skill_level = skill_level
        db.session.commit()

        if request.is_json:
            return jsonify({"success": True, "roadmap_id": roadmap.id})
        flash("Your personalized roadmap has been generated!", "success")
        return redirect(url_for("roadmap.index"))

    except Exception as exc:
        db.session.rollback()
        logger.error("Roadmap generation error: %s", exc)
        if request.is_json:
            return jsonify({"error": str(exc)}), 500
        flash(f"Roadmap generation failed: {str(exc)}", "danger")
        return redirect(url_for("roadmap.index"))


@roadmap_bp.route("/api/milestone/<int:milestone_id>/update", methods=["POST"])
@login_required
def update_milestone(milestone_id):
    """Update milestone status."""
    milestone = RoadmapMilestone.query.get_or_404(milestone_id)
    # Verify ownership
    roadmap = LearningRoadmap.query.filter_by(
        id=milestone.roadmap_id, user_id=current_user.id
    ).first_or_404()

    data = request.get_json(silent=True) or {}
    new_status = data.get("status", "")

    if new_status not in ("pending", "in_progress", "completed"):
        return jsonify({"error": "Invalid status."}), 400

    from datetime import datetime
    milestone.status = new_status
    if new_status == "completed":
        milestone.completed_at = datetime.utcnow()
    elif new_status != "completed":
        milestone.completed_at = None

    db.session.commit()
    return jsonify({"success": True, "status": new_status})


@roadmap_bp.route("/api/roadmap-data")
@login_required
def api_roadmap_data():
    """Return roadmap data as JSON for frontend rendering."""
    active_roadmap = LearningRoadmap.query.filter_by(
        user_id=current_user.id, is_active=True
    ).order_by(LearningRoadmap.created_at.desc()).first()

    if not active_roadmap:
        return jsonify({"error": "No active roadmap found."}), 404

    try:
        roadmap_data = json.loads(active_roadmap.roadmap_data)
    except Exception:
        roadmap_data = {}

    milestones = RoadmapMilestone.query.filter_by(
        roadmap_id=active_roadmap.id
    ).order_by(RoadmapMilestone.phase, RoadmapMilestone.order_index).all()

    milestones_data = [{
        "id": m.id,
        "title": m.title,
        "description": m.description,
        "phase": m.phase,
        "order_index": m.order_index,
        "status": m.status,
        "estimated_weeks": m.estimated_weeks,
        "resources": json.loads(m.resources or "[]"),
    } for m in milestones]

    return jsonify({
        "roadmap": roadmap_data,
        "milestones": milestones_data,
        "career_goal": active_roadmap.career_goal,
        "skill_level": active_roadmap.skill_level,
    })
