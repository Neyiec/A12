-- =====================================================================
-- 知识库维护（AI 索引）— PostgreSQL mock 数据
-- =====================================================================
-- 适用库      : A12-PY 的 PostgreSQL（须已执行 backend-python/A12-PY/postgresql_schema.sql）
-- 适用表      : a12_resource_index（索引主表）/ a12_resource_index_chunk（分块表）
--               / a12_retrieval_log（检索审计，仅插入演示行，不改动既有日志）
-- 对应页面    : 管理端「公共资源与知识库维护」Tab 2（KPI 四卡 / 任务列表 / 分块明细 / 向量检索）
-- 与 MySQL 脚本关系: 本脚本与 sql/mock_public_resource_knowledge.sql（MySQL，adm_resource
--               9401~9415）配套，键值 public:{9401..9415} 一一对应，Tab1/Tab2 数据联动一致
-- 向量策略    : 分块的 embedding_vector 置 NULL —— Python 检索 SQL 明确
--               「WHERE embedding_vector IS NOT NULL」，占位分块绝不会命中向量检索，
--               不污染真实 RAG；关键词兜底检索仍可按分块文本命中（演示效果好）
-- 幂等策略    : 仅操作 public:{9401..9415} 键段与 metadata->>'mock'='true' 的日志行，
--               重复执行前先删除同段数据，可反复导入
-- 原有数据    : 不触碰任何真实资源索引（personal 来源与其他 public 键均不受影响）；
--               注意若已对 9401~9415 执行过「全部重新索引」（bootstrap），本脚本会覆盖
--               这批演示资源已有的真实索引（该键段本就是 mock 专属段）
-- 取值域说明  : parse_status = pending / completed / failed（MySQL 侧 indexing 态在 PG
--               记为 pending）；available=false 且 allow_ai=false 表示人工停用
-- chunk_id 规范: 与 Python index_store.py 一致，= "{resource_key}:{chunk_index}"
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- 0. 清理同段 mock 数据（分块表经 FK ON DELETE CASCADE 随主表删除）
-- ---------------------------------------------------------------------
DELETE FROM a12_resource_index
WHERE source_type = 'public'
  AND resource_id IN ('9401','9402','9403','9404','9406','9407',
                      '9408','9409','9410','9411','9412','9413','9414','9415');

DELETE FROM a12_retrieval_log WHERE metadata->>'mock' = 'true';

-- ---------------------------------------------------------------------
-- 1. 索引主表 a12_resource_index（14 条，与 MySQL mock 资源一一对应）
--    completed×8 / failed×1 / pending×4 / 停用×1
-- ---------------------------------------------------------------------
INSERT INTO a12_resource_index
(resource_key, source_type, resource_id, file_url, file_fingerprint, title,
 metadata, available, allow_ai, parse_status, error_message, text_length, chunk_count,
 created_at, updated_at, indexed_at) VALUES

('public:9401', 'public', '9401', 'public/resources/mock/rjyy-bixiu-1.pdf', 'a12mockfingerprint9401000000000000000000000000000000000000000000',
 '人教版高中语文必修上册电子教材',
 '{"source":"mysql","mysql_table":"adm_resource","uploaded_by":90001,"resource_id":"9401","resource_type":"textbook","subject":"语文","grade":"高一","available":true,"allow_ai":true,"file_url":"public/resources/mock/rjyy-bixiu-1.pdf"}',
 TRUE, TRUE, 'completed', NULL, 48620, 3,
 '2026-08-28 09:30:00+08', '2026-09-01 10:24:00+08', '2026-09-01 10:24:00+08'),

('public:9402', 'public', '9402', 'public/resources/mock/rja-math-bixiu-1.pdf', 'a12mockfingerprint9402000000000000000000000000000000000000000000',
 '高中数学必修第一册（人教A版）电子课本',
 '{"source":"mysql","mysql_table":"adm_resource","uploaded_by":90001,"resource_id":"9402","resource_type":"textbook","subject":"数学","grade":"高一","available":true,"allow_ai":true,"file_url":"public/resources/mock/rja-math-bixiu-1.pdf"}',
 TRUE, TRUE, 'completed', NULL, 52130, 2,
 '2026-08-30 16:00:00+08', '2026-09-02 14:05:00+08', '2026-09-02 14:05:00+08'),

