"""Regression checks for import-safe Windows spawn bootstrap."""
import pathlib
import subprocess
import sys
import tempfile
import unittest


class RunnerEntryPointTests(unittest.TestCase):
    def test_import_and_spawn_bootstrap_have_no_execution_side_effects(self):
        helper = pathlib.Path(__file__).with_name("run_suite.py").resolve()
        for module_name in ("runner_import", "__mp_main__"):
            with self.subTest(module_name=module_name), tempfile.TemporaryDirectory() as directory:
                script = (
                    "import os, runpy, sys; before=os.getcwd(); "
                    "sys.argv=['run_suite.py', '--source', 'candidate', '--invalid-option']; "
                    f"ns=runpy.run_path({str(helper)!r}, run_name={module_name!r}); "
                    "assert os.getcwd()==before; assert callable(ns['main'])"
                )
                result = subprocess.run([sys.executable, "-c", script], cwd=directory,
                                        text=True, capture_output=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertEqual(list(pathlib.Path(directory).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
