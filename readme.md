# vLLM 负载均衡服务

一个基于 Flask 的 vLLM 节点管理和负载均衡服务，提供节点注册、状态查询和 JWT 认证功能。

## 功能特性

- 🔐 **JWT 身份认证** - 基于 JWT 的 API 访问控制
- 🖥️ **节点管理** - 完整的节点注册、更新、删除和查询功能
- 📊 **状态监控** - 实时查询节点状态信息和运行指标（运行任务数、等待任务数、KV缓存等）
- 🗄️ **Redis 存储** - 使用 Redis 存储节点数据
- 🌐 **CORS 支持** - 跨域资源共享支持
- 📝 **请求追踪** - 支持通过 X-Trace-ID 追踪请求

## 技术栈

- **框架**: Flask
- **认证**: PyJWT
- **存储**: Redis
- **CORS**: flask-cors

## 项目结构

```
nvllm/
├── api/                    # API 路由层
│   ├── __init__.py        # 路由注册
│   ├── node.py            # 节点相关 API
│   └── user.py            # 用户认证 API
├── service/               # 业务逻辑层
│   └── node.py            # 节点服务逻辑
├── model/                 # 数据模型
│   ├── base.py            # 响应模型
│   └── node.py            # 节点模型（包含 Node 和 NodeInfo）
├── middleware/            # 中间件
│   ├── auth.py            # JWT 认证中间件
│   └── redis_client.py    # Redis 客户端
├── dao/                   # 数据访问层（预留）
├── main.py                # 应用入口
└── requirements.txt       # 项目依赖
```

## 安装与配置

### 环境要求

- Python 3.8+
- Redis 服务器

### 安装步骤

1. **克隆项目**

```bash
git clone <repository-url>
cd nvllm
```

2. **创建虚拟环境**

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

3. **安装依赖**

```bash
pip install -r requirements.txt
```

4. **启动 Redis 服务**

```bash
# 确保 Redis 服务正在运行
redis-server
```

## 配置说明

### JWT 密钥配置

在 `middleware/auth.py` 中配置 JWT 密钥：

```python
SECRET_KEY = "your-jwt-secret-key"  # 请修改为安全的密钥
```

### Redis 配置

在 `middleware/redis_client.py` 中配置 Redis 连接信息（如需要）。

## 运行服务

```bash
python main.py
```

服务默认运行在 `http://127.0.0.1:5000`（调试模式）。

## API 文档

### 认证

#### 用户登录

**请求**
```http
POST /api/user/login
Content-Type: application/json

{
  "username": "admin"
}
```

**响应**
```json
{
  "message": "success",
  "status": "success",
  "code": 200,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  },
  "trace_id": "xxx"
}
```

**支持的用户名**: `admin`, `user`

### 节点管理

所有节点管理 API 都需要在请求头中携带 JWT Token：

```http
Authorization: Bearer <token>
X-Trace-ID: <trace_id>  # 可选，用于请求追踪
```

#### 注册节点

**请求**
```http
POST /api/node/node/register
Authorization: Bearer <token>
Content-Type: application/json

{
  "node_id": "node-001",
  "node_type": "worker",
  "node_address": "192.168.1.100",
  "node_port": 8000,
  "node_status": "online",
  "node_info": {
    "running": 0,
    "waiting": 0,
    "kv_cache": 0
  },
  "remark": "GPU节点1",
  "timeout": 60
}
```

**响应**
```json
{
  "message": "success",
  "status": "success",
  "code": 200,
  "data": {
    "node_id": "node-001",
    "node_type": "worker",
    "node_address": "192.168.1.100",
    "node_port": 8000,
    "node_status": "online",
    "node_info": {
      "running": 0,
      "waiting": 0,
      "kv_cache": 0
    },
    "remark": "GPU节点1",
    "timeout": 60,
    "create_time": "2024-01-01T00:00:00",
    "update_time": "2024-01-01T00:00:00"
  },
  "trace_id": "xxx"
}
```

**字段说明**:
- `node_id`: 节点唯一标识符（可选，不提供则自动生成 UUID）
- `node_type`: 节点类型，如 `master`、`worker`（默认: `master`）
- `node_address`: 节点 IP 地址（默认: `0.0.0.0`）
- `node_port`: 节点端口号（默认: `8000`）
- `node_status`: 节点状态，如 `online`、`offline`（默认: `offline`）
- `node_info`: 节点运行信息对象
  - `running`: 正在运行的任务数
  - `waiting`: 等待中的任务数
  - `kv_cache`: KV 缓存使用量
- `remark`: 备注信息（默认: `doc`）
- `timeout`: 超时时间（秒，默认: `60`）

#### 更新节点

