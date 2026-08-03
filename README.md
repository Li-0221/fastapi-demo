# FastAPI 中小型项目参考模板

这是一个供初学者阅读、运行和继续扩展的后端模板。它参考了
[`full-stack-fastapi-template`](https://github.com/fastapi/full-stack-fastapi-template/tree/master/backend/app)
的应用入口、配置、认证和测试思路，但把中小型项目最容易混乱的职责拆开了。
实现同时遵循仓库内的 [`AGENTS.md`](AGENTS.md)，重点落实 Session 生命周期、事务 owner、
内部 contract 和 Presenter 边界。

模板已包含：

- 用户公开注册、OAuth2 密码登录和 JWT Bearer 认证
- 当前用户读取和完整资料更新
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
│   │   ├── openapi.py             # OpenAPI 错误响应 schema 装配
│   │   └── router.py              # API 子路由汇总
│   ├── core/                      # 配置和密码/JWT 基础能力
│   ├── db/                        # Session manager 和 ORM metadata
│   ├── dependencies/              # Manager、Service、当前用户的依赖装配
│   ├── models/                    # SQLAlchemy ORM 模型
│   ├── presenters/                # 内部 Result 到公开 Data 的 allowlist 映射
│   ├── repositories/              # 查询、排序、约束错误和持久化
│   ├── schemas/                   # Request、Data 和 HTTP response 契约
│   ├── scripts/                   # 创建超级管理员等运维脚本
│   ├── services/                  # Command/Result、Session、事务和业务规则
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

一次登录请求的调用方向是：

```text
HTTP form -> Router -> Command -> AuthService -> short Session -> Repository -> Database
                |                   |              |
                |                   |              +-> 查询和 flush，不 commit
                |                   +-> 认证、业务异常、事务 owner
                +-> Presenter / OAuth2 标准响应
```

这个方向很重要：FastAPI dependency 只注入可复用的 session manager，不通过 `yield`
持有业务 Session；Service 的每个公开用例创建并关闭短 Session，是唯一的 commit/rollback
owner；Repository 不判断管理员权限，也不偷偷 commit；Presenter 只映射公开 allowlist 字段。
应用 lifespan 拥有数据库 Engine，并在进程关闭时释放连接池。

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
  "data": {}
}
```

列表的 `data` 包含 `items`、`total`、`page`、`pageSize`。所有普通 API 字段使用
camelCase。OAuth2 登录必须保持标准的 `access_token`、`token_type` 和 `expires_in`，否则
Swagger 和通用 OAuth2 客户端无法识别。

错误响应统一为：

```json
{
  "error": {
    "code": "STABLE_MACHINE_CODE",
    "message": "Safe message",
    "requestId": "request correlation id",
    "details": []
  }
}
```

主要端点：

| 方法 | 路径 | 权限 | 用途 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/auth/register` | 公开 | 注册普通用户 |
| `POST` | `/api/v1/auth/login/access-token` | 公开 | 登录并签发 access token |
| `GET` | `/api/v1/users/me` | 登录 | 查看自己 |
| `PUT` | `/api/v1/users/me` | 登录 | 完整更新自己的可编辑资料，可选修改密码 |
| `POST` | `/api/v1/users` | 管理员 | 创建用户 |
| `GET` | `/api/v1/users` | 管理员 | 稳定排序的分页列表 |
| `GET` | `/api/v1/users/{userId}` | 管理员 | 用户详情 |
| `PUT` | `/api/v1/users/{userId}` | 管理员 | 完整更新用户的可管理字段，可选修改密码 |
| `DELETE` | `/api/v1/users/{userId}` | 管理员 | 删除用户 |

PUT 要求完整提供当前资源可编辑的字段；`fullName: null` 表示清空姓名，不可为空的字段
（例如 `email`、`isActive`）缺失或收到 `null` 会在 request schema 边界返回 `422`。
密码无法从详情接口回读，因此是可选的 write-only 字段；省略或传 `null` 表示保持现有密码。

生产部署必须在网关或反向代理为公开的注册、登录端点设置请求体上限和按来源限流。
限流通常需要共享存储与可信客户端地址，不属于这个单进程教学模板的应用内能力。

## 5. PostgreSQL 容器

Compose 只管理本地 PostgreSQL，不在数据库容器启动时隐式执行 migration：

```bash
docker compose up -d --wait db
docker compose ps
docker compose logs db
```

本地验证 API 镜像：

```bash
docker build -t fastapi-demo .
```

生产环境应把 migration 作为独立部署步骤，并从 secret manager 注入配置，不要让每个 API
replica 在启动时竞争执行 migration。

## 6. 质量检查

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

## 7. 下一步扩展建议

先按业务需要逐项增加，而不是提前堆基础设施：

1. refresh token 与服务端撤销记录
2. 邮箱验证、找回密码和发送适配器
3. RBAC role/permission 表，替换单一 `isSuperuser`
4. 软删除与审计日志
5. 结构化日志、指标和 tracing

JWT access token 本身无法主动撤销。当前实现每次请求都会重新查询用户，因此删除或禁用用户
会立即阻止旧 token；若要支持“登出当前设备”，需要增加 token id 和撤销存储。
