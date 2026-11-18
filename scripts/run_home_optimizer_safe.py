from pathlib import Path
import runpy
import sys

# This wrapper is the one script that every deploy path runs (daily rebuild, fast deploy,
# link hotfix, alias merge, description enrichment). Each of those except the daily
# rebuild restores an older production snapshot first, and a snapshot can still contain
# HTML pages saved without a .html extension. Cloudflare Pages serves those as
# application/octet-stream downloads, so repair them here before anything is deployed.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import normalize_public_routes  # noqa: E402

_renamed, _removed = normalize_public_routes.normalize()
print(f"Public routes normalized: renamed={_renamed} removed_duplicates={_removed}")

TARGET = Path("scripts/optimize_home_for_immediate_discovery.py")
text = TARGET.read_text(encoding="utf-8")
old = "text = re.sub(r'<main\\b.*?</main>', build_main(), text, count=1, flags=re.S)"
new = "text = re.sub(r'<main\\b.*?</main>', lambda _m: build_main(), text, count=1, flags=re.S)"
if old in text:
    TARGET.write_text(text.replace(old, new, 1), encoding="utf-8")
elif new not in text:
    raise SystemExit("Homepage optimizer patch target not found")

runpy.run_path(str(TARGET), run_name="__main__")
