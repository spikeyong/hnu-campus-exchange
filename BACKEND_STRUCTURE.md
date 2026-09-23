# BACKEND_STRUCTURE

## 1. 后端目录结构

```text
backend/
├── app/
│   ├── main.py
│   ├── core/              # 配置、JWT、密码和安全工具
│   ├── db/                # engine、session、Base、迁移辅助
│   ├── models/            # SQLAlchemy 模型
│   ├── schemas/           # Pydantic 请求和响应模型
│   ├── repositories/      # 数据访问
│   ├── services/          # 业务规则和事务编排
│   ├── api/
│   │   └── v1/            # REST 路由
│   └── workers/           # 预留异步任务，不在 MVP 启用
├── alembic/
├── tests/
├── requirements.txt
├── .env.example
└── Dockerfile
```

## 2. 数据模型

### `users`

- `id`：主键
- `username`：仅管理员使用的后台账号，唯一
- `phone_hash`：手机号 HMAC 盲索引，唯一
- `phone_ciphertext`、`phone_last4`、`phone_verified_at`：加密手机号、展示尾号和号码验证时间
- `email_hash`、`email_ciphertext`、`email_verified_at`：可选邮箱绑定与验证时间，邮箱不用于学生身份认证
- `password_hash`：管理员密码使用 Argon2 哈希；学生仅短信登录，保留不可用随机哈希以兼容当前非空字段
- `name`：姓名，必要时加密
- `student_no`：AES-GCM 加密学号
- `student_no_hash`：标准化学号的 HMAC 盲索引，唯一
- `college`、`grade`：学院和年级
- `role`：`student` 或 `admin`
- `verification_status`：`unverified`、`pending`、`verified`、`rejected`
- `verification_method`：`none`、`manual` 或 `demo`，防止把课程演示认证描述为人工或官方认证
- `credit_score`：计算缓存，来源为信用事件
- `status`：`active`、`restricted`、`disabled`
- `created_at`、`updated_at`

### `student_verifications`

- `id`、`user_id`
- `challenge_code`、`expires_at`：一次性挑战码及失效时间
- `evidence_storage_key`：私有认证材料的受控存储引用
- `status`：`pending`、`approved`、`rejected`
- `reviewer_id`、`review_note`
- `created_at`、`reviewed_at`

### `categories`

- `id`
- `name`
- `listing_type`：`resource`、`skill` 或 `both`
- `is_active`
- `sort_order`

### `listings`

- `id`、`owner_id`、`category_id`
- `type`：`resource` 或 `skill`
- `title`、`description`
- `price`、`price_unit`
- `location`
- `status`：`published`、`reserved`、`completed`、`offline`、`deleted`
- `expires_at`
- `created_at`、`updated_at`

### `resource_details`

- `listing_id`
- `condition_level`
- `expected_exchange`
- `quantity`

### `skill_details`

- `listing_id`
- `service_mode`：`online`、`offline` 或 `both`
- `available_time`
- `service_description`
- `expected_exchange`

### `listing_images`

- `id`、`listing_id`
- `storage_key`
- `sort_order`
- `is_cover`
- `created_at`

### `transactions`

- `id`、`listing_id`
- `initiator_id`、`provider_id`
- `proposed_price`、`price_unit`
- `agreed_price`
- `proposed_time`、`agreed_time`
- `proposed_location`、`agreed_location`
- `request_note`
- `agreement_snapshot_json`
- `initiator_agreed_at`、`provider_agreed_at`
- `provider_completed_at`、`requester_completed_at`
- `demo_payment_status`、`demo_paid_at`：课程演示付款记录，与交易主状态分离
- `status`
- `cancel_reason`
- `created_at`、`updated_at`

### `transaction_messages`

- `id`、`transaction_id`、`sender_id`
- `content`
- `read_at`
- `created_at`

### `reviews`

- `id`、`transaction_id`
- `reviewer_id`、`reviewee_id`
- `rating`：1 到 5
- `content`
- `created_at`
- 唯一约束：`transaction_id + reviewer_id`

### `favorites`

