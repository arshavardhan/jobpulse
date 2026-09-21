import re
from pathlib import Path
from bs4 import BeautifulSoup

def verify_dom():
    html_path = Path("src/frontend/index.html")
    js_path = Path("src/frontend/app.js")

    assert html_path.exists(), "index.html missing"
    assert js_path.exists(), "app.js missing"

    html_content = html_path.read_text(encoding="utf-8")
    js_content = js_path.read_text(encoding="utf-8")

    soup = BeautifulSoup(html_content, "html.parser")
    dom_ids = set()
    for tag in soup.find_all(id=True):
        dom_ids.add(tag['id'])

    # Find all getElementById calls in js
    referenced_ids = set(re.findall(r"getElementById\(['\"]([a-zA-Z0-9_-]+)['\"]\)", js_content))

    print(f"Total DOM IDs defined in index.html: {len(dom_ids)}")
    print(f"Total IDs referenced in app.js: {len(referenced_ids)}")

    missing = []
    for r_id in referenced_ids:
        # Some dynamic ids like job-card-${job.id}, scope-btn-${s}, etc. might be partially formatted
        if "${" in r_id:
            continue
        if r_id not in dom_ids:
            missing.append(r_id)

    if missing:
        print("WARNING / ERROR: Missing IDs in DOM:")
        for m in missing:
            print(f" - {m}")
        assert False, f"Missing IDs in index.html: {missing}"
    else:
        print("SUCCESS: 100% of DOM IDs in app.js exist in index.html!")

if __name__ == "__main__":
    verify_dom()
