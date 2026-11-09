-- =====================================================================
-- 社区内容 & 热门榜单 · 批量 mock 数据（存储过程版）
-- =====================================================================
-- 目标        : 1) 新增 100 条 Skill + 100 条教学案例公开内容（社区列表扩容）
--               2) 精确构造 20 条上榜记录（错开日/周/月滚动窗口），热门榜扩容
-- 适用表      : com_content / com_interaction / com_like
-- 执行前提    : 已执行建表语句 + sql/upgrade_feature11_community_likes_ranking.sql
--               建议先执行 sql/mock_community_moderation.sql、sql/mock_hot_ranking.sql
-- 执行方式    : mysql CLI：mysql -u root -p < sql/mock_bulk_community.sql
--               （脚本使用 DELIMITER，图形工具需支持存储过程分隔符，如 Navicat/DataGrip）
-- 幂等策略    : 内容占用 com_content 9201~9300（skill）/ 9401~9500（lesson_case）段；
--               互动/点赞不指定主键（自增），删除时按 target_id 指向本段内容的行清理，
--               重复执行不会违反 com_like 唯一键，可反复导入
-- 用户 ID 约定: 作者/互动用户 10001~10005（与既有 mock 脚本一致）
-- 热度口径    : 与 ComContentMapper.selectRankCandidates / ServiceImpl.hotScore 一致——
--               热度分 = 窗口内 点赞×3 + 收藏×2 + 复用×4 + 浏览×0.2，
--               上榜门槛 = 窗口内 点赞+收藏+复用 ≥ 5（浏览不计门槛），内容须 status='public'
-- ---------------------------------------------------------------------
-- 榜单扩容设计（20 条新增上榜内容，窗口覆盖：日=近24h / 周=近7天 / 月=近30天）：
--   技能：9205/9210 日+周+月；9215/9220/9225/9230 周+月；9235/9240/9245/9250 仅月
--   案例：9405/9410 日+周+月；9415/9420/9425/9430/9445 周+月；9435/9440/9450 仅月
--   单条热度分：奇数序 15.4（3赞+1藏+1复用）/ 偶数序 20.4（4赞+2藏+1复用）
--   榜单效果（含前两个 mock 脚本的原有内容）：月榜 34 条 / 周榜 22 条 / 日榜 9 条
-- =====================================================================

USE a12;
SET NAMES utf8mb4;

-- ---------------------------------------------------------------------
-- 0. 清理本脚本数据段（保证脚本可重复执行）
-- ---------------------------------------------------------------------
DELETE FROM com_like        WHERE target_id BETWEEN 9201 AND 9599 AND target_type IN ('skill', 'lesson_case');
DELETE FROM com_interaction WHERE target_id BETWEEN 9201 AND 9599 AND target_type IN ('skill', 'lesson_case');
DELETE FROM com_content     WHERE id BETWEEN 9201 AND 9300;
DELETE FROM com_content     WHERE id BETWEEN 9401 AND 9500;

DELIMITER $$

