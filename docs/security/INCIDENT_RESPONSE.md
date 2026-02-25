# Security Incident Response Playbook

Comprehensive guide for handling security incidents at Zakera.

## 🚨 Emergency Contacts

**Security Team**
- Primary: security@zakera.ai
- On-call: +1-555-SECURITY
- Slack: #security-incidents

**Escalation Chain**
1. Security Lead → CTO → CEO
2. For P0/P1: Page on-call immediately
3. For P2+: Create incident in Slack

## 📊 Severity Classification

### P0 - Critical (Immediate Response)
**Response Time**: < 15 minutes  
**Examples**:
- Active data breach
- Production system compromised
- Ransomware attack
- Customer data exposed publicly
- Zero-day exploit being actively exploited

**Actions**:
1. Page on-call security team
2. Activate war room
3. Notify exec team
4. Consider taking systems offline

### P1 - High (Urgent Response)
**Response Time**: < 1 hour  
**Examples**:
- Suspected unauthorized access
- Critical vulnerability discovered
- Authentication bypass
- Privilege escalation
- SQL injection exploit

**Actions**:
1. Alert security team
2. Begin investigation
3. Prepare communication plan
4. Monitor for escalation

### P2 - Medium (Same Day Response)
**Response Time**: < 4 hours  
**Examples**:
- Suspicious activity detected
- Failed attack attempts
- Non-critical vulnerability
- Phishing attempt
- Brute force attempts

**Actions**:
1. Create incident ticket
2. Investigate during business hours
3. Document findings
4. Implement preventive measures

### P3 - Low (Best Effort)
**Response Time**: < 1 week  
**Examples**:
- Security policy violations
- Low-severity vulnerabilities
- Security awareness issues

**Actions**:
1. Log incident
2. Review during security sprint
3. Update documentation

## 🔍 Incident Response Phases

### 1. Detection

**How Incidents Are Detected**:
- Automated alerts (SIEM, IDS/IPS)
- User reports
- Security monitoring
- Penetration testing
- Bug bounty reports
- Third-party notifications

**Initial Assessment Questions**:
- What happened?
- When did it happen?
- How was it detected?
- What systems are affected?
- Is it still ongoing?
- What data is at risk?

### 2. Containment

**Immediate Actions** (First 30 minutes):

```bash
# 1. Isolate affected systems
# Block malicious IPs
sudo iptables -A INPUT -s MALICIOUS_IP -j DROP

# 2. Disable compromised accounts
aws iam update-access-key --access-key-id KEY --status Inactive

# 3. Revoke suspicious sessions
# Via API or database
DELETE FROM sessions WHERE suspicious = true;

# 4. Take snapshot for forensics
aws ec2 create-snapshot --volume-id VOLUME_ID

# 5. Enable additional logging
# Increase log verbosity for investigation
```

**Containment Checklist**:
- [ ] Identify and isolate affected systems
- [ ] Block malicious IPs/domains
- [ ] Disable compromised accounts
- [ ] Revoke exposed credentials/tokens
- [ ] Take system snapshots
- [ ] Preserve evidence
- [ ] Enable enhanced logging
- [ ] Notify relevant teams

### 3. Eradication

**Remove Threat**:

```bash
# 1. Remove malware/backdoors
find / -name "suspicious_file.php" -delete

# 2. Patch vulnerabilities
apt update && apt upgrade

# 3. Reset all credentials
# Force password resets for affected users
python scripts/force_password_reset.py --users affected_users.txt

# 4. Rotate API keys
python scripts/rotate_api_keys.py

# 5. Update firewall rules
# Block attack vectors
```

**Eradication Checklist**:
- [ ] Remove malicious code/files
- [ ] Patch vulnerabilities
- [ ] Reset compromised credentials
- [ ] Rotate API keys and secrets
- [ ] Update security configurations
- [ ] Scan for additional compromises
- [ ] Verify integrity of systems

### 4. Recovery

**Restore Normal Operations**:

```bash
# 1. Verify systems are clean
# Run malware scans
clamscan -r /var/www

# 2. Restore from clean backup (if needed)
aws ec2 restore-snapshot --snapshot-id CLEAN_SNAPSHOT

# 3. Gradually restore services
# Monitor for re-infection
kubectl scale deployment app --replicas=1
# Wait and monitor
kubectl scale deployment app --replicas=5

# 4. Re-enable disabled features
# After verification
```

**Recovery Checklist**:
- [ ] Verify systems are clean
- [ ] Restore from clean backups
- [ ] Gradually restore services
- [ ] Monitor for reinfection
- [ ] Re-enable security controls
- [ ] Update monitoring rules
- [ ] Test functionality
- [ ] Document changes

### 5. Post-Incident Analysis

**Within 72 Hours**:

1. **Timeline Creation**
   - When was the breach?
   - How long were attackers active?
   - What did they access?
   - When was it detected?
   - When was it contained?

