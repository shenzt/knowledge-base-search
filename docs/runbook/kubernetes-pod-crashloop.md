---
id: k8s-crashloop-001
title: Kubernetes Pod CrashLoopBackOff Troubleshooting Guide
owner: platform-team
tags: [kubernetes, troubleshooting, runbook, pod]
created: 2025-02-13
last_reviewed: 2025-02-13
confidence: high
---

# Kubernetes Pod CrashLoopBackOff Troubleshooting Guide

## Overview

A Pod in `CrashLoopBackOff` state means the container is repeatedly crashing and Kubernetes is backing off before restarting it. This guide covers the most common causes and resolution steps.

## Symptoms

- `kubectl get pods` shows status `CrashLoopBackOff`
- Pod restart count keeps increasing
- Application is unavailable or degraded

## Diagnostic Steps

### 1. Check Pod Events

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Look for:
- `OOMKilled` — container exceeded memory limits
- `Error` — application crashed on startup
- `ContainerCannotRun` — image or entrypoint issue

### 2. Check Container Logs

```bash
# Current crash logs
kubectl logs <pod-name> -n <namespace>

# Previous crash logs
kubectl logs <pod-name> -n <namespace> --previous
```

### 3. Check Resource Limits

```bash
kubectl get pod <pod-name> -n <namespace> -o jsonpath='{.spec.containers[*].resources}'
```

If the container is OOMKilled, increase memory limits:

```yaml
resources:
  requests:
    memory: "256Mi"
  limits:
    memory: "512Mi"
```

### 4. Check Liveness Probe

A misconfigured liveness probe can cause unnecessary restarts:

```bash
kubectl get pod <pod-name> -n <namespace> -o jsonpath='{.spec.containers[*].livenessProbe}'
```

Common issues:
- `initialDelaySeconds` too short for slow-starting apps
- Health endpoint not implemented correctly
- Probe timeout too aggressive

## Common Causes and Fixes

| Cause | Fix |
|-------|-----|
| OOMKilled | Increase memory limits or fix memory leak |
| Config error | Check ConfigMap/Secret mounts, env vars |
| Missing dependency | Ensure dependent services are running |
| Bad image | Verify image tag and registry access |
| Liveness probe failure | Adjust probe timing or fix health endpoint |
| Permission denied | Check SecurityContext and RBAC |

## Escalation

If the issue persists after 30 minutes:
1. Page the application team owner
2. Check recent deployments: `kubectl rollout history deployment/<name>`
3. Consider rollback: `kubectl rollout undo deployment/<name>`
