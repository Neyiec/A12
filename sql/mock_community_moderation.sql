-- =====================================================================
-- 内容审核与社区治理 — MySQL mock 数据
-- =====================================================================
-- 适用表      : com_content（社区内容）/ com_interaction（社区互动）/ adm_audit（审核与举报）
-- 覆盖场景    : 技能/案例公开池、待审核、返修中、已下线；收藏/浏览/复用互动；投稿审核与举报处置
-- 执行前提    : 已执行根目录 table_created.txt 中的建表语句（本脚本不含 DDL）
-- 幂等策略    : 使用 9100+ 高位显式主键，重复执行前先删除同段数据，可反复导入
-- 用户 ID 约定: 作者/举报人 10001~10005（教师）、审核人 90001（管理员）。
--              三表均无外键约束，用户不存在也可插入成功；如需界面显示正确，请替换为库中真实用户 ID。
-- 取值域说明  : com_content.status     = draft / reviewing / public / offline（代码实际使用值，DDL 注释未列 draft）
--              com_content.content_type = skill / lesson_case（normalizeContentType 白名单）
--              com_interaction.action_type = favorite / view / derivation（target_type 与 content_type 同值）
--              adm_audit.audit_type  = audit（投稿审核）/ report（举报）；action 见各 INSERT 注释
-- =====================================================================

SET NAMES utf8mb4;

START TRANSACTION;

-- ---------------------------------------------------------------------
-- 0. 清理同段 mock 数据（保证脚本可重复执行）
-- ---------------------------------------------------------------------
DELETE FROM com_content     WHERE id BETWEEN 9101 AND 9199;
DELETE FROM com_interaction WHERE id BETWEEN 9201 AND 9299;
DELETE FROM adm_audit       WHERE id BETWEEN 9301 AND 9399;

-- ---------------------------------------------------------------------
-- 1. 社区内容 com_content（12 条：6 public / 2 reviewing / 1 draft / 2 offline / 1 public 置顶补充）
--    显式指定 created_at/updated_at，便于审核队列按时间排序演示
-- ---------------------------------------------------------------------

-- ① 公开池 · 置顶技能
INSERT INTO com_content
(id, content_type, author_id, title, description, subject, grade, lesson_type, content_data, input_variables, example_effect, version, version_history, license, status, is_top, view_count, use_count, created_at, updated_at) VALUES
(9101, 'skill', 10001, '文言文情景教学技能包',
 '以情境任务驱动文言文精读：导入悬念、逐句疏通、情景演绎三段式，可复用到任意文言篇目。',
 '语文', '高中', '新授课',
 '{"source":"a12-skill-manual","summary":"情境任务驱动的文言文精读流程","slide_outline":[{"slide_no":1,"title":"导入·悬念情境","content_points":["以《鸿门宴》座次图设疑","抛出任务：为宴席排座次"]},{"slide_no":2,"title":"逐句疏通","content_points":["实词卡片配对","特殊句式归纳表"]}],"recommended_tools":["知识卡片","情景动画"]}',
 '[{"key":"topic","label":"课程主题（文言篇目）","type":"text","required":true},{"key":"grade","label":"年级","type":"select","options":["高一","高二","高三"],"required":true},{"key":"duration","label":"课时长度（分钟）","type":"number","required":false}]',
 '生成的大纲含 8-10 页：情境导入 1 页、逐句疏通 4-5 页、情景演绎任务卡 2 页、总结 1 页。',
 2,
 '[{"version_number":1,"description":"首发投稿","created_at":"2026-08-05 10:00:00"},{"version_number":2,"description":"补充情景演绎任务卡模板","created_at":"2026-08-28 15:30:00"}]',
 'CC BY-NC 4.0', 'public', 1, 356, 47, '2026-08-05 10:00:00', '2026-08-28 15:30:00'),

(9102, 'skill', 10002, '初中数学错题讲评课技能',
 '错题归因四象限法组织讲评课：按知识性/审题性/计算性/策略性错因分组，配变式训练生成规则。',
 '数学', '初中', '复习课',
 '{"source":"a12-skill-manual","summary":"错题归因四象限讲评流程","slide_outline":[{"slide_no":1,"title":"错题数据总览","content_points":["按错因四象限分类统计"]},{"slide_no":2,"title":"典型错题剖析","content_points":["归因标签","变式训练题"]}]}',
 '[{"key":"exam_title","label":"考试名称","type":"text","required":true},{"key":"wrong_questions","label":"错题清单","type":"textarea","required":true}]',
 '生成的讲评课大纲按错因分组，每组含变式训练 2 题。',
 1, '[{"version_number":1,"description":"首发投稿","created_at":"2026-08-12 09:00:00"}]',
 'CC BY-NC 4.0', 'public', 0, 214, 23, '2026-08-12 09:00:00', '2026-08-12 09:00:00'),

