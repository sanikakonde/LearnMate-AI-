"""
LearnMate AI – Progress & Study Timer Routes
"""
import json
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import ProgressLog, StudySession

logger = logging.getLogger(__name__)
progress_bp = Blueprint("progress", __name__, url_prefix="/progress")


@progress_bp.route("/")
@login_required
def index():
    logs = current_user.progress_logs.order_by(ProgressLog.updated_at.desc()).all()
    study_sessions = current_user.study_sessions.order_by(
        StudySession.created_at.desc()
    ).limit(20).all()
    total_study_mins = current_user.total_study_minutes()
    completed = current_user.completed_topics_count()

    # Weekly study data
    from app.routes.dashboard import _get_study_chart_data
    study_chart = json.dumps(_get_study_chart_data(7))

    return render_template(
        "progress/index.html",
        logs=logs,
        study_sessions=study_sessions,
        total_study_mins=total_study_mins,
        completed=completed,
        study_chart=study_chart,
    )


@progress_bp.route("/api/log", methods=["POST"])
@login_required
def api_log():
    """Add or update a progress log entry."""
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()
    status = data.get("status", "in_progress")
    progress_percent = int(data.get("progress_percent") or 0)
    notes = (data.get("notes") or "").strip()

    if not topic:
        return jsonify({"error": "Topic is required."}), 400
    if status not in ("in_progress", "completed", "paused"):
        return jsonify({"error": "Invalid status."}), 400
    if not (0 <= progress_percent <= 100):
        return jsonify({"error": "Progress must be 0-100."}), 400

    # Upsert
    log = current_user.progress_logs.filter_by(topic=topic).first()
    if log:
        log.status = status
        log.progress_percent = progress_percent
        log.notes = notes
        log.updated_at = datetime.utcnow()
    else:
        log = ProgressLog(
            user_id=current_user.id,
            topic=topic,
            status=status,
            progress_percent=progress_percent,
            notes=notes,
        )
        db.session.add(log)

    db.session.commit()
    return jsonify({"success": True, "id": log.id, "status": log.status})


@progress_bp.route("/api/log/<int:log_id>", methods=["DELETE"])
@login_required
def api_delete_log(log_id):
    """Delete a progress log entry."""
    log = ProgressLog.query.filter_by(id=log_id, user_id=current_user.id).first_or_404()
    db.session.delete(log)
    db.session.commit()
    return jsonify({"success": True})


@progress_bp.route("/api/study-session", methods=["POST"])
@login_required
def api_study_session():
    """Save a completed study timer session."""
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "Study Session").strip()
    duration_minutes = int(data.get("duration_minutes") or 0)
    session_type = data.get("session_type", "focus")
    notes = (data.get("notes") or "").strip()

    if duration_minutes <= 0:
        return jsonify({"error": "Duration must be positive."}), 400

    session = StudySession(
        user_id=current_user.id,
        topic=topic,
        duration_minutes=duration_minutes,
        session_type=session_type,
        notes=notes,
    )
    db.session.add(session)
    db.session.commit()
    return jsonify({"success": True, "id": session.id})


@progress_bp.route("/api/study-sessions")
@login_required
def api_study_sessions():
    """Get paginated study sessions."""
    page = request.args.get("page", 1, type=int)
    sessions = current_user.study_sessions.order_by(
        StudySession.created_at.desc()
    ).paginate(page=page, per_page=20, error_out=False)
    return jsonify({
        "sessions": [{
            "id": s.id,
            "topic": s.topic,
            "duration_minutes": s.duration_minutes,
            "session_type": s.session_type,
            "created_at": s.created_at.isoformat(),
        } for s in sessions.items],
        "total": sessions.total,
        "pages": sessions.pages,
    })
