-- =====================================================================
-- 热门榜单补充 mock 数据（社区「本月热门」日/周/月榜 · 功能11）
-- =====================================================================
-- 目标        : 丰富社区热门榜单——新增 8 条公开内容（4 Skill + 4 教学案例），
--               并补齐滚动窗口内的点赞/收藏/复用/浏览互动，使日/周/月三个榜单
--               每个页签（Skill / 教学案例）均有 2~7 条上榜内容。
-- 适用表      : com_content（新增公开内容）/ com_interaction / com_like
-- 执行前提    : 1) 已执行建表语句 + sql/upgrade_feature11_community_likes_ranking.sql
--               2) 建议先执行 sql/mock_community_moderation.sql（本脚本独立可跑，
--                  但其内容段 9101~9199 与本脚本 9121~9160 相邻，先跑基础脚本再跑本脚本，
--                  重复导入顺序：先 mock_community_moderation.sql，再本脚本）
-- 幂等策略    : 内容占用 9121~9160 段、互动 9501~9599 段、点赞 9601~9699 段，
--               重复执行前先删除同段数据及指向该内容段的孤儿互动/点赞，可反复导入
-- 用户 ID 约定: 教师 10001~10005（与 mock_community_moderation.sql 一致）
-- 热度口径    : 与 ComContentMapper.selectRankCandidates / ServiceImpl.hotScore 一致——
--               热度分 = 窗口内 点赞×3 + 收藏×2 + 复用×4 + 浏览×0.2，
--               上榜门槛 = 窗口内 点赞+收藏+复用 ≥ 5（浏览不计门槛），内容须 status='public'
-- 时间戳策略  : 互动统一 NOW() - INTERVAL 相对值，保证重复执行时始终落在榜单滚动窗口内
-- ---------------------------------------------------------------------
-- 上榜设计（窗口覆盖：日=近24h / 周=近7天 / 月=近30天）：
--   内容   类型        日  周  月   月榜热度分（近似）
--   9121   skill       ✓   ✓   ✓   26.8（技能月榜第1）
--   9122   skill       -   ✓   ✓   22.6
--   9123   skill       -   ✓   ✓   17.6
--   9124   skill       -   -   ✓   20.4（仅月榜）
--   9125   lesson_case ✓   ✓   ✓   26.8（案例月榜第1）
--   9126   lesson_case -   ✓   ✓   17.6
--   9127   lesson_case -   -   ✓   17.4（仅月榜）
--   9128   lesson_case -   -   ✓   14.4（仅月榜）
--   基础脚本原有上榜内容不受影响；9111 化学配平技能仍保留为「够不着门槛」的对照。
-- =====================================================================

USE a12;
SET NAMES utf8mb4;

START TRANSACTION;

-- ---------------------------------------------------------------------
-- 0. 清理本脚本同段数据（保证脚本可重复执行）
-- ---------------------------------------------------------------------
DELETE FROM com_like        WHERE target_id BETWEEN 9121 AND 9160 AND target_type IN ('skill', 'lesson_case');
DELETE FROM com_interaction WHERE target_id BETWEEN 9121 AND 9160 AND target_type IN ('skill', 'lesson_case');
DELETE FROM com_content     WHERE id BETWEEN 9121 AND 9160;

-- ---------------------------------------------------------------------
-- 1. 新增公开内容 com_content（8 条：4 skill / 4 lesson_case，全部 public）
--    created_at 取近 30 天内固定日期，view_count/use_count 为卡片展示的累计值（静态）
-- ---------------------------------------------------------------------
INSERT INTO com_content
(id, content_type, author_id, title, description, subject, grade, lesson_type, content_data, input_variables, example_effect, version, version_history, license, status, is_top, view_count, use_count, created_at, updated_at) VALUES
-- ① Skill · 小学英语自然拼读（日/周/月榜 · 技能榜首）
(9121, 'skill', 10005, '小学英语单词自然拼读教学技能',
 '按音形对应规律拆解单词发音：听音辨形、拆音拼读、韵律操巩固三步走，覆盖 CVC/CVCe 常见结构，可复用到任意单词表。',
 '英语', '小学', '新授课',
 '{"source":"a12-skill-manual","summary":"自然拼读三步教学法","slide_outline":[{"slide_no":1,"title":"听音辨形","content_points":["minimal pairs 听辨游戏","字母音-形对应卡"]},{"slide_no":2,"title":"拆音拼读","content_points":["CVC 单词手臂拼读法","CVCe 静音 e 对比组"]}],"recommended_tools":["拼读卡片","韵律操视频"]}',
 '[{"key":"unit_words","label":"本单元单词表","type":"textarea","required":true},{"key":"grade_band","label":"年级段","type":"select","options":["一年级","二年级","三年级"],"required":true}]',
 '生成拼读训练大纲 6-8 页，含课堂韵律操环节说明与单词拼读任务卡。',
 1, '[{"version_number":1,"description":"首发投稿","created_at":"2026-09-20 10:30:00"}]',
 'CC BY-NC 4.0', 'public', 0, 268, 26, '2026-09-20 10:30:00', '2026-09-20 10:30:00'),

