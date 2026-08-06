"""场景对话管理服务"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger("scenario-service")

# 预置场景库
SCENARIOS = {
    "restaurant": {
        "id": "restaurant",
        "name": "餐厅点餐",
        "name_en": "Restaurant Ordering",
        "description": "在美式餐厅中点餐、询问菜品、支付账单",
        "difficulty": "easy",
        "roles": ["Waiter/Waitress"],
        "learning_goals": [
            "学会用英文点餐和询问菜品",
            "掌握餐厅常用礼貌用语",
            "理解账单和支付相关表达"
        ],
        "icon": "🍽️",
        "opening_prompt": """📋 **场景：美式餐厅**
🎭 **NPC**：服务员 (Server)
🎯 **目标**：成功点餐并完成支付

你现在走进了一家美式餐厅，服务员正在等你点单。准备好了吗？""",
    },
    "directions": {
        "id": "directions",
        "name": "问路指路",
        "name_en": "Asking for Directions",
        "description": "在陌生城市问路、理解导航指引",
        "difficulty": "easy",
        "roles": ["Local Resident"],
        "learning_goals": [
            "学会询问方向和理解指路表达",
            "掌握方位介词（turn left, go straight 等）",
            "理解地标和距离表达"
        ],
        "icon": "🗺️",
        "opening_prompt": """📋 **场景：问路**
🎭 **NPC**：路人 (Passerby)
🎯 **目标**：问路并理解指路说明

你在一个陌生城市，需要找到最近的银行。一个路人正在你旁边走过...准备好了吗？""",
    },
    "classroom": {
        "id": "classroom",
        "name": "课堂讨论",
        "name_en": "Classroom Discussion",
        "description": "参与英语课堂讨论、表达观点、小组交流",
        "difficulty": "medium",
        "roles": ["Professor", "Classmate"],
        "learning_goals": [
            "学会用英文表达观点和论证",
            "掌握课堂讨论常用句式",
            "练习即兴回答和提问"
        ],
        "icon": "📚",
        "opening_prompt": """📋 **场景：课堂讨论**
🎭 **NPC**：教授 (Professor) + 同学 (Classmate)
🎯 **目标**：参与关于"环保"的话题讨论

教授刚提了一个问题："What do you think is the most important environmental issue today?"
准备好了吗？""",
    },
    "interview": {
        "id": "interview",
        "name": "求职面试",
        "name_en": "Job Interview",
        "description": "模拟英语求职面试、自我介绍、回答常见问题",
        "difficulty": "hard",
        "roles": ["HR Manager"],
        "learning_goals": [
            "学会英文自我介绍",
            "掌握面试常见问题的回答策略",
            "练习专业职场用语"
        ],
        "icon": "💼",
        "opening_prompt": """📋 **场景：求职面试**
🎭 **NPC**：HR 经理 (HR Manager)
🎯 **目标**：完成一次英文实习面试

你正在面试一家外企的暑期实习岗位。HR 经理请你做自我介绍。准备好了吗？""",
    },
    "travel": {
        "id": "travel",
        "name": "机场出行",
        "name_en": "Airport Travel",
        "description": "办理登机、过安检、登机口询问",
        "difficulty": "medium",
        "roles": ["Check-in Agent", "Security Officer"],
        "learning_goals": [
            "学会机场办理登机手续",
            "掌握安检和行李相关表达",
            "理解航班信息和广播通知"
        ],
        "icon": "✈️",
        "opening_prompt": """📋 **场景：机场出行**
🎭 **NPC**：值机人员 (Check-in Agent)
🎯 **目标**：办理登机手续，托运行李

你到了机场准备飞往纽约，现在在值机柜台前。准备好了吗？""",
    },
    "shopping": {
        "id": "shopping",
        "name": "购物砍价",
        "name_en": "Shopping",
        "description": "在商场购物、询问价格尺码、试穿",
        "difficulty": "easy",
        "roles": ["Shop Assistant"],
        "learning_goals": [
            "学会询问价格、尺码和颜色",
            "掌握试穿和退换货表达",
            "练习购物场景礼貌用语"
        ],
        "icon": "🛍️",
        "opening_prompt": """📋 **场景：购物**
