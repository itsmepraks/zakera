# Security Incident Response Playbook

> **Classification:** Internal Use  
> **Version:** 1.0  
> **Last Updated:** February 2026  
> **Owner:** Security Team

## Quick Reference

### 🚨 Emergency Contacts

| Role | Contact | Response Time |
|------|---------|---------------|
| Security Lead | security@zakera.dev | < 15 min |
| DevOps On-Call | oncall@zakera.dev | < 30 min |
| Legal/Compliance | legal@zakera.dev | < 2 hours |
| Executive Team | exec@zakera.dev | < 4 hours |

### Incident Severity Levels

| Level | Description | Examples | Response Time |
|-------|-------------|----------|---------------|
| **P0 - Critical** | Active attack, data breach | RCE, data exfiltration | Immediate |
| **P1 - High** | Confirmed vulnerability | Auth bypass, SQL injection | < 1 hour |
| **P2 - Medium** | Potential security issue | Unusual access patterns | < 4 hours |
| **P3 - Low** | Security finding | Outdated dependency | < 24 hours |

---

## Phase 1: Detection & Identification

### 1.1 Detection Triggers

#### Automated Alerts

```yaml
# Alert triggers requiring investigation
security_alerts:
  - Multiple failed authentication attempts (>10 in 1 min)
  - Authorization bypass attempts
  - Unusual API access patterns
  - SQL injection pattern detected
  - XSS payload detected
  - Rate limit violations
  - Abnormal token usage
  - Suspicious file access
  - Privilege escalation attempts
  - Data export anomalies
```

#### Monitoring Dashboards

```bash
# Real-time security monitoring
Grafana: http://localhost:3001/d/security
Jaeger: http://localhost:16686
Prometheus: http://localhost:9090

# Security-specific queries
rate(authentication_failures_total[5m]) > 10
rate(authorization_failures_total[5m]) > 5
sum(rate(sql_injection_attempts_total[5m])) > 0
```

### 1.2 Initial Assessment

**IMMEDIATELY upon detection:**

1. ✅ **Note the time** - Record exact timestamp
2. ✅ **Capture evidence** - Take screenshots, copy logs
3. ✅ **Assess severity** - Use severity matrix above
4. ✅ **Alert team** - Page appropriate responders
5. ✅ **Start timeline** - Document all actions

**Assessment Questions:**

```yaml
What:
  - What type of incident is this?
  - What systems are affected?
  - What data may be compromised?

When:
  - When was it first detected?
  - When did it likely start?
  - Is it still ongoing?

Where:
  - Which systems/endpoints?
  - Which environment (prod/staging)?
  - Geographic source?

Who:
  - Who discovered it?
  - Who might be affected?
  - Who is the attacker (if known)?

How:
  - How was it detected?
  - How did it happen?
  - How can we stop it?
```

---

## Phase 2: Containment

### 2.1 Immediate Actions (First 15 Minutes)

#### For Active Attacks

```bash
# 1. Block attacker IP addresses
curl -X POST http://localhost:8000/admin/block-ip \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"ip": "1.2.3.4", "reason": "Security incident #INC-001"}'

# 2. Revoke compromised tokens
python scripts/revoke_tokens.py --user-id <USER_ID>

# 3. Enable enhanced monitoring
export SECURITY_LOG_LEVEL=DEBUG
export ENABLE_DETAILED_AUDIT_LOGS=true

# 4. Take snapshot of current state
docker exec -it zakera-db pg_dump > incident_snapshot_$(date +%s).sql
kubectl logs -l app=zakera --all-containers > incident_logs_$(date +%s).log
```

#### For Data Breaches

```bash
# 1. Identify affected users
python scripts/identify_affected_users.py --incident INC-001

# 2. Disable affected accounts (if necessary)
python scripts/disable_accounts.py --file affected_users.txt

# 3. Force password reset
python scripts/force_password_reset.py --file affected_users.txt

# 4. Notify users (prepare notification)
python scripts/prepare_breach_notification.py --incident INC-001
```

### 2.2 Containment Strategies

#### Network Level