-- ② Skill · PBL 驱动问题设计（周/月榜）
(9122, 'skill', 10003, '项目式学习驱动问题设计技能',
 '把单元目标转译为真实驱动问题：情境锚定、问题拆解、里程碑产出三段设计法，配评价量规生成规则。',
 '通用', '通用', '活动课',
 '{"source":"a12-skill-manual","summary":"驱动问题设计三段法","slide_outline":[{"slide_no":1,"title":"情境锚定","content_points":["真实情境素材选择原则","驱动问题表述模板"]},{"slide_no":2,"title":"问题拆解","content_points":["驱动问题→子问题链","里程碑产出清单"]}]}',
 '[{"key":"unit_goal","label":"单元教学目标","type":"textarea","required":true},{"key":"duration_weeks","label":"项目周期（周）","type":"number","required":true}]',
 '生成含驱动问题、子问题链与里程碑表的 PBL 方案页，附小组评价量规。',
 1, '[{"version_number":1,"description":"首发投稿","created_at":"2026-09-22 15:20:00"}]',
 'CC BY-NC 4.0', 'public', 0, 176, 15, '2026-09-22 15:20:00', '2026-09-22 15:20:00'),

-- ③ Skill · 高中议论文升格（周/月榜）
(9123, 'skill', 10001, '高中议论文升格训练技能',
 '按「论点立得住—论据跟得上—论证转得动」三级升格路径批改议论文，每级配典型病文与升格示范。',
 '语文', '高中', '习题课',
 '{"source":"a12-skill-manual","summary":"议论文三级升格批改法","slide_outline":[{"slide_no":1,"title":"论点升格","content_points":["中心论点聚焦训练","分论点并列转递进"]},{"slide_no":2,"title":"论证升格","content_points":["例证分析句式支架","假设分析与因果分析"]}]}',
 '[{"key":"essay_topic","label":"作文题","type":"text","required":true},{"key":"student_draft","label":"学生习作片段","type":"textarea","required":false}]',
 '生成病文对照与升格示范讲评页，含课堂训练任务单。',
 1, '[{"version_number":1,"description":"首发投稿","created_at":"2026-09-24 09:10:00"}]',
 'CC BY-NC 4.0', 'public', 0, 132, 11, '2026-09-24 09:10:00', '2026-09-24 09:10:00'),

-- ④ Skill · 课堂即时评价（仅月榜）
(9124, 'skill', 10002, '课堂即时评价与反馈技能',
 '用「口头点评 + 二维量表 + 即时投票」组合做课堂即时评价，含反馈话术模板与常见误用提醒。',
 '通用', '通用', '新授课',
 '{"source":"a12-skill-manual","summary":"课堂即时评价组合拳","slide_outline":[{"slide_no":1,"title":"反馈话术模板","content_points":["描述式点评三句式","跟进追问策略"]},{"slide_no":2,"title":"即时投票","content_points":["举手投票 vs 工具投票","结果即时归因"]}]}',
 '[{"key":"lesson_segment","label":"评价环节","type":"text","required":true},{"key":"class_size","label":"班级人数","type":"number","required":false}]',
 '生成评价量表与反馈话术卡，可直接嵌入课件尾页。',
 1, '[{"version_number":1,"description":"首发投稿","created_at":"2026-09-12 14:00:00"}]',
 'CC BY 4.0', 'public', 0, 95, 8, '2026-09-12 14:00:00', '2026-09-12 14:00:00'),

