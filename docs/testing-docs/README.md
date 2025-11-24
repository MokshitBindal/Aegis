# Aegis SIEM - Testing Documentation

**Complete guides for testing Aegis SIEM in VM environments**

---

## 📚 Documentation Index

### 1. [VM Setup Guide](VM_SETUP_GUIDE.md) 📘

**Comprehensive installation guide for two-machine testing environment**

Set up a complete test environment with:

- **VM 1 (Arch Linux):** Server + Dashboard + Agent
- **VM 2 (Ubuntu 22.04):** Agent only

This guide includes:

- ✅ Step-by-step VM creation (VirtualBox/VMware/KVM)
- ✅ Complete Arch Linux server installation
- ✅ Ubuntu agent installation
- ✅ Network configuration
- ✅ Service configuration
- ✅ Verification procedures

**Start here if:** You're setting up VMs from scratch for testing.

---

### 2. [VM Testing Checklist](VM_TESTING_CHECKLIST.md) ✅

**Quick reference checklist to track testing progress**

A printable/trackable checklist covering:

- ✓ VM setup verification
- ✓ Server installation steps
- ✓ Agent installation steps
- ✓ Functionality testing
- ✓ Performance validation
- ✓ Edge case testing
- ✓ Final sign-off

**Use this when:** You want a quick reference to ensure nothing is missed during testing.

---

### 3. [VM Troubleshooting Guide](VM_TROUBLESHOOTING.md) 🔧

**Solutions to common issues encountered during VM testing**

Quick fixes for:

- 🔧 PostgreSQL connection issues
- 🔧 Server startup failures
- 🔧 Dashboard 404 errors
- 🔧 Agent registration problems
- 🔧 Network connectivity issues
- 🔧 Database problems
- 🔧 Performance optimization
- 🔧 Recovery procedures

**Use this when:** Something isn't working and you need quick solutions.

---

## 🚀 Quick Start

### New to Testing?

**Follow this order:**

1. **Read:** [VM Setup Guide](VM_SETUP_GUIDE.md) - Understand the architecture
2. **Setup:** Follow VM creation and installation steps
3. **Track:** Use [VM Testing Checklist](VM_TESTING_CHECKLIST.md) to track progress
4. **Troubleshoot:** Refer to [VM Troubleshooting Guide](VM_TROUBLESHOOTING.md) if issues arise

### Already Have VMs?

**Jump to relevant sections:**

