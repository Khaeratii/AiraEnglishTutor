# backend/app.py
import io
import json
import hashlib
import os
import re
import secrets
import smtplib
import ssl
import tempfile
import time
import uuid
from datetime import datetime, timedelta
from email.message import EmailMessage
from functools import wraps

import pytz
from flask import Flask, jsonify, redirect, request, send_file, send_from_directory
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from google import genai
from google.genai import types
from gtts import gTTS
from pydub import AudioSegment
import speech_recognition as sr
from sqlalchemy import and_, func

from .analytics import (
    CEFR_LEVEL_MAP,
    build_cefr_snapshot,
    build_evidence_package,
    calculate_long_term_stats,
    extract_learning_events,
    generate_teacher_report,
    get_today_range,
    normalize_cefr_level,
    tokenize_user_words,
)
from .config import API_KEY, APP_TIMEZONE, MODEL_NAME, SYSTEM_INSTRUCTIONS
from .database import SessionLocal, init_db
from .learning import adapt_conversation_prompt, build_learning_profile, normalize_mistake, upsert_recurring_mistake
from .models import (
    Conversation,
    DailyAnalysis,
    LearningEvent,
    LearningProfile,
    Message,
    PasswordResetToken,
    RecurringMistake,
    User,
    UserProgress,
)

# ============================================
# APP SETUP
# ============================================

app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400
app.config['SESSION_COOKIE_NAME'] = 'aira_session'

CORS(
    app,
    supports_credentials=True,
    origins=['http://localhost:5000', 'http://127.0.0.1:5000'],
    allow_headers=['Content-Type', 'Authorization'],
    methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
)

bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'
login_manager.session_protection = 'basic'


@login_manager.user_loader
def load_user(user_id):
    session = get_db()
    try:
        return session.get(User, int(user_id))
    finally:
        session.close()


@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Authentication required'}), 401
    return redirect('/login')


client = genai.Client(api_key=API_KEY)
AI_MAX_ATTEMPTS = 3
AI_RETRY_DELAYS = (0.5, 1.0)
print(f"🚀 Model: {MODEL_NAME}")
print(f"🌏 Timezone: {APP_TIMEZONE}")


# ============================================
# DATABASE HELPERS
# ============================================

def get_db():
    return SessionLocal()


def timezone_now():
    return datetime.now(pytz.timezone(APP_TIMEZONE)).isoformat()


def sync_user_level_from_snapshot(session, user_id, snapshot):
    if not snapshot:
        return None
    user = session.get(User, user_id)
    if not user:
        return None
    level_code = normalize_cefr_level(snapshot.get('cefr_level') or user.level or 'A1')
    level_name = snapshot.get('level_name') or snapshot.get('level_label') or CEFR_LEVEL_MAP.get(level_code, 'Beginner')
    user.level = level_code
    user.level_label = level_name
    user.overall_score = int(snapshot.get('overall_score') or user.overall_score or 0)
    session.commit()
    return {'cefr_level': level_code, 'level_name': level_name, 'level_label': level_name, 'overall_score': user.overall_score}


def _serialize_learning_mistake(item):
    if not item:
        return {}
    return {
        'id': item.id,
        'category': item.category,
        'pattern': item.pattern,
        'pattern_key': item.pattern_key,
        'incorrect': item.incorrect,
        'correct': item.correct,
        'explanation': item.explanation,
        'occurrence_count': item.occurrence_count,
        'first_detected': item.first_detected,
        'last_detected': item.last_detected,
        'status': item.status,
        'example_sentences': json.loads(item.example_sentences or '[]'),
        'learner_improved': item.learner_improved,
        'needs_retesting': item.needs_retesting,
    }


def _sync_user_learning_profile(session, user_id):
    mistakes = session.query(RecurringMistake).filter(RecurringMistake.user_id == user_id).order_by(RecurringMistake.occurrence_count.desc(), RecurringMistake.updated_at.desc()).all()
    payload = build_learning_profile([
        _serialize_learning_mistake(mistake)
        for mistake in mistakes
    ])

    existing = session.query(LearningProfile).filter(LearningProfile.user_id == user_id).first()
    profile_payload = json.dumps(payload)
    now = timezone_now()
    if existing:
        existing.current_level = payload.get('current_level', existing.current_level)
        existing.strengths = json.dumps(payload.get('strengths', []))
        existing.needs_practice = json.dumps(payload.get('needs_practice', []))
        existing.focus_areas = json.dumps(payload.get('focus_areas', []))
        existing.recurring_patterns = json.dumps(payload.get('recurring_patterns', []))
        existing.preferred_practice = json.dumps(payload.get('preferred_practice', []))
        existing.profile_data = profile_payload
        existing.updated_at = now
    else:
        session.add(LearningProfile(
            user_id=user_id,
            current_level=payload.get('current_level', 'Emerging'),
            strengths=json.dumps(payload.get('strengths', [])),
            needs_practice=json.dumps(payload.get('needs_practice', [])),
            focus_areas=json.dumps(payload.get('focus_areas', [])),
            recurring_patterns=json.dumps(payload.get('recurring_patterns', [])),
            preferred_practice=json.dumps(payload.get('preferred_practice', [])),
            profile_data=profile_payload,
            created_at=now,
            updated_at=now,
        ))
    session.flush()
    return payload


