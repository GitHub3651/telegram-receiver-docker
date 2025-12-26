# Telegram 接码平台 v2.0 升级方案：多用户 SaaS 架构

本方案旨在将现有的单用户工具升级为支持多用户注册、登录、数据隔离的商业级 SaaS 平台。

---

## 1. 核心目标

1.  **身份认证 (Authentication)**: 用户必须注册并登录才能使用系统。
2.  **数据隔离 (Authorization)**: 用户 A 只能看到自己添加的 Telegram 账号和验证码，无法看到用户 B 的数据。
3.  **用户管理**: 提供个人中心，支持修改密码、注销账号等功能。

---

## 2. 数据库架构变更 (Database Schema)

我们需要引入 `User` 实体，并重构现有的关系。

### 2.1 新增 `users` 表
用于存储用户的基本信息和认证凭据。

| 字段名 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| `id` | Integer | Primary Key | 用户唯一 ID |
| `email` | String | Unique, Not Null | 登录邮箱 (作为唯一标识符) |
| `password_hash` | String | Not Null | 加密后的密码 (Bcrypt) |
| `created_at` | DateTime | Default Now | 注册时间 |
| `is_active` | Boolean | Default True | 账号状态 (封禁控制) |

> **注册策略**: 使用邮箱作为唯一标识符，**无需邮箱验证码**（简化流程），但系统会在注册时检查邮箱是否已被占用（去重机制）。

### 2.2 修改 `accounts` 表
建立账号与用户的归属关系。

| 字段名 | 类型 | 变更说明 |
| :--- | :--- | :--- |
| `user_id` | Integer | **新增外键**，关联 `users.id` |
| `phone` | String | 保持不变 |
| `session_name` | String | 保持不变 |

> **注意**: `verification_codes` 表不需要修改结构。因为它通过 `phone` 字段与 `accounts` 表关联，而 `accounts` 表已经关联了 `user_id`。查询时通过级联关系即可确认权限。

---

## 3. 后端技术方案 (FastAPI)

### 3.1 认证机制 (JWT)
采用 **JSON Web Token (JWT)** 标准进行无状态认证。

1.  **登录流程**:
    *   用户提交邮箱/密码 -> 后端验证 -> 生成 JWT Token (包含 `user_id`, `email`, `exp`) -> 返回给前端。
2.  **请求流程**:
    *   前端在 HTTP Header 中携带 `Authorization: Bearer <token>`。
    *   后端中间件解析 Token，获取 `current_user` 对象。
    *   如果 Token 无效或过期，返回 `401 Unauthorized`。

### 3.2 API 接口规划

#### 新增认证模块 (`/api/auth`)
*   `POST /register`: 用户注册
    *   参数: `email`, `password`
    *   校验: 邮箱格式 + 邮箱去重检查
    *   无需邮箱验证码（简化注册流程）
*   `POST /login`: 用户登录
    *   参数: `email`, `password`
    *   返回: `access_token` (JWT)
*   `GET /me`: 获取当前用户信息 (需认证)
*   `PUT /me/password`: 修改密码 (需认证，需提供旧密码验证)
*   `DELETE /me`: 注销账号 (需认证，硬删除用户及关联数据)

#### 改造业务模块
所有现有接口都需要增加 `Depends(get_current_user)` 依赖，并修改查询逻辑。

*   `GET /api/accounts`:
    *   **旧逻辑**: `db.query(Account).all()`
    *   **新逻辑**: `db.query(Account).filter(Account.user_id == current_user.id).all()`
*   `POST /api/accounts/send-code`:
    *   发送前检查该手机号是否已被当前用户添加。
*   `GET /api/codes`:
    *   只返回属于当前用户账号的验证码。

### 3.3 Session 文件隔离
为了防止文件名冲突（不同用户添加相同手机号，虽然业务上可能限制，但物理上需隔离），Session 文件名格式将调整为：
*   旧: `sessions/+8613800000000.session`
*   新: `sessions/user_{user_id}_+8613800000000.session`

---

## 4. 前端交互方案

### 4.1 页面结构拆分
*   **`login.html` (新)**:
    *   包含“登录”和“注册”两个选项卡。
    *   设计简洁大气的商业风格卡片。
