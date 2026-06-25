import sys
import os
# 自动添加项目根目录至Python搜索路径
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_PATH)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base

# 数据库配置
# 选项1: 使用SQLite（推荐用于开发/测试，无需安装MySQL）
# DB_URL = "sqlite:///./aigc_trust.db"

# 选项2: 使用本地MySQL（如果已安装MySQL，取消下面注释并修改密码）
# DB_URL = "mysql+pymysql://root:你的密码@localhost:3306/aigc_trust"

# 选项3: 使用远程MySQL
DB_URL = "mysql+pymysql://root:root@192.168.88.144:3306/aigc_trust"

# SQLite需要特殊处理check_same_thread
if DB_URL.startswith("sqlite"):
    engine = create_engine(DB_URL, pool_pre_ping=True, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session():
    return SessionLocal()

def init_db():
    Base.metadata.create_all(bind=engine)
    print("数据库表初始化完成")

if __name__ == "__main__":
    init_db()