🎭 **NPC**：店员 (Shop Assistant)
🎯 **目标**：挑选一件合适的衣服并结账

你走进了一家服装店，店员过来打招呼。准备好了吗？""",
    },
    "hospital": {
        "id": "hospital",
        "name": "医院就诊",
        "name_en": "Hospital Visit",
        "description": "描述症状、挂号、与医生沟通",
        "difficulty": "medium",
        "roles": ["Doctor", "Nurse"],
        "learning_goals": [
            "学会描述身体不适的症状",
            "掌握挂号问诊流程表达",
            "理解医生的诊断和建议"
        ],
        "icon": "🏥",
        "opening_prompt": """📋 **场景：医院就诊**
🎭 **NPC**：医生 (Doctor)
🎯 **目标**：向医生描述症状并获取诊断

你因为头痛和发烧来到诊所。医生正在问你的情况。准备好了吗？""",
    },
    "phone_call": {
        "id": "phone_call",
        "name": "电话沟通",
        "name_en": "Phone Call",
        "description": "预约服务、电话咨询、客户服务",
        "difficulty": "medium",
        "roles": ["Customer Service Rep"],
        "learning_goals": [
            "学会电话沟通开场白和结束语",
            "掌握预约和改期的英文表达",
            "练习无视觉辅助的听力理解"
        ],
        "icon": "📞",
        "opening_prompt": """📋 **场景：电话沟通**
🎭 **NPC**：客服代表 (Customer Service)
🎯 **目标**：电话预约牙医

你正打电话给一家牙医诊所预约检查时间。准备好接听了吗？""",
    },
    "study_group": {
        "id": "study_group",
        "name": "学习小组",
        "name_en": "Study Group",
        "description": "参加英语学习小组、分享学习方法",
        "difficulty": "easy",
        "roles": ["Study Partner"],
        "learning_goals": [
            "学会用英文分享学习经验",
            "掌握小组讨论的互动表达",
            "练习给出和接受建议"
        ],
        "icon": "👥",
        "opening_prompt": """📋 **场景：学习小组**
🎭 **NPC**：学伴 (Study Partner)
🎯 **目标**：与学伴交流学习方法

你正在参加英语学习小组活动，你的学伴想和你聊聊英语学习方法。准备好了吗？""",
    },
    "presentation": {
        "id": "presentation",
        "name": "英文演讲",
        "name_en": "English Presentation",
        "description": "准备和发表简短英文演讲",
        "difficulty": "hard",
        "roles": ["Audience Member"],
        "learning_goals": [
            "学会演讲的结构（开场-主体-结尾）",
            "掌握过渡词和强调表达",
            "练习回答听众提问"
        ],
        "icon": "🎤",
        "opening_prompt": """📋 **场景：英文演讲**
🎭 **NPC**：观众 (Audience)
🎯 **目标**：发表一个 2 分钟的英文自我介绍

你需要在英语角做一次简短的自我介绍演讲。准备好了吗？""",
    },
}


class ScenarioService:
    """场景对话管理服务"""

    def get_all_scenarios(self) -> List[Dict]:
        """获取所有场景列表"""
        return [
            {
                "id": s["id"],
                "name": s["name"],
                "name_en": s["name_en"],
                "description": s["description"],
                "difficulty": s["difficulty"],
                "roles": s["roles"],
                "learning_goals": s["learning_goals"],
                "icon": s["icon"],
            }
            for s in SCENARIOS.values()
        ]

    def get_scenario(self, scene_id: str) -> Optional[Dict]:
        """获取单个场景详情"""
        return SCENARIOS.get(scene_id)

    def get_scenario_opening(self, scene_id: str) -> Optional[str]:
        """获取场景开场白"""
        s = SCENARIOS.get(scene_id)
        return s["opening_prompt"] if s else None

    def scene_required(self, scene_id: str) -> bool:
        """场景是否存在"""
        return scene_id in SCENARIOS


# 全局实例
_scenario_service: Optional[ScenarioService] = None


def get_scenario_service() -> ScenarioService:
    """获取场景服务单例"""
    global _scenario_service
    if _scenario_service is None:
        _scenario_service = ScenarioService()
    return _scenario_service
