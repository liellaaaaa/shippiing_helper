"""用户行为日志服务"""
import json
from datetime import datetime
from typing import Optional

from app.database import SessionLocal
from app.models.audit_log import AuditLog


class AuditService:
    def __init__(self, db=None):
        self.db = db or SessionLocal()

    def log(self, event_type: str, user_name: str, module: Optional[str] = None,
            detail: Optional[dict] = None, ip_address: Optional[str] = None,
            action_time: Optional[datetime] = None) -> AuditLog:
        log_entry = AuditLog(
            event_type=event_type,
            user_name=user_name,
            module=module,
            action_time=action_time or datetime.now(),
            detail=json.dumps(detail, ensure_ascii=False) if detail else None,
            ip_address=ip_address,
        )
        self.db.add(log_entry)
        self.db.commit()
        self.db.refresh(log_entry)
        return log_entry

    def query_logs(self, user_name: Optional[str] = None, event_type: Optional[str] = None,
                   module: Optional[str] = None, start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None, page: int = 1, page_size: int = 50):
        query = self.db.query(AuditLog)
        if user_name:
            query = query.filter(AuditLog.user_name == user_name)
        if event_type:
            query = query.filter(AuditLog.event_type == event_type)
        if module:
            query = query.filter(AuditLog.module == module)
        if start_time:
            query = query.filter(AuditLog.action_time >= start_time)
        if end_time:
            query = query.filter(AuditLog.action_time <= end_time)

        total = query.count()
        logs = query.order_by(AuditLog.action_time.desc()) \
                    .offset((page - 1) * page_size).limit(page_size).all()
        return {"logs": logs, "total": total, "page": page, "page_size": page_size}

    def get_stats(self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None):
        from sqlalchemy import func

        # 按用户统计
        by_user = self.db.query(
            AuditLog.user_name,
            func.count(AuditLog.id).label("count")
        )
        if start_time:
            by_user = by_user.filter(AuditLog.action_time >= start_time)
        if end_time:
            by_user = by_user.filter(AuditLog.action_time <= end_time)
        by_user = by_user.group_by(AuditLog.user_name).all()

        # 按事件类型统计
        by_event = self.db.query(
            AuditLog.event_type,
            func.count(AuditLog.id).label("count")
        )
        if start_time:
            by_event = by_event.filter(AuditLog.action_time >= start_time)
        if end_time:
            by_event = by_event.filter(AuditLog.action_time <= end_time)
        by_event = by_event.group_by(AuditLog.event_type).all()

        # 按模块统计
        by_module = self.db.query(
            AuditLog.module,
            func.count(AuditLog.id).label("count")
        )
        if start_time:
            by_module = by_module.filter(AuditLog.action_time >= start_time)
        if end_time:
            by_module = by_module.filter(AuditLog.action_time <= end_time)
        by_module = by_module.filter(AuditLog.module.isnot(None)).group_by(AuditLog.module).all()

        return {
            "by_user": [{"user_name": r[0], "count": r[1]} for r in by_user],
            "by_event": [{"event_type": r[0], "count": r[1]} for r in by_event],
            "by_module": [{"module": r[0], "count": r[1]} for r in by_module],
        }

    def export_logs(self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None):
        query = self.db.query(AuditLog)
        if start_time:
            query = query.filter(AuditLog.action_time >= start_time)
        if end_time:
            query = query.filter(AuditLog.action_time <= end_time)
        return query.order_by(AuditLog.action_time.desc()).all()
