# FastAPI Starter 项目指令

## 适用范围

- 本文件适用于本仓库全部目录。开始修改前先阅读本文件、`README.md`、相关代码和测试。
- 以当前代码、`pyproject.toml`、`uv.lock`、Alembic revision 和测试约束的行为为准，不从其他仓库机械复制目录、基类或事务模式。
- 这是面向中小型项目的教学模板。新增抽象必须解决真实的职责、生命周期或复用问题，不能只为了让目录看起来更完整。
- 简单优先不等于追求最少文件。Service、Repository、typed contract、事务、权限和数据库约束等能保护真实语义的结构必须保留，使项目可从小型平滑扩展到中型。
- 不在无关需求中顺手迁移全部旧代码或统一全仓风格；只在当前修改涉及的链路按本文件收敛。
- 修改前检查 Git 状态，保留用户已有改动；只暂存当前任务涉及的文件。

## 技术基线

- Python 3.12。
- FastAPI、Pydantic v2、SQLAlchemy 2 同步 Session、Alembic。
- 仅支持 `postgresql+psycopg`，不增加 SQLite fallback 来绕过 PostgreSQL 行为。
- 使用 `uv` 管理依赖，应用仓库必须提交 `uv.lock`。
- 本地 PostgreSQL 由 `compose.yaml` 提供；测试数据库由 Testcontainers 提供。

## 抽象与依赖原则

- 复用仓库现有类型和边界；只有 trust、owner、语义、生命周期或独立版本轴不同时才新增转换层。
- Command 和 Presenter 都是复杂用例的有效工具，不禁止使用，也不是默认必备层。简单同构链路中删除它们不会丢失 trust、owner、语义、生命周期、公开字段白名单或独立演进能力时，应当省略对应抽象。
- HTTP/CLI/worker 等多入口需要共享独立输入契约，或存在不同角色/信任级别、PATCH 三态、入站 shape 与用例语义不同、参数组需要独立演进时，应当启用 Service-owned Command。仅有多个调用方但关键字参数仍清晰，不足以单独证明需要 Command。
- 内部 Result/ORM/provider facts 与公开 Data 需要改名、计算、聚合重组、角色视图、API 版本差异或多处共享转换时，应当启用 Presenter/转换函数做显式 allowlist 映射。仅是同名字段子集时，可由目标 Data schema 在 Service 内直接校验收窄，但必须用 API contract test 断言精确公开字段且不暴露敏感数据。
- 无状态转换优先使用函数；只有存在状态、资源生命周期、多个真实实现或第三方隔离时才新增 class、`Protocol` 或 wrapper。
- `Protocol` 只用于真实可替换的 repository、client、clock 或 Unit of Work 边界，不为普通函数机械增加接口。
- helper、base class 或通用模块必须实际降低重复或认知成本，不能为了表面 DRY 把局部语义上移为全局抽象。
- 不新增 optional dependency 再通过运行时 `require_*()` 检查可用性；必需依赖应当通过构造函数或函数参数显式传入。

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

## 业务校验与数据库不变量

- Request schema 负责输入 shape、单字段约束和同一 payload 内可以立即判断的关联校验。
- Service 负责状态流转、当前时间、角色、资源归属和用例字段完整度等业务规则。
- 工作流 status、字符串 enum 成员、未来时间、状态跳转和只对特定 API/角色成立的规则，默认不重复建立数据库 `CHECK` constraint。
- 数据库负责所有 writer 都必须遵守的底层完整性：`NOT NULL`、`UNIQUE`、foreign key、并发一致性和必须原子成立的列间不变量。
- 唯一性和并发一致性必须由 constraint、lock、CAS/version 或原子 upsert 保护；禁止只依赖 check-then-write。
- 约束归属发生变化时通过新的 forward migration 调整，禁止修改已发布 migration。

## Settings 与环境变量

- 只有运行时代码真实读取并改变行为的配置才能进入 Settings、`.env.example` 或 `compose.yaml`。
- 新增配置前必须明确 owner、默认值、缺失行为、敏感级别和部署注入位置，并用运行路径或测试证明它被消费。
- 部署所需的必填配置必须在应用启动边界 fail fast；只有语义明确且跨环境安全的值才能提供默认值。
- 删除配置时必须同步清理 Settings 字段、示例 env、Compose、功能分支、错误码、测试和文档引用，不保留没有消费者的变量。
- `.env.example` 只描述变量名和安全占位值；真实 Secret 由运行环境注入。

