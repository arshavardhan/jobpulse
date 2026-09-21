import requests

BASE_URL = "http://localhost:8000"

def run_smoke_tests():
    print("--- 1. Verifying Root HTML, Home Page & Vendor Name Scrubbing ---")
    resp = requests.get(f"{BASE_URL}/")
    assert resp.status_code == 200, f"Root returned {resp.status_code}"
    assert "JobPulse" in resp.text, "JobPulse brand not found in root HTML"
    assert "Real jobs. Live opportunities. One place." in resp.text, "Tagline not found"
    assert "Autonomous AI Job Discovery &amp; Auto-Apply Engine" in resp.text, "Home hero badge not found"
    assert "How JobPulse Works" in resp.text, "How JobPulse Works pipeline not found"
    assert "Autonomous Application Bot" in resp.text, "Auto-Apply Bot section not found"
    
    # Verify complete scrubbing of vendor names
    html_lower = resp.text.lower()
    assert "lever" not in html_lower, "Found 'lever' in root HTML"
    assert "greenhouse" not in html_lower, "Found 'greenhouse' in root HTML"
    assert "ashby" not in html_lower, "Found 'ashby' in root HTML"
    print("[OK] Root HTML serves JobPulse Home Page with zero ATS vendor names.")

    print("--- 2. Verifying Static Assets ---")
    css = requests.get(f"{BASE_URL}/static/styles.css")
    assert css.status_code == 200, "styles.css failed"
    js = requests.get(f"{BASE_URL}/static/app.js")
    assert js.status_code == 200, "app.js failed"
    print("[OK] Static CSS and JS assets are reachable.")

    print("--- 3. Verifying System Status ---")
    status = requests.get(f"{BASE_URL}/api/system/status")
    assert status.status_code == 200
    st_json = status.json()
    print(f"[OK] System status healthy: {st_json.get('jobs_in_database')} active jobs in DB.")

    print("--- 4. Verifying Jobs API & Canonical Provenance ---")
    jobs = requests.get(f"{BASE_URL}/api/jobs?limit=5")
    assert jobs.status_code == 200
    j_list = jobs.json()
    assert len(j_list) > 0, "No live jobs returned!"
    sample_job = j_list[0]
    print(f"[OK] Sample live job: '{sample_job['title']}' at '{sample_job['company']}'")
    print(f"  - Apply URL: {sample_job['apply_url']}")
    print(f"  - Canonical Source: {sample_job.get('canonical_source')}")
    print(f"  - Sources Provenance: {sample_job.get('sources')}")
    assert sample_job["apply_url"].startswith("http"), "Invalid apply_url"

    print("--- 5. Verifying Sources Health Endpoint ---")
    health = requests.get(f"{BASE_URL}/api/sources/health")
    assert health.status_code == 200
    h_list = health.json()
    assert len(h_list) >= 8
    names = [h["source"] for h in h_list]
    print(f"[OK] Registered sources monitored ({len(h_list)}): {names}")
    for bound in ["linkedin", "indeed", "naukri"]:
        match = next((h for h in h_list if h["source"] == bound), None)
        assert match is not None, f"Missing boundary: {bound}"
        print(f"  - [{bound.upper()}] Status: {match.get('status')} (Requires Auth: {match.get('requires_auth')})")

    print("--- 6. Verifying Companies Directory ---")
    comps = requests.get(f"{BASE_URL}/api/companies")
    assert comps.status_code == 200
    c_list = comps.json()
    assert len(c_list) > 0
    top_comp = c_list[0]
    print(f"[OK] Companies directory ({len(c_list)} tracked companies). Top: '{top_comp['company_name']}' ({top_comp['job_count']} jobs)")

    print("--- 7. Verifying Contact Submission ---")
    contact_res = requests.post(f"{BASE_URL}/api/contact", json={
        "name": "Alex Smith",
        "email": "alex@example.org",
        "subject": "Platform Partnership",
        "category": "Partnership",
        "message": "We would like to onboard our direct career board."
    })
    assert contact_res.status_code == 200
    c_res = contact_res.json()
    print(f"[OK] Contact submission saved: ID {c_res['id']}, status: {c_res['status']}")

    print("--- 8. Verifying Job Issue Reporting ---")
    rep_res = requests.post(f"{BASE_URL}/api/jobs/{sample_job['id']}/report", json={
        "reason": "Broken link",
        "details": "Checking automated reachability workflow.",
        "reporter_email": "tester@example.com"
    })
    assert rep_res.status_code == 200
    r_res = rep_res.json()
    print(f"[OK] Job report filed: ID {r_res['id']} for job {sample_job['id']}, status: {r_res['status']}")

    print("--- 9. Verifying ATS Diagnostic Audit ---")
    ats_res = requests.post(f"{BASE_URL}/api/ats-check", json={
        "resume_text": "Experienced Python developer with 4 years building microservices in FastAPI, PostgreSQL, and Docker. Implemented distributed pipelines.",
        "target_role": "Senior Python Backend Developer",
        "experience_level": "Mid-Level"
    })
    assert ats_res.status_code == 200, f"ATS check failed: {ats_res.text}"
    ats_json = ats_res.json()
    print(f"[OK] ATS Audit: Overall Fit: {ats_json['overall_score']}%, Keyword Match: {ats_json['keyword_match_score']}%")
    print(f"  - Matched skills: {ats_json['matched_skills']}")
    print(f"  - Generated Google XYZ bullets: {len(ats_json['tailored_resume_bullet_fixes'])}")

    print("--- 10. Verifying PDF Resume Denoising & Parsing Endpoint ---")
    import pymupdf as fitz
    import io
    test_doc = fitz.open()
    test_page = test_doc.new_page()
    test_page.insert_text((50, 50), "Rajesh Kumar\nBackend Engineer\nrajesh.kumar@example.in")
    test_page.insert_text((50, 100), "Experience: 4 years of experience building Python APIs.")
    test_page.insert_text((50, 150), "Skills: Python, FastAPI, Docker, PostgreSQL, Redis, Kubernetes.")
    pdf_bytes = test_doc.tobytes()

    pdf_res = requests.post(f"{BASE_URL}/api/resume/parse", files={
        "file": ("rajesh_kumar.pdf", io.BytesIO(pdf_bytes), "application/pdf")
    })
    assert pdf_res.status_code == 200, f"PDF parse failed: {pdf_res.text}"
    pdf_json = pdf_res.json()
    print(f"[OK] PDF Parse: Success={pdf_json['success']}, Name='{pdf_json['name']}', Email='{pdf_json['email']}'")
    print(f"  - Clean Text snippet: {repr(pdf_json['clean_text'][:80])}")
    print(f"  - Detected skills: {pdf_json['skills']}")

    print("--- 11. Verifying Auto-Apply Bot Batch Execution (LazyApply / JobPilot Style) ---")
    batch_res = requests.post(f"{BASE_URL}/api/copilot/auto-apply-batch?count=2&min_match_score=50")
    assert batch_res.status_code == 200, f"Batch apply failed: {batch_res.text}"
    batch_json = batch_res.json()
    print(f"[OK] Auto-Apply Batch: Status={batch_json.get('status')}, Count={batch_json.get('applied_count')}")
    print(f"  - Execution Logs ({len(batch_json.get('execution_logs', []))} events):")
    for log in batch_json.get('execution_logs', [])[:3]:
        print(f"    > {log}")

    print("--- 12. Verifying 1-Click Copilot Apply for Individual Job ---")
    copilot_one_res = requests.post(f"{BASE_URL}/api/copilot/apply-one/{sample_job['id']}")
    assert copilot_one_res.status_code == 200, f"Copilot 1-click failed: {copilot_one_res.text}"
    cop_json = copilot_one_res.json()
    print(f"[OK] 1-Click Copilot Apply: Status={cop_json.get('status')}, Message='{cop_json.get('message')}'")

    print("--- 13. Verifying Multi-Role Domain Ingestion & Domain Endpoints ---")
    dom_res = requests.get(f"{BASE_URL}/api/jobs/domains")
    assert dom_res.status_code == 200, f"Domains endpoint failed: {dom_res.text}"
    dom_json = dom_res.json()
    print(f"[OK] Jobs by Role Domain (Total Active: {dom_json['total_active']}):")
    for d in dom_json["domains"]:
        print(f"  - {d['name']}: {d['count']} live openings")
    assert dom_json["total_active"] >= 300, f"Expected 300+ jobs, got {dom_json['total_active']}"

    # Verify filtering by non-dev domains
    for test_dom in ["Product", "Design", "Marketing", "Sales"]:
        filt_res = requests.get(f"{BASE_URL}/api/jobs?role_domain={test_dom}&limit=3")
        assert filt_res.status_code == 200
        filt_jobs = filt_res.json()
        print(f"  - Filter query role_domain='{test_dom}': {len(filt_jobs)} sample jobs returned.")

    print("\n========================================================")
    print("ALL 13 LIVE SMOKE TESTS PASSED 100%!")
    print("========================================================")

if __name__ == "__main__":
    run_smoke_tests()