(9103, 'lesson_case', 10003, '小学英语 Unit3 Weather 完整课件案例',
 '40 分钟 PEP 四年级下册 weather 话题课件：热身猜天气、句型呈现、小组天气预报播报三环节，含完整页面 HTML。',
 '英语', '小学', '新授课',
 '{"source":"a12-html-ppt-workspace","project_id":null,"presentation_id":"ppt_9f3a2c1e8b","workspace_mode":"ppt","slides":[{"slide_no":1,"title":"Warm-up","html_summary":"图片猜天气热身游戏"},{"slide_no":2,"title":"Presentation","html_summary":"What is the weather like 核心句型呈现"},{"slide_no":3,"title":"Group work","html_summary":"小组天气预报播报任务卡"}],"lesson_plan":{"teaching_goals":["能听懂并运用 weather 核心句型","能完成天气预报播报任务"],"duration_minutes":40}}',
 NULL,
 '含互动播报任务卡，学生参与度高；页面可直接在线预览。',
 1, '[{"version_number":1,"description":"从创作工作台发布","created_at":"2026-08-18 16:20:00"}]',
 'CC BY-NC 4.0', 'public', 0, 189, 31, '2026-08-18 16:20:00', '2026-08-18 16:20:00'),

(9104, 'lesson_case', 10004, '高中物理《牛顿第二定律》实验探究课案例',
 '以实验数据拟合为主线：控制变量法设计、数据表格、a-F 图像拟合，含实验误差讨论页。',
 '物理', '高中', '实验课',
 '{"source":"a12-html-ppt-workspace","project_id":null,"presentation_id":"ppt_7c2d9e4a1f","workspace_mode":"ppt","slides":[{"slide_no":1,"title":"实验设计","html_summary":"控制变量法思路图"},{"slide_no":2,"title":"数据记录","html_summary":"a-F 实验数据表格"},{"slide_no":3,"title":"图像拟合","html_summary":"线性拟合与结论提炼"}]}',
 NULL,
 '含数据表格页与图像拟合页，适合实验室多媒体环境。',
 1, '[{"version_number":1,"description":"从创作工作台发布","created_at":"2026-08-22 11:05:00"}]',
 'CC BY-NC-SA 4.0', 'public', 0, 143, 18, '2026-08-22 11:05:00', '2026-08-22 11:05:00'),

(9105, 'skill', 10005, '课堂小组合作分工技能',
 '四人小组角色轮换制（主持人/记录员/汇报员/质检员），含合作任务卡模板与评价量表生成规则。',
 '通用', '通用', '活动课',
 '{"source":"a12-skill-manual","summary":"四人小组角色轮换合作流程","slide_outline":[{"slide_no":1,"title":"角色分工说明","content_points":["四个角色职责卡"]},{"slide_no":2,"title":"评价量表","content_points":["自评互评各 3 项"]}]}'  ,
 '[{"key":"group_size","label":"小组人数","type":"number","required":true},{"key":"task","label":"合作任务描述","type":"textarea","required":true}]',
 '生成合作任务卡与评价量表各 1 页，角色随机分配规则内置。',
 1, '[{"version_number":1,"description":"首发投稿","created_at":"2026-09-01 08:40:00"}]',
 'CC BY 4.0', 'public', 0, 98, 12, '2026-09-01 08:40:00', '2026-09-01 08:40:00'),

(9111, 'skill', 10001, '化学方程式配平闯关技能',
 '把配平练习包装为闯关游戏：由易到难三级关卡，配平成功即时反馈，适合课堂前的热身巩固。',
 '化学', '初中', '习题课',
 '{"source":"a12-skill-manual","summary":"化学方程式配平三级闯关","slide_outline":[{"slide_no":1,"title":"第一关·观察法","content_points":["简单系数配平 3 题"]},{"slide_no":2,"title":"第二关·最小公倍数法","content_points":["中等难度 3 题"]}]}',
 '[{"key":"chapter","label":"章节","type":"text","required":true},{"key":"difficulty","label":"难度","type":"select","options":["基础","进阶"],"required":false}]',
 '生成闯关式练习页，含即时对错反馈说明。',
 1, '[{"version_number":1,"description":"首发投稿","created_at":"2026-09-03 20:10:00"}]',
 'CC BY-NC 4.0', 'public', 0, 66, 7, '2026-09-03 20:10:00', '2026-09-03 20:10:00'),

