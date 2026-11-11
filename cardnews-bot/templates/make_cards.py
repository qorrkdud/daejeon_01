# -*- coding: utf-8 -*-
"""
cards.json 으로 카드뉴스 6장을 만듭니다.  ->  output/card_01.png ~ card_06.png

방식 (--mode)
  A       : 크림색 레시피 카드 (배경 그림 없이 design_rules.md 그대로)
  B       : assets/cover_bg.png 배경 사용
            - 표지: 배경 위에 반투명 어두운 띠 + 그림자로 제목을 얹음
            - 본문: 같은 배경을 흐리게 + 반투명 흰색 글자 상자
  coverB  : 표지만 B, 본문은 A

실행 예:  py templates/make_cards.py --mode B
"""
import argparse
import sys
from pathlib import Path

from make_cover import (ACCOUNT, BG, BOTTOM, H, INK, LINE, MAIN, PAPER, ROOT, SECTION,
                        SERIES, SIDE, SOFT, SUB1, SUB2, TEXT_W, TOP, W, CardError,
                        balanced_wrap, dashed_line, fit_title, font, load_cards,
                        render_cover, text_w, wrap)
from PIL import Image, ImageDraw, ImageFilter, ImageStat

BG_FILE = ROOT / "assets" / "cover_bg.png"
OUT_DIR = ROOT / "output"
CREAM = "#FFF8EF"


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def load_bg():
    if not BG_FILE.exists():
        raise CardError(f"배경 그림이 없어요: {BG_FILE}\n"
                        "       먼저  py templates/make_background.py  로 만들거나, 그림을 그 이름으로 넣어 주세요.")
    try:
        bg = Image.open(BG_FILE).convert("RGB")
    except Exception:
        raise CardError(f"배경 그림을 열지 못했어요: {BG_FILE} (PNG/JPG 그림인지 확인해 주세요)")
    if bg.size != (W, H):  # 크기가 다르면 비율을 지켜 꽉 채우고 가운데를 자름
        s = max(W / bg.width, H / bg.height)
        bg = bg.resize((round(bg.width * s), round(bg.height * s)), Image.LANCZOS)
        l, t = (bg.width - W) // 2, (bg.height - H) // 2
        bg = bg.crop((l, t, l + W, t + H))
    return bg


def brightness(img, box):
    """그 영역이 얼마나 밝은지 (0 어두움 ~ 255 밝음)"""
    return ImageStat.Stat(img.crop(box).convert("L")).mean[0]


def auto_color(img, box):
    """배경이 밝으면 진갈색 글자, 어두우면 크림색 글자"""
    return INK if brightness(img, box) > 140 else CREAM


def draw_footer(img, page, total):
    d = ImageDraw.Draw(img)
    f = font("mono", 22)
    y = H - BOTTOM
    left_c = auto_color(img, (SIDE, y - 30, SIDE + 400, y))
    right_c = auto_color(img, (W - SIDE - 300, y - 30, W - SIDE, y))
    d.text((SIDE, y), ACCOUNT, font=f, fill=left_c, anchor="ld")
    tail = "  swipe →" if page == 1 else ""
    d.text((W - SIDE, y), f"{page:02d} / {total:02d}{tail}", font=f, fill=right_c, anchor="rd")


def draw_topbar(img, left, right, y0=TOP):
    d = ImageDraw.Draw(img)
    c = auto_color(img, (SIDE, y0 - 10, W - SIDE, y0 + 40))
    d.text((SIDE, y0 + 30), left, font=font("mono", 26), fill=c, anchor="ls")
    d.text((W - SIDE, y0 + 30), right, font=font("body", 26), fill=c, anchor="rs")
    dashed_line(d, y0 + 56, SIDE, W - SIDE, color=LINE if c == INK else "#6A5249")