def _save_recurring_mistake(session, user_id, user_message):
    normalized = normalize_mistake(user_message)
    if not normalized:
        return None

    existing = session.query(RecurringMistake).filter(
        RecurringMistake.user_id == user_id,
        RecurringMistake.pattern_key == normalized['pattern_key'],
    ).first()

    serialized_existing = {
        **_serialize_learning_mistake(existing),
    } if existing else {}
    merged = upsert_recurring_mistake(serialized_existing, user_message)
    now = timezone_now()

    if existing:
        existing.category = merged.get('category', existing.category)
        existing.pattern = merged.get('pattern', existing.pattern)
        existing.pattern_key = merged.get('pattern_key', existing.pattern_key)
        existing.incorrect = merged.get('incorrect', existing.incorrect)
        existing.correct = merged.get('correct', existing.correct)
        existing.explanation = merged.get('explanation', existing.explanation)
        existing.occurrence_count = merged.get('occurrence_count', existing.occurrence_count)
        existing.first_detected = merged.get('first_detected', existing.first_detected)
        existing.last_detected = merged.get('last_detected', existing.last_detected)
        existing.status = merged.get('status', existing.status)
        existing.example_sentences = json.dumps(merged.get('example_sentences', []))
        existing.learner_improved = merged.get('learner_improved', existing.learner_improved)
        existing.needs_retesting = merged.get('needs_retesting', existing.needs_retesting)
        existing.updated_at = now
        return _serialize_learning_mistake(existing)

    new_recurring = RecurringMistake(
        user_id=user_id,
        category=merged.get('category', 'grammar'),
        pattern=merged.get('pattern', 'common learner pattern'),
        pattern_key=merged.get('pattern_key', normalized['pattern_key']),
        incorrect=merged.get('incorrect', normalized['incorrect']),
        correct=merged.get('correct', normalized['correct']),
        explanation=merged.get('explanation', normalized['explanation']),
        occurrence_count=merged.get('occurrence_count', 1),
        first_detected=merged.get('first_detected', now),
        last_detected=merged.get('last_detected', now),
        status=merged.get('status', 'new'),
        example_sentences=json.dumps(merged.get('example_sentences', [user_message])),
        learner_improved=merged.get('learner_improved', False),
        needs_retesting=merged.get('needs_retesting', True),
        created_at=now,
        updated_at=now,
    )
    session.add(new_recurring)
    session.flush()
    return _serialize_learning_mistake(new_recurring)


def as_dict(model_obj):
    if model_obj is None:
        return None
    return {column.name: getattr(model_obj, column.name) for column in model_obj.__table__.columns}

def _provider_error_details(error):
    """Extract safe status information from a Gemini SDK exception."""
    status_code = getattr(error, 'status_code', None) or getattr(error, 'code', None)
    status_name = str(getattr(error, 'status', '') or '').upper()
    error_text = str(error).upper()
    if status_code is None:
        for code in (503, 429, 401, 403, 404, 400):
            if str(code) in error_text:
                status_code = code
                break
    return status_code, status_name, error_text

def _is_retryable_provider_error(error):
    status_code, status_name, error_text = _provider_error_details(error)
    return (
        status_code in (429, 500, 502, 503, 504)
        or status_name in {'UNAVAILABLE', 'RESOURCE_EXHAUSTED', 'DEADLINE_EXCEEDED'}
        or any(marker in error_text for marker in ('TIMEOUT', 'TIMED OUT', 'CONNECTION RESET'))
    )

def generate_chat_response(context, user_message):
    """Call Gemini with bounded retries for transient provider failures."""
    last_error = None
    for attempt in range(1, AI_MAX_ATTEMPTS + 1):
        print(f'[AI] Chat request started provider=Gemini model={MODEL_NAME} attempt={attempt}')
        try:
            chat_session = client.chats.create(
                model=MODEL_NAME,
                config=types.GenerateContentConfig(system_instruction=context),
            )
            response = chat_session.send_message(user_message)
            print(f'[AI] Chat response status=200 attempt={attempt}')
            return response.text
        except Exception as error:
            last_error = error
            status_code, status_name, _ = _provider_error_details(error)
            print(f'[AI] Chat response status={status_code or status_name or "error"} attempt={attempt}')
            if not _is_retryable_provider_error(error) or attempt == AI_MAX_ATTEMPTS:
                raise
            delay = AI_RETRY_DELAYS[min(attempt - 1, len(AI_RETRY_DELAYS) - 1)]
            print(f'[AI] Retry scheduled delay={delay}s')
            time.sleep(delay)
    raise last_error


init_db()


def login_required_api(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)

    return decorated


