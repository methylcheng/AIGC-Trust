import sys
import os
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_PATH)

from fastapi import APIRouter
from edge.edge_service import edge_light_detect
router = APIRouter()
@router.post("/report")
def edge_report(img_path: str):
    return edge_light_detect(img_path)
