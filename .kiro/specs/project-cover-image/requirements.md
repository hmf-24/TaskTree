# Requirements Document

## Introduction

项目封面图功能为 TaskTree 项目管理系统提供视觉识别能力。用户可以通过图标+颜色主题、上传自定义图片或使用 AI 生成图片三种方式为项目设置封面，增强项目列表的视觉区分度和用户体验。系统在创建项目时自动分配随机图标和颜色，用户可在创建时或后续编辑中修改封面。

## Glossary

- **Project_Cover_System**: 项目封面管理系统，负责封面图的存储、生成和展示
- **Icon_Theme**: 图标主题，由预设图标和颜色组合构成的默认封面方案
- **Cover_Image**: 封面图片，用户上传或 AI 生成的项目封面图片文件
- **MiniMax_API**: MiniMax 图片生成 API，用于 AI 生成项目封面图
- **Project_Modal**: 项目创建/编辑对话框，用户设置项目信息的界面
- **Project_List**: 项目列表页面，展示所有项目及其封面的界面
- **Storage_Service**: 存储服务，复用 TaskAttachment 的文件存储逻辑
- **Cover_Type**: 封面类型，包括 icon（图标主题）、upload（上传图片）、ai_generated（AI 生成）

## Requirements

### Requirement 1: 默认图标主题封面

**User Story:** 作为用户，我希望新建项目时自动获得一个视觉上有区分度的封面，这样我可以快速识别不同项目

#### Acceptance Criteria

1. WHEN 用户创建新项目，THE Project_Cover_System SHALL 自动分配一个随机图标和颜色组合
2. THE Project_Cover_System SHALL 支持至少 20 种预设图标（如文件夹、星星、火箭、灯泡、目标等）
3. THE Project_Cover_System SHALL 支持至少 12 种预设颜色（覆盖色相环主要色系）
4. THE Project_Cover_System SHALL 确保随机分配的图标和颜色组合具有良好的视觉对比度
5. THE Project_Cover_System SHALL 在数据库中存储封面类型（cover_type）、图标标识（icon_name）和颜色值（color_hex）
6. WHEN 项目使用图标主题封面，THE Project_List SHALL 在项目卡片上展示对应的图标和背景色
7. THE Project_Cover_System SHALL 允许用户在创建项目时手动选择图标和颜色组合

### Requirement 2: 创建时设置封面

**User Story:** 作为用户，我希望在创建项目时就能设置封面，这样可以一次性完成项目配置

#### Acceptance Criteria

1. WHEN 用户打开项目创建对话框，THE Project_Modal SHALL 展示封面设置区域
2. THE Project_Modal SHALL 提供三种封面设置方式的选项卡：图标主题、上传图片、AI 生成
3. THE Project_Modal SHALL 默认选中图标主题选项卡，并显示当前随机分配的图标和颜色
4. WHEN 用户选择图标主题选项卡，THE Project_Modal SHALL 展示图标选择器和颜色选择器
5. WHEN 用户选择上传图片选项卡，THE Project_Modal SHALL 展示文件上传组件
6. WHEN 用户选择 AI 生成选项卡，THE Project_Modal SHALL 展示提示词输入框和生成按钮
7. WHEN 用户提交创建项目表单，THE Project_Cover_System SHALL 保存用户选择的封面配置

### Requirement 3: 上传封面图片

**User Story:** 作为用户，我希望上传自己的图片作为项目封面，这样可以使用更个性化的视觉标识

#### Acceptance Criteria

1. THE Project_Cover_System SHALL 支持上传 JPG、JPEG、PNG、GIF、WEBP 格式的图片文件
2. THE Project_Cover_System SHALL 限制上传图片文件大小不超过 5MB
3. WHEN 用户选择上传图片，THE Project_Cover_System SHALL 验证文件类型和大小
4. IF 文件验证失败，THEN THE Project_Cover_System SHALL 显示具体的错误提示信息
5. WHEN 文件验证通过，THE Project_Cover_System SHALL 将图片保存到文件系统路径 `uploads/project_covers/{project_id}/`
6. THE Project_Cover_System SHALL 生成唯一文件名格式为 `{timestamp}_{uuid}_{original_filename}`
7. THE Project_Cover_System SHALL 在数据库中存储封面类型（cover_type='upload'）、文件路径（cover_image_path）和文件大小（cover_image_size）
8. WHEN 上传成功，THE Project_Modal SHALL 显示图片预览
9. THE Project_Cover_System SHALL 在前端对图片进行客户端压缩和裁剪（推荐尺寸 400x300px）
10. WHEN 用户更换封面图片，THE Project_Cover_System SHALL 删除旧的图片文件