```yaml
# Update firewall rules
kubectl apply -f kubernetes/network-policies/incident-lockdown.yml

# Block at load balancer
aws elb update-security-groups --load-balancer-name zakera-prod \
  --security-groups sg-incident-lockdown

# Enable DDoS protection
cloudflare zone set-security-level high
```

#### Application Level

```python
# src/security/incident_response.py

class IncidentContainment:
    async def enable_lockdown_mode(self, incident_id: str):
        """Enable security lockdown"""
        # 1. Increase rate limits strictness
        await self.rate_limiter.set_aggressive_mode()
        
        # 2. Require MFA for all requests
        await self.auth.require_mfa_all_users()
        
        # 3. Enable request logging
        await self.logger.set_max_verbosity()
        
        # 4. Disable non-essential features
        await self.feature_flags.disable_non_essential()
        
        logger.critical(f"Lockdown mode enabled: {incident_id}")
```

#### Database Level

```sql
-- Revoke write access temporarily
REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM app_user;

-- Enable query logging
ALTER DATABASE zakera SET log_statement = 'all';

-- Take backup
pg_dump zakera > incident_backup_$(date +%Y%m%d_%H%M%S).sql
```

---

## Phase 3: Eradication

### 3.1 Root Cause Analysis

```python
# Investigation script
import sys
from datetime import datetime, timedelta

class IncidentInvestigation:
    def analyze_attack_vector(self, incident_id: str):
        """Determine how the attack occurred"""
        
        # 1. Review audit logs
        logs = self.get_audit_logs(
            start_time=incident_start - timedelta(hours=24),
            end_time=datetime.now()
        )
        
        # 2. Analyze access patterns
        patterns = self.analyze_access_patterns(logs)
        
        # 3. Check for vulnerabilities
        vulns = self.scan_for_vulnerabilities()
        
        # 4. Review code changes
        recent_deploys = self.get_recent_deployments(days=7)
        
        return {
            "attack_vector": patterns.likely_vector,
            "vulnerabilities": vulns,
            "recent_changes": recent_deploys
        }
```

### 3.2 Remediation Steps

#### Patch Vulnerabilities

```bash
# 1. Apply security patches
git checkout -b hotfix/security-incident-001

# 2. Fix vulnerability
# (specific fix depends on vulnerability)

# 3. Test fix
pytest tests/security/ -v

# 4. Deploy emergency patch
make deploy-emergency-patch

# 5. Verify patch
curl -X POST http://localhost:8000/api/v1/verify-security-patch
```

#### Remove Backdoors/Malware

```bash
# 1. Scan for malware
clamscan -r /app --infected --log=incident_scan.log

# 2. Check for unauthorized changes
git diff production HEAD

# 3. Verify file integrity
md5sum -c checksums.txt

# 4. Rebuild from clean source
docker build --no-cache -t zakera:incident-clean .
```

#### Update Dependencies

```bash
# Update all dependencies to latest secure versions
pip install --upgrade $(pip freeze | cut -d'=' -f1)

# Check for known vulnerabilities
safety check --full-report

# Update Docker base image
docker pull python:3.11-slim
```

---

## Phase 4: Recovery

### 4.1 System Restoration

#### Pre-Recovery Checklist

- [ ] Root cause identified and fixed
- [ ] All vulnerabilities patched
- [ ] Malware/backdoors removed
- [ ] Security controls validated
- [ ] Monitoring enhanced
- [ ] Team briefed on changes

#### Recovery Steps

```bash
# 1. Restore from clean backup (if needed)
pg_restore -d zakera incident_backup_verified_clean.sql

# 2. Redeploy application
kubectl apply -f kubernetes/manifests/

# 3. Gradually restore traffic
# Start with 10% canary deployment
kubectl set image deployment/zakera-api \
  api=zakera:patched --record
kubectl scale deployment/zakera-api --replicas=1

# Monitor for 30 minutes, then scale up
kubectl scale deployment/zakera-api --replicas=3

# 4. Re-enable features gradually
python scripts/enable_features.py --gradual

# 5. Lift lockdown mode
curl -X POST http://localhost:8000/admin/disable-lockdown
```

