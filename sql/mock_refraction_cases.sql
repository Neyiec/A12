-- =====================================================================
-- 初中物理「光的折射」专题教学案例 · 补充 mock 数据
-- =====================================================================
-- 目标        : 新增 5 条初中物理光的折射主题教学案例（公开池），每条案例名称、
--               浏览量、点赞量均不相同，标题均含「光的折射」
-- 适用表      : com_content / com_interaction / com_like
-- 执行前提    : 已执行建表语句 + sql/upgrade_feature11_community_likes_ranking.sql；
--               与 mock_community_moderation.sql / mock_hot_ranking.sql /
--               mock_bulk_community.sql 均不冲突（内容段 9611~9615 为本脚本专用，
--               批量脚本按 target_id 9201~9599 清理互动，不会波及本脚本数据）
-- 幂等策略    : 先删 9611~9615 段内容及其互动/点赞，再插入，可反复导入
-- 用户 ID 约定: 教师 10001~10005（com_like 同人同内容仅一条，窗口内点赞需不同用户凑量）
-- 案例差异设计：
--   ID   案例名称                                     浏览量  点赞  收藏  复用  月榜
--   9611 初中物理《光的折射》实验探究课案例            368     5     2     1    ✓(23.6)
--   9612 初中物理《生活中的光的折射》情境课案例          295     4     1     1    ✓(18.4)
--   9613 初中物理《光的折射规律应用》习题课案例          243     3     1     1    ✓(15.2)
--   9614 初中物理《光的折射》海市蜃楼主题拓展课案例      187     2     1     1    ✗(门槛4<5)
--   9615 初中物理《光的折射》分组实验数字化课案例        132     1     1     0    ✗(门槛2<5)
-- =====================================================================

USE a12;
SET NAMES utf8mb4;

START TRANSACTION;

-- ---------------------------------------------------------------------
-- 0. 清理同段数据（保证脚本可重复执行）
-- ---------------------------------------------------------------------
DELETE FROM com_like        WHERE target_id BETWEEN 9611 AND 9615 AND target_type IN ('skill', 'lesson_case');
DELETE FROM com_interaction WHERE target_id BETWEEN 9611 AND 9615 AND target_type IN ('skill', 'lesson_case');
DELETE FROM com_content     WHERE id BETWEEN 9611 AND 9615;

-- ---------------------------------------------------------------------
-- 1. 案例内容 com_content（5 条，全部 public · 初中物理 · 标题含「光的折射」）
-- ---------------------------------------------------------------------
INSERT INTO com_content
(id, content_type, author_id, title, description, subject, grade, lesson_type, content_data, input_variables, example_effect, version, version_history, license, status, is_top, view_count, use_count, created_at, updated_at) VALUES
-- ① 实验探究（榜单候选：月榜 23.6 分，案例榜前三）
(9611, 'lesson_case', 10004, '初中物理《光的折射》实验探究课案例',
 '以「叉鱼」情境驱动：激光笔模拟叉鱼瞄准、折射规律分组探究、生活现象解释三环节，含实验记录单与光路图页。',
 '物理', '初中', '实验课',
 '{"source":"a12-html-ppt-workspace","project_id":null,"presentation_id":"ppt_8e4b2f6a1c","workspace_mode":"ppt","slides":[{"slide_no":1,"title":"叉鱼情境","html_summary":"渔夫叉鱼瞄准偏折动画"},{"slide_no":2,"title":"实验探究","html_summary":"激光笔光路演示与记录单"},{"slide_no":3,"title":"规律归纳","html_summary":"折射规律三线共面归纳页"},{"slide_no":4,"title":"现象解释","html_summary":"池水变浅等生活现象解释"}],"lesson_plan":{"teaching_goals":["能说出光的折射规律","能用折射规律解释叉鱼等现象"],"duration_minutes":45}}',
 NULL,
 '含实验记录单与光路图页，适合实验室多媒体环境。',
 1, '[{"version_number":1,"description":"从创作工作台发布","created_at":"2026-10-02 09:20:00"}]',
 'CC BY-NC 4.0', 'public', 0, 368, 12, '2026-10-02 09:20:00', '2026-10-02 09:20:00'),

