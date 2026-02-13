---
id: api-auth-001
title: API 认证与授权设计文档
owner: backend-team
tags: [api, authentication, oauth, jwt, 安全]
created: 2025-02-13
last_reviewed: 2025-02-13
confidence: high
---

# API 认证与授权设计文档

## 认证方式

系统采用 OAuth 2.0 + JWT 的认证方案。

### 登录流程

1. 客户端发送用户名密码到 `/api/v1/auth/login`
2. 服务端验证凭据，签发 access_token（15分钟）和 refresh_token（7天）
3. 客户端在后续请求的 `Authorization: Bearer <token>` 头中携带 access_token
4. access_token 过期后，用 refresh_token 到 `/api/v1/auth/refresh` 换取新 token

### JWT Token 结构

```json
{
  "sub": "user-uuid",
  "iss": "api-gateway",
  "iat": 1707820800,
  "exp": 1707821700,
  "roles": ["admin", "editor"],
  "tenant_id": "tenant-001"
}
```

### Token 验证

每个微服务独立验证 JWT：
- 验证签名（RS256，公钥从 JWKS endpoint 获取）
- 验证 `exp` 未过期
- 验证 `iss` 匹配
- 从 `roles` 字段提取权限

## 授权模型

采用 RBAC（基于角色的访问控制）：

| 角色 | 权限 |
|------|------|
| viewer | 只读访问 |
| editor | 读写访问 |
| admin | 全部权限 + 用户管理 |
| super_admin | 跨租户管理 |

### 资源级权限

除角色外，部分 API 支持资源级权限检查：

```python
@require_permission("document:write")
async def update_document(doc_id: str, user: User):
    doc = await get_document(doc_id)
    if doc.owner_id != user.id and "admin" not in user.roles:
        raise ForbiddenError("无权修改此文档")
```

## 安全要求

- access_token 有效期不超过 15 分钟
- refresh_token 单次使用，使用后立即轮换
- 敏感操作（删除、权限变更）需要二次验证
- 所有 token 传输必须使用 HTTPS
- 失败登录超过 5 次锁定账户 30 分钟

## API 错误码

| HTTP Status | 错误码 | 说明 |
|-------------|--------|------|
| 401 | UNAUTHORIZED | 未提供 token 或 token 无效 |
| 401 | TOKEN_EXPIRED | token 已过期，需刷新 |
| 403 | FORBIDDEN | 权限不足 |
| 429 | RATE_LIMITED | 请求频率超限 |
