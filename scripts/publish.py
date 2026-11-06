#!/usr/bin/env python3
"""Build the plugin package and generate the Jellyfin plugin repository manifest.

The manifest and the release asset are produced together on purpose: Jellyfin
verifies the MD5 of the downloaded zip against the `checksum` field, so the two
must always describe the exact same bytes.

Usage:
    python3 scripts/publish.py <version> [--owner OWNER] [--repo REPO]

Example:
    python3 scripts/publish.py 2026.1105.0000
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

try:
    from packaging.version import Version
except ImportError:
    sys.exit("The 'packaging' package is required: python3 -m pip install packaging")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSPROJ = os.path.join(REPO_ROOT, 'Jellyfin.Plugin.MetaTube', 'Jellyfin.Plugin.MetaTube.csproj')
# Note: the published manifest lives on the orphan 'dist' branch; this directory
# holds the generated artifacts that get copied onto that branch.
DIST_DIR = os.path.join(REPO_ROOT, 'repository')
MANIFEST = os.path.join(DIST_DIR, 'manifest.json')

DEFAULT_OWNER = 'serena7780'
DEFAULT_REPO = 'jellyfin-plugin-metatube'

# The plugin GUID must match Jellyfin.Plugin.MetaTube.Plugin.Id, otherwise the
# server treats the installed plugin as a different one.
PLUGIN_GUID = '01cc53ec-c415-4108-bbd4-a684a9801a32'
PLUGIN_NAME = 'MetaTube'
PLUGIN_DESCRIPTION = 'MetaTube Plugin for Jellyfin/Emby.'
PLUGIN_CATEGORY = 'Metadata'


def md5sum(filename: str) -> str:
    with open(filename, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def get_target_abi() -> str:
    """Return the plugin target ABI, e.g. '12.0.0'.

    The Jellyfin server compares its own version against this value using
    System.Version, so the ABI must be a plain three-part version number.
    A four-part value such as '12.0.0.0' compares as *greater* than the
    three-part '12.0.0' and would be rejected by a 12.0.0 server.
    """
    tree = ET.parse(CSPROJ)
    for pkg in tree.getroot().iter('PackageReference'):
        if pkg.attrib.get('Include') in ('Jellyfin.Controller', 'Jellyfin.Model'):
            release = Version(pkg.attrib.get('Version')).release
            while len(release) < 3:
                release = release + (0,)
            return '.'.join(str(part) for part in release[:3])

    raise Exception('Jellyfin version not found in %s' % CSPROJ)


def build_plugin(version: str) -> str:
    """Build the release package and return the path to the produced zip."""
    print('Building plugin %s ...' % version)
    subprocess.run(
        ['dotnet', 'build', '--configuration', 'Release', '-p:Version=%s' % version],
        cwd=REPO_ROOT, check=True)

    archive = os.path.join(
        REPO_ROOT, 'Jellyfin.Plugin.MetaTube', 'bin',
        'Jellyfin.MetaTube@v%s.zip' % version)
    if not os.path.isfile(archive):
        raise Exception('Expected package not found: %s' % archive)

    return archive


def load_existing_manifest() -> list:
    """Load the current manifest, if any, so history is preserved."""
    if not os.path.isfile(MANIFEST):
        return []
    try:
        with open(MANIFEST, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    return data if isinstance(data, list) else []


def generate(archive: str, version: str, owner: str, repo: str,
             target_abi: str) -> dict:
    return {
        'checksum': md5sum(archive),
        'changelog': 'Support Jellyfin 12.0 and above. Fix plugin image not being served.',
        'targetAbi': target_abi,
        'sourceUrl': 'https://github.com/%s/%s/releases/download/v%s/%s' % (
            owner, repo, version, os.path.basename(archive)),
        'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'version': version
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version', help='release version, e.g. 2026.1105.0000')
    parser.add_argument('--owner', default=DEFAULT_OWNER)
    parser.add_argument('--repo', default=DEFAULT_REPO)
    parser.add_argument('--skip-build', action='store_true',
                        help='reuse an already built package')
    args = parser.parse_args()

    version = args.version.lstrip('v')
    os.makedirs(DIST_DIR, exist_ok=True)

    if args.skip_build:
        archive = os.path.join(
            REPO_ROOT, 'Jellyfin.Plugin.MetaTube', 'bin',
            'Jellyfin.MetaTube@v%s.zip' % version)
        if not os.path.isfile(archive):
            raise Exception('Expected package not found: %s' % archive)
    else:
        archive = build_plugin(version)

    # Keep a copy of the exact package next to the manifest.
    dist_archive = os.path.join(DIST_DIR, os.path.basename(archive))
    if os.path.abspath(archive) != os.path.abspath(dist_archive):
        shutil.copy2(archive, dist_archive)

    target_abi = get_target_abi()
    entry = generate(archive, version, args.owner, args.repo, target_abi)

    manifest = load_existing_manifest()
    if not manifest:
        manifest = [{
            'guid': PLUGIN_GUID,
            'name': PLUGIN_NAME,
            'description': PLUGIN_DESCRIPTION,
            'overview': PLUGIN_DESCRIPTION,
            'owner': PLUGIN_NAME,
            'category': PLUGIN_CATEGORY,
            'imageUrl': 'https://raw.githubusercontent.com/%s/%s/main/'
                       'Jellyfin.Plugin.MetaTube/thumb.png' % (args.owner, args.repo),
            'versions': []
        }]

    # Newest first, and never list the same version twice.
    manifest[0]['versions'] = [
        v for v in manifest[0]['versions'] if v.get('version') != version]
    manifest[0]['versions'].insert(0, entry)

    with open(MANIFEST, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write('\n')

    print()
    print('manifest      : %s' % MANIFEST)
    print('package       : %s' % dist_archive)
    print('version       : %s' % version)
    print('targetAbi     : %s' % target_abi)
    print('checksum      : %s' % entry['checksum'])
    print('sourceUrl     : %s' % entry['sourceUrl'])
    print()
    print('Next steps:')
    print('  1. Publish the package as a release asset named %s'
          % os.path.basename(archive))
    print('     tag: v%s' % version)
    print('  2. Copy repository/manifest.json onto the dist branch and push it')
    print('  3. Add the repository URL to Jellyfin:')
    print('     https://raw.githubusercontent.com/%s/%s/dist/manifest.json'
          % (args.owner, args.repo))


if __name__ == '__main__':
    main()
