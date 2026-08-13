"""
生成典型病例参考影像库
使用 numpy + PIL 生成模拟医学影像（灰度图）
"""
import os
import numpy as np
from PIL import Image, ImageDraw

OUTPUT_DIR = "F:/Python/Project/backend/static/reference_images"
os.makedirs(OUTPUT_DIR, exist_ok=True)

SIZE = 512


def _save(name, arr):
    """保存 numpy 数组为 PNG"""
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr, mode="L")
    path = os.path.join(OUTPUT_DIR, name)
    img.save(path)
    print(f"  OK {name}  ({os.path.getsize(path)//1024}KB)")


# ════════════════════════════════════════════
# 1. 正常胸部 X 光 (chest_normal)
# ════════════════════════════════════════════
def gen_chest_normal():
    img = np.full((SIZE, SIZE), 30, dtype=np.uint8)
    y, x = np.ogrid[:SIZE, :SIZE]

    # 双肺区域（稍暗）
    left_lung = ((x - 190) ** 2) / 80 ** 2 + ((y - 260) ** 2) / 140 ** 2 <= 1
    right_lung = ((x - 322) ** 2) / 80 ** 2 + ((y - 260) ** 2) / 140 ** 2 <= 1
    img[left_lung] = 70
    img[right_lung] = 70

    # 纵隔 / 心脏（亮色）
    heart = ((x - 256) ** 2) / 60 ** 2 + ((y - 270) ** 2) / 80 ** 2 <= 1
    img[heart] = 160

    # 双肺门（血管影）
    for cx, cy in [(190, 260), (322, 260)]:
        hilum = ((x - cx) ** 2 + (y - cy) ** 2) <= 30 ** 2
        img[hilum] = 120

    # 锁骨
    img[250:255, 140:200] = 200
    img[250:255, 312:372] = 200

    # 肋骨痕迹（简单弧线）
    for i in range(6):
        ry = 180 + i * 30
        for cx in [190, 322]:
            rib = ((x - cx) ** 2) / 100 ** 2 + ((y - ry) ** 2) / 10 ** 2 <= 1
            img[rib] = 140

    _save("chest_normal.png", img)


# ════════════════════════════════════════════
# 2. 肺炎 (chest_pneumonia)
# ════════════════════════════════════════════
def gen_chest_pneumonia():
    img = np.full((SIZE, SIZE), 30, dtype=np.uint8)
    y, x = np.ogrid[:SIZE, :SIZE]

    # 双肺
    left_lung = ((x - 190) ** 2) / 80 ** 2 + ((y - 260) ** 2) / 140 ** 2 <= 1
    right_lung = ((x - 322) ** 2) / 80 ** 2 + ((y - 260) ** 2) / 140 ** 2 <= 1
    img[left_lung] = 70
    img[right_lung] = 70

    # 心脏
    heart = ((x - 256) ** 2) / 60 ** 2 + ((y - 270) ** 2) / 80 ** 2 <= 1
    img[heart] = 160

    # 右下肺片状高密度影（磨玻璃/实变）
    infiltrate = ((x - 350) ** 2) / 40 ** 2 + ((y - 320) ** 2) / 50 ** 2 <= 1
    img[infiltrate] = 140

    # 左下肺少许渗出
    infiltrate2 = ((x - 150) ** 2) / 25 ** 2 + ((y - 330) ** 2) / 35 ** 2 <= 1
    img[infiltrate2] = 120

    _save("chest_pneumonia.png", img)

# ════════════════════════════════════════════
# 3. 慢阻肺 (chest_copd)
# ════════════════════════════════════════════
def gen_chest_copd():
    img = np.full((SIZE, SIZE), 45, dtype=np.uint8)  # 背景更亮 = 肺过度充气
    y, x = np.ogrid[:SIZE, :SIZE]

    # 肺野更大、更亮
    left_lung = ((x - 180) ** 2) / 90 ** 2 + ((y - 260) ** 2) / 150 ** 2 <= 1
    right_lung = ((x - 332) ** 2) / 90 ** 2 + ((y - 260) ** 2) / 150 ** 2 <= 1
    img[left_lung] = 80
    img[right_lung] = 80

    # 心影狭长（桶状胸特征）
    heart = ((x - 256) ** 2) / 40 ** 2 + ((y - 270) ** 2) / 90 ** 2 <= 1
    img[heart] = 150

    # 肺纹理增多
    for _ in range(30):
        sx, sy = np.random.randint(140, 370), np.random.randint(150, 400)
        r = np.random.randint(3, 8)
        img[max(0, sy - r):sy + r, max(0, sx - r):sx + r] = 110

    _save("chest_copd.png", img)