### Requirement 4: AI 生成封面图片

**User Story:** 作为用户，我希望通过 AI 生成项目封面，这样可以快速获得符合项目主题的专业封面

#### Acceptance Criteria

1. WHEN 用户选择 AI 生成选项卡，THE Project_Modal SHALL 显示提示词输入框（支持中英文）
2. THE Project_Modal SHALL 提供提示词示例和最佳实践说明
3. WHEN 用户输入提示词并点击生成按钮，THE Project_Cover_System SHALL 调用 MiniMax_API 生成图片
4. THE Project_Cover_System SHALL 在生成过程中显示加载状态和进度提示
5. WHEN MiniMax_API 返回图片，THE Project_Cover_System SHALL 将图片保存到文件系统路径 `uploads/project_covers/{project_id}/`
6. THE Project_Cover_System SHALL 在数据库中存储封面类型（cover_type='ai_generated'）、文件路径（cover_image_path）、提示词（ai_prompt）
7. WHEN 生成成功，THE Project_Modal SHALL 显示生成的图片预览
8. IF MiniMax_API 调用失败，THEN THE Project_Cover_System SHALL 显示友好的错误提示并保持当前封面不变
9. THE Project_Cover_System SHALL 限制 AI 生成功能的调用频率（每用户每分钟最多 3 次）
10. THE Project_Cover_System SHALL 记录 AI 生成的调用日志（用户 ID、项目 ID、提示词、生成时间、结果状态）

### Requirement 5: 项目列表展示优化

**User Story:** 作为用户，我希望在项目列表中看到项目封面，这样可以快速识别和定位项目

#### Acceptance Criteria

1. WHEN 用户打开项目列表页面，THE Project_List SHALL 为每个项目展示封面
2. WHEN 项目使用图标主题封面，THE Project_List SHALL 展示图标和背景色
3. WHEN 项目使用上传或 AI 生成的图片封面，THE Project_List SHALL 展示封面图片
4. THE Project_List SHALL 确保封面图片按比例缩放并居中裁剪以适应卡片尺寸
5. THE Project_List SHALL 为封面图片添加加载占位符和加载失败的降级显示
6. WHEN 封面图片加载失败，THE Project_List SHALL 降级显示图标主题封面
7. THE Project_List SHALL 支持封面图片的懒加载以优化性能
8. THE Project_List SHALL 在项目卡片悬停时显示封面编辑入口（图标按钮）

### Requirement 6: 编辑项目封面

**User Story:** 作为项目所有者或管理员，我希望随时修改项目封面，这样可以根据项目进展调整视觉标识

#### Acceptance Criteria

1. WHEN 用户点击项目卡片的编辑封面按钮，THE Project_Modal SHALL 打开编辑模式并显示当前封面
2. THE Project_Modal SHALL 在编辑模式下提供与创建时相同的三种封面设置方式
3. WHEN 用户修改封面并保存，THE Project_Cover_System SHALL 更新数据库中的封面配置
4. WHEN 用户从图标主题切换到图片封面，THE Project_Cover_System SHALL 保留图标配置以便回退
5. WHEN 用户从图片封面切换到图标主题，THE Project_Cover_System SHALL 删除旧的图片文件
6. THE Project_Cover_System SHALL 验证用户权限（仅项目所有者和管理员可编辑封面）
7. IF 用户无编辑权限，THEN THE Project_Modal SHALL 隐藏编辑封面按钮
8. WHEN 封面更新成功，THE Project_List SHALL 立即刷新显示新封面

### Requirement 7: 封面图片存储管理

**User Story:** 作为系统管理员，我希望封面图片存储管理规范且高效，这样可以确保系统稳定性和可维护性

#### Acceptance Criteria

1. THE Storage_Service SHALL 复用 TaskAttachment 的文件存储逻辑和工具函数
2. THE Storage_Service SHALL 将封面图片存储在独立目录 `uploads/project_covers/{project_id}/`
3. THE Storage_Service SHALL 为每个上传的文件生成唯一文件名以避免冲突
4. THE Storage_Service SHALL 在项目删除时级联删除关联的封面图片文件
5. THE Storage_Service SHALL 提供封面图片的下载 API 端点 `GET /api/v1/projects/{project_id}/cover`
6. THE Storage_Service SHALL 为封面图片设置适当的缓存头（Cache-Control: max-age=86400）
7. THE Storage_Service SHALL 验证文件访问权限（项目成员可访问）
8. THE Storage_Service SHALL 记录文件操作日志（上传、删除、访问）

### Requirement 8: MiniMax API 集成