-- ② 生活情境
(9612, 'lesson_case', 10002, '初中物理《生活中的光的折射》情境课案例',
 '从硬币复现、筷子「折断」两个小实验切入，串联海市蜃楼视频情境，引导学生自主归纳折射规律并解释现象。',
 '物理', '初中', '新授课',
 '{"source":"a12-html-ppt-workspace","project_id":null,"presentation_id":"ppt_3c9d7e5b2f","workspace_mode":"ppt","slides":[{"slide_no":1,"title":"硬币复现","html_summary":"碗中硬币注水复现实验"},{"slide_no":2,"title":"筷子折断","html_summary":"筷子弯折现象慢镜头"},{"slide_no":3,"title":"海市蜃楼","html_summary":"成因视频与示意光路"}]}',
 NULL,
 '小实验取材方便，适合常规教室演示。',
 1, '[{"version_number":1,"description":"从创作工作台发布","created_at":"2026-09-28 14:10:00"}]',
 'CC BY-NC-SA 4.0', 'public', 0, 295, 9, '2026-09-28 14:10:00', '2026-09-28 14:10:00'),

-- ③ 习题课
(9613, 'lesson_case', 10001, '初中物理《光的折射规律应用》习题课案例',
 '折射作图三步法（定界面—定法线—定折射光线）+ 典型例题三层变式，含易错点辨析与作图规范页。',
 '物理', '初中', '习题课',
 '{"source":"a12-html-ppt-workspace","project_id":null,"presentation_id":"ppt_6f2a8c4d1e","workspace_mode":"ppt","slides":[{"slide_no":1,"title":"作图三步法","html_summary":"折射作图流程支架"},{"slide_no":2,"title":"例题精讲","html_summary":"水折射典型例题"},{"slide_no":3,"title":"变式训练","html_summary":"三层变式题组"},{"slide_no":4,"title":"易错辨析","html_summary":"折射角与入射角关系易错点"}]}',
 NULL,
 '作图支架清晰，适合折射规律课后巩固。',
 1, '[{"version_number":1,"description":"从创作工作台发布","created_at":"2026-09-20 10:30:00"}]',
 'CC BY-NC 4.0', 'public', 0, 243, 7, '2026-09-20 10:30:00', '2026-09-20 10:30:00'),

-- ④ 拓展课（未达榜单门槛：窗口内点赞+收藏+复用 = 4 < 5）
(9614, 'lesson_case', 10003, '初中物理《光的折射》海市蜃楼主题拓展课案例',
 '以海市蜃楼真实影像为主题：成因猜想、分层空气模型、光路示意绘制、科普短文写作四任务串。',
 '物理', '初中', '活动课',
 '{"source":"a12-html-ppt-workspace","project_id":null,"presentation_id":"ppt_9b5e3a7c2d","workspace_mode":"ppt","slides":[{"slide_no":1,"title":"影像导入","html_summary":"海市蜃楼真实影像"},{"slide_no":2,"title":"成因猜想","html_summary":"分层空气模型"},{"slide_no":3,"title":"拓展任务","html_summary":"光路示意与科普写作"}]}',
 NULL,
 '跨学科拓展素材，适合社团或课后服务。',
 1, '[{"version_number":1,"description":"从创作工作台发布","created_at":"2026-09-24 16:45:00"}]',
 'CC BY 4.0', 'public', 0, 187, 5, '2026-09-24 16:45:00', '2026-09-24 16:45:00'),

