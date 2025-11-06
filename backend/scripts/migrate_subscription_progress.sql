-- 订阅进度字段迁移脚本
-- 为 subscription 表添加进度跟踪字段
-- 执行方式: mysql -u root -p ollama_hack < migrate_subscription_progress.sql

USE ollama_hack;

-- 检查表是否存在
SELECT '开始迁移 subscription 表...' AS '';

-- 添加 status 字段
ALTER TABLE subscription 
ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'idle' 
COMMENT '订阅状态' 
AFTER error_message;

SELECT '✓ 添加 status 字段' AS '';

-- 添加 progress_current 字段
ALTER TABLE subscription 
ADD COLUMN IF NOT EXISTS progress_current INT NOT NULL DEFAULT 0 
COMMENT '当前处理数量' 
AFTER status;

SELECT '✓ 添加 progress_current 字段' AS '';

-- 添加 progress_total 字段
ALTER TABLE subscription 
ADD COLUMN IF NOT EXISTS progress_total INT NOT NULL DEFAULT 0 
COMMENT '总数量' 
AFTER progress_current;

SELECT '✓ 添加 progress_total 字段' AS '';

-- 添加 progress_message 字段
ALTER TABLE subscription 
ADD COLUMN IF NOT EXISTS progress_message TEXT NULL 
COMMENT '进度消息' 
AFTER progress_total;

SELECT '✓ 添加 progress_message 字段' AS '';

-- 验证表结构
SELECT '验证表结构...' AS '';

SELECT 
    COLUMN_NAME AS '字段名',
    DATA_TYPE AS '数据类型',
    COLUMN_DEFAULT AS '默认值',
    IS_NULLABLE AS '可空',
    COLUMN_COMMENT AS '注释'
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = 'ollama_hack' 
  AND TABLE_NAME = 'subscription' 
  AND COLUMN_NAME IN ('status', 'progress_current', 'progress_total', 'progress_message')
ORDER BY ORDINAL_POSITION;

SELECT '✅ 迁移完成！' AS '';

