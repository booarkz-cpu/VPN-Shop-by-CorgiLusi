"""Release asset selection must match the advertised version before extraction."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release_fetch", ROOT / "scripts/github_release_fetch.py")
fetcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fetcher)


class ReleaseSelectionTests(unittest.TestCase):
    def run_fetch(self, tag, names):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            app = root / "app"
            (app / "backend/app").mkdir(parents=True)
            (app / "backend/app/main.py").write_text('APP_VERSION = "20.0.18"\n')
            payload = {"tag_name": tag, "assets": [
                {"name": name, "browser_download_url": fetcher.DOWNLOAD_PREFIX + name}
                for name in names
            ]}
            with patch.object(fetcher, "fetch_json", return_value=payload), \
                 patch.object(fetcher, "download") as download, \
                 patch.object(fetcher.sys, "argv", ["fetch", str(app), str(root / "stage")]):
                with self.assertRaises(SystemExit):
                    fetcher.main()
                download.assert_not_called()
                self.assertFalse((root / "stage").exists())

    def test_rejects_archive_from_another_version(self):
        self.run_fetch("v20.0.19", ["remnawave_vpn_shop_v20_0_18_full_release.zip",
                                      "remnawave_vpn_shop_v20_0_18_full_release.zip.sha256"])

    def test_rejects_malformed_tag(self):
        self.run_fetch("v20.0.19-unsigned", ["remnawave_vpn_shop_v20_0_19_full_release.zip",
                                               "remnawave_vpn_shop_v20_0_19_full_release.zip.sha256"])

    def test_rejects_checksum_for_another_filename(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            app = root / "app"
            (app / "backend/app").mkdir(parents=True)
            (app / "backend/app/main.py").write_text('APP_VERSION = "20.0.18"\n')
            name = "remnawave_vpn_shop_v20_0_19_full_release.zip"
            payload = {"tag_name": "v20.0.19", "assets": [
                {"name": value, "browser_download_url": fetcher.DOWNLOAD_PREFIX + value}
                for value in (name, name + ".sha256")
            ]}
            with patch.object(fetcher, "fetch_json", return_value=payload), \
                 patch.object(fetcher, "download", side_effect=[b"archive", ("0" * 64 + "  other.zip").encode()]), \
                 patch.object(fetcher.sys, "argv", ["fetch", str(app), str(root / "stage")]):
                with self.assertRaises(SystemExit):
                    fetcher.main()
                self.assertFalse((root / "stage").exists())


if __name__ == "__main__":
    unittest.main()