-- ⑤ 教学案例 · 初中地理季风气候（日/周/月榜 · 案例榜首）
(9125, 'lesson_case', 10004, '初中地理《季风气候》读图析图课案例',
 '以气温曲线与降水柱状图判读为主线：读图提取信息、对比归纳季风特征、绘制简易风向示意图三环节，含读图任务单。',
 '地理', '初中', '新授课',
 '{"source":"a12-html-ppt-workspace","project_id":null,"presentation_id":"ppt_5a8c2e6f9b","workspace_mode":"ppt","slides":[{"slide_no":1,"title":"读图热身","html_summary":"北京与广州气温降水对比图"},{"slide_no":2,"title":"析图归纳","html_summary":"季风特征归纳表"},{"slide_no":3,"title":"绘图应用","html_summary":"风向示意图绘制任务"}],"lesson_plan":{"teaching_goals":["能判读气温曲线与降水柱状图","能归纳季风气候特征"],"duration_minutes":45}}',
 NULL,
 '含读图任务单与绘图任务页，适合多媒体教室投屏使用。',
 1, '[{"version_number":1,"description":"从创作工作台发布","created_at":"2026-09-26 16:40:00"}]',
 'CC BY-NC-SA 4.0', 'public', 0, 243, 22, '2026-09-26 16:40:00', '2026-09-26 16:40:00'),

-- ⑥ 教学案例 · 小学数学分数初步认识（周/月榜）
(9126, 'lesson_case', 10002, '小学数学《分数的初步认识》情境课案例',
 '以分月饼情境切入：折纸表示二分之一、涂色表示四分之一、生活实例找分数，含错例辨析页。',
 '数学', '小学', '新授课',
 '{"source":"a12-html-ppt-workspace","project_id":null,"presentation_id":"ppt_3d7f1a9c2e","workspace_mode":"ppt","slides":[{"slide_no":1,"title":"分月饼","html_summary":"平均分情境导入"},{"slide_no":2,"title":"折纸涂色","html_summary":"动手表示分数"},{"slide_no":3,"title":"错例辨析","html_summary":"没有平均分的反例"}]}',
 NULL,
 '含动手操作环节与错例辨析页，页面可在线预览。',
 1, '[{"version_number":1,"description":"从创作工作台发布","created_at":"2026-09-28 11:25:00"}]',
 'CC BY-NC 4.0', 'public', 0, 154, 13, '2026-09-28 11:25:00', '2026-09-28 11:25:00'),

-- ⑦ 教学案例 · 高中化学原电池（仅月榜）
(9127, 'lesson_case', 10001, '高中化学《原电池》实验探究课案例',
 '铜锌原电池实验探究：观察电流表偏转、书写电极反应式、设计水果电池拓展任务，含实验安全提示页。',
 '化学', '高中', '实验课',
 '{"source":"a12-html-ppt-workspace","project_id":null,"presentation_id":"ppt_9b4e7c1d8a","workspace_mode":"ppt","slides":[{"slide_no":1,"title":"实验观察","html_summary":"铜锌原电池装置与电流表偏转"},{"slide_no":2,"title":"原理建构","html_summary":"电极反应式书写"},{"slide_no":3,"title":"拓展任务","html_summary":"水果电池设计"}]}',
 NULL,
 '含实验记录单与安全提示页，适合实验室多媒体环境。',
 1, '[{"version_number":1,"description":"从创作工作台发布","created_at":"2026-09-15 10:05:00"}]',
 'CC BY-NC 4.0', 'public', 0, 118, 9, '2026-09-15 10:05:00', '2026-09-15 10:05:00'),

-- ⑧ 教学案例 · 初中英语听说课（仅月榜）
(9128, 'lesson_case', 10005, '初中英语《My weekend plan》听说课案例',
 '围绕周末计划展开听说训练：听力捕捉 be going to 句型、结对问答、小组汇报三环节，含听力原文页。',
 '英语', '初中', '新授课',
 '{"source":"a12-html-ppt-workspace","project_id":null,"presentation_id":"ppt_2c6b8d4f0a","workspace_mode":"ppt","slides":[{"slide_no":1,"title":"Lead-in","html_summary":"周末计划图片预测"},{"slide_no":2,"title":"Listening","html_summary":"be going to 句型听力任务"},{"slide_no":3,"title":"Pair work","html_summary":"结对问答与汇报"}]}',
 NULL,
 '含听力任务链与口语支架页，适合听说课教学。',
 1, '[{"version_number":1,"description":"从创作工作台发布","created_at":"2026-09-10 19:30:00"}]',
 'CC BY-NC 4.0', 'public', 0, 87, 6, '2026-09-10 19:30:00', '2026-09-10 19:30:00');

