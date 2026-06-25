from core.multimodal_pre import preprocess_image
from core.frequency_analysis import calc_noise_residual
from fingerprint.phash_img import calc_phash
def edge_light_detect(img_path: str):
    img, _ = preprocess_image(img_path, max_edge=480)
    noise = calc_noise_residual(img)
    p_hash = calc_phash(img)
    risk_tag = "边缘初筛低风险" if noise < 10 else "边缘初筛可疑"
    return {"noise_score": noise, "phash": p_hash, "risk_tag": risk_tag}
