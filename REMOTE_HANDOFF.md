# 远程开发与部署交接

本文供接手前端美化、服务器部署、域名和 HTTPS 配置的开发者使用。开始工作前，请先阅读 `README.md`、`PROJECT_CONTEXT.md`、`PRD.md` 和 `APP_FLOW.md`。

## 1. 当前交付范围

- 前端：Vue 3 + Vite + Axios，当前以桌面端为主。
- 后端：FastAPI + SQLAlchemy + Alembic。
- 本地开发数据库：SQLite。
- 生产部署数据库：Docker Compose 中的 MySQL 8。
- 生产入口：Nginx 托管前端，并把 `/api/` 和 `/uploads/` 代理到后端。
- API 文档：后端启动后访问 `/docs`。

当前核心业务已可运行。远程阶段的主要工作是前端视觉优化、公网服务器部署、域名解析、HTTPS、真实 SMTP 配置和上线回归，不需要重写业务模型。

## 2. 本地启动

环境要求：Python 3.12、Node.js 20 和 npm。

后端（PowerShell）：

```powershell
python -m pip install -r backend/requirements.txt
$env:PYTHONPATH='backend'
Set-Location backend
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

前端（另开一个终端）：

```powershell
Set-Location frontend
npm install
npm run dev -- --host 127.0.0.1
```

访问 `http://127.0.0.1:5173`。Vite 会把 `/api` 和 `/uploads` 代理到 `http://127.0.0.1:8000`。

## 3. 提交中不包含的数据

以下内容被 `.gitignore` 排除，不会上传 GitHub：

- SQLite 数据库及本地演示账号。
- `backend/.env` 和任何真实密钥。
- 上传的公开图片与私密认证材料。
- `frontend/node_modules` 和生产构建产物。

接手者首次启动时会得到空数据库。请通过界面重新创建测试账号和测试数据，不要把真实学生证、学号、手机号或其他个人信息提交到仓库。

## 4. 环境变量

本地后端配置参考 `backend/.env.example`。Docker 部署配置参考根目录 `.env.example`，在服务器上创建 `.env`，不得提交该文件。

生产环境至少需要设置：

```dotenv
SECRET_KEY=至少32位的随机字符串
MYSQL_PASSWORD=强数据库密码
MYSQL_ROOT_PASSWORD=另一个强密码
ADMIN_USERNAME=自定义管理员账号
ADMIN_PASSWORD=强管理员密码
FRONTEND_ORIGINS=https://你的域名
DEMO_FEATURES_ENABLED=false
EMAIL_PROVIDER=smtp
SMTP_HOST=邮件服务商SMTP地址
SMTP_PORT=587
SMTP_USERNAME=发信账号
SMTP_PASSWORD=应用专用密码
SMTP_FROM=发信地址
SMTP_SECURITY=starttls
```

上线前不得沿用示例密码。邮箱验证码只证明用户控制该邮箱，不代表学生身份。

真实 SMTP 投递已经实现，但短信服务目前只有开发用控制台提供者和供应商接入边界，尚未绑定任何真实短信厂商。生产模式会主动拒绝控制台短信，因此正式开放手机号注册前，必须在 `backend/app/services/sms.py` 接入合规短信供应商，并补齐发送失败、限流和回归测试；不得在公网返回 `debug_code`。

## 5. 服务器、域名与 HTTPS

推荐使用一台已安装 Docker 与 Docker Compose 的 Linux 服务器：

1. 拉取仓库，在项目根目录创建生产 `.env`。
2. 执行 `docker compose up --build -d`。
3. 确认首页、`/api/v1` 请求、图片上传和刷新前端路由均正常。
4. 将域名的 DNS `A` 记录指向服务器公网 IP。
5. 在云服务器安全组和系统防火墙中仅开放必要端口，公网提供 80/443。
6. 在现有 Web 入口前配置 HTTPS，可使用宿主机 Nginx/Caddy 和 Let's Encrypt。
7. 将 `FRONTEND_ORIGINS` 改为正式 HTTPS 域名后重新部署。
8. 配置数据库与上传卷备份，并验证恢复流程。

当前 `docker-compose.yml` 暴露的默认站点端口是 `8080`。如果宿主机反向代理直接转发到该端口，不要把 MySQL 或后端 8000 端口暴露到公网。

中国大陆服务器公开提供网站通常需要 ICP 备案。域名可访问与被搜索引擎收录是两件事；正式域名确定后还需要更新 `robots.txt`、增加 `sitemap.xml`，并在相应搜索资源平台提交。

## 6. 前端美化边界

前端目前主要集中在：

- `frontend/src/App.vue`
- `frontend/src/style.css`
- `frontend/src/api.js`

可以调整布局、色彩、字体、组件拆分、空状态和桌面端交互，但不要因视觉改造删除或改写以下业务状态：

- 资源置换与技能互助双轨入口。
- 发布者接受后，发起者仍需确认，协议才达成。
- 交付后双方分别确认；只有双方都确认，交易才进入 `completed`。
- 模拟付款与交易主状态分离，不能把它显示为真实扣款、担保交易或平台已收款。
- 平台不托管资金，不验证线下付款真伪。
- 手机号和邮箱只证明联系方式控制权，不是学生身份证明。
- 学生认证只能显示为“平台人工认证”或明确标注的“课程演示认证”，不得声称已经接入海南大学或学信网。
- 私密认证材料不得改成公开静态文件访问。

如需调整接口字段或交易状态，必须同步修改后端、Alembic 迁移、前端和自动化测试。

## 7. 演示功能

`DEMO_FEATURES_ENABLED=true` 会开放课程演示认证和模拟付款。它们只适合课堂展示，并已在界面中明确标注：

- 演示认证不连接海南大学、学信网或其他官方身份系统。
- 模拟付款不连接微信、支付宝或银行，不产生扣款。
- 模拟付款不会替代协议确认和双方完成确认。

普通公开部署应保持 `DEMO_FEATURES_ENABLED=false`。若课程展示站必须开启，也不能移除相关演示说明。

## 8. 上线前验证

代码级检查：

```powershell
$env:PYTHONPATH='backend'
python -m pytest backend/tests -q -p no:cacheprovider
Set-Location frontend
npm ci
npm run build
```

上线后至少人工回归：手机号注册/登录、可选邮箱绑定、人工认证材料权限、发布资源和技能、搜索筛选、收藏、发起交易、双方协议确认、双方完成确认、评价、举报及管理员处理。

同时检查：

- 未登录用户可以浏览公开列表和详情。
- 管理员不能进入学生发布和交易流程。
- 同一发布不能同时存在多笔有效交易。
- 认证材料不能通过公开 URL 直接访问。
- 生产环境不会在接口响应或日志中暴露短信/邮箱验证码。
- HTTPS 页面没有混合内容，刷新任意前端路由不会返回 404。

## 9. 已知限制

- 尚未接入海南大学统一身份认证或学信网。
- 尚未接入真实支付渠道，平台不负责资金结算。
- 尚未接入真实短信供应商，生产模式下不能使用开发控制台验证码。
- 站内消息是 REST 轮询，不是 WebSocket 实时通信。
- Docker Compose 配置尚需在实际服务器环境完成一次完整验证。
- 当前优先保证桌面端，移动端适配不是本阶段交付重点。
