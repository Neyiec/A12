-- =====================================================================
-- 公共资源与知识库维护 — MySQL mock 数据
-- =====================================================================
-- 适用表      : adm_resource（公共资源与组件表，管理端「公共资源与知识库维护」Tab 1 数据源）
-- 覆盖场景    : 4 类资源（textbook 教材 / question_bank 题库 / media 媒体 / component 互动组件）；
--               启用与禁用；AI 索引五态（completed / indexing / pending / failed / disabled）全值域覆盖；
--               含失败原因（ai_index_error）与索引完成时间（ai_indexed_at）样例
-- 执行前提    : 已执行根目录 table_created.txt 中的建表语句（本脚本不含 DDL）
-- 幂等策略    : 使用 9400+ 高位显式主键（与社区治理 mock 的 9100~9399 段不重叠），
--               重复执行前先删除同段数据，可反复导入
-- 用户 ID 约定: uploaded_by = 90001（管理员，与社区治理 mock 的管理员 ID 一致）；
--               表无外键约束，用户不存在也可插入成功
-- 文件 URL 约定: file_url 仅为演示用对象键（public/resources/mock/ 前缀），并非桶中真实对象——
--               列表/图标/格式提取（前端按扩展名识别）正常，但「下载/预签名」会因对象不存在返回 404
-- Tab 2 说明  : 知识库维护（AI 索引任务）行来自 PostgreSQL a12_resource_index/_chunk（Python 侧），
--               本脚本不手工造 PG 向量伪数据（避免污染真实 RAG 检索）；
--               导入本脚本后，在管理端执行「全部重新索引」（bootstrap，force_reparse=true）
--               即可将上述 mock 资源解析入向量库，任务列表随之出现对应行
-- 取值域说明  : adm_resource.resource_type  = textbook / question_bank / media / component（DDL 注释值域）
--               adm_resource.status         = 1 启用 / 0 禁用
--               adm_resource.ai_index_status = pending / indexing / completed / failed / disabled
-- =====================================================================

SET NAMES utf8mb4;

START TRANSACTION;

-- ---------------------------------------------------------------------
-- 0. 清理同段 mock 数据（保证脚本可重复执行）
-- ---------------------------------------------------------------------
DELETE FROM adm_resource WHERE id BETWEEN 9401 AND 9499;

-- ---------------------------------------------------------------------
-- 1. 公共资源 adm_resource（14 条）
--    ①~⑭ 覆盖：4 资源类型 × 启停 × 索引五态；file_url 均带真实扩展名
--    （component 类型例外：无文件，靠 template_data 承载模板数据）
-- ---------------------------------------------------------------------

INSERT INTO adm_resource
(id, resource_type, title, subject, grade, file_url, template_data, thumbnail, description, file_size, status, uploaded_by, ai_index_status, ai_indexed_at, ai_index_error, created_at, updated_at) VALUES

-- ① 教材 · PDF · 索引完成
(9401, 'textbook', '人教版高中语文必修上册电子教材',
 '语文', '高一', 'public/resources/mock/rjyy-bixiu-1.pdf', NULL, NULL,
 '人教版高中语文必修上册全册电子课本，含课文、注释与单元学习任务，供 AI 备课时检索引用。',
 28553600, 1, 90001, 'completed', '2026-09-01 10:24:00', NULL, '2026-08-28 09:12:00', '2026-09-01 10:24:00'),

-- ② 教材 · PDF · 索引完成
(9402, 'textbook', '高中数学必修第一册（人教A版）电子课本',
 '数学', '高一', 'public/resources/mock/rja-math-bixiu-1.pdf', NULL, NULL,
 '人教A版必修第一册：集合与常用逻辑用语、一元二次函数与不等式等章节，含例题与习题。',
 31245800, 1, 90001, 'completed', '2026-09-02 14:05:00', NULL, '2026-08-30 15:40:00', '2026-09-02 14:05:00'),

-- ③ 题库 · DOCX · 索引完成
(9403, 'question_bank', '高考物理力学专题题库（含解析）',
 '物理', '高三', 'public/resources/mock/physics-mechanics-bank.docx', NULL, NULL,
 '力学专题 320 题：受力分析、牛顿定律、功能关系三大板块，每题附详解与易错点标注。',
 1862000, 1, 90001, 'completed', '2026-09-03 09:47:00', NULL, '2026-08-31 11:20:00', '2026-09-03 09:47:00'),

-- ④ 题库 · PDF · 索引失败（向量超时样例）
(9404, 'question_bank', '初中英语语法填空题库 500 题',
 '英语', '初中', 'public/resources/mock/english-grammar-500.pdf', NULL, NULL,
 '初中语法填空专项 500 题，按词法/句法分类，含答案与讲评要点。',
 9450000, 1, 90001, 'failed', NULL, 'embedding 阶段超时：单批向量请求超过 540s 解析上限，请重解析或拆分文档', '2026-09-05 16:30:00', '2026-09-05 16:30:00'),

-- ⑤ 媒体 · MP4 · 索引完成
(9406, 'media', '细胞分裂动画演示视频',
 '生物', '高一', 'public/resources/mock/cell-division-animation.mp4', NULL, NULL,
 '有丝分裂全程 3D 动画（4 分 30 秒），含各期特征字幕标注，适合导入环节播放。',
 76830000, 1, 90001, 'completed', '2026-09-04 20:12:00', NULL, '2026-09-01 08:55:00', '2026-09-04 20:12:00'),

