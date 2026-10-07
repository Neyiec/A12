"""学科教学策略。只提供教学方法建议，不把学科名称当作可信指令。"""

from __future__ import annotations


_POLICIES = {
    "语言": {
        "subjects": ("英语", "日语", "外语"),
        "method": "从真实交际情境出发，安排可理解输入、示范、同伴表达与即时纠错。",
        "activity": "让学生完成有信息差的听说读写任务，并以实际表达结果评价。",
        "visual": "优先情境图片、语篇结构、例句对比和可跟读的语言支架。",
        "page_structure": "情境导入→示范输入→同伴表达→即时反馈",
        "examples": "真实交际任务、信息差对话",
    },
    "文科": {
        "subjects": ("语文", "历史", "政治", "道德与法治", "思想政治", "地理"),
        "method": "以真实文本或史料提出解释性问题，比较证据与观点，组织讨论和有依据的表达。",
        "activity": "给学生一段材料，要求标注证据、提出主张并互评。",
        "visual": "优先时间线、概念关系、地图或文本对照；引用须保留出处。",
        "page_structure": "材料问题→证据对照→观点表达→迁移讨论",
        "examples": "史料证据比较、文本观点辨析",
    },
    "理科": {
        "subjects": ("数学", "物理", "化学", "生物", "科学"),
        "method": "从可检验问题出发，经历预测、实验或推导、数据解释和迁移练习。",
        "activity": "先让学生独立预测，再通过操作或例题检验，解释错误原因。",
        "visual": "优先可编辑的公式、图表、几何图或实验过程；标明单位和变量。",
        "page_structure": "现象预测→实验或推导→数据解释→变式练习",
        "examples": "函数图像探究、实验变量控制",
    },
    "工科": {
        "subjects": ("信息技术", "计算机", "通用技术", "工程", "编程"),
        "method": "围绕可交付的问题或项目，安排需求分析、方案设计、实现、测试与复盘。",
        "activity": "给出有限条件和验收标准，让学生制作原型并用测试结果改进。",
        "visual": "优先流程图、系统结构图、代码片段和可操作的步骤卡。",
        "page_structure": "真实需求→设计方案→实现测试→复盘改进",
        "examples": "程序调试、工程原型迭代",
    },
}

_STYLE_GUIDANCE = {
    "heuristic": "启发式探究：用层层递进的问题引导学生发现，不直接给出全部结论。",
    "lecture": "讲授式教学：结构清晰、概念准确，同时穿插短检测避免连续被动听讲。",
    "cooperative": "合作学习：设计有分工、有共同产出和互评标准的小组任务。",
    "project_based": "项目式学习：围绕真实产物安排设计、实现、展示与复盘。",
    "blended": "混合式教学：区分课前自学、课中实践和课后巩固。",
}

_PUBLISHED_POLICIES: dict[str, dict] = {}


def set_published_policies(values: dict[str, str]) -> None:
    """只接受后台已发布、结构完整且长度受限的策略；无效项不覆盖默认值。"""
    import json

    policies = {}
    for key, raw in values.items():
        if not key.startswith("subject_policy:") or not isinstance(raw, str) or len(raw) > 4000:
            continue
        try:
            value = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(value, dict) or not all(isinstance(value.get(k), str) and 0 < len(value[k]) <= 800
                                               for k in ("method", "activity", "visual")):
            continue
        subjects = value.get("subjects")
        if not isinstance(subjects, list) or not 1 <= len(subjects) <= 30 or not all(
            isinstance(item, str) and 1 <= len(item.strip()) <= 40 for item in subjects
        ):
            continue
        policies[key] = {"category": key.split(":", 1)[1][:40], "subjects": tuple(subjects),
                         **{name: value[name] for name in ("method", "activity", "visual")},
                         **{name: value[name][:1000] for name in ("page_structure", "examples")
                            if isinstance(value.get(name), str)}}
    global _PUBLISHED_POLICIES
    _PUBLISHED_POLICIES = policies


def teaching_style_guidance(style: str | None) -> str:
    value = (style or "").strip()[:100]
    return _STYLE_GUIDANCE.get(value, value or "未显式设置")


def teaching_policy(subject: str | None) -> dict[str, str]:
    name = (subject or "").strip().lower()
    for policy in _PUBLISHED_POLICIES.values():
        if any(token.strip().lower() in name for token in policy["subjects"]):
            return {key: policy.get(key, "") for key in ("category", "method", "activity", "visual", "page_structure", "examples")}
    for category, policy in _POLICIES.items():
        if any(token.lower() in name for token in policy["subjects"]):
            return {"category": category, **{key: policy[key] for key in ("method", "activity", "visual", "page_structure", "examples")}}
    return {
        "category": "通用",
        "method": "结合课程目标与学情设计问题、示例、学生任务和当堂评价。",
        "activity": "安排学生可观察、可反馈的探究或练习。",
        "visual": "按知识类型选择清晰、可编辑的图文表达。",
        "page_structure": "问题导入→核心知识→学生实践→检测反馈",
        "examples": "贴近学生经验的真实教学案例",
    }


def teaching_model_guidance(model: str | None) -> str:
    if model == "general":
        return "采用适合本课的教学流程；明确导入、目标、活动、评价和总结，不强制套用固定六阶段。"
    return (
        "采用 BOPPPS：导入 Bridge-in、学习目标 Objective、前测 Pre-assessment、"
        "参与式学习 Participatory learning、后测 Post-assessment、总结 Summary。"
        "短课可合并页面，但六项教学功能必须在大纲或讲稿中可追溯。"
    )
