"""Trusted validation-only artifact reader; install outside candidate source."""
import argparse, base64, hashlib, json, os, re, stat, urllib.request, zipfile
from pathlib import Path
BASE = '09707e49116b6021fa7bb695c1979aeb240b4fca'
MAX_ARCHIVE = 8 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024

def require(value, message):
    if not value:
        raise ValueError(message)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode('ascii')

def portable(name):
    require(type(name) is str and 0 < len(name) <= 512, 'invalid path')
    reserved = {'con','prn','aux','nul'} | {prefix+str(i) for prefix in ('com','lpt') for i in range(1,10)}
    for part in name.split('/'):
        require(re.fullmatch(r'[A-Za-z0-9_.-]+', part) is not None and part not in ('.','..')
                and not part.endswith('.') and part.lower() != '.git'
                and part.split('.')[0].lower() not in reserved, 'unsafe portable path')

def private_path(root, relative):
    current = root
    for part in relative.split('/'):
        current = current / part
        if current.exists() or current.is_symlink():
            info = current.lstat()
            require(not stat.S_ISLNK(info.st_mode)
                    and not getattr(info, 'st_file_attributes', 0) & 0x400,
                    'symlink/reparse path rejected')
    return current

def verify(archive, archive_sha, manifest_sha, candidate_sha, destination, verify_only=False):
    for value in (archive_sha, manifest_sha, candidate_sha):
        require(re.fullmatch('[0-9a-f]{64}', value) is not None, 'invalid digest')
    require(archive.stat().st_size <= MAX_ARCHIVE, 'archive size limit')
    require(digest(archive.read_bytes()) == archive_sha, 'archive SHA-256 mismatch')
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist()
        require(len(infos) <= 20001 and sum(i.file_size for i in infos) <= MAX_TOTAL, 'expanded archive limit')
        names = [i.filename for i in infos]
        require(len({name.casefold() for name in names}) == len(names), 'duplicate or case-colliding ZIP paths')
        raw = z.read('.candidate-manifest.json')
        require(digest(raw) == manifest_sha, 'manifest SHA-256 mismatch')
        manifest = json.loads(raw)
        require(manifest['schema_version'] == 1 and manifest['package_kind'] == 'source-only-rebuild-v1'
                and manifest['base_sha'] == BASE and manifest['branch'] == 'codex/task-controller-batch1',
                'candidate identity mismatch')
        require(len(manifest['entries']) == 749 and len(set(manifest['changed_files'])) == 20,
                'unexpected source or change count')
        require(digest(canonical({'base_sha': BASE, 'entries': manifest['entries']}))
                == candidate_sha == manifest['candidate_digest'], 'source-content digest mismatch')
        entries = {entry['path']: entry for entry in manifest['entries']}
        require(len(entries) == len(manifest['entries']), 'duplicate manifest path')
        require(set(names) == set(entries) | {'.candidate-manifest.json'}, 'extra or missing ZIP entry')
        require(set(manifest['changed_files']) <= set(entries), 'changed-file inventory mismatch')
        payloads = {}
        for name, entry in entries.items():
            portable(name)
            info = z.getinfo(name)
            require(entry['mode'] in ('100644','100755'), 'unsupported source mode')
            require(not info.flag_bits & 1 and stat.S_IFMT(info.external_attr >> 16) == stat.S_IFREG,
                    'encrypted/link/special ZIP entry rejected')
            require(format((info.external_attr >> 16) & 0o177777, '06o') == entry['mode'], 'mode mismatch')
            require(type(entry['size']) is int and 0 <= info.file_size == entry['size'] <= 1048576,
                    'file size mismatch/limit')
            with z.open(info) as stream:
                data = stream.read(1048577)
            require(len(data) == entry['size'] and digest(data) == entry['sha256'], 'file digest mismatch')
            payloads[name] = data
        # Validate all content before creating any extracted source files.
        if verify_only:
            require(destination.is_dir() and not destination.is_symlink(), 'missing/unsafe source root')
        else:
            require(not destination.exists() and not destination.is_symlink(), 'destination must be new')
            destination.mkdir(parents=True, exist_ok=False)
        for name, entry in entries.items():
            target = private_path(destination, name)
            if verify_only:
                require(target.is_file() and digest(target.read_bytes()) == entry['sha256'], 'tested source changed')
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payloads[name])
                if os.name == 'posix':
                    target.chmod(int(entry['mode'], 8) & 0o777)
        return {'verified': True, 'source_files': 749, 'changed_files': 20,
                'base_sha': BASE, 'candidate_digest': candidate_sha, 'archive_sha256': archive_sha}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--blob-sha')
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--archive-sha256', required=True)
    p.add_argument('--manifest-sha256', required=True)
    p.add_argument('--candidate-digest', required=True)
    p.add_argument('--destination', type=Path, required=True)
    p.add_argument('--verify-only', action='store_true')
    p.add_argument('--report', type=Path)
    a = p.parse_args()
    if a.blob_sha:
        require(re.fullmatch('[0-9a-f]{40}', a.blob_sha) is not None, 'invalid Git blob SHA')
        require(not a.archive.exists(), 'do not overwrite an existing download')
        url = 'https://api.github.com/repos/kostekdolata/NightRecon/git/blobs/' + a.blob_sha
        request = urllib.request.Request(url, headers={'Accept':'application/vnd.github+json','User-Agent':'NightRecon-checkpoint'})
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read(12 * 1024 * 1024 + 1)
        require(len(raw) <= 12 * 1024 * 1024, 'blob response limit')
        blob = json.loads(raw)
        require(blob['encoding'] == 'base64', 'unexpected blob encoding')
        a.archive.write_bytes(base64.b64decode(blob['content']))
    result = verify(a.archive, a.archive_sha256, a.manifest_sha256, a.candidate_digest,
                    a.destination, a.verify_only)
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
if __name__ == '__main__':
    main()