('public:9403', 'public', '9403', 'public/resources/mock/physics-mechanics-bank.docx', 'a12mockfingerprint9403000000000000000000000000000000000000000000',
 '高考物理力学专题题库（含解析）',
 '{"source":"mysql","mysql_table":"adm_resource","uploaded_by":90001,"resource_id":"9403","resource_type":"question_bank","subject":"物理","grade":"高三","available":true,"allow_ai":true,"file_url":"public/resources/mock/physics-mechanics-bank.docx"}',
 TRUE, TRUE, 'completed', NULL, 38940, 3,
 '2026-08-31 11:40:00+08', '2026-09-03 09:47:00+08', '2026-09-03 09:47:00+08'),

('public:9404', 'public', '9404', 'public/resources/mock/english-grammar-500.pdf', 'a12mockfingerprint9404000000000000000000000000000000000000000000',
 '初中英语语法填空题库 500 题',
 '{"source":"mysql","mysql_table":"adm_resource","uploaded_by":90001,"resource_id":"9404","resource_type":"question_bank","subject":"英语","grade":"初中","available":true,"allow_ai":true,"file_url":"public/resources/mock/english-grammar-500.pdf"}',
 TRUE, TRUE, 'failed', 'embedding 阶段超时：单批向量请求超过 540s 解析上限，请重解析或拆分文档', 12780, 0,
 '2026-09-05 16:30:00+08', '2026-09-05 16:30:00+08', NULL),

('public:9406', 'public', '9406', 'public/resources/mock/cell-division-animation.mp4', 'a12mockfingerprint9406000000000000000000000000000000000000000000',
 '细胞分裂动画演示视频',
 '{"source":"mysql","mysql_table":"adm_resource","uploaded_by":90001,"resource_id":"9406","resource_type":"media","subject":"生物","grade":"高一","available":true,"allow_ai":true,"file_url":"public/resources/mock/cell-division-animation.mp4"}',
 TRUE, TRUE, 'completed', NULL, 3120, 1,
 '2026-09-01 09:10:00+08', '2026-09-04 20:12:00+08', '2026-09-04 20:12:00+08'),

('public:9407', 'public', '9407', 'public/resources/mock/english-listening-30.mp3', 'a12mockfingerprint9407000000000000000000000000000000000000000000',
 '英语听力训练：日常对话 30 篇',
 '{"source":"mysql","mysql_table":"adm_resource","uploaded_by":90001,"resource_id":"9407","resource_type":"media","subject":"英语","grade":"初中","available":true,"allow_ai":true,"file_url":"public/resources/mock/english-listening-30.mp3"}',
 TRUE, TRUE, 'pending', NULL, 0, 0,
 '2026-09-10 09:00:00+08', '2026-09-10 09:00:00+08', NULL),

('public:9408', 'public', '9408', 'public/resources/mock/periodic-table-hd.png', 'a12mockfingerprint9408000000000000000000000000000000000000000000',
 '化学元素周期表高清挂图',
 '{"source":"mysql","mysql_table":"adm_resource","uploaded_by":90001,"resource_id":"9408","resource_type":"textbook","subject":"化学","grade":"高一","available":true,"allow_ai":true,"file_url":"public/resources/mock/periodic-table-hd.png"}',
 TRUE, TRUE, 'completed', NULL, 2140, 1,
 '2026-09-02 10:30:00+08', '2026-09-06 11:02:00+08', '2026-09-06 11:02:00+08'),

('public:9409', 'public', '9409', 'public/resources/mock/5n3-math-2026-selection.pdf', 'a12mockfingerprint9409000000000000000000000000000000000000000000',
 '五年高考三年模拟·数学（2026 版）章节选编',
 '{"source":"mysql","mysql_table":"adm_resource","uploaded_by":90001,"resource_id":"9409","resource_type":"question_bank","subject":"数学","grade":"高三","available":true,"allow_ai":true,"file_url":"public/resources/mock/5n3-math-2026-selection.pdf"}',
 TRUE, TRUE, 'pending', NULL, 0, 0,
 '2026-09-15 14:20:00+08', '2026-09-15 14:20:00+08', NULL),