### 4.2 User Communication

#### For Data Breaches (Required by Law)

```markdown
# Breach Notification Template

Subject: Important Security Update - Action Required

Dear [User],

We are writing to inform you of a security incident that may have 
affected your account.

**What Happened:**
On [DATE], we detected [DESCRIPTION]. We immediately took action to
secure our systems.

**What Information Was Involved:**
- [LIST OF DATA TYPES]

**What We Are Doing:**
- [REMEDIATION STEPS]
- Enhanced security monitoring
- Security review completed

**What You Should Do:**
1. Change your password immediately
2. Enable two-factor authentication
3. Monitor your account for suspicious activity
4. Review our updated security practices

**Questions?**
Contact: security@zakera.dev
Incident ID: INC-001

We sincerely apologize for this incident.

The Zakera Security Team
```

#### Notification Timeline

- **Immediately:** Internal team
- **< 72 hours:** Affected users (GDPR requirement)
- **< 72 hours:** Regulatory authorities (if required)
- **< 7 days:** Public disclosure (if widespread)

---

## Phase 5: Post-Incident Activities

### 5.1 Post-Incident Review (PIR)

**Schedule within 48 hours of incident resolution**

#### PIR Agenda

```yaml
1. Incident Timeline (15 min)
   - When detected
   - Response actions taken
   - Resolution timestamp

2. What Went Well (15 min)
   - Effective monitoring
   - Quick response
   - Good communication

3. What Could Be Improved (30 min)
   - Detection delays
   - Response gaps
   - Tool limitations

4. Root Cause (15 min)
   - Technical cause
   - Process failures
   - Human factors

5. Action Items (15 min)
   - Preventive measures
   - Process improvements
   - Tool enhancements
   - Training needs
```

### 5.2 Documentation

#### Incident Report Template

```yaml
Incident ID: INC-001
Date: 2026-02-24
Severity: P1 - High
Status: Resolved

Summary:
  Brief description of incident

Timeline:
  - 14:00 UTC: Initial detection
  - 14:05 UTC: Team alerted
  - 14:10 UTC: Containment started
  - 14:30 UTC: Attack stopped
  - 15:00 UTC: Root cause identified
  - 16:00 UTC: Patch deployed
  - 18:00 UTC: System restored
  - 20:00 UTC: Incident closed

Impact:
  - Users affected: 50
  - Data exposed: Email addresses
  - Downtime: 15 minutes
  - Financial impact: $X

Root Cause:
  SQL injection vulnerability in conversation export endpoint

Resolution:
  - Patched vulnerability
  - Enhanced input validation
  - Improved WAF rules

Preventive Measures:
  - [ ] Add input validation tests
  - [ ] Enable automated security scanning
  - [ ] Train team on secure coding
  - [ ] Update security guidelines

Lessons Learned:
  1. Need faster detection for SQL injection
  2. Better input validation framework
  3. Improve incident response time

Action Items:
  - SECURITY-101: Implement parameterized queries (Owner: @dev, Due: 2026-03-01)
  - SECURITY-102: Add SQLi detection (Owner: @security, Due: 2026-03-05)
  - SECURITY-103: Security training (Owner: @hr, Due: 2026-03-15)
```

### 5.3 Continuous Improvement

```python
# Track incident metrics
class IncidentMetrics:
    def record_incident(self, incident: Incident):
        metrics = {
            "time_to_detect": incident.detected_at - incident.started_at,
            "time_to_respond": incident.responded_at - incident.detected_at,
            "time_to_resolve": incident.resolved_at - incident.detected_at,
            "severity": incident.severity,
            "category": incident.category,
        }
        
        # Store in database
        await self.db.store_metrics(metrics)
        
        # Send to monitoring
        prometheus_client.Histogram(
            "incident_resolution_time_seconds",
            "Time to resolve security incident"
        ).observe(metrics["time_to_resolve"].total_seconds())
```

---

## Incident Categories & Runbooks

### Authentication Bypass

