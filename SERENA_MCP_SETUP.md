# Serena MCP 配置完成指南 ✅

## 📍 配置文件位置

配置文件已成功创建于：
```
C:\Users\szh2051\AppData\Roaming\Claude\claude_desktop_config.json
```

## 🎯 配置内容

```json
{
  "mcpServers": {
    "serena": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/oraios/serena",
        "serena",
        "start-mcp-server",
        "--project",
        "C:\\Users\\szh2051\\OneDrive - Carnival Corporation\\Desktop\\Python\\Claude Demo",
        "--context",
        "ide-assistant",
        "--mode",
        "interactive",
        "--mode",
        "editing",
        "--log-level",
        "INFO"
      ]
    }
  }
}
```

## 🚀 启用步骤

### 1️⃣ 重启 Claude Desktop
1. **完全关闭** Claude Desktop（确保从系统托盘也退出）
2. **重新打开** Claude Desktop
3. Serena MCP 将自动启动并加载

### 2️⃣ 验证 Serena 是否加载

打开 Claude Desktop 后，尝试以下命令：

#### 测试命令 1: 查看项目符号
```
"显示 app.py 文件中定义的所有类和函数"
```
如果 Serena 工作，Claude 会使用 `get_symbols_overview` 工具。

#### 测试命令 2: 查找符号
```
"查找项目中所有包含 'user' 的类"
```
如果 Serena 工作，Claude 会使用 `find_symbol` 工具。

#### 测试命令 3: 保存记忆
```
"记住这个项目使用 Flask 和 SQLite"
```
如果 Serena 工作，Claude 会使用 `write_memory` 工具。

### 3️⃣ 查看可用工具

在 Claude Desktop 中询问：
```
"你现在有哪些 Serena 工具可用？"
```

您应该能看到这些工具：
- ✅ `find_symbol` - 查找代码符号
- ✅ `find_referencing_symbols` - 查找引用
- ✅ `get_symbols_overview` - 文件符号概览
- ✅ `replace_symbol_body` - 替换符号定义
- ✅ `insert_before_symbol` / `insert_after_symbol` - 插入代码
- ✅ `rename_symbol` - 智能重命名
- ✅ `write_memory` / `read_memory` - 项目记忆
- ✅ `onboarding` - 项目分析
- ✅ 等 30+ 工具

## 📋 配置说明

### 当前配置参数

| 参数 | 值 | 说明 |
|------|-----|------|
| `--project` | 您的项目路径 | 指向 Claude Demo 项目 |
| `--context` | `ide-assistant` | IDE 辅助上下文，适合代码编辑 |
| `--mode` | `interactive`, `editing` | 启用交互和编辑模式 |
| `--log-level` | `INFO` | 日志级别 |

### 可选配置调整

如果需要修改配置，编辑 `claude_desktop_config.json`：

#### 启用 Web Dashboard
```json
"args": [
  ...
  "--enable-web-dashboard",
  "true"
]
```

#### 更改上下文
```json
"--context",
"desktop-app"  // 或 "agent", "codex" 等
```

#### 添加更多模式
```json
"--mode",
"interactive",
"--mode",
"editing",
"--mode",
"thinking"  // 启用思考模式
```

## 🎯 针对 Cruise Assessment 项目的使用建议

### 场景 1: 快速了解项目结构
```
"运行项目入门分析，了解测试和构建方式"
→ Serena 使用 onboarding() 自动分析
```

### 场景 2: 查找评估模块代码
```
"找到所有与 listening 评估相关的类和函数"
→ Serena 使用 find_symbol("listening")
```

### 场景 3: 重构代码
```
"把 calculate_score 函数重命名为 compute_assessment_score"
→ Serena 使用 rename_symbol() 安全重构
```

### 场景 4: 记录架构决策
```
"记住：所有评估模块在 src/main/python/modules/ 目录"
→ Serena 使用 write_memory() 保存
```

### 场景 5: 添加新功能
```
"在 AssessmentSession 类中添加一个 get_progress() 方法"
→ Serena 使用 insert_after_symbol() 精确插入
```

## 🔧 疑难解决

### 问题 1: Serena 没有加载

**检查步骤**:
1. 确认 Claude Desktop 完全重启
2. 检查 `uvx` 是否在系统 PATH 中：
   ```bash
   uvx --version
   ```
3. 查看 Claude Desktop 日志：
   - Help → View Logs
   - 查找 Serena 相关错误

### 问题 2: JSON 配置错误

**常见错误**:
- ❌ 路径使用单反斜杠：`C:\Users\...`
- ✅ 正确使用双反斜杠：`C:\\Users\\...`

### 问题 3: 项目路径不正确

**修改项目路径**:
编辑 `claude_desktop_config.json`，更新 `--project` 参数。

### 问题 4: uvx 未找到

**解决方案**:
1. 确认 uv 已安装：
   ```bash
   uv --version
   ```
2. 如果未安装，按照 Serena 文档安装 uv

## 📊 性能优化

### 大型项目优化

如果项目很大，可以添加超时设置：
```json
"args": [
  ...
  "--tool-timeout",
  "60.0"
]
```

### 减少日志输出

如果不需要详细日志：
```json
"--log-level",
"WARNING"
```

## 🆘 获取帮助

### Serena 文档
- GitHub: https://github.com/oraios/serena
- 查看更多配置选项和使用示例

### Claude Desktop 帮助
- Help → View Logs - 查看日志
- Help → Documentation - 官方文档

## ✅ 配置验证清单

- [ ] claude_desktop_config.json 已创建
- [ ] JSON 语法正确（路径使用双反斜杠）
- [ ] uvx 在系统中可用
- [ ] Claude Desktop 已完全重启
- [ ] Serena 工具在 Claude Desktop 中可见
- [ ] 测试命令成功执行

---

**🎉 配置完成！现在您可以在 Claude Desktop 中使用 Serena 的强大功能了！**

**下一步**: 打开 Claude Desktop，测试上面的验证命令，开始享受智能代码编辑体验！
