# backend/analytics.py
"""
Aira Analytics Engine
- Structured extraction of learning events
- Timezone-aware daily analysis
- Long-term statistics calculation
"""

import json
import time
import re
from datetime import datetime, timedelta
from collections import Counter
import pytz


CEFR_LEVEL_MAP = {
    'A1': 'Beginner',
    'A2': 'Elementary',
    'B1': 'Intermediate',
    'B2': 'Upper-Intermediate',
    'C1': 'Advanced',
    'C2': 'Proficient',
}


def normalize_cefr_level(level):
    code = (level or 'A1').upper().strip()
    if code not in CEFR_LEVEL_MAP:
        return 'A1'
    return code


def build_cefr_snapshot(score, evidence_count=0, confidence_hint='moderate'):
    """Return a single canonical proficiency snapshot shared by profile and stats."""
    score = max(0, min(100, int(score or 0)))
    if evidence_count < 3:
        level_code = 'A1'
        level_name = CEFR_LEVEL_MAP['A1']
        confidence = 'limited'
    elif score >= 85:
        level_code = 'C1'
        level_name = CEFR_LEVEL_MAP['C1']
        confidence = 'strong' if evidence_count >= 8 else 'moderate'
    elif score >= 75:
        level_code = 'B2'
        level_name = CEFR_LEVEL_MAP['B2']
        confidence = 'strong' if evidence_count >= 8 else 'moderate'
    elif score >= 65:
        level_code = 'B1'
        level_name = CEFR_LEVEL_MAP['B1']
        confidence = 'moderate' if evidence_count >= 5 else 'limited'
    elif score >= 55:
        level_code = 'A2'
        level_name = CEFR_LEVEL_MAP['A2']
        confidence = 'moderate' if evidence_count >= 5 else 'limited'
    else:
        level_code = 'A1'
        level_name = CEFR_LEVEL_MAP['A1']
        confidence = 'moderate' if evidence_count >= 5 else 'limited'

    if confidence_hint and confidence_hint in {'limited', 'moderate', 'strong'}:
        confidence = confidence_hint if evidence_count >= 3 else 'limited'

    return {
        'cefr_level': level_code,
        'level_name': level_name,
        'level_label': level_name,
        'confidence': confidence,
        'evidence_count': int(evidence_count),
        'assessment_version': '1.0',
    }


def tokenize_user_words(text):
    """Normalize and tokenize user-written English for analytics."""
    if text is None:
        return []
    normalized = re.sub(r"[\u2019\']", "'", str(text))
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9'\s]", ' ', normalized)
    normalized = re.sub(r"\s+", ' ', normalized).strip()
    if not normalized:
        return []
    tokens = []
    for token in normalized.split():
        token = token.strip("'")
        if not token or token.isdigit():
            continue
        if token in {'i', 'im', 'ive', 'youre', 'dont', 'doesnt', 'isnt', 'arent', 'wasnt', 'werent'}:
            tokens.append(token)
            continue
        tokens.append(token)
    return tokens


def normalize_word_count(content):
    return len(tokenize_user_words(content))


def build_user_activity_snapshot(user_messages):
    """Return a real statistics snapshot derived from actual user text."""
    if not user_messages:
        return {
            'total_conversations': 0,
            'total_turns': 0,
            'total_words': 0,
            'avg_words_per_turn': 0,
            'unique_words': 0,
            'vocabulary_tokens': [],
            'conversation_ids': [],
        }

    conversation_ids = []
    total_turns = 0
    total_words = 0
    tokens = []

    for message in user_messages:
        if not message or not isinstance(message, dict):
            continue
        if message.get('role') != 'user':
            continue
        conv_id = message.get('conversation_id')
        if conv_id and conv_id not in conversation_ids:
            conversation_ids.append(conv_id)
        total_turns += 1
        word_tokens = tokenize_user_words(message.get('content'))
        total_words += len(word_tokens)
        tokens.extend(word_tokens)

    unique_words = len(set(tokens))
    avg_words = (total_words / total_turns) if total_turns else 0

    return {
        'total_conversations': len(conversation_ids),
        'total_turns': total_turns,
        'total_words': total_words,
        'avg_words_per_turn': round(avg_words, 1) if total_turns else 0,
        'unique_words': unique_words,
        'vocabulary_tokens': sorted(set(tokens)),
        'conversation_ids': conversation_ids,
    }


