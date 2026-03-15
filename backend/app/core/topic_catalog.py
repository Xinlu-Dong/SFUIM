from typing import List, TypedDict


class TopicItem(TypedDict):
    id: str
    title: str


TOPIC_CATALOG: List[TopicItem] = [
    {
        "id": "ml_vs_programming",
        "title": "What is machine learning, and how is it different from traditional programming?",
    },
    {
        "id": "database_basics",
        "title": "What is a database, and why do applications need one?",
    },
    {
        "id": "multithreading_basics",
        "title": "What is multithreading, and why can it improve performance?",
    },
    {
        "id": "cloud_computing_basics",
        "title": "What is cloud computing, and how is it different from local computing?",
    },
]


def get_topic_catalog() -> List[TopicItem]:
    """
    Return a shallow copy so callers do not mutate the global catalog by mistake.
    """
    return [dict(item) for item in TOPIC_CATALOG]