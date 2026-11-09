-- =============================================
-- 演示种子：AI 备课批量生成 + 提示词版本管理 + 公共资源巡检 + 课程双图谱（PostgreSQL，Python AI 服务库）
-- 学习路径不落库（/learning-path 由图谱实时计算），有图谱即可演示
-- 前置：把下方 v_user 的 'REPLACE_BBB_USER_ID' 改成 bbb 的用户 id
--       （在 MySQL 库 a12 执行 SELECT id FROM sys_user WHERE username='bbb'; 取数字）
-- 可重复执行：先删后插，仅清理 demo 前缀与指定批次
-- 结构对齐：batch_store.confirm / batch_worker.import_payload / agent_evolution
-- =============================================

DO $$
DECLARE
    v_user varchar := 'REPLACE_BBB_USER_ID';  -- ★ 必改：bbb 的数字用户 id（字符串形式）
    v_plan varchar := 'b0a7c11d00000000000000000000a001';
    v_item1 varchar := 'b0a7c11e00000000000000000000a001';
    v_item2 varchar := 'b0a7c11e00000000000000000000a002';
    v_item3 varchar := 'b0a7c11e00000000000000000000a003';
BEGIN
    -- 清理（顺序：先子表/引用方）
    DELETE FROM a12_prompt_outcome        WHERE run_id LIKE 'demo-run-%';
    DELETE FROM a12_prompt_run            WHERE id    LIKE 'demo-run-%';
    DELETE FROM a12_prompt_release_history WHERE actor = 'demo';
    UPDATE a12_prompt_release SET canary_version = NULL, canary_percent = 0 WHERE id = 1;
    DELETE FROM a12_prompt_version        WHERE fingerprint LIKE 'demo-%';
    DELETE FROM a12_batch_item            WHERE batch_id = v_plan;
    DELETE FROM a12_batch_job             WHERE id       = v_plan;
    DELETE FROM a12_batch_plan            WHERE id       = v_plan;
    DELETE FROM a12_public_source_patrol  WHERE actor LIKE 'demo%';
    DELETE FROM a12_graph_evidence        WHERE user_id = v_user AND course_id LIKE 'demo-%';
    DELETE FROM a12_course_graph_version  WHERE user_id = v_user AND course_id LIKE 'demo-%';
    DELETE FROM a12_course_graph          WHERE user_id = v_user AND course_id LIKE 'demo-%';

    -- ---------- 批量生成：1 个已确认批次（2 ready + 1 failed，failed 次数 1 可现场重试）----------
    INSERT INTO a12_batch_plan (id,user_id,session_id,revision,status,payload) VALUES
    (v_plan, v_user, NULL, 1, 'confirmed',
     '{"title":"高一物理·机械能守恒（演示批次）","subject":"物理","grade":"高一","textbook_version":"人教版 2019 必修第一册","requirements":"演示数据：按章节生成课件；教材版本：人教版 2019 必修第一册","reasoning_effort":"low","enable_rag":false,"basis":"file","needs_input":false,"items":[{"id":"b0a7c11e00000000000000000000a001","title":"功与功率","min_pages":6,"max_pages":12,"hours":"1 课时","objectives":"理解功与功率的概念与计算"},{"id":"b0a7c11e00000000000000000000a002","title":"动能与动能定理","min_pages":6,"max_pages":12,"hours":"1 课时","objectives":"掌握动能定理及其应用"},{"id":"b0a7c11e00000000000000000000a003","title":"机械能守恒定律","min_pages":6,"max_pages":12,"hours":"1 课时","objectives":"理解机械能守恒条件并会应用"}]}'::jsonb);

    INSERT INTO a12_batch_job (id,user_id,title,theme,status,zip_status,zip_error,include_partial) VALUES
    (v_plan, v_user, '高一物理·机械能守恒（演示批次）', '素白风', 'partial_failed', 'idle', '', FALSE);

    INSERT INTO a12_batch_item (id,batch_id,user_id,item_order,title,payload,output,status,stage,progress,attempts,error) VALUES
    (v_item1, v_plan, v_user, 1, '功与功率',
     '{"id":"b0a7c11e00000000000000000000a001","title":"功与功率","min_pages":6,"max_pages":12,"hours":"1 课时","objectives":"理解功与功率的概念与计算","subject":"物理","grade":"高一","enable_rag":false,"reasoning_effort":"low","requirements":"演示数据：按章节生成课件；教材版本：人教版 2019 必修第一册"}'::jsonb,
     '{"prompt_version":1,"outline":{"sections":[{"title":"功与功率"},{"title":"功率的计算"}]},"presentation":{"metadata":{"theme":"素白风","generated_by":"演示数据"},"slides":[{"title":"功与功率","html":"<section class=''slide''><h1>功与功率</h1><ul><li>功的公式：W = F·s·cosθ</li><li>正功与负功的判断</li></ul></section>"},{"title":"功率","html":"<section class=''slide''><h1>功率</h1><ul><li>定义式：P = W / t</li><li>瞬时功率：P = F·v</li></ul></section>"},{"title":"课堂练习","html":"<section class=''slide''><h1>课堂练习</h1><ul><li>已知 F=10N，s=2m，同向，求 W</li><li>答案：W = 20 J</li></ul></section>"}]}}'::jsonb,
     'ready', '已生成，等待保存到个人项目', 100, 1, ''),
    (v_item2, v_plan, v_user, 2, '动能与动能定理',
     '{"id":"b0a7c11e00000000000000000000a002","title":"动能与动能定理","min_pages":6,"max_pages":12,"hours":"1 课时","objectives":"掌握动能定理及其应用","subject":"物理","grade":"高一","enable_rag":false,"reasoning_effort":"low","requirements":"演示数据：按章节生成课件；教材版本：人教版 2019 必修第一册"}'::jsonb,
     '{"prompt_version":1,"outline":{"sections":[{"title":"动能"},{"title":"动能定理"}]},"presentation":{"metadata":{"theme":"素白风","generated_by":"演示数据"},"slides":[{"title":"动能","html":"<section class=''slide''><h1>动能</h1><ul><li>表达式：Ek = ½mv²</li><li>动能是标量，只有正值</li></ul></section>"},{"title":"动能定理","html":"<section class=''slide''><h1>动能定理</h1><ul><li>W合 = ΔEk</li><li>合外力做功等于动能变化</li></ul></section>"},{"title":"例题","html":"<section class=''slide''><h1>例题</h1><ul><li>m=2kg，v 从 2m/s 增至 4m/s，求 W合</li><li>答案：12 J</li></ul></section>"}]}}'::jsonb,
     'ready', '已生成，等待保存到个人项目', 100, 1, ''),
    (v_item3, v_plan, v_user, 3, '机械能守恒定律',
     '{"id":"b0a7c11e00000000000000000000a003","title":"机械能守恒定律","min_pages":6,"max_pages":12,"hours":"1 课时","objectives":"理解机械能守恒条件并会应用","subject":"物理","grade":"高一","enable_rag":false,"reasoning_effort":"low","requirements":"演示数据：按章节生成课件；教材版本：人教版 2019 必修第一册"}'::jsonb,
     '{}'::jsonb,
     'failed', '生成失败', 40, 1, '模型响应超时（演示数据）');

    -- ---------- 提示词版本：新增 2 个实验版本（不改 active，canary 0 不影响线上）----------
    INSERT INTO a12_prompt_version (id,name,instruction,layout_rule,evidence,parent_version,created_by,fingerprint,template_bundle) VALUES
    (9201,'演示-双栏图示版','在标准流程基础上采用双栏排版：左侧要点、右侧配图或公式，标题不超过 16 字。','每页要点 3-5 条；公式独立成行居中。','{"note":"演示用实验版本","author":"demo"}'::jsonb,1,'demo','demo-dual-col-v2','{}'::jsonb),
    (9202,'演示-精简复习版','输出更精简：每页要点不超过 3 条，以结论和例题为主，适合复习课节奏。','每页要点不超过 3 条；保留章节进度页。','{"note":"演示用实验版本","author":"demo"}'::jsonb,1,'demo','demo-concise-v3','{}'::jsonb);

    UPDATE a12_prompt_release SET canary_version = 9201, canary_percent = 0 WHERE id = 1;
    -- 想现场演示灰度放量：UPDATE a12_prompt_release SET canary_version=9201, canary_percent=10 WHERE id=1;
    -- 复位：UPDATE a12_prompt_release SET canary_version=9201, canary_percent=0 WHERE id=1;

    INSERT INTO a12_prompt_release_history (actor,action,reason,before_state,after_state) VALUES
    ('demo','create','新增演示版本：双栏图示版','{"canary_version":null,"canary_percent":0}'::jsonb,'{"canary_version":9201,"canary_percent":0}'::jsonb),
    ('demo','canary','配置演示灰度目标版本，比例暂为 0','{"canary_version":null,"canary_percent":0}'::jsonb,'{"canary_version":9201,"canary_percent":0}'::jsonb);

    INSERT INTO a12_prompt_run (id,user_id,version_id,release_revision,cohort,runtime_run_id,theme,status,completed_at) VALUES
    ('demo-run-0001', v_user, 9201, 1, 'canary', NULL, '素白风', 'completed', NOW()),
    ('demo-run-0002', v_user, 9201, 1, 'canary', NULL, '素白风', 'completed', NOW()),
    ('demo-run-0003', v_user, 1,    1, 'control', NULL, '素白风', 'completed', NOW());

    INSERT INTO a12_prompt_outcome (run_id,action,event_key,project_id) VALUES
    ('demo-run-0001','generate','ppt.generated',NULL),
    ('demo-run-0001','save','ppt.saved',NULL),
    ('demo-run-0002','generate','ppt.generated',NULL),
    ('demo-run-0003','generate','ppt.generated',NULL);

    -- ---------- 公共资源巡检记录 ----------
    INSERT INTO a12_public_source_patrol (actor,checked_count,warning_count) VALUES
    ('demo-admin', 12, 1),
    ('demo-admin', 15, 0);

    -- ---------- 课程双图谱（结构对齐 course_graph.validate_graph：concept/skill 双图、supports 必须知识点→技能、整体无环）----------
    INSERT INTO a12_course_graph (user_id,course_id,title,version,graph_data) VALUES
    (v_user, 'demo-physics-mechanics', '高一物理·机械能守恒（演示课程）', 1,
     ('{"nodes":['
     || '{"id":"k1","label":"匀变速直线运动","kind":"concept","description":"速度随时间均匀变化的直线运动，是运动学的基础模型。","subject":"物理","difficulty":0.3,"exam_frequency":0.8,"bloom":"understand","resource_ids":[],"mastery_standard":"能用公式描述匀变速运动并解释图像含义。","assessment":"能用公式描述匀变速运动并解释图像含义。","position":{"x":60,"y":60}},'
     || '{"id":"k2","label":"功","kind":"concept","description":"力与沿力方向位移的乘积，能量转化的量度。","subject":"物理","difficulty":0.3,"exam_frequency":0.9,"bloom":"understand","resource_ids":[],"mastery_standard":"会计算恒力做功并判断正负。","assessment":"会计算恒力做功并判断正负。","position":{"x":200,"y":60}},'
     || '{"id":"k3","label":"功率","kind":"concept","description":"单位时间内做的功，分平均功率与瞬时功率。","subject":"物理","difficulty":0.4,"exam_frequency":0.8,"bloom":"apply","resource_ids":[],"mastery_standard":"区分平均功率与瞬时功率并完成计算。","assessment":"区分平均功率与瞬时功率并完成计算。","position":{"x":340,"y":60}},'
     || '{"id":"k4","label":"动能","kind":"concept","description":"物体因运动而具有的能量，Ek = ½mv²。","subject":"物理","difficulty":0.4,"exam_frequency":0.9,"bloom":"understand","resource_ids":[],"mastery_standard":"写出动能表达式并说明其标量性。","assessment":"写出动能表达式并说明其标量性。","position":{"x":200,"y":220}},'
     || '{"id":"k5","label":"势能","kind":"concept","description":"重力势能与弹性势能，与相对位置有关。","subject":"物理","difficulty":0.4,"exam_frequency":0.7,"bloom":"understand","resource_ids":[],"mastery_standard":"会计算重力势能并理解其相对性。","assessment":"会计算重力势能并理解其相对性。","position":{"x":340,"y":220}},'
     || '{"id":"k6","label":"动能定理","kind":"concept","description":"合外力做的功等于物体动能的变化。","subject":"物理","difficulty":0.6,"exam_frequency":0.9,"bloom":"apply","resource_ids":[],"mastery_standard":"能用动能定理求解多过程问题。","assessment":"能用动能定理求解多过程问题。","position":{"x":270,"y":380}},'
     || '{"id":"k7","label":"机械能守恒定律","kind":"concept","description":"只有重力或弹力做功时，机械能总量保持不变。","subject":"物理","difficulty":0.7,"exam_frequency":0.95,"bloom":"apply","resource_ids":[],"mastery_standard":"能判断守恒条件并用守恒律列方程解题。","assessment":"能判断守恒条件并用守恒律列方程解题。","position":{"x":270,"y":540}},'
     || '{"id":"s1","label":"受力与做功分析","kind":"skill","description":"对给定情境完成受力分析并计算各力做功。","subject":"物理","difficulty":0.5,"exam_frequency":0.8,"bloom":"apply","resource_ids":[],"mastery_standard":"能独立完成受力分析并计算各力做功。","assessment":"给定情境能画出受力图并列表计算各力做功。","position":{"x":60,"y":220}},'
     || '{"id":"s2","label":"功率的计算","kind":"skill","description":"运用 P=W/t 与 P=Fv 求解实际问题。","subject":"物理","difficulty":0.4,"exam_frequency":0.7,"bloom":"apply","resource_ids":[],"mastery_standard":"能用 P=Fv 估算机车启动问题。","assessment":"能用 P=Fv 估算机车启动问题。","position":{"x":440,"y":60}},'
     || '{"id":"s3","label":"动能定理解题","kind":"skill","description":"多过程、变力情境下应用动能定理。","subject":"物理","difficulty":0.7,"exam_frequency":0.9,"bloom":"analyze","resource_ids":[],"mastery_standard":"能拆解多过程并分步列动能定理方程。","assessment":"能拆解多过程并分步列动能定理方程。","position":{"x":150,"y":460}},'
     || '{"id":"s4","label":"机械能守恒综合应用","kind":"skill","description":"链条、滑轮、曲线运动等情境的守恒判断与计算。","subject":"物理","difficulty":0.8,"exam_frequency":0.9,"bloom":"analyze","resource_ids":[],"mastery_standard":"能识别守恒条件并完成综合计算。","assessment":"能识别守恒条件并完成综合计算。","position":{"x":390,"y":460}}'
     || '],"edges":['
     || '{"source":"k1","target":"k2","relation":"prerequisite"},{"source":"k2","target":"k3","relation":"prerequisite"},'
     || '{"source":"k2","target":"k4","relation":"prerequisite"},{"source":"k2","target":"k5","relation":"prerequisite"},'
     || '{"source":"k4","target":"k6","relation":"prerequisite"},{"source":"k5","target":"k7","relation":"prerequisite"},'
     || '{"source":"k6","target":"k7","relation":"prerequisite"},{"source":"k1","target":"k6","relation":"related"},'
     || '{"source":"k2","target":"s1","relation":"supports"},{"source":"k3","target":"s2","relation":"supports"},'
     || '{"source":"k6","target":"s3","relation":"supports"},{"source":"k7","target":"s4","relation":"supports"}'
     || '],"subject":"物理","grade":"高一"}')::jsonb);

    INSERT INTO a12_course_graph_version (user_id,course_id,version,title,graph_data)
    SELECT user_id,course_id,version,title,graph_data FROM a12_course_graph
    WHERE user_id = v_user AND course_id = 'demo-physics-mechanics';

    -- 节点证据（挂上一轮种的公共资源 930001/930002，供对话大纲生成时的图谱证据演示）
    INSERT INTO a12_graph_evidence (user_id,course_id,resource_key,content_sha256,node_id,excerpt) VALUES
    (v_user,'demo-physics-mechanics','public:930001','e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855','k2','功的大小等于力与沿力方向位移的乘积，正负功的判断是本单元常见考点。'),
    (v_user,'demo-physics-mechanics','public:930002','e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855','k7','只有重力或弹力做功时，动能与势能相互转化而机械能总量保持不变。');
END $$;