-- ---------------------------------------------------------------------
-- 2. 近期互动 com_interaction（9501~9599 段）
--    favorite：同人同内容仅一条；view：每用户每内容一条；derivation：target_version=1
--    target_project_id 保持 NULL（bind_materials 后端暂未读写，保持 NULL）
-- ---------------------------------------------------------------------

-- 近期收藏（19 条）
INSERT INTO com_interaction
(id, user_id, action_type, target_type, target_id, target_version, target_project_id, bind_materials, created_at) VALUES
(9501, 10005, 'favorite', 'skill',       9121, NULL, NULL, NULL, NOW() - INTERVAL 6 HOUR),
(9502, 10001, 'favorite', 'skill',       9121, NULL, NULL, NULL, NOW() - INTERVAL 3 DAY),
(9503, 10004, 'favorite', 'skill',       9121, NULL, NULL, NULL, NOW() - INTERVAL 5 DAY),
(9504, 10002, 'favorite', 'skill',       9122, NULL, NULL, NULL, NOW() - INTERVAL 2 DAY),
(9505, 10004, 'favorite', 'skill',       9122, NULL, NULL, NULL, NOW() - INTERVAL 5 DAY),
(9506, 10005, 'favorite', 'skill',       9122, NULL, NULL, NULL, NOW() - INTERVAL 6 DAY),
(9507, 10002, 'favorite', 'skill',       9123, NULL, NULL, NULL, NOW() - INTERVAL 4 DAY),
(9508, 10003, 'favorite', 'skill',       9123, NULL, NULL, NULL, NOW() - INTERVAL 6 DAY),
(9509, 10001, 'favorite', 'skill',       9124, NULL, NULL, NULL, NOW() - INTERVAL 10 DAY),
(9510, 10005, 'favorite', 'skill',       9124, NULL, NULL, NULL, NOW() - INTERVAL 15 DAY),
(9511, 10001, 'favorite', 'lesson_case', 9125, NULL, NULL, NULL, NOW() - INTERVAL 5 HOUR),
(9512, 10003, 'favorite', 'lesson_case', 9125, NULL, NULL, NULL, NOW() - INTERVAL 2 DAY),
(9513, 10005, 'favorite', 'lesson_case', 9125, NULL, NULL, NULL, NOW() - INTERVAL 4 DAY),
(9514, 10001, 'favorite', 'lesson_case', 9126, NULL, NULL, NULL, NOW() - INTERVAL 3 DAY),
(9515, 10004, 'favorite', 'lesson_case', 9126, NULL, NULL, NULL, NOW() - INTERVAL 6 DAY),
(9516, 10002, 'favorite', 'lesson_case', 9127, NULL, NULL, NULL, NOW() - INTERVAL 10 DAY),
(9517, 10003, 'favorite', 'lesson_case', 9127, NULL, NULL, NULL, NOW() - INTERVAL 14 DAY),
(9518, 10002, 'favorite', 'lesson_case', 9128, NULL, NULL, NULL, NOW() - INTERVAL 17 DAY),
(9519, 10004, 'favorite', 'lesson_case', 9128, NULL, NULL, NULL, NOW() - INTERVAL 20 DAY);

