"""GPL-3.0-only. Verify a Gradle 2.7 ZIP before any JVM runs; never starts Java.

The exact legacy MDK wrapper lacks SHA256 enforcement. Run this helper first,
then extract the verified ZIP in the task cache and invoke that distribution.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import urllib.request

URL = "https://services.gradle.org/distributions/gradle-2.7-bin.zip"
SHA256 = "cde43b90945b5304c43ee36e58aab4cc6fb3a3d5f9bd9449bb1709a68371cb06"


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default = (Path("E:/CodexTemp/QiZhangVerdict/legacy-build/1.8.9/tools")
               if os.name == "nt" else Path(tempfile.gettempdir()) / "qizhangverdict-1.8.9-tools")
    parser.add_argument("--cache-root", type=Path, default=default)
    parser.add_argument("--download", action="store_true", help="Download only when the ZIP does not exist")
    args = parser.parse_args()
    root = args.cache_root.resolve()
    project = Path(__file__).resolve().parents[2]
    if root == project or project in root.parents:
        parser.error("Gradle cache must be outside the project tree")
    destination = root / "gradle-2.7-bin.zip"
    if not destination.exists():
        if not args.download:
            parser.error("No cached Gradle ZIP; use --download to fetch the pinned official distribution")
        root.mkdir(parents=True, exist_ok=True)
        partial = root / "gradle-2.7-bin.zip.part"
        # Exclusive creation preserves any interrupted download for inspection.
        request = urllib.request.Request(URL, headers={"User-Agent": "QiZhangVerdict-build-preflight"})
        with partial.open("xb") as out, urllib.request.urlopen(request, timeout=45) as response:
            total = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > 200 * 1024 * 1024:
                    raise ValueError("Unexpected Gradle ZIP size")
                out.write(chunk)
        if digest(partial) != SHA256:
            raise ValueError("Gradle SHA256 mismatch; untrusted partial file retained, nothing executed")
        # Exclusive destination creation also refuses concurrent replacement on POSIX.
        with partial.open("rb") as source, destination.open("xb") as out:
            shutil.copyfileobj(source, out)
        if digest(destination) != SHA256:
            raise ValueError("Verified ZIP copy mismatch; files retained, nothing executed")
        partial.unlink()
    if digest(destination) != SHA256:
        raise ValueError("Cached Gradle SHA256 mismatch; file retained, nothing executed")
    print(json.dumps({"verified": True, "zip": str(destination), "sha256": SHA256,
                      "javaStarted": False, "extracted": False}))


if __name__ == "__main__":
    main()
