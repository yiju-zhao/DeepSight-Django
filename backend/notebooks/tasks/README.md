# Notebooks Tasks Refactoring

## Overview

The `notebooks/tasks.py` file (1373 lines) has been refactored into a modular structure for better maintainability and organization.

## New Structure

```
notebooks/tasks/
├── __init__.py              # Re-exports all tasks for backward compatibility ✅
├── README.md                # This file - migration guide ✅
├── _helpers.py              # Shared helper functions ✅
├── maintenance_tasks.py     # Cleanup and health check tasks ✅
├── ragflow_tasks.py         # RAGFlow integration tasks ✅
└── processing_tasks.py      # URL/file processing tasks ✅
```

## Migration Status

### ✅ Completed (4/4 modules - 100%)

#### 1. `_helpers.py` (完成)
Shared helper functions extracted from original tasks.py:
- `_validate_task_inputs()` - Input validation
- `_get_notebook_and_user()` - Fetch notebook and user objects
- `_get_or_create_knowledge_item()` - KB item management
- `_update_batch_item_status()` - Batch job item status updates
- `_check_batch_completion()` - Batch job completion checking
- `_handle_task_completion()` - Success handler with SSE
- `_handle_task_error()` - Error handler with SSE

#### 2. `maintenance_tasks.py` (完成)
Maintenance and monitoring tasks:
- `cleanup_old_batch_jobs` - Clean up batch jobs older than 7 days
- `test_caption_generation_task` - Testing task for caption generation
- `health_check_task` - Celery worker health check

#### 3. `ragflow_tasks.py` (完成)
RAGFlow integration tasks:
- `upload_to_ragflow_task` - Upload processed documents to RAGFlow
  - Validates KB item and notebook
  - Retrieves file from MinIO storage
  - Uploads to RAGFlow dataset
  - Triggers parsing and schedules status check

- `check_ragflow_status_task` - Poll RAGFlow processing status
  - Linear polling with 15s intervals
  - Max 120 retries (30 minutes timeout)
  - Publishes SSE events on completion/failure
  - Auto-retries on transient errors

#### 4. `processing_tasks.py` (完成)
8 个 URL/文件处理任务已迁移：

**解析任务 (Parse tasks)** - 从原始 tasks.py 提取：
- `parse_url_task` (line 360-456)
  - 基础 URL 解析
  - 创建 KB item
  - 使用 URLExtractor 处理

- `parse_url_with_media_task` (line 458-560)
  - URL 解析 + 媒体提取
  - 处理图片和视频
  - 生成字幕

- `parse_document_url_task` (line 562-662)
  - 文档 URL 解析
  - 支持 PDF, DOCX 等格式
  - 下载并处理文档

**处理任务 (Process tasks)** - 从原始 tasks.py 提取：
- `process_url_task` (line 771-860)
  - 完整 URL 处理流程
  - SSE 事件发布
  - 批处理支持

- `process_url_media_task` (line 863-943)
  - URL + 媒体处理
  - 图片提取和存储
  - 视频处理

- `process_url_document_task` (line 945-1025)
  - 文档 URL 完整处理
  - 文件下载和转换
  - MinIO 存储

- `process_file_upload_task` (line 1027-1134)
  - 文件上传处理
  - 支持多种格式
  - 转 Markdown

- `generate_image_captions_task` (line 1136-1194)
  - 图片标题生成
  - 使用 AI 模型
  - 更新 KB item 元数据

## ✅ 迁移已完成！

所有模块已成功迁移：
- ✅ `_helpers.py` - 7个辅助函数
- ✅ `maintenance_tasks.py` - 3个维护任务
- ✅ `ragflow_tasks.py` - 2个 RAGFlow 任务
- ✅ `processing_tasks.py` - 8个处理任务
- ✅ `__init__.py` - 完整的导入和导出

**特殊说明**：`processing_tasks.py` 包含本地版本的 `_handle_task_completion` 和 `_handle_task_error`，这些版本包含了 RAGFlow 链接和字幕生成调度等特定于处理任务的逻辑。

## Backward Compatibility（向后兼容）

`__init__.py` 确保所有现有导入继续工作：

```python
# 旧方式（仍然有效）
from notebooks.tasks import cleanup_old_batch_jobs
from notebooks.tasks import upload_to_ragflow_task
from notebooks.tasks import process_url_task

# 新方式（也有效）
from notebooks.tasks.maintenance_tasks import cleanup_old_batch_jobs
from notebooks.tasks.ragflow_tasks import upload_to_ragflow_task
from notebooks.tasks.processing_tasks import process_url_task
```

