import re
from collections import defaultdict
from datetime import datetime


VALID_CATEGORIES = {
    "grammar",
    "word_choice",
    "naturalness",
    "collocation",
    "preposition",
    "article",
    "tense",
    "subject_verb_agreement",
    "sentence_structure",
    "vocabulary",
}


THIRD_PERSON_VERBS = {
    "work": "works",
    "go": "goes",
    "study": "studies",
    "play": "plays",
    "eat": "eats",
    "like": "likes",
    "live": "lives",
    "read": "reads",
    "write": "writes",
    "speak": "speaks",
    "talk": "talks",
    "practice": "practices",
    "need": "needs",
    "want": "wants",
    "help": "helps",
    "teach": "teaches",
    "travel": "travels",
    "watch": "watches",
    "listen": "listens",
    "cook": "cooks",
    "stay": "stays",
}


def _conjugate_third_person(verb):
    if verb.endswith("y") and len(verb) > 1 and verb[-2] not in "aeiou":
        return verb[:-1] + "ies"
    if verb.endswith(("s", "x", "z", "ch", "sh", "o")):
        return verb + "es"
    return verb + "s"


def normalize_mistake(message):
    text = (message or "").strip()
    if not text:
        return None
    lowered = text.lower()

    for pronoun in ["she", "he", "it", "my brother", "my sister", "the teacher", "john", "maria"]:
        for verb in sorted(THIRD_PERSON_VERBS.keys(), key=len, reverse=True):
            pattern = rf"\b{re.escape(pronoun)}\s+{re.escape(verb)}\b"
            match = re.search(pattern, lowered)
            if match:
                incorrect = match.group(0).strip()
                correct = f"{pronoun} {_conjugate_third_person(verb)}"
                return {
                    "category": "subject_verb_agreement",
                    "pattern": "subject-verb agreement",
                    "incorrect": incorrect,
                    "correct": correct,
                    "explanation": "Third-person singular subjects in the present simple usually need the -s form.",
                    "status": "new",
                    "occurrence_count": 1,
                    "first_detected": datetime.utcnow().isoformat(),
                    "last_detected": datetime.utcnow().isoformat(),
                    "needs_retesting": True,
                    "learner_improved": False,
                    "pattern_key": f"subject_verb_agreement::{incorrect}::{correct}",
                }

    for wrong, correct in [
        ("in the weekend", "on the weekend"),
        ("at the weekend", "on the weekend"),
        ("i am agree", "i agree"),
        ("i am interesting", "i am interested"),
        ("i have went", "i went"),
    ]:
        if wrong in lowered:
            return {
                "category": "preposition" if "weekend" in wrong else "grammar",
                "pattern": "common learner pattern",
                "incorrect": wrong,
                "correct": correct,
                "explanation": "This phrase is a common pattern that sounds more natural in English with the corrected form.",
                "status": "new",
                "occurrence_count": 1,
                "first_detected": datetime.utcnow().isoformat(),
                "last_detected": datetime.utcnow().isoformat(),
                "needs_retesting": True,
                "learner_improved": False,
                "pattern_key": f"{wrong}::{correct}",
            }

    return None


def upsert_recurring_mistake(existing, user_message):
    normalized = normalize_mistake(user_message)
    if normalized is None:
        return existing or {}

    pattern_key = normalized["pattern_key"]
    now = datetime.utcnow().isoformat()

    if existing and existing.get("pattern_key") == pattern_key:
        occurrence_count = int(existing.get("occurrence_count", 0)) + 1
        status = "new"
        if occurrence_count >= 2:
            status = "recurring"
        if occurrence_count >= 3:
            status = "improving"
        return {
            **existing,
            "category": existing.get("category") or normalized["category"],
            "incorrect": existing.get("incorrect") or normalized["incorrect"],
            "correct": existing.get("correct") or normalized["correct"],
            "explanation": existing.get("explanation") or normalized["explanation"],
            "occurrence_count": occurrence_count,
            "last_detected": now,
            "status": status,
            "needs_retesting": occurrence_count >= 2,
            "learner_improved": occurrence_count >= 3,
            "pattern_key": pattern_key,
            "example_sentences": list(dict.fromkeys([
                *(existing.get("example_sentences") or []),
                user_message,
            ]))[:6],
        }

    return {
        "category": normalized["category"],
        "pattern": normalized["pattern"],
        "incorrect": normalized["incorrect"],
        "correct": normalized["correct"],
        "explanation": normalized["explanation"],
        "occurrence_count": 1,
        "first_detected": now,
        "last_detected": now,
        "status": "new",
        "needs_retesting": True,
        "learner_improved": False,
        "pattern_key": pattern_key,
        "example_sentences": [user_message],
    }


