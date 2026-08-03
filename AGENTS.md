# FastAPI Starter 项目指令

## 适用范围

- 本文件适用于本仓库全部目录。开始修改前先阅读本文件、`README.md`、相关代码和测试。
- 以当前代码、`pyproject.toml`、`uv.lock`、Alembic revision 和测试约束的行为为准，不从其他仓库机械复制目录、基类或事务模式。
- 这是面向中小型项目的教学模板。新增抽象必须解决真实的职责、生命周期或复用问题，不能只为了让目录看起来更完整。
- 修改前检查 Git 状态，保留用户已有改动；只暂存当前任务涉及的文件。

## 技术基线

- Python 3.12。
- FastAPI、Pydantic v2、SQLAlchemy 2 同步 Session、Alembic。
- 仅支持 `postgresql+psycopg`，不增加 SQLite fallback 来绕过 PostgreSQL 行为。
- 使用 `uv` 管理依赖，应用仓库必须提交 `uv.lock`。
- 本地 PostgreSQL 由 `compose.yaml` 提供；测试数据库由 Testcontainers 提供。

## 常用命令

首次启动：

```bash
cp .env.example .env
set -a
source .env
set +a
docker compose up -d db
uv sync --all-groups
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

质量检查：

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest --cov=app --cov-report=term-missing
uv run pre-commit run --all-files
uv run alembic check
```

- 修改时先运行最窄的相关测试，再按风险扩大到完整检查。
- 数据库集成测试需要 Docker 可用；不能用 mock 或 SQLite 代替 PostgreSQL 语义验证。
- 只能报告实际运行过的检查，不得把未运行的命令写成已通过。

## 分层职责

### Router

- 只负责 HTTP typed binding、依赖注入、调用 Service、调用 Presenter，以及组装 HTTP response。
- 禁止直接访问 ORM、Session 或 Repository，禁止拥有事务、权限推导和业务状态变更。
- 普通 JSON 成功响应在 Router 组装 `ApiResponse[T]`；OAuth2 token 与 `204 No Content` 保持协议原始形状。

### Service

- 拥有业务用例、业务校验、认证/授权解释、稳定业务异常和事务边界。
- 本项目的 FastAPI dependency 只注入 `DatabaseSessionManager`；每个公开 Service 用例创建并关闭自己的短 Session。
- Service 是唯一 commit/rollback owner。Repository 不得隐藏 commit，外部 IO 不得放在数据库事务中。
- Service 返回 ORM、typed Result/Facts 或简单业务数据，禁止返回 FastAPI `Response` 或 HTTP envelope。

### Repository

- 只负责查询、稳定排序、约束相关持久化和 `flush()`，不负责 HTTP、角色授权或完整业务结论。
- 查询 miss 返回 typed `None`，由 Service 转换为稳定 NotFound。
- 写入参数使用 Repository 拥有的 typed dataclass/schema，禁止把 request 的裸 `dict` 直接 mass assignment 到 ORM。

### Mapper 与 Presenter

- Mapper 将 request schema 显式转换为内部 Command，保留 PATCH 的字段提供状态。
- Presenter 通过 allowlist 把 ORM/Result 转换为公开 Data schema。
- 两者只能转换字段，禁止访问数据库、判断权限、改变状态或提交事务。
- 禁止整体 dump ORM 或宽内部模型作为公开响应，尤其不能暴露 `hashed_password`。

## API 契约

- Request、内部 Command/Result、ORM 和 Response Data 分别拥有自己的类型；owner 或语义不同时必须拆型。
- 普通 API wire 字段使用 camelCase；Python 内部保持 snake_case。
- OAuth2 token 响应必须保留标准的 `access_token`、`token_type`、`expires_in`。
- 普通成功响应使用 `{ "data": ... }`；错误响应使用统一的 `{ "error": ... }`；`204` 不返回 JSON body。
- 分页响应保留 `items`、`total`、`page`、`pageSize`，Repository 查询必须有稳定排序。
- PATCH 必须区分未提供、显式 `null` 和具体值，使用 `model_fields_set` 或 `exclude_unset=True` 保留该语义。
- 禁止用 `exclude_none=True` 实现 PATCH。不可为空字段收到显式 `null` 时必须在 request schema 边界拒绝。
- 使用 Pydantic v2 API；禁止新增 `.dict()` 和未经重新验证的 `model_copy(update=...)`。

