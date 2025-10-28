# Celery Task Discovery Fix

## 问题诊断

### 症状
- 上传文件后无法触发 Celery 任务处理
- `process_file_upload_task.delay()` 调用失败或任务未执行

### 根本原因
**这是由于 tasks 重构导致的，而不是 drf-spectacular 迁移！**

在重构中，我们将：
```
notebooks/tasks.py  →  notebooks/tasks/__init__.py
                       notebooks/tasks/processing_tasks.py
                       notebooks/tasks/ragflow_tasks.py
                       notebooks/tasks/maintenance_tasks.py
```

**Celery 的问题**：
1. `app.autodiscover_tasks()` 默认只查找名为 `tasks.py` 的**文件**
2. 它不会自动识别 `tasks/` **包**（目录结构）
3. 虽然 Python 导入 `from notebooks.tasks import xxx` 可以工作（因为 `__init__.py`），但 Celery 的任务注册机制需要显式配置

## 解决方案

### 1. 显式包含任务模块（✅ 已修复）

在 `backend/backend/celery.py` 中添加：

```python
# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Explicitly include notebooks tasks package modules (after refactoring to package structure)
app.autodiscover_tasks(
    [
        "notebooks.tasks.processing_tasks",
        "notebooks.tasks.ragflow_tasks",
        "notebooks.tasks.maintenance_tasks",
    ]
)
```

### 2. 更新任务路由配置（✅ 已修复）

任务的完整名称已改变：
- **旧名称**: `notebooks.tasks.process_file_upload_task`
- **新名称**: `notebooks.tasks.processing_tasks.process_file_upload_task`

更新 `task_routes` 配置：

```python
task_routes={
    # Processing tasks (updated paths)
    "notebooks.tasks.processing_tasks.parse_url_task": {"queue": "notebook_processing"},
    "notebooks.tasks.processing_tasks.parse_url_with_media_task": {"queue": "notebook_processing"},
    "notebooks.tasks.processing_tasks.parse_document_url_task": {"queue": "notebook_processing"},
    "notebooks.tasks.processing_tasks.process_url_task": {"queue": "notebook_processing"},
    "notebooks.tasks.processing_tasks.process_url_media_task": {"queue": "notebook_processing"},
    "notebooks.tasks.processing_tasks.process_url_document_task": {"queue": "notebook_processing"},
    "notebooks.tasks.processing_tasks.process_file_upload_task": {"queue": "notebook_processing"},
    "notebooks.tasks.processing_tasks.generate_image_captions_task": {"queue": "notebook_processing"},

    # RAGFlow tasks (updated paths)
    "notebooks.tasks.ragflow_tasks.upload_to_ragflow_task": {"queue": "notebook_processing"},
    "notebooks.tasks.ragflow_tasks.check_ragflow_status_task": {"queue": "notebook_processing"},

    # Maintenance tasks (updated paths)
    "notebooks.tasks.maintenance_tasks.test_caption_generation_task": {"queue": "notebook_processing"},
    "notebooks.tasks.maintenance_tasks.cleanup_old_batch_jobs": {"queue": "maintenance"},
}
```

## 验证步骤

### 1. 重启 Celery Worker

```bash
cd backend
celery -A backend worker -l info
```

### 2. 检查任务注册

启动后，查看日志中的任务列表：
```
[tasks]
  . notebooks.tasks.processing_tasks.process_file_upload_task
  . notebooks.tasks.ragflow_tasks.upload_to_ragflow_task
  ...
```

### 3. 使用 Celery inspect 验证

```bash
# 查看已注册的任务
celery -A backend inspect registered

# 应该能看到：
# - notebooks.tasks.processing_tasks.process_file_upload_task
# - notebooks.tasks.ragflow_tasks.upload_to_ragflow_task
# 等等
```

### 4. 测试文件上传

1. 启动 Django 开发服务器
2. 启动 Celery worker
3. 上传一个文件
4. 检查 Celery worker 日志，应该能看到任务被执行

## 为什么 Python 导入可以工作但 Celery 发现不了？

**Python 导入层面**：
```python
# 这两个是等价的：
from notebooks.tasks import process_file_upload_task  # 从 tasks/__init__.py 导入
from notebooks.tasks.processing_tasks import process_file_upload_task  # 直接导入
```

**Celery 任务发现层面**：
- Celery 使用文件系统扫描来发现任务
- `autodiscover_tasks()` 查找 `app_name/tasks.py` 文件
- 不会自动查找 `app_name/tasks/` 包中的子模块
- 需要显式告诉它去哪里找

## 关键点总结

✅ **已修复的内容**：
1. Celery 配置中添加了显式的任务模块发现
2. 更新了所有任务路由配置中的任务名称
3. 保持了向后兼容性（Python 导入仍然可以使用旧路径）

⚠️ **重要提醒**：
- **必须重启 Celery worker** 才能使更改生效
- 如果使用 Celery Beat，也需要重启
- 检查任务路由是否正确，确保任务进入正确的队列

## 相关文件

- `backend/backend/celery.py` - Celery 配置（已更新）
- `backend/notebooks/tasks/__init__.py` - 任务包入口（向后兼容导出）
- `backend/notebooks/tasks/processing_tasks.py` - 处理任务
- `backend/notebooks/tasks/ragflow_tasks.py` - RAGFlow 任务
- `backend/notebooks/tasks/maintenance_tasks.py` - 维护任务

## 参考

- [Celery Documentation - Application](https://docs.celeryq.dev/en/stable/userguide/application.html)
- [Celery Documentation - Task Names](https://docs.celeryq.dev/en/stable/userguide/tasks.html#task-names)
