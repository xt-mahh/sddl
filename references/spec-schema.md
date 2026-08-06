# Spec Schema（五层结构）

> `/sddl:spec` 生成 spec 时使用的完整结构定义。含字段说明 + 完整示例。

## 分层总览

| 层 | 内容 | 机器可消费性 | 检查方法 |
|----|------|------------|---------|
| L1 接口契约 | 函数签名、参数、返回、错误类型 | 完全 | 静态类型检查 / AST 对比 |
| L2 数据模型 | JSON Schema / 类型定义 | 完全 | Schema 验证器 |
| L3 行为描述 | GWT 场景 + 优先级 | 半（结构可解析） | 测试生成 + Checklist 语义检查 |
| L4 边界条件 | 显式枚举的极端情况 + 优先级 | 半 | 专项测试 + Checklist |
| L5 质量约束 | 性能/安全/可观测性 | 弱 | 翻译为可执行规则；性能类标注 env |

## 字段结构

```yaml
meta:
  id: "auth-service"            # 必填：唯一标识
  version: "0.1.0"              # 必填：语义化版本
  domain: "auth"                # 必填：领域名（= 目录名）
  status: "reviewing"           # interviewing | drafting | reviewing | frozen | evolved
  dependencies: ["user-model@>=1.0"]   # 可选：依赖的其他 spec

non_goals:                      # 非目标：防 scope creep，checker 可检测越界
  - "本服务不负责用户注册"

decision_points:                # 决策点登记（形成 Loop 阶段 3 的输入）
  - id: "DP-001"
    topic: "token 有效期"
    default: "7 天"
    alternatives: ["1 天", "30 天", "7 天"]
    rationale: "平衡安全与体验"
    category: "contract"        # contract | behavior | constraint | implementation
    requires_confirmation: true
    status: "pending"           # pending | confirmed | modified | delegated

interfaces:                     # L1 接口契约
  - name: "authenticate"        # 必填：接口名
    signature:                  # 必填：签名
      params:                   # 参数列表
        - { name: "credentials", type: "Credentials", required: true }
      returns: { type: "AuthResult" }
    errors: ["InvalidCredentialsError"]   # 必填：错误类型枚举（引用错误类型需在 behaviors 或独立定义）

data_models:                    # L2 数据模型（JSON Schema）
  - name: "Credentials"
    schema:
      type: "object"
      properties:
        email: { type: "string", format: "email" }
        password: { type: "string", minLength: 8 }
      required: ["email", "password"]

behaviors:                      # L3 行为描述（GWT + 优先级）
  - id: "B001"                  # 必填：唯一编号
    interface: "authenticate"   # 必填：引用 L1 接口
    priority: "must"            # must | should | could | wont
    scenario: "valid credentials"
    given: "用户存在且密码匹配"
    when: "调用 authenticate(valid credentials)"
    then:                       # 必填：可断言的结果（引用决策点: "expires_in 按 DP-001"）
      - "返回 AuthResult，包含有效的 access_token"
      - "expires_in >= 300"
    acceptance: true            # 标记为验收标准（C1 检查对象）

boundaries:                     # L4 边界条件
  - condition: "数据库连接断开"
    expectation: "抛出 ServiceUnavailableError，不产生部分写入"
    priority: "must"

quality_constraints:            # L5 质量约束
  performance:
    - metric: "P99 latency"
      threshold: "500ms"
      scope: "authenticate"
      verification: "env"       # env = 环境验证，不进 loop
      priority: "should"
  security:
    - "密码不以明文存储或记录到日志"
  observability:
    - "每次 authenticate 调用记录 audit log（不含密码）"
```

## 字段必填性

| 字段 | 必填 | 说明 |
|------|------|------|
| meta.id / version / domain / status | ✅ | 基础元数据 |
| meta.dependencies | 条件 | 有跨组件依赖时 |
| non_goals | 建议 | 防 scope creep |
| decision_points | ✅ | 形成 Loop 必需（无决策点也要有记录） |
| interfaces[].name / signature / errors | ✅ | L1 完整性 |
| data_models[].name / schema | ✅ | L2 完整性 |
| behaviors[].id / interface / priority / given / when / then | ✅ | L3 完整性 |
| boundaries[].condition / expectation | ✅ | L4 |
| quality_constraints | 建议 | L5（无则写 `quality_constraints: {}`） |

## 优先级语义

| 优先级 | 收敛角色 |
|--------|---------|
| must | 硬性，未覆盖**阻塞**收敛 |
| should | 软性，未覆盖不阻塞，进风险清单 |
| could | 不阻塞，仅记录 |
| wont | 显式排除（等价 non_goals） |

## GWT 写作规范

- **GIVEN**：可构造的前置条件（"用户存在" ✅ / "天气好" ❌）
- **WHEN**：明确的操作（"调用 authenticate(valid)" ✅ / "系统运行中" ❌）
- **THEN**：可断言的结果（"返回 AuthResult 且 HTTP 200" ✅ / "返回成功" ❌）
- THEN 禁止模糊词：成功/正常/正确/尽快/快速/高效/友好/合理/适当/必要时/等/其他/相关/相应/尽可能/大概/大约/左右/一些/若干/部分/某些

## 跨组件标记

```yaml
behaviors:
  - id: "B010"
    cross_component: true      # 跨组件行为：生成集成测试，顶层 loop 验证
    depends_on: ["payment-service"]
```

## 完整示例（auth 服务）

见附录 B（v1.1 方案的 auth 示例）——生成 spec 时以此为质量参照：接口有签名有错误、模型有 schema、行为有 GWT 且 THEN 可断言、边界有优先级、质量约束标注 verification。