# ════════════════════════════════════════════
# 4. 正常头颅 CT (brain_normal)
# ════════════════════════════════════════════
def gen_brain_normal():
    img = np.full((SIZE, SIZE), 20, dtype=np.uint8)
    y, x = np.ogrid[:SIZE, :SIZE]
    cy, cx = SIZE // 2, SIZE // 2

    # 颅骨
    skull = ((x - cx) ** 2) / 200 ** 2 + ((y - cy) ** 2) / 230 ** 2 <= 1
    img[skull] = 50

    # 脑组织
    brain = ((x - cx) ** 2) / 170 ** 2 + ((y - cy) ** 2) / 200 ** 2 <= 1
    img[brain] = 100

    # 脑室（低密度）
    ventricle = ((x - cx + 10) ** 2) / 30 ** 2 + ((y - cy - 20) ** 2) / 50 ** 2 <= 1
    img[ventricle] = 60

    # 中线结构
    img[cy - 5:cy + 5, cx - 10:cx + 10] = 130

    # 对称的基底节
    for d in [-40, 40]:
        bg = ((x - cx + d) ** 2 + (y - cy + 10) ** 2) <= 20 ** 2
        img[bg] = 120

    _save("brain_normal.png", img)


# ════════════════════════════════════════════
# 5. 脑梗死 (brain_infarction)
# ════════════════════════════════════════════
def gen_brain_infarction():
    img = np.full((SIZE, SIZE), 20, dtype=np.uint8)
    y, x = np.ogrid[:SIZE, :SIZE]
    cy, cx = SIZE // 2, SIZE // 2

    skull = ((x - cx) ** 2) / 200 ** 2 + ((y - cy) ** 2) / 230 ** 2 <= 1
    img[skull] = 50
    brain = ((x - cx) ** 2) / 170 ** 2 + ((y - cy) ** 2) / 200 ** 2 <= 1
    img[brain] = 100

    # 左侧扇形低密度区（梗死灶）
    infarct = ((x - cx + 60) ** 2) / 45 ** 2 + ((y - cy - 20) ** 2) / 55 ** 2 <= 1
    img[infarct] = 50  # 暗色梗死区

    # 脑室受压 中线偏移
    ventricle = ((x - cx + 20) ** 2) / 25 ** 2 + ((y - cy - 20) ** 2) / 40 ** 2 <= 1
    img[ventricle] = 60
    img[cy - 3:cy + 3, cx + 5:cx + 15] = 130  # 中线右偏

    _save("brain_infarction.png", img)


# ════════════════════════════════════════════
# 6. 脑出血 (brain_hemorrhage)
# ════════════════════════════════════════════
def gen_brain_hemorrhage():
    img = np.full((SIZE, SIZE), 20, dtype=np.uint8)
    y, x = np.ogrid[:SIZE, :SIZE]
    cy, cx = SIZE // 2, SIZE // 2

    skull = ((x - cx) ** 2) / 200 ** 2 + ((y - cy) ** 2) / 230 ** 2 <= 1
    img[skull] = 50
    brain = ((x - cx) ** 2) / 170 ** 2 + ((y - cy) ** 2) / 200 ** 2 <= 1
    img[brain] = 100

    # 右侧基底节区团状高密度（出血）
    hemorrhage = ((x - cx - 30) ** 2) / 40 ** 2 + ((y - cy + 10) ** 2) / 50 ** 2 <= 1
    img[hemorrhage] = 200

    # 周围低密度水肿带
    edema = ((x - cx - 30) ** 2) / 60 ** 2 + ((y - cy + 10) ** 2) / 75 ** 2 <= 1
    edema = edema & ~hemorrhage
    img[edema] = 70

    # 脑室受压
    ventricle = ((x - cx + 15) ** 2) / 25 ** 2 + ((y - cy - 15) ** 2) / 35 ** 2 <= 1
    img[ventricle] = 55
    img[cy - 2:cy + 2, cx + 8:cx + 18] = 130

    _save("brain_hemorrhage.png", img)


# ════════════════════════════════════════════
# 7. 正常腰椎 (spine_normal)
# ════════════════════════════════════════════
def gen_spine_normal():
    img = np.full((SIZE, SIZE), 20, dtype=np.uint8)

    # 椎体（从上面下的长方形）
    for i in range(5):
        y0 = 80 + i * 80
        img[y0:y0 + 40, 180:332] = 160  # 椎体
        img[y0 + 5:y0 + 35, 185:327] = 120  # 内部骨髓

    # 椎间隙
    for i in range(4):
        y0 = 120 + i * 80
        img[y0:y0 + 10, 190:322] = 70

    # 棘突
    img[80:480, 255:257] = 140

    _save("spine_normal.png", img)


