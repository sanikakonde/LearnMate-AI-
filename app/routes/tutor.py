"""
LearnMate AI – AI Tutor Routes
Domain-validated, Granite-powered AI tutor with conversation history.
"""
import json
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import db
from app.models import ChatSession, ChatMessage

logger = logging.getLogger(__name__)
tutor_bp = Blueprint("tutor", __name__, url_prefix="/tutor")


@tutor_bp.route("/")
@login_required
def index():
    sessions = current_user.chat_sessions.order_by(ChatSession.updated_at.desc()).limit(20).all()
    active_session = sessions[0] if sessions else None
    messages = []
    if active_session:
        messages = active_session.messages.order_by(ChatMessage.created_at.asc()).all()
    return render_template(
        "tutor/index.html",
        sessions=sessions,
        active_session=active_session,
        messages=messages,
    )


@tutor_bp.route("/session/<int:session_id>")
@login_required
def session(session_id):
    chat_session = ChatSession.query.filter_by(
        id=session_id, user_id=current_user.id
    ).first_or_404()
    sessions = current_user.chat_sessions.order_by(ChatSession.updated_at.desc()).limit(20).all()
    messages = chat_session.messages.order_by(ChatMessage.created_at.asc()).all()
    return render_template(
        "tutor/index.html",
        sessions=sessions,
        active_session=chat_session,
        messages=messages,
    )


@tutor_bp.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    """Main chat endpoint — classifies domain then calls Granite."""
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    session_id = data.get("session_id")

    if not question:
        return jsonify({"error": "Question is required."}), 400
    if len(question) > 4000:
        return jsonify({"error": "Question too long (max 4000 characters)."}), 400

    # --- Domain Classification ---
    try:
        from app.services.ai_service import classify_domain
        domain_result = classify_domain(question)
        if not domain_result.get("is_tech_domain", True):
            return jsonify({
                "response": (
                    "I'm LearnMate AI, your technology learning assistant. "
                    "I can help only with programming, AI, software development, cloud computing, "
                    "cybersecurity, data science, career guidance, learning roadmaps and other "
                    "technology-related topics. I cannot answer questions outside my learning domain."
                ),
                "is_off_topic": True,
                "session_id": session_id,
            })
    except Exception as exc:
        logger.warning("Domain classification error: %s", exc)

    # --- Get or Create Chat Session ---
    chat_session = None
    if session_id:
        chat_session = ChatSession.query.filter_by(
            id=session_id, user_id=current_user.id
        ).first()

    if not chat_session:
        # No session at all — create one with a placeholder; title set below
        chat_session = ChatSession(user_id=current_user.id, title="New Conversation")
        db.session.add(chat_session)
        db.session.flush()

    # --- Generate title on the FIRST user message ---
    # Fires whether the session was just created or was pre-created by
    # /api/new-session. Condition: title is still the default AND no
    # user messages have been saved yet for this session.
    generated_title = None
    _is_default_title = chat_session.title in ("New Conversation", "", None)
    _has_no_messages = not chat_session.messages.filter_by(role="user").first()
    if _is_default_title and _has_no_messages:
        from app.services.ai_service import generate_chat_title
        generated_title = generate_chat_title(question)
        chat_session.title = generated_title

    # --- Save user message ---
    user_msg = ChatMessage(session_id=chat_session.id, role="user", content=question)
    db.session.add(user_msg)

    # --- Build conversation history ---
    history = []
    past_messages = chat_session.messages.order_by(ChatMessage.created_at.asc()).all()
    for msg in past_messages[-20:]:
        history.append({"role": msg.role, "content": msg.content})

    # --- Get AI response ---
    try:
        from app.services.ai_service import get_tutor_response
        user_profile = {
            "name": current_user.get_display_name(),
            "career_goal": current_user.career_goal or "Software Engineer",
            "skill_level": current_user.current_skill_level or "beginner",
            "interests": current_user.interests or "Technology",
        }
        ai_response = get_tutor_response(question, history, user_profile)
    except Exception as exc:
        logger.error("Tutor response error: %s", exc)
        return jsonify({"error": f"AI service error: {str(exc)}"}), 500

    # --- Save AI response ---
    ai_msg = ChatMessage(session_id=chat_session.id, role="assistant", content=ai_response)
    db.session.add(ai_msg)
    chat_session.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "response": ai_response,
        "session_id": chat_session.id,
        "title": generated_title,   # None on follow-up messages; title string on first message
        "is_off_topic": False,
    })


@tutor_bp.route("/api/new-session", methods=["POST"])
@login_required
def new_session():
    """Create a new chat session."""
    session = ChatSession(user_id=current_user.id, title="New Conversation")
    db.session.add(session)
    db.session.commit()
    return jsonify({"session_id": session.id, "title": session.title})


@tutor_bp.route("/api/delete-session/<int:session_id>", methods=["DELETE"])
@login_required
def delete_session(session_id):
    """Delete a chat session."""
    chat_session = ChatSession.query.filter_by(
        id=session_id, user_id=current_user.id
    ).first_or_404()
    db.session.delete(chat_session)
    db.session.commit()
    return jsonify({"success": True})
