import os
import json
import matplotlib.pyplot as plt

# Paths
DATA_DIR = "data"
REVIEWS_JSON = os.path.join(DATA_DIR, "reviews.json")
REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

def generate_dashboard():
    print("=" * 60)
    print("             NETSAGE AI - PERFORMANCE DASHBOARD")
    print("=" * 60)
    
    if not os.path.exists(REVIEWS_JSON):
        print(f"Error: Review database '{REVIEWS_JSON}' not found.")
        print("Please run the review system or seed database first.")
        return
        
    with open(REVIEWS_JSON, "r", encoding="utf-8") as f:
        reviews = json.load(f)
        
    total_cases = len(reviews)
    if total_cases == 0:
        print("No reviewed cases found in database.")
        return
        
    accepted_count = 0
    edited_count = 0
    rejected_count = 0
    
    layer_counts = {}
    deterministic_solved = 0
    llm_solved = 0
    
    for r in reviews.values():
        status = r.get("review_status", "Pending")
        if status == "Accepted":
            accepted_count += 1
        elif status == "Edited":
            edited_count += 1
        elif status == "Rejected":
            rejected_count += 1
            
        # Check target layer of final diagnosis
        layer = r.get("final_osi_layer", "Unspecified")
        layer_counts[layer] = layer_counts.get(layer, 0) + 1
        
        # Check if solved by deterministic regex
        det = r.get("deterministic_findings", {})
        faults_found = det.get("deterministic_faults_found", 0)
        if faults_found > 0:
            deterministic_solved += 1
        else:
            llm_solved += 1
            
    # Calculations
    agreement_rate = (accepted_count / total_cases) * 100
    
    # Terminal Display Table
    print(f"{'Metric':<30} | {'Value':<10}")
    print("-" * 60)
    print(f"{'Total Evaluated Cases':<30} | {total_cases:<10}")
    print(f"{'  Accepted (100% Accurate)':<30} | {accepted_count:<10}")
    print(f"{'  Edited (Parameter Correction)':<30} | {edited_count:<10}")
    print(f"{'  Rejected (Hallucination)':<30} | {rejected_count:<10}")
    print(f"{'Agreement Rate (AI Accuracy)':<30} | {agreement_rate:.2f}%")
    print("-" * 60)
    print(f"{'Deterministic Regex Solved':<30} | {deterministic_solved:<10}")
    print(f"{'LLM Semantic Solved':<30} | {llm_solved:<10}")
    print("=" * 60)
    print("Layer Distribution:")
    for layer, count in sorted(layer_counts.items()):
        print(f"  {layer:<10}: {count} cases")
    print("=" * 60)
    
    # --- Generate Charts ---
    try:
        plt.style.use('dark_background')
    except:
        pass # fallback
        
    # Chart 1: Review Status Breakdown (Agreement Rate)
    fig, ax = plt.subplots(figsize=(6, 5))
    labels = ['Accepted', 'Edited', 'Rejected']
    sizes = [accepted_count, edited_count, rejected_count]
    colors = ['#10b981', '#f59e0b', '#ef4444']
    
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors, startangle=140,
           wedgeprops={'edgecolor': '#24354f', 'linewidth': 1})
    ax.set_title("Human Review Status Breakdown (Agreement Rate)", pad=20, fontsize=12, fontweight='bold')
    plt.tight_layout()
    status_path = os.path.join(REPORTS_DIR, "review_status_chart.png")
    plt.savefig(status_path, dpi=120)
    plt.close()
    
    # Chart 2: OSI Layer Distribution
    fig, ax = plt.subplots(figsize=(7, 5))
    layers = sorted(layer_counts.keys())
    counts = [layer_counts[l] for l in layers]
    
    ax.bar(layers, counts, color='#6366f1', edgecolor='#24354f', width=0.5)
    ax.set_title("Fault Distribution by OSI Layer", pad=15, fontsize=12, fontweight='bold')
    ax.set_ylabel("Number of Cases")
    ax.set_xlabel("OSI Model Layer")
    # Grid lines
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    plt.tight_layout()
    layer_path = os.path.join(REPORTS_DIR, "layer_distribution_chart.png")
    plt.savefig(layer_path, dpi=120)
    plt.close()
    
    # Chart 3: Determinism vs LLM
    fig, ax = plt.subplots(figsize=(6, 5))
    categories = ['Deterministic (Regex)', 'Semantic (LLM AI)']
    counts_det = [deterministic_solved, llm_solved]
    colors_det = ['#06b6d4', '#8b5cf6']
    
    ax.bar(categories, counts_det, color=colors_det, edgecolor='#24354f', width=0.4)
    ax.set_title("Deterministic Auditing vs Semantic AI Reasoning", pad=15, fontsize=12, fontweight='bold')
    ax.set_ylabel("Number of Cases")
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    plt.tight_layout()
    det_path = os.path.join(REPORTS_DIR, "determinism_chart.png")
    plt.savefig(det_path, dpi=120)
    plt.close()
    
    print(f"Charts saved to '{REPORTS_DIR}/' successfully:")
    print(f"  - {status_path}")
    print(f"  - {layer_path}")
    print(f"  - {det_path}")
    print("=" * 60)

if __name__ == "__main__":
    generate_dashboard()
