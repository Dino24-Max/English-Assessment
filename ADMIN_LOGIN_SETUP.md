# Admin 登录系统使用指南

## 功能概述

已实现统一登录界面的 Admin 登录功能，通过"🔐 Admin Login"复选框区分管理员和普通用户登录。

---

## Admin 账户信息

### 默认 Admin 账户

| 项目 | 值 |
|------|------|
| **邮箱** | `admin@carnival.com` |
| **密码** | `admin123` |
| **角色** | Administrator |

---

## 登录步骤

### Admin 登录流程

1. 访问 `http://127.0.0.1:8000/login`
2. 输入邮箱：`admin@carnival.com`
3. 输入密码：`admin123`
4. **勾选** "🔐 Admin Login" 复选框
5. 点击 "Login" 按钮
6. 自动跳转到 `/admin` 管理后台

### 普通用户登录流程

1. 访问 `http://127.0.0.1:8000/login`
2. 输入用户邮箱和密码
3. **不勾选** "Admin Login" 复选框
4. 点击 "Login" 按钮
5. 自动跳转到 `/select-operation` 选择部门页面

---

## 功能特性

### 1. 统一登录界面 ✅
- 同一个登录页面服务于管理员和普通用户
- 通过复选框区分登录类型
- 无需维护两套登录系统

### 2. 智能重定向 ✅
- Admin 登录 → `/admin` 管理后台
- 普通用户登录 → `/select-operation` 选择部门

### 3. 权限验证 ✅
- 勾选"Admin Login"但不是 admin → 拒绝登录，显示错误
- 未勾选"Admin Login"，admin 可以普通用户身份登录
- 所有 `/admin/*` 路由受保护，需要 admin 权限

### 4. Session 管理 ✅
- `session["is_admin"]` 标记 admin 身份
- `localStorage.is_admin` 前端存储
- 所有 admin 页面检查 session 权限

---

## 路由保护

### 受保护的 Admin 路由

| 路由 | 说明 | 保护状态 |
|------|------|----------|
| `/admin` | Admin Dashboard | ✅ 需要 admin 权限 |
| `/admin/invitations` | 邀请码管理 | ✅ 需要 admin 权限 |
| `/admin/scoreboard` | 用户排行榜 | ✅ 需要 admin 权限 |

### 保护机制

未登录或非 admin 用户访问 admin 页面：
- 自动重定向到 `/login` 登录页面
- 提示需要 admin 权限

---

## 创建新的 Admin 账户

### 方法 1: 使用快速创建脚本（推荐）

```bash
python scripts/quick_create_admin.py
```

自动创建 `admin@carnival.com / admin123` 账户

### 方法 2: 使用交互式脚本

```bash
python scripts/create_admin_user.py
```

按提示输入：
- First Name
- Last Name
- Email
- Password
- Nationality (可选)

### 方法 3: 更新现有用户为 Admin

运行 `scripts/quick_create_admin.py`，如果邮箱已存在，会提示是否更新为 admin。

---

## 数据库结构

### User 表新增字段

```sql
is_admin BOOLEAN DEFAULT 0
```

- `0` (False): 普通用户
- `1` (True): 管理员

### 索引

```sql
CREATE INDEX ix_users_admin ON users (is_admin, is_active)
```

优化 admin 用户查询性能

---

## 测试验证

### 测试 1: Admin 登录

**步骤**:
1. 访问 `/login`
2. 输入 `admin@carnival.com` / `admin123`
3. 勾选 "🔐 Admin Login"
4. 点击 Login

**预期结果**:
- ✅ 登录成功消息："Admin login successful! Redirecting to admin panel..."
- ✅ 自动跳转到 `/admin`
- ✅ 显示 Admin Dashboard
- ✅ localStorage.is_admin = "true"

### 测试 2: 普通用户尝试 Admin 登录

**步骤**:
1. 使用普通用户账户（如 `testuser999@test.com`）
2. 勾选 "Admin Login"
3. 尝试登录

**预期结果**:
- ❌ 登录失败
- ❌ 错误消息："You do not have admin privileges"

### 测试 3: 未授权访问 Admin 页面

**步骤**:
1. 退出登录
2. 直接访问 `http://127.0.0.1:8000/admin`

**预期结果**:
- ✅ 自动重定向到 `/login`

### 测试 4: Admin 用户普通登录

**步骤**:
1. 使用 `admin@carnival.com` / `admin123`
2. **不勾选** "Admin Login"
3. 登录

**预期结果**:
- ✅ 登录成功
- ✅ 跳转到 `/select-operation`（可以做评估）

---

## 安全特性

1. **Session 验证**: 所有 admin 路由检查 `session["is_admin"]`
2. **双重验证**: Admin API 端点仍需要 `admin_key` 参数
3. **角色分离**: Admin 可以以普通用户身份使用系统
4. **密码加密**: 使用 bcrypt 加密存储

---

## 常见问题

### Q: 忘记 Admin 密码怎么办？
A: 运行 `python scripts/quick_create_admin.py`，脚本会更新密码为 `admin123`

### Q: 如何创建多个 Admin 账户？
A: 使用 `python scripts/create_admin_user.py` 交互式创建

### Q: Admin Key 和 Admin Login 有什么区别？
A: 
- **Admin Key** (`dev-admin-key-123`): 用于 API 调用认证
- **Admin Login**: 用于网页界面登录认证

### Q: 如何撤销某个用户的 admin 权限？
A: 直接修改数据库：
```bash
# 使用 Python
python -c "
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import sys
sys.path.insert(0, 'src/main/python')
from core.database import engine
from models.assessment import User

async def revoke_admin(email):
    async with AsyncSession(engine) as db:
        await db.execute(
            update(User).where(User.email == email).values(is_admin=False)
        )
        await db.commit()
        print(f'Revoked admin from {email}')

asyncio.run(revoke_admin('user@example.com'))
"
```

---

## 已完成功能

- ✅ User 模型添加 `is_admin` 字段
- ✅ 数据库迁移添加列和索引
- ✅ 登录页面添加"Admin Login"复选框
- ✅ 登录 API 验证 admin 角色
- ✅ 登录后智能重定向（admin → /admin, 用户 → /select-operation）
- ✅ 所有 admin 路由添加权限保护
- ✅ 创建 admin 账户脚本
- ✅ 创建默认 admin 账户

---

**Admin 登录系统已完全部署并测试通过！** 🎉