-- ⑤ 数字化分组实验（未达榜单门槛：窗口内点赞+收藏 = 2 < 5）
(9615, 'lesson_case', 10005, '初中物理《光的折射》分组实验数字化课案例',
 '用手机光学测量 App 与激光光学平台分组测量折射角，数据表自动汇总拟合，含器材清单与安全提示页。',
 '物理', '初中', '实验课',
 '{"source":"a12-html-ppt-workspace","project_id":null,"presentation_id":"ppt_4d8c1f6e3a","workspace_mode":"ppt","slides":[{"slide_no":1,"title":"器材与安全","html_summary":"分组器材清单与激光安全"},{"slide_no":2,"title":"分组测量","html_summary":"折射角测量任务分工"},{"slide_no":3,"title":"数据拟合","html_summary":"折射角-入射角数据表"}]}',
 NULL,
 '数字化测量环节新颖，适合有平板/手机的班级。',
 1, '[{"version_number":1,"description":"从创作工作台发布","created_at":"2026-10-05 19:30:00"}]',
 'CC BY-NC 4.0', 'public', 0, 132, 3, '2026-10-05 19:30:00', '2026-10-05 19:30:00');

-- ---------------------------------------------------------------------
-- 2. 互动 com_interaction（收藏/浏览/复用，同人同内容各仅一条）
-- ---------------------------------------------------------------------
INSERT INTO com_interaction
(id, user_id, action_type, target_type, target_id, target_version, target_project_id, bind_materials, created_at) VALUES
-- 收藏：9611×2 / 9612~9615×1
(9581, 10001, 'favorite', 'lesson_case', 9611, NULL, NULL, NULL, NOW() - INTERVAL 8 HOUR),
(9582, 10003, 'favorite', 'lesson_case', 9611, NULL, NULL, NULL, NOW() - INTERVAL 2 DAY),
(9583, 10004, 'favorite', 'lesson_case', 9612, NULL, NULL, NULL, NOW() - INTERVAL 3 DAY),
(9584, 10002, 'favorite', 'lesson_case', 9613, NULL, NULL, NULL, NOW() - INTERVAL 9 DAY),
(9585, 10001, 'favorite', 'lesson_case', 9614, NULL, NULL, NULL, NOW() - INTERVAL 14 DAY),
(9586, 10005, 'favorite', 'lesson_case', 9615, NULL, NULL, NULL, NOW() - INTERVAL 19 DAY),
-- 复用派生：9611~9614×1（9615 无复用）
(9587, 10002, 'derivation', 'lesson_case', 9611, 1, NULL, NULL, NOW() - INTERVAL 1 DAY),
(9588, 10005, 'derivation', 'lesson_case', 9612, 1, NULL, NULL, NOW() - INTERVAL 4 DAY),
(9589, 10003, 'derivation', 'lesson_case', 9613, 1, NULL, NULL, NOW() - INTERVAL 11 DAY),
(9590, 10004, 'derivation', 'lesson_case', 9614, 1, NULL, NULL, NOW() - INTERVAL 15 DAY),
-- 最近浏览（每用户每内容一条）
(9591, 10001, 'view', 'lesson_case', 9611, NULL, NULL, NULL, NOW() - INTERVAL 5 HOUR),
(9592, 10004, 'view', 'lesson_case', 9611, NULL, NULL, NULL, NOW() - INTERVAL 2 DAY),
(9593, 10005, 'view', 'lesson_case', 9611, NULL, NULL, NULL, NOW() - INTERVAL 4 DAY),
(9594, 10002, 'view', 'lesson_case', 9612, NULL, NULL, NULL, NOW() - INTERVAL 3 DAY),
(9595, 10005, 'view', 'lesson_case', 9612, NULL, NULL, NULL, NOW() - INTERVAL 6 DAY),
(9596, 10004, 'view', 'lesson_case', 9613, NULL, NULL, NULL, NOW() - INTERVAL 10 DAY),
(9597, 10002, 'view', 'lesson_case', 9614, NULL, NULL, NULL, NOW() - INTERVAL 15 DAY),
(9598, 10001, 'view', 'lesson_case', 9615, NULL, NULL, NULL, NOW() - INTERVAL 18 DAY),
(9599, 10002, 'view', 'lesson_case', 9615, NULL, NULL, NULL, NOW() - INTERVAL 20 DAY);