**User Story:** 作为开发者，我希望正确集成 MiniMax 图片生成 API，这样可以为用户提供稳定的 AI 生成功能

#### Acceptance Criteria

1. THE Project_Cover_System SHALL 使用 MiniMax 图片生成 API 端点 `https://api.minimax.chat/v1/text_to_image`
2. THE Project_Cover_System SHALL 从环境变量读取 API 密钥（MINIMAX_API_KEY）和 Group ID（MINIMAX_GROUP_ID）
3. WHEN 调用 MiniMax_API，THE Project_Cover_System SHALL 设置图片尺寸为 400x300px
4. THE Project_Cover_System SHALL 设置请求超时时间为 60 秒
5. THE Project_Cover_System SHALL 处理 API 调用的各种错误场景（网络错误、超时、API 限流、内容审核失败）
6. WHEN API 返回错误，THE Project_Cover_System SHALL 记录详细错误日志并返回用户友好的错误消息
7. THE Project_Cover_System SHALL 实现 API 调用的重试机制（最多重试 2 次，指数退避）
8. THE Project_Cover_System SHALL 验证 API 返回的图片数据完整性

### Requirement 9: 数据库模型扩展

**User Story:** 作为开发者，我希望数据库模型支持封面功能的所有需求，这样可以完整存储和查询封面数据

#### Acceptance Criteria

1. THE Project_Cover_System SHALL 在 Project 表中添加字段 `cover_type`（类型：String，可选值：icon/upload/ai_generated，默认：icon）
2. THE Project_Cover_System SHALL 在 Project 表中添加字段 `icon_name`（类型：String，可空，存储图标标识）
3. THE Project_Cover_System SHALL 在 Project 表中添加字段 `color_hex`（类型：String，可空，存储颜色值如 #FF5733）
4. THE Project_Cover_System SHALL 在 Project 表中添加字段 `cover_image_path`（类型：String，可空，存储图片文件路径）
5. THE Project_Cover_System SHALL 在 Project 表中添加字段 `cover_image_size`（类型：Integer，可空，存储图片文件大小字节数）
6. THE Project_Cover_System SHALL 在 Project 表中添加字段 `ai_prompt`（类型：Text，可空，存储 AI 生成的提示词）
7. THE Project_Cover_System SHALL 为 `cover_type` 字段创建索引以优化查询性能
8. THE Project_Cover_System SHALL 在数据库迁移脚本中为现有项目设置默认封面（随机图标和颜色）

### Requirement 10: API 端点设计

**User Story:** 作为前端开发者，我希望有清晰的 API 端点来管理项目封面，这样可以高效实现前端功能

#### Acceptance Criteria

1. THE Project_Cover_System SHALL 提供端点 `POST /api/v1/projects/{project_id}/cover/upload` 用于上传封面图片
2. THE Project_Cover_System SHALL 提供端点 `POST /api/v1/projects/{project_id}/cover/generate` 用于 AI 生成封面图片
3. THE Project_Cover_System SHALL 提供端点 `PUT /api/v1/projects/{project_id}/cover/icon` 用于更新图标主题封面
4. THE Project_Cover_System SHALL 提供端点 `GET /api/v1/projects/{project_id}/cover` 用于获取封面图片文件
5. THE Project_Cover_System SHALL 提供端点 `DELETE /api/v1/projects/{project_id}/cover` 用于删除封面图片（恢复为图标主题）
6. WHEN 调用上传或生成端点，THE Project_Cover_System SHALL 返回完整的封面配置信息
7. WHEN 调用获取端点，THE Project_Cover_System SHALL 返回图片文件流和适当的 Content-Type 头
8. THE Project_Cover_System SHALL 在所有端点中验证用户权限和项目存在性

### Requirement 11: 前端组件设计

**User Story:** 作为前端开发者，我希望有可复用的封面组件，这样可以在不同场景下一致地展示和编辑封面

#### Acceptance Criteria

1. THE Project_Cover_System SHALL 提供 `ProjectCoverDisplay` 组件用于展示项目封面
2. THE Project_Cover_System SHALL 提供 `ProjectCoverEditor` 组件用于编辑项目封面
3. THE ProjectCoverDisplay SHALL 支持三种封面类型的渲染（图标主题、上传图片、AI 生成图片）
4. THE ProjectCoverEditor SHALL 提供选项卡切换三种封面设置方式
5. THE ProjectCoverEditor SHALL 集成 Ant Design 的 Upload 组件用于文件上传
6. THE ProjectCoverEditor SHALL 提供图标选择器（网格布局展示所有可选图标）
7. THE ProjectCoverEditor SHALL 提供颜色选择器（使用 Ant Design ColorPicker 组件）
8. THE ProjectCoverEditor SHALL 在 AI 生成选项卡中提供提示词输入框和生成按钮
9. THE ProjectCoverEditor SHALL 显示实时预览当前选择的封面效果
10. THE Project_Cover_System SHALL 在 Project 类型定义中添加封面相关字段

