import sys
import os
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_PATH)

from fastapi import APIRouter
from db.db_conn import get_db_session
from db.models import AuditLog
router = APIRouter()
@router.get("/logs")
def get_logs():
    db = get_db_session()
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).all()
    return [l.__dict__ for l in logs]
