-- =============================================
-- 演示种子：题库与组卷 + 公共资源来源登记（MySQL 库 a12）
-- 依赖：本地库已存在 username='bbb' 的教师账号（owner/上传人用子查询取其 id）
-- 可重复执行：先删后插，仅清理 92xxxx/93xxxx 演示号段
-- 结构对齐：QuestionBankService.validateQuestion / savePaper、ResourceProvenance.validate
-- =============================================

DELETE FROM qb_review   WHERE question_id BETWEEN 920001 AND 920099;
DELETE FROM qb_paper    WHERE id          BETWEEN 920101 AND 920199;
DELETE FROM qb_question WHERE id          BETWEEN 920001 AND 920099;
DELETE FROM adm_resource WHERE id         BETWEEN 930001 AND 930099;

-- ---------- 题目（4 approved + 1 pending + 1 draft + 1 rejected）----------
INSERT INTO qb_question (id,owner_id,subject,grade,question_type,difficulty,stem,knowledge_points,content_json,status,review_note,reviewer_id,revision) VALUES
(920001,(SELECT id FROM sys_user WHERE username='bbb'),'物理','高一','single','easy',
 '物体做匀变速直线运动，初速度为 2 m/s，加速度为 3 m/s²，3 s 后速度大小为（ ）',
 '匀变速直线运动;速度公式',
 '{"subject":"物理","grade":"高一","question_type":"single","difficulty":"easy","stem":"物体做匀变速直线运动，初速度为 2 m/s，加速度为 3 m/s²，3 s 后速度大小为（ ）","knowledge_points":"匀变速直线运动;速度公式","analysis":"由 v = v0 + at，得 v = 2 + 3×3 = 11 m/s，故选 B。","formula":"v = v0 + at","chemical":"","options":["8 m/s","11 m/s","9 m/s","6 m/s"],"answer":"B"}',
 'approved','',NULL,1),
(920002,(SELECT id FROM sys_user WHERE username='bbb'),'物理','高一','judgment','easy',
 '做自由落体运动的物体，速度变化率恒定。',
 '自由落体;加速度',
 '{"subject":"物理","grade":"高一","question_type":"judgment","difficulty":"easy","stem":"做自由落体运动的物体，速度变化率恒定。","knowledge_points":"自由落体;加速度","analysis":"自由落体是初速度为零的匀加速运动，加速度恒为 g，速度变化率即加速度，故保持恒定。","formula":"","chemical":"","options":[],"answer":"正确"}',
 'approved','',NULL,1),
(920003,(SELECT id FROM sys_user WHERE username='bbb'),'物理','高一','blank','easy',
 '匀变速直线运动中，速度与时间的关系式为____（用 v0、a、t 表示）。',
 '匀变速直线运动;速度公式',
 '{"subject":"物理","grade":"高一","question_type":"blank","difficulty":"easy","stem":"匀变速直线运动中，速度与时间的关系式为____（用 v0、a、t 表示）。","knowledge_points":"匀变速直线运动;速度公式","analysis":"基本公式直接记忆：v = v0 + at。","formula":"v = v0 + at","chemical":"","options":[],"answer":"v = v0 + at"}',
 'approved','',NULL,1),
(920004,(SELECT id FROM sys_user WHERE username='bbb'),'物理','高一','short','medium',
 '简述动能定理的内容，并写出其表达式。',
 '动能定理;功能关系',
 '{"subject":"物理","grade":"高一","question_type":"short","difficulty":"medium","stem":"简述动能定理的内容，并写出其表达式。","knowledge_points":"动能定理;功能关系","analysis":"合外力对物体所做的功等于物体动能的变化量；表达式 W合 = ΔEk = Ek2 - Ek1。使用时注意 W 为所有外力做功的代数和。","formula":"W合 = ΔEk","chemical":"","options":[],"answer":"合外力对物体做的功等于物体动能的变化，W合 = ΔEk = Ek2 - Ek1。"}',
 'approved','',NULL,1),
