# FastAPI 中小型项目参考模板

## 项目定位

本项目是一个**面向初学者、可直接作为中小型后台项目起点的 FastAPI starter**。
它希望在“容易读懂”和“能承担真实项目”之间取得平衡：

- **对新手友好**：调用链保持清晰，优先使用 Router、Service、Repository 和 typed schema 组成的直接结构。
- **可用于真实后台**：保留 PostgreSQL、Alembic、认证与授权、事务、稳定错误契约、安全日志边界和分层测试等生产基础能力。
- **简单优先，但不追求极端最简**：不为一比一字段复制提前增加层级，也不会为减少文件而删除真正保护权限、数据完整性和事务语义的结构。
- **按复杂度演进**：Command、Result、Presenter、Unit of Work 等都不被禁止；当多入口契约、PATCH 三态、聚合映射、角色视图或跨 Repository 事务等真实需求出现时再启用。

它不是只演示路由和 CRUD 的一次性 demo，也不是预先搭好 DDD、CQRS、微服务和各种抽象层的大型企业脚手架。
目标是让初学者现在能顺着代码学会正确边界，也让项目未来能够自然扩展到中型后台。

实现参考了 [`full-stack-fastapi-template`](https://github.com/fastapi/full-stack-fastapi-template/tree/master/backend/app)
的应用入口、配置、认证和测试思路；仓库工程约束见 [`AGENTS.md`](AGENTS.md)。

模板已包含：

- 用户公开注册、OAuth2 密码登录和 JWT Bearer 认证
- 当前用户读取、完整资料更新和校验旧密码后的密码修改
- 管理员用户创建、分页列表、详情、完整更新和删除
- Argon2 密码哈希，公开响应永不包含密码哈希
- SQLAlchemy 2、Alembic 与 Docker PostgreSQL
- 统一成功 envelope、稳定错误码、请求 ID 和安全的未知错误响应
- Ruff、mypy、pytest、pre-commit 和 API contract tests

## 1. 先理解目录

```text
fastapi-demo/
├── alembic/                       # 数据库 schema 的迁移环境与版本历史
│   ├── versions/                  # Alembic revision 文件
│   └── env.py                     # Alembic 运行环境和 metadata 装配
├── src/app/
│   ├── api/
│   │   ├── routes/                # HTTP 参数、依赖注入、响应组装
│   │   └── router.py              # API 子路由汇总
│   ├── core/                      # 配置和密码/JWT 基础能力
│   ├── db/                        # Session manager 和 ORM metadata
│   ├── dependencies/              # Manager、Service、当前用户的依赖装配
│   ├── models/                    # SQLAlchemy ORM 模型
│   ├── repositories/              # 查询、排序、约束错误和持久化
│   ├── schemas/                   # Request、Data 和 HTTP response 契约
│   ├── scripts/                   # 创建超级管理员等运维脚本
│   ├── services/                  # Session、事务、权限和业务规则
│   ├── exception_handlers.py      # 业务错误到 HTTP 错误契约的唯一映射
│   ├── exceptions.py              # 稳定业务异常与错误码
│   ├── main.py                    # FastAPI 应用工厂
│   └── middleware.py              # Request ID 等 HTTP 中间件
├── tests/
│   ├── api/                       # 从真实 ASGI 边界验证公开 API 契约
│   ├── integration/               # PostgreSQL Session 与 migration 集成测试
│   ├── unit/                      # 配置等快速单元测试
│   ├── conftest.py                # pytest fixture 和测试数据库生命周期
│   └── support.py                 # 测试数据工厂
├── .dockerignore                  # 排除 Secret、虚拟环境和本地构建产物
├── .env.example                   # 本地环境变量安全示例
├── .python-version                # 锁定本地与容器的 Python 3.12 基线
├── .pre-commit-config.yaml        # 提交前检查配置
├── AGENTS.md                      # 本仓库工程约束
├── Dockerfile                     # API 容器镜像定义
├── alembic.ini                    # Alembic 配置
├── compose.yaml                   # 本地 PostgreSQL 编排
├── pyproject.toml                 # Python 依赖与工具配置
└── uv.lock                        # 锁定后的依赖版本
```

核心调用方向是 `Router -> Service -> Repository -> PostgreSQL`。Service 拥有短 Session、
事务和业务授权，Repository 只负责持久化。完整请求链路及 Command/Presenter 的启用条件见
[`docs/request-lifecycle.md`](docs/request-lifecycle.md) 和 [`AGENTS.md`](AGENTS.md)。
事务、Session、PATCH 三态和 Pydantic Optional 的复习笔记见
[`docs/FastAPI 当前最需要复习的 5 个知识点.md`](docs/FastAPI%20当前最需要复习的%205%20个知识点.md)。

## 2. 本地启动（Docker PostgreSQL）

应用只支持 `postgresql+psycopg`，没有 SQLite fallback。应用不会自行读取 `.env` 文件；
Compose 使用 `.env` 启动数据库，本地 shell 再显式导出同一份配置。

本地需要 Python 3.12、uv 0.11 和支持 `--wait` 的 Docker Compose。仓库内的
`.python-version` 会让 uv 选择 Python 3.12。

```bash
cd fastapi-demo
cp .env.example .env
# 填写 .env 中的本地隔离配置
set -a
source .env
set +a
docker compose up -d --wait db
uv sync --all-groups
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

`APP_SECRET_KEY` 至少 32 个字符。`APP_DATABASE_URL` 必须使用 `postgresql+psycopg` driver，
并连接到 Compose 映射到本机的 PostgreSQL 端口。可以用
`python -c 'import secrets; print(secrets.token_urlsafe(48))'` 生成本地 Secret。
应用会在启动时校验这两项必填配置；`.env` 已被 Git 忽略，不能提交。

打开：

- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>
- 健康检查: <http://127.0.0.1:8000/api/v1/health>

需要验证 API 镜像时运行：

```bash
docker build -t fastapi-demo .
```

生产环境应把 migration 作为独立部署步骤，并从 secret manager 注入配置，不要让每个 API
replica 在启动时竞争执行 migration。

## 3. 创建第一个管理员

先执行迁移，再运行交互式脚本。密码通过终端隐藏输入，不会进入 shell history：

```bash
uv run python -m app.scripts.create_superuser
```

然后在 `/docs` 点击 **Authorize**。OAuth2 表单中的 `username` 填邮箱，`password` 填刚才输入的密码。

## 4. API 契约

除 OAuth2 登录与 `204 No Content` 外，成功响应统一为：

```json
{
  "code": 0,
  "data": {},
  "message": "success"
}
```

分页 query 使用 `page`、`pageSize`。分页响应的 `data` 固定包含 `total`、`items`、`page`、
`pageSize`，具体列表可以增加额外字段。普通 API 字段统一使用 camelCase。OAuth2
登录必须保持标准的 `access_token`、`token_type` 和 `expires_in`，否则 Swagger 和通用
OAuth2 客户端无法识别。

错误响应统一为：

```json
{
  "code": 10007,
  "data": null,
  "message": "A user with this email already exists"
}
```

失败响应继续返回真实的 `4xx`/`5xx` HTTP 状态；顶层 `code` 是独立、稳定且非零的自定义
整数业务码，不能从 HTTP 状态码推导。`data` 固定为 `null`，`message` 提供安全的展示消息，
请求关联 ID 通过 `X-Request-ID` header 返回。

| HTTP 状态 | 业务码 | 错误定义 |
| --- | --- | --- |
| `400` | `10003` | `INVALID_CURRENT_PASSWORD` |
| `401` | `10001`、`10002` | `AUTHENTICATION_REQUIRED`、`INVALID_CREDENTIALS` |
| `403` | `10004`、`10005` | `INACTIVE_USER`、`PERMISSION_DENIED` |
| `404` | `10006`、`10010` | `USER_NOT_FOUND`、`HTTP_ERROR` |
| `405` | `10010` | `HTTP_ERROR` |
| `409` | `10007`、`10008` | `EMAIL_ALREADY_EXISTS`、`SELF_ADMINISTRATION_NOT_ALLOWED` |
| `422` | `10009` | `VALIDATION_ERROR` |
| `500` | `10011` | `INTERNAL_ERROR` |

端点、请求参数和成功响应字段以运行时 Swagger/ReDoc 为准。为保持 Router 声明简洁，OpenAPI
不逐项枚举业务错误响应；错误状态、稳定错误码和统一 envelope 由本节及 API contract tests 约束。

PUT 要求完整提供当前资源可编辑的字段；`fullName: null` 表示清空姓名，不可为空的字段
（例如 `email`、`isActive`）缺失或收到 `null` 会在 request schema 边界返回 `422`。
用户修改密码必须调用 `/users/me/password` 并提供 `currentPassword` 和 `newPassword`；管理员
更新其他用户时，`password` 仍是可选的 write-only 字段，省略或传 `null` 表示不重置密码。

生产部署必须在网关或反向代理为公开的注册、登录端点设置请求体上限和按来源限流。
限流通常需要共享存储与可信客户端地址，不属于这个单进程教学模板的应用内能力。

JWT access token 本身无法主动撤销。当前实现每次请求都会重新查询用户，因此删除或禁用用户
会立即阻止旧 token；修改密码只影响后续登录，已经签发的 token 仍会在过期前有效。

## 5. 质量检查

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest --cov=app --cov-report=term-missing
uv run pre-commit run --all-files
uv run alembic check
```

首次 clone 后可运行 `uv run pre-commit install` 安装提交钩子。

当模型变化时，先确认当前只有一个 migration head，再生成并审查新 revision：

```bash
uv run alembic heads
uv run alembic revision --autogenerate -m "describe the schema change"
uv run alembic upgrade head
```

不要修改已经在共享环境执行过的 migration；应新增 forward revision。
