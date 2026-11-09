import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET
from urllib.error import HTTPError

from scripts import update_profile as updater


class ProfileUpdateTests(unittest.TestCase):
    def test_paginates_counts_public_repos_and_excludes_fork_stars(self):
        page_one = [{"stargazers_count": 1, "fork": False, "private": False} for _ in range(100)]
        page_one[0]["stargazers_count"] = 7
        page_one[1]["fork"] = True
        page_one[1]["stargazers_count"] = 19
        page_one[2]["private"] = True
        page_two = [{"stargazers_count": 4, "fork": False, "private": False}]
        with patch.object(updater, "get_json", side_effect=[{"followers": 3}, page_one, page_two]) as get_json:
            self.assertEqual(updater.fetch_stats("sample-user"), {"followers": 3, "repos": 100, "stars": 108})
        self.assertEqual(get_json.call_count, 3)
        self.assertIn("page=2", get_json.call_args_list[2].args[0])

    def test_rejects_invalid_api_fields_instead_of_fabricating_counts(self):
        invalid_responses = [
            [{"fork": False}],
            [{"stargazers_count": 2}],
            [{"stargazers_count": True, "fork": False}],
            [{"stargazers_count": 1, "fork": "false"}],
        ]
        for repos in invalid_responses:
            with self.subTest(repos=repos), patch.object(updater, "get_json", side_effect=[{"followers": 2}, repos]):
                with self.assertRaises(updater.UpdateError):
                    updater.fetch_stats("sample-user")
        with patch.object(updater, "get_json", return_value={"followers": True}):
            with self.assertRaises(updater.UpdateError):
                updater.fetch_stats("sample-user")

    def test_svg_escapes_xml_and_is_well_formed(self):
        svg = updater.render_svg('user<&"', date(2026, 11, 9), {"followers": 1, "repos": 2, "stars": 3})
        root = ET.fromstring(svg)
        self.assertIn("user&lt;&amp;&quot;", svg)
        self.assertEqual(root.attrib["width"], "1000")

    def test_offline_marks_values_unavailable_and_does_not_claim_api_data(self):
        svg = updater.render_svg("sample-user", date(2026, 11, 9), None)
        self.assertIn("STATS UNAVAILABLE", svg)
        self.assertIn("Live data unavailable", svg)
        self.assertNotIn("Data from the public GitHub API", svg)

    def test_api_failure_preserves_last_valid_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "daily.svg"
            destination.write_text("last valid image", encoding="utf-8")
            with patch.object(updater, "OUTPUT", destination), patch.object(updater, "fetch_stats", side_effect=updater.UpdateError("unavailable")):
                self.assertEqual(updater.main(["--username", "sample-user", "--date", "2026-11-09"]), 1)
            self.assertEqual(destination.read_text(encoding="utf-8"), "last valid image")

    def test_offline_cli_writes_deterministic_unavailable_card(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "daily.svg"
            with patch.object(updater, "OUTPUT", destination), patch.object(updater, "fetch_stats") as fetch:
                self.assertEqual(updater.main(["--username", "sample-user", "--offline", "--date", "2026-11-09"]), 0)
            fetch.assert_not_called()
            svg = destination.read_text(encoding="utf-8")
            self.assertIn("2026.11.09", svg)
            self.assertIn("STATS UNAVAILABLE", svg)

    def test_http_failure_is_reported_without_response_body(self):
        failure = HTTPError("https://api.github.com/users/sample-user", 503, "unavailable", {}, None)
        with patch.object(updater, "urlopen", side_effect=failure):
            with self.assertRaisesRegex(updater.UpdateError, "HTTPError") as caught:
                updater.get_json("https://api.github.com/users/sample-user")
        self.assertNotIn("unavailable", str(caught.exception))

    def test_invalid_username_is_rejected(self):
        with self.assertRaises(updater.UpdateError):
            updater.valid_username("<bad>")


if __name__ == "__main__":
    unittest.main()
