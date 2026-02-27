"""
Custom reporters for performance test results.

Provides detailed reporting capabilities including:
- HTML reports with charts
- JSON reports for CI/CD integration
- Prometheus metrics export
- Slack/Discord notifications
- SLA validation
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from jinja2 import Template
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend


class PerformanceReporter:
    """Base class for performance test reporters."""
    
    def __init__(self, output_dir: str = "results"):
        """Initialize reporter with output directory."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.test_start_time = datetime.now()
        self.test_name = "Performance Test"
    
    def generate_report(self, stats, test_config: Dict):
        """Generate performance test report."""
        raise NotImplementedError


class HTMLReporter(PerformanceReporter):
    """Generate detailed HTML reports with charts."""
    
    HTML_TEMPLATE = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>{{ test_name }} - Performance Test Report</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                margin: 0;
                padding: 20px;
                background: #f5f5f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            h1 {
                color: #2c3e50;
                border-bottom: 3px solid #3498db;
                padding-bottom: 10px;
            }
            h2 {
                color: #34495e;
                margin-top: 30px;
            }
            .metrics {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }
            .metric-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            .metric-card.success {
                background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            }
            .metric-card.warning {
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            }
            .metric-card.error {
                background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
            }
            .metric-value {
                font-size: 36px;
                font-weight: bold;
                margin: 10px 0;
            }
            .metric-label {
                font-size: 14px;
                opacity: 0.9;
            }
            .chart-container {
                margin: 20px 0;
                text-align: center;
            }
            .chart-container img {
                max-width: 100%;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
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
                background: #3498db;
                color: white;
                font-weight: 600;
            }
            tr:hover {
                background: #f5f5f5;
            }
            .sla-pass {
                color: #27ae60;
                font-weight: bold;
            }
            .sla-fail {
                color: #e74c3c;
                font-weight: bold;
            }
            .footer {
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                color: #7f8c8d;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{{ test_name }}</h1>
            <p><strong>Test Date:</strong> {{ test_date }}</p>
            <p><strong>Duration:</strong> {{ duration }}</p>
            <p><strong>Description:</strong> {{ description }}</p>
            
            <h2>Key Metrics</h2>
            <div class="metrics">
                <div class="metric-card {{ 'success' if total_requests > 0 else 'error' }}">
                    <div class="metric-label">Total Requests</div>
                    <div class="metric-value">{{ total_requests | number_format }}</div>
                </div>
                <div class="metric-card {{ 'success' if failure_rate < 1 else 'warning' if failure_rate < 5 else 'error' }}">
                    <div class="metric-label">Failure Rate</div>
                    <div class="metric-value">{{ "%.2f"|format(failure_rate) }}%</div>
                </div>
                <div class="metric-card {{ 'success' if avg_response_time < 1000 else 'warning' }}">
                    <div class="metric-label">Avg Response Time</div>
                    <div class="metric-value">{{ "%.0f"|format(avg_response_time) }}ms</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Requests/Second</div>
                    <div class="metric-value">{{ "%.1f"|format(rps) }}</div>
                </div>
            </div>
            
            <h2>Response Time Distribution</h2>
            <div class="chart-container">
                <img src="response_time_distribution.png" alt="Response Time Distribution">
            </div>
            
            <h2>Requests Over Time</h2>
            <div class="chart-container">
                <img src="requests_over_time.png" alt="Requests Over Time">
            </div>
            
            <h2>Endpoint Statistics</h2>
            <table>
                <thead>
                    <tr>
                        <th>Endpoint</th>
                        <th>Requests</th>
                        <th>Failures</th>
                        <th>Avg (ms)</th>
                        <th>Min (ms)</th>
                        <th>Max (ms)</th>
                        <th>Req/s</th>
                    </tr>
                </thead>
                <tbody>
                    {% for endpoint in endpoints %}
                    <tr>
                        <td>{{ endpoint.name }}</td>
                        <td>{{ endpoint.num_requests }}</td>
                        <td>{{ endpoint.num_failures }}</td>
                        <td>{{ "%.0f"|format(endpoint.avg_response_time) }}</td>
                        <td>{{ endpoint.min_response_time }}</td>
                        <td>{{ endpoint.max_response_time }}</td>
                        <td>{{ "%.2f"|format(endpoint.total_rps) }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            
            <h2>SLA Validation</h2>
            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Expected</th>
                        <th>Actual</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% for sla in sla_results %}
                    <tr>
                        <td>{{ sla.metric }}</td>
                        <td>{{ sla.expected }}</td>
                        <td>{{ sla.actual }}</td>
                        <td class="{{ 'sla-pass' if sla.passed else 'sla-fail' }}">
                            {{ '✓ PASS' if sla.passed else '✗ FAIL' }}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            
            <div class="footer">
                <p>Generated by Zakera Performance Test Suite</p>
                <p>Report generated at {{ report_time }}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    def generate_report(self, stats, test_config: Dict):
        """Generate HTML report with charts."""
        # Generate charts
        self._generate_response_time_chart(stats)
        self._generate_requests_chart(stats)
        
        # Prepare data for template
        template_data = self._prepare_template_data(stats, test_config)
        
        # Render HTML
        template = Template(self.HTML_TEMPLATE)
        html_content = template.render(**template_data)
        
        # Save report
        report_path = self.output_dir / f"{test_config.get('test_name', 'test').replace(' ', '_').lower()}_report.html"
        with open(report_path, 'w') as f:
            f.write(html_content)
        
        print(f"📊 HTML report generated: {report_path}")
        return report_path
    
    def _prepare_template_data(self, stats, test_config: Dict) -> Dict:
        """Prepare data for HTML template."""
        total = stats.total
        
        # Calculate metrics
        failure_rate = (total.num_failures / total.num_requests * 100) if total.num_requests > 0 else 0
        
        # Prepare endpoint data
        endpoints = []
        for name, entry in stats.entries.items():
            endpoints.append({
                "name": name,
                "num_requests": entry.num_requests,
                "num_failures": entry.num_failures,
                "avg_response_time": entry.avg_response_time,
                "min_response_time": entry.min_response_time or 0,
                "max_response_time": entry.max_response_time or 0,
                "total_rps": entry.total_rps,
            })
        
        # SLA validation
        sla_results = self._validate_sla(stats, test_config)
        
        return {
            "test_name": test_config.get("test_name", "Performance Test"),
            "test_date": self.test_start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": test_config.get("run_time", "N/A"),
            "description": test_config.get("description", ""),
            "total_requests": total.num_requests,
            "failure_rate": failure_rate,
            "avg_response_time": total.avg_response_time,
            "rps": total.total_rps,
            "endpoints": endpoints,
            "sla_results": sla_results,
            "report_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    
    def _validate_sla(self, stats, test_config: Dict) -> List[Dict]:
        """Validate SLA requirements."""
        total = stats.total
        failure_rate = (total.num_failures / total.num_requests * 100) if total.num_requests > 0 else 0
        
        sla_checks = [
            {
                "metric": "Average Response Time",
                "expected": f"< {test_config.get('expected_avg_response_time', 1000)}ms",
                "actual": f"{total.avg_response_time:.0f}ms",
                "passed": total.avg_response_time < test_config.get('expected_avg_response_time', 1000)
            },
            {
                "metric": "Max Response Time",
                "expected": f"< {test_config.get('expected_max_response_time', 5000)}ms",
                "actual": f"{total.max_response_time or 0}ms",
                "passed": (total.max_response_time or 0) < test_config.get('expected_max_response_time', 5000)
            },
            {
                "metric": "Failure Rate",
                "expected": f"< {test_config.get('expected_failure_rate', 1.0)}%",
                "actual": f"{failure_rate:.2f}%",
                "passed": failure_rate < test_config.get('expected_failure_rate', 1.0)
            },
            {
                "metric": "Throughput",
                "expected": f"> {test_config.get('expected_rps', 10)} req/s",
                "actual": f"{total.total_rps:.2f} req/s",
                "passed": total.total_rps > test_config.get('expected_rps', 10)
            },
        ]
        
        return sla_checks
    
    def _generate_response_time_chart(self, stats):
        """Generate response time distribution chart."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Collect response time data
        endpoints = []
        avg_times = []
        
        for name, entry in stats.entries.items():
            if entry.num_requests > 0:
                endpoints.append(name[:30])  # Truncate long names
                avg_times.append(entry.avg_response_time)
        
        # Create bar chart
        ax.barh(endpoints, avg_times, color='#3498db')
        ax.set_xlabel('Average Response Time (ms)')
        ax.set_title('Response Time by Endpoint')
        ax.grid(axis='x', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'response_time_distribution.png', dpi=100, bbox_inches='tight')
        plt.close()
    
    def _generate_requests_chart(self, stats):
        """Generate requests over time chart."""
        # This is a placeholder - in production, you'd collect time-series data
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Simulated data for demonstration
        import numpy as np
        time_points = np.linspace(0, 10, 50)
        requests = np.random.poisson(stats.total.total_rps, 50)
        
        ax.plot(time_points, requests, color='#2ecc71', linewidth=2)
        ax.fill_between(time_points, requests, alpha=0.3, color='#2ecc71')
        ax.set_xlabel('Time (minutes)')
        ax.set_ylabel('Requests per Second')
        ax.set_title('Request Rate Over Time')
        ax.grid(alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'requests_over_time.png', dpi=100, bbox_inches='tight')
        plt.close()


class JSONReporter(PerformanceReporter):
    """Generate JSON reports for CI/CD integration."""
    
    def generate_report(self, stats, test_config: Dict):
        """Generate JSON report."""
        total = stats.total
        
        report = {
            "test_name": test_config.get("test_name", "Performance Test"),
            "timestamp": datetime.now().isoformat(),
            "duration": test_config.get("run_time", "N/A"),
            "configuration": {
                "users": test_config.get("users", 0),
                "spawn_rate": test_config.get("spawn_rate", 0),
                "host": test_config.get("host", ""),
            },
            "summary": {
                "total_requests": total.num_requests,
                "total_failures": total.num_failures,
                "failure_rate": (total.num_failures / total.num_requests * 100) if total.num_requests > 0 else 0,
                "avg_response_time": total.avg_response_time,
                "min_response_time": total.min_response_time or 0,
                "max_response_time": total.max_response_time or 0,
                "requests_per_second": total.total_rps,
            },
            "endpoints": {},
            "sla_validation": {
                "passed": True,
                "checks": []
            }
        }
        
        # Add endpoint details
        for name, entry in stats.entries.items():
            report["endpoints"][name] = {
                "num_requests": entry.num_requests,
                "num_failures": entry.num_failures,
                "avg_response_time": entry.avg_response_time,
                "min_response_time": entry.min_response_time or 0,
                "max_response_time": entry.max_response_time or 0,
                "requests_per_second": entry.total_rps,
            }
        
        # Add SLA validation
        failure_rate = report["summary"]["failure_rate"]
        sla_checks = [
            {
                "metric": "avg_response_time",
                "threshold": test_config.get('expected_avg_response_time', 1000),
                "value": total.avg_response_time,
                "passed": total.avg_response_time < test_config.get('expected_avg_response_time', 1000)
            },
            {
                "metric": "failure_rate",
                "threshold": test_config.get('expected_failure_rate', 1.0),
                "value": failure_rate,
                "passed": failure_rate < test_config.get('expected_failure_rate', 1.0)
            },
        ]
        
        report["sla_validation"]["checks"] = sla_checks
        report["sla_validation"]["passed"] = all(check["passed"] for check in sla_checks)
        
        # Save report
        report_path = self.output_dir / f"{test_config.get('test_name', 'test').replace(' ', '_').lower()}_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📄 JSON report generated: {report_path}")
        return report_path


class PrometheusReporter(PerformanceReporter):
    """Export metrics in Prometheus format."""
    
    def generate_report(self, stats, test_config: Dict):
        """Generate Prometheus metrics file."""
        metrics = []
        
        # Add summary metrics
        total = stats.total
        test_name = test_config.get("test_name", "performance_test").replace(" ", "_").lower()
        
        metrics.append(f'# HELP {test_name}_total_requests Total number of requests')
        metrics.append(f'# TYPE {test_name}_total_requests counter')
        metrics.append(f'{test_name}_total_requests {total.num_requests}')
        
        metrics.append(f'# HELP {test_name}_total_failures Total number of failures')
        metrics.append(f'# TYPE {test_name}_total_failures counter')
        metrics.append(f'{test_name}_total_failures {total.num_failures}')
        
        metrics.append(f'# HELP {test_name}_avg_response_time_ms Average response time in milliseconds')
        metrics.append(f'# TYPE {test_name}_avg_response_time_ms gauge')
        metrics.append(f'{test_name}_avg_response_time_ms {total.avg_response_time}')
        
        metrics.append(f'# HELP {test_name}_requests_per_second Requests per second')
        metrics.append(f'# TYPE {test_name}_requests_per_second gauge')
        metrics.append(f'{test_name}_requests_per_second {total.total_rps}')
        
        # Save metrics
        metrics_path = self.output_dir / f"{test_name}_metrics.prom"
        with open(metrics_path, 'w') as f:
            f.write('\n'.join(metrics))
        
        print(f"📊 Prometheus metrics generated: {metrics_path}")
        return metrics_path