# ============================================
# AUTH ROUTES
# ============================================

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.json or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    confirm = data.get('confirm_password', '')

    if not all([name, email, password, confirm]):
        return jsonify({'error': 'All fields required'}), 400
    if password != confirm:
        return jsonify({'error': 'Passwords do not match'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be 6+ characters'}), 400

    session = get_db()
    try:
        existing = session.query(User).filter(User.email == email).first()
        if existing:
            return jsonify({'error': 'Email already registered'}), 400

        hashed = bcrypt.generate_password_hash(password).decode('utf-8')
        now = timezone_now()
        user = User(name=name, email=email, password=hashed, created_at=now, level='A1', level_label='Beginner', overall_score=0)
        session.add(user)
        session.flush()
        session.add(UserProgress(user_id=user.id, turns=0, updated_at=now))
        session.commit()
        confirmation_sent = False
        try:
            confirmation_sent = _send_account_confirmation_email(user.name, user.email, user.created_at)
        except Exception as exc:
            print(f'[MAIL] Signup confirmation failed: {exc}')
        return jsonify({
            'message': (
                'Account created. Confirmation email sent.'
                if confirmation_sent
                else "Account created, but we couldn't send the confirmation email."
            ),
            'user_id': user.id,
            'email_sent': confirmation_sent,
        })
    finally:
        session.close()


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    session = get_db()
    try:
        user = session.query(User).filter(User.email == email).first()
        if not user or not bcrypt.check_password_hash(user.password, password):
            return jsonify({'error': 'Invalid email or password'}), 401

        login_user(user, remember=True)
        return jsonify({
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'level': user.level,
                'level_label': user.level_label,
            },
        })
    finally:
        session.close()


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    logout_user()
    return jsonify({'message': 'Logged out'})


@app.route('/api/auth/me', methods=['GET'])
def get_current_user():
    if not current_user.is_authenticated:
        return jsonify({'error': 'Not authenticated'}), 401
    return jsonify({
        'id': current_user.id,
        'name': current_user.name,
        'email': current_user.email,
        'level': current_user.level,
        'level_label': current_user.level_label,
    })


def _hash_reset_token(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def _send_reset_email(recipient, reset_url):
    server = os.getenv('MAIL_SERVER')
    username = os.getenv('MAIL_USERNAME')
    password = os.getenv('MAIL_PASSWORD')
    if not all([server, username, password]):
        print('[MAIL] Reset email not sent: SMTP is not configured')
        return False

    port = int(os.getenv('MAIL_PORT', '587'))
    use_tls = os.getenv('MAIL_USE_TLS', 'true').lower() in {'1', 'true', 'yes'}
    message = EmailMessage()
    message['Subject'] = 'Reset your Aira password'
    message['From'] = username
    message['To'] = recipient
    message.set_content(
        'Aira password reset\n\n'
        f'Use this link to reset your password: {reset_url}\n\n'
        'This link expires in 60 minutes and can only be used once. '
        'If you did not request this, you can ignore this email.'
    )
    with smtplib.SMTP(server, port, timeout=15) as smtp:
        if use_tls:
            smtp.starttls(context=ssl.create_default_context())
        smtp.login(username, password)
        smtp.send_message(message)
    return True

def _send_account_confirmation_email(user_name, recipient, created_at):
    server = os.getenv('MAIL_SERVER')
    username = os.getenv('MAIL_USERNAME')
    password = os.getenv('MAIL_PASSWORD')
    if not all([server, username, password]):
        print('[MAIL] Signup confirmation not sent: SMTP is not configured')
        return False

    base_url = os.getenv('APP_BASE_URL', 'http://127.0.0.1:5000').rstrip('/')
    message = EmailMessage()
    message['Subject'] = 'Welcome to Aira'
    message['From'] = os.getenv('MAIL_FROM', username)
    message['To'] = recipient
    message.set_content(
        f'Hi {user_name},\n\n'
        'Your Aira account has been created successfully.\n\n'
        f'Account email: {recipient}\n'
        f'Registered: {created_at}\n\n'
        f'Open Aira: {base_url}/login\n\n'
        'For your security, Aira never sends or displays your password. '
        'If you did not create this account, please contact support.'
    )
    port = int(os.getenv('MAIL_PORT', '587'))
    use_tls = os.getenv('MAIL_USE_TLS', 'true').lower() in {'1', 'true', 'yes'}
    with smtplib.SMTP(server, port, timeout=15) as smtp:
        if use_tls:
            smtp.starttls(context=ssl.create_default_context())
        smtp.login(username, password)
        smtp.send_message(message)
    return True


@app.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    generic_response = {
        'success': True,
        'message': "If an account with that email exists, we've sent instructions to reset your password.",
    }
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        return jsonify(generic_response)

    session = get_db()
    try:
        user = session.query(User).filter(User.email == email).first()
        if not user:
            return jsonify(generic_response)
        now = datetime.now(pytz.timezone(APP_TIMEZONE))
        recent = session.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.created_at >= (now - timedelta(minutes=1)).isoformat(),
            PasswordResetToken.used_at.is_(None),
        ).first()
        if recent:
            return jsonify(generic_response)

        raw_token = secrets.token_urlsafe(32)
        token = PasswordResetToken(
            user_id=user.id,
            token_hash=_hash_reset_token(raw_token),
            expires_at=(now + timedelta(minutes=60)).isoformat(),
            created_at=now.isoformat(),
        )
        session.add(token)
        session.commit()
        base_url = os.getenv('APP_BASE_URL', request.host_url.rstrip('/')).rstrip('/')
        reset_url = f'{base_url}/reset-password/{raw_token}'
        try:
            _send_reset_email(user.email, reset_url)
        except Exception as exc:
            session.query(PasswordResetToken).filter(PasswordResetToken.id == token.id).delete()
            session.commit()
        return jsonify(generic_response)
    finally:
        session.close()


@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    data = request.json or {}
    raw_token = data.get('token', '')
    password = data.get('password', '')
    confirm = data.get('confirm_password', '')
    if not raw_token:
        return jsonify({'success': False, 'message': 'This reset link is invalid.'}), 400
    if len(password) < 6:
        return jsonify({'success': False, 'message': 'Password must be 6+ characters.'}), 400
    if password != confirm:
        return jsonify({'success': False, 'message': 'Passwords do not match.'}), 400

    session = get_db()
    try:
        token = session.query(PasswordResetToken).filter(
            PasswordResetToken.token_hash == _hash_reset_token(raw_token),
        ).first()
        if not token:
            return jsonify({'success': False, 'message': 'This reset link is invalid.'}), 400
        if token.used_at:
            return jsonify({'success': False, 'message': 'This reset link is no longer valid.'}), 400
        if datetime.now(pytz.timezone(APP_TIMEZONE)).isoformat() >= token.expires_at:
            return jsonify({'success': False, 'message': 'This reset link has expired.'}), 400

        user = session.get(User, token.user_id)
        user.password = bcrypt.generate_password_hash(password).decode('utf-8')
        token.used_at = datetime.now(pytz.timezone(APP_TIMEZONE)).isoformat()
        session.commit()
        return jsonify({'success': True, 'message': 'Your password has been reset successfully. You can now log in.'})
    finally:
        session.close()


@app.route('/api/profile', methods=['GET'])
@login_required_api
def profile():
    session = get_db()
    try:
        conversations = session.query(Conversation).filter(
            Conversation.user_id == current_user.id,
            Conversation.deleted == False,
        ).count()
        messages = session.query(Message).filter(Message.user_id == current_user.id).count()
        events = session.query(LearningEvent).filter(LearningEvent.user_id == current_user.id).count()
        progress = session.query(UserProgress).filter(UserProgress.user_id == current_user.id).first()
        profile_payload = _sync_user_learning_profile(session, current_user.id)

        # Use the same canonical proficiency used by statistics.
        stats_data = {
            'overall_score': current_user.overall_score or 0,
            'total_turns': progress.turns if progress else 0,
        }
        canonical = build_cefr_snapshot(stats_data['overall_score'], evidence_count=max(1, stats_data['total_turns']))
        sync_user_level_from_snapshot(session, current_user.id, {
            'cefr_level': canonical['cefr_level'],
            'level_name': canonical['level_name'],
            'overall_score': stats_data['overall_score'],
        })

        return jsonify({
            'id': current_user.id,
            'name': current_user.name,
            'email': current_user.email,
            'created_at': current_user.created_at,
            'level': canonical['cefr_level'],
            'level_label': canonical['level_name'],
            'canonical_proficiency': canonical,
            'learning': {
                'conversations': conversations,
                'messages': messages,
                'learning_events': events,
                'turns': progress.turns if progress else 0,
            },
            'learning_profile': profile_payload,
        })
    finally:
        session.close()


@app.route('/api/learning/profile', methods=['GET'])
@login_required_api
def learning_profile():
    session = get_db()
    try:
        payload = _sync_user_learning_profile(session, current_user.id)
        return jsonify({'success': True, 'profile': payload})
    finally:
        session.close()


@app.route('/api/profile/change-password', methods=['POST'])
@login_required_api
def change_password():
    data = request.json or {}
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    confirm = data.get('confirm_password', '')
    if not bcrypt.check_password_hash(current_user.password, current_password):
        return jsonify({'success': False, 'message': 'Current password is incorrect.'}), 400
    if len(new_password) < 6:
        return jsonify({'success': False, 'message': 'New password must be 6+ characters.'}), 400
    if new_password != confirm:
        return jsonify({'success': False, 'message': 'New passwords do not match.'}), 400
    session = get_db()
    try:
        user = session.get(User, current_user.id)
        user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        session.commit()
        return jsonify({'success': True, 'message': 'Your password has been changed successfully.'})
    finally:
        session.close()


# ============================================
# FRONTEND ROUTES
# ============================================

@app.route('/')
def serve_index():
    if current_user.is_authenticated:
        return send_from_directory(app.static_folder, 'index.html')
    return send_from_directory(app.static_folder, 'login.html')


@app.route('/login')
def login_page():
    return send_from_directory(app.static_folder, 'login.html')


@app.route('/signup')
def signup_page():
    return send_from_directory(app.static_folder, 'signup.html')


@app.route('/forgot-password')
def forgot_password_page():
    return send_from_directory(app.static_folder, 'forgot-password.html')


@app.route('/reset-password/<token>')
def reset_password_page(token):
    return send_from_directory(app.static_folder, 'reset-password.html')


@app.route('/history')
def history_page():
    if not current_user.is_authenticated:
        return redirect('/login')
    return send_from_directory(app.static_folder, 'history.html')


@app.route('/profile')
def profile_page():
    if not current_user.is_authenticated:
        return redirect('/login')
    return send_from_directory(app.static_folder, 'profile.html')


@app.route('/statistics')
def statistics_page():
    if not current_user.is_authenticated:
        return redirect('/login')
    return send_from_directory(app.static_folder, 'statistics.html')


@app.route('/analysis')
def analysis_page():
    if not current_user.is_authenticated:
        return redirect('/login')
    return send_from_directory(app.static_folder, 'analysis.html')


@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)