def shadow_text(base, xy, text, f, fill, offset=(3, 5), blur=6, alpha=150):
    """글자 아래 부드러운 그림자를 깔고 글자를 씁니다."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((xy[0] + offset[0], xy[1] + offset[1]), text, font=f,
                               fill=(20, 12, 8, alpha), anchor="ma")
    base.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(base).text(xy, text, font=f, fill=fill, anchor="ma")


# ----------------------------------------------------------------------
# 표지 B: 배경 + 반투명 어두운 띠 + 그림자 제목 (가운데 정렬)
# ----------------------------------------------------------------------
def cover_b(card, bg, total):
    img = bg.copy().convert("RGBA")
    d = ImageDraw.Draw(img)
    pad = 56
    tf, size, lines = fit_title(d, card.get("title", "").strip(), TEXT_W - 40, max_h=360)
    lh = size * 1.14
    bf = font("body", 36)
    sub_lines = wrap(d, card.get("body", "").strip(), bf, TEXT_W - 40) if card.get("body") else []
    ef = font("mono", 28)

    block_h = 28 + 26 + len(lines) * lh + (30 + len(sub_lines) * 36 * 1.5 if sub_lines else 0)
    band_h = block_h + pad * 2
    band_top = round(H * 0.52 - band_h / 2)            # 화면 가운데보다 살짝 아래
    band = (0, band_top, W, round(band_top + band_h))

    # 띠 진하기 자동 조절: 배경이 밝을수록 진하게
    lum = brightness(img, band)
    alpha = round(255 * min(0.88, 0.55 + 0.33 * lum / 255))
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rectangle(band, fill=hex_rgb(INK) + (alpha,))
    img.alpha_composite(layer)

    d = ImageDraw.Draw(img)
    y = band_top + pad
    d.text((W / 2, y), "NEW ARRIVAL", font=ef, fill=SUB2, anchor="ma")
    y += 28 + 26
    for line in lines:
        shadow_text(img, (W / 2, y), line, tf, CREAM)
        y += lh
    if sub_lines:
        y += 30
        for line in sub_lines:
            ImageDraw.Draw(img).text((W / 2, y), line, font=bf, fill=SUB1, anchor="ma")
            y += 36 * 1.5

    draw_topbar(img, SERIES, SECTION, y0=TOP + 60)   # 위쪽 크림 거품 아래로
    draw_footer(img, 1, total)
    return img.convert("RGB"), size, lines


# ----------------------------------------------------------------------
# 본문 카드 (A: 크림 바탕 / B: 흐린 배경 + 반투명 흰 상자)
# ----------------------------------------------------------------------
def body_card(card, total, base, translucent):
    no = card["no"]
    img = base.copy().convert("RGBA")
    label = "RECIPE COMPLETE" if no == total else f"RECIPE NOTE {no - 1:02d}"
    draw_topbar(img, label, f"{no:02d} / {total:02d}")
    d = ImageDraw.Draw(img)

    # 크기부터 계산: 제목 + 상자 묶음을 화면 가운데쯤에 놓기 위해
    tf, tsize, tlines = fit_title(d, card.get("title", "").strip(), TEXT_W - 220,
                                  max_h=180, start=72, smallest=56, max_lines=2)
    tlh = tsize * 1.22
    area_top, area_bottom = TOP + 56 + 60, H - BOTTOM - 70
    inner_w = TEXT_W - 2 * 56
    body = card.get("body", "").strip()
    for bsize in range(40, 27, -2):   # 글자가 넘치면 크기를 줄여서 상자 안에 맞춤
        bf = font("body", bsize)
        blines = wrap(d, body, bf, inner_w)
        blh = bsize * 1.6
        box_h = max(380, round(64 * 2 + len(blines) * blh))
        block_h = len(tlines) * tlh + 48 + box_h
        if block_h <= area_bottom - area_top:
            break
    else:
        raise CardError(f"{no}장 본문이 너무 길어서 상자에 들어가지 않아요. 글자를 줄여 주세요.")
    y = round(area_top + (area_bottom - area_top - block_h) * 0.42)   # 가운데보다 살짝 위

    # 큰 번호 장식 (오른쪽)
    nf = font("mono", 150)
    d.text((W - SIDE, y + len(tlines) * tlh + 10), f"{no - 1:02d}" if no < total else "OK",
           font=nf, fill=SUB1, anchor="rd")

    # 제목
    title_c = auto_color(img, (SIDE, y, W - SIDE, y + round(len(tlines) * tlh)))
    for i, line in enumerate(tlines):
        if i == len(tlines) - 1 and title_c == INK:
            lw = text_w(d, line, tf)
            d.rectangle([SIDE - 6, y + tlh * 0.62, SIDE + lw + 6, y + tlh * 0.92], fill=SUB1)
        d.text((SIDE, y), line, font=tf, fill=title_c, anchor="la")
        y += tlh

    box_top = round(y + 48)
    box = (SIDE, box_top, W - SIDE, box_top + box_h)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    if translucent:   # B: 반투명 흰 상자
        ld.rounded_rectangle(box, radius=28, fill=(255, 253, 249, 215), outline=hex_rgb(INK) + (255,), width=3)
    else:             # A: 종이 상자
        ld.rounded_rectangle(box, radius=28, fill=hex_rgb(PAPER) + (255,), outline=hex_rgb(INK) + (255,), width=3)
    img.alpha_composite(layer)

    d = ImageDraw.Draw(img)
    by = box_top + 64
    for line in blines:
        d.text((SIDE + 56, by), line, font=bf, fill=INK, anchor="la")
        by += blh

    draw_footer(img, no, total)
    return img.convert("RGB"), bsize


def plain_base():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.ellipse([W - 300, H - 330, W + 160, H + 130], fill=SUB1)   # 오른쪽 아래 장식
    d.ellipse([-120, H - 260, 140, H], fill=SUB2)
    return img


def blurred_base(bg):
    soft = bg.filter(ImageFilter.GaussianBlur(24))
    return Image.blend(soft, Image.new("RGB", (W, H), BG), 0.25)  # 크림색을 살짝 섞어 차분하게


# ----------------------------------------------------------------------
def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="B", choices=["A", "B", "coverB"])
    mode = ap.parse_args().mode

    try:
        cards = load_cards()
        total = len(cards)
        if total != 6:
            print(f"※ 카드가 {total}장이에요 (보통 6장). 있는 만큼 만들게요.")
        need_bg = mode in ("B", "coverB")
        bg = load_bg() if need_bg else None
        OUT_DIR.mkdir(exist_ok=True)

        saved = []
        # 1장: 표지
        if need_bg:
            img, size, lines = cover_b(cards[0], bg, total)
        else:
            img, size, lines, warn = render_cover(cards[0], total)
            if warn:
                print("※ " + warn)
        p = OUT_DIR / "card_01.png"
        img.save(p)
        saved.append(f"  {p.name}  표지 (제목 {size}px, {len(lines)}줄: {' / '.join(lines)})")

        # 2장~: 본문
        base = blurred_base(bg) if mode == "B" else plain_base()
        for card in cards[1:]:
            img, bsize = body_card(card, total, base, translucent=(mode == "B"))
            p = OUT_DIR / f"card_{card['no']:02d}.png"
            img.save(p)
            saved.append(f"  {p.name}  본문 글자 {bsize}px")
    except CardError as e:
        print(f"[오류] {e}")
        sys.exit(1)
    except PermissionError as e:
        print(f"[오류] 그림을 저장하지 못했어요. 그림 파일이 열려 있으면 닫고 다시 해 주세요. ({e.filename})")
        sys.exit(1)

    name = {"A": "A (크림 레시피 카드)", "B": "B (배경 그림)", "coverB": "표지만 B"}[mode]
    print(f"방식 {name}으로 {len(saved)}장을 만들었어요 → output 폴더")
    print("\n".join(saved))


if __name__ == "__main__":
    main()
