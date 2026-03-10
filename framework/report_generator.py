import os
import json
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

class HTMLReportGenerator:
    def __init__(self, output_dir="reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results = []
        self.summary = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "duration": "0s",
            "device_info": {}
        }

    def add_result(self, category_name: str, test_name: str, is_pass: bool, message: str = ""):
        self.results.append({
            "category": category_name,
            "test_name": test_name,
            "status": "PASS" if is_pass else "FAIL",
            "message": message
        })
        self.summary["total"] += 1
        if is_pass:
            self.summary["passed"] += 1
        else:
            self.summary["failed"] += 1

    def set_device_info(self, info: dict):
        self.summary["device_info"] = info

    def finalize(self, duration_secs: float) -> str:
        self.summary["duration"] = f"{duration_secs:.2f}s"
        
        # Calculate Release Readiness
        if self.summary["failed"] == 0:
            readiness = "🟢 Ready for Release"
        elif self.summary["failed"] <= 3: # Arbitrary threshold for conditional
            readiness = "🟡 Conditional Release (Review Required)"
        else:
            readiness = "🔴 DO NOT RELEASE (Critical Failures)"
            
        self.summary["readiness"] = readiness

        html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Android Sanity Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1, h2 { color: #333; }
        .summary-box { display: flex; gap: 20px; margin-bottom: 20px; }
        .stat-card { background: #e9ecef; padding: 15px; border-radius: 6px; flex: 1; text-align: center; }
        .pass { color: #28a745; font-weight: bold; }
        .fail { color: #dc3545; font-weight: bold; }
        .readiness-banner { padding: 15px; font-size: 1.2em; font-weight: bold; text-align: center; border-radius: 6px; margin-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; }
        .status-PASS { color: white; background-color: #28a745; padding: 4px 8px; border-radius: 4px; font-size: 0.9em; }
        .status-FAIL { color: white; background-color: #dc3545; padding: 4px 8px; border-radius: 4px; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📱 Android Sanity Test Report</h1>
        
        <div class="readiness-banner" style="background-color: {{ '#d4edda' if summary.failed == 0 else ('#fff3cd' if summary.failed <= 3 else '#f8d7da') }}">
            Release Recommendation: {{ summary.readiness }}
        </div>

        <div class="summary-box">
            <div class="stat-card"><h3>Total Tests</h3><p>{{ summary.total }}</p></div>
            <div class="stat-card"><h3>Passed</h3><p class="pass">{{ summary.passed }}</p></div>
            <div class="stat-card"><h3>Failed</h3><p class="fail">{{ summary.failed }}</p></div>
            <div class="stat-card"><h3>Duration</h3><p>{{ summary.duration }}</p></div>
        </div>
        
        <h2>Device Information</h2>
        <ul>
            {% for key, value in summary.device_info.items() %}
            <li><strong>{{ key }}:</strong> {{ value }}</li>
            {% endfor %}
        </ul>

        <h2>Detailed Test Results (Fully Automated)</h2>
        <table>
            <thead>
                <tr>
                    <th>Category</th>
                    <th>Test Name</th>
                    <th>Status</th>
                    <th>Details</th>
                </tr>
            </thead>
            <tbody>
                {% for result in results %}
                <tr>
                    <td>{{ result.category }}</td>
                    <td>{{ result.test_name }}</td>
                    <td><span class="status-{{ result.status }}">{{ result.status }}</span></td>
                    <td>{{ result.message }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
        """
        
        import jinja2
        template = jinja2.Template(html_template)
        output_html = template.render(summary=self.summary, results=self.results)
        
        filename = f"{self.output_dir}/sanity_report_{self.timestamp}.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(output_html)
            
        print(f"Report generated successfully: {filename}")
        return filename
