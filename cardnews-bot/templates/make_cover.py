# -*- coding: utf-8 -*-
"""
cards.json 의 1장(표지)을 1080 x 1350 PNG 로 만듭니다.  ->  output/cover.png
디자인 값은 templates/design_rules.md 를 따릅니다. (A 방식: 크림색 레시피 카드)

실행:  py templates/make_cover.py
필요한 도구: Pillow  (설치: py -m pip install pillow)

이 파일의 도구(폰트, 줄바꿈 등)는 make_cards.py 에서도 같이 씁니다.
"""
import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("[오류] 이미지 도구 Pillow 가 설치되어 있지 않아요.")
    print("       검은 창에서  py -m pip install pillow  를 실행한 뒤 다시 해 주세요.")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
CARDS = ROOT / "cards.json"
OUT = ROOT / "output" / "cover.png"

# ---------------- 디자인 규칙 (design_rules.md) ----------------
W, H = 1080, 1350
MAIN = "#C9735A"      # 메인: 테라코타
SUB1 = "#F8D3C0"      # 보조 1: 피치
SUB2 = "#FFEBB0"      # 보조 2: 버터
BG = "#FFF8EF"        # 배경: 크림
PAPER = "#FFFDF9"     # 상자 안쪽
INK = "#3B2A24"       # 글자: 진갈색
SOFT = "#8A766C"      # 보조 글자
LINE = "#EADBCF"      # 점선
TOP, SIDE, BOTTOM = 84, 84, 76
TEXT_W = W - SIDE * 2

ACCOUNT = "@weekly.beauty.recipe"   # 계정 이름 (확정)
SERIES = "HEALING RECIPE"
EYEBROW = "NEW ARRIVAL"
SECTION = "신상 편"

FONT_DIR = Path("C:/Windows/Fonts")
FONTS = {
    "title": "malgunbd.ttf",   # 맑은 고딕 Bold
    "body": "malgun.ttf",      # 맑은 고딕
    "mono": "consolab.ttf",    # Consolas Bold
}


class CardError(Exception):
    """사용자에게 보여 줄 한국어 오류"""


def font(kind, size):
    path = FONT_DIR / FONTS[kind]
    if not path.exists():
        raise CardError(f"폰트 파일을 찾지 못했어요: {path}\n"
                        "       윈도우 기본 폰트(맑은 고딕, Consolas)가 있는지 확인해 주세요.")
    return ImageFont.truetype(str(path), size)


def text_w(draw, s, f):
    return draw.textlength(s, font=f)


def wrap(draw, text, f, max_w):
    """단어(띄어쓰기) 단위로 줄을 바꿉니다. 한 단어가 너무 길면 글자 단위로 자릅니다."""
    lines = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            trial = (cur + " " + word).strip()
            if text_w(draw, trial, f) <= max_w:
                cur = trial
                continue
            if cur:
                lines.append(cur)
            cur = ""
            for ch in word:  # 단어 하나가 한 줄보다 길 때: 글자 단위로 자르기
                if text_w(draw, cur + ch, f) <= max_w:
                    cur += ch
                else:
                    lines.append(cur)
                    cur = ch
        lines.append(cur)
    return [l for l in lines if l]


def balanced_wrap(draw, text, f, max_w):
    """줄 수는 그대로 두고, 줄 길이가 비슷해지도록 나눕니다 (한쪽만 긴 줄 방지)."""
    lines = wrap(draw, text, f, max_w)
    if len(lines) < 2:
        return lines
    best, w = lines, max_w
    while w > max_w * 0.5:
        w -= 10
        trial = wrap(draw, text, f, w)
        if len(trial) != len(lines):
            break
        best = trial
    return best


def fit_title(draw, text, max_w, max_h, start=100, smallest=72, max_lines=3, kind="title"):
    """제목이 정해진 칸에 들어갈 때까지 줄바꿈하고, 그래도 넘치면 글자를 조금씩 줄입니다."""
    size = start
    while True:
        f = font(kind, size)
        lines = balanced_wrap(draw, text, f, max_w)
        height = len(lines) * size * 1.14
        if (len(lines) <= max_lines and height <= max_h) or size <= smallest:
            return f, size, lines
        size -= 4


def dashed_line(draw, y, x1, x2, color=LINE, dash=14, gap=10, width=2):
    x = x1
    while x < x2:
        draw.line([(x, y), (min(x + dash, x2), y)], fill=color, width=width)
        x += dash + gap