2. **Root Cause Analysis**
   - How did the breach occur?
   - What vulnerability was exploited?
   - Why wasn't it prevented?
   - What controls failed?

3. **Impact Assessment**
   - What data was accessed/stolen?
   - How many users affected?
   - What systems compromised?
   - Financial impact?
   - Reputational impact?

4. **Lessons Learned**
   - What went well?
   - What went poorly?
   - What should change?
   - What training is needed?

5. **Action Items**
   - Technical improvements
   - Process improvements
   - Training needs
   - Policy updates

**Post-Mortem Template**:

```markdown
# Security Incident Post-Mortem

## Incident Summary
- **Date**: 2026-02-24
- **Severity**: P1 - High
- **Duration**: 2 hours 15 minutes
- **Affected Systems**: Production API

## Timeline
- 14:23 - Suspicious activity detected
- 14:30 - Incident declared
- 14:45 - Systems isolated
- 16:30 - Threat eradicated
- 16:38 - Systems restored

## Root Cause
- SQL injection vulnerability in API endpoint
- Input validation bypass
- Insufficient WAF rules

## Impact
- 500 user records accessed
- No data exfiltration confirmed
- 2 hours of downtime

## What Went Well
- Fast detection (7 minutes)
- Good communication
- Effective containment

## What Went Poorly
- Vulnerability should have been caught in code review
- No automated SQL injection testing
- Delayed executive notification

## Action Items
- [ ] Add SQL injection tests to CI/CD
- [ ] Implement code scanning (CodeQL)
- [ ] Update WAF rules
- [ ] Security training for dev team
- [ ] Update incident response runbook

## Follow-up
- Security audit scheduled for next week
- Penetration test in 2 weeks
- User notification sent
```

## 📢 Communication

### Internal Communication

**During Incident**:
- Use #security-incidents Slack channel
- Create incident war room
- Provide regular updates (every 30 minutes)
- Document all actions in incident ticket

**After Incident**:
- Send post-mortem to all teams
- Present lessons learned
- Update security documentation

### External Communication

**Customer Notification** (if data breach):

```
Subject: Security Incident Notification - Action Required

Dear Zakera User,

We are writing to inform you about a security incident that may have
affected your account.

**What Happened**:
On [DATE], we discovered [DESCRIPTION]. We immediately took action to
contain the incident and protect your data.

**What Information Was Involved**:
[LIST OF DATA TYPES - be specific]

**What We're Doing**:
- Patched the vulnerability
- Enhanced security monitoring
- Working with law enforcement

**What You Should Do**:
1. Reset your password immediately
2. Enable multi-factor authentication
3. Monitor your account for suspicious activity
4. Review our security best practices

**More Information**:
For more details, visit: https://zakera.ai/security-incident

We sincerely apologize for this incident and the concern it may cause.

Security Team
Zakera AI
```

### Regulatory Notification

**GDPR** (if EU data affected):
- Notify supervisory authority within 72 hours
- Provide: nature of breach, categories and number of affected, likely consequences, measures taken

**State Laws** (if US data affected):
- Check state breach notification laws
- Typically 30-60 days to notify
- Some states require media notification for large breaches

## 🔐 Evidence Preservation

**Legal Hold Procedures**:

```bash
# 1. Take system snapshots
aws ec2 create-snapshot --volume-id vol-xxx

# 2. Copy logs to secure storage
aws s3 cp /var/log/nginx/ s3://security-evidence/incident-001/ --recursive

# 3. Hash files for integrity
sha256sum /var/log/nginx/* > checksums.txt

# 4. Protect from deletion
aws s3api put-object-legal-hold --bucket security-evidence \
  --key incident-001/logs.tar.gz --legal-hold Status=ON
```

**Chain of Custody**:
- Document who accessed evidence
- When it was accessed
- What was done
- Maintain integrity hashes

## 🧪 Testing & Drills

**Quarterly Incident Response Drills**:

1. **Tabletop Exercise** - Discuss scenario
2. **Simulation** - Practice response
3. **Red Team Exercise** - Real attack simulation
4. **After-action Review** - Identify improvements

**Example Scenarios**:
- Ransomware attack
- Data breach
- DDoS attack
- Insider threat
- Supply chain compromise

## 📚 Resources

### Incident Response Tools
- **Forensics**: Volatility, Autopsy, Wireshark
- **Malware Analysis**: VirusTotal, Hybrid Analysis
- **Log Analysis**: ELK Stack, Splunk
- **Network Analysis**: tcpdump, Zeek

### External Resources
- [NIST Incident Response Guide](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-61r2.pdf)
- [SANS Incident Response](https://www.sans.org/incident-response/)
- [OWASP Incident Response](https://owasp.org/www-community/Incident_Response)

---

**Last Updated**: February 24, 2026  
**Next Drill**: May 24, 2026  
**On-Call**: security-oncall@zakera.ai

⚠️ **This is a living document. Update after each incident.**