## 分层职责

### Router

- 只负责 HTTP typed binding、依赖注入、调用 Service、在必要时调用 Presenter/转换函数，以及组装 HTTP response。
- 禁止直接访问 ORM、Session 或 Repository，禁止拥有事务、权限推导和业务状态变更。
- 普通 JSON 成功响应在 Router 组装 `ApiResponse[T]`；OAuth2 token 与 `204 No Content` 保持协议原始形状。

### Service

- 拥有业务用例、业务校验、认证/授权解释、稳定业务异常和事务边界。
- 本项目的 FastAPI dependency 只注入 `DatabaseSessionManager`；每个公开 Service 用例创建并关闭自己的短 Session。
- FastAPI dependency 禁止通过 `yield` 持有业务 Session；Session 必须由 Service 的公开用例或显式上层事务 owner 创建和关闭。
- Service 是唯一 commit/rollback owner。Repository 不得隐藏 commit，外部 IO 不得放在数据库事务中。
- Service 必须在关闭 Session 前返回不含敏感内部字段的 response Data、typed Result/Facts 或简单业务数据；禁止把 ORM、FastAPI `Response` 或 HTTP envelope 返回给 Router。
- 如果一个上层用例未来需要跨多个 Service 保持原子事务，应将必需 Session 显式传给事务内协作者；协作者不得再次开 Session 或 commit。
- 高风险外部副作用不能与数据库写入组成不可恢复的假事务；应先持久化可恢复 intent，再调用外部系统，最后记录成功或失败事实。

### Repository

- 只负责查询、稳定排序、约束相关持久化和 `flush()`，不负责 HTTP、角色授权或完整业务结论。
- 查询 miss 返回 typed `None`，由 Service 转换为稳定 NotFound。
- 写入参数使用 Repository 拥有的 typed dataclass/schema，禁止把 request 的裸 `dict` 直接 mass assignment 到 ORM。
- `flush()` 只用于在当前事务内取得数据库生成值、触发约束或让后续 SQL 看见写入；它不等于持久提交。
- Repository 返回 ORM、typed read model、`list[T]` 或 `(items, total)`，不得让 SQLAlchemy `Row`、裸 tuple 或裸 dict 泄漏到业务层。

### Contract 转换与 Presenter

- 简单用例由 Router 把已校验字段作为明确关键字参数传给 Service，不为一比一复制新增 Command。当 trust、owner、语义、生命周期或演进方向不同，或参数组已形成独立概念时，应当改用 Service-owned Command。
- Router 禁止把 request 先 dump 成裸 dict 再传递；Service 也禁止把 request 或裸 dict 继续下传给 Repository。
- 需要 Request 到 Command 或 ORM 到 Result 的转换时，通过目标 contract 的 named constructor 完成，并保留 PUT 的完整字段语义。
- 不为单一字段复制链路新增独立 `mappers/` 目录或无状态 Mapper class；只有存在多个真实来源或 adapter 时才建立独立转换模块。
- ORM/Result 到公开 Data 只是同名字段子集时，Service 可以在 Session 关闭前用目标 Data schema 直接校验收窄；涉及改名、计算、聚合、角色视图、版本差异或共享转换时，必须通过 Presenter/转换函数做显式 allowlist 映射。若 Service 已返回与公开 Data 同构同义的 typed Data，Router 可以直接组装 response。
- Presenter/转换函数只能转换字段，禁止访问数据库、判断权限、改变状态或提交事务。无状态且只有一个实现时优先使用语义明确的模块级函数，不为形式统一新增 Presenter class。
- 禁止整体 dump ORM 或宽内部模型作为公开响应，尤其不能暴露 `hashed_password`。

## API 契约