(9112, 'lesson_case', 10002, '小学语文《观潮》情境朗读课案例',
 '以钱塘江大潮视频情境导入，按潮来前/潮来时/潮头过三段设计朗读梯度，含朗读评价星页。',
 '语文', '小学', '新授课',
 '{"source":"a12-html-ppt-workspace","project_id":null,"presentation_id":"ppt_1a2b3c4d5e","workspace_mode":"ppt","slides":[{"slide_no":1,"title":"情境导入","html_summary":"钱塘江大潮视频页"},{"slide_no":2,"title":"潮来时","html_summary":"朗读梯度指导"}]}',
 NULL,
 '朗读梯度设计清晰，配乐朗读环节学生反应热烈。',
 1, '[{"version_number":1,"description":"从创作工作台发布","created_at":"2026-09-05 19:45:00"}]',
 'CC BY-NC 4.0', 'public', 0, 77, 9, '2026-09-05 19:45:00', '2026-09-05 19:45:00'),

-- ② 待审核（reviewing，对应 adm_audit 待办 9301/9302）
(9106, 'lesson_case', 10003, '初中历史《丝绸之路》项目式学习案例',
 '以博物馆策展为驱动任务：分组考证丝路商品路线，产出策展方案与讲解词，含过程性评价页。',
 '历史', '初中', '活动课',
 '{"source":"a12-html-ppt-workspace","project_id":null,"presentation_id":"ppt_6e5d4c3b2a","workspace_mode":"ppt","slides":[{"slide_no":1,"title":"策展任务发布","html_summary":"驱动性问题与分组"},{"slide_no":2,"title":"史料证据包","html_summary":"丝路商品与路线图"}]}',
 NULL,
 '项目式学习案例，含策展评价量规。',
 1, '[{"version_number":1,"description":"从创作工作台发布并提交审核","created_at":"2026-09-10 14:30:00"}]',
 'CC BY-NC 4.0', 'reviewing', 0, 5, 0, '2026-09-10 14:30:00', '2026-09-10 14:30:00'),

(9107, 'skill', 10004, 'AI 生成课件二次加工技能',
 '把 AI 生成的课件页按学情做二次加工：替换情境素材、调整提问坡度、补本地化案例的三步法。',
 '通用', '通用', '新授课',
 '{"source":"a12-skill-manual","summary":"AI 课件二次加工三步法","slide_outline":[{"slide_no":1,"title":"第一步·换情境","content_points":["替换为本地学生熟悉素材"]},{"slide_no":2,"title":"第二步·调坡度","content_points":["提问链难度递进设计"]}]}',
 '[{"key":"ai_outline","label":"AI 生成的大纲","type":"textarea","required":true},{"key":"class_profile","label":"学情描述","type":"textarea","required":false}]',
 '输出二次加工清单与改写示例对照页。',
 1, '[{"version_number":1,"description":"首发投稿","created_at":"2026-09-11 21:15:00"}]',
 'CC BY-NC 4.0', 'reviewing', 0, 3, 0, '2026-09-11 21:15:00', '2026-09-11 21:15:00'),

-- ③ 返修中（draft，对应 adm_audit 9306 rework）
(9108, 'lesson_case', 10005, '初中生物《光合作用》探究课案例（返修中）',
 '实验探究课案例初稿：金鱼藻产氧实验 + 叶片脱色对照，审核意见要求补充实验安全提示页。',
 '生物', '初中', '实验课',
 '{"source":"a12-html-ppt-workspace","project_id":null,"presentation_id":"ppt_8b7c6d5e4f","workspace_mode":"ppt","slides":[{"slide_no":1,"title":"实验设计","html_summary":"金鱼藻产氧装置图"},{"slide_no":2,"title":"现象记录","html_summary":"气泡计数记录表"}]}',
 NULL,
 '初稿，按审核意见返修中。',
 2,
 '[{"version_number":1,"description":"首发投稿","created_at":"2026-09-06 10:00:00"},{"version_number":2,"description":"按审核意见返修中","created_at":"2026-09-12 09:20:00"}]',
 'CC BY-NC 4.0', 'draft', 0, 0, 0, '2026-09-06 10:00:00', '2026-09-12 09:20:00'),