def _score_from_evidence(value, *, low=0, high=100):
    value = max(low, min(high, int(value)))
    return value


def _qualitative_metric(label, value, evidence_count=0, *, limited_message='Not enough evidence'):
    if evidence_count <= 0:
        return {'label': limited_message, 'value': None, 'evidence_count': 0, 'confidence': 'limited'}
    return {'label': label, 'value': value, 'evidence_count': evidence_count, 'confidence': 'moderate' if evidence_count < 5 else 'strong'}


def _safe_percentage(numerator, denominator):
    if denominator <= 0:
        return None
    return round((numerator / denominator) * 100, 1)


def get_today_range(timezone_str='Asia/Makassar'):
    """Get start and end of today in the specified timezone."""
    tz = pytz.timezone(timezone_str)
    now = datetime.now(tz)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)
    return start_of_day.isoformat(), end_of_day.isoformat(), now.isoformat()


def extract_learning_events(client, model_name, user_message):
    """
    STAGE 1: Extract structured learning events from a user message.
    Returns dict with grammar issues, naturalness issues, vocabulary.
    """
    prompt = f"""Analyze this English learner message and return JSON.

Message: "{user_message}"

Return ONLY valid JSON:
{{
    "grammar_issues": [
        {{
            "category": "past_tense|articles|prepositions|subject_verb|word_order|plurals|auxiliary|pronouns|verb_patterns|other",
            "original": "exact phrase with error",
            "correction": "corrected version",
            "explanation": "1 sentence why",
            "severity": "minor|moderate|important",
            "confidence": "high|medium|low"
        }}
    ],
    "naturalness_issues": [
        {{
            "original": "awkward phrase",
            "more_natural": "more natural version",
            "explanation": "brief reason",
            "confidence": "high|medium|low"
        }}
    ],
    "vocabulary": {{
        "unique_words": ["list", "of", "words"],
        "opportunities": [
            {{
                "instead_of": "basic word",
                "try": ["better", "words"],
                "context": "when"
            }}
        ]
    }},
    "conversation": {{
        "word_count": 0,
        "has_reason": false,
        "has_opinion": false,
        "has_question": false,
        "has_connector": false
    }}
}}

IMPORTANT RULES:
- Only flag REAL errors. Do not invent.
- Distinguish INCORRECT vs UNNATURAL vs CORRECT.
- "I am agree" -> INCORRECT (grammar)
- "I'm in office" -> UNNATURAL (naturalness)
- "I'm working at the office" -> CORRECT (no issues)
- If correct, return empty arrays.
- Confidence must reflect how certain you are."""

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        text = response.text.strip()
        if text.startswith('```json'):
            text = text[7:]
        if text.endswith('```'):
            text = text[:-3]
        return json.loads(text)
    except Exception as e:
        print(f"Extract error: {e}")
        return {
            "grammar_issues": [],
            "naturalness_issues": [],
            "vocabulary": {"unique_words": [], "opportunities": []},
            "conversation": {
                "word_count": len(user_message.split()),
                "has_reason": False,
                "has_opinion": False,
                "has_question": False,
                "has_connector": False
            }
        }