*   **`index.html` (改造)**:
    *   **顶部导航栏**: 增加“用户头像”下拉菜单（个人设置、退出登录）。
    *   **鉴权逻辑**: 页面加载时检查 `localStorage` 是否有 Token。如果没有，自动跳转到 `login.html`。

### 4.2 状态管理
*   **Token 存储**: 使用 `localStorage.setItem('token', '...')` 持久化存储。
*   **退出登录**: 清除 `localStorage` 并跳转回登录页。
*   **全局拦截器**: 封装 `fetch` 方法，自动为所有请求添加 `Authorization` 头，并统一处理 401 错误。

---

## 5. 完整实施路线图 (Roadmap)

### 第一阶段：后端基础建设 (Backend Foundation)

#### 5.1.1 修改依赖文件
**文件**: `backend/requirements.txt`

新增以下依赖：
```
python-jose[cryptography]  # JWT Token 生成和验证
passlib[bcrypt]            # 密码加密
python-multipart           # 支持表单数据解析
```

#### 5.1.2 创建用户模型
**文件**: `backend/database.py`

在现有的 `Account` 和 `VerificationCode` 模型之外，新增：
```python
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # 关系
    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
```

修改 `Account` 模型，新增外键：
```python
class Account(Base):
    __tablename__ = 'accounts'
    
    # ... 现有字段 ...
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # 新增
    
    # 关系
    user = relationship("User", back_populates="accounts")  # 新增
```

#### 5.1.3 创建认证工具库
**新建文件**: `backend/auth.py`

包含以下功能：
- `get_password_hash(password: str) -> str`: 使用 bcrypt 加密密码
- `verify_password(plain_password: str, hashed_password: str) -> bool`: 验证密码
- `create_access_token(data: dict) -> str`: 生成 JWT Token（有效期 7 天）
- `get_current_user(token: str, db: Session) -> User`: 从 Token 解析用户
- `validate_email(email: str) -> bool`: 邮箱格式校验

#### 5.1.4 实现认证 API
**文件**: `backend/main.py`

新增以下路由：

```python
# 用户注册
@app.post("/api/auth/register")
async def register(email: str, password: str, db: Session = Depends(get_db)):
    # 1. 校验邮箱格式
    # 2. 检查邮箱是否已存在
    # 3. 加密密码并创建用户
    # 4. 返回成功信息

# 用户登录
@app.post("/api/auth/login")
async def login(email: str, password: str, db: Session = Depends(get_db)):
    # 1. 查询用户
    # 2. 验证密码
    # 3. 生成并返回 access_token

# 获取当前用户信息
@app.get("/api/auth/me")
async def get_me(current_user: User = Depends(get_current_user)):
    # 返回用户的 id, email, created_at

# 修改密码
@app.put("/api/auth/me/password")
async def change_password(
    old_password: str, 
    new_password: str, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. 验证旧密码
    # 2. 更新为新密码
    # 3. 返回成功信息

# 注销账号
@app.delete("/api/auth/me")
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. 删除用户的所有 Session 文件
    # 2. 删除数据库中的用户记录（级联删除关联的 accounts 和 codes）
    # 3. 返回成功信息
```

---

### 第二阶段：业务逻辑迁移 (Business Logic Migration)

#### 5.2.1 改造账号管理 API
**文件**: `backend/main.py`

所有 `/api/accounts` 相关接口都需要：
1. 增加 `current_user: User = Depends(get_current_user)` 参数。
2. 修改数据库查询，添加 `user_id` 过滤。

**示例**：
```python
# 获取账号列表
@app.get("/api/accounts")
async def get_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 旧: accounts = db.query(Account).all()
    # 新: accounts = db.query(Account).filter(Account.user_id == current_user.id).all()

# 发送验证码
@app.post("/api/accounts/send-code")
async def send_code(
    phone: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 检查该手机号是否已被当前用户添加
    existing = db.query(Account).filter(
        Account.user_id == current_user.id,
        Account.phone == phone
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该手机号已添加")
    # ... 其余逻辑不变

# 验证登录（创建账号）
@app.post("/api/accounts/verify")
async def verify_account(
    phone: str, code: str, password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 创建账号时，关联 user_id
    new_account = Account(
        phone=phone,
        session_name=f"user_{current_user.id}_{phone}",  # 新的命名格式
        user_id=current_user.id  # 关联当前用户
    )
    # ... 其余逻辑

# 删除账号
@app.delete("/api/accounts/{account_id}")
async def delete_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 确保只能删除属于自己的账号
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == current_user.id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在或无权限")
    # ... 删除逻辑
```