def mist_bottle(draw, cx, bottom):
    """미스트 병 그림 (사진 대신 쓰는 일러스트)"""
    bw, bh = 200, 300
    x1, y1, x2, y2 = cx - bw // 2, bottom - bh, cx + bw // 2, bottom
    draw.rounded_rectangle([x1, y1, x2, y2], radius=34, fill=PAPER, outline=INK, width=5)
    draw.rounded_rectangle([x1 + 22, y1 + 90, x2 - 22, y1 + 200], radius=18, fill=SUB1, outline=INK, width=3)
    lab = font("mono", 34)
    t = "MIST"
    draw.text((cx - text_w(draw, t, lab) / 2, y1 + 125), t, font=lab, fill=INK)
    draw.rectangle([cx - 28, y1 - 46, cx + 28, y1], fill=INK)                          # 목
    draw.rounded_rectangle([cx - 52, y1 - 110, cx + 52, y1 - 40], radius=14, fill=INK)  # 노즐
    for i, (dx, dy, r) in enumerate([(-90, -86, 14), (-135, -104, 11), (-128, -60, 10),
                                     (-180, -120, 8), (-176, -78, 8), (-220, -98, 6)]):
        draw.ellipse([cx + dx - r, y1 + dy - r, cx + dx + r, y1 + dy + r],
                     fill=MAIN if i % 2 == 0 else SUB1, outline=INK if r > 9 else None, width=2)


def load_cards():
    if not CARDS.exists():
        raise CardError(f"cards.json 파일이 없어요: {CARDS}")
    try:
        data = json.loads(CARDS.read_text(encoding="utf-8-sig"))
        cards = sorted(data["cards"], key=lambda c: c["no"])
    except json.JSONDecodeError as e:
        raise CardError(f"cards.json 형식이 잘못됐어요 ({e.lineno}번째 줄 근처). 쉼표나 따옴표를 확인해 주세요.")
    except (KeyError, TypeError):
        raise CardError('cards.json 은 {"cards":[{"no":1,"title":"","body":""}]} 형식이어야 해요.')
    if not cards or cards[0]["no"] != 1:
        raise CardError('cards.json 에서 1장("no":1) 카드를 찾지 못했어요.')
    return cards


def render_cover(card, total=6):
    """A 방식 표지: 크림색 바탕 + 형광펜 제목 + 미스트 병 그림"""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    d.ellipse([W - 470, 760, W + 210, 1440], fill=SUB1)
    d.ellipse([SIDE + 330, 1030, SIDE + 500, 1200], fill=SUB2)

    d.text((SIDE, TOP + 30), SERIES, font=font("mono", 26), fill=INK, anchor="ls")
    d.text((W - SIDE, TOP + 30), SECTION, font=font("body", 26), fill=SOFT, anchor="rs")
    dashed_line(d, TOP + 56, SIDE, W - SIDE)

    y = TOP + 56 + 120
    d.text((SIDE, y), EYEBROW, font=font("mono", 28), fill=MAIN, anchor="la")
    y += 28 + 24

    tf, size, lines = fit_title(d, card.get("title", "").strip(), TEXT_W, max_h=420)
    lh = size * 1.14
    for i, line in enumerate(lines):
        if i == len(lines) - 1:   # 마지막 줄에 형광펜 밑줄
            lw = text_w(d, line, tf)
            d.rectangle([SIDE - 6, y + lh * 0.68, SIDE + lw + 6, y + lh * 0.98], fill=SUB1)
        d.text((SIDE, y), line, font=tf, fill=INK, anchor="la")
        y += lh

    sub = card.get("body", "").strip()
    if sub:
        y += 36
        bf = font("body", 36)
        for line in wrap(d, sub, bf, TEXT_W):
            d.text((SIDE, y), line, font=bf, fill=SOFT, anchor="la")
            y += 36 * 1.55

    mist_bottle(d, cx=W - SIDE - 150, bottom=H - BOTTOM - 70)

    mono22 = font("mono", 22)
    d.text((SIDE, H - BOTTOM), ACCOUNT, font=mono22, fill=SOFT, anchor="ld")
    d.text((W - SIDE, H - BOTTOM), f"01 / {total:02d}  swipe →", font=mono22, fill=SOFT, anchor="rd")

    warn = "제목과 부제가 길어서 아래 그림과 가까워요." if y > H - BOTTOM - 420 else ""
    return img, size, lines, warn


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        cards = load_cards()
        img, size, lines, warn = render_cover(cards[0], total=len(cards))
        OUT.parent.mkdir(exist_ok=True)
        img.save(OUT, "PNG")
    except CardError as e:
        print(f"[오류] {e}")
        sys.exit(1)
    except PermissionError:
        print(f"[오류] {OUT} 을 저장하지 못했어요. 그림 파일이 열려 있으면 닫고 다시 해 주세요.")
        sys.exit(1)
    if warn:
        print("※ " + warn)
    print(f"표지를 만들었어요: {OUT.relative_to(ROOT)}")
    print(f"  제목 {size}px, {len(lines)}줄: " + " / ".join(lines))


if __name__ == "__main__":
    main()