- Request、ORM 和 Response Data 不得因为方便而混为一个宽型。内部 Command/Result 在 owner、trust、语义、生命周期或演进方向不同时必须拆出；语义完全一致且已排除敏感字段的 typed Data 可以由 Service 和 Router 共用。
- 入站 request schema 继承项目的 `RqModel`，统一获得 camelCase alias 和 `extra="forbid"`；公开 response Data 继承 `RsModel`。
- 需要独立 Command/Result 时，使用 dataclass 或独立内部模型，不继承 `RqModel`/`RsModel`，避免 wire alias、extra 和序列化策略进入业务层。
- 普通 API wire 字段使用 camelCase；Python 内部保持 snake_case。
- OAuth2 token 响应必须保留标准的 `access_token`、`token_type`、`expires_in`。
- 普通成功响应使用 `{ "data": ... }`；错误响应使用统一的 `{ "error": ... }`；`204` 不返回 JSON body。
- 分页响应保留 `items`、`total`、`page`、`pageSize`，Repository 查询必须有稳定排序。
- PATCH 必须区分未提供、显式 `null` 和具体值，使用 `model_fields_set` 或 `exclude_unset=True` 保留该语义。
- 禁止用 `exclude_none=True` 实现 PATCH。不可为空字段收到显式 `null` 时必须在 request schema 边界拒绝。
- 使用 Pydantic v2 API；禁止新增 `.dict()` 和未经重新验证的 `model_copy(update=...)`。
- `Optional` 只表示当前 contract 中真实可达的缺失状态；应在第一个拥有完整事实的 schema/Service 边界收窄，不能沿调用链重复判空或补默认值。
- 字段约束、alias 和 serializer metadata 使用 `Annotated[T, Field(...)]`；真实可变默认值使用 `default_factory`。
- `model_dump()` 只用于真实 JSON、持久化或 typed update 边界。普通 FastAPI response model 交给框架序列化；只有手动构造 HTTP JSON 时才按 contract 显式选择 `mode="json"`、`by_alias` 和 `exclude_none`。
- 业务层之间传 Pydantic model、dataclass 或其他 owned typed structure；裸 dict 只能停留在真实 JSON/HTTP/JSONB 边界。

## PUT、PATCH 与写入模型

- 新增 PUT 默认表示完整资源替换，使用语义明确的 `FooPut` request；完整资源字段必须提供，可清空字段也必须显式传 `null`。
- 现有用户更新接口使用 PUT 表达完整替换；请求必须提供对应资源全部可编辑字段，允许清空的字段也必须显式传 `null`。
- 本仓库的用户 update 必须保持为 PUT，不得改回 PATCH 后将 request `model_dump()` 为带字符串 key 的 dict 再更新 ORM。PUT 本身不会自动消除字符串 key；真正的不变量是 `FooPut` request、必要时的 typed Command、typed `UserRecordReplacement` 和 Repository 显式 ORM 属性赋值组成的完整 typed 链路。
- 密码等无法从详情响应回读的 write-only 字段可以在 PUT 中保持可选；省略或 `null` 表示不轮换该凭据，不影响其他字段的完整替换语义。
- ORM 更新优先显式字段赋值，使类型检查能够发现字段拼写和归属错误；禁止 request dump 后通过字符串 key 动态 `setattr`。
- 不新增全局通用 `UpdateSchema`。确需复用更新 payload 时，由目标 Repository 拥有窄 typed schema，并明确 omitted/null/value 语义。
- 密码等需要转换的字段先在 Service 生成业务事实，再以 typed persistence payload 传给 Repository，不能把原始 request 直接下传。

## OpenAPI 与描述元数据

- 不添加没有运行价值的 `Field(description=...)`、route `summary`、route `description`、`response_description` 或 OpenAPI tag description。
- Router handler 不写会被 FastAPI 收集为 operation description 的说明性 docstring。
- 使用清晰的 route、函数、schema、字段名以及类型约束表达接口含义。
- `Field` 仍可用于约束、alias、validator 和 serializer；真实业务字段名为 `description` 不受本规则影响。

## 认证与授权

- 密码只保存 Argon2 哈希；密码、密码哈希和 Secret 不得进入响应、日志、测试快照或提交内容。JWT 只能出现在认证协议明确要求的 access-token 响应中，不得进入日志、快照或其他响应。
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
- 捕获 `IntegrityError` 或其他使事务失败的数据库异常后，必须先 rollback，再查询冲突事实、执行幂等恢复或转换稳定业务异常。
- `refresh()` 只在提交后仍需读取 server default、触发器更新、过期属性或 relationship 来构造返回值时使用，不机械 refresh 无返回写入。
- 大表 schema/data 变更必须评估锁和参数预算，采用 expand/backfill/contract 或有界批处理，并明确恢复路径。

## 时间与时区

- 对外时间使用带 offset 的 RFC3339；需要统一 UTC 时，在 schema/Service 边界校验或规范化。
- 数据库 datetime 使用 timezone-aware 类型并按 UTC 语义读写，不保存无时区但默认解释为 UTC 的模糊时间。
- 用户界面选择的时区属于交互上下文；除非业务 contract 明确需要，不为展示目的额外持久化时区。
- 区分业务事件时间、应用 clock、数据库 statement time 和 transaction time；测试使用符合事实语义且可控制的时间来源。

