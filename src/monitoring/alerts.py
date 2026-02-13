"""Alert management system"""

import asyncio
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from dataclasses import dataclass
import json
import httpx
from datetime import datetime, timedelta

from .logging import get_logger

logger = get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert definition"""
    name: str
    severity: AlertSeverity
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    resolved: bool = False
    resolution_time: Optional[datetime] = None


class AlertChannel:
    """Base class for alert channels"""
    
    async def send(self, alert: Alert):
        """Send alert through this channel"""
        raise NotImplementedError


class EmailAlertChannel(AlertChannel):
    """Email alert channel"""
    
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addrs: List[str],
        use_tls: bool = True
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs
        self.use_tls = use_tls
    
    async def send(self, alert: Alert):
        """Send alert via email"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.name}"
            msg['From'] = self.from_addr
            msg['To'] = ', '.join(self.to_addrs)
            
            # Create email body
            text_body = f"""
            Alert: {alert.name}
            Severity: {alert.severity.value}
            Time: {alert.timestamp.isoformat()}
            
            Message:
            {alert.message}
            
            Details:
            {json.dumps(alert.details, indent=2)}
            """
            
            html_body = f"""
            <html>
              <head></head>
              <body>
                <h2 style="color: {'red' if alert.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL] else 'orange'}">
                  {alert.severity.value.upper()}: {alert.name}
                </h2>
                <p><strong>Time:</strong> {alert.timestamp.isoformat()}</p>
                <p><strong>Message:</strong> {alert.message}</p>
                <h3>Details:</h3>
                <pre>{json.dumps(alert.details, indent=2)}</pre>
              </body>
            </html>
            """
            
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            await aiosmtplib.send(
                msg,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.username,
                password=self.password,
                use_tls=self.use_tls
            )
            
            logger.info(
                f"Alert sent via email",
                alert_name=alert.name,
                severity=alert.severity.value,
                recipients=self.to_addrs
            )
        
        except Exception as e:
            logger.error(
                f"Failed to send email alert: {e}",
                alert_name=alert.name,
                error=str(e)
            )


class WebhookAlertChannel(AlertChannel):
    """Webhook alert channel (Slack, Discord, etc.)"""
    
    def __init__(
        self,
        webhook_url: str,
        format: str = "slack"  # slack, discord, generic
    ):
        self.webhook_url = webhook_url
        self.format = format
    
    async def send(self, alert: Alert):
        """Send alert via webhook"""
        try:
            # Format message based on platform
            if self.format == "slack":
                payload = self._format_slack(alert)
            elif self.format == "discord":
                payload = self._format_discord(alert)
            else:
                payload = self._format_generic(alert)
            
            # Send webhook
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()
            
            logger.info(
                f"Alert sent via webhook",
                alert_name=alert.name,
                severity=alert.severity.value,
                format=self.format
            )
        
        except Exception as e:
            logger.error(
                f"Failed to send webhook alert: {e}",
                alert_name=alert.name,
                error=str(e)
            )
    
    def _format_slack(self, alert: Alert) -> Dict:
        """Format alert for Slack"""
        color = {
            AlertSeverity.INFO: "#36a64f",
            AlertSeverity.WARNING: "#ff9900",
            AlertSeverity.ERROR: "#ff0000",
            AlertSeverity.CRITICAL: "#990000"
        }[alert.severity]
        
        return {
            "attachments": [{
                "color": color,
                "title": f"{alert.severity.value.upper()}: {alert.name}",
                "text": alert.message,
                "fields": [
                    {"title": key, "value": str(value), "short": True}
                    for key, value in alert.details.items()
                ],
                "ts": int(alert.timestamp.timestamp())
            }]
        }
    
    def _format_discord(self, alert: Alert) -> Dict:
        """Format alert for Discord"""
        color_map = {
            AlertSeverity.INFO: 0x36a64f,
            AlertSeverity.WARNING: 0xff9900,
            AlertSeverity.ERROR: 0xff0000,
            AlertSeverity.CRITICAL: 0x990000
        }
        
        return {
            "embeds": [{
                "title": f"{alert.severity.value.upper()}: {alert.name}",
                "description": alert.message,
                "color": color_map[alert.severity],
                "fields": [
                    {"name": key, "value": str(value), "inline": True}
                    for key, value in alert.details.items()
                ],
                "timestamp": alert.timestamp.isoformat()
            }]
        }
    
    def _format_generic(self, alert: Alert) -> Dict:
        """Format alert as generic JSON"""
        return {
            "name": alert.name,
            "severity": alert.severity.value,
            "message": alert.message,
            "details": alert.details,
            "timestamp": alert.timestamp.isoformat()
        }