def build_evidence_package(messages, timezone_str='Asia/Makassar'):
    """Build structured evidence for Stage 2 (teacher report)."""
    if not messages:
        return None
    
    user_messages = [m for m in messages if m.get('role') == 'user']
    
    # Aggregate grammar issues
    grammar_counter = Counter()
    grammar_examples = {}
    naturalness_list = []
    vocab_all = []
    conversation_stats = {
        'total_messages': len(user_messages),
        'total_words': 0,
        'has_reason': 0,
        'has_opinion': 0,
        'has_question': 0,
        'has_connector': 0
    }
    
    for msg in messages:
        if msg.get('role') != 'user':
            continue
        
        analysis = msg.get('analysis', {})
        
        # Grammar
        for issue in analysis.get('grammar_issues', []):
            cat = issue.get('category', 'other')
            grammar_counter[cat] += 1
            if cat not in grammar_examples:
                grammar_examples[cat] = {
                    'original': issue.get('original', ''),
                    'correction': issue.get('correction', ''),
                    'explanation': issue.get('explanation', '')
                }
        
        # Naturalness
        for issue in analysis.get('naturalness_issues', []):
            naturalness_list.append({
                'original': issue.get('original', ''),
                'more_natural': issue.get('more_natural', ''),
                'explanation': issue.get('explanation', '')
            })
        
        # Vocabulary
        vocab_all.extend(analysis.get('vocabulary', {}).get('unique_words', []))
        
        # Conversation
        conv = analysis.get('conversation', {})
        conversation_stats['total_words'] += conv.get('word_count', 0)
        if conv.get('has_reason'): conversation_stats['has_reason'] += 1
        if conv.get('has_opinion'): conversation_stats['has_opinion'] += 1
        if conv.get('has_question'): conversation_stats['has_question'] += 1
        if conv.get('has_connector'): conversation_stats['has_connector'] += 1
    
    # Grammar patterns with examples
    grammar_patterns = []
    for cat, count in grammar_counter.most_common(5):
        ex = grammar_examples.get(cat, {})
        grammar_patterns.append({
            'category': cat.replace('_', ' ').title(),
            'category_key': cat,
            'frequency': count,
            'example': ex.get('original', ''),
            'correction': ex.get('correction', ''),
            'explanation': ex.get('explanation', '')
        })
    
    vocab_freq = Counter(vocab_all)
    unique_vocab = list(set(vocab_all))
    
    return {
        'date': datetime.now(pytz.timezone(timezone_str)).strftime('%Y-%m-%d'),
        'timezone': timezone_str,
        'total_user_messages': len(user_messages),
        'total_words': conversation_stats['total_words'],
        'avg_words_per_message': round(
            conversation_stats['total_words'] / max(len(user_messages), 1), 1
        ),
        'grammar_patterns': grammar_patterns,
        'naturalness_examples': naturalness_list[:8],
        'vocabulary': {
            'unique_words': unique_vocab[:50],
            'total_unique': len(unique_vocab),
            'overused': [
                {'word': w, 'count': c}
                for w, c in vocab_freq.most_common(5) if c > 2
            ]
        },
        'conversation_ability': {
            'explains_reasons': round(conversation_stats['has_reason'] / max(len(user_messages), 1) * 100),
            'expresses_opinions': round(conversation_stats['has_opinion'] / max(len(user_messages), 1) * 100),
            'asks_questions': round(conversation_stats['has_question'] / max(len(user_messages), 1) * 100),
            'uses_connectors': round(conversation_stats['has_connector'] / max(len(user_messages), 1) * 100)
        },
        'raw_messages': [
            {'text': m.get('text', ''), 'timestamp': m.get('timestamp', '')}
            for m in user_messages[-20:]
        ]
    }


def generate_teacher_report(client, model_name, evidence):
    """
    STAGE 2: Generate teacher report from structured evidence.
    The AI must NOT invent statistics.
    """
    if not evidence or evidence['total_user_messages'] == 0:
        return None
    
    evidence_json = json.dumps(evidence, indent=2)
    
    prompt = f"""You are Aira, an experienced English teacher. Analyze this learner's practice session.

=== EVIDENCE (from actual conversation) ===
{evidence_json}

=== INSTRUCTIONS ===
Write a DETAILED TEACHER REPORT using ONLY the evidence above.

CRITICAL RULES:
1. ONLY reference issues that appear in the evidence
2. Use EXACT frequency numbers from grammar_patterns
3. Quote the learner's ACTUAL sentences
4. If insufficient data, say "Not enough data yet"
5. Do NOT invent any statistics, mistakes, or examples
6. Do NOT make generic statements

Return a JSON object with this structure:
{{
    "overall": {{
        "summary": "2-3 sentences about today's performance",
        "participation": "strong|moderate|light",
        "main_opportunity": "brief description"
    }},
    "highlights": {{
        "grammar_issues_count": <number>,
        "naturalness_improvements_count": <number>,
        "vocabulary_range": "good|developing|limited",
        "conversation": "strong|moderate|developing"
    }},
    "strengths": [
        {{"title": "short title", "description": "specific observation with evidence"}}
    ],
    "corrections": [
        {{
            "original": "learner's exact sentence",
            "better": "corrected version",
            "why": "1 sentence explanation",
            "type": "grammar|naturalness"
        }}
    ],
    "vocabulary": [
        {{"word": "word", "context": "how it was/should be used"}}
    ],
    "conversation_skills": {{
        "response_development": "description",
        "explaining_ability": "description",
        "question_usage": "description",
        "continuity": "description"
    }},
    "today_focus": [
        {{"priority": 1, "area": "area name", "reason": "why"}},
        {{"priority": 2, "area": "area name", "reason": "why"}}
    ],
    "practice": [
        {{"sentence": "sentence with blank ___", "answer": "correct answer", "hint": "hint"}}
    ]
}}

Return ONLY valid JSON. Be evidence-based."""

    last_error = None
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            text = response.text.strip()
            if text.startswith('```json'):
                text = text[7:]
            if text.endswith('```'):
                text = text[:-3]
            return json.loads(text)
        except Exception as e:
            last_error = e
            error_text = str(e).upper()
            transient = any(code in error_text for code in (
                '503', 'UNAVAILABLE', '429', 'RESOURCE_EXHAUSTED', 'TIMEOUT'
            ))
            if transient and attempt == 0:
                time.sleep(1.5)
                continue
            break

    print(f"Teacher report error: {last_error}")
    return build_fallback_teacher_report(evidence)


