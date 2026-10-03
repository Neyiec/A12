-- 已有 MySQL 数据库执行一次；新库使用 a12_schema.sql。
ALTER TABLE adm_audit
  ADD COLUMN ai_domain VARCHAR(20) DEFAULT NULL COMMENT 'AI审核学科代理: arts/science/engineering' AFTER status,
  ADD COLUMN ai_verdict VARCHAR(20) DEFAULT NULL COMMENT 'AI结论: pass/review/fail/error' AFTER ai_domain,
  ADD COLUMN ai_score INT DEFAULT NULL COMMENT 'AI审核评分0-100' AFTER ai_verdict,
  ADD COLUMN ai_report JSON DEFAULT NULL COMMENT '检查维度、证据和风险点' AFTER ai_score,
  ADD COLUMN ai_model VARCHAR(100) DEFAULT NULL COMMENT 'AI审核模型' AFTER ai_report,
  ADD COLUMN ai_reviewed_at DATETIME DEFAULT NULL COMMENT 'AI审核时间' AFTER ai_model;