# ============================================
# CONVERSATION MANAGEMENT
# ============================================

@app.route('/api/conversations', methods=['GET'])
@login_required_api
def list_conversations():
    session = get_db()
    try:
        rows = session.query(Conversation).filter(
            Conversation.user_id == current_user.id,
            Conversation.deleted == False,
        ).order_by(Conversation.updated_at.desc()).limit(50).all()
        return jsonify({'conversations': [as_dict(r) for r in rows]})
    finally:
        session.close()


@app.route('/api/conversations', methods=['POST'])
@login_required_api
def create_conversation():
    data = request.json or {}
    conv_id = str(uuid.uuid4())
    now = timezone_now()
    title = data.get('title', 'New Conversation')

    session = get_db()
    try:
        session.add(Conversation(id=conv_id, user_id=current_user.id, title=title, created_at=now, updated_at=now, deleted=False, turn_count=0))
        session.commit()
        return jsonify({'conversation_id': conv_id, 'title': title})
    finally:
        session.close()


@app.route('/api/conversations/<conv_id>', methods=['GET'])
@login_required_api
def get_conversation(conv_id):
    session = get_db()
    try:
        conv = session.query(Conversation).filter(
            Conversation.id == conv_id,
            Conversation.user_id == current_user.id,
            Conversation.deleted == False,
        ).first()
        if not conv:
            return jsonify({'error': 'Not found'}), 404

        msgs = session.query(Message).filter(Message.conversation_id == conv_id).order_by(Message.timestamp.asc()).all()
        return jsonify({
            'conversation': as_dict(conv),
            'messages': [as_dict(m) for m in msgs],
        })
    finally:
        session.close()