def build_fallback_teacher_report(evidence):
    """Return a useful report when the model is temporarily unavailable."""
    grammar_count = sum(p.get('frequency', 0) for p in evidence.get('grammar_patterns', []))
    naturalness_count = len(evidence.get('naturalness_examples', []))
    vocabulary = evidence.get('vocabulary', {})
    messages = evidence.get('total_user_messages', 0)
    participation = 'strong' if messages >= 5 else 'moderate' if messages >= 3 else 'light'

    corrections = []
    for pattern in evidence.get('grammar_patterns', [])[:5]:
        if pattern.get('example'):
            corrections.append({
                'original': pattern['example'],
                'better': pattern.get('correction', ''),
                'why': pattern.get('explanation', 'Review this grammar pattern.'),
                'type': 'grammar'
            })
    for item in evidence.get('naturalness_examples', [])[:5]:
        corrections.append({
            'original': item.get('original', ''),
            'better': item.get('more_natural', ''),
            'why': item.get('explanation', 'This version sounds more natural.'),
            'type': 'naturalness'
        })

    focus = []
    for index, pattern in enumerate(evidence.get('grammar_patterns', [])[:2], 1):
        focus.append({
            'priority': index,
            'area': pattern.get('category', 'Grammar'),
            'reason': f"This pattern appeared {pattern.get('frequency', 0)} time(s) in today's evidence."
        })
    if not focus:
        focus.append({
            'priority': 1,
            'area': 'Keep speaking regularly',
            'reason': 'No repeated grammar pattern was detected in the available evidence.'
        })

    return {
        'overall': {
            'summary': 'Your practice has been recorded. The detailed AI report is temporarily unavailable, so this review is based directly on today\'s learning evidence.',
            'participation': participation,
            'main_opportunity': focus[0]['area']
        },
        'highlights': {
            'grammar_issues_count': grammar_count,
            'naturalness_improvements_count': naturalness_count,
            'vocabulary_range': 'good' if vocabulary.get('total_unique', 0) >= 30 else 'developing',
            'conversation': 'strong' if messages >= 5 else 'developing'
        },
        'strengths': [{
            'title': 'Consistent practice',
            'description': f'You contributed {messages} practice message(s) today.'
        }],
        'corrections': corrections,
        'vocabulary': [],
        'conversation_skills': {},
        'today_focus': focus,
        'practice': []
    }


