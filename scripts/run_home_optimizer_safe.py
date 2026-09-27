from pathlib import Path
import runpy

TARGET = Path("scripts/optimize_home_for_immediate_discovery.py")
text = TARGET.read_text(encoding="utf-8")
old = "text = re.sub(r'<main\\b.*?</main>', build_main(), text, count=1, flags=re.S)"
new = "text = re.sub(r'<main\\b.*?</main>', lambda _m: build_main(), text, count=1, flags=re.S)"
if old in text:
    TARGET.write_text(text.replace(old, new, 1), encoding="utf-8")
elif new not in text:
    raise SystemExit("Homepage optimizer patch target not found")

runpy.run_path(str(TARGET), run_name="__main__")