-- ⑥ 媒体 · MP3 · 待索引
(9407, 'media', '英语听力训练：日常对话 30 篇',
 '英语', '初中', 'public/resources/mock/english-listening-30.mp3', NULL, NULL,
 '慢速日常对话听力材料合辑，语速 120 词/分钟，配套听写任务单另行上传。',
 26540000, 1, 90001, 'pending', NULL, NULL, '2026-09-10 09:00:00', '2026-09-10 09:00:00'),

-- ⑦ 教材 · PNG 挂图 · 索引完成
(9408, 'textbook', '化学元素周期表高清挂图',
 '化学', '高一', 'public/resources/mock/periodic-table-hd.png', NULL, NULL,
 '1080P 元素周期表挂图，含原子量与外层电子排布色块，可作课件插图引用。',
 4820000, 1, 90001, 'completed', '2026-09-06 11:02:00', NULL, '2026-09-02 10:18:00', '2026-09-06 11:02:00'),

-- ⑧ 题库 · PDF · 索引中（演示 indexing 态，Java 侧 MySQL 状态优先展示）
(9409, 'question_bank', '五年高考三年模拟·数学（2026 版）章节选编',
 '数学', '高三', 'public/resources/mock/5n3-math-2026-selection.pdf', NULL, NULL,
 '2026 版五三数学重点章节选编：函数与导数、解析几何两大板块精选题组。',
 15230000, 1, 90001, 'indexing', NULL, NULL, '2026-09-15 14:20:00', '2026-09-15 14:20:00'),

-- ⑨ 教材 · PPTX · 索引完成
(9410, 'textbook', '小学科学三年级上册配套课件包',
 '科学', '小学', 'public/resources/mock/science-grade3-slides.pptx', NULL, NULL,
 '教科版小学科学三上 12 课时配套课件：植物、动物、天气三个单元，含课堂活动页。',
 52340000, 1, 90001, 'completed', '2026-09-08 15:36:00', NULL, '2026-09-05 17:02:00', '2026-09-08 15:36:00'),

-- ⑩ 媒体 · MP4 · 索引中
(9411, 'media', '演示实验视频：串联与并联电路对比',
 '物理', '初中', 'public/resources/mock/series-parallel-circuit-demo.mp4', NULL, NULL,
 '电学演示实验实录（6 分钟）：小灯泡亮度对比、电流表读数特写，含安全操作提示。',
 94210000, 1, 90001, 'indexing', NULL, NULL, '2026-09-15 16:05:00', '2026-09-15 16:05:00'),

-- ⑪ 互动组件 · 无文件 · 索引完成（template_data 承载模板）
(9412, 'component', '古诗词上下句填空互动组件',
 '语文', '初中', NULL,
 '{"component":"poem-blank","version":1,"props":{"title":"古诗词上下句填空","items":[{"hint":"海内存知己","answer":"天涯若比邻"},{"hint":"但愿人长久","answer":"千里共婵娟"},{"hint":"会当凌绝顶","answer":"一览众山小"}],"showFirstHint":true},"style":{"theme":"ink","fontSize":18}}',
 NULL, '古诗词填空课堂互动组件：给出上句，学生输入下句即时判分，支持自定义题集。',
 NULL, 1, 90001, 'completed', '2026-09-07 13:40:00', NULL, '2026-09-03 10:30:00', '2026-09-07 13:40:00'),

-- ⑫ 题库 · DOCX · 已停用（disabled 态：人工下架，不参与检索）
(9413, 'question_bank', '旧版英语听力训练材料汇编（2024）',
 '英语', '初中', 'public/resources/mock/english-listening-2024.docx', NULL, NULL,
 '2024 年旧版听力材料，音频源已失效，已停用并关闭 AI 索引，待新版材料替换。',
 12050000, 0, 90001, 'disabled', NULL, NULL, '2026-08-20 10:00:00', '2026-09-09 09:30:00'),

-- ⑬ 教材 · PDF · 待索引
(9414, 'textbook', '地理必修第二册电子教材（扫描版）',
 '地理', '高一', 'public/resources/mock/geo-bixiu-2-scan.pdf', NULL, NULL,
 '人教版地理必修第二册扫描版：人口、城镇与乡村、产业区位三单元，扫描件已做纠偏处理。',
 48760000, 1, 90001, 'pending', NULL, NULL, '2026-09-14 11:45:00', '2026-09-14 11:45:00'),

-- ⑭ 互动组件 · 无文件 · 索引完成
(9415, 'component', '数学公式推导分步展示组件',
 '数学', '高中', NULL,
 '{"component":"formula-steps","version":1,"props":{"title":"公式推导分步展示","steps":[{"label":"原式","formula":"a^2+b^2=c^2"},{"label":"移项","formula":"a^2=c^2-b^2"},{"label":"结论","formula":"a=\\\\sqrt{c^2-b^2}"}],"autoPlay":false},"style":{"theme":"board","fontSize":20}}',
 NULL, '分步展示数学公式推导过程的课堂组件：逐步点击呈现，支持自动播放与回看。',
 NULL, 1, 90001, 'completed', '2026-09-09 10:15:00', NULL, '2026-09-06 14:22:00', '2026-09-09 10:15:00');

COMMIT;

-- =====================================================================
-- 导入后验证（可选，手动执行）
--   SELECT resource_type, ai_index_status, COUNT(*) FROM adm_resource
--    WHERE id BETWEEN 9401 AND 9499 GROUP BY resource_type, ai_index_status;
-- 预期：textbook×4, question_bank×4, media×3, component×2（共 14 条）；
--       completed×8 / indexing×2 / pending×2 / failed×1 / disabled×1
-- =====================================================================
