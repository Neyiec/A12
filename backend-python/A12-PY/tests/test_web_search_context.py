from a12_ppt.outline_chat.tool_node import OutlineToolNode


def test_public_query_excludes_private_teaching_context():
    intent = {"enable_web": True, "title": "力和运动", "subject": "物理", "grade": "高一",
              "requirements": "教师的个性化要求"}
    node = OutlineToolNode()
    plans = node._rule_plans(intent, "聊天记录及资源正文")
    assert next(plan.args["query"] for plan in plans if plan.name == "web_search") == "力和运动 物理 高一"
    assert all(plan.name != "web_search" for plan in node._rule_plans({**intent, "enable_web": False}, "正文"))
