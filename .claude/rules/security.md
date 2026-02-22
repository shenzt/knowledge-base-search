# 安全规则

## API Key / Secret 禁止硬编码

- API key、token、secret、password 只能放在 `.env`（已 gitignore）或环境变量中
- 脚本中用 `${VAR:?请设置环境变量}` 引用，不要写明文值
- 提交前检查：`git diff --cached | grep -iE "sk-|api.key|token|secret|password"`
- `.env`、`config.json`（含 key 的）必须在 `.gitignore` 中
- 发现泄露后：1) 立即从文件中移除 2) `git-filter-repo` 清历史 3) force push 4) 轮换 key

## 代码中的安全实践

- 不要在日志中输出完整的 API key（最多显示前 4 位 + `***`）
- 环境变量优先级：`.env` < 系统环境变量 < 命令行参数
- 测试代码中使用 mock key（如 `sk-test-xxx`），不要用真实 key