-- ---------------------------------------------------------------------
-- 1. 批量生成 100 Skill + 100 教学案例
--    标题唯一性：每 20 条一个「学科+年级」块，块内主题轮换不重复，跨块学科不同
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS mock_bulk_community_content $$
CREATE PROCEDURE mock_bulk_community_content()
BEGIN
  DECLARE i INT DEFAULT 1;
  DECLARE v_created DATETIME;
  DECLARE v_subject VARCHAR(20);
  DECLARE v_grade VARCHAR(20);
  DECLARE v_topic VARCHAR(100);

  -- ① 100 条 Skill（9201~9300）
  WHILE i <= 100 DO
    SET v_created = DATE_SUB(NOW(), INTERVAL 1 + ((i - 1) MOD 25) DAY);
    SET v_subject = ELT(1 + ((i - 1) DIV 20), '语文', '数学', '英语', '物理', '化学');
    SET v_grade   = ELT(1 + ((i - 1) DIV 20), '高中', '初中', '小学', '高中', '初中');
    SET v_topic   = ELT(1 + ((i - 1) MOD 20),
      '情境导入设计', '课堂提问链设计', '小组合作任务分配', '错题归因讲评', '单元整体教学',
      '跨学科主题学习', '作业分层设计', '思维导图梳理', '实验探究组织', '项目式学习方案',
      '复习课结构化', '概念辨析教学', '读图析图训练', '口语表达训练', '写作支架搭建',
      '计算能力进阶', '课堂游戏化闯关', '知识点口诀记忆', '课堂即时反馈', '探究问题链设计');
    INSERT INTO com_content
    (id, content_type, author_id, title, description, subject, grade, lesson_type,
     content_data, input_variables, example_effect, version, version_history, license,
     status, is_top, view_count, use_count, created_at, updated_at)
    VALUES
    (9200 + i, 'skill', 10001 + ((i - 1) MOD 5),
     CONCAT(v_subject, '·', v_topic, '技能包'),
     CONCAT('面向', v_grade, v_subject, '课堂的', v_topic, '方法包：三段式教学流程拆解 + 任务卡模板 + 评价量表，可参数化复用到同类课时。'),
     v_subject, v_grade,
     ELT(1 + ((i - 1) MOD 5), '新授课', '复习课', '习题课', '实验课', '活动课'),
     CONCAT('{"source":"a12-skill-manual","summary":"', v_topic, '三段式流程","slide_outline":[{"slide_no":1,"title":"环节一·方法讲解","content_points":["流程拆解","示例演示"]},{"slide_no":2,"title":"环节二·任务实施","content_points":["任务卡发放","小组实施与巡视"]}],"recommended_tools":["任务卡","评价量表"]}'),
     '[{"key":"topic","label":"课程主题","type":"text","required":true},{"key":"grade","label":"年级","type":"select","options":["小学","初中","高中"],"required":true}]',
     '生成 6-8 页教学流程大纲，含任务卡与评价量表。',
     1,
     CONCAT('[{"version_number":1,"description":"首发投稿","created_at":"', DATE_FORMAT(v_created, '%Y-%m-%d %H:%i:%s'), '"}]'),
     ELT(1 + ((i - 1) MOD 3), 'CC BY-NC 4.0', 'CC BY-NC-SA 4.0', 'CC BY 4.0'),
     'public', 0, 60 + ((i * 37) MOD 300), 5 + ((i * 13) MOD 35), v_created, v_created);
    SET i = i + 1;
  END WHILE;

  -- ② 100 条教学案例（9401~9500）
  SET i = 1;
  WHILE i <= 100 DO
    SET v_created = DATE_SUB(NOW(), INTERVAL 1 + ((i - 1) MOD 25) DAY);
    SET v_subject = ELT(1 + ((i - 1) DIV 20), '语文', '数学', '英语', '物理', '地理');
    SET v_grade   = ELT(1 + ((i - 1) DIV 20), '小学', '小学', '初中', '初中', '高中');
    SET v_topic   = ELT(1 + ((i - 1) MOD 20),
      '传统节日探秘', '生活中的对称美', '水资源调查', '校园植物地图', '天气与生活',
      '声音的旅行', '光影成像游戏', '种子的旅行', '地图上的家乡', '垃圾分类行动',
      '桥梁结构探秘', '营养搭配小厨房', '古诗词里的科学', '四季变化观察', '交通安全体验',
      '校园运动会策划', '班级图书角管理', '社区服务实践', '时间测量小史', '探秘人工智能');
    INSERT INTO com_content
    (id, content_type, author_id, title, description, subject, grade, lesson_type,
     content_data, input_variables, example_effect, version, version_history, license,
     status, is_top, view_count, use_count, created_at, updated_at)
    VALUES
    (9400 + i, 'lesson_case', 10001 + ((i - 1) MOD 5),
     CONCAT(v_grade, v_subject, '《', v_topic, '》',
            ELT(1 + ((i - 1) MOD 5), '情境', '探究', '项目式', '读写结合', '复习'), '课案例'),
     CONCAT('以「', v_topic, '」为主线设计的', v_grade, v_subject, '课案例：含完整课件页面与课堂任务单，可在线预览或复用派生。'),
     v_subject, v_grade,
     ELT(1 + ((i - 1) MOD 5), '新授课', '复习课', '习题课', '实验课', '活动课'),
     CONCAT('{"source":"a12-html-ppt-workspace","project_id":null,"presentation_id":"ppt_', LPAD(9400 + i, 10, '0'),
            '","workspace_mode":"ppt","slides":[{"slide_no":1,"title":"情境导入","html_summary":"', v_topic,
            ' 情境页"},{"slide_no":2,"title":"核心探究","html_summary":"主问题探究任务"},{"slide_no":3,"title":"总结延伸","html_summary":"课堂小结与拓展任务"}]}'),
     NULL,
     '含完整页面与任务单，可在线预览。',
     1,
     CONCAT('[{"version_number":1,"description":"从创作工作台发布","created_at":"', DATE_FORMAT(v_created, '%Y-%m-%d %H:%i:%s'), '"}]'),
     ELT(1 + ((i - 1) MOD 3), 'CC BY-NC 4.0', 'CC BY-NC-SA 4.0', 'CC BY 4.0'),
     'public', 0, 60 + ((i * 41) MOD 260), 5 + ((i * 17) MOD 30), v_created, v_created);
    SET i = i + 1;
  END WHILE;
