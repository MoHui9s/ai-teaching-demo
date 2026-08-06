"""场景对话端点"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.scenario_service import get_scenario_service, SCENARIOS
from api.schemas import DialogRequest, DialogMessage, DialogResponse, ScenarioInfo, APIResponse

logger = logging.getLogger("edulingua-scenarios")

router = APIRouter(prefix="/api/scenarios", tags=["Scenarios"])


@router.get("/list")
async def list_scenarios():
    """获取所有场景列表"""
    service = get_scenario_service()
    scenarios = service.get_all_scenarios()
    return APIResponse(
        success=True,
        data={"scenarios": scenarios}
    )


@router.get("/{scene_id}")
async def get_scenario(scene_id: str):
    """获取场景详情"""
    service = get_scenario_service()
    scenario = service.get_scenario(scene_id)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"场景 '{scene_id}' 不存在")
    return APIResponse(
        success=True,
        data={
            "scenario": scenario,
            "opening": service.get_scenario_opening(scene_id),
        }
    )


@router.post("/start")
async def start_scenario(request: DialogRequest, user_id: str = "default"):
    """
    开始场景对话

    Args:
        request: 场景类型和难度
        user_id: 用户标识

    Returns:
        场景开场白和 NPC 首次发言
    """
    service = get_scenario_service()
    scenario = service.get_scenario(request.scene_type)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"场景 '{request.scene_type}' 不存在")

    opening = service.get_scenario_opening(request.scene_type)

    return APIResponse(
        success=True,
        message="场景已就绪",
        data={
            "scene_type": request.scene_type,
            "difficulty": request.difficulty,
            "opening_prompt": opening,
            "scenario": {
                "id": scenario["id"],
                "name": scenario["name"],
                "learning_goals": scenario["learning_goals"],
            }
        }
    )


@router.get("/by-level/{level}")
async def get_scenarios_by_level(level: str):
    """按难度获取场景"""
    scenarios = [
        {
            "id": s["id"],
            "name": s["name"],
            "name_en": s["name_en"],
            "description": s["description"],
            "difficulty": s["difficulty"],
            "icon": s["icon"],
        }
        for s in SCENARIOS.values()
        if s["difficulty"] == level
    ]
    return APIResponse(
        success=True,
        data={"scenarios": scenarios, "level": level}
    )