-- ④ 已下线（offline：9109 审核驳回 / 9110 举报下架）
(9109, 'skill', 10002, '万金油课堂开场白合集',
 '收集了 30 条课堂开场白，未区分学科与学情，且与平台 AI 生成定位重复度低。',
 '通用', '通用', '新授课',
 '{"source":"a12-skill-manual","summary":"课堂开场白合集","slide_outline":[{"slide_no":1,"title":"开场白清单","content_points":["30 条开场白列表"]}]}',
 NULL,
 '已被审核驳回：内容与技能包定位不符。',
 1, '[{"version_number":1,"description":"首发投稿","created_at":"2026-08-30 13:00:00"}]',
 'CC BY-NC 4.0', 'offline', 0, 21, 0, '2026-08-30 13:00:00', '2026-09-08 10:00:00'),

(9110, 'lesson_case', 10003, '高中数学《导数概念》课件案例',
 '导数概念引入课件（被举报内容与他人公开课件高度雷同，管理员核实后下架）。',
 '数学', '高中', '新授课',
 '{"source":"a12-html-ppt-workspace","project_id":null,"presentation_id":"ppt_0f1e2d3c4b","workspace_mode":"ppt","slides":[{"slide_no":1,"title":"瞬时速度引入","html_summary":"高台跳水情境"},{"slide_no":2,"title":"概念建构","html_summary":"割线到切线的极限"}]}',
 NULL,
 '因版权举报下架处理。',
 1, '[{"version_number":1,"description":"从创作工作台发布","created_at":"2026-09-02 17:00:00"}]',
 'CC BY-NC 4.0', 'offline', 0, 54, 2, '2026-09-02 17:00:00', '2026-09-13 11:00:00');

-- ---------------------------------------------------------------------
-- 2. 社区互动 com_interaction（收藏 / 最近浏览 / 复用派生）
--    view 语义：每用户对同一内容仅保留一条最近浏览记录（后端先删后插）
--    derivation：bind_materials 字段后端暂未读写，保持 NULL；target_project_id 指向
--    ws_project 派生项目（如库中无对应项目记录，可置 NULL，仅影响追溯展示）
-- ---------------------------------------------------------------------
INSERT INTO com_interaction
(id, user_id, action_type, target_type, target_id, target_version, target_project_id, bind_materials, created_at) VALUES
-- 收藏（教师互藏优质内容）
(9201, 10002, 'favorite', 'skill',       9101, NULL, NULL, NULL, '2026-08-10 09:12:00'),
(9202, 10003, 'favorite', 'skill',       9101, NULL, NULL, NULL, '2026-08-15 20:40:00'),
(9203, 10004, 'favorite', 'skill',       9101, NULL, NULL, NULL, '2026-08-20 08:05:00'),
(9204, 10002, 'favorite', 'lesson_case', 9103, NULL, NULL, NULL, '2026-08-19 10:30:00'),
(9205, 10005, 'favorite', 'lesson_case', 9103, NULL, NULL, NULL, '2026-08-25 14:22:00'),
(9206, 10001, 'favorite', 'skill',       9102, NULL, NULL, NULL, '2026-08-14 16:00:00'),
(9207, 10003, 'favorite', 'lesson_case', 9104, NULL, NULL, NULL, '2026-08-23 19:18:00'),
(9208, 10004, 'favorite', 'skill',       9111, NULL, NULL, NULL, '2026-09-04 11:11:00'),
(9209, 10005, 'favorite', 'lesson_case', 9112, NULL, NULL, NULL, '2026-09-06 08:47:00'),
-- 最近浏览（每用户每内容一条）
(9211, 10002, 'view', 'skill',       9101, NULL, NULL, NULL, '2026-09-12 08:30:00'),
(9212, 10003, 'view', 'skill',       9101, NULL, NULL, NULL, '2026-09-11 21:05:00'),
(9213, 10002, 'view', 'lesson_case', 9103, NULL, NULL, NULL, '2026-09-12 20:15:00'),
(9214, 10005, 'view', 'skill',       9102, NULL, NULL, NULL, '2026-09-10 13:40:00'),
(9215, 10001, 'view', 'lesson_case', 9104, NULL, NULL, NULL, '2026-09-09 15:26:00'),
(9216, 10004, 'view', 'skill',       9105, NULL, NULL, NULL, '2026-09-08 10:02:00'),
(9217, 10002, 'view', 'lesson_case', 9112, NULL, NULL, NULL, '2026-09-13 09:08:00'),
(9218, 10003, 'view', 'skill',       9111, NULL, NULL, NULL, '2026-09-07 17:33:00'),
-- 复用派生（target_version 记录来源版本；项目 ID 为占位，可按需替换/置 NULL）
(9221, 10002, 'derivation', 'skill',       9101, 2, 3001, NULL, '2026-08-29 10:00:00'),
(9222, 10005, 'derivation', 'lesson_case', 9103, 1, 3002, NULL, '2026-09-01 09:30:00'),
(9223, 10004, 'derivation', 'skill',       9105, 1, NULL,  NULL, '2026-09-06 16:45:00');

