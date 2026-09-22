import unittest

from backend.analytics import (
    build_cefr_snapshot,
    calculate_long_term_stats,
    tokenize_user_words,
)
from backend.learning import (
    adapt_conversation_prompt,
    build_learning_profile,
    normalize_mistake,
    upsert_recurring_mistake,
)


class LearningFeatureTests(unittest.TestCase):
    def test_normalize_mistake_detects_subject_verb_pattern(self):
        result = normalize_mistake("I think she work in Jakarta.")
        self.assertEqual(result["category"], "subject_verb_agreement")
        self.assertIn("she work", result["incorrect"]) 
        self.assertIn("she works", result["correct"]) 

    def test_upsert_increases_frequency_for_same_pattern(self):
        first = upsert_recurring_mistake({
            "category": "subject_verb_agreement",
            "incorrect": "she work",
            "correct": "she works",
            "explanation": "Third person singular takes -s.",
            "status": "new",
            "occurrence_count": 1,
        }, "she work")
        second = upsert_recurring_mistake(first, "she work")
        self.assertGreater(second["occurrence_count"], first["occurrence_count"])
        self.assertEqual(second["status"], "recurring")

    def test_build_profile_lists_recurring_issues(self):
        profile = build_learning_profile([
            {"category": "subject_verb_agreement", "incorrect": "she work", "correct": "she works", "occurrence_count": 2, "status": "recurring"},
            {"category": "preposition", "incorrect": "in the weekend", "correct": "on the weekend", "occurrence_count": 1, "status": "new"},
        ])
        self.assertIn("subject_verb_agreement", profile["focus_areas"]) 
        self.assertIn("preposition", profile["focus_areas"]) 
        self.assertIn("she work", profile["recurring_patterns"][0]["incorrect"]) 

    def test_adapt_conversation_prompt_uses_profile_context(self):
        prompt = adapt_conversation_prompt(
            "The learner keeps saying 'in the weekend' instead of 'on the weekend'.",
            {"focus_areas": ["preposition", "subject_verb_agreement"], "weak_patterns": ["in the weekend -> on the weekend"]},
        )
        self.assertIn("preposition", prompt.lower())
        self.assertIn("on the weekend", prompt)

    def test_level_mapping_is_consistent(self):
        score_55 = build_cefr_snapshot(55, evidence_count=5)
        score_75 = build_cefr_snapshot(75, evidence_count=5)
        self.assertEqual(score_55['cefr_level'], 'A2')
        self.assertEqual(score_55['level_name'], 'Elementary')
        self.assertEqual(score_75['cefr_level'], 'B2')
        self.assertEqual(score_75['level_name'], 'Upper-Intermediate')

    def test_average_words_per_turn_uses_real_user_messages(self):
        user_messages = []
        for i in range(23):
            user_messages.append({'role': 'user', 'content': 'one two three four five six seven eight nine ten eleven twelve', 'conversation_id': f'c{i}'})
        user_messages.append({'role': 'user', 'content': 'one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen', 'conversation_id': 'c23'})
        stats = calculate_long_term_stats(
            conversations=[{'id': f'c{i}', 'turn_count': 1} for i in range(24)],
            user_messages=user_messages,
            learning_events=[]
        )
        self.assertEqual(stats['total_turns'], 24)
        self.assertEqual(stats['total_words'], 293)
        self.assertAlmostEqual(stats['avg_words_per_turn'], 12.2, places=1)

    def test_unique_vocabulary_counts_normalized_words(self):
        tokens = tokenize_user_words('Hello hello HELLO! I am happy. happy')
        self.assertEqual(len(set(tokens)), 4)
        self.assertIn('hello', tokens)

    def test_no_data_returns_not_enough_evidence(self):
        stats = calculate_long_term_stats([], user_messages=[], learning_events=[])
        self.assertFalse(stats['has_enough_data'])
        self.assertEqual(stats['total_turns'], 0)

    def test_conversation_count_is_distinct_per_user_session(self):
        stats = calculate_long_term_stats(
            conversations=[{'id': 'c1', 'turn_count': 1}, {'id': 'c2', 'turn_count': 1}],
            user_messages=[
                {'role': 'user', 'content': 'A', 'conversation_id': 'c1'},
                {'role': 'user', 'content': 'B', 'conversation_id': 'c1'},
                {'role': 'user', 'content': 'C', 'conversation_id': 'c2'},
            ],
            learning_events=[]
        )
        self.assertEqual(stats['total_conversations'], 2)
        self.assertEqual(stats['total_turns'], 3)


if __name__ == "__main__":
    unittest.main()