(920005,(SELECT id FROM sys_user WHERE username='bbb'),'数学','高一','single','easy',
 '不等式 x² - 3x + 2 > 0 的解集是（ ）',
 '一元二次不等式',
 '{"subject":"数学","grade":"高一","question_type":"single","difficulty":"easy","stem":"不等式 x² - 3x + 2 > 0 的解集是（ ）","knowledge_points":"一元二次不等式","analysis":"因式分解得 (x-1)(x-2) > 0，由二次函数图象知解为 x < 1 或 x > 2，故选 B。","formula":"(x-1)(x-2) > 0","chemical":"","options":["1 < x < 2","x < 1 或 x > 2","x > 2","x < 1"],"answer":"B"}',
 'approved','',NULL,1),
(920006,(SELECT id FROM sys_user WHERE username='bbb'),'物理','高一','single','medium',
 '下列关于功的说法正确的是（ ）',
 '功的概念',
 '{"subject":"物理","grade":"高一","question_type":"single","difficulty":"medium","stem":"下列关于功的说法正确的是（ ）","knowledge_points":"功的概念","analysis":"力对物体做功的两个要素是力和沿力方向的位移；力与位移垂直时不做功，故选 A。","formula":"W = F·s·cosθ","chemical":"","options":["力和物体在力的方向上发生的位移是做功的两个要素","力越大做功一定越多","位移越大做功一定越多","摩擦力一定对物体做负功"],"answer":"A"}',
 'pending','',NULL,1),
(920007,(SELECT id FROM sys_user WHERE username='bbb'),'语文','高一','short','medium',
 '《劝学》开篇以“青出于蓝”设喻，有何论证作用？',
 '比喻论证;文言文阅读',
 '{"subject":"语文","grade":"高一","question_type":"short","difficulty":"medium","stem":"《劝学》开篇以“青出于蓝”设喻，有何论证作用？","knowledge_points":"比喻论证;文言文阅读","analysis":"以染料提取中颜色加深为喻，说明学习可以使人提高和改变，把抽象道理具体化，引出中心论点“学不可以已”。","formula":"","chemical":"","options":[],"answer":"以生活现象作比，化抽象为具体，自然引出并支撑“学不可以已”的中心论点。"}',
 'draft','',NULL,1),
(920008,(SELECT id FROM sys_user WHERE username='bbb'),'物理','高一','judgment','medium',
 '滑动摩擦力的方向一定与物体运动方向相反。',
 '滑动摩擦力;受力分析',
 '{"subject":"物理","grade":"高一","question_type":"judgment","difficulty":"medium","stem":"滑动摩擦力的方向一定与物体运动方向相反。","knowledge_points":"滑动摩擦力;受力分析","analysis":"滑动摩擦力方向与相对运动方向相反；当地面为参考系时它可以与运动方向相同（如轻放上传送带的物体），因此该说法错误。","formula":"","chemical":"","options":[],"answer":"错误"}',
 'rejected','题干未限定参考系，表述不严谨，请补充说明后重新投稿',(SELECT id FROM sys_user WHERE username='bbb'),2);

-- ---------- 审核记录 ----------
INSERT INTO qb_review (question_id,reviewer_id,decision,note,question_revision) VALUES
(920001,(SELECT id FROM sys_user WHERE username='bbb'),'approved','后台直接发布',1),
(920008,(SELECT id FROM sys_user WHERE username='bbb'),'rejected','题干未限定参考系，表述不严谨。',1);