@app.route('/api/conversations/<conv_id>', methods=['DELETE'])
@login_required_api
def delete_conversation(conv_id):
    session = get_db()
    try:
        conv = session.query(Conversation).filter(
            Conversation.id == conv_id,
            Conversation.user_id == current_user.id,
        ).first()
        if not conv:
            return jsonify({'error': 'Not found'}), 404

        conv.deleted = True
        conv.updated_at = timezone_now()
        session.commit()
        return jsonify({'message': 'Conversation deleted'})
    finally:
        session.close()


@app.route('/api/conversations/reset', methods=['POST'])
@login_required_api
def reset_conversation():
    """Archive the active conversation and start a fresh session."""
    data = request.json or {}
    current_id = data.get('current_conversation_id')
    new_id = str(uuid.uuid4())
    now = timezone_now()

    session = get_db()
    try:
        if current_id:
            session.query(Conversation).filter(
                Conversation.id == current_id,
                Conversation.user_id == current_user.id,
                Conversation.deleted == False,
            ).update({'updated_at': now})
        session.add(Conversation(id=new_id, user_id=current_user.id, title='New Conversation', created_at=now, updated_at=now, deleted=False, turn_count=0))
        session.commit()
        return jsonify({'success': True, 'conversation_id': new_id})
    finally:
        session.close()


# ============================================
# CHAT (PRESERVED - DO NOT CHANGE LOGIC)
# ============================================