- Server not starting? → [Troubleshooting: Server Issues](VM_TROUBLESHOOTING.md#-server-issues-vm-1---arch)
- Agent can't connect? → [Troubleshooting: Agent Issues](VM_TROUBLESHOOTING.md#-agent-issues)
- Network problems? → [Troubleshooting: Network Issues](VM_TROUBLESHOOTING.md#-network-issues)

---

## 🎯 Testing Scenarios

### Scenario 1: Basic Functionality Test

**Duration:** 30 minutes  
**Goal:** Verify all components work

1. Install server on VM 1
2. Install agent on VM 1 (local monitoring)
3. Install agent on VM 2 (remote monitoring)
4. Verify both devices appear in dashboard
5. Check data collection (metrics, logs, commands)

**Success Criteria:** Both agents online, data flowing

---

### Scenario 2: Alert Testing

**Duration:** 15 minutes  
**Goal:** Test alert generation

1. Generate high CPU load: `stress-ng --cpu 4 --timeout 120s`
2. Wait 2-3 minutes
3. Verify alert appears in dashboard
4. Check alert details are accurate

**Success Criteria:** Alert generated with correct device info

---

### Scenario 3: ML Anomaly Detection

**Duration:** 30 minutes  
**Goal:** Test machine learning detection

1. Let system run normally for 10-15 minutes (baseline)
2. Perform anomalous actions:
   - Install unusual package
   - Run suspicious commands
   - Access uncommon files
3. Wait 5-10 minutes
4. Check for ML anomaly alerts

**Success Criteria:** Anomaly detected and alerted

---

### Scenario 4: Resilience Testing

**Duration:** 20 minutes  
**Goal:** Test recovery from failures

1. Stop agent service, verify dashboard shows offline
2. Restart agent, verify auto-reconnect
3. Restart server, verify agents reconnect
4. Disconnect network, verify buffering and recovery

**Success Criteria:** System recovers automatically from all failures

---

## 📊 Expected Resource Usage

### VM 1 (Arch - Server + Agent)

- **RAM:** 1.5 - 2.5 GB
- **CPU:** 5 - 15% (idle)
- **Disk:** < 5 GB
- **Network:** < 100 KB/s

### VM 2 (Ubuntu - Agent Only)

- **RAM:** 200 - 400 MB
- **CPU:** 1 - 5% (idle)
- **Disk:** < 500 MB
- **Network:** < 50 KB/s

---

## 🐛 Common Issues Quick Reference

| Issue                            | Quick Fix                                                       | Details                                                                   |
| -------------------------------- | --------------------------------------------------------------- | ------------------------------------------------------------------------- |
| PostgreSQL won't start           | `sudo -u postgres initdb -D /var/lib/postgres/data`             | [Full fix](VM_TROUBLESHOOTING.md#postgresql-wont-start)                   |
| Dashboard 404                    | Check `~/Aegis/aegis-dashboard/dist/` exists, rebuild if needed | [Full fix](VM_TROUBLESHOOTING.md#dashboard-shows-404-not-found)           |
| Agent won't register             | Generate new token, check server connectivity                   | [Full fix](VM_TROUBLESHOOTING.md#agent-wont-register)                     |
| Agents offline                   | Check firewall, verify server URL in agent config               | [Full fix](VM_TROUBLESHOOTING.md#agent-shows-offline-in-dashboard)        |
| Can't access dashboard from host | Use Bridged network mode, check VM firewall                     | [Full fix](VM_TROUBLESHOOTING.md#cant-access-dashboard-from-host-machine) |

---

## 🎬 Testing Workflow

```
┌─────────────────────────┐
│   Read VM Setup Guide   │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Create VM 1 (Arch)    │
│   Install Server +      │
│   Dashboard + Agent     │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Verify Server Access   │
│  Create Admin User      │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Create VM 2 (Ubuntu)   │
│  Install Agent          │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Verify Both Agents     │
│  Appear in Dashboard    │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Run Test Scenarios     │
│  (Use Checklist)        │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Document Results       │
│  Report Issues          │
└─────────────────────────┘
```

---

## 🆘 Getting Help

### Before Asking for Help

1. **Check the troubleshooting guide:** Most issues are covered there
2. **Collect diagnostic info:** See [Collect Diagnostic Information](VM_TROUBLESHOOTING.md#collect-diagnostic-information)
3. **Check logs:** `sudo journalctl -u aegis-server -n 100`

### Where to Get Help

- **GitHub Issues:** [Report bugs or ask questions](https://github.com/MokshitBindal/Aegis/issues)
- **Documentation:** Read all three testing guides thoroughly
- **Project Knowledge Base:** See `PROJECT_KNOWLEDGE_BASE.md` in root directory

---

## ✅ Success Checklist

Before considering testing complete:

- [ ] Server installed and running on VM 1
- [ ] Dashboard accessible from host browser
- [ ] Agent running on VM 1 (local monitoring)
- [ ] Agent running on VM 2 (remote monitoring)
- [ ] Both devices show "Online" in dashboard
- [ ] Metrics collected and displayed for both
- [ ] Commands logged from both devices
- [ ] Alerts generated appropriately
- [ ] ML anomaly detection working
- [ ] System recovers from service restarts
- [ ] No errors in logs
- [ ] Performance meets expected ranges
- [ ] All test scenarios passed
- [ ] Issues documented (if any)

---

## 📝 Testing Report Template

After completing testing, document your results:

```markdown
# Aegis SIEM Testing Report

**Date:** YYYY-MM-DD
**Tester:** Your Name
**Environment:** VirtualBox/VMware/KVM

## Setup Summary

- VM 1 (Arch): [IP Address]
- VM 2 (Ubuntu): [IP Address]
- Installation Time: [Total minutes]

## Test Results

- Server Installation: ✅ Pass / ❌ Fail
- Agent Installation (VM1): ✅ Pass / ❌ Fail
- Agent Installation (VM2): ✅ Pass / ❌ Fail
- Data Collection: ✅ Pass / ❌ Fail
- Alert Generation: ✅ Pass / ❌ Fail
- ML Detection: ✅ Pass / ❌ Fail
- Resilience Testing: ✅ Pass / ❌ Fail

## Issues Found

1. [Issue description and resolution]
2. [Issue description and resolution]

## Performance Metrics

- Server RAM: [X] GB
- Server CPU: [X]%
- Agent RAM: [X] MB
- Response Time: [X] ms

## Recommendations

1. [Recommendation]
2. [Recommendation]

## Overall Assessment

✅ Production Ready / ⚠️ Needs Fixes / ❌ Major Issues

**Signature:** ******\_\_\_******
```

---

## 🎯 Next Steps After Testing

1. **Production Deployment**

   - Use tested installers on production systems
   - Configure backups
   - Set up monitoring alerts

2. **Performance Tuning**

   - Optimize based on testing results
   - Adjust collection intervals
   - Configure resource limits

3. **Documentation Updates**

   - Document any issues found
   - Update guides with lessons learned
   - Create deployment runbooks

4. **Security Hardening**
   - Enable HTTPS
   - Configure firewall rules
   - Set up proper authentication

---

**Ready to test? Start with the [VM Setup Guide](VM_SETUP_GUIDE.md)! 🚀**

---

**Last Updated:** November 19, 2025  
**Version:** 1.0.0  
**Maintainer:** Mokshit Bindal
