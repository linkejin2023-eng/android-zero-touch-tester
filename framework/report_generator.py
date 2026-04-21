import os
import json
import math
import time
import logging
from datetime import datetime
import jinja2

import yaml # For loading status logic

class HTMLReportGenerator:
    def __init__(self, output_dir="reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.timestamp_file = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results = []
        self.last_mark = time.time()
        
        # Load Status Logic Registry
        self.logic_registry = {}
        try:
            logic_path = "configs/status_logic.yaml"
            if os.path.exists(logic_path):
                with open(logic_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    # Create a lookup: (category, name) -> level
                    for item in data.get("items", []):
                        self.logic_registry[(item["category"], item["name"])] = item["level"]
        except Exception as e:
            logging.warning(f"ReportGenerator: Failed to load status_logic.yaml ({e})")

        self.summary = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "error": 0,
            "skipped": 0,
            "exempt": 0, # NEW: Environmental Exemptions
            "duration": "0s",
            "device_info": {},
            "categories": {},
            "readiness": "🔴"
        }

    def add_result(self, category_name: str, test_name: str, is_pass: bool, message: str = "", duration: float = 0.0, status_override: str = None, procedure: str = "", pass_criteria: str = ""):
        # Determine actual status
        if status_override:
            status = status_override.upper()
        else:
            status = "PASS" if is_pass else "FAIL"
            
        # [Industrial Logic] If FAIL, check if it should be EXEMPT (Env Excluded)
        if status == "FAIL":
            level = self.logic_registry.get((category_name, test_name))
            if level == "ENV_EXCLUDED":
                status = "EXEMPT"
                message = f"[Env Excluded] {message}"
            
        # Automatic incremental duration
        if duration == 0.0:
            now = time.time()
            duration = now - self.last_mark
            self.last_mark = now
            
        cat_id = f"sec-{category_name.replace(' ', '_')}"
        test_id = f"d-{len(self.results)}_{test_name.lower().replace(' ', '_').replace('/', '_')}"
            
        result = {
            "category": category_name,
            "category_id": cat_id,
            "test_id": test_id,
            "test_name": test_name,
            "status": status,
            "duration": f"{duration:.2f}s",
            "message": message,
            "procedure": procedure if procedure else "N/A",
            "pass_criteria": pass_criteria if pass_criteria else "N/A"
        }
        self.results.append(result)
        
        self.summary["total"] += 1
        if status == "PASS": self.summary["passed"] += 1
        elif status == "FAIL": self.summary["failed"] += 1
        elif status == "ERROR": self.summary["error"] += 1
        elif status == "SKIP": self.summary["skipped"] += 1
        elif status == "EXEMPT": self.summary["exempt"] += 1
            
        # Update category stats
        if category_name not in self.summary["categories"]:
            self.summary["categories"][category_name] = {
                "name": category_name,
                "id": cat_id,
                "total": 0, "passed": 0, "failed": 0, "error": 0, "skipped": 0, "exempt": 0
            }
        
        cat = self.summary["categories"][category_name]
        cat["total"] += 1
        if status == "PASS": cat["passed"] += 1
        elif status == "FAIL": cat["failed"] += 1
        elif status == "ERROR": cat["error"] += 1
        elif status == "SKIP": cat["skipped"] += 1
        elif status == "EXEMPT": cat["exempt"] += 1

    def set_device_info(self, info: dict):
        self.summary["device_info"] = info

    def _calculate_donut_chart(self):
        total = self.summary["total"]
        exempt = self.summary["exempt"]
        
        # Weighted Total: Exclude Exemptions from the denominator for more accurate quality gauge
        effective_total = total - exempt
        
        if total == 0 or effective_total <= 0:
            return {"pass_pct": "0.0%", "pass_dash": 0, "fail_dash": 0, "skip_dash": 0, "exempt_dash": 0, 
                    "fail_offset": 0, "skip_offset": 0, "exempt_offset": 0}
            
        passed = self.summary["passed"]
        failed = self.summary["failed"]
        error = self.summary["error"]
        skipped = self.summary["skipped"]
        
        circumference = 408
        pass_ratio = passed / effective_total
        fail_ratio = (failed + error) / total # Still based on full total for segment size
        skip_ratio = skipped / total
        exempt_ratio = exempt / total
        
        # Draw the chart based on full total but center text uses effective pass rate
        pass_dash = circumference * (passed / total)
        fail_dash = circumference * fail_ratio
        skip_dash = circumference * skip_ratio
        exempt_dash = circumference * exempt_ratio
        
        # Offsets
        fail_offset = -pass_dash
        skip_offset = -(pass_dash + fail_dash)
        exempt_offset = -(pass_dash + fail_dash + skip_dash)
        
        return {
            "pass_pct": f"{(pass_ratio * 100):.1f}%",
            "pass_dash": pass_dash,
            "fail_dash": fail_dash,
            "skip_dash": skip_dash,
            "exempt_dash": exempt_dash,
            "fail_offset": fail_offset,
            "skip_offset": skip_offset,
            "exempt_offset": exempt_offset
        }
        
    def _prepare_subsystem_stats(self):
        for cat_name, cat in self.summary["categories"].items():
            total = cat["total"]
            exempt = cat["exempt"]
            effective_total = total - exempt
            if total == 0: continue
            
            # Pass Rate per category also excludes exemptions
            cat["pass_pct_raw"] = (cat["passed"] / effective_total * 100) if effective_total > 0 else 100
            
            cat["pass_pct"] = (cat["passed"] / total) * 100
            cat["fail_pct"] = (cat["failed"] / total) * 100
            cat["error_pct"] = (cat["error"] / total) * 100
            cat["skip_pct"] = (cat["skipped"] / total) * 100
            cat["exempt_pct"] = (cat["exempt"] / total) * 100
            cat["is_perfect"] = (cat["passed"] == (total - exempt))

    def export_summary_json(self, version: str, variant: str, status: str = "UNKNOWN"):
        """Export a machine-readable summary for CI/CD notification scripts."""
        failed_cases = []
        env_excluded_cases = []
        
        for res in self.results:
            if res["status"] in ["FAIL", "ERROR"]:
                case_info = {
                    "category": res["category"],
                    "test_name": res["test_name"],
                    "message": res["message"]
                }
                if "[ENV-EXCLUDED]" in res["message"]:
                    env_excluded_cases.append(case_info)
                else:
                    failed_cases.append(case_info)

        summary_data = {
            "status": status,
            "version": version,
            "variant": variant,
            "timestamp": self.timestamp,
            "model": self.summary["device_info"].get("Model", "Unknown"),
            "stats": {
                "total": self.summary["total"],
                "passed": self.summary["passed"],
                "failed": self.summary["failed"],
                "error": self.summary["error"],
                "exempt": self.summary["exempt"],
                "skipped": self.summary["skipped"],
                "pass_rate": f"{(self.summary['passed'] / (self.summary['total'] - self.summary['exempt']) * 100):.1f}%" if (self.summary['total'] - self.summary['exempt']) > 0 else "100.0%"
            },
            "failed_cases": failed_cases,
            "env_excluded_cases": env_excluded_cases
        }
        
        filename = f"test_summary.json" # Always fixed name in workspace for easy grep
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=4)
        logging.info(f"Summary JSON exported: {filename}")
        return filename

    def finalize(self, duration_secs: float, version: str = "Unknown", variant: str = "user") -> str:
        self.summary["duration"] = f"{duration_secs:.2f}s"
        
        if self.summary["failed"] == 0 and self.summary["error"] == 0:
            self.summary["overall_status"] = "pass"
            self.summary["overall_text"] = f"✓ {self.summary['passed']} PASSED"
        else:
            self.summary["overall_status"] = "fail"
            bad_count = self.summary["failed"] + self.summary["error"]
            self.summary["overall_text"] = f"✖ {bad_count} FAILED"

        self._prepare_subsystem_stats()
        donut = self._calculate_donut_chart()

        html_template = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Smoke Test Report - {{ summary.device_info.get('Model', 'Device') }}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,500;0,9..40,700;1,9..40,400&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0f1117;
    --surface: #1a1d27;
    --surface-2: #232733;
    --surface-3: #2c3040;
    --border: #333848;
    --text: #e4e7ef;
    --text-dim: #8891a5;
    --text-muted: #5a6478;
    --accent: #6c8cff;
    --accent-dim: rgba(108,140,255,.12);
    --green: #34d399;
    --green-bg: rgba(52,211,153,.08);
    --green-border: rgba(52,211,153,.25);
    --red: #f87171;
    --red-bg: rgba(248,113,113,.08);
    --red-border: rgba(248,113,113,.25);
    --amber: #fbbf24;
    --amber-bg: rgba(251,191,36,.08);
    --amber-border: rgba(251,191,36,.25);
    --pink: #f472b6;
    --pink-bg: rgba(244,114,182,.1);
    --radius: 10px;
    --mono: 'JetBrains Mono', 'SF Mono', 'Fira Code', monospace;
    --sans: 'DM Sans', -apple-system, 'Segoe UI', sans-serif;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  body { font-family: var(--sans); background: var(--bg); color: var(--text); line-height: 1.6; min-height: 100vh; }
  .container { max-width: 1280px; margin: 0 auto; padding: 32px 40px 60px; }
  
  /* Header */
  header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 36px; padding-bottom: 24px; border-bottom: 1px solid var(--border); }
  .header-icon { width: 36px; height: 36px; border-radius: 8px; background: var(--accent-dim); border: 1px solid rgba(108,140,255,.2); display: flex; align-items: center; justify-content: center; font-size: 18px; margin-right: 14px; flex-shrink: 0; }
  .header-left { display: flex; align-items: flex-start; }
  header h1 { font-size: 22px; font-weight: 700; letter-spacing: -0.3px; color: var(--text); }
  .header-meta { display: flex; gap: 20px; font-size: 13px; color: var(--text-dim); margin-top: 6px; font-family: var(--mono); }
  .header-meta .sep { color: var(--text-muted); }
  .header-right { text-align: right; font-size: 13px; color: var(--text-dim); }
  .overall-badge { display: inline-flex; align-items: center; gap: 6px; padding: 6px 16px; border-radius: 20px; font-weight: 700; font-size: 14px; margin-bottom: 6px; }
  .overall-badge.pass { background: var(--green-bg); color: var(--green); border: 1px solid var(--green-border); }
  .overall-badge.fail { background: var(--red-bg); color: var(--red); border: 1px solid var(--red-border); }
  .overall-badge.exempt { background: var(--amber-bg); color: var(--amber); border: 1px solid var(--amber-border); }
  
  /* Stats Row */
  .stats-row { display: grid; grid-template-columns: 200px 1fr; gap: 24px; margin-bottom: 36px; }
  .donut-wrap { background: var(--surface); border-radius: var(--radius); border: 1px solid var(--border); padding: 24px; display: flex; align-items: center; justify-content: center; }
  .donut { position: relative; width: 140px; height: 140px; }
  .donut svg { transform: rotate(-90deg); }
  .donut-center { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
  .donut-pct { font-size: 32px; font-weight: 700; font-family: var(--mono); line-height: 1; }
  .donut-label { font-size: 11px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 1px; margin-top: 2px; }
  
  .stat-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; }
  .stat-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 18px 20px; position: relative; overflow: hidden; }
  .stat-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; }
  .stat-card.total::before { background: var(--accent); } .stat-card.pass::before { background: var(--green); }
  .stat-card.fail::before { background: var(--red); } .stat-card.error::before { background: var(--pink); } 
  .stat-card.skip::before { background: rgba(255,255,255,.2); } .stat-card.exempt::before { background: var(--amber); }
  .stat-card .stat-label { font-size: 11px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 6px; }
  .stat-card .stat-value { font-size: 28px; font-weight: 700; font-family: var(--mono); line-height: 1; }
  .stat-card.total .stat-value { color: var(--accent); } .stat-card.pass .stat-value { color: var(--green); }
  .stat-card.fail .stat-value { color: var(--red); } .stat-card.error .stat-value { color: var(--pink); } 
  .stat-card.skip .stat-value { color: var(--text-muted); } .stat-card.exempt .stat-value { color: var(--amber); }

  /* Device Info */
  .info-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px 32px; }
  .info-row { display: flex; padding: 4px 0; font-size: 13px; gap: 12px; border-bottom: 1px solid rgba(51,56,72,.3); }
  .info-row:last-child { border-bottom: none; }
  .info-label { color: var(--text-dim); min-width: 120px; flex-shrink: 0; font-weight: 500; }
  .info-value { color: var(--text); font-family: var(--mono); font-size: 11.5px; word-break: break-all; }

  /* Subsystem Summary */
  .section-title { font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; color: var(--text-dim); margin-bottom: 16px; padding-bottom: 10px; border-bottom: 1px solid var(--border); }
  .subsystem-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; margin-bottom: 40px; }
  .sub-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px 20px; cursor: pointer; transition: border-color .2s, transform .15s, box-shadow .2s; position: relative; }
  .sub-card:hover { border-color: var(--accent); transform: translateY(-1px); }
  .sub-card.s-pass { border-left: 3px solid var(--green); }
  .sub-card.s-fail { border-left: 3px solid var(--red); box-shadow: 0 0 20px rgba(248,113,113,.08), inset 0 0 30px rgba(248,113,113,.03); }
  .sub-name { font-size: 14px; font-weight: 600; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
  .sub-badge { font-size: 11px; font-family: var(--mono); padding: 2px 8px; border-radius: 10px; font-weight: 600; }
  .sub-card.s-pass .sub-badge { background: var(--green-bg); color: var(--green); }
  .sub-card.s-fail .sub-badge { background: var(--red-bg); color: var(--red); }
  .sub-bar { height: 6px; border-radius: 3px; background: var(--surface-3); overflow: hidden; display: flex; }
  .sub-bar > div { height: 100%; }
  .sub-stats { display: flex; gap: 12px; margin-top: 10px; font-size: 12px; font-family: var(--mono); color: var(--text-dim); }
  .sub-stats span { display: flex; align-items: center; gap: 4px; }
  .sub-stats .dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
  .dot.g { background: var(--green); } .dot.r { background: var(--red); } .dot.a { background: var(--amber); } .dot.p { background: var(--pink); } .dot.gray { background: var(--text-muted); }

  /* Filter Bar */
  .filter-bar { display: flex; gap: 8px; margin-bottom: 20px; align-items: center; flex-wrap: wrap; }
  .filter-btn { font-family: var(--mono); font-size: 12px; font-weight: 600; padding: 5px 14px; border-radius: 6px; border: 1px solid var(--border); background: var(--surface); color: var(--text-dim); cursor: pointer; transition: all .15s; }
  .filter-btn:hover { border-color: var(--accent); color: var(--text); }
  .filter-btn.active { border-color: var(--accent); background: var(--accent-dim); color: var(--accent); }
  .filter-btn.f-fail.active { border-color: var(--red); background: var(--red-bg); color: var(--red); }
  .filter-btn.f-skip.active { border-color: var(--amber); background: var(--amber-bg); color: var(--amber); }
  .filter-btn.f-pass.active { border-color: var(--green); background: var(--green-bg); color: var(--green); }
  .filter-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; margin-right: 4px; }

  /* Detail Tables */
  .cat-section { margin-bottom: 16px; }
  .cat-section-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 20px; background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius) var(--radius) 0 0; cursor: pointer; user-select: none; transition: background .15s; }
  .cat-section-header:hover { background: var(--surface-3); }
  .cat-section-header h3 { font-size: 14px; font-weight: 600; display: flex; align-items: center; gap: 10px; }
  .cat-section-header .cat-count { font-family: var(--mono); font-size: 12px; color: var(--text-dim); margin-left: 4px; }
  .cat-section-header .chevron { color: var(--text-muted); transition: transform .2s; font-size: 12px; }
  .cat-section.collapsed .chevron { transform: rotate(-90deg); }
  .cat-section.collapsed .cat-table-wrap { display: none; }
  .cat-table-wrap { border: 1px solid var(--border); border-top: none; border-radius: 0 0 var(--radius) var(--radius); overflow: hidden; }

  table { width: 100%; border-collapse: collapse; }
  th { background: var(--surface-3); color: var(--text-dim); padding: 10px 16px; text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; border-bottom: 1px solid var(--border); }
  td { padding: 10px 16px; border-bottom: 1px solid rgba(51,56,72,.5); font-size: 13px; vertical-align: top; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: rgba(108,140,255,.03); }
  tr.hidden-by-filter { display: none; }
  td.id-col { font-family: var(--mono); font-size: 12px; color: var(--text-dim); white-space: nowrap; }
  td.dur-col { font-family: var(--mono); font-size: 12px; color: var(--text-dim); white-space: nowrap; }
  td.msg-col { font-size: 12px; color: var(--text-dim); max-width: 400px; word-break: break-word; }

  /* Detail expand */
  tr.has-detail { cursor: pointer; }
  tr.has-detail td:first-child { position: relative; padding-left: 20px; }
  tr.has-detail td:first-child::before { content: '▸'; position: absolute; left: 6px; top: 12px; color: var(--text-muted); font-size: 10px; transition: transform .2s, color .2s; }
  tr.has-detail.expanded td:first-child::before { transform: rotate(90deg); color: var(--accent); }
  tr.detail-row { display: none; }
  tr.detail-row.show { display: table-row; }
  tr.detail-row td { padding: 0 16px 14px 40px; background: var(--surface); border-bottom: 1px solid var(--border); border-left: 2px solid var(--accent); }
  .detail-content { display: flex; gap: 32px; padding: 10px 16px; background: rgba(108,140,255,.03); border-radius: 6px; font-size: 12px; }
  .detail-item { display: flex; flex-direction: column; gap: 3px; }
  .detail-label { color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-size: 9px; letter-spacing: 1px; }
  .detail-value { color: var(--text-dim); font-family: var(--mono); font-size: 11px; word-break: break-all; line-height: 1.5; }

  .status { display: inline-flex; align-items: center; gap: 5px; font-family: var(--mono); font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 6px; }
  .status.s-PASS { color: var(--green); background: var(--green-bg); }
  .status.s-FAIL { color: var(--red); background: var(--red-bg); }
  .status.s-SKIP { color: var(--text-dim); background: rgba(255,255,255,.05); }
  .status.s-EXEMPT { color: var(--amber); background: var(--amber-bg); }
  .status.s-ERROR { color: var(--pink); background: var(--pink-bg); }
  
  footer { margin-top: 48px; padding-top: 20px; border-top: 1px solid var(--border); font-size: 12px; color: var(--text-muted); display: flex; justify-content: space-between; }
  
  @keyframes fadeUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
  .animate-in { animation: fadeUp .35s ease-out both; }
  .d1 { animation-delay: .05s } .d2 { animation-delay: .1s } .d3 { animation-delay: .15s }
  .d4 { animation-delay: .2s } .d5 { animation-delay: .25s }
  @media (max-width: 900px) { .device-grid { grid-template-columns: 1fr; } .stats-row { grid-template-columns: 1fr; } header { flex-direction: column; gap: 12px; } }
