# -*- coding: utf-8 -*-
"""
표지용 배경 이미지를 만듭니다.  ->  assets/cover_bg.png  (1080 x 1350, 세로 4:5)

- 주제: 뿌리면 크림이 되는 미스트 (미스트 물방울, 크림 거품 느낌)
- 분위기: 손글씨 레시피 카드 같은 따뜻한 주방 감성 (design_rules.md 색만 사용)
- 가운데와 아래는 비워 두어 글자를 얹기 쉽게 합니다
- 글자, 숫자, 로고, 사람 얼굴, 상표는 넣지 않습니다

실행:  py templates/make_background.py
"""
import random
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "cover_bg.png"
W, H = 1080, 1350

MAIN = (201, 115, 90)     # #C9735A
SUB1 = (248, 211, 192)    # #F8D3C0
SUB2 = (255, 235, 176)    # #FFEBB0
BG = (255, 248, 239)      # #FFF8EF
PEACH2 = (251, 230, 218)  # #FBE6DA
INK = (59, 42, 36)        # #3B2A24
PAPER = (255, 253, 249)   # #FFFDF9

random.seed(7)  # 매번 같은 그림이 나오게


def vertical_gradient(top, bottom):
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        d.line([(0, y), (W, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))
    return img


def soft_blob(base, cx, cy, r, color, blur):
    # 모양(투명도)만 흐리게 하고 색은 그대로 두어야 가장자리가 회색으로 변하지 않아요
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(blur))
    layer = Image.new("RGBA", (W, H), color + (255,))
    layer.putalpha(mask)
    base.alpha_composite(layer)


def bubble(d, cx, cy, r, width=4):
    """테두리 있는 물방울 + 반짝이는 하이라이트"""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=PAPER + (235,), outline=INK + (255,), width=width)
    hr = r * 0.55
    d.arc([cx - hr, cy - hr, cx + hr, cy + hr], start=200, end=260, fill=SUB1 + (255,), width=max(3, int(r * 0.14)))


def main():
    img = vertical_gradient(PEACH2, BG).convert("RGBA")

    # 1) 부드럽게 번진 색 덩어리 (위쪽과 가장자리에만)
    soft_blob(img, 930, 120, 360, SUB1, 70)
    soft_blob(img, 90, 230, 230, SUB2, 60)
    soft_blob(img, 60, 1290, 230, SUB1, 70)
    soft_blob(img, 1060, 1180, 170, SUB2, 60)

    # 2) 크림 거품처럼 둥글게 이어진 윗부분
    cream = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cd = ImageDraw.Draw(cream)
    for cx, r in [(-20, 95), (150, 120), (330, 100), (520, 130), (720, 105), (900, 125), (1090, 100)]:
        cd.ellipse([cx - r, -r - 20, cx + r, r - 20], fill=PAPER + (255,))
    img.alpha_composite(cream)
    # 거품 아래 테두리 선
    line = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(line)
    for cx, r in [(-20, 95), (150, 120), (330, 100), (520, 130), (720, 105), (900, 125), (1090, 100)]:
        ld.arc([cx - r, -r - 20, cx + r, r - 20], start=10, end=170, fill=INK + (255,), width=4)
    img.alpha_composite(line)
    # 겹치는 부분 선 지우기 (거품 안쪽은 다시 크림색으로)
    inner = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    idr = ImageDraw.Draw(inner)
    for cx, r in [(-20, 95), (150, 120), (330, 100), (520, 130), (720, 105), (900, 125), (1090, 100)]:
        idr.ellipse([cx - r + 4, -r - 16, cx + r - 4, r - 24], fill=PAPER + (255,))
    img.alpha_composite(inner)

    # 3) 미스트 물방울 (오른쪽 위 ~ 왼쪽 위로 흩어지게, 가운데는 비움)
    d = ImageDraw.Draw(img, "RGBA")
    for cx, cy, r in [(880, 300, 46), (980, 380, 26), (790, 380, 20), (930, 470, 14),
                      (160, 400, 30), (90, 330, 16), (240, 330, 12)]:
        bubble(d, cx, cy, r, width=4 if r > 18 else 3)
    for cx, cy, r, c in [(720, 300, 9, MAIN), (1010, 290, 7, MAIN), (850, 430, 6, SUB2),
                         (60, 430, 7, MAIN), (300, 400, 6, MAIN), (200, 470, 5, SUB1)]:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c + (255,))

    # 4) 아래쪽 가장자리의 작은 장식 (글자 칸은 침범하지 않게 모서리에만)
    for cx, cy, r in [(1000, 1130, 22), (60, 1100, 14)]:   # 아래 계정명·페이지 번호와 겹치지 않게
        bubble(d, cx, cy, r, width=3)

    # 5) 종이 질감 (아주 약한 잡티)
    noise = Image.effect_noise((W, H), 10).convert("L").point(lambda v: 200 + v // 5)
    noise = Image.merge("RGBA", (noise, noise, noise, Image.new("L", (W, H), 12)))
    img.alpha_composite(noise)

    OUT.parent.mkdir(exist_ok=True)
    img.convert("RGB").save(OUT, "PNG")
    print(f"배경 이미지를 만들었어요: {OUT.relative_to(ROOT)}  ({W}x{H})")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
