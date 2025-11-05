# FOFA扫描功能模块

## 概述

FOFA扫描功能集成了 [FOFA](https://fofa.info) 网络空间搜索引擎，用于自动发现全球范围内的 Ollama 服务。

核心逻辑 100% 对齐 [Awesome-Ollama-Server](https://github.com/shibing624/Awesome-Ollama-Server) 的实现。

## 功能特性

- ✅ **FOFA API 集成**: 支持按国家搜索 Ollama 服务
- ✅ **HTML 解析**: 自动提取主机地址列表
- ✅ **批量创建端点**: 自动将发现的主机添加到系统
- ✅ **自动触发检测**: 可选自动对新端点进行性能测试
- ✅ **扫描历史**: 记录所有扫描活动和结果
- ✅ **管理员专用**: 仅管理员可访问（权限保护）

## API 端点

### 1. 启动扫描
```http
POST /api/v2/fofa/scan
```

请求体:
```json
{
  "country": "US",
  "custom_query": null,
  "auto_test": true,
  "test_delay_seconds": 5
}
```

响应:
```json
{
  "scan_id": 1,
  "status": "running",
  "query": "app=\"Ollama\" && country=\"US\"",
  "country": "US",
  "total_found": 0,
  "total_created": 0,
  "message": "FOFA扫描已启动，正在后台处理"
}
```

### 2. 获取扫描结果
```http
GET /api/v2/fofa/scan/{scan_id}
```

### 3. 获取扫描历史
```http
GET /api/v2/fofa/scans?limit=20&offset=0
```

## 数据库表结构

### fofa_scan
| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| query | str | FOFA查询语句 |
| country | str | 目标国家代码 |
| status | enum | pending/running/completed/failed |
| total_found | int | 发现的主机数量 |
| total_created | int | 成功创建的端点数量 |
| error_message | str | 错误信息（可选） |
| created_at | datetime | 创建时间 |
| completed_at | datetime | 完成时间（可选） |
| created_by | int | 创建者ID（外键） |

## 使用方法

### 1. 数据库迁移
首先运行数据库迁移脚本创建FOFA扫描表：
```bash
cd backend
python scripts/create_fofa_table.py
```

### 2. 启动服务
```bash
cd backend
poetry run uvicorn src.main:app --reload
```

### 3. 访问前端
- 以管理员身份登录系统
- 访问侧边栏的 "FOFA扫描" 菜单
- 选择目标国家，点击 "启动扫描"

## 核心代码解析

### FOFA 客户端 (client.py)
```python
class FofaClient:
    """
    核心逻辑与AOS的fofa-scan.mjs完全对齐
    """
    def build_query(self, country: str = "US", custom_query: Optional[str] = None) -> str:
        """对应AOS: const searchQuery = `app="Ollama" && country="${country}"`"""
        if custom_query:
            return custom_query
        return f'app="Ollama" && country="{country}"'
```

### HTML 解析器 (parser.py)
```python
class FofaHTMLParser:
    """
    核心解析逻辑与AOS的fofa-scan.mjs完全对齐
    """
    HTML_START_TAG = 'hsxa-host"><a href="'  # 对应AOS
    HTML_END_TAG = '"'                        # 对应AOS
```

## 技术亮点

1. **后台任务处理**: 使用 FastAPI BackgroundTasks 异步处理扫描
2. **数据库持久化**: 完整的扫描历史记录
3. **权限控制**: 仅管理员可访问
4. **自动化集成**: 与现有的 endpoint 和 scheduler 系统无缝集成
5. **错误处理**: 完善的异常捕获和错误记录

## 前端功能

- 🎨 **现代化 UI**: 使用 Ant Design 组件库
- 🔄 **自动刷新**: 实时更新扫描状态（5秒间隔）
- 📊 **可视化状态**: 图标+颜色标识扫描状态
- 🌍 **国家选择**: 预设10个常用国家
- ⚙️ **高级选项**: 支持自定义FOFA查询语句
- 📜 **历史记录**: 完整的扫描历史表格

## 常见问题

### Q: FOFA API 有访问限制吗？
A: 使用的是 FOFA 公开搜索，无需 API Key，但可能有访问频率限制。建议合理控制扫描频率。

### Q: 扫描失败怎么办？
A: 检查 `error_message` 字段，常见原因包括网络问题、FOFA 服务不可用等。

### Q: 如何自定义查询？
A: 在前端界面填写"自定义查询"字段，例如：`app="Ollama" && city="Beijing"`

## 许可证

MIT License

## 致谢

核心逻辑参考 [Awesome-Ollama-Server](https://github.com/shibing624/Awesome-Ollama-Server)

