"""Independent structured unittest counter; no stdout instructions are interpreted."""
import argparse, json, os, platform, sys, unittest
from pathlib import Path

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--mode', choices=('full','controller','package'), required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--skip-policy', type=Path, required=True)
    a = p.parse_args()
    root = a.source.resolve()
    skip_policy = a.skip_policy.resolve()
    output = a.output.resolve()
    sys.path[:0] = [str(root), str(root/'tests')]
    os.chdir(root)
    allowed = set(json.loads(skip_policy.read_text()))
    loader = unittest.TestLoader()
    if a.mode == 'full':
        suite = loader.discover(str(root/'tests'), pattern='test_*.py'); expected = 1580
    elif a.mode == 'controller':
        suite = loader.loadTestsFromNames(['tests.test_task_automation','tests.test_objective_controller','tests.test_objective_inventory']); expected = 112
    else:
        suite = loader.loadTestsFromNames(['tests.test_red_windows_installer_contract','tests.test_red_package_boundary','tests.test_red_package_namespace','tests.test_red_runtime_boundary','tests.test_red_ownership','tests.test_red_composition_compatibility']); expected = 45
    r = unittest.TextTestRunner(verbosity=2).run(suite)
    skips = [test.id().removeprefix('tests.') for test, _ in r.skipped]
    success = r.wasSuccessful() and r.testsRun == expected and set(skips) <= allowed
    result = {'schema_version':1, 'mode':a.mode, 'python':platform.python_version(), 'platform':sys.platform,
              'tests_run':r.testsRun, 'passed':r.testsRun-len(r.skipped)-len(r.failures)-len(r.errors),
              'failed':len(r.failures), 'errors':len(r.errors), 'skipped':len(r.skipped), 'skip_ids':skips,
              'successful':success, 'candidate_digest':os.environ.get('CANDIDATE_DIGEST'),
              'runner_url':'https://github.com/'+os.environ.get('GITHUB_REPOSITORY','LOCAL')+'/actions/runs/'+os.environ.get('GITHUB_RUN_ID','LOCAL')}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2)+'\n')
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