-- 近期浏览（23 条；每用户每内容仅一条）
INSERT INTO com_interaction
(id, user_id, action_type, target_type, target_id, target_version, target_project_id, bind_materials, created_at) VALUES
(9531, 10001, 'view', 'skill',       9121, NULL, NULL, NULL, NOW() - INTERVAL 1 HOUR),
(9532, 10002, 'view', 'skill',       9121, NULL, NULL, NULL, NOW() - INTERVAL 1 DAY),
(9533, 10004, 'view', 'skill',       9121, NULL, NULL, NULL, NOW() - INTERVAL 2 DAY),
(9534, 10005, 'view', 'skill',       9121, NULL, NULL, NULL, NOW() - INTERVAL 6 DAY),
(9535, 10001, 'view', 'skill',       9122, NULL, NULL, NULL, NOW() - INTERVAL 2 DAY),
(9536, 10003, 'view', 'skill',       9122, NULL, NULL, NULL, NOW() - INTERVAL 4 DAY),
(9537, 10005, 'view', 'skill',       9122, NULL, NULL, NULL, NOW() - INTERVAL 6 DAY),
(9538, 10001, 'view', 'skill',       9123, NULL, NULL, NULL, NOW() - INTERVAL 4 DAY),
(9539, 10002, 'view', 'skill',       9123, NULL, NULL, NULL, NOW() - INTERVAL 3 DAY),
(9540, 10004, 'view', 'skill',       9123, NULL, NULL, NULL, NOW() - INTERVAL 5 DAY),
(9541, 10001, 'view', 'skill',       9124, NULL, NULL, NULL, NOW() - INTERVAL 8 DAY),
(9542, 10005, 'view', 'skill',       9124, NULL, NULL, NULL, NOW() - INTERVAL 14 DAY),
(9543, 10001, 'view', 'lesson_case', 9125, NULL, NULL, NULL, NOW() - INTERVAL 2 HOUR),
(9544, 10002, 'view', 'lesson_case', 9125, NULL, NULL, NULL, NOW() - INTERVAL 9 HOUR),
(9545, 10004, 'view', 'lesson_case', 9125, NULL, NULL, NULL, NOW() - INTERVAL 1 DAY),
(9546, 10005, 'view', 'lesson_case', 9125, NULL, NULL, NULL, NOW() - INTERVAL 3 DAY),
(9547, 10001, 'view', 'lesson_case', 9126, NULL, NULL, NULL, NOW() - INTERVAL 2 DAY),
(9548, 10003, 'view', 'lesson_case', 9126, NULL, NULL, NULL, NOW() - INTERVAL 3 DAY),
(9549, 10005, 'view', 'lesson_case', 9126, NULL, NULL, NULL, NOW() - INTERVAL 5 DAY),
(9550, 10002, 'view', 'lesson_case', 9127, NULL, NULL, NULL, NOW() - INTERVAL 9 DAY),
(9551, 10005, 'view', 'lesson_case', 9127, NULL, NULL, NULL, NOW() - INTERVAL 13 DAY),
(9552, 10002, 'view', 'lesson_case', 9128, NULL, NULL, NULL, NOW() - INTERVAL 16 DAY),
(9553, 10003, 'view', 'lesson_case', 9128, NULL, NULL, NULL, NOW() - INTERVAL 18 DAY);

-- 近期复用派生（10 条）
INSERT INTO com_interaction
(id, user_id, action_type, target_type, target_id, target_version, target_project_id, bind_materials, created_at) VALUES
(9561, 10002, 'derivation', 'skill',       9121, 1, NULL, NULL, NOW() - INTERVAL 4 HOUR),
(9562, 10003, 'derivation', 'skill',       9121, 1, NULL, NULL, NOW() - INTERVAL 5 DAY),
(9563, 10001, 'derivation', 'skill',       9122, 1, NULL, NULL, NOW() - INTERVAL 3 DAY),
(9564, 10004, 'derivation', 'skill',       9123, 1, NULL, NULL, NOW() - INTERVAL 6 DAY),
(9565, 10003, 'derivation', 'skill',       9124, 1, NULL, NULL, NOW() - INTERVAL 9 DAY),
(9566, 10002, 'derivation', 'lesson_case', 9125, 1, NULL, NULL, NOW() - INTERVAL 7 HOUR),
(9567, 10005, 'derivation', 'lesson_case', 9125, 1, NULL, NULL, NOW() - INTERVAL 3 DAY),
(9568, 10005, 'derivation', 'lesson_case', 9126, 1, NULL, NULL, NOW() - INTERVAL 4 DAY),
(9569, 10004, 'derivation', 'lesson_case', 9127, 1, NULL, NULL, NOW() - INTERVAL 11 DAY),
(9570, 10001, 'derivation', 'lesson_case', 9128, 1, NULL, NULL, NOW() - INTERVAL 19 DAY);