**请求**
```http
PUT /api/node/node/update/<node_id>
Authorization: Bearer <token>
Content-Type: application/json

{
  "node_type": "worker",
  "node_address": "192.168.1.100",
  "node_port": 8001,
  "node_status": "online",
  "node_info": {
    "running": 2,
    "waiting": 1,
    "kv_cache": 1024
  },
  "remark": "GPU节点1-更新",
  "timeout": 120
}
```

**注意**: 所有字段都是可选的，只需提供需要更新的字段即可。

#### 删除节点

**请求**
```http
DELETE /api/node/node/delete/<node_id>
Authorization: Bearer <token>
```

#### 获取单个节点

**请求**
```http
GET /api/node/node/get_node/<node_id>
Authorization: Bearer <token>
```

**响应**
```json
{
  "message": "success",
  "status": "success",
  "code": 200,
  "data": {
    "node_id": "node-001",
    "node_type": "worker",
    "node_address": "192.168.1.100",
    "node_port": 8000,
    "node_status": "online",
    "node_info": {
      "running": 0,
      "waiting": 0,
      "kv_cache": 0
    },
    "remark": "GPU节点1",
    "timeout": 60,
    "create_time": "2024-01-01T00:00:00",
    "update_time": "2024-01-01T00:00:00"
  },
  "trace_id": "xxx"
}
```

#### 获取节点状态

**请求**
```http
GET /api/node/node/status/<node_id>
Authorization: Bearer <token>
```

**响应**
```json
{
  "message": "success",
  "status": "success",
  "code": 200,
  "data": {
    "node_id": "node-001",
    "node_type": "worker",
    "node_address": "192.168.1.100",
    "node_port": 8000,
    "node_status": "online",
    "node_info": {
      "running": 2,
      "waiting": 1,
      "kv_cache": 1024
    },
    "remark": "GPU节点1",
    "timeout": 60,
    "create_time": "2024-01-01T00:00:00",
    "update_time": "2024-01-01T00:00:00"
  },
  "trace_id": "xxx"
}
```

#### 获取所有节点

**请求**
```http
GET /api/node/node/all
Authorization: Bearer <token>
```

**响应**
```json
{
  "message": "success",
  "status": "success",
  "code": 200,
  "data": [
    {
      "node_id": "node-001",
      "node_type": "worker",
      "node_address": "192.168.1.100",
      "node_port": 8000,
      "node_status": "online",
      "node_info": {
        "running": 0,
        "waiting": 0,
        "kv_cache": 0
      },
      "remark": "GPU节点1",
      "timeout": 60,
      "create_time": "2024-01-01T00:00:00",
      "update_time": "2024-01-01T00:00:00"
    }
  ],
  "trace_id": "xxx"
}
```

## 错误响应格式

```json
{
  "message": "error",
  "status": "error",
  "code": 500,
  "error": "错误信息描述",
  "trace_id": "xxx"
}
```

## 响应代码说明

| 代码 | 说明 |
|------|------|
| 200 | 成功 |
| 401 | 未授权 |
| 403 | 禁止访问 |
| 404 | 资源不存在 |
| 405 | 方法不允许 |
| 500 | 服务器错误 |

## 开发

### 代码结构说明

- **api/**: 定义所有 API 端点，处理 HTTP 请求和响应
- **service/**: 包含业务逻辑，处理节点管理操作
- **model/**: 数据模型定义
  - `Response`: 统一响应格式模型
  - `Node`: 节点模型，包含节点基本信息和运行状态
  - `NodeInfo`: 节点运行信息模型（运行任务数、等待任务数、KV缓存）
- **middleware/**: 中间件，包括认证和 Redis 客户端

### 数据模型

#### Node 模型

节点模型包含以下字段：

| 字段 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| node_id | string | 节点唯一标识符 | 自动生成 UUID |
| node_type | string | 节点类型 | `master` |
| node_address | string | 节点 IP 地址 | `0.0.0.0` |
| node_port | int | 节点端口号 | `8000` |
| node_status | string | 节点状态 | `offline` |
| node_info | NodeInfo | 节点运行信息 | 空对象 |
| remark | string | 备注信息 | `doc` |
| timeout | int | 超时时间（秒） | `60` |
| create_time | datetime | 创建时间 | 当前时间 |
| update_time | datetime | 更新时间 | 当前时间 |

#### NodeInfo 模型

节点运行信息模型包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| running | int | 正在运行的任务数 |
| waiting | int | 等待中的任务数 |
| kv_cache | int | KV 缓存使用量 |

### 测试

运行测试脚本：

```bash
./test/test.sh
```

## 许可证

本项目采用 [MIT License](LICENSE) 许可证。

## 贡献

欢迎提交 Issue 和 Pull Request！
