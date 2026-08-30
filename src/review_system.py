import os
import json
import sys
import argparse
import pandas as pd
from datetime import datetime
from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS

# Import local engines
from rule_checker import NetworkRuleChecker
from ai_diagnoser import AIDiagnoser

app = Flask(__name__)
CORS(app)

# Paths
DATA_DIR = "data"
CASES_CSV = os.path.join(DATA_DIR, "cases.csv")
REVIEWS_JSON = os.path.join(DATA_DIR, "reviews.json")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)

# Initialize checkers
ai_diagnoser = AIDiagnoser()

def load_cases():
    """Loads cases from CSV."""
    if not os.path.exists(CASES_CSV):
        print(f"Error: {CASES_CSV} not found. Please run the case generator first.")
        return []
    df = pd.read_csv(CASES_CSV)
    # Ensure NaN values are handled
    df = df.fillna("")
    return df.to_dict(orient="records")

def load_reviews():
    """Loads human reviews from JSON."""
    if not os.path.exists(REVIEWS_JSON):
        return {}
    try:
        with open(REVIEWS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading reviews: {e}")
        return {}

def save_reviews(reviews):
    """Saves human reviews to JSON."""
    try:
        with open(REVIEWS_JSON, "w", encoding="utf-8") as f:
           
        return True
    except Exception as e:
        print(f"Error saving reviews: {e}")
        return False

# ==============================================================================
# CLI REVIEW SYSTEM
# ==============================================================================
def run_cli_review():
    print("=" * 70)
    print("               NETSAGE AI - HUMAN-IN-THE-LOOP CLI GATE")
    print("=" * 70)
    
    cases = load_cases()
    if not cases:
        return
        
    reviews = load_reviews()
    pending_cases = [c for c in cases if c["id"] not in reviews]
    print(f"Total Database Cases: {len(cases)} | Pending human review: {len(pending_cases)}")
    
    if not pending_cases:
        print("All cases have been reviewed!")
        return
        
    for case in pending_cases:
        case_id = case["id"]
        domain = case["domain"]
        symptom = case["symptom"]
        topology = case["topology_notes"]
        show_outputs = case["show_outputs"]
        
        print("\n" + "#" * 60)
        print(f"CASE: {case_id} | Fault Domain: {domain}")
        print("#" * 60)
        print(f"Symptom: {symptom}")
        print(f"Topology: {topology}\n")
        print("Show Command Outputs:")
        for line in show_outputs.splitlines():
            print(f"  | {line}")
        print("-" * 60)
        
        # 1. Run Deterministic Checker
        det_res = NetworkRuleChecker.audit_config(show_outputs)
        print(f"Deterministic Python Rule Checker ({det_res['deterministic_faults_found']} faults found):")
        for find in det_res["findings"]:
            print(f"  [!] Rule: {find['rule']} | Layer: {find['layer']}")
            print(f"      Detail: {find['detail']}")
            print(f"      Suggested Fix: {find['suggested_fix']}")
        print("-" * 60)
        
        # 2. Run AI Diagnoser
        print("Diagnosing with AI engine...")
        ai_resp = ai_diagnoser.diagnose(symptom, topology, show_outputs, case_id)
        
        print(f"AI Suspected Fault:   {ai_resp.get('suspected_fault')}")
        print(f"AI OSI Layer:         {ai_resp.get('osi_layer')}")
        print(f"AI Confidence:        {ai_resp.get('confidence')}")
        print(f"AI Evidence:          {', '.join(ai_resp.get('evidence_extracted', []))}")
        print(f"AI Next Verify:       {ai_resp.get('next_verification_command')}")
        print(f"AI Remediation:       {', '.join(ai_resp.get('remediation_steps', []))}")
        print(f"AI Safety Flag:       {ai_resp.get('safety_flag')}")
        print("-" * 60)
        
        # 3. Prompt Action
        while True:
            choice = input("Decision: [A]ccept, [E]dit, [R]eject, [S]kip, [Q]uit: ").strip().lower()
            if choice == 'q':
                print("Exiting review gate. Changes saved.")
                return
            elif choice == 's':
                print("Skipping case...")
                break
            elif choice == 'a':
                reviews[case_id] = {
                    "case_id": case_id,
                    "domain": domain,
                    "symptom": symptom,
                    "topology_notes": topology,
                    "show_outputs": show_outputs,
                    "deterministic_findings": det_res,
                    "ai_diagnosis": ai_resp,
                    "review_status": "Accepted",
                    "reviewed_by": "Human Auditor (CLI)",
                    "reviewed_at": datetime.now().isoformat(),
                    "final_suspected_fault": ai_resp.get("suspected_fault"),
                    "final_osi_layer": ai_resp.get("osi_layer"),
                    "final_confidence": ai_resp.get("confidence"),
                    "final_evidence_extracted": ai_resp.get("evidence_extracted", []),
                    "final_next_verification_command": ai_resp.get("next_verification_command"),
                    "final_remediation_steps": ai_resp.get("remediation_steps", []),
                    "final_safety_flag": ai_resp.get("safety_flag"),
                    "notes": ""
                }
                save_reviews(reviews)
                print(f"Saved {case_id} as Accepted.")
                break
            elif choice == 'r':
                notes = input("Enter rejection reason: ").strip()
                reviews[case_id] = {
                    "case_id": case_id,
                    "domain": domain,
                    "symptom": symptom,
                    "topology_notes": topology,
                    "show_outputs": show_outputs,
                    "deterministic_findings": det_res,
                    "ai_diagnosis": ai_resp,
                    "review_status": "Rejected",
                    "reviewed_by": "Human Auditor (CLI)",
                    "reviewed_at": datetime.now().isoformat(),
                    "final_suspected_fault": "Rejected / False Positive",
                    "final_osi_layer": "Layer 1",
                    "final_confidence": "Low",
                    "final_evidence_extracted": [],
                    "final_next_verification_command": "",
                    "final_remediation_steps": [],
                    "final_safety_flag": "Low Risk",
                    "notes": notes
                }
                save_reviews(reviews)
                print(f"Saved {case_id} as Rejected.")
                break
            elif choice == 'e':
                print("\n--- Editing Mode ---")
                final_fault = input(f"Suspected Fault [{ai_resp.get('suspected_fault')}]: ").strip() or ai_resp.get("suspected_fault")
                final_layer = input(f"OSI Layer [{ai_resp.get('osi_layer')}]: ").strip() or ai_resp.get("osi_layer")
                final_conf = input(f"Confidence [{ai_resp.get('confidence')}]: ").strip() or ai_resp.get("confidence")
                
                evidence_str = input(f"Evidence (comma separated) [{', '.join(ai_resp.get('evidence_extracted', []))}]: ").strip()
                final_evidence = [x.strip() for x in evidence_str.split(",") if x.strip()] if evidence_str else ai_resp.get("evidence_extracted", [])
                
                final_verify = input(f"Next Verify Cmd [{ai_resp.get('next_verification_command')}]: ").strip() or ai_resp.get("next_verification_command")
                
                remed_str = input(f"Remediation steps (comma separated) [{', '.join(ai_resp.get('remediation_steps', []))}]: ").strip()
                final_remed = [x.strip() for x in remed_str.split(",") if x.strip()] if remed_str else ai_resp.get("remediation_steps", [])
                
                final_safety = input(f"Safety Flag [{ai_resp.get('safety_flag')}]: ").strip() or ai_resp.get("safety_flag")
                notes = input("Correction notes: ").strip()
                
                reviews[case_id] = {
                    "case_id": case_id,
                    "domain": domain,
                    "symptom": symptom,
                    "topology_notes": topology,
                    "show_outputs": show_outputs,
                    "deterministic_findings": det_res,
                    "ai_diagnosis": ai_resp,
                    "review_status": "Edited",
                    "reviewed_by": "Human Auditor (CLI)",
                    "reviewed_at": datetime.now().isoformat(),
                    "final_suspected_fault": final_fault,
                    "final_osi_layer": final_layer,
                    "final_confidence": final_conf,
                    "final_evidence_extracted": final_evidence,
                    "final_next_verification_command": final_verify,
                    "final_remediation_steps": final_remed,
                    "final_safety_flag": final_safety,
                    "notes": notes
                }
                save_reviews(reviews)
                print(f"Saved {case_id} as Edited.")
                break

# ==============================================================================
# WEB REVIEW DEPLOYMENT
# ==============================================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NetSage AI Advisor - Human-in-the-Loop Gate</title>
    <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0b0f19;
            --bg-card: #161f30;
            --border-color: #24354f;
            --primary: #6366f1;
            --primary-hover: #4f46e5;
            --text-main: #f8fafc;
            --text-secondary: #94a3b8;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --accent: #06b6d4;
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-dark);
            color: var(--text-main);
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        header {
            background-color: var(--bg-card);
            border-bottom: 1px solid var(--border-color);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 10;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.3);
        }
        
        header h1 {
            font-size: 1.48rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            background: linear-gradient(to right, var(--accent), var(--primary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .header-controls {
            display: flex;
            align-items: center;
            gap: 1.5rem;
        }
        
        .stats-summary {
            display: flex;
            gap: 0.75rem;
        }
        
        .stat-badge {
            background-color: rgba(36, 53, 79, 0.4);
            padding: 0.35rem 0.75rem;
            border-radius: 6px;
            font-size: 0.8rem;
            border: 1px solid var(--border-color);
        }
        
        .stat-badge span.num {
            font-weight: 700;
            color: var(--accent);
        }
        
        .main-container {
            display: flex;
            flex: 1;
            overflow: hidden;
        }
        
        /* SIDEBAR */
        .sidebar {
            width: 320px;
            background-color: rgba(22, 31, 48, 0.5);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            overflow-y: auto;
        }
        
        .sidebar-title {
            padding: 1.2rem;
            border-bottom: 1px solid var(--border-color);
            font-weight: 600;
            color: var(--text-secondary);
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05rem;
        }
        
        .case-list {
            list-style: none;
        }
        
        .case-item {
            padding: 1rem 1.2rem;
            border-bottom: 1px solid rgba(36, 53, 79, 0.3);
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .case-item:hover {
            background-color: rgba(36, 53, 79, 0.25);
        }
        
        .case-item.active {
            background-color: rgba(99, 102, 241, 0.15);
            border-left: 4px solid var(--primary);
        }
        
        .case-meta {
            display: flex;
            flex-direction: column;
            gap: 0.2rem;
        }
        
        .case-id {
            font-weight: 600;
            font-size: 0.95rem;
        }
        
        .case-domain {
            font-size: 0.75rem;
            color: var(--text-secondary);
        }
        
        .status-badge {
            font-size: 0.72rem;
            padding: 0.18rem 0.5rem;
            border-radius: 9999px;
            font-weight: 500;
        }
        
        .st-pending { background-color: #334155; color: #cbd5e1; }
        .st-accepted { background-color: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
        .st-edited { background-color: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
        .st-rejected { background-color: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }

        /* WORKSPACE */
        .workspace {
            flex: 1;
            overflow-y: auto;
            padding: 1.5rem 2rem;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }
        
        .case-detail-card {
            background-color: var(--bg-card);
            border-radius: 10px;
            padding: 1.25rem 1.5rem;
            border: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }
        
        .detail-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(36, 53, 79, 0.5);
            padding-bottom: 0.5rem;
        }
        
        .detail-title {
            font-size: 1.2rem;
            font-weight: 600;
            color: var(--text-main);
        }
        
        .meta-group {
            display: flex;
            gap: 1rem;
            font-size: 0.85rem;
            color: var(--text-secondary);
        }
        
        .meta-group strong {
            color: var(--text-main);
        }
        
        .box-symptom {
            background-color: rgba(11, 15, 25, 0.6);
            padding: 1rem;
            border-radius: 6px;
            border-left: 4px solid var(--accent);
            font-size: 0.92rem;
            line-height: 1.5;
        }
        
        .grid-panels {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
        }
        
        .workspace-panel {
            background-color: var(--bg-card);
            border-radius: 10px;
            border: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .w-panel-header {
            padding: 0.85rem 1.2rem;
            border-bottom: 1px solid var(--border-color);
            font-weight: 600;
            background-color: rgba(11, 15, 25, 0.3);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .w-panel-body {
            padding: 1.2rem;
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow-y: auto;
        }
        
        pre.terminal-log {
            background-color: #05070c;
            color: #38bdf8;
            padding: 1rem;
            border-radius: 6px;
            font-family: 'Fira Code', monospace;
            font-size: 0.85rem;
            line-height: 1.5;
            white-space: pre-wrap;
            overflow-x: auto;
            border: 1px solid rgba(255,255,255,0.03);
            flex: 1;
        }
        
        /* REGEX FINDINGS */
        .regex-finding-card {
            background-color: rgba(239, 68, 68, 0.08);
            border: 1px solid rgba(239, 68, 68, 0.25);
            border-left: 4px solid var(--danger);
            padding: 0.85rem 1rem;
            border-radius: 6px;
            margin-bottom: 0.75rem;
        }
        
        .regex-finding-card.no-faults {
            background-color: rgba(16, 185, 129, 0.08);
            border: 1px solid rgba(16, 185, 129, 0.25);
            border-left: 4px solid var(--success);
            color: var(--text-secondary);
        }
        
        .finding-title {
            font-weight: 600;
            font-size: 0.92rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.25rem;
        }
        
        .finding-detail {
            font-size: 0.82rem;
            color: var(--text-secondary);
            margin-bottom: 0.4rem;
        }
        
        .finding-fix {
            font-family: 'Fira Code', monospace;
            font-size: 0.78rem;
            color: var(--accent);
            background-color: rgba(0,0,0,0.2);
            padding: 0.3rem 0.5rem;
            border-radius: 4px;
        }
        
        /* AI SCHEMA DISPLAY */
        .schema-card {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }
        
        .schema-field {
            background-color: rgba(11, 15, 25, 0.4);
            border: 1px solid var(--border-color);
            padding: 0.65rem 0.9rem;
            border-radius: 6px;
        }
        
        .field-title {
            font-size: 0.7rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.03rem;
            margin-bottom: 0.2rem;
        }
        
        .field-content {
            font-size: 0.9rem;
            line-height: 1.4;
        }
        
        .layer-tag {
            font-size: 0.72rem;
            font-weight: 600;
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            background-color: var(--primary);
            color: white;
            text-transform: uppercase;
        }
        
        /* ACTIONS & EDITING */
        .actions-card {
            background-color: var(--bg-card);
            border-radius: 10px;
            border: 1px solid var(--border-color);
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        
        .actions-row {
            display: flex;
            gap: 1rem;
        }
        
        .action-btn {
            flex: 1;
            padding: 0.75rem;
            border: none;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            font-size: 0.92rem;
        }
        
        .btn-accept { background: linear-gradient(to right, #10b981, #059669); }
        .btn-accept:hover { opacity: 0.9; transform: translateY(-1px); }
        .btn-edit { background: linear-gradient(to right, #f59e0b, #d97706); }
        .btn-edit:hover { opacity: 0.9; transform: translateY(-1px); }
        .btn-reject { background: linear-gradient(to right, #ef4444, #dc2626); }
        .btn-reject:hover { opacity: 0.9; transform: translateY(-1px); }
        
        /* CORRECTION FORM */
        .correction-form {
            display: none;
            flex-direction: column;
            gap: 0.85rem;
            border-top: 1px solid var(--border-color);
            padding-top: 1.2rem;
            margin-top: 0.5rem;
        }
        
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
        }
        
        .form-group {
            display: flex;
            flex-direction: column;
            gap: 0.35rem;
        }
        
        .form-group label {
            font-size: 0.8rem;
            font-weight: 500;
            color: var(--text-secondary);
        }
        
        .form-group input, .form-group textarea, .form-group select {
            background-color: rgba(11, 15, 25, 0.8);
            border: 1px solid var(--border-color);
            padding: 0.6rem;
            border-radius: 5px;
            color: var(--text-main);
            font-family: inherit;
            font-size: 0.9rem;
        }
        
        .form-group textarea {
            min-height: 80px;
            font-family: 'Fira Code', monospace;
            font-size: 0.85rem;
        }
        
        .form-group input:focus, .form-group textarea:focus, .form-group select:focus {
            outline: none;
            border-color: var(--primary);
        }
    </style>
</head>
<body>

    <header>
        <h1><span>🛡️</span> NetSage AI Advisor</h1>
        <div class="header-controls">
            <div class="stats-summary">
                <div class="stat-badge">Total Cases: <span class="num" id="stat-total">0</span></div>
                <div class="stat-badge">Reviewed: <span class="num" id="stat-reviewed">0</span></div>
                <div class="stat-badge">Accepted: <span class="num" id="stat-accepted" style="color:var(--success)">0</span></div>
                <div class="stat-badge">Edited: <span class="num" id="stat-edited" style="color:var(--warning)">0</span></div>
                <div class="stat-badge">Rejected: <span class="num" id="stat-rejected" style="color:var(--danger)">0</span></div>
            </div>
        </div>
    </header>

    <div class="main-container">
        <!-- SIDEBAR -->
        <div class="sidebar">
            <div class="sidebar-title">Networking Cases</div>
            <ul class="case-list" id="case-list-ul">
                <!-- Populated dynamically -->
            </ul>
        </div>
        
        <!-- WORKSPACE -->
        <div class="workspace" id="workspace-div">
            <div style="display:flex; justify-content:center; align-items:center; height:100%; color:var(--text-secondary)">
                Select a network case to begin evaluation and human validation.
            </div>
        </div>
    </div>

    <script>
        let cases = [];
        let activeCase = null;
        let activeDiagnosis = null;

        async function loadInitData() {
            try {
                const casesResp = await fetch('/api/cases');
                cases = await casesResp.json();
                
                const statsResp = await fetch('/api/stats');
                const stats = await statsResp.json();
                updateStatsUI(stats);
                
                renderSidebar();
                
                if (cases.length > 0) {
                    selectCase(cases[0].id);
                }
            } catch (err) {
                console.error("Initialization error:", err);
            }
        }

        function updateStatsUI(stats) {
            document.getElementById('stat-total').innerText = stats.total_cases;
            document.getElementById('stat-reviewed').innerText = stats.reviewed_count;
            document.getElementById('stat-accepted').innerText = stats.status_counts.Accepted || 0;
            document.getElementById('stat-edited').innerText = stats.status_counts.Edited || 0;
            document.getElementById('stat-rejected').innerText = stats.status_counts.Rejected || 0;
        }

        function renderSidebar() {
            const ul = document.getElementById('case-list-ul');
            ul.innerHTML = '';
            
            cases.forEach(c => {
                const li = document.createElement('li');
                li.className = `case-item ${activeCase && activeCase.id === c.id ? 'active' : ''}`;
                li.onclick = () => selectCase(c.id);
                
                let label = 'Pending';
                let cls = 'st-pending';
                if (c.review_status) {
                    label = c.review_status;
                    cls = `st-${c.review_status.toLowerCase()}`;
                }
                
                li.innerHTML = `
                    <div class="case-meta">
                        <span class="case-id">${c.id}</span>
                        <span class="case-domain">${c.domain}</span>
                    </div>
                    <span class="status-badge ${cls}">${label}</span>
                `;
                ul.appendChild(li);
            });
        }

        async function selectCase(caseId) {
            activeCase = cases.find(c => c.id === caseId);
            renderSidebar();
            
            const ws = document.getElementById('workspace-div');
            ws.innerHTML = `
                <div style="display:flex; justify-content:center; align-items:center; height:200px; color:var(--text-secondary)">
                    Diagnosing Configuration ...
                </div>
            `;
            
            try {
                const response = await fetch(`/api/case/${caseId}`);
                const data = await response.json();
                activeDiagnosis = data.ai_diagnosis;
                renderWorkspace(data);
            } catch (err) {
                ws.innerHTML = `<div style="color:var(--danger)">Error querying diagnoser: ${err}</div>`;
            }
        }

        function renderWorkspace(data) {
            const ws = document.getElementById('workspace-div');
            const c = data.case;
            const det = data.deterministic_findings;
            const ai = data.ai_diagnosis;
            const review = data.saved_review;
            
            // Build deterministic checker findings list
            let detHTML = '';
            if (det.findings.length === 0) {
                detHTML = `
                    <div class="regexfinding-card no-faults" style="padding: 1rem; border-radius: 6px; border: 1px dashed var(--border-color); color: var(--text-secondary)">
                        No syntax faults flagged by regex checker.
                    </div>
                `;
            } else {
                det.findings.forEach(f => {
                    detHTML += `
                        <div class="regex-finding-card">
                            <div class="finding-title">
                                <span>${f.rule}</span>
                                <span class="layer-tag" style="background:#4b5563">${f.layer}</span>
                            </div>
                            <div class="finding-detail">${f.detail}</div>
                            <div class="finding-fix">Fix: ${f.suggested_fix}</div>
                        </div>
                    `;
                });
            }
            
            let reviewBanner = '';
            if (c.review_status) {
                let color = 'var(--success)';
                if (c.review_status === 'Edited') color = 'var(--warning)';
                if (c.review_status === 'Rejected') color = 'var(--danger)';
                reviewBanner = `
                    <div style="background-color:rgba(255,255,255,0.02); border:1px solid var(--border-color); padding:0.8rem 1.2rem; border-radius:6px; font-size:0.85rem; display:flex; justify-content:space-between">
                        <div>Status: <span style="font-weight:700; color:${color}">${c.review_status.toUpperCase()}</span></div>
                        <div style="color:var(--text-secondary)">Audited by ${review.reviewed_by} | ${new Date(review.reviewed_at).toLocaleTimeString()}</div>
                    </div>
                `;
            }
            
            ws.innerHTML = `
                ${reviewBanner}
                
                <div class="case-detail-card">
                    <div class="detail-header">
                        <span class="detail-title">${c.id}</span>
                        <div class="meta-group">
                            <span>Domain: <strong>${c.domain}</strong></span>
                        </div>
                    </div>
                    <div class="meta-group">
                        <span>Topology: <strong>${c.topology_notes}</strong></span>
                    </div>
                    <div class="box-symptom">
                        <strong>Symptom Evidence:</strong> ${c.symptom}
                    </div>
                </div>
                
                <div class="grid-panels">
                    <div class="workspace-panel">
                        <div class="w-panel-header">Raw CLI Evidence / Outputs</div>
                        <div class="w-panel-body">
                            <pre class="terminal-log">${c.show_outputs}</pre>
                        </div>
                    </div>
                    
                    <div class="workspace-panel">
                        <div class="w-panel-header">Deterministic Rule Faults</div>
                        <div class="w-panel-body">
                            ${detHTML}
                        </div>
                    </div>
                </div>
                
                <!-- AI Diagnosis Card -->
                <div class="workspace-panel">
                    <div class="w-panel-header">
                        <span>Structured AI Diagnosis Output</span>
                        <span style="font-size:0.75rem; color:var(--accent); font-weight:600">${data.mode === 'api' ? 'Gemini 2.5 Active' : 'Offline Mock Fallback'}</span>
                    </div>
                    <div class="w-panel-body" style="gap:1rem">
                        <div class="form-row">
                            <div class="schema-field">
                                <div class="field-title">Suspected Fault</div>
                                <div class="field-content" style="font-weight:600">${ai.suspected_fault}</div>
                            </div>
                            <div class="schema-field">
                                <div class="field-title">OSI Target Layer</div>
                                <div class="field-content"><span class="layer-tag">${ai.osi_layer}</span></div>
                            </div>
                        </div>
                        
                        <div class="form-row">
                            <div class="schema-field">
                                <div class="field-title">Confidence Rating</div>
                                <div class="field-content" style="font-weight:600">${ai.confidence}</div>
                            </div>
                            <div class="schema-field">
                                <div class="field-title">Risk Safety Flag</div>
                                <div class="field-content" style="color: ${ai.safety_flag.toLowerCase().includes('high') ? 'var(--danger)' : 'var(--success)'}">${ai.safety_flag}</div>
                            </div>
                        </div>
                        
                        <div class="schema-field">
                            <div class="field-title">Evidence Extracted from Outputs</div>
                            <div class="field-content" style="font-family:'Fira Code', monospace; font-size:0.82rem; color:var(--accent)">
                                ${ai.evidence_extracted.map(x => `• ${x}`).join('<br>')}
                            </div>
                        </div>
                        
                        <div class="schema-field">
                            <div class="field-title">Next Verification Command</div>
                            <div class="field-content" style="font-family:'Fira Code', monospace; color:#38bdf8">${ai.next_verification_command}</div>
                        </div>
                        
                        <div class="schema-field">
                            <div class="field-title">Remediation Steps</div>
                            <div class="field-content" style="font-family:'Fira Code', monospace; color:var(--success)">
                                ${ai.remediation_steps.map(x => `• ${x}`).join('<br>')}
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Review Control Center -->
                <div class="actions-card">
                    <div style="font-weight:600; font-size:1rem">Reviewer Gate Actions</div>
                    <div class="actions-row">
                        <button class="action-btn btn-accept" onclick="submitReview('Accepted')">✓ Accept AI Diagnosis</button>
                        <button class="action-btn btn-edit" onclick="toggleEditForm()">✎ Correct Parameters</button>
                        <button class="action-btn btn-reject" onclick="submitReview('Rejected')">✗ Reject / Hallucinated</button>
                    </div>
                    
                    <!-- Form for corrections -->
                    <div class="correction-form" id="correction-block">
                        <div style="font-weight:600; color:var(--warning); margin-bottom:0.5rem">Correct Diagnosis Fields</div>
                        
                        <div class="form-row">
                            <div class="form-group">
                                <label>Suspected Fault</label>
                                <input type="text" id="form-fault" value="${ai.suspected_fault}">
                            </div>
                            <div class="form-group">
                                <label>OSI Layer</label>
                                <select id="form-layer">
                                    <option value="Layer 1" ${ai.osi_layer === 'Layer 1' ? 'selected' : ''}>Layer 1</option>
                                    <option value="Layer 2" ${ai.osi_layer === 'Layer 2' ? 'selected' : ''}>Layer 2</option>
                                    <option value="Layer 3" ${ai.osi_layer === 'Layer 3' ? 'selected' : ''}>Layer 3</option>
                                    <option value="Layer 4" ${ai.osi_layer === 'Layer 4' ? 'selected' : ''}>Layer 4</option>
                                    <option value="Layer 7" ${ai.osi_layer === 'Layer 7' ? 'selected' : ''}>Layer 7</option>
                                </select>
                            </div>
                        </div>
                        
                        <div class="form-row">
                            <div class="form-group">
                                <label>Confidence</label>
                                <select id="form-confidence">
                                    <option value="High" ${ai.confidence === 'High' ? 'selected' : ''}>High</option>
                                    <option value="Medium" ${ai.confidence === 'Medium' ? 'selected' : ''}>Medium</option>
                                    <option value="Low" ${ai.confidence === 'Low' ? 'selected' : ''}>Low</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label>Safety Flag / Risk</label>
                                <input type="text" id="form-safety" value="${ai.safety_flag}">
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <label>Evidence Extracted (one per line)</label>
                            <textarea id="form-evidence">${ai.evidence_extracted.join('\\n')}</textarea>
                        </div>
                        
                        <div class="form-group">
                            <label>Next Verification Command</label>
                            <input type="text" id="form-verify" value="${ai.next_verification_command}">
                        </div>
                        
                        <div class="form-group">
                            <label>Remediation Steps (one command per line)</label>
                            <textarea id="form-remediation">${ai.remediation_steps.join('\\n')}</textarea>
                        </div>
                        
                        <div class="form-group">
                            <label>Auditor Review Notes (Reason for correction)</label>
                            <input type="text" id="form-notes" placeholder="Explain the correction details for Responsible AI logging..." value="${review && review.notes ? review.notes : ''}">
                        </div>
                        
                        <div style="display:flex; gap:1rem; margin-top:0.5rem">
                            <button class="action-btn btn-accept" onclick="saveEditedReview()" style="max-width:200px">Save Changes</button>
                            <button class="action-btn" onclick="toggleEditForm()" style="background:#475569; max-width:120px">Cancel</button>
                        </div>
                    </div>
                </div>
            `;
        }

        function toggleEditForm() {
            const form = document.getElementById('correction-block');
            if (form.style.display === 'flex') {
                form.style.display = 'none';
            } else {
                form.style.display = 'flex';
                form.scrollIntoView({ behavior: 'smooth' });
            }
        }

        async function submitReview(status) {
            let notes = '';
            if (status === 'Rejected') {
                notes = prompt("Identify the AI hallucination or error details:");
                if (notes === null) return;
            }
            
            const payload = {
                case_id: activeCase.id,
                review_status: status,
                final_suspected_fault: status === 'Rejected' ? 'False Positive / Rejected' : activeDiagnosis.suspected_fault,
                final_osi_layer: status === 'Rejected' ? 'Layer 1' : activeDiagnosis.osi_layer,
                final_confidence: status === 'Rejected' ? 'Low' : activeDiagnosis.confidence,
                final_evidence_extracted: status === 'Rejected' ? [] : activeDiagnosis.evidence_extracted,
                final_next_verification_command: status === 'Rejected' ? '' : activeDiagnosis.next_verification_command,
                final_remediation_steps: status === 'Rejected' ? [] : activeDiagnosis.remediation_steps,
                final_safety_flag: status === 'Rejected' ? 'Low Risk' : activeDiagnosis.safety_flag,
                notes: notes
            };
            
            await sendReviewData(payload);
        }

        async function saveEditedReview() {
            const payload = {
                case_id: activeCase.id,
                review_status: 'Edited',
                final_suspected_fault: document.getElementById('form-fault').value,
                final_osi_layer: document.getElementById('form-layer').value,
                final_confidence: document.getElementById('form-confidence').value,
                final_evidence_extracted: document.getElementById('form-evidence').value.split('\\n').map(x => x.trim()).filter(x => x),
                final_next_verification_command: document.getElementById('form-verify').value,
                final_remediation_steps: document.getElementById('form-remediation').value.split('\\n').map(x => x.trim()).filter(x => x),
                final_safety_flag: document.getElementById('form-safety').value,
                notes: document.getElementById('form-notes').value
            };
            
            await sendReviewData(payload);
        }

        async function sendReviewData(payload) {
            try {
                const response = await fetch('/api/review', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const res = await response.json();
                if (res.success) {
                    const cIdx = cases.findIndex(c => c.id === payload.case_id);
                    cases[cIdx].review_status = payload.review_status;
                    
                    const statsResp = await fetch('/api/stats');
                    const stats = await statsResp.json();
                    updateStatsUI(stats);
                    
                    renderSidebar();
                    selectCase(payload.case_id);
                } else {
                    alert("Error saving review: " + res.error);
                }
            } catch (err) {
                alert("Network error: " + err);
            }
        }

        window.onload = loadInitData;
    </script>
</body>
</html>
"""
    </script>
</body>
</html>
"""

# API endpoint: list cases
@app.route('/api/cases')
def api_cases():
    cases = load_cases()
    reviews = load_reviews()
    for c in cases:
        case_id = c["id"]
        if case_id in reviews:
            c["review_status"] = reviews[case_id]["review_status"]
        else:
            c["review_status"] = None
    return jsonify(cases)

# API endpoint: case details and dynamic checkers
@app.route('/api/case/<case_id>')
def api_case_detail(case_id):
    if not c:
        return jsonify({"error": "Case not found"}), 404
        
    symptom = c["symptom"]
    topology = c["topology_notes"]
    show_outputs = c["show_outputs"]
    
    # 1. Deterministic rules
    det_findings = NetworkRuleChecker.audit_config(show_outputs)
    
    # 2. AI diagnosis
    ai_diag = ai_diagnoser.diagnose(symptom, topology, show_outputs, case_id)
    
    saved_review = reviews.get(case_id, None)
    if saved_review:
        c["review_status"] = saved_review["review_status"]
    else:
        c["review_status"] = None
        
    mode = "api" if ai_diagnoser.api_available else "mock"
    
    return jsonify({
        "case": c,
        "deterministic_findings": det_findings,
        "ai_diagnosis": ai_diag,
        "saved_review": saved_review,
        "mode": mode
    })

# API endpoint: submit review
@app.route('/api/review', methods=['POST'])
def api_review():
    data = request.json
# API endpoint: submit review
@app.route('/api/review', methods=['POST'])
def api_review():
    data = request.json
    case_id = data.get("case_id")
    status = data.get("review_status")
    
    if not case_id or not status:
        return jsonify({"success": False, "error": "Missing parameter"}), 400
        
    cases = load_cases()
    c = next((item for item in cases if item["id"] == case_id), None)
    if not c:
        return jsonify({"success": False, "error": "Invalid case_id"}), 404
        
    reviews = load_reviews()
    det_findings = NetworkRuleChecker.audit_config(c["show_outputs"])
    ai_diag = ai_diagnoser.diagnose(c["symptom"], c["topology_notes"], c["show_outputs"], case_id)
    
    reviews[case_id] = {
        "case_id": case_id,
        "domain": c["domain"],
        "symptom": c["symptom"],
        "topology_notes": c["topology_notes"],
        "show_outputs": c["show_outputs"],
        "deterministic_findings": det_findings,
        "ai_diagnosis": ai_diag,
        "review_status": status,
        "reviewed_by": "Human Auditor (Web)",
        "reviewed_at": datetime.now().isoformat(),
        "final_suspected_fault": data.get("final_suspected_fault", ai_diag.get("suspected_fault")),
        "final_osi_layer": data.get("final_osi_layer", ai_diag.get("osi_layer")),
        "final_confidence": data.get("final_confidence", ai_diag.get("confidence")),
        "final_evidence_extracted": data.get("final_evidence_extracted", ai_diag.get("evidence_extracted", [])),
        "final_next_verification_command": data.get("final_next_verification_command", ai_diag.get("next_verification_command")),
        "final_remediation_steps": data.get("final_remediation_steps", ai_diag.get("remediation_steps", [])),
                        <div style="display:flex; gap:1rem; margin-top:0.5rem">
                            <button class="action-btn btn-accept" onclick="saveEditedReview()" style="max-width:200px">Save Changes</button>
                            <button class="action-btn" onclick="toggleEditForm()" style="background:#475569; max-width:120px">Cancel</button>
                        </div>
                    </div>
                </div>
            `;
        }

        function toggleEditForm() {
            const form = document.getElementById('correction-block');
            if (form.style.display === 'flex') {
                form.style.display = 'none';
            } else {
                form.style.display = 'flex';
                form.scrollIntoView({ behavior: 'smooth' });
            }
        }

        async function submitReview(status) {
            let notes = '';
            if (status === 'Rejected') {
                notes = prompt("Identify the AI hallucination or error details:");
                if (notes === null) return;
            }
            
            const payload = {
                case_id: activeCase.id,
                review_status: status,
                final_suspected_fault: status === 'Rejected' ? 'False Positive / Rejected' : activeDiagnosis.suspected_fault,
                final_osi_layer: status === 'Rejected' ? 'Layer 1' : activeDiagnosis.osi_layer,
def web_index():
    return render_template_string(HTML_TEMPLATE)

# ==============================================================================
# MAIN ROUTING
# ==============================================================================
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="NetSage AI review system")
    parser.add_argument('--cli', action='store_true', help="Run in terminal CLI mode.")
    parser.add_argument('--port', type=int, default=5000, help="Web UI port (Default: 5000)")
    args = parser.parse_args()
    
    if not os.path.exists(CASES_CSV):
        print(f"[NetSage] Error: {CASES_CSV} does not exist.")
        sys.exit(1)
        
    if args.cli:
        run_cli_review()
    else:
        print(f"[NetSage] Web server running on http://127.0.0.1:{args.port} ...")
        app.run(debug=True, port=args.port)

                            : 'Unknown';
                            
                        tr.innerHTML = `
                            <td style="font-weight:600;">
                                <div>${r.case_id}</div>
                                <span class="status-badge" style="background-color:rgba(255,255,255,0.02); color:${badgeColor}; border:1px solid ${badgeColor}; padding:0.1rem 0.35rem; font-size:0.68rem; margin-top:0.25rem; display:inline-block;">
                                    ${r.review_status}
                                </span>
                            </td>
                            <td style="color:var(--text-secondary);">${r.domain}</td>
                            <td style="color:#f87171; font-size:0.85rem; font-family:'Fira Code', monospace; background-color:rgba(239, 68, 68, 0.02); border-radius:4px; padding:0.8rem;">
                                ${aiFault}
                            </td>
                            <td style="color:#34d399; font-size:0.85rem; font-family:'Fira Code', monospace; background-color:rgba(16, 185, 129, 0.02); border-radius:4px; padding:0.8rem;">
                                ${r.final_suspected_fault}
                            </td>
                            <td style="font-style:italic; font-size:0.88rem;">
                                ${r.notes || '<span style="color:var(--text-secondary)">No justification provided</span>'}
          
                        `;
                        tbody.appendChild(tr);
                    });
                }
            } catch (err) {
                console.error("Error loading insights:", err);
            }
        }

        window.onload = loadInitData;
    </script>
</body>
</html>
"""

# API endpoint: serve reports/charts
@app.route('/reports/<path:filename>')
def serve_report(filename):
    reports_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../reports'))
    return send_from_directory(reports_dir, filename)

# API endpoint: list cases
@app.route('/api/cases')
def api_cases():
    cases = load_cases()
    reviews = load_reviews()
    for c in cases:
        case_id = c["id"]
        if case_id in reviews:
            c["review_status"] = reviews[case_id]["review_status"]
        else:
            c["review_status"] = None
    return jsonify(cases)

# API endpoint: case details and dynamic checkers
@app.route('/api/case/<case_id>')
def api_case_detail(case_id):
    cases = load_cases()
    reviews = load_reviews()
    
    c = next((item for item in cases if item["id"] == case_id), None)
    if not c:
        return jsonify({"error": "Case not found"}), 404
        
    symptom = c["symptom"]
    topology = c["topology_notes"]
    show_outputs = c["show_outputs"]
    
    # 1. Deterministic rules
    det_findings = NetworkRuleChecker.audit_config(show_outputs)
    
    # 2. AI diagnosis
    ai_diag = ai_diagnoser.diagnose(symptom, topology, show_outputs, case_id)
    
    saved_review = reviews.get(case_id, None)
    if saved_review:
        c["review_status"] = saved_review["review_status"]
    else:
        c["review_status"] = None
        
    mode = "api" if ai_diagnoser.api_available else "mock"
    
    return jsonify({
        "case": c,
        "deterministic_findings": det_findings,
        "ai_diagnosis": ai_diag,
        "saved_review": saved_review,
        "mode": mode
    })

# API endpoint: submit review
@app.route('/api/review', methods=['POST'])
def api_review():
    data = request.json
    case_id = data.get("case_id")
    status = data.get("review_status")
    
    if not case_id or not status:
        return jsonify({"success": False, "error": "Missing parameter"}), 400
        
    cases = load_cases()
    c = next((item for item in cases if item["id"] == case_id), None)
    if not c:
        return jsonify({"success": False, "error": "Invalid case_id"}), 404
        
    reviews = load_reviews()
    det_findings = NetworkRuleChecker.audit_config(c["show_outputs"])
    ai_diag = ai_diagnoser.diagnose(c["symptom"], c["topology_notes"], c["show_outputs"], case_id)
    
    reviews[case_id] = {
        "case_id": case_id,
        "domain": c["domain"],
        "symptom": c["symptom"],
        "topology_notes": c["topology_notes"],
        "show_outputs": c["show_outputs"],
        "deterministic_findings": det_findings,
        "ai_diagnosis": ai_diag,
        "review_status": status,
        "reviewed_by": "Human Auditor (Web)",
        "reviewed_at": datetime.now().isoformat(),
        "final_suspected_fault": data.get("final_suspected_fault", ai_diag.get("suspected_fault")),
        "final_osi_layer": data.get("final_osi_layer", ai_diag.get("osi_layer")),
        "final_confidence": data.get("final_confidence", ai_diag.get("confidence")),
        "final_evidence_extracted": data.get("final_evidence_extracted", ai_diag.get("evidence_extracted", [])),
        "final_next_verification_command": data.get("final_next_verification_command", ai_diag.get("next_verification_command")),
        "final_remediation_steps": data.get("final_remediation_steps", ai_diag.get("remediation_steps", [])),
        "final_safety_flag": data.get("final_safety_flag", ai_diag.get("safety_flag")),
        "notes": data.get("notes", "")
    }
    
    if save_reviews(reviews):
        try:
            generate_dashboard()
        except Exception as e:
            print(f"[NetSage] Warning: Failed to regenerate dashboard: {e}")
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Error saving reviews file"}), 500

# API endpoint: get stats
@app.route('/api/stats')
def api_stats():
    cases = load_cases()
    reviews = load_reviews()
    
    total = len(cases)
    reviewed = len(reviews)
    
    status_counts = {"Accepted": 0, "Edited": 0, "Rejected": 0}
    for r in reviews.values():
        stat = r.get("review_status")
        if stat in status_counts:
            status_counts[stat] += 1
            
    return jsonify({
        "total_cases": total,
        "reviewed_count": reviewed,
        "status_counts": status_counts
    })

# Main Web App UI page
@app.route('/')
def web_index():
    return render_template_string(HTML_TEMPLATE)

# ==============================================================================
# MAIN ROUTING
# ==============================================================================
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="NetSage AI review system")
    parser.add_argument('--cli', action='store_true', help="Run in terminal CLI mode.")
    parser.add_argument('--port', type=int, default=5000, help="Web UI port (Default: 5000)")
    args = parser.parse_args()
    
    if not os.path.exists(CASES_CSV):
        print(f"[NetSage] Error: {CASES_CSV} does not exist.")
        sys.exit(1)
        
    if args.cli:
        run_cli_review()
    else:
        try:
            print("[NetSage] Initializing performance dashboard charts...")
            generate_dashboard()
        except Exception as e:
            print(f"[NetSage] Warning: Failed to generate initial dashboard: {e}")
        print(f"[NetSage] Web server running on http://127.0.0.1:{args.port} ...")
        app.run(debug=True, port=args.port)