-- ---------- 试卷（物理，引用 approved 题目做快照）----------
INSERT INTO qb_paper (id,owner_id,title,subject,duration_minutes,total_score,content_json,revision) VALUES
(920101,(SELECT id FROM sys_user WHERE username='bbb'),'高一物理·匀变速运动单元测（演示卷A）','物理',45,20.00,
 '{"items":[{"question_id":920001,"score":5,"source_revision":1,"question":{"subject":"物理","grade":"高一","question_type":"single","difficulty":"easy","stem":"物体做匀变速直线运动，初速度为 2 m/s，加速度为 3 m/s²，3 s 后速度大小为（ ）","knowledge_points":"匀变速直线运动;速度公式","analysis":"由 v = v0 + at，得 v = 2 + 3×3 = 11 m/s，故选 B。","formula":"v = v0 + at","chemical":"","options":["8 m/s","11 m/s","9 m/s","6 m/s"],"answer":"B"}},{"question_id":920002,"score":5,"source_revision":1,"question":{"subject":"物理","grade":"高一","question_type":"judgment","difficulty":"easy","stem":"做自由落体运动的物体，速度变化率恒定。","knowledge_points":"自由落体;加速度","analysis":"自由落体是初速度为零的匀加速运动，加速度恒为 g，速度变化率即加速度，故保持恒定。","formula":"","chemical":"","options":[],"answer":"正确"}},{"question_id":920003,"score":10,"source_revision":1,"question":{"subject":"物理","grade":"高一","question_type":"blank","difficulty":"easy","stem":"匀变速直线运动中，速度与时间的关系式为____（用 v0、a、t 表示）。","knowledge_points":"匀变速直线运动;速度公式","analysis":"基本公式直接记忆：v = v0 + at。","formula":"v = v0 + at","chemical":"","options":[],"answer":"v = v0 + at"}}]}',1),
(920102,(SELECT id FROM sys_user WHERE username='bbb'),'高一物理·期中热身（演示卷B）','物理',40,10.00,
 '{"items":[{"question_id":920004,"score":10,"source_revision":1,"question":{"subject":"物理","grade":"高一","question_type":"short","difficulty":"medium","stem":"简述动能定理的内容，并写出其表达式。","knowledge_points":"动能定理;功能关系","analysis":"合外力对物体所做的功等于物体动能的变化量；表达式 W合 = ΔEk = Ek2 - Ek1。使用时注意 W 为所有外力做功的代数和。","formula":"W合 = ΔEk","chemical":"","options":[],"answer":"合外力对物体做的功等于物体动能的变化，W合 = ΔEk = Ek2 - Ek1。"}}]}',1);

-- ---------- 公共资源（带来源登记，供治理演示）----------
INSERT INTO adm_resource (id,resource_type,title,subject,grade,file_url,template_data,thumbnail,description,file_size,status,uploaded_by,ai_index_status,ai_indexed_at,source_metadata) VALUES
(930001,'textbook','人教版物理必修第一册（演示）','物理','高一',NULL,NULL,NULL,'教材目录与章节结构示意，来源已登记为官方。',NULL,1,
 (SELECT id FROM sys_user WHERE username='bbb'),'completed',NOW(),
 '{"source_kind":"textbook","source_type":"official","source_url":"https://www.moe.gov.cn/jyb_sjzl/moe_364/moe_302/moe_309/202006/t20200603_462199.html","source_note":"教育部普通中小学教学用书目录","version_label":"人教版必修第一册（2019 年审定）","version_year":"2019","authority_level":"official","valid_until":""}'),
(930002,'question_bank','人教社配套题库节选（演示）','物理','高一',NULL,NULL,NULL,'人教社官网公开配套资源节选，来源登记为出版社。',NULL,1,
 (SELECT id FROM sys_user WHERE username='bbb'),'completed',NOW(),
 '{"source_kind":"other","source_type":"publisher","source_url":"https://www.pep.com.cn/gzdlzx/","source_note":"人教社官网配套资源栏目","version_label":"人教版配套资源包 2023","version_year":"2023","authority_level":"publisher","valid_until":""}'),
(930003,'media','2026 秋季时政素材包（演示）','政治','高三',NULL,NULL,NULL,'教师自整时政素材，时政类必填有效期。',NULL,1,
 (SELECT id FROM sys_user WHERE username='bbb'),'completed',NOW(),
 '{"source_kind":"current_affairs","source_type":"teacher","source_url":"","source_note":"教师自行整理，仅校内演示使用","version_label":"2026 秋季时政合集","version_year":"2026","authority_level":"general","valid_until":"2026-12-31"}');
