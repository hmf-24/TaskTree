# 任务列表：钉钉Stream模式客户端

## 1. 配置管理

### 1.1 添加Stream模式配置项
- [ ] 在 `backend/app/core/config.py` 中添加配置项
  - `DINGTALK_CLIENT_ID: str`
  - `DINGTALK_CLIENT_SECRET: str`
  - `DINGTALK_STREAM_ENABLED: bool`
- [ ] 更新 `.env.example` 文件，添加配置示例
- [ ] 添加配置验证逻辑

## 2. Stream客户端实现

### 2.1 创建Stream客户端服务
- [ ] 创建 `backend/app/services/dingtalk_stream_client.py`
- [ ] 实现 `DingtalkStreamClient` 类
  - `__init__()`: 初始化客户端
  - `start()`: 启动客户端并建立连接
  - `stop()`: 停止客户端并关闭连接
  - `is_running()`: 检查运行状态

### 2.2 创建消息处理器
- [ ] 在 `dingtalk_stream_client.py` 中实现 `DingtalkMessageHandler` 类
  - `__init__()`: 初始化处理器
  - `handle_message()`: 处理钉钉消息
- [ ] 实现消息字段提取逻辑（`senderId`, `text.content`）
- [ ] 实现用户身份映射查询
- [ ] 集成频率限制检查
- [ ] 调用 `process_dingtalk_message` 处理消息

### 2.3 实现启动函数
- [ ] 实现 `start_dingtalk_stream_mode()` 函数
- [ ] 创建数据库会话工厂
- [ ] 初始化消息处理器
- [ ] 创建并启动Stream客户端
- [ ] 添加错误处理和日志记录

## 3. 生命周期集成

### 3.1 集成到FastAPI应用
- [ ] 修改 `backend/app/main.py` 的 `lifespan` 函数
- [ ] 在启动阶段调用 `start_dingtalk_stream_mode()`
- [ ] 在关闭阶段停止Stream客户端
- [ ] 将客户端引用保存到 `app.state`

### 3.2 添加配置检查
- [ ] 检查 `DINGTALK_STREAM_ENABLED` 配置
- [ ] 验证 `DINGTALK_CLIENT_ID` 和 `DINGTALK_CLIENT_SECRET` 非空
- [ ] 配置缺失时记录警告日志

## 4. 错误处理

### 4.1 实现错误处理逻辑
- [ ] 处理配置缺失错误
- [ ] 处理连接失败错误
- [ ] 处理消息处理异常
- [ ] 处理数据库连接失败

### 4.2 添加日志记录
- [ ] 启动成功日志
- [ ] 连接状态日志
- [ ] 消息接收日志
- [ ] 错误和异常日志
- [ ] 关闭日志

## 5. 测试

### 5.1 单元测试
- [ ] 创建 `backend/tests/test_dingtalk_stream_client.py`
- [ ] 测试 `DingtalkStreamClient` 初始化
- [ ] 测试 `DingtalkMessageHandler.handle_message()`
- [ ] 测试配置验证逻辑
- [ ] 测试错误处理逻辑

### 5.2 集成测试
- [ ] 创建 `backend/tests/test_dingtalk_stream_integration.py`
- [ ] 测试应用启动和关闭流程
- [ ] 测试消息接收和处理流程
- [ ] 测试用户绑定流程
- [ ] 测试频率限制

### 5.3 手动测试
- [ ] 配置测试环境（钉钉测试应用）
- [ ] 测试基本消息接收
- [ ] 测试任务更新流程
- [ ] 测试错误场景
- [ ] 测试连接恢复

## 6. 文档

### 6.1 更新技术文档
- [ ] 更新 `docs/技术/钉钉对接指南.md`
- [ ] 添加Stream模式配置说明
- [ ] 添加部署指南
- [ ] 添加故障排查指南

### 6.2 更新用户文档
- [ ] 更新 `docs/功能文档/03-钉钉智能助手.md`
- [ ] 说明Stream模式和Webhook模式的区别
- [ ] 添加配置步骤
- [ ] 添加常见问题解答

## 7. 部署准备

### 7.1 环境配置
- [ ] 准备生产环境配置模板
- [ ] 配置钉钉应用（Stream模式）
- [ ] 获取 `AppKey` 和 `AppSecret`

### 7.2 Docker支持
- [ ] 验证Docker环境下的运行
- [ ] 更新 `docker-compose.yml`（如需要）
- [ ] 测试容器化部署

## 8. 验收测试

### 8.1 功能验收
- [ ] 执行 AT1: 基本消息接收测试
- [ ] 执行 AT2: 用户绑定流程测试
- [ ] 执行 AT3: 任务更新测试
- [ ] 执行 AT4: 频率限制测试
- [ ] 执行 AT5: 连接恢复测试
- [ ] 执行 AT6: 应用关闭测试

### 8.2 性能验收
- [ ] 验证消息响应时间 < 200ms
- [ ] 验证用户查询时间 < 50ms
- [ ] 验证并发处理能力

### 8.3 安全验收
- [ ] 验证TLS加密
- [ ] 验证敏感信息不泄露
- [ ] 验证频率限制生效

## 9. 上线发布

### 9.1 代码审查
- [ ] 代码审查
- [ ] 安全审查
- [ ] 性能审查

### 9.2 发布准备
- [ ] 更新版本号
- [ ] 更新 CHANGELOG
- [ ] 准备发布说明

### 9.3 发布执行
- [ ] 部署到测试环境
- [ ] 测试环境验证
- [ ] 部署到生产环境
- [ ] 生产环境验证
- [ ] 监控运行状态
