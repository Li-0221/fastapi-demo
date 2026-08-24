# HTTP 请求生命周期

本文说明一次请求如何穿过当前 FastAPI 应用，以及 HTTP contract、业务用例和持久化边界各自由谁负责。主图以需要 Bearer Token 的普通 JSON 写接口为例；公开接口、OAuth2 登录和 `204 No Content` 的差异见文末。

## 成功路径

```text
Vue / 浏览器
   ↓ HTTP Request
FastAPI + RequestIdMiddleware
   ↓ 路由匹配、参数校验、依赖与认证
Router（传入已校验字段、调用 Service）
   ↓
Service（业务规则、授权、短 Session 和事务）
   ↓
Repository ↔ PostgreSQL
   ↓
Service 返回安全的 typed Data / Result / Facts，并关闭 Session
   ↓
Router 组装 ApiResponse
   ↓
FastAPI 序列化；Middleware 添加 X-Request-ID
   ↓ HTTP Response
Vue / 浏览器
```

请求进入时，[`RequestIdMiddleware`](../src/app/middleware.py) 为请求生成关联 ID。响应返回时，同一个 Middleware 把该 ID 写入 `X-Request-ID` header。应用在 [`main.py`](../src/app/main.py) 注册 Middleware、异常处理器和 API Router。

## 认证子链路

需要 `CurrentUser` 的接口会在进入 Router Handler 前执行认证依赖：

```text
Authorization: Bearer <token>
   ↓
OAuth2PasswordBearer（提取 token）
   ↓
AuthService（验证 JWT claims）
   ↓ 打开只读短 Session
UserRepository（按 token subject 查询用户）
   ↓
检查用户存在且处于 active 状态
   ↓
UserData（可信 CurrentUser / actor）
   ↓
Router Handler → Service
```

认证依赖只负责建立可信身份。管理员角色、资源归属和具体操作是否允许，仍由拥有业务事实的 Service 判断。相关装配位于 [`dependencies/auth.py`](../src/app/dependencies/auth.py)、[`dependencies/user.py`](../src/app/dependencies/user.py) 和 [`dependencies/database.py`](../src/app/dependencies/database.py)。

## 各边界的职责

| 边界 | 当前职责 | 不应负责 |
| --- | --- | --- |
| Middleware | request ID 等所有请求共享的 HTTP 横切能力 | 业务授权、数据库事务 |
| Dependency | 参数解析、认证、装配 Manager 和 Service | 资源授权、业务状态变更 |
| Request Schema | HTTP 入站 shape、camelCase alias 和输入校验 | 数据库写入、业务状态判断 |
| Router | 调用 Service，组装 HTTP response | ORM 查询、事务和业务规则 |
| Service 输入 | 简单用例使用明确关键字参数；复杂用例可使用 Command | HTTP alias、裸 dict |
| Service | 用例编排、业务校验、授权、Session 和 commit/rollback | HTTP envelope、公开字段展示 |
| Repository | 查询、排序、锁、flush 和持久化细节 | 角色判断、HTTP response |
| Data / Result / Facts | 在 Session 关闭前收窄 ORM，表达安全输出或内部事实 | 暴露 ORM 生命周期 |
| Presenter / 转换函数 | 内部结果与公开 Data 不同时做 allowlist 映射 | 数据库访问、权限判断和状态变更 |
| Response Schema | 定义公开字段、alias 和 envelope | 反向承载内部或数据库模型 |

具体实现可从 [`api/routes/users.py`](../src/app/api/routes/users.py) 依次追踪到 [`services/user.py`](../src/app/services/user.py) 和 [`repositories/user.py`](../src/app/repositories/user.py)。

## Request Schema 与 Service 输入

Request Schema 回答“客户端按 HTTP contract 提交了什么”。当用例输入与它一致时，Router 直接把已校验字段作为关键字参数传给 Service，不再复制一个同构 Command。

```text
HTTP JSON
   ↓
UserCreateRequest（Pydantic、camelCase、输入校验）
   ↓
UserService.create_user（明确关键字参数）
   ↓
UserRecordCreate（规范化邮箱、密码哈希等持久化输入）
```

Command 不是 FastAPI 的要求，也不代表项目实现了完整 CQRS。它在 HTTP/CLI/worker 多入口、不同信任级别、PATCH 三态或参数组需要独立演进时很有价值，此时应由 Service 拥有 Command。当前用户写入只需要明确的 typed 参数；创建超级管理员的 CLI 与 Router 复用同一个 Service 方法。

认证链路仍保留 `LoginUserFacts` 和 `AccessTokenResult`，因为它们分别拥有密码哈希的短生命周期以及 OAuth2 token 结果语义，并不是对 HTTP schema 的一比一复制。

## 异常路径

```text
任意请求阶段发生异常
   ├─ Pydantic / FastAPI 参数校验失败 → 422 VALIDATION_ERROR
   ├─ 已知 AppError                   → 稳定的 4xx error code
   ├─ 路由或 HTTP method 错误         → 404 / 405 HTTP_ERROR
   └─ 未处理异常                      → 500 INTERNAL_ERROR
   ↓
Exception Handler
   ↓
ErrorResponse + X-Request-ID
   ↓ HTTP Response
Vue / 浏览器
```

统一转换位于 [`exception_handlers.py`](../src/app/exception_handlers.py)。异常响应不会暴露 stack、SQL、内部 URL、headers 或原始 payload。已知业务异常由 Service 抛出并原样交给统一 handler，不在 Router 重复包装。

## 接口差异

- 公开注册不解析 `CurrentUser`，其余写入链路相同。
- OAuth2 登录接收 form data，并返回标准 `access_token`、`token_type`、`expires_in`，不使用普通 `ApiResponse` envelope。
- `204 No Content` 直接返回空 `Response`，不经过 Data 转换或 JSON envelope。
- 读取接口没有写事务；Service 仍拥有短 Session 的创建和关闭。
- 应用 lifespan 拥有数据库 Engine，并在进程关闭时释放连接池；它不属于单次请求链路。
