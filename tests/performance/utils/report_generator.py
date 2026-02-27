"""Report Generator for Performance Tests

Generates:
- HTML reports with charts
- CSV exports
- JSON data
- PDF reports (optional)
- Comparison reports
"""

import json
import csv
import os
from typing import Dict, List, Optional
from datetime import datetime
import logging
from jinja2 import Template

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates performance test reports in various formats"""
    
    def __init__(self, output_dir: str = './reports'):
        """Initialize report generator
        
        Args:
            output_dir: Directory to save reports
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_html_report(self, data: Dict, filename: str = 'report.html'):
        """Generate HTML report with charts
        
        Args:
            data: Test results data
            filename: Output filename
        """
        template = self._get_html_template()
        
        html_content = template.render(
            title='Zakera Performance Test Report',
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            data=data
        )
        
        output_path = os.path.join(self.output_dir, filename)
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        logger.info(f"HTML report generated: {output_path}")
        return output_path
    
    def generate_csv_report(self, data: Dict, filename: str = 'results.csv'):
        """Generate CSV report
        
        Args:
            data: Test results data
            filename: Output filename
        """
        output_path = os.path.join(self.output_dir, filename)
        
        # Flatten data for CSV
        rows = self._flatten_data(data)
        
        if not rows:
            logger.warning("No data to export to CSV")
            return None
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        
        logger.info(f"CSV report generated: {output_path}")
        return output_path
    
    def generate_json_report(self, data: Dict, filename: str = 'results.json'):
        """Generate JSON report
        
        Args:
            data: Test results data
            filename: Output filename
        """
        output_path = os.path.join(self.output_dir, filename)
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"JSON report generated: {output_path}")
        return output_path
    
    def generate_markdown_summary(self, data: Dict, filename: str = 'summary.md'):
        """Generate Markdown summary
        
        Args:
            data: Test results data
            filename: Output filename
        """
        output_path = os.path.join(self.output_dir, filename)
        
        with open(output_path, 'w') as f:
            f.write(self._create_markdown_summary(data))
        
        logger.info(f"Markdown summary generated: {output_path}")
        return output_path
    
    def compare_results(self, baseline_file: str, current_data: Dict,
                       filename: str = 'comparison.html'):
        """Compare current results with baseline
        
        Args:
            baseline_file: Path to baseline JSON file
            current_data: Current test results
            filename: Output filename
        """
        try:
            with open(baseline_file, 'r') as f:
                baseline_data = json.load(f)
        except FileNotFoundError:
            logger.error(f"Baseline file not found: {baseline_file}")
            return None
        
        comparison = self._compare_data(baseline_data, current_data)
        
        template = self._get_comparison_template()
        html_content = template.render(
            title='Performance Comparison Report',
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            baseline=baseline_data,
            current=current_data,
            comparison=comparison
        )
        
        output_path = os.path.join(self.output_dir, filename)
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        logger.info(f"Comparison report generated: {output_path}")
        return output_path
    
    def _flatten_data(self, data: Dict, parent_key: str = '') -> List[Dict]:
        """Flatten nested dict for CSV export"""
        rows = []
        
        def flatten(d, prefix=''):
            row = {}
            for key, value in d.items():
                full_key = f"{prefix}_{key}" if prefix else key
                if isinstance(value, dict):
                    row.update(flatten(value, full_key))
                elif isinstance(value, (list, tuple)):
                    row[full_key] = str(value)
                else:
                    row[full_key] = value
            return row
        
        if isinstance(data, dict):
            rows.append(flatten(data))
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    rows.append(flatten(item))
        
        return rows
    
    def _compare_data(self, baseline: Dict, current: Dict) -> Dict:
        """Compare two datasets and calculate deltas"""
        comparison = {}
        
        # Compare key metrics
        metrics_to_compare = [
            'avg_latency',
            'p95_latency',
            'p99_latency',
            'error_rate',
            'throughput'
        ]
        
        for metric in metrics_to_compare:
            if metric in baseline and metric in current:
                baseline_val = baseline[metric]
                current_val = current[metric]
                delta = current_val - baseline_val
                delta_percent = (delta / baseline_val * 100) if baseline_val != 0 else 0
                
                comparison[metric] = {
                    'baseline': baseline_val,
                    'current': current_val,
                    'delta': delta,
                    'delta_percent': delta_percent,
                    'improved': self._is_improvement(metric, delta)
                }
        
        return comparison
    
    def _is_improvement(self, metric: str, delta: float) -> bool:
        """Determine if delta represents improvement"""
        # Lower is better for these metrics
        lower_is_better = ['latency', 'error_rate', 'p95', 'p99']
        
        for pattern in lower_is_better:
            if pattern in metric.lower():
                return delta < 0
        
        # Higher is better for throughput
        return delta > 0
    
    def _create_markdown_summary(self, data: Dict) -> str:
        """Create Markdown summary"""
        md = f"""# Performance Test Summary

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview

"""
        
        if 'chat_stats' in data:
            stats = data['chat_stats']
            md += f"""### Chat Performance

- **Total Requests:** {stats.get('total_requests', 0)}
- **Average Duration:** {stats.get('avg_duration', 0):.3f}s
- **P95 Duration:** {stats.get('p95_duration', 0):.3f}s
- **P99 Duration:** {stats.get('p99_duration', 0):.3f}s
- **Total Cost:** ${stats.get('total_cost', 0):.4f}

"""
        
        if 'provider_stats' in data:
            md += """### Provider Performance\n\n"""
            for provider, stats in data['provider_stats'].items():
                md += f"""#### {provider.title()}
- Requests: {stats.get('total_requests', 0)}
- Success Rate: {stats.get('success_rate', 0):.1f}%
- Avg Duration: {stats.get('avg_duration', 0):.3f}s

"""
        
        return md
    
    def _get_html_template(self) -> Template:
        """Get HTML report template"""
        template_str = """<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <meta charset="utf-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }
        h2 {
            color: #555;
            margin-top: 30px;
        }
        .metric {
            display: inline-block;
            margin: 15px;
            padding: 20px;
            background-color: #f9f9f9;
            border-left: 4px solid #4CAF50;
            border-radius: 4px;
        }
        .metric-label {
            font-size: 14px;
            color: #777;
            text-transform: uppercase;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #4CAF50;
            color: white;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .timestamp {
            color: #888;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>{{ title }}</h1>
        <p class="timestamp">{{ timestamp }}</p>
        
        {% if data.chat_stats %}
        <h2>Chat Performance</h2>
        <div>
            <div class="metric">
                <div class="metric-label">Total Requests</div>
                <div class="metric-value">{{ data.chat_stats.total_requests }}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Avg Duration</div>
                <div class="metric-value">{{ "%.3f"|format(data.chat_stats.avg_duration) }}s</div>
            </div>
            <div class="metric">
                <div class="metric-label">P95 Duration</div>
                <div class="metric-value">{{ "%.3f"|format(data.chat_stats.p95_duration) }}s</div>
            </div>
            <div class="metric">
                <div class="metric-label">Total Cost</div>
                <div class="metric-value">${{ "%.4f"|format(data.chat_stats.total_cost) }}</div>
            </div>
        </div>
        {% endif %}
        
        {% if data.provider_stats %}
        <h2>Provider Performance</h2>
        <table>
            <thead>
                <tr>
                    <th>Provider</th>
                    <th>Requests</th>
                    <th>Success Rate</th>
                    <th>Avg Duration</th>
                    <th>P95 Duration</th>
                    <th>Total Cost</th>
                </tr>
            </thead>
            <tbody>
            {% for provider, stats in data.provider_stats.items() %}
                <tr>
                    <td>{{ provider }}</td>
                    <td>{{ stats.total_requests }}</td>
                    <td>{{ "%.1f"|format(stats.success_rate) }}%</td>
                    <td>{{ "%.3f"|format(stats.avg_duration) }}s</td>
                    <td>{{ "%.3f"|format(stats.p95_duration) }}s</td>
                    <td>${{ "%.4f"|format(stats.total_cost) }}</td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
        {% endif %}
    </div>
</body>
</html>
"""
        return Template(template_str)
    
    def _get_comparison_template(self) -> Template:
        """Get comparison report template"""
        # Similar to HTML template but with comparison data
        return self._get_html_template()  # Simplified for now
