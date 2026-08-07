"""词汇学习端点"""

import json
import logging
import random
from pathlib import Path
from fastapi import APIRouter, Query

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.schemas import APIResponse

logger = logging.getLogger("edulingua-vocab")

router = APIRouter(prefix="/api/vocab", tags=["Vocab"])

# 词库文件路径
VOCAB_DIR = Path(__file__).parent.parent / "data" / "vocab"
FILES = {
    "beginner": VOCAB_DIR / "beginner.json",
    "intermediate": VOCAB_DIR / "intermediate.json",
    "advanced": VOCAB_DIR / "advanced.json",
}


def _load_vocab(level: str) -> list[dict]:
    """加载指定级别词库"""
    file_path = FILES.get(level)
    if not file_path or not file_path.exists():
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载词库失败: {level}, {e}")
        return []


@router.get("/list", response_model=APIResponse)
async def get_vocab_list(
    level: str = Query("beginner", description="级别: beginner / intermediate / advanced"),
    count: int = Query(20, description="返回单词数量，0=全部"),
):
    """
    获取词汇列表

    返回指定级别的词汇，含英文、中文释义、例句。
    """
    if level not in FILES:
        return APIResponse(
            success=False,
            message=f"不支持的级别: {level}，支持: {', '.join(FILES.keys())}",
        )

    words = _load_vocab(level)
    if not words:
        return APIResponse(success=False, message=f"词库为空: {level}")

    # 随机抽取指定数量（不打乱原始列表，保证多次调用多样性）
    if count > 0 and count < len(words):
        selected = random.sample(words, count)
    else:
        selected = words.copy()
        random.shuffle(selected)

    return APIResponse(
        success=True,
        message=f"已加载 {len(selected)} 个 {level} 级别词汇",
        data={
            "words": selected,
            "total_available": len(words),
            "level": level,
        },
    )