## 认证与授权

- 密码只保存 Argon2 哈希；密码、密码哈希、JWT 和 Secret 不得进入响应、日志、测试快照或提交内容。
- 当前用户身份只能来自验证后的 Bearer token，不能相信 body、query 或客户端自报 header 中的 user/role。
- 缺失、无效或已失效认证返回 `401` 并保留 `WWW-Authenticate: Bearer`；身份有效但权限不足返回 `403`。
- 管理员授权在拥有用户事实的服务端边界验证，不能只依赖前端隐藏入口。
- 当前实现每次认证请求都会查询用户，因此删除或禁用用户会阻止旧 access token；不要在未实现撤销存储时宣称支持主动登出或 token revoke。
- 认证、越权、禁用用户和删除用户后的旧 token 都必须有负向 API contract test。

## 数据库与 Migration

- API 启动和 PostgreSQL 容器启动时禁止调用 `Base.metadata.create_all()` 或自动执行 Alembic。
- Migration 是独立部署步骤，只能由一个明确 owner 执行，避免多个 API replica 竞争升级 schema。
- 模型变更必须新增 forward revision；禁止修改已经在共享环境执行过的 migration。
- 创建 revision 前确认单一 head，并审查表、列、nullable、constraint、index、server default、upgrade 和 downgrade。
- Migration 至少在真实 PostgreSQL 上验证 upgrade；声明可逆时同时验证 downgrade。
- `Base.metadata.create_all()` 仅允许用于不验证 migration 的隔离测试 fixture，不能替代 migration integration test。

## 错误、日志与请求 ID

- 已知失败转换为 `AppError` 子类，由统一 exception handler 映射 HTTP 状态和稳定错误码。
- 禁止在 Router、Service 或 Repository 中随意抛通用 `HTTPException` 来表达业务错误。
- 未处理异常对外只返回固定安全文案；不得泄漏 stack、SQL、连接串、内部 URL、headers 或原始 payload。
- 请求 ID 必须通过统一 middleware/handler 传播；外部 request ID 只能作为受约束的关联信息，不能成为身份或权限事实。
- 同一异常只在能决定恢复、retry 或终止语义的 owner 记录一次。

## 测试要求

- Router/API contract test 从真实 FastAPI/ASGI 边界进入，断言状态码、精确公开字段、envelope、认证 header 和错误码。
- Repository、Session、constraint、事务和 migration 使用真实 PostgreSQL 集成测试。
- 权限测试同时覆盖允许与越权；分页覆盖稳定顺序、空结果和边界参数。
- 修复 bug 必须增加一个修复前会失败的最小回归测试。
- 测试独立于执行顺序，不依赖其他测试遗留的数据；测试凭据使用运行时随机值，不写死真实凭据。

## 文件与凭据卫生

- 禁止提交 `.env`、`.coverage`、`app.db`、数据库 volume、缓存、虚拟环境、日志或任何 credential。
- `.env.example` 只能包含安全占位值和配置结构，不能包含真实用户名、密码、token、连接串或 Secret。
- SSH 私钥、公钥配置和 GitHub credential 属于开发主机，不得放进本仓库。
- 新增运行产物时同步更新 `.gitignore`，并在提交前检查暂存区。

## 完成检查

- [ ] Router、Service、Repository、Mapper/Presenter 职责未串层。
- [ ] Session 和 transaction owner 唯一，没有隐藏 commit 或长事务。
- [ ] PATCH omitted/null/value、分页排序和公开字段有 contract test。
- [ ] 认证身份来自可信 token，越权和失效路径已测试。
- [ ] 模型变更新增了 migration，并在 PostgreSQL 上验证。
- [ ] Ruff、format、mypy、pytest、pre-commit 和适用的 Alembic 检查已实际运行。
- [ ] 暂存区不含 Secret、`.env`、coverage、数据库文件、缓存或无关改动。