# ════════════════════════════════════════════
# 8. 椎间盘突出 (spine_disc_herniation)
# ════════════════════════════════════════════
def gen_spine_disc_herniation():
    img = np.full((SIZE, SIZE), 20, dtype=np.uint8)

    # 椎体
    for i in range(5):
        y0 = 80 + i * 80
        img[y0:y0 + 40, 180:332] = 160
        if i == 2:  # L3/L4 椎体边缘增生
            img[y0 - 5:y0, 175:337] = 180
        img[y0 + 5:y0 + 35, 185:327] = 120

    # L4/L5 椎间隙变窄（第4个间隙）
    for i in range(3):
        y0 = 120 + i * 80
        img[y0:y0 + 10, 190:322] = 70
    # L4/L5 间隙变窄
    img[360:366, 190:322] = 60

    # 椎间盘向后突出（L4/L5）
    img[358:368, 328:350] = 90

    # 棘突
    img[80:480, 255:257] = 140

    _save("spine_disc_herniation.png", img)


# ════════════════════════════════════════════
# 9. 骨折 (bone_fracture)
# ════════════════════════════════════════════
def gen_bone_fracture():
    img = np.full((SIZE, SIZE), 15, dtype=np.uint8)

    # 长骨（股骨）
    img[40:472, 210:302] = 180  # 骨皮质
    img[50:462, 222:290] = 120  # 骨髓腔

    # 骨折线（股骨中段）
    img[220:228, 200:310] = 40  # 骨折透亮线
    # 骨折断端轻微错位
    img[228:235, 205:310] = 190  # 稍重叠

    # 周围软组织肿胀
    img[200:260, 180:330] = np.maximum(img[200:260, 180:330], 40)

    # 关节端
    for y0, w in [(40, 50), (462, 50)]:
        joint = ((np.ogrid[:SIZE, :SIZE][0] - y0) ** 2) / w ** 2 + (
            (np.ogrid[:SIZE, :SIZE][1] - 256) ** 2) / 35 ** 2 <= 1
        img[joint] = 160

    _save("bone_fracture.png", img)


# ════════════════════════════════════════════
# 10. 正常心脏 (heart_normal)
# ════════════════════════════════════════════
def gen_heart_normal():
    img = np.full((SIZE, SIZE), 25, dtype=np.uint8)
    y, x = np.ogrid[:SIZE, :SIZE]

    # 胸廓
    chest = ((x - 256) ** 2) / 180 ** 2 + ((y - 256) ** 2) / 220 ** 2 <= 1
    img[chest] = 50

    # 双肺
    left_lung = ((x - 190) ** 2) / 75 ** 2 + ((y - 260) ** 2) / 130 ** 2 <= 1
    right_lung = ((x - 322) ** 2) / 75 ** 2 + ((y - 260) ** 2) / 130 ** 2 <= 1
    img[left_lung] = 70
    img[right_lung] = 70

    # 心脏（正常大小 — 心胸比约 0.5）
    heart = ((x - 256) ** 2) / 55 ** 2 + ((y - 270) ** 2) / 75 ** 2 <= 1
    img[heart] = 150

    _save("heart_normal.png", img)


# ════════════════════════════════════════════
# 11. 心脏肥大 (heart_hypertrophy)
# ════════════════════════════════════════════
def gen_heart_hypertrophy():
    img = np.full((SIZE, SIZE), 25, dtype=np.uint8)
    y, x = np.ogrid[:SIZE, :SIZE]

    chest = ((x - 256) ** 2) / 180 ** 2 + ((y - 256) ** 2) / 220 ** 2 <= 1
    img[chest] = 50
    left_lung = ((x - 180) ** 2) / 70 ** 2 + ((y - 260) ** 2) / 130 ** 2 <= 1
    right_lung = ((x - 332) ** 2) / 70 ** 2 + ((y - 260) ** 2) / 130 ** 2 <= 1
    img[left_lung] = 70
    img[right_lung] = 70

    # 心脏明显增大（心胸比 > 0.5）
    heart = ((x - 256) ** 2) / 80 ** 2 + ((y - 270) ** 2) / 95 ** 2 <= 1
    img[heart] = 160

    # 左下心缘延长
    extra = ((x - 220) ** 2) / 60 ** 2 + ((y - 310) ** 2) / 40 ** 2 <= 1
    img[extra] = 150

    _save("heart_hypertrophy.png", img)


# ════════════════════════════════════════════
# Main
# ════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 50)
    print("--  生成典型病例参考影像库")
    print("=" * 50)
    print()

    print("输出目录:", OUTPUT_DIR)
    print()

    gen_chest_normal()
    gen_chest_pneumonia()
    gen_chest_copd()
    gen_brain_normal()
    gen_brain_infarction()
    gen_brain_hemorrhage()
    gen_spine_normal()
    gen_spine_disc_herniation()
    gen_bone_fracture()
    gen_heart_normal()
    gen_heart_hypertrophy()

    print()
    print("=" * 50)
    print(f"共生成 11 张参考影像")
    print("=" * 50)
