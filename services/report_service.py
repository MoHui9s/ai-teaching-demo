"""周报生成服务 + 定时任务"""

import os
import json
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger("report-service")


class ReportService:
    """学习周报生成服务"""

    def __init__(self):
        self.reports_dir = Path(os.getcwd()) / "data" / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_weekly_report(
        self,
        user_id: str,
        week_start: date,
        week_end: date,
        daily_progress: List[Dict],
        pronunciation_records: List[Dict],
        dialog_records: List[Dict],
        task_records: List[Dict],
    ) -> Dict[str, Any]:
        """
        生成周报数据（AI 文本由 Agent 生成）

        Args:
            user_id: 用户 ID
            week_start: 周开始日期
            week_end: 周结束日期
            daily_progress: 每日进度列表
            pronunciation_records: 发音记录
            dialog_records: 对话记录
            task_records: 任务记录

        Returns:
            周报数据
        """
        total_minutes = sum(p.get("total_minutes", 0) for p in daily_progress)
        total_tasks = sum(p.get("tasks_completed", 0) for p in daily_progress)
        total_dialogs = sum(p.get("dialogs_count", 0) for p in daily_progress)
        total_new_words = sum(p.get("new_words", 0) for p in daily_progress)

        avg_pronunciation = 0.0
        if pronunciation_records:
            avg_pronunciation = sum(r.get("score", 0) for r in pronunciation_records) / len(pronunciation_records)

        study_days = len([p for p in daily_progress if p.get("total_minutes", 0) > 0])

        # 分析亮点和薄弱点
        highlights = []
        weaknesses = []
        next_week = []

        if study_days >= 5:
            highlights.append(f"本周坚持学习了 {study_days} 天，非常有毅力！")
        elif study_days < 3:
            weaknesses.append("本周学习天数较少，建议下周至少保持 5 天学习")

        if avg_pronunciation > 70:
            highlights.append(f"发音平均分达到 {avg_pronunciation:.0f} 分，继续保持！")
        elif pronunciation_records:
            weaknesses.append(f"发音平均分 {avg_pronunciation:.0f}，建议每天坚持跟读练习")
            next_week.append("每天完成 1 次跟读练习，重点关注 th/r/l 的发音")

        if total_tasks < 5:
            next_week.append("每天完成至少 1 个学习任务，保持 15 分钟以上的学习时间")
        else:
            highlights.append(f"本周完成了 {total_tasks} 个学习任务，执行力满分！")

        if total_dialogs < 2:
            next_week.append("尝试完成 2 次场景对话练习，锻炼口语实战能力")
        else:
            highlights.append(f"完成了 {total_dialogs} 次场景对话，口语实战能力在提升！")

        return {
            "user_id": user_id,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "stats": {
                "total_minutes": total_minutes,
                "total_tasks": total_tasks,
                "total_dialogs": total_dialogs,
                "total_new_words": total_new_words,
                "avg_pronunciation": round(avg_pronunciation, 1),
                "study_days": study_days,
            },
            "highlights": highlights,
            "weaknesses": weaknesses,
            "next_week_suggestions": next_week,
        }

    def save_report(self, report_data: Dict) -> None:
        """保存周报到磁盘"""
        user_id = report_data["user_id"]
        week_start = report_data["week_start"]
        filename = f"{user_id}_{week_start}.json"
        filepath = self.reports_dir / filename
        filepath.write_text(
            json.dumps(report_data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        logger.info(f"周报已保存: {filepath}")

    def load_report(self, user_id: str, week_start: str) -> Optional[Dict]:
        """加载周报"""
        filename = f"{user_id}_{week_start}.json"
        filepath = self.reports_dir / filename
        if filepath.exists():
            return json.loads(filepath.read_text(encoding="utf-8"))
        return None

    def load_all_reports(self, user_id: str) -> List[Dict]:
        """加载用户所有周报"""
        reports = []
        for filepath in sorted(self.reports_dir.glob(f"{user_id}_*.json")):
            try:
                reports.append(json.loads(filepath.read_text(encoding="utf-8")))
            except Exception:
                continue
        return reports


# 全局实例
_report_service: Optional[ReportService] = None


def get_report_service() -> ReportService:
    """获取周报服务单例"""
    global _report_service
    if _report_service is None:
        _report_service = ReportService()
    return _report_service
