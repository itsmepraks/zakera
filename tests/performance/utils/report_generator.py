"""Generate HTML performance test reports."""

import csv
import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime


class ReportGenerator:
    """Generate beautiful HTML reports from performance test data."""
    
    HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Performance Test Report - {test_name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f7fa;
            color: #2c3e50;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header .meta {{ opacity: 0.9; font-size: 0.9em; }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }}
        .metric-card:hover {{ transform: translateY(-5px); }}
        .metric-card .label {{
            font-size: 0.85em;
            color: #7f8c8d;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}
        .metric-card .value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }}
        .metric-card .unit {{ font-size: 0.5em; color: #95a5a6; }}
        .section {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .section h2 {{
            font-size: 1.8em;
            margin-bottom: 20px;
            color: #2c3e50;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid #ecf0f1;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #2c3e50;
        }}
        tr:hover {{ background: #f8f9fa; }}
        .status-badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }}
        .status-pass {{ background: #d4edda; color: #155724; }}
        .status-fail {{ background: #f8d7da; color: #721c24; }}
        .chart {{ margin: 20px 0; }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #95a5a6;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Performance Test Report</h1>
            <div class="meta">
                <p>Test: {test_name}</p>
                <p>Date: {timestamp}</p>
                <p>Duration: {duration}</p>
            </div>
        </div>
        
        <div class="metrics-grid">
            {metrics_cards}
        </div>
        
        <div class="section">
            <h2>📊 Response Time Statistics</h2>
            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                        <th>Threshold</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {response_time_rows}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>📈 Endpoint Performance</h2>
            <table>
                <thead>
                    <tr>
                        <th>Endpoint</th>
                        <th>Requests</th>
                        <th>Failures</th>
                        <th>Avg (ms)</th>
                        <th>P95 (ms)</th>
                        <th>P99 (ms)</th>
                    </tr>
                </thead>
                <tbody>
                    {endpoint_rows}
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>Generated by Zakera Performance Testing Suite</p>
            <p>Powered by Locust</p>
        </div>
    </div>
</body>
</html>
    """
    
    METRIC_CARD_TEMPLATE = """
        <div class="metric-card">
            <div class="label">{label}</div>
            <div class="value">{value}<span class="unit">{unit}</span></div>
        </div>
    """
    
    def __init__(self, csv_file: str):
        """Initialize report generator.
        
        Args:
            csv_file: Path to Locust stats CSV file
        """
        self.csv_file = Path(csv_file)
        self.data = self._load_data()
    
    def _load_data(self) -> List[Dict]:
        """Load data from CSV file.
        
        Returns:
            List of data rows
        """
        data = []
        with open(self.csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        return data
    
    def generate_report(self, output_file: str, test_name: str = "Load Test"):
        """Generate HTML report.
        
        Args:
            output_file: Output HTML file path
            test_name: Name of the test
        """
        # Calculate metrics
        total_requests = sum(int(row.get('Request Count', 0)) for row in self.data if row.get('Name') != 'Aggregated')
        total_failures = sum(int(row.get('Failure Count', 0)) for row in self.data if row.get('Name') != 'Aggregated')
        
        # Find aggregated row
        aggregated = next((row for row in self.data if row.get('Name') == 'Aggregated'), None)
        
        if aggregated:
            avg_response = float(aggregated.get('Average Response Time', 0))
            median_response = float(aggregated.get('Median Response Time', 0))
            p95_response = float(aggregated.get('95%', 0))
            p99_response = float(aggregated.get('99%', 0))
            rps = float(aggregated.get('Requests/s', 0))
        else:
            avg_response = median_response = p95_response = p99_response = rps = 0
        
        error_rate = (total_failures / total_requests * 100) if total_requests > 0 else 0
        
        # Generate metric cards
        metrics_cards = "".join([
            self.METRIC_CARD_TEMPLATE.format(
                label="Total Requests",
                value=f"{total_requests:,}",
                unit=""
            ),
            self.METRIC_CARD_TEMPLATE.format(
                label="Avg Response Time",
                value=f"{avg_response:.0f}",
                unit="ms"
            ),
            self.METRIC_CARD_TEMPLATE.format(
                label="P95 Latency",
                value=f"{p95_response:.0f}",
                unit="ms"
            ),
            self.METRIC_CARD_TEMPLATE.format(
                label="Error Rate",
                value=f"{error_rate:.2f}",
                unit="%"
            ),
            self.METRIC_CARD_TEMPLATE.format(
                label="Throughput",
                value=f"{rps:.1f}",
                unit="RPS"
            ),
        ])
        
        # Generate response time rows
        thresholds = {
            "Average": (avg_response, 100),
            "Median": (median_response, 80),
            "95th Percentile": (p95_response, 200),
            "99th Percentile": (p99_response, 500),
        }
        
        response_time_rows = ""
        for metric, (value, threshold) in thresholds.items():
            status = "pass" if value <= threshold else "fail"
            status_text = "✅ PASS" if status == "pass" else "❌ FAIL"
            response_time_rows += f"""
                <tr>
                    <td>{metric}</td>
                    <td>{value:.2f} ms</td>
                    <td>{threshold} ms</td>
                    <td><span class="status-badge status-{status}">{status_text}</span></td>
                </tr>
            """
        
        # Generate endpoint rows
        endpoint_rows = ""
        for row in self.data:
            if row.get('Name') and row.get('Name') != 'Aggregated':
                name = row.get('Name', '')
                requests = row.get('Request Count', '0')
                failures = row.get('Failure Count', '0')
                avg = float(row.get('Average Response Time', 0))
                p95 = float(row.get('95%', 0))
                p99 = float(row.get('99%', 0))
                
                endpoint_rows += f"""
                    <tr>
                        <td>{name}</td>
                        <td>{requests}</td>
                        <td>{failures}</td>
                        <td>{avg:.2f}</td>
                        <td>{p95:.2f}</td>
                        <td>{p99:.2f}</td>
                    </tr>
                """
        
        # Generate HTML
        html = self.HTML_TEMPLATE.format(
            test_name=test_name,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            duration="5 minutes",  # Update based on actual duration
            metrics_cards=metrics_cards,
            response_time_rows=response_time_rows,
            endpoint_rows=endpoint_rows
        )
        
        # Write to file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html)
        
        print(f"✅ Report generated: {output_file}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python report_generator.py <input_csv> <output_html>")
        sys.exit(1)
    
    generator = ReportGenerator(sys.argv[1])
    generator.generate_report(sys.argv[2])
