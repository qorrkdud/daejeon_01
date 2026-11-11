# -*- coding: utf-8 -*-
"""
인스타그램 프로필 이미지를 만듭니다.  ->  assets/profile.png (1080 x 1080)

- 컨셉: '레시피 그릇'에 담긴 몽글몽글한 세안 거품 + 물방울 (뷰티 루틴을 요리 레시피처럼)
- 색: design_rules.md (피치 배경, 테라코타 그릇, 크림 거품, 진갈색 선, 버터 반짝이)
- 인스타 프로필은 동그랗게 잘리고 아주 작게 보여서, 글자 없이 그림만 크게 넣었어요.

실행:  py templates/make_profile.py
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "profile.png"
SIZE = 1080
SS = 2                      # 2배로 크게 그린 뒤 줄여서 선을 매끄럽게
N = SIZE * SS
CX, CY, ZOOM = N / 2, N * 0.53, 1.18   # 그림 전체 위치·크기

MAIN, SUB1, SUB2 = "#C9735A", "#F8D3C0", "#FFEBB0"
PEACH2, PAPER, INK = "#FBE6DA", "#FFFDF9", "#3B2A24"
LINE_W = 34


def p(x, y):
    """기준 좌표(2160 칸)를 가운데 기준으로 키워서 옮김"""
    return (CX + (x - 1080) * ZOOM, CY + (y - 1130) * ZOOM)


def box(cx, cy, rx, ry=None):
    ry = rx if ry is None else ry
    x1, y1 = p(cx - rx, cy - ry)
    x2, y2 = p(cx + rx, cy + ry)
    return [x1, y1, x2, y2]


def main():
    img = Image.new("RGB", (N, N), SUB1)
    d = ImageDraw.Draw(img)
    d.ellipse([N * 0.08, N * 0.08, N * 0.92, N * 0.92], fill=PEACH2)   # 가운데 밝은 원

    lw = int(LINE_W * ZOOM)

    # 1) 거품기 (먼저 그려서 철사 아랫부분은 거품 속에 묻히게)
    whisk = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    wd = ImageDraw.Draw(whisk)
    base = p(1270, 1080)                       # 거품 속에 꽂힌 지점
    bx, by = base
    for half_w in (140, 85, 30):               # 철사 고리 3개
        wd.ellipse([bx - half_w * ZOOM, by - 430 * ZOOM, bx + half_w * ZOOM, by + 40 * ZOOM],
                   outline=INK, width=int(22 * ZOOM))
    wd.rounded_rectangle([bx - 32 * ZOOM, by - 480 * ZOOM, bx + 32 * ZOOM, by - 410 * ZOOM],
                         radius=int(10 * ZOOM), fill=INK)                          # 손잡이 이음새
    wd.rounded_rectangle([bx - 46 * ZOOM, by - 700 * ZOOM, bx + 46 * ZOOM, by - 470 * ZOOM],
                         radius=int(46 * ZOOM), fill=MAIN, outline=INK, width=int(22 * ZOOM))  # 손잡이
    whisk = whisk.rotate(-28, center=base, resample=Image.BICUBIC)
    img.paste(whisk, (0, 0), whisk)
    d = ImageDraw.Draw(img)

    # 2) 거품 (테두리 먼저 → 안쪽을 다시 칠해 겹친 선 지우기). 아래 네모가 그릇과의 빈틈을 메움
    foam = [(700, 1170, 175), (890, 1030, 215), (1110, 960, 235), (1340, 1040, 205), (1490, 1170, 160)]
    base_rect = (560, 1120, 1600, 1290)
    for x, y, r in foam:
        d.ellipse(box(x, y, r), fill=INK)
    x1, y1 = p(base_rect[0], base_rect[1]); x2, y2 = p(base_rect[2], base_rect[3])
    d.rectangle([x1, y1, x2, y2], fill=INK)
    for x, y, r in foam:
        d.ellipse(box(x, y, r - LINE_W / ZOOM), fill=PAPER)
    d.rectangle([x1 + lw, y1, x2 - lw, y2], fill=PAPER)
    for x, y, r in foam[1:4]:   # 거품 반짝이
        d.arc(box(x - r * 0.25, y - r * 0.25, r * 0.5), start=200, end=265, fill=SUB1, width=int(26 * ZOOM))

    # 3) 믹싱볼 (아래 반원) + 버터색 띠 + 두꺼운 테두리
    bowl = box(1080, 1270, 590, 400)
    mask = Image.new("L", (N, N), 0)
    ImageDraw.Draw(mask).pieslice(bowl, 0, 180, fill=255)
    layer = Image.new("RGB", (N, N), MAIN)
    ld = ImageDraw.Draw(layer)
    ld.rectangle([0, p(0, 1420)[1], N, p(0, 1490)[1]], fill=SUB2)
    img.paste(layer, (0, 0), mask)
    d.pieslice(bowl, 0, 180, outline=INK, width=lw)
    d.rounded_rectangle(box(1080, 1270, 640, 46), radius=int(46 * ZOOM), fill=PAPER, outline=INK, width=lw)  # 그릇 테두리

    # 3) 떠다니는 물방울
    for x, y, r in [(500, 880, 70), (400, 1080, 42), (1770, 1020, 52), (1690, 1190, 32)]:
        d.ellipse(box(x, y, r), fill=PAPER, outline=INK, width=int(22 * ZOOM))
        d.arc(box(x - r * 0.2, y - r * 0.2, r * 0.45), start=200, end=270, fill=SUB1, width=int(12 * ZOOM))

    # 4) 버터색 반짝이 (네 갈래 별)
    for x, y, s in [(660, 660, 74), (470, 690, 40)]:
        pts = [p(x, y - s), p(x + s * 0.28, y - s * 0.28), p(x + s, y), p(x + s * 0.28, y + s * 0.28),
               p(x, y + s), p(x - s * 0.28, y + s * 0.28), p(x - s, y), p(x - s * 0.28, y - s * 0.28)]
        d.polygon(pts, fill=SUB2, outline=INK, width=int(14 * ZOOM))

    out = img.resize((SIZE, SIZE), Image.LANCZOS)
    OUT.parent.mkdir(exist_ok=True)
    out.save(OUT, "PNG")
    print(f"프로필 이미지를 만들었어요: {OUT.relative_to(ROOT)} ({SIZE}x{SIZE})")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
