# FastAPI 当前最需要复习的 5 个知识点

## 1. 事务：`flush / commit / rollback / refresh`

这是目前最需要彻底区分的一组概念。

### `flush`

```python
session.flush()
```

作用：

> 把当前 ORM 变更真正发送给数据库执行 SQL，但不提交事务。

例如：

```python
user = User(email="a@test.com")

session.add(user)
session.flush()

print(user.id)
```

如果 `id` 是数据库自增主键，`flush()` 后通常已经能拿到：

```python
user.id
```

因为：

```text
add
↓
flush
↓
执行 INSERT
↓
数据库生成 id
↓
SQLAlchemy 拿到 id
```

但此时事务还没提交，所以仍然可以：

```python
session.rollback()
```

撤销操作。

---

### `commit`

```python
session.commit()
```

可以粗略理解为：

```text
flush
+
提交事务
```

事务一旦成功 commit，这一批数据库修改才算正式完成。

核心区别：

```text
flush
→ SQL 已执行
→ 事务还没结束

commit
→ SQL 已执行
→ 事务正式提交
```

---

### `rollback`

如果：

```python
session.commit()
```

或：

```python
session.flush()
```

发生异常，通常需要：

```python
session.rollback()
```

例如：

```python
try:
    session.commit()
except Exception:
    session.rollback()
    raise
```

原因不只是“撤销数据”。

SQLAlchemy 在数据库异常后，当前 Session 的事务可能进入失败状态。

如果不 rollback，后续继续使用这个 Session 可能继续报错。

可以理解为：

```text
数据库操作失败
↓
当前事务进入失败状态
↓
rollback
↓
Session 恢复可用
```

---

### `refresh`

```python
session.refresh(user)
```

不是“验证数据”。

而是：

> 重新从数据库读取当前对象的数据。

例如数据库自动生成：

```text
id
created_at
updated_at
默认值
Trigger 生成字段
```

可以通过：

```python
session.refresh(user)
```

重新加载。

简单记忆：

```text
add
→ 加入 Session 管理

flush
→ SQL 发给数据库，但不提交

commit
→ 提交事务

rollback
→ 回滚事务

refresh
→ 从数据库重新读取对象
```

---

## 2. 事务边界：Service 和 Repository

你之前比较容易混淆的是：

> 到底谁应该 `commit()`？

通常更推荐：

```text
Repository
→ 数据库操作

Service
→ 业务流程 + 事务边界
```

而不是每个 Repository 自己 commit。

例如注册用户：

```text
创建 User
创建 UserProfile
创建 Settings
```

Repository：

```python
def create_user(session, data):
    user = User(...)
    session.add(user)
    session.flush()
    return user
```

```python
def create_profile(session, user_id):
    ...
```

```python
def create_settings(session, user_id):
    ...
```

Service：

```python
def register_user(session, data):
    user = user_repo.create_user(session, data)

    profile_repo.create_profile(
        session,
        user.id,
    )

    settings_repo.create_settings(
        session,
        user.id,
    )

    session.commit()

    return user
```

如果最后一步失败：

```python
session.rollback()
```

那么整个注册业务都不会保存。

---

### 为什么 Repository 不建议各自 commit？

错误示例：

```text
user_repo.create()
↓
commit

profile_repo.create()
↓
commit

settings_repo.create()
↓
失败
```

这时候：

```text
User        已存在
Profile     已存在
Settings    不存在
```

业务数据就不完整了。

所以更合理的是：

```text
多个 Repository 操作
↓
共同组成一个业务事务
↓
Service 最后统一 commit
```

### 重点记忆

```text
Repository
→ 怎么操作数据库

Service
→ 这组操作什么时候一起成功
```

---

## 3. SQLAlchemy `Session`

`Session` 不应该简单理解成：

```text
数据库连接
```

也不完全等于：

```text
事务
```

更适合把它理解为：

> ORM 的一次工作单元 / 数据库会话。

例如 FastAPI 经常：

```python
def get_db():
    with Session(engine) as session:
        yield session
```

然后：

