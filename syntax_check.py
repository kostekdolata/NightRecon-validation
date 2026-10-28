import ast, json, sys, tomllib
from pathlib import Path
root = Path(sys.argv[1]); manifest = json.loads(Path(sys.argv[2]).read_text())
counts = {'python':0, 'toml':0, 'json':0}
for entry in manifest['entries']:
    p = root/entry['path']
    if p.suffix == '.py':
        ast.parse(p.read_bytes(), filename=str(p)); counts['python'] += 1
    if p.name == 'pyproject.toml':
        tomllib.loads(p.read_text()); counts['toml'] += 1
    if p.suffix == '.json' and entry['path'].startswith('.github/codex/'):
        json.loads(p.read_text()); counts['json'] += 1
print(json.dumps({'successful':True, 'syntax_files':counts}))