@app.route('/api/chat', methods=['POST'])
@login_required_api
def chat():
    data = request.json or {}
    user_message = data.get('message', '').strip()
    conv_id = data.get('conversation_id')
    user_id = current_user.id

    if not user_message:
        return jsonify({'error': 'No message'}), 400

    session = get_db()
    try:
        if not conv_id:
            conv_id = str(uuid.uuid4())
            now = timezone_now()
            title = user_message[:40] + ('...' if len(user_message) > 40 else '')
            session.add(Conversation(id=conv_id, user_id=user_id, title=title, created_at=now, updated_at=now, deleted=False, turn_count=0))
            session.commit()
        else:
            existing = session.query(Conversation).filter(
                Conversation.id == conv_id,
                Conversation.user_id == user_id,
                Conversation.deleted == False,
            ).first()
            if not existing:
                return jsonify({'error': 'Conversation not found'}), 404

        user_level = current_user.level or 'beginner'
        system_instruction = SYSTEM_INSTRUCTIONS.get(user_level, SYSTEM_INSTRUCTIONS['beginner'])
        history = session.query(Message).filter(Message.conversation_id == conv_id).order_by(Message.timestamp.desc()).limit(10).all()
        history = list(reversed(history))

        learning_profile = _sync_user_learning_profile(session, user_id)
        context = system_instruction
        if learning_profile and not learning_profile.get('empty_state'):
            context = adapt_conversation_prompt(
                'general English conversation',
                learning_profile,
            ) + '\n\n' + context
        if history:
            context += "\n\nRecent conversation:\n"
            for item in history:
                role = "User" if item.role == 'user' else "Aira"
                context += f"{role}: {item.content}\n"
            context += "\nNow respond to the user's latest message."

        now = timezone_now()
        user_msg = Message(
            conversation_id=conv_id,
            user_id=user_id,
            role='user',
            content=user_message,
            timestamp=now,
        )
        session.add(user_msg)
        session.commit()

        try:
            ai_response = generate_chat_response(context, user_message)
        except Exception as error:
            session.rollback()
            status_code, status_name, _ = _provider_error_details(error)
            print(f'[AI] Chat failed provider_status={status_code or status_name or "unknown"}')
            if _is_retryable_provider_error(error):
                return jsonify({
                    'success': False,
                    'error': 'AI temporarily unavailable',
                    'message': 'Aira is having trouble reaching the AI service. Your message was saved; please try again in a moment.',
                    'retryable': True,
                    'conversation_id': conv_id,
                }), 503
            if status_code in (401, 403):
                return jsonify({
                    'success': False,
                    'error': 'AI authentication failed',
                    'message': 'Aira cannot reach the AI service configuration right now.',
                    'retryable': False,
                }), 502
            if status_code == 404:
                return jsonify({
                    'success': False,
                    'error': 'AI model unavailable',
                    'message': 'Aira is temporarily unavailable because the configured AI model could not be reached.',
                    'retryable': False,
                }), 502
            print(f'[AI] Chat request failed: {error}')
            return jsonify({
                'success': False,
                'error': 'AI request failed',
                'message': 'Aira could not process that message. Please try again.',
                'retryable': False,
            }), 502

        now = timezone_now()
        session.add(Message(conversation_id=conv_id, user_id=user_id, role='ai', content=ai_response, timestamp=now))

        conversation = session.query(Conversation).filter(Conversation.id == conv_id).first()
        conversation.updated_at = now
        conversation.turn_count = (conversation.turn_count or 0) + 1
        session.commit()

        try:
            events = extract_learning_events(client, MODEL_NAME, user_message)
            now2 = timezone_now()

            for issue in events.get('grammar_issues', []):
                session.add(LearningEvent(
                    user_id=user_id,
                    conversation_id=conv_id,
                    message_id=user_msg.id,
                    event_type='grammar',
                    category=issue.get('category', 'other'),
                    original=issue.get('original', ''),
                    correction=issue.get('correction', ''),
                    explanation=issue.get('explanation', ''),
                    severity=issue.get('severity', 'minor'),
                    confidence=issue.get('confidence', 'medium'),
                    timestamp=now2,
                ))

            for issue in events.get('naturalness_issues', []):
                session.add(LearningEvent(
                    user_id=user_id,
                    conversation_id=conv_id,
                    message_id=user_msg.id,
                    event_type='naturalness',
                    category='unnatural',
                    original=issue.get('original', ''),
                    correction=issue.get('more_natural', ''),
                    explanation=issue.get('explanation', ''),
                    severity='moderate',
                    confidence=issue.get('confidence', 'medium'),
                    timestamp=now2,
                ))

            if events.get('grammar_issues') or events.get('naturalness_issues'):
                for issue in events.get('grammar_issues', []):
                    _save_recurring_mistake(session, user_id, issue.get('original', ''))
                for issue in events.get('naturalness_issues', []):
                    _save_recurring_mistake(session, user_id, issue.get('original', ''))
                _sync_user_learning_profile(session, user_id)

            session.commit()
            print(f"✅ Learning events saved for message {user_msg.id}")
        except Exception as exc:
            session.rollback()
            print(f"⚠️ Event extraction failed: {exc}")

        return jsonify({'response': ai_response, 'conversation_id': conv_id})
    except Exception as exc:
        session.rollback()
        err = str(exc)
        print(f"❌ Chat error: {err}")
        if '429' in err or 'RESOURCE_EXHAUSTED' in err:
            return jsonify({'error': 'Quota exceeded', 'message': 'Daily limit reached'}), 429
        return jsonify({'error': 'AI error', 'message': 'Aira is temporarily unavailable'}), 500
    finally:
        session.close()


# ============================================
# STT (PRESERVED)
# ============================================