```python
@app.get("/users")
def get_users(
    session: Session = Depends(get_db),
):
    ...
```

通常采用：

```text
一个 HTTP Request
=
一个 Session
```

---

### 为什么一个请求一个 Session？

主要是为了让不同请求的：

```text
ORM 状态
事务状态
对象缓存
数据库操作
```

彼此隔离。

例如：

```text
Request A
→ Session A

Request B
→ Session B
```

而不是：

```text
Request A ┐
Request B ├→ 同一个全局 Session
Request C ┘
```

后者在并发情况下很危险。

---

### Session 不等于 Connection

Session 需要执行 SQL 时，可以：

```text
Session
↓
从 Connection Pool 获取连接
↓
执行 SQL
↓
适当时候归还连接
```

所以：

```text
Session
≠
Connection
```

---

### `yield` 的意义

```python
def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
```

执行过程：

```text
创建 Session
↓
yield 给 Router / Service 使用
↓
请求执行完成
↓
继续执行 finally
↓
close Session
```

所以 `yield` 很适合管理：

```text
数据库 Session
文件
连接
锁
临时资源
```

---

## 4. PATCH 与 `exclude_unset=True`

这是写更新接口最重要的知识之一。

假设：

```python
class UserUpdate(BaseModel):
    name: str | None = None
    age: int | None = None
```

数据库：

```json
{
  "name": "Tom",
  "age": 18
}
```

请求：

```json
{
  "name": "Jack"
}
```

如果：

```python
data.model_dump()
```

可能得到：

```python
{
    "name": "Jack",
    "age": None,
}
```

如果直接拿去更新数据库，就可能错误地把：

```text
age = NULL
```

---

### PATCH 应该区分

```text
没传
```

和：

```text
明确传 null
```

这两件事完全不同。

所以通常：

```python
update_data = data.model_dump(
    exclude_unset=True
)
```

得到：

```python
{
    "name": "Jack"
}
```

只更新客户端真正传过来的字段。

---

### 明确传 `null`

如果请求：

```json
{
  "age": null
}
```

那么：

```python
data.model_dump(
    exclude_unset=True
)
```

会得到：

```python
{
    "age": None
}
```

这说明：

> 用户明确要求把 `age` 清空。

因此应该更新为数据库：

```text
NULL
```

---

### 不要随便用 `exclude_none=True`

如果：

```python
data.model_dump(
    exclude_none=True
)
```

那么：

```json
{
  "age": null
}
```

可能被直接过滤掉。

结果后端就无法知道：

> 用户到底是没传 age，还是主动想清空 age。

### 重点记忆

```text
exclude_unset=True
→ 排除“没传”的字段

exclude_none=True
→ 排除“值是 None”的字段
```

PATCH 通常更关心：

```python
exclude_unset=True
```

---

## 5. Pydantic Optional：`str | None = None`

这一点也非常容易混。

例如：

```python
email: str | None = None
```

要拆开看。

### `str | None`

表示：

> 值可以是 `str`，也可以是 `None`。

所以：

```json
{
  "email": null
}
```

合法。

---

### `= None`

表示：

> 这个字段有默认值，因此可以不传。

所以：

```json
{}
```

也合法。

---

### 两者结合

```python
email: str | None = None
```

表示下面三种都可以：

```json
{}
```

```json
{
  "email": null
}
```

```json
{
  "email": "a@test.com"
}
```

---

### 如果写成

```python
email: str | None
```

没有：

```python
= None
```

那么字段仍然是必填的。

也就是说：

```json
{}
```

不合法。

但：

```json
{
  "email": null
}
```

合法。

### 最重要的记忆方式

```text
| None
→ 这个字段能不能传 null

= None
→ 这个字段能不能不传
```

---

# 最后只记这 5 句话

```text
1. flush 发 SQL，但不提交事务；commit 才真正提交。

2. Repository 负责数据库操作，Service 通常负责事务边界。

3. Session 是 ORM 工作单元，不等于数据库连接。

4. PATCH 要区分“没传”和“传 null”，常用 exclude_unset=True。

5. | None 表示允许 null，= None 表示允许不传。
```