-- ---------------------------------------------------------------------
-- 3. 审核与举报 adm_audit
--    audit_type='audit'  : 投稿审核（reporter_id 存投稿人，reason 存提交备注）
--    audit_type='report' : 举报（reason 存举报原因，comment 存补充说明）
--    action 取值          : 审核侧 approve/reject/rework；举报侧 approve/offline/ignore/reject/restore
--    status               : pending（待处理）/ processed（已处置）——与 AdminModerationServiceImpl 写入值一致
-- ---------------------------------------------------------------------
INSERT INTO adm_audit
(id, audit_type, target_type, target_id, reporter_id, reason, handler_id, action, comment, status, created_at, processed_at) VALUES
-- ① 投稿审核 · 待办（进入管理端「内容审核」队列）
(9301, 'audit', 'lesson_case', 9106, 10003, '本人原创或已获得授权，请审核', NULL, NULL, NULL, 'pending', '2026-09-10 14:31:00', NULL),
(9302, 'audit', 'skill',       9107, 10004, '原创技能总结，附二次加工示例', NULL, NULL, NULL, 'pending', '2026-09-11 21:16:00', NULL),
-- ② 投稿审核 · 已办
(9303, 'audit', 'lesson_case', 9103, 10003, '本人原创或已获得授权', 90001, 'approve', '课件结构完整，互动设计合理，审核通过上架。', 'processed', '2026-08-18 16:21:00', '2026-08-19 09:10:00'),
(9304, 'audit', 'skill',       9105, 10005, '原创技能总结', 90001, 'approve', '角色轮换机制描述清楚，同意上架。', 'processed', '2026-09-01 08:41:00', '2026-09-01 19:30:00'),
(9305, 'audit', 'skill',       9109, 10002, '开场白合集，请审核', 90001, 'reject',  '内容为通用话术罗列，与技能包（可参数化复用）定位不符，不予上架。', 'processed', '2026-08-30 13:01:00', '2026-09-08 10:00:00'),
(9306, 'audit', 'lesson_case', 9108, 10005, '生物实验探究课案例', 90001, 'rework',  '缺少实验安全提示与器材清单页，请补充后重新提交。', 'processed', '2026-09-06 10:01:00', '2026-09-11 15:40:00'),
-- ③ 举报 · 待办
(9311, 'report', 'lesson_case', 9112, 10002, '涉嫌抄袭', NULL, NULL, NULL, 'pending', '2026-09-13 09:10:00', NULL),
(9312, 'report', 'skill',       9101, 10003, '内容含有错误知识', NULL, NULL, NULL, 'pending', '2026-09-13 10:25:00', NULL),
-- ④ 举报 · 已办
(9313, 'report', 'lesson_case', 9110, 10004, '该课件与他人公开发布的导数课件高度雷同', 90001, 'offline', '比对属实，侵犯原作者权益，已下架处理。', 'processed', '2026-09-12 20:00:00', '2026-09-13 11:00:00'),
(9314, 'report', 'skill',       9102, 10005, '题目答案有误', 90001, 'ignore',  '经复核为表述歧义而非错误，维持上架。', 'processed', '2026-09-10 18:30:00', '2026-09-11 09:15:00');

COMMIT;

-- ---------------------------------------------------------------------
-- 4. 自检查询（可选执行）：核对 mock 数据落库与关联关系
-- ---------------------------------------------------------------------
-- 内容分布：SELECT status, COUNT(*) FROM com_content WHERE id BETWEEN 9101 AND 9199 GROUP BY status;
-- 待办审核：SELECT id, target_type, target_id, reason FROM adm_audit WHERE id BETWEEN 9301 AND 9399 AND status = 'pending';
-- 互动统计：SELECT action_type, COUNT(*) FROM com_interaction WHERE id BETWEEN 9201 AND 9299 GROUP BY action_type;
-- 池内内容与计数：SELECT id, title, status, view_count, use_count FROM com_content WHERE id BETWEEN 9101 AND 9199;