@app.route('/api/stt', methods=['POST'])
@login_required_api
def speech_to_text():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio'}), 400

    af = request.files['audio']
    audio_bytes = af.read()

    if len(audio_bytes) < 1000:
        return jsonify({'error': 'Audio too short'}), 400

    temp_audio = None
    try:
        format_by_type = {
            'audio/webm': 'webm',
            'audio/ogg': 'ogg',
            'audio/mp4': 'mp4',
            'audio/m4a': 'mp4',
            'audio/wav': 'wav',
            'audio/x-wav': 'wav',
            'audio/aac': 'aac',
        }
        content_type = (af.mimetype or '').split(';', 1)[0].lower()
        detected_format = format_by_type.get(content_type)
        if not detected_format and af.filename:
            detected_format = os.path.splitext(af.filename)[1].lstrip('.').lower()

        try:
            seg = AudioSegment.from_file(io.BytesIO(audio_bytes), format=detected_format) if detected_format else AudioSegment.from_file(io.BytesIO(audio_bytes))
        except Exception:
            seg = None
            for fallback_format in ['webm', 'mp4', 'ogg', 'opus', 'wav', 'm4a', 'aac']:
                try:
                    seg = AudioSegment.from_file(io.BytesIO(audio_bytes), format=fallback_format)
                    break
                except Exception:
                    continue
            if seg is None:
                return jsonify({'error': 'Unsupported audio format'}), 400

        seg = seg.set_channels(1).set_frame_rate(16000)
        buf = io.BytesIO()
        seg.export(buf, format='wav')
        buf.seek(0)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as f:
            f.write(buf.read())
            temp_audio = f.name

        r = sr.Recognizer()
        r.dynamic_energy_threshold = False
        with sr.AudioFile(temp_audio) as source:
            data = r.record(source)

        if temp_audio and os.path.exists(temp_audio):
            os.unlink(temp_audio)

        text = r.recognize_google(data, language='en-US')
        return jsonify({'text': text})
    except sr.UnknownValueError:
        return jsonify({'error': 'No speech detected. Please speak clearly and try again.'}), 422
    except Exception as e:
        if temp_audio and os.path.exists(temp_audio):
            try:
                os.unlink(temp_audio)
            except Exception:
                pass
        return jsonify({'error': str(e)}), 500


# ============================================
# TTS (PRESERVED)
# ============================================

@app.route('/api/tts', methods=['POST'])
@login_required_api
def text_to_speech():
    data = request.json or {}
    text = data.get('text', '')
    if not text:
        return jsonify({'error': 'No text'}), 400

    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'#{1,6}\s*', '', text)

    try:
        tts = gTTS(text=text.strip(), lang='en', slow=False)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
            tts.save(f.name)
            tf = f.name
        return send_file(tf, mimetype='audio/mpeg', as_attachment=True, download_name='aira.mp3')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# DAILY ANALYSIS (TODAY ONLY)
# ============================================

@app.route('/api/analysis', methods=['POST'])
@login_required_api
def get_daily_analysis():
    """
    Get TODAY's analysis only.
    Timezone-aware. Excludes deleted conversations.
    """
    user_id = current_user.id
    start_iso, end_iso, now_iso = get_today_range(APP_TIMEZONE)

    session = get_db()
    try:
        rows = session.query(Message, Conversation.id.label('conv_id')).join(
            Conversation,
            Message.conversation_id == Conversation.id,
        ).filter(
            Message.user_id == user_id,
            Conversation.deleted == False,
            Message.timestamp >= start_iso,
            Message.timestamp < end_iso,
        ).order_by(Message.timestamp.asc()).all()

        user_messages = []
        for message, conv_id in rows:
            if message.role == 'user':
                user_messages.append({
                    'id': message.id,
                    'role': message.role,
                    'content': message.content,
                    'timestamp': message.timestamp,
                    'conv_id': conv_id,
                })

        if len(user_messages) < 2:
            return jsonify({
                'success': True,
                'has_data': False,
                'message': "You haven't practiced enough today for a meaningful review yet.",
                'today_messages_count': len(user_messages),
            })

        events = session.query(LearningEvent).filter(
            LearningEvent.user_id == user_id,
            LearningEvent.timestamp >= start_iso,
            LearningEvent.timestamp < end_iso,
        ).all()

        msg_analyses = {}
        for event in events:
            mid = event.message_id
            if mid not in msg_analyses:
                msg_analyses[mid] = {'grammar_issues': [], 'naturalness_issues': [], 'vocabulary': {'unique_words': []}, 'conversation': {}}

            if event.event_type == 'grammar':
                msg_analyses[mid]['grammar_issues'].append({
                    'category': event.category,
                    'original': event.original,
                    'correction': event.correction,
                    'explanation': event.explanation,
                    'severity': event.severity,
                })
            elif event.event_type == 'naturalness':
                msg_analyses[mid]['naturalness_issues'].append({
                    'original': event.original,
                    'more_natural': event.correction,
                    'explanation': event.explanation,
                })

        structured = []
        for m in user_messages:
            structured.append({
                'role': 'user',
                'text': m['content'],
                'timestamp': m['timestamp'],
                'analysis': msg_analyses.get(m['id'], {
                    'grammar_issues': [],
                    'naturalness_issues': [],
                    'vocabulary': {'unique_words': []},
                    'conversation': {},
                }),
            })

        evidence = build_evidence_package(structured, APP_TIMEZONE)
        if not evidence:
            return jsonify({
                'success': True,
                'has_data': False,
                'message': 'No data to analyze today.',
            })

        report = generate_teacher_report(client, MODEL_NAME, evidence)
        if not report:
            return jsonify({
                'success': False,
                'has_data': True,
                'message': 'Could not generate report. Please try again.',
                'evidence': evidence,
            }), 503

        conv_ids = list({m['conv_id'] for m in user_messages})
        today = datetime.now(pytz.timezone(APP_TIMEZONE)).strftime('%Y-%m-%d')
        existing = session.query(DailyAnalysis).filter(
            DailyAnalysis.user_id == user_id,
            DailyAnalysis.analysis_date == today,
        ).first()
        if existing:
            existing.timezone = APP_TIMEZONE
            existing.conversation_ids = json.dumps(conv_ids)
            existing.analysis_data = json.dumps(report)
            existing.created_at = timezone_now()
        else:
            session.add(DailyAnalysis(
                user_id=user_id,
                analysis_date=today,
                timezone=APP_TIMEZONE,
                conversation_ids=json.dumps(conv_ids),
                analysis_data=json.dumps(report),
                created_at=timezone_now(),
            ))
        session.commit()

        return jsonify({
            'success': True,
            'has_data': True,
            'date': today,
            'timezone': APP_TIMEZONE,
            'conversations_count': len(conv_ids),
            'messages_count': len(user_messages),
            'report': report,
            'evidence': {
                'grammar_patterns': evidence['grammar_patterns'],
                'naturalness_examples': evidence['naturalness_examples'],
                'vocabulary': evidence['vocabulary'],
                'conversation_ability': evidence['conversation_ability'],
            },
        })
    finally:
        session.close()


