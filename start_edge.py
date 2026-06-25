import sys
import os
BASE_PATH = os.path.abspath(__file__)
BASE_DIR = os.path.dirname(BASE_PATH)
sys.path.insert(BASE_DIR)

from edge.edge_service import edge_light_detect
if __name__ == "__main__":
    print("openEuler边缘检测节点已就绪，可调用 /api/edge/report 接口")