```yaml
Symptoms:
  - Users accessing accounts without proper authentication
  - JWT validation failures
  - Session hijacking detected

Immediate Actions:
  1. Revoke all active sessions
  2. Force re-authentication
  3. Enable MFA for all users
  4. Review authentication logs

Investigation:
  - Check JWT signing key integrity
  - Review session management code
  - Analyze authentication flow
  - Check for timing attacks

Remediation:
  - Rotate JWT signing keys
  - Fix authentication vulnerability
  - Enhance session security
  - Add monitoring for auth anomalies
```

### Data Exfiltration

```yaml
Symptoms:
  - Unusual data export patterns
  - Large volume downloads
  - Unauthorized API access
  - Database query anomalies

Immediate Actions:
  1. Block suspicious IPs
  2. Revoke API keys
  3. Disable export functionality
  4. Snapshot current database state

Investigation:
  - Identify affected data
  - Determine exfiltration method
  - Check for insider threat
  - Review access logs

Remediation:
  - Enhance data access controls
  - Implement data loss prevention
  - Add export monitoring
  - Enable encryption at rest
```

### SQL Injection

```yaml
Symptoms:
  - SQL error messages in responses
  - Unusual database queries
  - WAF SQL injection alerts
  - Suspicious input patterns

Immediate Actions:
  1. Enable WAF strict mode
  2. Add input validation
  3. Review database logs
  4. Check for data modifications

Investigation:
  - Identify injection point
  - Review vulnerable code
  - Check for data tampering
  - Analyze attack payloads

Remediation:
  - Use parameterized queries
  - Add input sanitization
  - Deploy updated code
  - Add SQLi detection rules
```

---

## Tools & Resources

### Investigation Tools

```bash
# Log analysis
jq '.level == "ERROR" or .security_event == true' logs/*.json

# Network traffic analysis
tcpdump -i any -w incident.pcap port 8000
wireshark incident.pcap

# Database forensics
psql zakera -c "SELECT * FROM audit_logs WHERE timestamp > '2026-02-24 14:00'"

# File integrity
tripwire --check

# Memory analysis
volatility -f memory.dump pslist
```

### External Resources

- **NIST Incident Response:** https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-61r2.pdf
- **SANS Incident Handler:** https://www.sans.org/reading-room/whitepapers/incident
- **OWASP Incident Response:** https://owasp.org/www-community/Incident_Response

---

## Training & Drills

### Tabletop Exercises (Quarterly)

```yaml
Scenario 1: Data Breach
  - Simulated database compromise
  - Practice notification procedures
  - Test backup restoration

Scenario 2: DDoS Attack
  - Simulated traffic spike
  - Practice scaling procedures
  - Test failover systems

Scenario 3: Insider Threat
  - Simulated malicious employee
  - Practice access revocation
  - Test audit log analysis
```

### Red Team Exercises (Annually)

- Full penetration test
- Social engineering attempts
- Physical security testing
- Incident response validation

---

## Compliance Requirements

### Regulatory Notifications

```yaml
GDPR (EU):
  - Notify supervisory authority < 72 hours
  - Notify affected individuals without undue delay
  - Document incident details

CCPA (California):
  - Notify affected users
  - Notify California AG if >500 residents
  
HIPAA (Healthcare):
  - Notify HHS < 60 days
  - Notify affected individuals < 60 days
  - Notify media if >500 affected
```

---

## Appendix

### A. Incident Severity Matrix

| Factor | P0 | P1 | P2 | P3 |
|--------|----|----|----|----|  
| Data Exposure | PII/PHI | Internal data | Metadata | Public data |
| Users Affected | >1000 | 100-1000 | 10-100 | <10 |
| System Impact | Complete outage | Major features | Minor features | No impact |
| Attack Active | Yes | Possible | No | No |

### B. Communication Templates

See: `docs/security/templates/`

### C. Legal Requirements

See: `docs/security/compliance/`

---

**Document Version:** 1.0  
**Last Updated:** February 2026  
**Next Review:** May 2026  
**Owner:** Security Team

**Emergency Hotline:** security@zakera.dev  
**Incident Reports:** https://incidents.zakera.dev
