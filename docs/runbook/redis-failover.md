---
id: redis-failover-001
title: Redis 主从切换故障恢复手册
owner: sre-team
tags: [redis, failover, runbook, 高可用]
created: 2025-02-13
last_reviewed: 2025-02-13
confidence: high
---

# Redis 主从切换故障恢复手册

## 概述

当 Redis Sentinel 触发主从切换（failover）后，应用层需要正确处理连接重建。本文档描述完整的故障恢复流程。

## 故障现象

- 应用日志出现大量 `READONLY You can't write against a read only replica` 错误
- Sentinel 日志显示 `+switch-master` 事件
- 监控告警：Redis 写入延迟突增

## 排查步骤

### 1. 确认 Sentinel 状态

```bash
redis-cli -p 26379 SENTINEL masters
redis-cli -p 26379 SENTINEL get-master-addr-by-name mymaster
```

确认新 master 的 IP 和端口。

### 2. 检查新 master 状态

```bash
redis-cli -h <new-master-ip> -p 6379 INFO replication
```

确认 `role:master`，检查 `connected_slaves` 数量。

### 3. 检查应用连接池

确认应用是否已经切换到新 master：

```bash
# 查看应用连接数
redis-cli -h <new-master-ip> CLIENT LIST | wc -l
```

## 恢复操作

### 自动恢复（推荐）

如果应用使用 Sentinel 客户端（如 Jedis Sentinel、redis-py Sentinel），连接会自动切换。检查：

1. 确认客户端配置了 Sentinel 地址而非直连 master
2. 确认连接池的 `testOnBorrow` 或等效配置已开启
3. 等待 30 秒，观察错误率是否下降

### 手动恢复

如果应用直连 master IP：

1. 获取新 master 地址：`redis-cli -p 26379 SENTINEL get-master-addr-by-name mymaster`
2. 更新应用配置中的 Redis 地址
3. 滚动重启应用 Pod

```bash
kubectl rollout restart deployment/<app-name> -n <namespace>
```

## 预防措施

- 所有应用必须使用 Sentinel 客户端，禁止直连 master IP
- 连接池配置 `minEvictableIdleTimeMillis=60000`
- 定期演练 failover：`redis-cli -p 26379 SENTINEL failover mymaster`

## 相关文档

- Redis Sentinel 架构设计
- 应用连接池配置规范