class AlertManager:
    """
    Central alert management system
    """
    
    def __init__(self):
        self.channels: List[AlertChannel] = []
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.alert_rules: Dict[str, Callable] = {}
        self._cooldown_periods: Dict[str, datetime] = {}
        self.default_cooldown = timedelta(minutes=15)
    
    def add_channel(self, channel: AlertChannel):
        """Add an alert channel"""
        self.channels.append(channel)
        logger.info(f"Added alert channel: {type(channel).__name__}")
    
    def register_rule(
        self,
        name: str,
        check_func: Callable[[Any], bool],
        severity: AlertSeverity,
        message_func: Callable[[Any], str],
        cooldown: Optional[timedelta] = None
    ):
        """Register an alert rule"""
        self.alert_rules[name] = {
            "check": check_func,
            "severity": severity,
            "message": message_func,
            "cooldown": cooldown or self.default_cooldown
        }
    
    async def check_rules(self, context: Dict[str, Any]):
        """Check all alert rules"""
        for name, rule in self.alert_rules.items():
            try:
                # Check if alert is in cooldown
                if name in self._cooldown_periods:
                    if datetime.now() < self._cooldown_periods[name]:
                        continue
                
                # Check rule condition
                if rule["check"](context):
                    # Create alert
                    alert = Alert(
                        name=name,
                        severity=rule["severity"],
                        message=rule["message"](context),
                        details=context,
                        timestamp=datetime.now()
                    )
                    
                    # Send alert
                    await self.send_alert(alert)
                    
                    # Set cooldown
                    self._cooldown_periods[name] = datetime.now() + rule["cooldown"]
                else:
                    # Resolve alert if it was active
                    if name in self.active_alerts:
                        await self.resolve_alert(name)
            
            except Exception as e:
                logger.error(
                    f"Error checking alert rule {name}: {e}",
                    rule_name=name,
                    error=str(e)
                )
    
    async def send_alert(self, alert: Alert):
        """Send alert through all channels"""
        # Store alert
        self.active_alerts[alert.name] = alert
        self.alert_history.append(alert)
        
        # Log alert
        logger.log(
            alert.severity.value,
            f"Alert triggered: {alert.name}",
            alert_name=alert.name,
            severity=alert.severity.value,
            message=alert.message,
            **alert.details
        )
        
        # Send through all channels
        tasks = [channel.send(alert) for channel in self.channels]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def resolve_alert(self, alert_name: str):
        """Resolve an active alert"""
        if alert_name in self.active_alerts:
            alert = self.active_alerts[alert_name]
            alert.resolved = True
            alert.resolution_time = datetime.now()
            
            del self.active_alerts[alert_name]
            
            logger.info(
                f"Alert resolved: {alert_name}",
                alert_name=alert_name,
                duration_seconds=(alert.resolution_time - alert.timestamp).total_seconds()
            )
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return list(self.active_alerts.values())
    
    def get_alert_history(
        self,
        limit: int = 100,
        severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """Get alert history"""
        history = self.alert_history[-limit:]
        
        if severity:
            history = [a for a in history if a.severity == severity]
        
        return history


# Global alert manager
alert_manager = AlertManager()


# =============================================================================
# Built-in Alert Rules
# =============================================================================

def register_default_alerts():
    """Register default alert rules"""
    
    # High error rate
    alert_manager.register_rule(
        name="high_error_rate",
        check_func=lambda ctx: ctx.get("error_rate", 0) > 0.1,  # 10%
        severity=AlertSeverity.ERROR,
        message_func=lambda ctx: f"High error rate detected: {ctx.get('error_rate', 0) * 100:.1f}%",
        cooldown=timedelta(minutes=15)
    )
    
    # High CPU usage
    alert_manager.register_rule(
        name="high_cpu_usage",
        check_func=lambda ctx: ctx.get("cpu_percent", 0) > 90,
        severity=AlertSeverity.WARNING,
        message_func=lambda ctx: f"High CPU usage: {ctx.get('cpu_percent', 0):.1f}%",
        cooldown=timedelta(minutes=10)
    )
    
    # High memory usage
    alert_manager.register_rule(
        name="high_memory_usage",
        check_func=lambda ctx: ctx.get("memory_percent", 0) > 90,
        severity=AlertSeverity.WARNING,
        message_func=lambda ctx: f"High memory usage: {ctx.get('memory_percent', 0):.1f}%",
        cooldown=timedelta(minutes=10)
    )
    
    # Database connection failures
    alert_manager.register_rule(
        name="database_connection_failure",
        check_func=lambda ctx: not ctx.get("database_healthy", True),
        severity=AlertSeverity.CRITICAL,
        message_func=lambda ctx: "Database connection failed",
        cooldown=timedelta(minutes=5)
    )
    
    # Model provider down
    alert_manager.register_rule(
        name="all_model_providers_down",
        check_func=lambda ctx: ctx.get("healthy_providers", 1) == 0,
        severity=AlertSeverity.CRITICAL,
        message_func=lambda ctx: "All model providers are unavailable",
        cooldown=timedelta(minutes=5)
    )
    
    # Slow response time
    alert_manager.register_rule(
        name="slow_response_time",
        check_func=lambda ctx: ctx.get("avg_response_time_ms", 0) > 5000,
        severity=AlertSeverity.WARNING,
        message_func=lambda ctx: f"Slow response time: {ctx.get('avg_response_time_ms', 0):.0f}ms",
        cooldown=timedelta(minutes=15)
    )
