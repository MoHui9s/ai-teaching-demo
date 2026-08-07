"""APScheduler 定时任务调度"""
import logging
from datetime import date, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("scheduler")

scheduler = BackgroundScheduler()


def start_scheduler():
    """启动定时任务调度器（周报生成）"""
    from services.report_service import get_report_service
    from database.database import get_db_session
    from database.models import User, DailyProgress, PronunciationRecord, DialogHistory, DailyTask

    def generate_all_weekly_reports():
        """为所有活跃用户生成上周学习周报"""
        db = get_db_session()
        try:
            users = db.query(User).filter(User.is_active == True).all()
            if not users:
                logger.info("周报生成：无活跃用户，跳过")
                return

            report_service = get_report_service()
            today = date.today()
            # 上周一 ~ 上周日
            week_start = today - timedelta(days=today.weekday() + 7)
            week_end = week_start + timedelta(days=6)

            count = 0
            for user in users:
                try:
                    # 汇总上周每日进度
                    daily_progress = (
                        db.query(DailyProgress)
                        .filter(
                            DailyProgress.user_id == user.id,
                            DailyProgress.date >= week_start,
                            DailyProgress.date <= week_end,
                        )
                        .all()
                    )
                    progress_dicts = [
                        {
                            "total_minutes": dp.total_minutes,
                            "tasks_completed": dp.tasks_completed,
                            "dialogs_count": dp.dialogs_count,
                            "new_words": dp.new_words,
                        }
                        for dp in daily_progress
                    ]

                    # 汇总上周发音记录
                    pronunciation_records = (
                        db.query(PronunciationRecord)
                        .filter(
                            PronunciationRecord.user_id == user.id,
                            PronunciationRecord.created_at >= week_start,
                            PronunciationRecord.created_at < week_end + timedelta(days=1),
                        )
                        .all()
                    )
                    pron_dicts = [{"score": pr.score} for pr in pronunciation_records]

                    # 汇总上周对话记录
                    dialog_records = (
                        db.query(DialogHistory)
                        .filter(
                            DialogHistory.user_id == user.id,
                            DialogHistory.created_at >= week_start,
                            DialogHistory.created_at < week_end + timedelta(days=1),
                        )
                        .all()
                    )
                    dialog_dicts = [{"scene_type": dr.scene_type} for dr in dialog_records]

                    # 汇总上周任务记录
                    task_records = (
                        db.query(DailyTask)
                        .filter(
                            DailyTask.user_id == user.id,
                            DailyTask.date >= week_start,
                            DailyTask.date <= week_end,
                        )
                        .all()
                    )
                    task_dicts = [{"status": t.status} for t in task_records]

                    # 跳过一周无任何学习记录的用户
                    if not progress_dicts and not pron_dicts:
                        continue

                    report = report_service.generate_weekly_report(
                        user_id=user.user_id,
                        week_start=week_start,
                        week_end=week_end,
                        daily_progress=progress_dicts,
                        pronunciation_records=pron_dicts,
                        dialog_records=dialog_dicts,
                        task_records=task_dicts,
                    )
                    report_service.save_report(report)
                    count += 1
                    logger.info(f"周报已生成: user={user.user_id}, week={week_start}")

                except Exception as e:
                    logger.error(f"周报生成失败: user={user.user_id}, {e}")

            logger.info(f"周报定时任务完成：{count}/{len(users)} 个用户")

        except Exception as e:
            logger.error(f"周报批量生成异常: {e}")
        finally:
            db.close()

    # 每周日 23:00 执行
    scheduler.add_job(
        generate_all_weekly_reports,
        CronTrigger(day_of_week="sun", hour=23, minute=0),
        id="weekly_report",
        name="生成学习周报",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("定时任务调度器已启动（周报：每周日 23:00）")
