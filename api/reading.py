"""阅读训练端点"""

import json
import logging
from pathlib import Path
from fastapi import APIRouter, Query

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.schemas import APIResponse

logger = logging.getLogger("edulingua-reading")

router = APIRouter(prefix="/api/reading", tags=["Reading"])

READING_DIR = Path(__file__).parent.parent / "data" / "reading"
FILES = {
    "beginner": READING_DIR / "beginner.json",
    "intermediate": READING_DIR / "intermediate.json",
    "advanced": READING_DIR / "advanced.json",
}


def _load_articles(level: str) -> list[dict]:
    """加载指定级别的阅读文章"""
    file_path = FILES.get(level)
    if not file_path or not file_path.exists():
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载阅读材料失败: {level}, {e}")
        return []


@router.get("/list", response_model=APIResponse)
async def get_reading_list(
    level: str = Query("beginner", description="级别: beginner / intermediate / advanced"),
):
    """
    获取阅读文章列表（不含答案）

    返回文章标题和正文，题目包含选项但隐藏正确答案。
    """
    if level not in FILES:
        return APIResponse(
            success=False,
            message=f"不支持的级别: {level}，支持: {', '.join(FILES.keys())}",
        )

    articles = _load_articles(level)
    if not articles:
        return APIResponse(success=False, message=f"暂无阅读材料: {level}")

    # 返回时隐藏正确答案
    safe_articles = []
    for a in articles:
        safe = {
            "id": a["id"],
            "title": a["title"],
            "content": a["content"],
            "questions": [
                {"question": q["question"], "options": q["options"]}
                for q in a["questions"]
            ],
        }
        safe_articles.append(safe)

    return APIResponse(
        success=True,
        message=f"已加载 {len(safe_articles)} 篇 {level} 级别阅读文章",
        data={"articles": safe_articles, "level": level},
    )


@router.get("/article/{article_id}", response_model=APIResponse)
async def get_article(
    article_id: str,
    level: str = Query("beginner", description="级别"),
):
    """获取单篇阅读文章（含题目，不含答案）"""
    articles = _load_articles(level)
    article = next((a for a in articles if a["id"] == article_id), None)
    if not article:
        return APIResponse(success=False, message="文章不存在")

    return APIResponse(
        success=True,
        data={
            "id": article["id"],
            "title": article["title"],
            "content": article["content"],
            "questions": [
                {"question": q["question"], "options": q["options"]}
                for q in article["questions"]
            ],
        },
    )


@router.post("/check/{article_id}", response_model=APIResponse)
async def check_answers(
    article_id: str,
    answers: dict,  # body: {"answers": [0, 2]} — 用户选择的选项索引
    level: str = Query("beginner", description="级别"),
):
    """检查阅读题答案"""
    articles = _load_articles(level)
    article = next((a for a in articles if a["id"] == article_id), None)
    if not article:
        return APIResponse(success=False, message="文章不存在")

    user_answers = answers.get("answers", [])
    questions = article["questions"]
    results = []

    correct_count = 0
    for i, q in enumerate(questions):
        user_ans = user_answers[i] if i < len(user_answers) else -1
        is_correct = user_ans == q["answer"]
        if is_correct:
            correct_count += 1
        results.append({
            "question": q["question"],
            "your_answer": q["options"][user_ans] if 0 <= user_ans < len(q["options"]) else "(未作答)",
            "correct_answer": q["options"][q["answer"]],
            "correct": is_correct,
        })

    score = round(correct_count / len(questions) * 100) if questions else 0

    return APIResponse(
        success=True,
        message=f"得分: {correct_count}/{len(questions)} ({score}%)",
        data={
            "score": score,
            "correct_count": correct_count,
            "total": len(questions),
            "results": results,
        },
    )