END$$

-- ---------------------------------------------------------------------
-- 2. 批量生成 20 条上榜记录的窗口内互动
--    k=1~10 → 技能 9205/9210/.../9250；k=11~20 → 案例 9405/9410/.../9450
--    奇数 k：3 赞 + 1 藏 + 1 复用（门槛 5，热度 15.4）
--    偶数 k：4 赞 + 2 藏 + 1 复用（门槛 7，热度 20.4）
--    v_h 为距现在的小时数：1/2/11/12 号位落在日榜窗口，3~6/13~16/19 号位周榜，其余月榜
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS mock_bulk_hot_ranking_interactions $$
CREATE PROCEDURE mock_bulk_hot_ranking_interactions()
BEGIN
  DECLARE k INT DEFAULT 1;
  DECLARE v_cid INT;
  DECLARE v_h INT;
  DECLARE v_type VARCHAR(20);

  WHILE k <= 20 DO
    IF k <= 10 THEN
      SET v_cid = 9200 + k * 5;
    ELSE
      SET v_cid = 9400 + (k - 10) * 5;
    END IF;
    SET v_type = IF(k <= 10, 'skill', 'lesson_case');
    SET v_h = CASE k
      WHEN 1 THEN 4  WHEN 2 THEN 9   WHEN 3 THEN 30  WHEN 4 THEN 55  WHEN 5 THEN 80
      WHEN 6 THEN 120 WHEN 7 THEN 200 WHEN 8 THEN 280 WHEN 9 THEN 360 WHEN 10 THEN 440
      WHEN 11 THEN 6 WHEN 12 THEN 14 WHEN 13 THEN 40 WHEN 14 THEN 65 WHEN 15 THEN 100
      WHEN 16 THEN 150 WHEN 17 THEN 220 WHEN 18 THEN 300 WHEN 19 THEN 140 ELSE 460 END;

    -- 点赞（奇数 3 个用户 / 偶数 4 个用户）
    INSERT INTO com_like (user_id, target_type, target_id, created_at) VALUES
      (10001, v_type, v_cid, DATE_SUB(NOW(), INTERVAL v_h HOUR)),
      (10002, v_type, v_cid, DATE_SUB(NOW(), INTERVAL v_h + 1 HOUR)),
      (10003, v_type, v_cid, DATE_SUB(NOW(), INTERVAL v_h + 2 HOUR));
    IF k MOD 2 = 0 THEN
      INSERT INTO com_like (user_id, target_type, target_id, created_at)
      VALUES (10004, v_type, v_cid, DATE_SUB(NOW(), INTERVAL v_h + 3 HOUR));
    END IF;

    -- 收藏（com_interaction，同人同内容仅一条）
    IF k MOD 2 = 1 THEN
      INSERT INTO com_interaction (user_id, action_type, target_type, target_id, created_at)
      VALUES (10004, 'favorite', v_type, v_cid, DATE_SUB(NOW(), INTERVAL v_h + 1 HOUR));
    ELSE
      INSERT INTO com_interaction (user_id, action_type, target_type, target_id, created_at) VALUES
        (10001, 'favorite', v_type, v_cid, DATE_SUB(NOW(), INTERVAL v_h + 1 HOUR)),
        (10005, 'favorite', v_type, v_cid, DATE_SUB(NOW(), INTERVAL v_h + 2 HOUR));
    END IF;

    -- 复用派生
    IF k MOD 2 = 1 THEN
      INSERT INTO com_interaction (user_id, action_type, target_type, target_id, created_at)
      VALUES (10005, 'derivation', v_type, v_cid, DATE_SUB(NOW(), INTERVAL v_h + 2 HOUR));
    ELSE
      INSERT INTO com_interaction (user_id, action_type, target_type, target_id, created_at)
      VALUES (10002, 'derivation', v_type, v_cid, DATE_SUB(NOW(), INTERVAL v_h + 3 HOUR));
    END IF;

    -- 浏览（每用户每内容一条）
    INSERT INTO com_interaction (user_id, action_type, target_type, target_id, created_at) VALUES
      (10001, 'view', v_type, v_cid, DATE_SUB(NOW(), INTERVAL v_h HOUR)),
      (10003, 'view', v_type, v_cid, DATE_SUB(NOW(), INTERVAL v_h + 1 HOUR));

    SET k = k + 1;
  END WHILE;
