import unittest
from pathlib import Path

from src.config import Config
from src.judge import calculate_priority, stage_b_judge
from src.prompt_builder import build_prompt


def make_config() -> Config:
    return Config(
        onecomme_ws_urls=["ws://localhost:11180/api/director/stream"],
        onecomme_stream_ids=["stream"],
        aituberkit_base_url="http://localhost:3000",
        aituberkit_client_id="dummy",
        aituberkit_timeout=30,
        use_aituberkit_system_prompt=True,
        max_queue_size=10,
        allow_concurrent_response=False,
        trigger_words=["教えて"],
        greeting_first="{username}さん、はじめまして！",
        greeting_return="{username}さん、また来てくれてありがとう！",
        use_greeting=True,
        min_comment_length=2,
        ignore_patterns=["w"],
        positive_keywords=["?"],
        enable_llm_judge=True,
        llm_judge_cpu_threshold=60,
        max_cpu_usage=80,
        cpu_check_interval=5,
        log_level="INFO",
        log_file=Path("logs/system.log"),
        stats_file=Path("logs/stats.json"),
        debug_mode=False,
        show_all_comments=False,
    )


class JudgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = make_config()

    def test_priority_trigger(self) -> None:
        comment = {"comment": "教えてください", "isFirstTime": False}
        priority, has_trigger = calculate_priority(comment, self.config)
        self.assertEqual(priority, 0)
        self.assertTrue(has_trigger)

    def test_priority_first_time(self) -> None:
        comment = {"comment": "こんにちは", "isFirstTime": True}
        priority, has_trigger = calculate_priority(comment, self.config)
        self.assertEqual(priority, 0)
        self.assertFalse(has_trigger)

    def test_priority_normal(self) -> None:
        comment = {"comment": "なるほど"}
        priority, has_trigger = calculate_priority(comment, self.config)
        self.assertEqual(priority, 3)
        self.assertFalse(has_trigger)

    def test_stage_b_skip(self) -> None:
        decision, reason = stage_b_judge("w", self.config)
        self.assertFalse(decision)
        self.assertEqual(reason, "too_short")

    def test_prompt_builder(self) -> None:
        prompt = build_prompt(
            {"name": "太郎", "comment": "こんばんは!", "isFirstTime": True},
            self.config,
        )
        self.assertIn("太郎さん、はじめまして！", prompt)
        self.assertIn("太郎さんのコメント: こんばんは!", prompt)


if __name__ == "__main__":
    unittest.main()