-- ---------------------------------------------------------------------
-- 3. 近期点赞 com_like（9601~9699 段；唯一键同人同内容仅一条）
--    分布：9121/9125 各 4 赞（含 24h 内 3 赞，撑起日榜），其余 2~4 赞错开窗口
-- ---------------------------------------------------------------------
INSERT INTO com_like
(id, user_id, target_type, target_id, created_at) VALUES
(9601, 10001, 'skill',       9121, NOW() - INTERVAL 2 HOUR),
(9602, 10002, 'skill',       9121, NOW() - INTERVAL 5 HOUR),
(9603, 10003, 'skill',       9121, NOW() - INTERVAL 9 HOUR),
(9604, 10004, 'skill',       9121, NOW() - INTERVAL 2 DAY),
(9605, 10001, 'skill',       9122, NOW() - INTERVAL 2 DAY),
(9606, 10002, 'skill',       9122, NOW() - INTERVAL 3 DAY),
(9607, 10004, 'skill',       9122, NOW() - INTERVAL 4 DAY),
(9608, 10005, 'skill',       9122, NOW() - INTERVAL 6 DAY),
(9609, 10002, 'skill',       9123, NOW() - INTERVAL 3 DAY),
(9610, 10003, 'skill',       9123, NOW() - INTERVAL 4 DAY),
(9611, 10005, 'skill',       9123, NOW() - INTERVAL 5 DAY),
(9612, 10001, 'skill',       9124, NOW() - INTERVAL 8 DAY),
(9613, 10003, 'skill',       9124, NOW() - INTERVAL 9 DAY),
(9614, 10004, 'skill',       9124, NOW() - INTERVAL 12 DAY),
(9615, 10005, 'skill',       9124, NOW() - INTERVAL 14 DAY),
(9616, 10001, 'lesson_case', 9125, NOW() - INTERVAL 3 HOUR),
(9617, 10002, 'lesson_case', 9125, NOW() - INTERVAL 8 HOUR),
(9618, 10003, 'lesson_case', 9125, NOW() - INTERVAL 10 HOUR),
(9619, 10005, 'lesson_case', 9125, NOW() - INTERVAL 2 DAY),
(9620, 10001, 'lesson_case', 9126, NOW() - INTERVAL 2 DAY),
(9621, 10003, 'lesson_case', 9126, NOW() - INTERVAL 3 DAY),
(9622, 10004, 'lesson_case', 9126, NOW() - INTERVAL 5 DAY),
(9623, 10002, 'lesson_case', 9127, NOW() - INTERVAL 9 DAY),
(9624, 10004, 'lesson_case', 9127, NOW() - INTERVAL 10 DAY),
(9625, 10005, 'lesson_case', 9127, NOW() - INTERVAL 12 DAY),
(9626, 10001, 'lesson_case', 9128, NOW() - INTERVAL 16 DAY),
(9627, 10003, 'lesson_case', 9128, NOW() - INTERVAL 18 DAY);

-- ---------------------------------------------------------------------
-- 4. 冗余计数回填：卡片展示的 like_count/favorite_count 与互动行保持一致
--    （榜单读窗口聚合不受影响，但列表卡片「N 赞 / N 收藏」直接读冗余列）
-- ---------------------------------------------------------------------
UPDATE com_content c SET
  like_count = (SELECT COUNT(*) FROM com_like l
                WHERE l.target_type = c.content_type AND l.target_id = c.id),
  favorite_count = (SELECT COUNT(*) FROM com_interaction i
                    WHERE i.action_type = 'favorite'
                      AND i.target_type = c.content_type AND i.target_id = c.id);

COMMIT;

-- ---------------------------------------------------------------------
-- 5. 自检查询（可选执行）
-- ---------------------------------------------------------------------
-- 新增内容分布：
-- SELECT id, content_type, title, status, like_count, favorite_count, use_count
-- FROM com_content WHERE id BETWEEN 9121 AND 9160;
--
-- ★月榜模拟（技能，与 selectRankCandidates 同口径，应返回 9121/9122/9123/9124 + 原有 3 条）：
-- SELECT c.id, c.title,
--        COALESCE(l.like_cnt,0)*3 + COALESCE(s.fav_cnt,0)*2 + COALESCE(s.use_cnt,0)*4 + COALESCE(s.view_cnt,0)*0.2 AS hot_score
-- FROM com_content c
-- LEFT JOIN (SELECT target_id, COUNT(*) AS like_cnt FROM com_like
--            WHERE created_at >= NOW() - INTERVAL 30 DAY GROUP BY target_id) l ON l.target_id = c.id
-- LEFT JOIN (SELECT target_id, SUM(action_type='favorite') AS fav_cnt, SUM(action_type='derivation') AS use_cnt,
--                   SUM(action_type='view') AS view_cnt
--            FROM com_interaction WHERE action_type IN ('favorite','derivation','view')
--              AND created_at >= NOW() - INTERVAL 30 DAY GROUP BY target_id) s ON s.target_id = c.id
-- WHERE c.status='public' AND c.content_type='skill'
--   AND (COALESCE(l.like_cnt,0)+COALESCE(s.fav_cnt,0)+COALESCE(s.use_cnt,0)) >= 5
-- ORDER BY hot_score DESC;
--
-- 注意：榜单优先读 Redis ZSET（community:rank:{type}:{period}），定时任务每 10 分钟重建；
--       导入本脚本后如需立即生效，可删除对应 Redis 键或等待下一轮重建。
-- =====================================================================