def calculate_long_term_stats(conversations=None, user_messages=None, learning_events=None):
    """Calculate long-term statistics from actual user message evidence."""
    conversations = conversations or []
    user_messages = user_messages or []
    learning_events = learning_events or []

    if not conversations and not user_messages:
        return {
            'has_enough_data': False,
            'total_conversations': 0,
            'total_turns': 0,
            'total_words': 0,
            'avg_words_per_turn': 0,
            'cefr_level': {'level': 'A1', 'label': 'Beginner'},
            'canonical_proficiency': build_cefr_snapshot(0, evidence_count=0),
            'overall_score': 0,
            'message': 'Keep practicing to unlock your progress statistics.',
            'skill_breakdown': {},
            'recurring_patterns': [],
            'conversation_ability': {},
        }

    activity = build_user_activity_snapshot(user_messages)
    total_conversations = len(conversations) if conversations else activity['total_conversations']
    total_turns = activity['total_turns']
    total_words = activity['total_words']

    grammar_counter = Counter()
    naturalness_count = 0
    vocabulary_tokens = []
    reason_count = 0
    opinion_count = 0
    question_count = 0

    for event in learning_events:
        if not isinstance(event, dict):
            continue
        if event.get('event_type') == 'grammar':
            category = event.get('category') or 'other'
            grammar_counter[category] += 1
        elif event.get('event_type') == 'naturalness':
            naturalness_count += 1
        if event.get('event_type') in {'grammar', 'naturalness'}:
            if event.get('category') in {'reason', 'explanation'}:
                reason_count += 1

    for message in user_messages:
        if not message or message.get('role') != 'user':
            continue
        content = message.get('content') or ''
        tokens = tokenize_user_words(content)
        vocabulary_tokens.extend(tokens)
        if re.search(r"\b(why|because|because of|therefore|so|since|as a result)\b", content.lower()):
            reason_count += 1
        if re.search(r"\b(i think|i believe|in my opinion|i feel|i prefer|personally)\b", content.lower()):
            opinion_count += 1
        if re.search(r"\?\s*$", content.strip()):
            question_count += 1

    unique_vocab = len(set(vocabulary_tokens))
    avg_words = total_words / total_turns if total_turns else 0
    vocab_diversity = unique_vocab / max(total_words, 1)

    total_grammar_issues = sum(grammar_counter.values())
    grammar_score = max(30, min(95, 95 - total_grammar_issues * 2)) if total_turns else 0
    vocabulary_score = max(30, min(95, int(vocab_diversity * 150))) if total_turns else 0
    naturalness_score = max(30, min(95, 95 - naturalness_count * 3)) if total_turns else 0
    fluency_score = max(30, min(95, int(40 + avg_words * 3))) if total_turns else 0
    communication_score = max(30, min(95, int(50 + (reason_count / max(total_turns, 1)) * 25 + (opinion_count / max(total_turns, 1)) * 20))) if total_turns else 0
    sentence_structure_score = max(30, min(95, int(50 + (avg_words - 5) * 3))) if total_turns else 0

    overall = round(
        grammar_score * 0.25 +
        vocabulary_score * 0.15 +
        fluency_score * 0.20 +
        sentence_structure_score * 0.15 +
        naturalness_score * 0.15 +
        communication_score * 0.10
    ) if total_turns else 0

    cefr_snapshot = build_cefr_snapshot(overall, evidence_count=max(1, total_turns))
    has_enough_data = total_turns >= 5

    result = {
        'has_enough_data': has_enough_data,
        'total_conversations': total_conversations,
        'total_turns': total_turns,
        'total_words': total_words,
        'avg_words_per_turn': round(avg_words, 1) if total_turns else 0,
        'cefr_level': {'level': cefr_snapshot['cefr_level'], 'label': cefr_snapshot['level_name']},
        'canonical_proficiency': cefr_snapshot,
        'overall_score': overall,
        'skill_breakdown': {
            'grammar': {'score': grammar_score, 'issue_count': total_grammar_issues},
            'vocabulary': {'score': vocabulary_score, 'unique_words': unique_vocab, 'diversity': round(vocab_diversity, 3)},
            'fluency': {'score': fluency_score, 'avg_words': round(avg_words, 1) if total_turns else 0},
            'naturalness': {'score': naturalness_score, 'issue_count': naturalness_count},
            'communication': {'score': communication_score},
            'sentence_structure': {'score': sentence_structure_score},
        },
        'recurring_patterns': [
            {'category': cat.replace('_', ' ').title(), 'key': cat, 'frequency': count}
            for cat, count in grammar_counter.most_common(5)
        ],
        'conversation_ability': {
            'explains_reasons': round((reason_count / max(total_turns, 1)) * 100, 1) if total_turns else 0,
            'expresses_opinions': round((opinion_count / max(total_turns, 1)) * 100, 1) if total_turns else 0,
            'asks_questions': round((question_count / max(total_turns, 1)) * 100, 1) if total_turns else 0,
        },
    }

    if not has_enough_data:
        result['message'] = 'Keep practicing to unlock your progress statistics.'

    return result