### Requirement 12: 错误处理和用户反馈

**User Story:** 作为用户，我希望在封面操作失败时得到清晰的错误提示，这样可以知道如何解决问题

#### Acceptance Criteria

1. WHEN 文件类型不支持，THE Project_Cover_System SHALL 显示错误消息 "不支持的文件格式，请上传 JPG、PNG、GIF 或 WEBP 图片"
2. WHEN 文件大小超限，THE Project_Cover_System SHALL 显示错误消息 "文件大小超过 5MB 限制，请选择更小的图片"
3. WHEN 网络请求失败，THE Project_Cover_System SHALL 显示错误消息 "网络错误，请检查连接后重试"
4. WHEN MiniMax_API 调用失败，THE Project_Cover_System SHALL 显示错误消息 "AI 生成失败，请稍后重试或更换提示词"
5. WHEN 用户无编辑权限，THE Project_Cover_System SHALL 显示错误消息 "您没有权限编辑此项目封面"
6. WHEN 操作成功，THE Project_Cover_System SHALL 显示成功提示消息（如 "封面已更新"）
7. THE Project_Cover_System SHALL 在加载过程中显示加载指示器（Spinner 或进度条）
8. THE Project_Cover_System SHALL 在 AI 生成过程中显示预估等待时间（约 10-30 秒）

### Requirement 13: 性能优化

**User Story:** 作为用户，我希望封面功能响应迅速，这样可以获得流畅的使用体验

#### Acceptance Criteria

1. THE Project_List SHALL 使用虚拟滚动技术优化大量项目的渲染性能
2. THE Project_List SHALL 对封面图片实现懒加载（仅加载可视区域的图片）
3. THE Project_Cover_System SHALL 在前端对上传图片进行压缩（质量 80%，最大尺寸 400x300px）
4. THE Project_Cover_System SHALL 为封面图片生成缩略图（200x150px）用于列表展示
5. THE Storage_Service SHALL 为封面图片设置 CDN 缓存策略（如使用 CloudFlare 或 OSS）
6. THE Project_Cover_System SHALL 在数据库查询中使用索引优化封面数据的检索
7. WHEN 用户切换封面类型，THE Project_Modal SHALL 使用防抖技术避免频繁的 API 调用
8. THE Project_Cover_System SHALL 限制并发的 AI 生成请求数量（每用户最多 1 个并发请求）

### Requirement 14: 可访问性和国际化

**User Story:** 作为有特殊需求的用户，我希望封面功能具有良好的可访问性，这样我可以无障碍地使用该功能

#### Acceptance Criteria

1. THE ProjectCoverDisplay SHALL 为封面图片提供 alt 属性描述（如 "项目名称的封面图"）
2. THE ProjectCoverEditor SHALL 为所有交互元素提供键盘导航支持
3. THE ProjectCoverEditor SHALL 为图标选择器提供 ARIA 标签
4. THE Project_Cover_System SHALL 确保图标和背景色的对比度符合 WCAG AA 标准（对比度至少 4.5:1）
5. THE Project_Cover_System SHALL 支持中英文界面文本的国际化
6. THE Project_Cover_System SHALL 为屏幕阅读器提供适当的语义化标签
7. THE ProjectCoverEditor SHALL 在颜色选择器中提供颜色名称的文本标签

### Requirement 15: 测试和质量保证

**User Story:** 作为开发者，我希望封面功能有完善的测试覆盖，这样可以确保功能稳定可靠

#### Acceptance Criteria

1. THE Project_Cover_System SHALL 提供单元测试覆盖所有文件验证函数
2. THE Project_Cover_System SHALL 提供单元测试覆盖所有 API 端点
3. THE Project_Cover_System SHALL 提供集成测试覆盖完整的封面上传-展示-删除流程
4. THE Project_Cover_System SHALL 提供集成测试覆盖 MiniMax_API 调用和错误处理
5. THE Project_Cover_System SHALL 提供前端组件测试覆盖 ProjectCoverDisplay 和 ProjectCoverEditor
6. THE Project_Cover_System SHALL 提供端到端测试覆盖用户创建项目并设置封面的完整流程
7. THE Project_Cover_System SHALL 在 CI/CD 流程中自动运行所有测试
8. THE Project_Cover_System SHALL 确保测试覆盖率达到至少 80%