('public:9410', 'public', '9410', 'public/resources/mock/science-grade3-slides.pptx', 'a12mockfingerprint94100000000000000000000000000000000000000000000',
 '小学科学三年级上册配套课件包',
 '{"source":"mysql","mysql_table":"adm_resource","uploaded_by":90001,"resource_id":"9410","resource_type":"textbook","subject":"科学","grade":"小学","available":true,"allow_ai":true,"file_url":"public/resources/mock/science-grade3-slides.pptx"}',
 TRUE, TRUE, 'completed', NULL, 18450, 2,
 '2026-09-05 17:10:00+08', '2026-09-08 15:36:00+08', '2026-09-08 15:36:00+08'),

('public:9411', 'public', '9411', 'public/resources/mock/series-parallel-circuit-demo.mp4', 'a12mockfingerprint9411000000000000000000000000000000000000000000',
 '演示实验视频：串联与并联电路对比',
 '{"source":"mysql","mysql_table":"adm_resource","uploaded_by":90001,"resource_id":"9411","resource_type":"media","subject":"物理","grade":"初中","available":true,"allow_ai":true,"file_url":"public/resources/mock/series-parallel-circuit-demo.mp4"}',
 TRUE, TRUE, 'pending', NULL, 0, 0,
 '2026-09-15 16:05:00+08', '2026-09-15 16:05:00+08', NULL),

('public:9412', 'public', '9412', 'component://9412', 'a12mockfingerprint9412000000000000000000000000000000000000000000',
 '古诗词上下句填空互动组件',
 '{"source":"mysql","mysql_table":"adm_resource","uploaded_by":90001,"resource_id":"9412","resource_type":"component","subject":"语文","grade":"初中","available":true,"allow_ai":true,"file_url":null,"template_component":"poem-blank"}',
 TRUE, TRUE, 'completed', NULL, 980, 1,
 '2026-09-03 10:40:00+08', '2026-09-07 13:40:00+08', '2026-09-07 13:40:00+08'),

('public:9413', 'public', '9413', 'public/resources/mock/english-listening-2024.docx', 'a12mockfingerprint9413000000000000000000000000000000000000000000',
 '旧版英语听力训练材料汇编（2024）',
 '{"source":"mysql","mysql_table":"adm_resource","uploaded_by":90001,"resource_id":"9413","resource_type":"question_bank","subject":"英语","grade":"初中","available":false,"allow_ai":false,"file_url":"public/resources/mock/english-listening-2024.docx"}',
 FALSE, FALSE, 'completed', NULL, 9600, 0,
 '2026-08-20 10:20:00+08', '2026-09-09 09:30:00+08', '2026-08-22 11:00:00+08'),

('public:9414', 'public', '9414', 'public/resources/mock/geo-bixiu-2-scan.pdf', 'a12mockfingerprint9414000000000000000000000000000000000000000000',
 '地理必修第二册电子教材（扫描版）',
 '{"source":"mysql","mysql_table":"adm_resource","uploaded_by":90001,"resource_id":"9414","resource_type":"textbook","subject":"地理","grade":"高一","available":true,"allow_ai":true,"file_url":"public/resources/mock/geo-bixiu-2-scan.pdf"}',
 TRUE, TRUE, 'pending', NULL, 0, 0,
 '2026-09-14 11:45:00+08', '2026-09-14 11:45:00+08', NULL),

('public:9415', 'public', '9415', 'component://9415', 'a12mockfingerprint9415000000000000000000000000000000000000000000',
 '数学公式推导分步展示组件',
 '{"source":"mysql","mysql_table":"adm_resource","uploaded_by":90001,"resource_id":"9415","resource_type":"component","subject":"数学","grade":"高中","available":true,"allow_ai":true,"file_url":null,"template_component":"formula-steps"}',
 TRUE, TRUE, 'completed', NULL, 1120, 1,
 '2026-09-06 14:30:00+08', '2026-09-09 10:15:00+08', '2026-09-09 10:15:00+08');

