"""设置持久化模块单元测试。"""
import unittest
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import settings


class TestSettings(unittest.TestCase):

    def setUp(self):
        self.tmpfile = os.path.join(tempfile.gettempdir(), "test_settings.json")

    def tearDown(self):
        try:
            os.remove(self.tmpfile)
        except OSError:
            pass

    def test_load_defaults_when_no_file(self):
        data = settings.load("/nonexistent/settings.json")
        self.assertEqual(data["speed"], "中")
        self.assertEqual(data["step_size"], 100)
        self.assertEqual(data["language"], "zh")

    def test_save_and_load(self):
        data = {"speed": "快", "step_size": 200}
        ok = settings.save(data, self.tmpfile)
        self.assertTrue(ok)
        loaded = settings.load(self.tmpfile)
        self.assertEqual(loaded["speed"], "快")
        self.assertEqual(loaded["step_size"], 200)
        # 未设置的键使用默认值
        self.assertEqual(loaded["language"], "zh")

    def test_update_single_key(self):
        settings.save({"speed": "慢"}, self.tmpfile)
        settings.update("step_size", 50, self.tmpfile)
        loaded = settings.load(self.tmpfile)
        self.assertEqual(loaded["speed"], "慢")
        self.assertEqual(loaded["step_size"], 50)

    def test_reset(self):
        settings.save({"speed": "快", "language": "en"}, self.tmpfile)
        settings.reset(self.tmpfile)
        loaded = settings.load(self.tmpfile)
        self.assertEqual(loaded["speed"], "中")
        self.assertEqual(loaded["language"], "zh")

    def test_defaults_all_keys_present(self):
        data = settings.load("/nonexistent/settings.json")
        for key in settings.DEFAULTS:
            self.assertIn(key, data)


if __name__ == "__main__":
    unittest.main()
