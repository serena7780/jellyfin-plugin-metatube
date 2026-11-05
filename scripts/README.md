# Plugin repository

This plugin is published as a Jellyfin plugin repository, served as a plain
JSON manifest. It follows the same layout as the upstream project, so a
Jellyfin server can install it directly.

## Layout

| Branch / Path | Contents |
| --- | --- |
| `main` | plugin source |
| `dist` | `manifest.json` — the plugin repository manifest |

The manifest is served from the `dist` branch:

```
https://raw.githubusercontent.com/serena7780/jellyfin-plugin-metatube/dist/manifest.json
```

The packages themselves are served as GitHub release assets, referenced by the
manifest's `sourceUrl` entries.

## Adding the repository to Jellyfin

In the Jellyfin dashboard:

1. Go to **Dashboard → Plugins → Manage Repositories**
2. Click **Add Repository**
3. Enter the manifest URL:

   ```
   https://raw.githubusercontent.com/serena7780/jellyfin-plugin-metatube/dist/manifest.json
   ```

4. Save, then open **Plugins → Catalog** and install **MetaTube**

## Publishing a new release

The manifest and the package must be produced together: the server verifies the
MD5 of the downloaded zip against the manifest's `checksum` field, so the two
must describe the exact same bytes. Zip archives embed timestamps, so a
checksum copied from an earlier build will not match.

Use the publish script, which builds the package and regenerates the manifest
in one step:

```bash
python3 -m pip install packaging
python3 scripts/publish.py 2026.1105.0000
```

This writes:

- `repository/Jellyfin.MetaTube@v2026.1105.0000.zip` — the package
- `repository/manifest.json` — the regenerated manifest

Then publish the package and update the `dist` branch:

```bash
# 1. Publish the package as a release asset, tagged v2026.1105.0000
gh release create v2026.1105.0000 \
    "repository/Jellyfin.MetaTube@v2026.1105.0000.zip" \
    --title "v2026.1105.0000"

# 2. Copy the manifest onto the dist branch
git checkout dist
cp repository/manifest.json .
git commit -am "Auto Updated by Actions"
git push origin dist

# 3. Return to main
git checkout main
```

The `dist` branch is an orphan branch containing only `manifest.json`. To
recreate it from scratch:

```bash
git checkout --orphan dist
git rm -rf --cached . -q
rm -rf ./* .github .gitignore
cp repository/manifest.json .
git add manifest.json
git commit -m "Auto Updated by Actions"
git push -f origin dist
```

## Manifest format

The manifest is a JSON array of `PackageInfo` objects, as defined by
`MediaBrowser.Model.Updates.PackageInfo` in Jellyfin:

```json
[
  {
    "guid": "01cc53ec-c415-4108-bbd4-a684a9801a32",
    "name": "MetaTube",
    "description": "MetaTube Plugin for Jellyfin/Emby.",
    "overview": "MetaTube Plugin for Jellyfin/Emby.",
    "owner": "MetaTube",
    "category": "Metadata",
    "imageUrl": "https://raw.githubusercontent.com/serena7780/jellyfin-plugin-metatube/main/Jellyfin.Plugin.MetaTube/thumb.png",
    "versions": [
      {
        "checksum": "33a4554bb232670a410149c2736b2b7a",
        "changelog": "Support Jellyfin 12.0 and above.",
        "targetAbi": "12.0.0",
        "sourceUrl": "https://github.com/serena7780/jellyfin-plugin-metatube/releases/download/v2026.1105.0000/Jellyfin.MetaTube@v2026.1105.0000.zip",
        "timestamp": "2026-11-05T13:18:02Z",
        "version": "2026.1105.0000"
      }
    ]
  }
]
```

### Notes on the fields

- **`guid`** must match `Plugin.Id` in `Jellyfin.Plugin.MetaTube/Plugin.cs`,
  otherwise the server treats the installed plugin as a different one.
- **`targetAbi`** is compared against the server version using
  `System.Version`. It must be a plain **three-part** version. A four-part
  value such as `12.0.0.0` compares as *greater* than the three-part `12.0.0`,
  which would cause a Jellyfin 12.0.0 server to reject the plugin. The
  publish script derives this from the `Jellyfin.Controller` package version.
- **`checksum`** is the MD5 of the release asset, computed by the publish
  script from the exact zip it ships with.
- **`sourceUrl`** must point at a release asset with the same name as the
  checksummed file.
- **`versions`** is ordered newest first. The publish script inserts new
  versions at the front and removes any duplicate of the same version.