-- ---------------------------------------------------------------------
-- 2. 分块表 a12_resource_index_chunk（14 块，embedding_vector 置 NULL）
--    chunk_count 已与主表逐条对齐；向量检索不会命中，关键词兜底可按文本命中
-- ---------------------------------------------------------------------
INSERT INTO a12_resource_index_chunk
(chunk_id, resource_key, source_type, resource_id, chunk_index, content, embedding_vector, metadata, created_at) VALUES

-- 9401 语文教材 ×3
('public:9401:0', 'public:9401', 'public', '9401', 0,
 '第一单元 青春激扬：《沁园春·长沙》以独立寒秋之景起笔，借湘江秋景抒发革命青春豪情；单元任务要求把握意象特点，体会景中寓情、情中显志的写法。',
 NULL, '{"available":true,"allow_ai":true}', '2026-09-01 10:24:00+08'),
('public:9401:1', 'public:9401', 'public', '9401', 1,
 '第二单元 劳动光荣：《喜看稻菽千重浪》展现袁隆平躬耕田野的科学家精神，《心有一团火》记录张秉贵的服务艺术，人物通讯注重典型事件与细节描写。',
 NULL, '{"available":true,"allow_ai":true}', '2026-09-01 10:24:00+08'),
('public:9401:2', 'public:9401', 'public', '9401', 2,
 '第三单元 生命的诗意：《短歌行》慷慨深沉，《归园田居》恬淡自然，对比诵读中体会建安风骨与田园意趣；学习任务包含意象梳理与名句默写。',
 NULL, '{"available":true,"allow_ai":true}', '2026-09-01 10:24:00+08'),

-- 9402 数学教材 ×2
('public:9402:0', 'public:9402', 'public', '9402', 0,
 '第一章 集合与常用逻辑用语：集合的概念与表示、基本关系与运算；充分条件与必要条件的判定是高考高频考点，注意全称量词与存在量词命题的否定形式。',
 NULL, '{"available":true,"allow_ai":true}', '2026-09-02 14:05:00+08'),
('public:9402:1', 'public:9402', 'public', '9402', 1,
 '第二章 一元二次函数、方程和不等式：基本不等式及其应用，均值不等式求最值的三种常见配凑技巧；一元二次不等式与二次函数图象的对应关系。',
 NULL, '{"available":true,"allow_ai":true}', '2026-09-02 14:05:00+08'),

-- 9403 物理题库 ×3
('public:9403:0', 'public:9403', 'public', '9403', 0,
 '受力分析专题：隔离法与整体法的选择策略，例题 1-15 涵盖斜面模型、连接体模型；易错点：漏掉摩擦力方向判断，未按先重力再弹力后摩擦力的顺序分析。',
 NULL, '{"available":true,"allow_ai":true}', '2026-09-03 09:47:00+08'),
('public:9403:1', 'public:9403', 'public', '9403', 1,
 '牛顿运动定律专题：瞬时性问题（绳剪断、撤力瞬间）与传送带模型；例题 16-32 配详细解析，突显超重失重视图在判断支持力变化中的应用。',
 NULL, '{"available":true,"allow_ai":true}', '2026-09-03 09:47:00+08'),
('public:9403:2', 'public:9403', 'public', '9403', 2,
 '功能关系专题：动能定理在多过程问题中的分段应用，摩擦力做功与热量计算 Q=f·s 相对位移；综合计算题 45-52 附评分标准与时间分配建议。',
 NULL, '{"available":true,"allow_ai":true}', '2026-09-03 09:47:00+08'),

-- 9406 生物动画 ×1
('public:9406:0', 'public:9406', 'public', '9406', 0,
 '有丝分裂动画字幕摘要：间期 DNA 复制与蛋白质合成；前期染色体出现核膜消失；中期着丝点排列于赤道板；后期姐妹染色单体分离；末期细胞膜缢裂形成两个子细胞。',
 NULL, '{"available":true,"allow_ai":true}', '2026-09-04 20:12:00+08'),