#### 5.2.2 改造验证码 API
**文件**: `backend/main.py`

```python
# 获取验证码列表
@app.get("/api/codes")
async def get_codes(
    hours: int = 24,
    limit: int = 1,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 通过 JOIN 查询，只返回属于当前用户账号的验证码
    codes = db.query(VerificationCode).join(Account).filter(
        Account.user_id == current_user.id,
        VerificationCode.received_at >= datetime.utcnow() - timedelta(hours=hours)
    ).order_by(VerificationCode.received_at.desc()).limit(limit).all()
    return codes

# 检查验证码
@app.post("/api/accounts/check/{phone}")
async def check_codes(
    phone: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 确保该手机号属于当前用户
    account = db.query(Account).filter(
        Account.phone == phone,
        Account.user_id == current_user.id
    ).first()
    if not account:
        raise HTTPException(status_code=403, detail="无权限")
    # ... 其余逻辑

# 清空验证码
@app.delete("/api/codes")
async def clear_codes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 只清空属于当前用户的验证码
    db.query(VerificationCode).filter(
        VerificationCode.phone.in_(
            db.query(Account.phone).filter(Account.user_id == current_user.id)
        )
    ).delete(synchronize_session=False)
    db.commit()
```

#### 5.2.3 修改 Telegram 客户端
**文件**: `backend/receiver.py`

修改 Session 文件命名和加载逻辑：

```python
async def check_codes_for_account(account: Account, db: Session):
    # 旧: session_path = f"sessions/{account.session_name}.session"
    # 新: session_path = f"sessions/user_{account.user_id}_{account.phone}.session"
    
    client = TelegramClient(
        session_path,
        API_ID,
        API_HASH
    )
    # ... 其余逻辑不变
```

#### 5.2.4 修改定时任务调度器
**文件**: `backend/scheduler.py`

确保定时任务在扫描账号时，能够正确处理所有用户的账号（不需要特别修改，因为它会遍历 `accounts` 表的所有记录）。

---

### 第三阶段：前端重构 (Frontend Refactoring)

#### 5.3.1 创建登录/注册页面
**新建文件**: `frontend/dist/login.html`

**页面结构**：
- 左右分栏布局，左侧展示产品介绍，右侧是登录/注册表单。
- 使用 Tab 切换"登录"和"注册"。
- 注册表单：邮箱输入框 + 密码输入框 + 确认密码输入框。
- 登录表单：邮箱输入框 + 密码输入框。
- 提交按钮：显示加载状态（"登录中..."/"注册中..."）。

**核心逻辑**：
```javascript
// 注册
async function register() {
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;
    
    const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    });
    
    if (response.ok) {
        alert('注册成功，请登录');
        switchTab('login');
    } else {
        const error = await response.json();
        alert(error.detail);
    }
}

// 登录
async function login() {
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    
    const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    });
    
    if (response.ok) {
        const data = await response.json();
        localStorage.setItem('token', data.access_token);
        window.location.href = '/';  // 跳转到主页
    } else {
        alert('登录失败：邮箱或密码错误');
    }
}
```

#### 5.3.2 改造主页面
**文件**: `frontend/dist/index.html`

**1. 增加鉴权检查**（页面加载时执行）：
```javascript
async function checkAuth() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/login.html';
        return;
    }
    
    // 验证 Token 是否有效
    const response = await fetch('/api/auth/me', {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    
    if (!response.ok) {
        localStorage.removeItem('token');
        window.location.href = '/login.html';
        return;
    }
    
    const user = await response.json();
    displayUserInfo(user);
}
```

**2. 封装全局请求拦截器**：
```javascript
// 重写 fetch，自动添加 Authorization 头
const originalFetch = window.fetch;
window.fetch = function(url, options = {}) {
    const token = localStorage.getItem('token');
    if (token) {
        options.headers = {
            ...options.headers,
            'Authorization': `Bearer ${token}`
        };
    }
    
    return originalFetch(url, options).then(response => {
        if (response.status === 401) {
            localStorage.removeItem('token');
            window.location.href = '/login.html';
        }
        return response;
    });
};
```