当前 `__init__.py` 状态：
- ✅ 从 `_helpers.py` 导入辅助函数
- ✅ 从 `maintenance_tasks.py` 导入维护任务
- ✅ 从 `ragflow_tasks.py` 导入 RAGFlow 任务
- ✅ 从 `processing_tasks.py` 导入处理任务

## Benefits（优势）

1. **更好的组织**: 按功能分组任务
2. **更易测试**: 较小、专注的模块更容易测试
3. **改进可维护性**: 一个类别的更改不影响其他类别
4. **更清晰的依赖**: 每个模块只导入所需内容
5. **向后兼容**: 对现有代码无破坏性更改
6. **减少合并冲突**: 团队成员可以在不同模块上工作
7. **更好的代码审查**: 更小的 PR，更容易审查

## Testing（测试）

### 当前已完成模块的测试

```bash
# 1. 启动 Celery worker
cd backend
celery -A backend worker -l info

# 2. 验证任务已注册
celery -A backend inspect registered | grep -E "(cleanup|health_check|upload_to_ragflow|check_ragflow)"

# 3. 测试维护任务
python manage.py shell
>>> from notebooks.tasks import health_check_task
>>> result = health_check_task.delay()
>>> result.get()

# 4. 测试 RAGFlow 任务（需要真实 KB item）
>>> from notebooks.tasks import upload_to_ragflow_task
>>> result = upload_to_ragflow_task.delay("kb_item_id_here")
>>> result.get()
```

### 完成 processing_tasks.py 后的完整测试

```bash
# 测试所有任务类型
cd backend
python manage.py shell

# 测试文件上传处理
>>> from notebooks.tasks import process_file_upload_task
>>> result = process_file_upload_task.delay(...)

# 测试 URL 处理
>>> from notebooks.tasks import process_url_task
>>> result = process_url_task.delay(url="https://example.com", ...)

# 验证批处理功能
>>> from notebooks.tasks import _check_batch_completion
>>> _check_batch_completion(batch_job_id)
```

## Next Steps（下一步）

### ✅ 已完成的工作
1. ✅ 创建 `_helpers.py` 和辅助函数
2. ✅ 创建 `maintenance_tasks.py` 和维护任务
3. ✅ 创建 `ragflow_tasks.py` 和 RAGFlow 任务
4. ✅ 创建 `processing_tasks.py` 和处理任务
5. ✅ 更新 `__init__.py` 使用所有新模块
6. ✅ 完整的文档和迁移指南

### 推荐的后续步骤
1. **测试验证** - 启动 Celery worker 并验证所有任务正常工作
2. **标记原始文件** - 在原始 `tasks.py` 顶部添加弃用警告
3. **更新文档** - 更新项目文档以引用新的模块结构
4. **添加单元测试** - 为每个模块添加单元测试
5. **考虑移除原始文件** - 在确认一切正常后，可以删除原始 `tasks.py`

### 可选的优化
- 为每个模块添加更完整的类型提示
- 考虑进一步拆分 `processing_tasks.py`（目前约800行）
- 添加更详细的日志记录
- 优化错误处理和重试策略

## Important Notes（重要说明）

- **任务名称和签名不变**: 所有现有代码无需修改
- **Celery 路由无需更改**: `backend/celery.py` 中的队列路由保持不变
- **`@shared_task` 装饰器**: 确保任务正确注册到 Celery
- **辅助函数前缀**: `_` 前缀表示内部函数，不应直接导入使用
- **原始文件保留**: 在确认所有功能正常前，保留 `tasks.py`
- **渐进迁移**: 可以逐步迁移，不需要一次完成所有任务

## Rollback Plan（回滚计划）

如果新结构出现问题：

1. **临时回滚**:
```python
# 在 __init__.py 中恢复从原始 tasks.py 导入所有任务
from ..tasks import *
```

2. **永久回滚**:
```bash
# 删除 tasks/ 目录
rm -rf backend/notebooks/tasks/

# 恢复使用原始 tasks.py
# 所有导入自动恢复正常
```

## Contact & Support（联系和支持）

如果在迁移过程中遇到问题：
1. 检查 Celery worker 日志
2. 验证任务注册: `celery -A backend inspect registered`
3. 检查导入错误: `python manage.py check`
4. 查看本 README 的测试部分