-- 9408 元素周期表挂图 ×1
('public:9408:0', 'public:9408', 'public', '9408', 0,
 '元素周期表挂图 OCR 内容：七个周期十六个族，原子序数=质子数=核外电子数；同周期从左到右原子半径递减、金属性减弱；同主族从上到下最外层电子数相同、金属性增强。',
 NULL, '{"available":true,"allow_ai":true}', '2026-09-06 11:02:00+08'),

-- 9410 科学课件 ×2
('public:9410:0', 'public:9410', 'public', '9410', 0,
 '第一单元 植物：种子萌发需要适宜的温度、一定的水分和充足的空气；根尖结构从尖端向上依次为根冠、分生区、伸长区、成熟区，成熟区生有根毛是吸水主要部位。',
 NULL, '{"available":true,"allow_ai":true}', '2026-09-08 15:36:00+08'),
('public:9410:1', 'public:9410', 'public', '9410', 1,
 '第三单元 天气与气候：气温观测一天中最高气温出现在午后 2 时左右；降水形成的两个条件是空气达到饱和与凝结核；常用天气符号与空气质量指数判读。',
 NULL, '{"available":true,"allow_ai":true}', '2026-09-08 15:36:00+08'),

-- 9412 古诗词组件 ×1
('public:9412:0', 'public:9412', 'public', '9412', 0,
 '古诗词上下句填空互动组件说明：内置题集含「海内存知己—天涯若比邻」「但愿人长久—千里共婵娟」「会当凌绝顶—一览众山小」，学生输入下句即时判分，支持自定义题集与水墨主题。',
 NULL, '{"available":true,"allow_ai":true}', '2026-09-07 13:40:00+08'),

-- 9415 公式组件 ×1
('public:9415:0', 'public:9415', 'public', '9415', 0,
 '数学公式推导分步展示组件说明：以勾股定理为例演示 a²+b²=c² 到 a=√(c²-b²) 的分步移项推导，支持逐步点击呈现、自动播放与回看，黑板板书主题样式。',
 NULL, '{"available":true,"allow_ai":true}', '2026-09-09 10:15:00+08');

-- ---------------------------------------------------------------------
-- 3. 检索审计日志 a12_retrieval_log（3 条演示行，metadata.mock 标记便于清理）
-- ---------------------------------------------------------------------
INSERT INTO a12_retrieval_log (query, resource_ids, match_count, top_score, search_mode, latency_ms, metadata, created_at) VALUES
('牛顿第二定律 实验探究 控制变量法', '[{"resource_key":"public:9403","chunk_index":1}]', 3, 0.72, 'pgvector_hybrid_rerank', 86,
 '{"mock":"true","top_matches":[{"resource_key":"public:9403","score":0.72},{"resource_key":"public:9401","score":0.41}]}', '2026-09-18 10:12:00+08'),
('文言文 情境教学 导入设计', '[{"resource_key":"public:9401","chunk_index":0}]', 2, 0.65, 'fallback_hybrid_rerank', 34,
 '{"mock":"true","fallback_reason":"embedding 服务不可用，已降级关键词检索"}', '2026-09-19 15:40:00+08'),
('元素周期表 原子半径 递变规律', '[]', 0, NULL, 'no_match', 52,
 '{"mock":"true","note":"无命中样例，用于演示零结果展示"}', '2026-09-20 09:05:00+08');

COMMIT;

-- =====================================================================
-- 导入后验证（可选，手动执行）
--   SELECT parse_status, available, COUNT(*), SUM(chunk_count) FROM a12_resource_index
--    WHERE source_type='public' AND resource_id IN
--          ('9401','9402','9403','9404','9406','9407','9408','9409',
--           '9410','9411','9412','9413','9414','9415')
--    GROUP BY parse_status, available ORDER BY parse_status;
-- 预期：completed×9（含 1 条停用）+ failed×1 + pending×4 = 14 条资源、14 个分块；
--       KPI 四卡 / 任务列表 / 分块明细随之有数据；
--       「向量检索」不会命中 mock 分块（embedding 为 NULL 被检索 SQL 过滤），
--       关键词兜底模式可按分块文本正常命中。
-- =====================================================================
