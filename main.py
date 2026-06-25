import sys
import os
BASE_PATH = os.path.abspath(__file__)
BASE_DIR = os.path.dirname(BASE_PATH)
sys.path.insert(0, BASE_DIR)

from fastapi import FastAPI
from api.auth import router as auth_r
from api.content_api import router as content_r
from api.task_api import router as task_r
from api.fingerprint_api import router as fp_r
from api.cert_api import router as cert_r
from api.audit_api import router as audit_r
from api.edge_api import router as edge_r
from api.stats_api import router as stats_r

# 初始化可信签名链条系统
print("\n" + "="*60)
print("正在初始化 AIGC-Trust 可信签名链条系统...")
try:
    from crypto.trust_chain import initialize_trust_system
    trust_system = initialize_trust_system()
    print("✓ 可信签名链条系统初始化成功")
except Exception as e:
    print(f"✗ 可信签名链条系统初始化失败: {str(e)}")
    print("  证书功能可能不可用，请检查密钥配置")
print("="*60 + "\n")

app = FastAPI(title="AIGC-Trust：AIGC内容真实性检测与可信溯源系统")

@app.get("/")
def root():
    return {"message": "AIGC-Trust API 服务运行中", "docs": "/docs"}

app.include_router(auth_r, prefix="/api/auth")
app.include_router(content_r, prefix="/api/contents")
app.include_router(task_r, prefix="/api/tasks")
app.include_router(fp_r, prefix="/api/fingerprints")
app.include_router(cert_r, prefix="/api/certificates")
app.include_router(audit_r, prefix="/api/audit")
app.include_router(edge_r, prefix="/api/edge")
app.include_router(stats_r, prefix="/api/stats")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
