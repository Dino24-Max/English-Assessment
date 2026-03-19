# 🧪 所有测试链接 - Test Links

**服务器地址**: `http://127.0.0.1:8000`  
**默认端口**: `8000`  
**启动命令**: `python run_server.py`

---

## 📋 目录 Table of Contents

1. [前端页面链接](#前端页面链接-ui-pages)
2. [API 端点链接](#api-端点链接-api-endpoints)
3. [管理后台链接](#管理后台链接-admin-pages)
4. [测试工具链接](#测试工具链接-testing-tools)
5. [文档链接](#文档链接-documentation)

---

## 🌐 前端页面链接 (UI Pages)

### 用户流程页面

| 页面 | 链接 | 说明 |
|------|------|------|
| **首页** | `http://127.0.0.1:8000/` | 主页面 |
| **说明页面** | `http://127.0.0.1:8000/instructions` | 评估说明 |
| **开始评估** | `http://127.0.0.1:8000/start-assessment` | 开始评估页面 |
| **题目页面** | `http://127.0.0.1:8000/question/{question_num}` | 答题页面 (question_num: 1-21) |
| **结果页面** | `http://127.0.0.1:8000/results` | 评估结果页面 |
| **防作弊报告** | `http://127.0.0.1:8000/anti-cheating-report` | 防作弊行为报告 |

### 认证页面

| 页面 | 链接 | 说明 |
|------|------|------|
| **邀请页面** | `http://127.0.0.1:8000/invitation` | 查看邀请信息 |
| **注册页面** | `http://127.0.0.1:8000/register` | 用户注册 (支持邀请码: `?code=XXXX`) |
| **登录页面** | `http://127.0.0.1:8000/login` | 用户登录 |

### 管理后台页面

| 页面 | 链接 | 说明 |
|------|------|------|
| **管理首页** | `http://127.0.0.1:8000/admin` | 管理后台主页 |
| **邀请码管理** | `http://127.0.0.1:8000/admin/invitations` | 创建和管理邀请码 |
| **排行榜** | `http://127.0.0.1:8000/admin/scoreboard` | 成绩排行榜 |

### 调试页面

| 页面 | 链接 | 说明 |
|------|------|------|
| **会话调试** | `http://127.0.0.1:8000/debug/session` | 查看当前会话信息 |

---

## 🔌 API 端点链接 (API Endpoints)

### 基础端点

| 端点 | 方法 | 链接 | 说明 |
|------|------|------|------|
| **API 根** | GET | `http://127.0.0.1:8000/api` | API 信息 |
| **健康检查** | GET | `http://127.0.0.1:8000/health` | 服务器健康状态 |
| **UI 健康检查** | GET | `http://127.0.0.1:8000/health` | UI 路由健康检查 |

### 认证 API (`/api/v1/auth`)

| 端点 | 方法 | 链接 | 说明 |
|------|------|------|------|
| **注册** | POST | `http://127.0.0.1:8000/api/v1/auth/register` | 用户注册 |
| **登录** | POST | `http://127.0.0.1:8000/api/v1/auth/login` | 用户登录 |
| **登出** | POST | `http://127.0.0.1:8000/api/v1/auth/logout` | 用户登出 |
| **检查邮箱** | GET | `http://127.0.0.1:8000/api/v1/auth/check-email?email=xxx@example.com` | 检查邮箱是否已注册 |
| **当前用户** | GET | `http://127.0.0.1:8000/api/v1/auth/me` | 获取当前登录用户信息 |

### 评估 API (`/api/v1/assessment`)

| 端点 | 方法 | 链接 | 说明 |
|------|------|------|------|
| **注册候选人** | POST | `http://127.0.0.1:8000/api/v1/assessment/register` | 注册评估候选人 |
| **创建评估** | POST | `http://127.0.0.1:8000/api/v1/assessment/create` | 创建新评估 |
| **开始评估** | POST | `http://127.0.0.1:8000/api/v1/assessment/{assessment_id}/start` | 开始评估 |
| **提交答案** | POST | `http://127.0.0.1:8000/api/v1/assessment/{assessment_id}/answer` | 提交题目答案 |
| **提交口语** | POST | `http://127.0.0.1:8000/api/v1/assessment/{assessment_id}/speaking` | 提交口语录音 |
| **完成评估** | POST | `http://127.0.0.1:8000/api/v1/assessment/{assessment_id}/complete` | 完成评估 |
| **评估状态** | GET | `http://127.0.0.1:8000/api/v1/assessment/{assessment_id}/status` | 获取评估状态 |
| **加载题目** | POST | `http://127.0.0.1:8000/api/v1/assessment/load-questions` | 加载题目到数据库 |
| **跟踪标签切换** | POST | `http://127.0.0.1:8000/api/v1/assessment/track-tab-switch` | 记录标签页切换 |
| **跟踪复制粘贴** | POST | `http://127.0.0.1:8000/api/v1/assessment/track-copy-paste` | 记录复制粘贴行为 |

### 管理 API (`/api/v1/admin`)

| 端点 | 方法 | 链接 | 说明 |
|------|------|------|------|
| **加载完整题库** | POST | `http://127.0.0.1:8000/api/v1/admin/load-full-question-bank?admin_key=dev-admin-key-123` | 加载1600题到数据库 |
| **统计信息** | GET | `http://127.0.0.1:8000/api/v1/admin/stats` | 获取系统统计 |
| **检查配置** | GET | `http://127.0.0.1:8000/api/v1/admin/check-config` | 检查系统配置 |
| **防作弊评估列表** | GET | `http://127.0.0.1:8000/api/v1/admin/anti-cheating/assessments` | 获取可疑评估列表 |
| **防作弊详情** | GET | `http://127.0.0.1:8000/api/v1/admin/anti-cheating/assessment/{assessment_id}` | 获取评估防作弊详情 |
| **创建邀请码** | POST | `http://127.0.0.1:8000/api/v1/admin/invitation/create` | 创建邀请码 |
| **邀请码列表** | GET | `http://127.0.0.1:8000/api/v1/admin/invitations` | 获取所有邀请码 |
| **邀请码状态** | GET | `http://127.0.0.1:8000/api/v1/admin/invitation/{code}/status` | 检查邀请码状态 |
| **删除邀请码** | DELETE | `http://127.0.0.1:8000/api/v1/admin/invitation/{code}` | 删除邀请码 |
| **验证邀请码** | GET | `http://127.0.0.1:8000/api/v1/admin/invitation/{code}/validate` | 验证邀请码有效性 |
| **评估列表** | GET | `http://127.0.0.1:8000/api/v1/admin/assessments` | 获取所有评估 |
| **导出评估** | GET | `http://127.0.0.1:8000/api/v1/admin/assessments/export` | 导出评估数据 |
| **评估详情** | GET | `http://127.0.0.1:8000/api/v1/admin/assessment/{assessment_id}` | 获取评估详情 |

### 分析 API (`/api/v1/analytics`)

| 端点 | 方法 | 链接 | 说明 |
|------|------|------|------|
| **分析仪表板** | GET | `http://127.0.0.1:8000/api/v1/analytics/dashboard` | 获取分析数据 |

---

## 🛠️ 管理后台链接 (Admin Pages)

### 管理功能

| 功能 | 链接 | 说明 |
|------|------|------|
| **管理首页** | `http://127.0.0.1:8000/admin` | 管理后台主页 |
| **邀请码管理** | `http://127.0.0.1:8000/admin/invitations` | 创建和管理邀请码 |
| **成绩排行榜** | `http://127.0.0.1:8000/admin/scoreboard` | 查看所有用户成绩 |

---

## 🧪 测试工具链接 (Testing Tools)

### API 文档

| 工具 | 链接 | 说明 |
|------|------|------|
| **Swagger UI** | `http://127.0.0.1:8000/docs` | 交互式 API 文档 (推荐) |
| **ReDoc** | `http://127.0.0.1:8000/redoc` | 替代 API 文档视图 |

### 测试脚本

| 脚本 | 命令 | 说明 |
|------|------|------|
| **运行所有测试** | `python run_tests.py` | 运行完整测试套件 |
| **单元测试** | `pytest src/test/unit/ -v` | 运行单元测试 |
| **集成测试** | `pytest src/test/integration/ -v` | 运行集成测试 |
| **性能测试** | `python test_performance_improvements.py` | 运行性能测试 |

### 测试文件位置

```
src/test/
├── unit/
│   ├── test_anti_cheating.py          # 防作弊测试
│   └── test_assessment_engine.py     # 评估引擎测试
├── integration/
│   ├── test_api_endpoints.py         # API 端点测试
│   └── test_ui_routes.py             # UI 路由测试
```

---

## 📚 文档链接 (Documentation)

### 项目文档

| 文档 | 位置 | 说明 |
|------|------|------|
| **快速测试指南** | `QUICK_TEST_GUIDE.md` | 快速开始测试指南 |
| **测试文档** | `TESTING.md` | 完整测试文档 |
| **测试套件总结** | `TEST_SUITE_SUMMARY.md` | 测试套件总结 |
| **性能测试报告** | `PERFORMANCE_TEST_REPORT.md` | 性能测试报告 |
| **README** | `README.md` | 项目说明 |
| **架构文档** | `ARCHITECTURE.md` | 系统架构 |
| **API 文档** | `API_DOCUMENTATION.md` | API 详细文档 |

---

## 🎯 常用测试流程链接

### 完整评估流程

1. **创建邀请码**
   - 页面: `http://127.0.0.1:8000/admin/invitations`
   - 或 API: `POST http://127.0.0.1:8000/api/v1/admin/invitation/create`

2. **用户注册**
   - 页面: `http://127.0.0.1:8000/register?code=XXXX`
   - 或 API: `POST http://127.0.0.1:8000/api/v1/auth/register`

3. **用户登录**
   - 页面: `http://127.0.0.1:8000/login`
   - 或 API: `POST http://127.0.0.1:8000/api/v1/auth/login`

4. **开始评估**
   - 页面: `http://127.0.0.1:8000/start-assessment`
   - 或 API: `POST http://127.0.0.1:8000/api/v1/assessment/create`

5. **答题**
   - 页面: `http://127.0.0.1:8000/question/1` (题目1-21)
   - 提交: `POST http://127.0.0.1:8000/submit`

6. **查看结果**
   - 页面: `http://127.0.0.1:8000/results`

### 题库加载流程（创建带 department 的邀请码前必须执行）

**重要**: 每次创建带 department（如 Laundry、Housekeeping）的 invitation link 前，必须先加载完整题库，否则 assessment 无法给出对应部门的题目。

1. **加载完整题库**
   - API: `POST http://127.0.0.1:8000/api/v1/admin/load-full-question-bank?admin_key=dev-admin-key-123`
   - 或 Swagger: `http://127.0.0.1:8000/docs` → 找到 `POST /api/v1/admin/load-full-question-bank`

2. **验证加载**
   - 健康检查: `http://127.0.0.1:8000/health`
   - 应显示: `{"status": "healthy", "questions_loaded": 1600}`

3. **数据流**
   - Admin 创建 invitation 时选择 department → 存入 InvitationCode
   - 用户用 invitation 注册 → User.department、Assessment.department 从 invitation 继承
   - start_assessment 时按 department 筛选题目 → question_order 存 21 题 ID
   - question_page 从 question_order 加载题目 → 显示对应部门题目

---

## 🔑 重要参数

### 默认配置

- **服务器地址**: `127.0.0.1:8000`
- **管理员密钥**: `dev-admin-key-123` (当前使用，来自 .env 文件)
- **备用密钥**: `admin123` (代码默认值，如果 .env 未设置)
- **数据库**: SQLite (默认)
- **会话超时**: 4小时

### 环境变量

创建 `.env` 文件设置:
```env
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite+aiosqlite:///./data/assessment.db
ADMIN_API_KEY=dev-admin-key-123
DEBUG=true
```

**注意**: 当前项目使用 `ADMIN_API_KEY=dev-admin-key-123`，请在生成邀请码时使用此密钥。

---

## 📝 测试检查清单

### 基础功能测试

- [ ] 服务器启动成功
- [ ] 健康检查通过: `http://127.0.0.1:8000/health`
- [ ] API 文档可访问: `http://127.0.0.1:8000/docs`
- [ ] 首页加载: `http://127.0.0.1:8000/`
- [ ] 注册页面: `http://127.0.0.1:8000/register`
- [ ] 登录页面: `http://127.0.0.1:8000/login`

### 管理功能测试

- [ ] 管理后台: `http://127.0.0.1:8000/admin`
- [ ] 邀请码管理: `http://127.0.0.1:8000/admin/invitations`
- [ ] 创建邀请码成功
- [ ] 题库加载: `POST /api/v1/admin/load-full-question-bank`
- [ ] 统计信息: `GET /api/v1/admin/stats`

### 评估流程测试

- [ ] 用户注册成功
- [ ] 用户登录成功
- [ ] 创建评估成功
- [ ] 开始评估成功
- [ ] 答题提交成功
- [ ] 结果页面显示正确

---

## 🚀 快速测试命令

```bash
# 启动服务器
python run_server.py

# 运行所有测试
python run_tests.py

# 运行单元测试
pytest src/test/unit/ -v

# 运行集成测试
pytest src/test/integration/ -v

# 查看测试覆盖率
pytest src/test/ --cov=src/main/python --cov-report=html
```

---

**最后更新**: 2025-01-25  
**服务器地址**: `http://127.0.0.1:8000`  
**文档版本**: 1.0