- `user_id`、`listing_id`
- 联合主键或唯一约束
- `created_at`

### `reports`

- `id`、`reporter_id`
- `target_type`、`target_id`
- `transaction_id` 可为空
- `reason`、`description`
- `evidence_storage_keys`
- `status`：`pending`、`investigating`、`resolved`、`rejected`
- `handler_id`、`resolution`
- `created_at`、`resolved_at`

### `credit_events`

- `id`、`user_id`、`transaction_id` 可为空
- `event_type`
- `score_delta`
- `reason`
- `operator_id` 可为空
- `created_at`

### `notifications`

- `id`、`user_id`
- `type`、`title`、`content`
- `related_type`、`related_id`
- `read_at`
- `created_at`

### `admin_operation_logs`

- `id`、`admin_id`
- `action`、`target_type`、`target_id`
- `detail_json`
- `ip_address`
- `created_at`

## 3. 交易状态

```text
pending_provider
  -> rejected
  -> pending_initiator
  -> agreed
  -> requester_confirmed / provider_confirmed
  -> completed

pending_provider/pending_initiator -> cancelled（仅发起者）
agreed -> cancelled（任一参与者，必须填写原因）
agreed/requester_confirmed/provider_confirmed -> disputed -> completed/cancelled
```

状态转换必须在 Service 层集中实现，并使用数据库事务。前端不允许直接提交任意目标状态。

## 4. API 约定

所有接口前缀为 `/api/v1`，错误格式统一为：

```json
{
  "code": "BUSINESS_ERROR_CODE",
  "message": "用户可理解的错误描述",
  "details": {}
}
```

### 认证

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/sms/send`
- `POST /auth/verification/challenge`
- `POST /auth/verification/submit`
- `POST /auth/verification/demo`（仅显式启用课程演示时）
- `POST /auth/email/send`
- `POST /auth/email/bind`
- `DELETE /auth/email`

### 发布信息

- `GET /listings`
- `POST /listings`
- `GET /listings/{id}`
- `PATCH /listings/{id}`
- `DELETE /listings/{id}`
- `POST /listings/{id}/favorite`
- `DELETE /listings/{id}/favorite`

### 交易

- `POST /transactions?listing_id={id}`
- `GET /transactions`
- `GET /transactions/{id}`
- `POST /transactions/{id}/accept`
- `POST /transactions/{id}/reject`
- `POST /transactions/{id}/agree`
- `POST /transactions/{id}/cancel`
- `POST /transactions/{id}/provider-complete`
- `POST /transactions/{id}/requester-complete`
- `POST /transactions/{id}/simulate-payment`（仅记录课程演示状态）

### 消息和评价

- `GET /transactions/{id}/messages?after_id=...`
- `POST /transactions/{id}/messages`
- `POST /transactions/{id}/reviews`

### 举报和信用

- `POST /reports`
- `GET /credit/me`
- `GET /notifications`
- `POST /notifications/{id}/read`

### 管理员

- `GET /admin/verifications`
- `POST /admin/verifications/{id}/approve`
- `POST /admin/verifications/{id}/reject`
- `GET /admin/reports`
- `POST /admin/reports/{id}/resolve`
- `POST /admin/credit-events`
- `PATCH /admin/listings/{id}/status`
- `GET /admin/statistics`
- `GET /admin/operation-logs`

## 5. 索引和数据完整性

- `users.phone_hash`、`users.username` 和 `users.student_no_hash` 唯一索引。
- `listings.type, status, category_id, created_at` 组合索引。
- `transactions.initiator_id, provider_id, status` 索引。
- `transaction_messages.transaction_id, created_at` 索引。
- `reports.status, created_at` 索引。
- 外键默认禁止删除仍被交易引用的发布信息，使用逻辑删除。

## 6. 认证和授权

- 公共接口：列表、详情、分类。
- 登录接口：注册、登录、验证码。
- 学生接口：个人内容、交易、消息、收藏、评价和举报。
- 参与者接口：只允许交易双方访问协议、消息和收款码。
- 管理员接口：必须要求 `role=admin`，每次写操作记录操作日志。
