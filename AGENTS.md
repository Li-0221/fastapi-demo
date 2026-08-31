# FastAPI Starter 规则

## 定位与技术基线

- 本项目是面向中小型项目的 FastAPI 后端模板，优先清晰、typed contract 和可维护性，不预置 DDD、CQRS、微服务或没有消费者的抽象。
- 使用 Python 3.12、FastAPI、Pydantic v2、SQLAlchemy 2 同步 Session、Alembic、PostgreSQL 和 uv；依赖变更必须同步 `uv.lock`。
- 只支持 `postgresql+psycopg`。本地数据库由 `compose.yaml` 提供，数据库集成测试使用 Testcontainers，不增加 SQLite fallback。
- 修改前阅读 `README.md`、相关代码和测试，检查 Git 状态并保留无关改动。其他仓库只能作为参考，不能机械复制目录、基类、认证或事务模式。

## 分层与抽象

- 调用方向保持 `Router -> Service -> Repository -> PostgreSQL`。
- Router 只负责 HTTP typed binding、依赖注入、调用 Service 和响应组装，不直接访问 ORM、Session 或 Repository。
- Service 拥有业务规则、授权、稳定业务异常和事务。FastAPI dependency 只注入 `DatabaseSessionManager`；每个公开用例创建并关闭自己的短 Session，并且是唯一 commit/rollback owner。
- Repository 只负责查询、稳定排序、约束相关写入和 `flush()`；查询 miss 返回 typed `None`，不得隐藏 commit 或返回裸 dict、裸 tuple、SQLAlchemy `Row`。
- 不把 request 或裸 dict 传入业务层，不用字符串 key mass assignment ORM，不让 ORM、Session、FastAPI `Response` 或密码哈希离开业务边界。
- 简单用例传递明确的 typed 参数，不为一比一复制增加 Command。存在多入口、不同信任级别、PATCH 三态、入站 shape 与用例语义不同或参数组需要独立演进时，启用 Service-owned Command。
- 内部 ORM/Result 与公开 Data 存在改名、计算、聚合、角色视图、版本差异或多处共享转换时，启用 Presenter/mapper/转换函数做显式 allowlist 映射。
- 公开 Data 只是同名字段子集时，可由 Service 在 Session 关闭前用目标 response schema 校验收窄，并用 API contract test 断言精确公开字段，不额外增加 Presenter。
- Presenter/mapper 只转换字段，不查询数据库、不判断权限、不改变状态或提交事务。无状态转换优先使用模块级函数，不为字段复制增加 `mappers/` 目录或 Mapper class。
- 只有真实多实现、资源生命周期或独立变化轴存在时才增加 class、`Protocol` 或 Unit of Work。

## API 契约

- 入站 schema 继承 `RequestModel`，获得 camelCase alias 和 `extra="forbid"`；公开 response data 继承 `ResponseModel`。内部 Command/Result 不继承 HTTP schema 基类。
- Request schema 负责输入 shape 和 payload 内可立即判断的规则；Service 负责状态、时间、角色、资源归属等业务规则；数据库只承担所有 writer 都必须遵守的不变量。
- 普通成功响应为 `{ code: 0, data, message: "success" }`；错误使用非零稳定业务码和真实 HTTP 状态，`data` 为 `null`，请求 ID 通过 `X-Request-ID` 返回；OAuth2 token 和 `204` 保持协议原始形状。
- wire 字段使用 camelCase；分页固定使用 `page`、`pageSize`、`items`、`total`，Repository 查询必须稳定排序。OAuth2 token 字段保留标准 snake_case。
- PUT 表示完整替换，可清空字段显式传 `null`；write-only 密码字段省略或 `null` 表示不轮换。PATCH 必须区分 omitted、`null` 和普通值，不使用 `exclude_none=True` 合并语义。
- 已知业务失败使用 `AppError` 并由统一 handler 映射；未知错误不得泄漏 stack、SQL、headers、连接串、内部 URL 或 payload。

## 认证与安全

- 身份只来自验证后的 Bearer token，权限由拥有业务事实的 Service 判断；不能相信 body、query 或客户端自报的 user/role。
- 缺失、无效或过期认证返回 `401` 并保留 `WWW-Authenticate: Bearer`；身份有效但权限不足返回 `403`。
- 密码只保存 Argon2 哈希；密码、token 和 Secret 不得进入普通响应、日志、快照或提交内容。
- 当前提供公开注册和 access token 登录，没有 refresh session、token rotation、主动登出撤销或 token revocation 子系统，不得从全栈模板复制相关假设。
- 每次认证请求都会查询用户，因此停用或删除用户会阻止旧 access token；其他已签发 token 只在自然过期后失效。

## 数据库与配置

- 数据库约束保护所有 writer 都必须遵守的不变量；唯一性和并发一致性不能只依赖 check-then-write。
- 捕获使事务失败的 `IntegrityError` 后必须先 rollback，再查询冲突事实、恢复或转换稳定业务异常。外部 IO 不放在数据库事务中。
- 模型变更新增 forward migration，不修改已发布 revision。应用启动时不自动执行 migration 或 `create_all()`；migration 在真实 PostgreSQL 验证 upgrade，声称可逆时同时验证 downgrade。
- 对外时间使用带 offset 的 RFC3339，数据库 datetime 使用 timezone-aware UTC 语义。
- 只有运行时代码真实读取的配置才能进入 Settings、`.env.example` 和 Compose；必填生产配置启动时 fail fast，Secret 由运行环境注入。

## 验证与卫生

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest --cov=app --cov-report=term-missing
uv run pre-commit run --all-files
uv run alembic check
```

- 先运行最窄相关测试，再按风险扩大。API contract 从真实 ASGI 边界验证状态码、精确公开字段、错误码和认证 header；Repository、事务和 migration 使用真实 PostgreSQL。
- 认证、越权、停用和删除用户后的旧 token 必须有负向 contract test；bug 修复增加修复前会失败的最小回归测试。
- 只报告实际执行过的检查。不提交 `.env`、凭据、数据库文件、缓存、虚拟环境、日志、coverage 或无关改动。