</style>
</head>
<body>
<div class="container">
  <header class="animate-in">
    <div class="header-left">
      <div class="header-icon">&#x2691;</div>
      <div>
        <h1>System Smoke Test Report</h1>
        <div class="header-meta">
          <span>{{ summary.device_info.get('Model', 'Unknown Device') }}</span>
          <span class="sep">/</span>
          <span>{{ timestamp }}</span>
          <span class="sep">/</span>
          <span style="color: var(--accent); font-weight: 700;">Duration: {{ summary.duration }}</span>
        </div>
      </div>
    </div>
    <div class="header-right">
      <div class="overall-badge {{ summary.overall_status }}">{{ summary.overall_text }}</div>
      <div>{{ summary.total }} tests executed</div>
    </div>
  </header>

  <div class="stats-row animate-in d1">
    <div class="donut-wrap">
      <div class="donut">
        <svg width="140" height="140" viewBox="0 0 140 140">
          <circle cx="70" cy="70" r="65" fill="none" stroke="var(--surface-3)" stroke-width="10"/>
          <circle cx="70" cy="70" r="65" fill="none" stroke="var(--green)" stroke-width="10" stroke-dasharray="{{ donut.pass_dash }} 408" stroke-linecap="round"/>
          <circle cx="70" cy="70" r="65" fill="none" stroke="var(--red)" stroke-width="10" stroke-dasharray="{{ donut.fail_dash }} 408" stroke-dashoffset="{{ donut.fail_offset }}" stroke-linecap="round"/>
          <circle cx="70" cy="70" r="65" fill="none" stroke="var(--amber)" stroke-width="10" stroke-dasharray="{{ donut.exempt_dash }} 408" stroke-dashoffset="{{ donut.exempt_offset }}" stroke-linecap="round"/>
          <circle cx="70" cy="70" r="65" fill="none" stroke="var(--text-muted)" stroke-width="10" stroke-dasharray="{{ donut.skip_dash }} 408" stroke-dashoffset="{{ donut.skip_offset }}" stroke-linecap="round" opacity="0.3"/>
        </svg>
        <div class="donut-center">
          <div class="donut-pct">{{ donut.pass_pct }}</div>
          <div class="donut-label">pass rate</div>
        </div>
      </div>
    </div>
    <div class="stat-cards">
      <div class="stat-card total"><div class="stat-label">Total</div><div class="stat-value">{{ summary.total }}</div></div>
      <div class="stat-card pass"><div class="stat-label">Passed</div><div class="stat-value">{{ summary.passed }}</div></div>
      <div class="stat-card fail"><div class="stat-label">Failed</div><div class="stat-value">{{ summary.failed }}</div></div>
      <div class="stat-card exempt"><div class="stat-label">Exempt</div><div class="stat-value">{{ summary.exempt }}</div></div>
      <div class="stat-card error"><div class="stat-label">Error</div><div class="stat-value">{{ summary.error }}</div></div>
      <div class="stat-card skip"><div class="stat-label">Skipped</div><div class="stat-value">{{ summary.skipped }}</div></div>
    </div>
  </div>

  <div class="device-panel animate-in d2" style="margin-bottom: 36px;">
    <h3>Device Information & Diagnostics</h3>
    <div class="info-grid">
      {% for key, val in summary.device_info.items() %}
      <div class="info-row"><span class="info-label">{{ key }}</span><span class="info-value">{{ val }}</span></div>
      {% endfor %}
    </div>
  </div>

  <div class="section-title animate-in d3">Subsystem Overview</div>
  <div class="subsystem-grid animate-in d3">
    {% for cat_name, cat in summary.categories.items() %}
    <div class="sub-card {% if cat.is_perfect %}s-pass{% else %}s-fail{% endif %}" onclick="jumpToSection('{{ cat.id }}')">
      <div class="sub-name">{{ cat.name }}<span class="sub-badge">{{ cat.passed }}/{{ cat.total - cat.exempt }}</span></div>
      <div class="sub-bar">
        {% if cat.pass_pct > 0 %}<div style="width: {{ cat.pass_pct }}%; background: var(--green);"></div>{% endif %}
        {% if cat.fail_pct > 0 %}<div style="width: {{ cat.fail_pct }}%; background: var(--red);"></div>{% endif %}
        {% if cat.error_pct > 0 %}<div style="width: {{ cat.error_pct }}%; background: var(--pink);"></div>{% endif %}
        {% if cat.exempt_pct > 0 %}<div style="width: {{ cat.exempt_pct }}%; background: var(--amber);"></div>{% endif %}
        {% if cat.skip_pct > 0 %}<div style="width: {{ cat.skip_pct }}%; background: var(--text-muted); opacity: 0.3;"></div>{% endif %}
      </div>
      <div class="sub-stats">
        <span><span class="dot g"></span>{{ cat.passed }}</span>
        {% if cat.failed > 0 %}<span><span class="dot r"></span>{{ cat.failed }}</span>{% endif %}
        {% if cat.exempt > 0 %}<span><span class="dot a"></span>{{ cat.exempt }}</span>{% endif %}
        {% if cat.skipped > 0 %}<span><span class="dot gray"></span>{{ cat.skipped }}</span>{% endif %}
      </div>
    </div>
    {% endfor %}
  </div>

  <div class="section-title animate-in d4">Detailed Results</div>
  <div class="filter-bar animate-in d4">
    <span class="filter-label">Filter:</span>
    <button class="filter-btn active" onclick="filterTests('all')">All</button>
    <button class="filter-btn f-fail" onclick="filterTests('FAIL')">Failed / Error</button>
    <button class="filter-btn f-skip" onclick="filterTests('EXEMPT')">Exempt (Env)</button>
    <button class="filter-btn f-pass" onclick="filterTests('PASS')">Passed</button>
  </div>

  {% for cat_name, cat in summary.categories.items() %}
  <div class="cat-section {% if cat.is_perfect %}collapsed{% endif %}" id="{{ cat.id }}">
    <div class="cat-section-header" onclick="toggleSection('{{ cat.id }}')">
      <h3>
        <span class="status {% if cat.is_perfect %}s-PASS{% else %}s-FAIL{% endif %}">
          {% if cat.is_perfect %}✓{% else %}✗{% endif %}
        </span>
        {{ cat.name }}
        <span class="cat-count">{{ cat.passed }}/{{ cat.total - cat.exempt }}</span>
      </h3>
      <span class="chevron">▼</span>
    </div>
    <div class="cat-table-wrap">
      <table>
        <tr><th>ID / Test Name</th><th>Status</th><th>Duration</th><th>Message</th></tr>
        {% for row in results %}
          {% if row.category == cat.name %}
          <tr data-status="{{ row.status }}" class="has-detail" onclick="toggleDetail('{{ row.test_id }}', this)">
            <td class="id-col">{{ row.test_name }}</td>
            <td><span class="status s-{{ row.status }}">{{ row.status }}</span></td>
            <td class="dur-col">{{ row.duration }}</td>
            <td class="msg-col">{{ row.message }}</td>
          </tr>
          <tr class="detail-row" id="{{ row.test_id }}">
            <td colspan="4">
              <div class="detail-content">
                <div class="detail-item"><span class="detail-label">Procedure / Execution</span><span class="detail-value">{{ row.procedure }}</span></div>
                <div class="detail-item"><span class="detail-label">Pass Criteria / Traceback</span><span class="detail-value">{{ row.pass_criteria }}</span></div>
              </div>
            </td>
          </tr>
          {% endif %}
        {% endfor %}
      </table>
    </div>
  </div>
  {% endfor %}

  <footer class="animate-in d5">
    <span>Smoke Test Automation Framework / T70</span>
    <span>Generated {{ timestamp }}</span>
  </footer>