-- ---------------------------------------------------------------------
-- 3. 点赞 com_like（5/4/3/2/1 条错档，窗口内同人同内容仅一条）
-- ---------------------------------------------------------------------
INSERT INTO com_like
(id, user_id, target_type, target_id, created_at) VALUES
-- 9611：5 赞（周榜窗口内）
(9641, 10001, 'lesson_case', 9611, NOW() - INTERVAL 6 HOUR),
(9642, 10002, 'lesson_case', 9611, NOW() - INTERVAL 1 DAY),
(9643, 10003, 'lesson_case', 9611, NOW() - INTERVAL 2 DAY),
(9644, 10004, 'lesson_case', 9611, NOW() - INTERVAL 3 DAY),
(9645, 10005, 'lesson_case', 9611, NOW() - INTERVAL 5 DAY),
-- 9612：4 赞
(9646, 10001, 'lesson_case', 9612, NOW() - INTERVAL 2 DAY),
(9647, 10002, 'lesson_case', 9612, NOW() - INTERVAL 3 DAY),
(9648, 10003, 'lesson_case', 9612, NOW() - INTERVAL 5 DAY),
(9649, 10004, 'lesson_case', 9612, NOW() - INTERVAL 6 DAY),
-- 9613：3 赞（仅月榜窗口）
(9650, 10001, 'lesson_case', 9613, NOW() - INTERVAL 8 DAY),
(9651, 10003, 'lesson_case', 9613, NOW() - INTERVAL 10 DAY),
(9652, 10005, 'lesson_case', 9613, NOW() - INTERVAL 12 DAY),
-- 9614：2 赞
(9653, 10002, 'lesson_case', 9614, NOW() - INTERVAL 13 DAY),
(9654, 10004, 'lesson_case', 9614, NOW() - INTERVAL 16 DAY),
-- 9615：1 赞
(9655, 10003, 'lesson_case', 9615, NOW() - INTERVAL 18 DAY);

-- ---------------------------------------------------------------------
-- 4. 冗余计数回填（卡片「N 赞 / N 收藏」与互动行一致）
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
-- 五条案例卡片数据（浏览量/点赞量各不相同）：
-- SELECT id, title, view_count, like_count, favorite_count, use_count
-- FROM com_content WHERE id BETWEEN 9611 AND 9615 ORDER BY view_count DESC;
--
-- 折射专题月榜候选（应返回 9611/9612/9613，热度 23.6/18.4/15.2）：
-- SELECT c.id, c.title,
--        COALESCE(l.like_cnt,0)*3 + COALESCE(s.fav_cnt,0)*2 + COALESCE(s.use_cnt,0)*4 + COALESCE(s.view_cnt,0)*0.2 AS hot_score
-- FROM com_content c
-- LEFT JOIN (SELECT target_id, COUNT(*) AS like_cnt FROM com_like
--            WHERE created_at >= NOW() - INTERVAL 30 DAY GROUP BY target_id) l ON l.target_id = c.id
-- LEFT JOIN (SELECT target_id, SUM(action_type='favorite') AS fav_cnt, SUM(action_type='derivation') AS use_cnt,
--                   SUM(action_type='view') AS view_cnt
--            FROM com_interaction WHERE action_type IN ('favorite','derivation','view')
--              AND created_at >= NOW() - INTERVAL 30 DAY GROUP BY target_id) s ON s.target_id = c.id
-- WHERE c.status='public' AND c.id BETWEEN 9611 AND 9615
--   AND (COALESCE(l.like_cnt,0)+COALESCE(s.fav_cnt,0)+COALESCE(s.use_cnt,0)) >= 5
-- ORDER BY hot_score DESC;
--
-- 注意：榜单优先读 Redis ZSET（community:rank:{type}:{period}），定时任务每 10 分钟重建；
--       导入本脚本后如需立即生效，可删除对应 Redis 键或等待下一轮重建。
-- =====================================================================
