# 海南大学校园资源置换与技能互助平台

这是一个面向海南大学学生的前后端分离软件工程课程项目。平台支持资源发布、技能互助、交易协议、双向完成确认、信用评价和管理员纠纷处理。

## 当前状态

MVP 已进入可运行状态，包含：

- 学生手机号短信注册与短信登录（不设置学生密码）、管理员后台账号密码登录和 JWT 鉴权
- 一次性挑战码、私密材料上传和管理员人工学生认证
- 可选邮箱验证码绑定；邮箱只证明邮箱控制权，不作为学生身份证明
- 可显式开启的课程演示认证和模拟付款，界面不会声称连接学校或真实支付渠道
- 资源与技能发布、图片上传、分类、搜索和公开列表
- 交易请求、双方协议确认、双方完成确认
- 交易内异步消息、完成后评价和信用事件
- 收藏接口、举报提交、管理员认证审核和举报处理
- 学号 AES-GCM 加密存储和接口掩码
- Alembic 初始迁移、Docker Compose 和 Nginx 反向代理

## 文档入口

- `PRD.md`：产品范围、角色、规则和验收标准
- `APP_FLOW.md`：页面、路由和用户流程
- `TECH_STACK.md`：锁定的技术栈和工程约束
- `FRONTEND_GUIDELINES.md`：界面设计系统和交互规则
- `BACKEND_STRUCTURE.md`：数据模型、接口和后端结构
- `IMPLEMENTATION_PLAN.md`：七阶段实施计划和两天排期
- `REMOTE_HANDOFF.md`：远程前端美化、服务器、域名和上线交接
- `CLAUDE.md`：AI 开发规则
- `progress.txt`：当前进度和已知限制
- `lessons.md`：项目经验和防复发规则

## 技术方向

- 前端：Vue 3、JavaScript、Vite、Axios
- 后端：Python 3.12、FastAPI、SQLAlchemy、Alembic
- 数据库：MySQL 8
- 部署：Docker Compose、Nginx

## 核心边界

平台不托管资金，不保存微信支付密码或银行卡信息。双方在平台外完成付款，平台只记录交易协议、交付状态和双方确认结果。课程演示模式可以记录“模拟付款”，但不会发起扣款，也不会替代双方完成确认。真实校园身份接口、真实支付、实时聊天和 AI 推荐列为后续扩展。

## 本地运行

当前开发环境默认使用 SQLite，便于无需安装 MySQL 直接启动。生产部署由 Compose 切换为 MySQL。

### 后端

```powershell
python -m pip install -r backend/requirements.txt
$env:PYTHONPATH='backend'
Set-Location backend
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

接口文档：`http://127.0.0.1:8000/docs`

### 前端

```powershell
Set-Location frontend
npm install
npm run dev -- --host 127.0.0.1
```

访问：`http://127.0.0.1:5173`

开发环境演示管理员：`admin / Admin123!`。该默认密码只在开发环境启用，生产环境必须通过环境变量设置。

开发环境短信服务会在接口响应中提供测试验证码；生产环境不会返回验证码，必须先配置合规短信服务商。

开发环境默认启用课程演示认证与模拟付款。公开部署默认关闭；课程展示站如需启用，必须显式设置 `DEMO_FEATURES_ENABLED=true`，并保留页面上的演示标识。

邮箱在开发环境使用控制台验证码。向任意正常邮箱实际投递验证码时，将 `EMAIL_PROVIDER` 设置为 `smtp`，并配置邮箱服务商提供的 SMTP 主机、端口、账号和应用专用密码。

## 测试

```powershell
$env:PYTHONPATH='backend'
python -m pytest backend/tests -q -p no:cacheprovider
Set-Location frontend
npm run build
```

## Docker 部署

1. 根据根目录 `.env.example` 创建 `.env`，设置强密码和至少 32 位随机 `SECRET_KEY`。
2. 运行 `docker compose up --build -d`。
3. 默认访问 `http://localhost:8080`。

生产配置缺少安全 `SECRET_KEY` 时，后端会拒绝启动。

## 让其他电脑访问

### 同一局域网临时演示

后端使用 `--host 0.0.0.0`，前端使用 `npm run dev -- --host 0.0.0.0` 启动，并在 Windows 防火墙仅放行需要的端口。其他电脑随后访问：

```text
http://你的局域网IP:5173
```

局域网地址只能被同一网络中的设备访问，不能被互联网搜索引擎收录。

### 公网部署

1. 准备具有公网 IP 的云服务器，并安装 Docker 与 Docker Compose。
2. 将项目部署到服务器，配置强 `SECRET_KEY`、数据库密码、管理员密码和 SMTP。
3. 使用 `docker compose up --build -d` 启动，安全组和防火墙开放 80/443。
4. 购买域名，把 DNS 的 `A` 记录指向服务器公网 IP。
5. 使用 Nginx 和 Let's Encrypt 配置 HTTPS，并将 `FRONTEND_ORIGINS` 设置为正式域名。
6. 中国大陆服务器对公网提供网站通常需要完成 ICP 备案；课程临时展示可以根据学校要求选择校内服务器或合规的境外节点。

### 被搜索引擎发现

项目已经提供页面标题、描述和 `robots.txt`。获得正式域名后，还需要：

1. 把域名写入站点地图 `sitemap.xml`，并在 `robots.txt` 中声明站点地图地址。
2. 分别在百度搜索资源平台、Bing Webmaster Tools 或 Google Search Console 验证域名并提交站点地图。
3. 保证公开列表和详情无需登录、HTTPS 可访问、页面长期稳定返回 `200`。
4. Vue 单页应用的动态详情对搜索引擎不如服务端渲染友好；课程项目可以先保证首页收录，后续再做预渲染或 SSR。

公网可访问不等于立即能搜到。新域名被抓取通常需要数天到数周，`localhost`、`127.0.0.1` 和局域网 IP 永远不会被公网搜索引擎收录。