</div>

<script>
function toggleDetail(id, row) {
  var el = document.getElementById(id);
  if (el) { el.classList.toggle('show'); if (row) row.classList.toggle('expanded'); }
}
function toggleSection(id) { document.getElementById(id).classList.toggle('collapsed'); }
function jumpToSection(id) {
  var el = document.getElementById(id);
  if (!el) return;
  el.classList.remove('collapsed');
  el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
function filterTests(status) {
  document.querySelectorAll('.filter-btn').forEach(function(b) { b.classList.remove('active'); });
  event.target.classList.add('active');
  document.querySelectorAll('tr[data-status]').forEach(function(row) {
    if (status === 'all') { row.classList.remove('hidden-by-filter'); }
    else if (status === 'FAIL') { row.classList.toggle('hidden-by-filter', row.dataset.status !== 'FAIL' && row.dataset.status !== 'ERROR'); }
    else { row.classList.toggle('hidden-by-filter', row.dataset.status !== status); }
  });
  document.querySelectorAll('.cat-section').forEach(function(sec) {
    var visibleRows = sec.querySelectorAll('tr[data-status]:not(.hidden-by-filter)');
    if (status !== 'all' && visibleRows.length === 0) { sec.classList.add('collapsed'); }
    else if (status !== 'all') { sec.classList.remove('collapsed'); }
  });
}
</script>
</body>
</html>"""

        template = jinja2.Template(html_template)
        output_html = template.render(
            summary=self.summary, 
            results=self.results, 
            timestamp=self.timestamp,
            donut=donut
        )
        
        # 檔名規則：T70_smoke_test_report_VERSION_VARIANT_TIMESTAMP.html
        model = self.summary["device_info"].get('Model', 'T70').replace(" ", "_")
        filename = f"{self.output_dir}/{model}_smoke_test_report_{version}_{variant}_{self.timestamp_file}.html"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(output_html)
            
        print(f"Report generated successfully: {filename}")
        return filename