# ============================================
# STATISTICS (LONG-TERM)
# ============================================

@app.route('/api/stats', methods=['GET'])
@login_required_api
def get_long_term_stats():
    """Get long-term statistics from ALL valid data."""
    user_id = current_user.id

    session = get_db()
    try:
        total_convs = session.query(Conversation).filter(
            Conversation.user_id == user_id,
            Conversation.deleted == False,
        ).count()

        total_turns = session.query(Message).join(
            Conversation,
            Message.conversation_id == Conversation.id,
        ).filter(
            Message.user_id == user_id,
            Conversation.deleted == False,
            Message.role == 'user',
        ).count()

        msgs = session.query(Message).join(
            Conversation,
            Message.conversation_id == Conversation.id,
        ).filter(
            Message.user_id == user_id,
            Conversation.deleted == False,
            Message.role == 'user',
        ).all()
        events = session.query(LearningEvent).filter(
            LearningEvent.user_id == user_id,
        ).all()

        user_messages = [
            {
                'role': m.role,
                'content': m.content,
                'conversation_id': m.conversation_id,
            }
            for m in msgs
        ]

        learning_events = [
            {
                'event_type': ev.event_type,
                'category': ev.category,
            }
            for ev in events
        ]

        stats = calculate_long_term_stats(
            conversations=[{'id': conv.id, 'turn_count': conv.turn_count or 0} for conv in session.query(Conversation).filter(Conversation.user_id == user_id, Conversation.deleted == False).all()],
            user_messages=user_messages,
            learning_events=learning_events,
        )
        total_words = sum(len(tokenize_user_words(m.content)) for m in msgs)
        if not stats or not stats.get('has_enough_data'):
            fallback_snapshot = build_cefr_snapshot(0, evidence_count=max(1, total_turns))
            sync_user_level_from_snapshot(session, user_id, {
                'cefr_level': fallback_snapshot['cefr_level'],
                'level_name': fallback_snapshot['level_name'],
                'overall_score': 0,
            })
            return jsonify({
                'has_enough_data': False,
                'total_conversations': total_convs,
                'total_turns': total_turns,
                'message': 'Keep practicing! Complete at least 5 conversations to unlock statistics.',
                'canonical_proficiency': fallback_snapshot,
                'cefr_level': {'level': fallback_snapshot['cefr_level'], 'label': fallback_snapshot['level_name']},
                'total_words': total_words,
                'avg_words_per_turn': round(total_words / total_turns, 1) if total_turns else 0,
            })

        stats['total_conversations'] = total_convs
        stats['total_turns'] = total_turns
        stats['total_words'] = total_words
        stats['avg_words_per_turn'] = round(total_words / total_turns, 1) if total_turns else 0
        sync_user_level_from_snapshot(session, user_id, {
            'cefr_level': stats['cefr_level']['level'],
            'level_name': stats['cefr_level']['label'],
            'overall_score': stats['overall_score'],
        })
        return jsonify(stats)
    finally:
        session.close()


# ============================================
# LEGACY STATS (for compatibility)
# ============================================

@app.route('/api/stats/simple', methods=['GET'])
@login_required_api
def get_simple_stats():
    user_id = current_user.id
    session = get_db()
    try:
        total = session.query(Message).join(
            Conversation,
            Message.conversation_id == Conversation.id,
        ).filter(
            Message.user_id == user_id,
            Conversation.deleted == False,
        ).count()
        return jsonify({'total': total, 'avg_user': 0, 'avg_ai': 0})
    finally:
        session.close()


# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not found'}), 404
    return send_from_directory(app.static_folder, 'login.html')


@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal error'}), 500


# ============================================
# RUN
# ============================================

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🚀 AIRA - English Conversation Partner")
    print("=" * 60)
    print(f"📱 http://localhost:5000")
    print(f"🤖 Model: {MODEL_NAME}")
    print(f"🌏 Timezone: {APP_TIMEZONE}")
    print("=" * 60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
