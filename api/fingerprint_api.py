import sys
import os
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_PATH)

from fastapi import APIRouter
from db.db_conn import get_db_session
from db.models import FingerPrint
router = APIRouter()
@router.get("/{content_id}")
def get_fp(content_id: str):
    db = get_db_session()
    fp = db.query(FingerPrint).filter(FingerPrint.content_id==content_id).first()
    return fp.__dict__
