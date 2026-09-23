# TECH_STACK

## 1. 版本基线

以下版本是 MVP 的目标基线。安装阶段如遇到兼容性问题，只允许进行补丁版本调整，并同步更新本文档和 `progress.txt`。

### 前端

- Node.js 20 LTS
- Vue 3.5.13
- TypeScript 5.7.2
- Vite 6.0.7
- Vue Router 4.5.0
- Pinia 2.3.0
- Element Plus 2.9.1
- Axios 1.7.9

### 后端

- Python 3.12
- FastAPI 0.115.6
- Uvicorn 0.34.0
- Pydantic 2.10.5
- SQLAlchemy 2.0.36
- Alembic 1.14.1
- PyMySQL 1.1.1
- PyJWT 2.10.1
- pwdlib 0.2.1
- python-multipart 0.0.20
- cryptography 50.0.1

### 测试和运维

- Pytest 8.3.4
- HTTPX 0.28.1
- Docker Compose v2
- Nginx 1.27.x
- MySQL 8.0.x
- Git

## 2. 架构约束

- 前后端通过 JSON REST API 通信。
- 前端不直接访问数据库。
- 后端使用分层结构：API、Service、Repository、Model、Schema。
- 业务规则放在 Service 层，不写在路由函数中。
- 数据校验使用 Pydantic；数据库约束使用 SQLAlchemy/Alembic。
- 所有分页列表必须有明确的默认排序和最大页大小。
- 所有写操作必须进行身份认证、权限检查和输入校验。
- 不增加本文档未列出的依赖，除非先说明原因并更新版本基线。

## 3. 认证与安全

- 使用短期 JWT access token。
- 学生使用短信验证码注册登录，不设置密码；管理员密码使用 Argon2 哈希，禁止明文和可逆保存。
- 生产环境的密钥只放在 `.env` 或部署平台密钥配置中。
- 学号、认证材料路径等敏感字段使用应用层 AES-GCM 加密或受控访问。
- 手机号和邮箱使用 HMAC 盲索引查询并加密保存；邮箱验证码通过可替换的控制台/SMTP 提供者发送。
- 课程演示认证和模拟付款由 `DEMO_FEATURES_ENABLED` 显式控制，公开生产部署默认关闭。
- 生产环境所有外部访问使用 HTTPS。
- 后端对资源所有者、交易参与者和管理员做细粒度授权。

## 4. 文件策略

- 允许的图片类型：JPEG、PNG、WebP。
- 单文件大小上限：5 MB。
- 单次发布图片数量上限：6 张。
- 文件名使用服务端生成的随机标识，不使用用户原始文件名作为路径。
- 公共列表只返回经过处理的缩略图 URL。
- 认证材料和收款码使用授权下载接口，不暴露静态公开路径。

## 5. 聊天策略

MVP 使用交易范围内的 REST 轮询，不使用 WebSocket、Redis 或消息队列。消息接口必须支持分页、增量查询、未读数和参与者授权。未来如果需要实时聊天，再引入 WebSocket、Redis Pub/Sub 和连接心跳。

## 6. 部署策略

Docker Compose 至少包含：

- Nginx：静态资源、反向代理和 HTTPS 入口。
- Frontend：构建后的 Vue 静态文件。
- Backend：FastAPI/Uvicorn 服务。
- MySQL：持久化数据库。

文件上传目录和数据库目录使用持久化卷。`.env` 不提交到 Git，只提交 `.env.example`。