END$$

DELIMITER ;

-- ---------------------------------------------------------------------
-- 3. 执行批量生成（内容 + 互动同一事务提交）
-- ---------------------------------------------------------------------
START TRANSACTION;
CALL mock_bulk_community_content();
CALL mock_bulk_hot_ranking_interactions();

-- 冗余计数回填：卡片展示的 like_count/favorite_count 与互动行保持一致
UPDATE com_content c SET
  like_count = (SELECT COUNT(*) FROM com_like l
                WHERE l.target_type = c.content_type AND l.target_id = c.id),
  favorite_count = (SELECT COUNT(*) FROM com_interaction i
                    WHERE i.action_type = 'favorite'
                      AND i.target_type = c.content_type AND i.target_id = c.id);

COMMIT;

-- ---------------------------------------------------------------------
-- 4. 清理临时存储过程
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS mock_bulk_community_content;
DROP PROCEDURE IF EXISTS mock_bulk_hot_ranking_interactions;

-- ---------------------------------------------------------------------
-- 5. 自检查询（可选执行）
-- ---------------------------------------------------------------------
-- 内容分布：
-- SELECT content_type, status, COUNT(*) FROM com_content
-- WHERE (id BETWEEN 9201 AND 9300 OR id BETWEEN 9401 AND 9500) GROUP BY content_type, status;
--
-- ★月榜模拟（与 selectRankCandidates 同口径，新增 20 条 + 原有 14 条 = 34 条）：
-- SELECT c.id, c.title, c.content_type,
--        COALESCE(l.like_cnt,0)*3 + COALESCE(s.fav_cnt,0)*2 + COALESCE(s.use_cnt,0)*4 + COALESCE(s.view_cnt,0)*0.2 AS hot_score
-- FROM com_content c
-- LEFT JOIN (SELECT target_id, COUNT(*) AS like_cnt FROM com_like
--            WHERE created_at >= NOW() - INTERVAL 30 DAY GROUP BY target_id) l ON l.target_id = c.id
-- LEFT JOIN (SELECT target_id, SUM(action_type='favorite') AS fav_cnt, SUM(action_type='derivation') AS use_cnt,
--                   SUM(action_type='view') AS view_cnt
--            FROM com_interaction WHERE action_type IN ('favorite','derivation','view')
--              AND created_at >= NOW() - INTERVAL 30 DAY GROUP BY target_id) s ON s.target_id = c.id
-- WHERE c.status='public'
--   AND (COALESCE(l.like_cnt,0)+COALESCE(s.fav_cnt,0)+COALESCE(s.use_cnt,0)) >= 5
-- ORDER BY hot_score DESC;
--
-- 注意：榜单优先读 Redis ZSET（community:rank:{type}:{period}），定时任务每 10 分钟重建；
--       导入本脚本后如需立即生效，可删除对应 Redis 键或等待下一轮重建。
-- =====================================================================