**3. 增加用户菜单**（右上角）：
```html
<div class="user-menu">
    <img id="user-avatar" src="default-avatar.png" />
    <span id="user-email">user@example.com</span>
    <div class="dropdown">
        <a href="#" onclick="openSettings()">个人设置</a>
        <a href="#" onclick="logout()">退出登录</a>
    </div>
</div>
```

**4. 实现退出登录**：
```javascript
function logout() {
    localStorage.removeItem('token');
    window.location.href = '/login.html';
}
```

**5. 实现修改密码弹窗**：
在现有的模态框基础上，增加一个"修改密码"模态框，调用 `PUT /api/auth/me/password`。

---

### 第四阶段：数据迁移与部署 (Data Migration & Deployment)

#### 5.4.1 清空旧数据
**操作步骤**：

1. **停止所有服务**：
```bash
docker-compose down
```

2. **删除 Session 文件**：
```bash
rm -rf sessions/*.session
```

3. **重置数据库**：
```bash
# 方式1：删除 Docker 卷（会丢失所有数据）
docker volume rm telegram-receiver-docker_postgres_data

# 方式2：手动删除表（保留数据库结构）
docker-compose up -d postgres
docker-compose exec postgres psql -U telegram_user -d telegram_codes -c "DROP TABLE IF EXISTS verification_codes, accounts, users CASCADE;"
```

#### 5.4.2 创建新表结构
**文件**: `backend/init_db.py`（已有，无需修改，它会自动根据 models 创建表）

重新启动后端，数据库会自动创建新表：
```bash
docker-compose up -d --build backend
```

#### 5.4.3 更新 Nginx 配置
**文件**: `nginx/nginx.conf`

确保新增的 `login.html` 能被正确路由：
```nginx
location / {
    root /usr/share/nginx/html;
    try_files $uri $uri/ /index.html;
}

location /login.html {
    root /usr/share/nginx/html;
}
```

#### 5.4.4 测试流程
1. 访问 `http://your-server-ip`，应自动跳转到 `/login.html`。
2. 注册一个新账号（如 `test@example.com`）。
3. 登录成功后，跳转到主页，能看到用户邮箱显示在右上角。
4. 添加一个 Telegram 账号，检查是否正常工作。
5. 登出后重新登录，确认数据隔离（看不到其他用户的账号）。

---

### 第五阶段：文档更新 (Documentation Update)

#### 5.5.1 更新 README.md
需要更新以下章节：
- **核心功能**：增加"多用户支持"、"数据隔离"。
- **快速开始**：增加"首次访问需要注册账号"。
- **API 文档**：增加 `/api/auth` 模块的说明。
- **常见问题**：增加"忘记密码怎么办"（目前暂不支持找回，需后续实现）。

#### 5.5.2 更新 BACKEND_MANUAL.md
增加用户管理相关的说明。

---

## 完成标志

当以下所有功能测试通过时，v2.0 即正式完成：

- ✅ 用户可以通过邮箱注册并登录。
- ✅ 用户只能看到自己的 Telegram 账号和验证码。
- ✅ 用户可以修改密码和注销账号。
- ✅ 未登录状态下无法访问主页（自动跳转登录页）。
- ✅ Token 过期后自动重定向到登录页。

---

## 6. 确认的实施策略

基于讨论，以下策略已确认：

1.  **注册模式**: 使用**邮箱注册**，格式校验 + 去重检查，**无需邮箱验证码**（简化流程）。
2.  **旧数据处理**: **清空所有旧数据**（数据库表 + Session 文件）。
3.  **开放性**: 采用**开放注册**模式（任何人都可以通过邮箱注册）。

---

## 7. 技术细节补充

### 7.1 邮箱格式校验
使用正则表达式验证邮箱格式：
```python
import re
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
```

### 7.2 Token 有效期
*   Access Token: 7 天（`exp = now + 7 days`）。
*   前端无需 Refresh Token（简化实现）。

---

准备就绪，可以开始实施。建议按照阶段顺序逐步推进，每完成一个阶段后进行测试验证。
