from app.core.topic_handler import detect_new_topic, update_task_state

def test_new_topic_when_task_empty():
    is_new, dbg = detect_new_topic("我想学FastAPI", "")
    assert is_new is True
    assert dbg["reason"] == "empty_task"

def test_same_topic_when_similar():
    task = "解释 FastAPI 的 router 和 Pydantic"
    is_new, dbg = detect_new_topic("那 router 的 prefix 有什么用？", task, jaccard_threshold=0.10)
    # 阈值低一点避免误判
    assert is_new is False
