"""Offline regression tests for Macca's Meta token maintenance."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from scripts import renew_instagram_token as rotation


class TokenMaintenanceTests(unittest.TestCase):
    def test_instagram_login_is_identified(self):
        with patch.object(rotation, "graph_get", return_value={"user_id": "ig-123"}):
            self.assertEqual(rotation.identify_token("dummy", "unused"), ("instagram_login", "ig-123"))

    def test_facebook_page_is_not_mistaken_for_instagram_login(self):
        def fake_graph(url, token, params):
            if url == rotation.INSTAGRAM_ME:
                raise rotation.TokenError("Meta returned HTTP 400")
            return {"id": "page-456"}
        with patch.object(rotation, "graph_get", side_effect=fake_graph):
            self.assertEqual(rotation.identify_token("dummy", "page-456"), ("facebook_page", "page-456"))
            with self.assertRaises(rotation.TokenError):
                rotation.identify_token("dummy", "a-different-page")

    def test_refresh_writes_only_the_macca_secret(self):
        commands = []

        def fake_graph(url, token, params):
            if url == rotation.INSTAGRAM_REFRESH:
                return {"access_token": "new-private-token", "expires_in": 5184000}
            if url == rotation.INSTAGRAM_ME:
                return {"user_id": "ig-123"}
            raise AssertionError("Unexpected Meta call")

        def fake_run(command, **kwargs):
            commands.append((command, kwargs))
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with patch.object(rotation, "graph_get", side_effect=fake_graph), \
             patch.object(rotation.subprocess, "run", side_effect=fake_run), \
             patch("builtins.print"):
            rotation.renew("old-private-token", "ig-123", {"GH_TOKEN": "github-credential"})
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0][0], [
            "gh", "secret", "set", "INSTAGRAM_ACCESS_TOKEN", "--repo", "PkLavc/lab"
        ])
        self.assertEqual(commands[0][1]["input"], "new-private-token\n")
        self.assertEqual(commands[0][1]["env"]["GH_TOKEN"], "github-credential")

    def test_wrong_identity_does_not_write_secret(self):
        def fake_graph(url, token, params):
            if url == rotation.INSTAGRAM_REFRESH:
                return {"access_token": "new-private-token", "expires_in": 5184000}
            return {"user_id": "unexpected-account"}

        with patch.object(rotation, "graph_get", side_effect=fake_graph), \
             patch.object(rotation.subprocess, "run") as gh, \
             patch("builtins.print"):
            with self.assertRaises(rotation.TokenError):
                rotation.renew("old-private-token", "ig-123", {})
        gh.assert_not_called()

    def test_permission_check_does_not_modify_secrets(self):
        with patch.object(rotation.subprocess, "run", return_value=SimpleNamespace(
                returncode=0, stdout="key-id\n", stderr="")) as runner:
            env = rotation.verify_github_access("github-credential")
        self.assertEqual(env["GH_TOKEN"], "github-credential")
        self.assertEqual(runner.call_args.args[0][0:2], ["gh", "api"])

    def test_main_page_token_skips_refresh(self):
        with patch.dict(os.environ, {
            "INSTAGRAM_ACCESS_TOKEN": "page-token",
            "INSTAGRAM_ROTATION_GITHUB_TOKEN": "github-credential",
            "INSTAGRAM_PAGE_ID": "page-456",
        }), patch("sys.argv", ["renew_instagram_token.py", "renew"]), \
             patch.object(rotation, "identify_token", return_value=("facebook_page", "page-456")), \
             patch.object(rotation, "verify_github_access", return_value={}), \
             patch.object(rotation, "renew") as renew, \
             patch("builtins.print"):
            self.assertEqual(rotation.main(), 0)
        renew.assert_not_called()


if __name__ == "__main__":
    unittest.main()