## 错误、日志与请求 ID

- 已知失败转换为 `AppError` 子类，由统一 exception handler 映射 HTTP 状态和稳定错误码。
- 禁止在 Router、Service 或 Repository 中随意抛通用 `HTTPException` 来表达业务错误。
- 未处理异常对外只返回固定安全文案；不得泄漏 stack、SQL、连接串、内部 URL、headers 或原始 payload。
- 请求 ID 必须通过统一 middleware/handler 传播；外部 request ID 只能作为受约束的关联信息，不能成为身份或权限事实。
- 同一异常只在能决定恢复、retry 或终止语义的 owner 记录一次。
- 日志只记录必要的 request/user/resource id、状态、计数、duration 和 error type；禁止记录完整 PII、完整 query 或未经脱敏的 payload。
- 用户输入、邮箱、资源 ID 等高基数字段不得直接作为 metric label；telemetry 失败默认不能改变业务结果。

## Worker 扩展规则

- 当前项目没有 worker。未来新增普通轮询任务时，默认采用独立进程、单 worker、顺序 `while True` 和可单独测试的 `tick()`。
- 每个 tick 创建并释放自己的短 Session；长 worker 不长期持有 Session/transaction，也不把 ORM entity 跨 Session 传递。
- 默认不使用 `asyncio.gather()` 制造并发 worker。只有吞吐量证据明确，且已设计 claim、锁、幂等、lease 恢复和重复执行语义时才增加并发或多副本。
- 外部 IO、retry backoff 和长计算不得持有数据库事务；worker 异常由能够决定 retry/terminal 语义的 owner 记录一次。

## 测试要求

- Router/API contract test 从真实 FastAPI/ASGI 边界进入，断言状态码、精确公开字段、envelope、认证 header 和错误码。
- Repository、Session、constraint、事务和 migration 使用真实 PostgreSQL 集成测试。
- 权限测试同时覆盖允许与越权；分页覆盖稳定顺序、空结果和边界参数。
- 修复 bug 必须增加一个修复前会失败的最小回归测试。
- 测试独立于执行顺序，不依赖其他测试遗留的数据；测试凭据使用运行时随机值，不写死真实凭据。
- Schema/validator/serializer、实际存在的 contract factory/Presenter 和纯业务规则使用快速单元测试，覆盖边界值、alias、omitted/null/value 与失败路径。
- 不为通过测试删除断言、放宽公开 contract 或吞掉错误；测试替身只实现调用方真实依赖的 contract。

## 文件与凭据卫生

- 禁止提交 `.env`、`.coverage`、`app.db`、数据库 volume、缓存、虚拟环境、日志或任何 credential。
- `.env.example` 只能包含安全占位值和配置结构，不能包含真实用户名、密码、token、连接串或 Secret。
- SSH 私钥、公钥配置和 GitHub credential 属于开发主机，不得放进本仓库。
- 新增运行产物时同步更新 `.gitignore`，并在提交前检查暂存区。

## 完成检查

- [ ] Router、Service、Repository 职责未串层；Command、contract factory 与 Presenter 只在有真实边界需要时存在。
- [ ] 业务规则由 schema/Service 拥有，数据库只承担所有 writer 必须遵守的不变量。
- [ ] Settings/env 有真实消费者，新增或删除时同步更新配置、测试和文档。
- [ ] Session 和 transaction owner 唯一，没有隐藏 commit 或长事务。
- [ ] PUT 完整替换及 write-only 字段语义明确，ORM 更新没有字符串 key mass assignment。
- [ ] 分页排序、公开字段、camelCase/OAuth2 例外有 contract test。
- [ ] 没有无运行价值的 Field/route/OpenAPI description metadata。
- [ ] 认证身份来自可信 token，越权和失效路径已测试。
- [ ] 模型变更新增了 migration，并在 PostgreSQL 上验证。
- [ ] 时间使用 timezone-aware UTC 语义；新增 worker 时遵守短 Session、可测试 tick 和幂等规则。
- [ ] 已运行本次改动适用的最窄检查，并按风险扩大到 Ruff、format、mypy、pytest、pre-commit 或 Alembic；只报告实际运行的结果。
- [ ] 暂存区不含 Secret、`.env`、coverage、数据库文件、缓存或无关改动。