def build_learning_profile(mistakes):
    if not mistakes:
        return {
            "current_level": "Emerging",
            "strengths": [],
            "needs_practice": [],
            "focus_areas": [],
            "recurring_patterns": [],
            "weak_patterns": [],
            "preferred_practice": ["short conversational practice", "gentle corrections"],
            "empty_state": True,
        }

    ordered = sorted(mistakes, key=lambda item: (int(item.get("occurrence_count", 0)), item.get("category", "")), reverse=True)
    focus_areas = []
    seen = set()
    for item in ordered:
        category = item.get("category")
        if category and category not in seen:
            focus_areas.append(category)
            seen.add(category)

    recurring_patterns = [
        {
            "category": item.get("category"),
            "incorrect": item.get("incorrect"),
            "correct": item.get("correct"),
            "occurrence_count": int(item.get("occurrence_count", 0)),
            "status": item.get("status", "new"),
        }
        for item in ordered
        if int(item.get("occurrence_count", 0)) >= 2
    ]

    improved = [item for item in ordered if item.get("learner_improved")]
    strengths = []
    for item in improved[:3]:
        strengths.append(item.get("category"))

    needs_practice = [
        item.get("category")
        for item in ordered[:3]
        if item.get("category")
    ]

    return {
        "current_level": "Developing",
        "strengths": strengths or ["conversation confidence", "willingness to practice"],
        "needs_practice": needs_practice or focus_areas[:3],
        "focus_areas": focus_areas,
        "recurring_patterns": recurring_patterns,
        "weak_patterns": [
            {
                "incorrect": item.get("incorrect"),
                "correct": item.get("correct"),
                "category": item.get("category"),
                "occurrence_count": int(item.get("occurrence_count", 0)),
            }
            for item in ordered[:5]
        ],
        "preferred_practice": [
            "conversational English",
            "real-life topics",
            "short corrective feedback",
        ],
        "empty_state": False,
    }


def adapt_conversation_prompt(topic, profile):
    topic = topic or "general conversation"
    if not profile or not profile.get("focus_areas"):
        return topic

    focus = ", ".join(profile.get("focus_areas", [])[:3])
    weak_patterns = profile.get("weak_patterns") or []
    pattern_text = ""
    if weak_patterns:
        examples = []
        for item in weak_patterns[:2]:
            if isinstance(item, dict):
                wrong = item.get('incorrect')
                right = item.get('correct')
            else:
                wrong = item
                right = None
            if wrong and right:
                examples.append(f"{wrong} → {right}")
            elif isinstance(item, str) and "->" in item:
                examples.append(item)
        if examples:
            pattern_text = " Keep the correction natural around: " + "; ".join(examples) + "."

    return (
        f"Learner profile: focus areas include {focus}. "
        f"The next conversation should feel natural and supportive, with brief, contextual practice around the learner's recurring patterns.{pattern_text}"
        f" Conversation topic: {topic}"
    )


def aggregate_user_mistakes(events):
    grouped = defaultdict(dict)
    for event in events:
        category = event.get("category")
        incorrect = event.get("incorrect") or ""
        correct = event.get("correct") or ""
        if not category or not incorrect or not correct:
            continue
        key = f"{category}::{incorrect.lower()}::{correct.lower()}"
        item = grouped[key]
        if not item:
            item.update({
                "category": category,
                "incorrect": incorrect,
                "correct": correct,
                "pattern_key": key,
                "occurrence_count": 0,
                "status": "new",
                "learner_improved": False,
                "first_detected": event.get("timestamp") or datetime.utcnow().isoformat(),
                "last_detected": event.get("timestamp") or datetime.utcnow().isoformat(),
                "example_sentences": [],
            })
        item["occurrence_count"] += 1
        item["last_detected"] = event.get("timestamp") or item.get("last_detected")
        if item["occurrence_count"] >= 2:
            item["status"] = "recurring"
        if item["occurrence_count"] >= 3:
            item["status"] = "improving"
        if event.get("example_sentence"):
            item["example_sentences"] = list(dict.fromkeys(item.get("example_sentences", []) + [event["example_sentence"]]))[:6]
        grouped[key] = item
    return list(grouped.values())
