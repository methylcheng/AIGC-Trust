from sqlalchemy import Column, String, Integer, Text, DateTime, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    role = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.now)

class Content(Base):
    __tablename__ = "contents"
    content_id = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    type = Column(String(20), nullable=False)
    path = Column(Text, nullable=False)
    sm3_hash = Column(String(64), nullable=False)
    source = Column(String(32))
    created_at = Column(DateTime, default=datetime.datetime.now)

class DetectionTask(Base):
    __tablename__ = "detection_tasks"
    task_id = Column(String(64), primary_key=True)
    content_id = Column(String(64), ForeignKey("contents.content_id"))
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    status = Column(String(16), nullable=False)
    progress = Column(Float, default=0)
    node_id = Column(String(32))
    result = Column(Text)  # 存储检测结果的JSON字符串
    created_at = Column(DateTime, default=datetime.datetime.now)

class FrequencyFeature(Base):
    __tablename__ = "frequency_features"
    id = Column(Integer, primary_key=True, autoincrement=True)
    content_id = Column(String(64), ForeignKey("contents.content_id"))
    fft_feature = Column(Text)
    dct_feature = Column(Text)
    noise_score = Column(Float)

class ModelResult(Base):
    __tablename__ = "model_results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), ForeignKey("detection_tasks.task_id"))
    model_name = Column(String(64))
    model_version = Column(String(32))
    score = Column(Float)
    label = Column(String(32))

class FingerPrint(Base):
    __tablename__ = "fingerprints"
    id = Column(Integer, primary_key=True, autoincrement=True)
    content_id = Column(String(64), ForeignKey("contents.content_id"))
    phash = Column(String(128))
    simhash = Column(String(128))
    frame_merkle_root = Column(String(64))

class Cert(Base):
    __tablename__ = "certificates"
    cert_id = Column(String(64), primary_key=True)
    content_id = Column(String(64), ForeignKey("contents.content_id"))
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    risk_level = Column(String(16))
    signature = Column(Text)
    issued_at = Column(DateTime, default=datetime.datetime.now)
    expires_at = Column(DateTime)  # 新增：证书过期时间
    is_revoked = Column(Integer, default=0)  # 新增：吊销状态 (0:正常, 1:已吊销)
    revocation_reason = Column(String(255))  # 新增：吊销原因
    revoked_at = Column(DateTime)  # 新增：吊销时间

class AuditLog(Base):
    __tablename__ = "audit_logs"
    log_id = Column(String(64), primary_key=True)
    action = Column(Text)
    prev_hash = Column(String(64))
    log_hash = Column(String(64))
    operator = Column(String(50))
    created_at = Column(DateTime, default=datetime.datetime.now)

class EdgeNode(Base):
    __tablename__ = "edge_nodes"
    node_id = Column(String(64), primary_key=True)
    ip = Column(String(32))
    status = Column(String(16))
    version = Column(String(32))
    last_seen = Column(DateTime)
