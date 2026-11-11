# -*- coding: utf-8 -*-
"""
make.bat 이 실행하는 프로그램 (카드뉴스 만들기 한 번에)

[1/5] 후보 고르기     : picks/오늘날짜.md 의 추천 목록을 보여 주고 번호를 물어봅니다
[2/5] cards.json 준비 : 고른 소식의 원문을 sources 에 저장하고, 그 소식으로 쓴 cards.json 이 있는지 확인합니다
[3/5] 카드 이미지 만들기 : templates/make_cards.py (방식 A / B / 표지만 B)
[4/5] 캡션 만들기     : templates/make_caption.py -> output/caption.txt
[5/5] 폴더 열기       : output 폴더를 엽니다
"""
import html
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KST = timezone(timedelta(hours=9))
CARDS = ROOT / "cards.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) cardnews-bot/1.0"
DEFAULT_MODE = os.environ.get("DEFAULT_MODE", "HTML")   # make.bat 에서 바꿀 수 있어요
MODES = {"1": ("HTML", "레시피 카드 (제품 사진 포함)"), "2": ("A", "A (크림 레시피 카드, 글 위주)"),
         "3": ("B", "B (배경 그림)"), "4": ("coverB", "표지만 B")}
PHOTO_DIR = ROOT / "assets" / "products"


class StepError(Exception):
    def __init__(self, step, msg):
        super().__init__(msg)
        self.step = step


def ask(prompt):
    try:
        # 눈에 안 보이는 문자(BOM 등)가 붙어 와도 번호를 알아보게 정리
        return input(prompt).strip().lstrip("﻿​").strip()
    except EOFError:
        raise StepError("입력", "입력을 받을 수 없어요. make.bat 를 더블클릭해서 실행해 주세요.")


# ---------------------------------------------------------------- [1/5]
def read_picks(today):
    path = ROOT / "picks" / f"{today}.md"
    if not path.exists():
        raise StepError("1/5 후보 고르기",
                        f"오늘 추천 파일이 없어요: picks\\{today}.md\n"
                        "       먼저 morning.bat 를 실행해서 오늘 후보를 만들어 주세요.")
    picks, cur = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"## (\d+)위 · (\d+)/25점 · (.+)", line)
        if m:
            cur = {"rank": int(m.group(1)), "score": m.group(2), "title": m.group(3).strip()}
            picks.append(cur)
        elif cur and line.startswith("- 링크:"):
            cur["link"] = line.split(":", 1)[1].strip()
        elif cur and line.startswith("- 출처:"):
            cur["source"] = line.split(":", 1)[1].split("/")[0].strip()
    picks = [p for p in picks if p.get("link")]
    if not picks:
        raise StepError("1/5 후보 고르기", f"picks\\{today}.md 안에 고를 수 있는 후보가 없어요.")
    return picks


def choose(picks):
    print("오늘의 추천 후보\n")
    for p in picks:
        print(f"  {p['rank']}. [{p['score']}점] {p['title']}  ({p.get('source', '')})")
    print()
    for _ in range(5):
        a = ask(f"몇 번 소식으로 만들까요? (1~{len(picks)}): ")
        if a.isdigit() and any(p["rank"] == int(a) for p in picks):
            return next(p for p in picks if p["rank"] == int(a))
        print("  번호를 다시 입력해 주세요.")
    raise StepError("1/5 후보 고르기", "번호를 5번 잘못 입력해서 멈췄어요. 다시 실행해 주세요.")


def choose_mode():
    default_key = next(k for k, (m, _) in MODES.items() if m == DEFAULT_MODE)
    print("\n디자인 방식")
    for k, (m, name) in MODES.items():
        print(f"  {k}. {name}" + ("  ← 기본" if k == default_key else ""))
    a = ask(f"번호를 고르세요 (그냥 Enter 를 누르면 {MODES[default_key][1]}): ") or default_key
    return MODES.get(a, MODES[default_key])


# ---------------------------------------------------------------- [2/5]
def fetch_page(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
    m = re.search(rb'charset=["\']?([\w-]+)', raw[:3000])
    return raw.decode(m.group(1).decode() if m else "utf-8", errors="replace")


def save_photo(pick, today):
    """기사 속 대표 사진(보통 제품 사진)을 assets/products 에 저장합니다."""
    old = sorted(PHOTO_DIR.glob(f"{today}_pick{pick['rank']}.*"))
    if old:
        return old[0], None, "이미 저장돼 있어요"
    try:
        s = fetch_page(pick["link"])
    except Exception as e:
        return None, None, f"기사를 열지 못했어요 ({e})"
    url, credit = None, None
    m = re.search(r'<img[^>]+xtype="photo"[^>]*>', s, re.I)            # 기사 본문 사진 (코스인코리아 등)
    if m:
        tag = m.group(0)
        u = re.search(r'src="([^"]+)"', tag)
        url = u.group(1) if u else None
        c = re.search(r'title="[^"]*출처\s*[:：]\s*([^"]+)"', tag)
        credit = c.group(1).strip() if c else None
    if not url:                                                           # 기사 본문 원본 사진 (장업신문·뷰티경제 등)
        m = re.search(r'<img[^>]+src="([^"]*/news/photo/[^"]+)"', s, re.I)
        url = m.group(1) if m else None
    if not url:                                                           # 대표 이미지 (작은 미리보기일 수 있음)
        m = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', s, re.I) or \
            re.search(r'<meta[^>]+content="([^"]+)"[^>]+property="og:image"', s, re.I)
        url = m.group(1) if m else None
    if not url:
        return None, None, "기사에서 사진을 찾지 못했어요"
    url = urllib.parse.urljoin(pick["link"], html.unescape(url))
    ext = ".png" if url.lower().split("?")[0].endswith(".png") else ".jpg"
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    out = PHOTO_DIR / f"{today}_pick{pick['rank']}{ext}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": pick["link"]})
        with urllib.request.urlopen(req, timeout=30) as r:
            out.write_bytes(r.read())
    except Exception as e:
        return None, None, f"사진을 받지 못했어요 ({e})"
    try:
        from PIL import Image
        w, h = Image.open(out).size
        if min(w, h) < 500:
            print(f"    ※ 사진이 작아요 ({w}x{h}). 카드에서 흐릿할 수 있어요.")
    except Exception:
        pass
    return out, credit or f"{pick.get('source', '')} 기사 사진", None


def save_article(pick, today):
    """원문을 sources 폴더에 보관합니다 (카드에는 그대로 쓰지 않아요)."""
    out = ROOT / "sources" / f"{today}_pick{pick['rank']}.txt"
    if out.exists():
        return out, True
    try:
        s = fetch_page(pick["link"])
    except Exception as e:
        return None, f"원문을 가져오지 못했어요 ({e})"
    m = re.search(r'<(?:div|article)[^>]*(?:id|itemprop)="?(article-view-content-div|articleBody|article_body|'
                  r'news_body_area|textinput)[^>]*>(.*?)</(?:div|article)>', s, re.S | re.I)
    body = m.group(2) if m else " ".join(re.findall(r"<p[^>]*>(.*?)</p>", s, re.S))
    body = re.sub(r"<script.*?</script>|<style.*?</style>", "", body, flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", "\n", body))
    text = "\n".join(l.strip() for l in text.splitlines() if l.strip())
    head = (f"출처: {pick.get('source', '')}\n제목: {pick['title']}\n링크: {pick['link']}\n"
            f"저장: {today} (원본 보관용, 카드에 그대로 쓰지 않기)\n\n")
    out.write_text(head + text + "\n", encoding="utf-8")
    return out, True


def cards_match(pick):
    if not CARDS.exists():
        return False
    try:
        data = json.loads(CARDS.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        raise StepError("2/5 cards.json 준비", f"cards.json 형식이 잘못됐어요 ({e.lineno}번째 줄 근처).")
    return data.get("source", {}).get("link", "").rstrip("/") == pick["link"].rstrip("/")


def check_lengths():
    data = json.loads(CARDS.read_text(encoding="utf-8-sig"))
    bad = []
    last = max(c["no"] for c in data["cards"])
    for c in data["cards"]:
        if c["no"] == 1 and len(c["title"]) > 15:
            bad.append(f"1장 제목 {len(c['title'])}자 (15자 이내)")
        if 2 <= c["no"] < last and len(c["body"]) > 60:   # 표지와 마지막 장을 뺀 본문 카드
            bad.append(f"{c['no']}장 본문 {len(c['body'])}자 (60자 이내)")
    return bad


# ---------------------------------------------------------------- 실행
def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    today = datetime.now(KST).strftime("%Y-%m-%d")

    try:
        # [1/5]
        print("\n[1/5] 후보 고르기\n")
        pick = choose(read_picks(today))
        mode, mode_name = choose_mode()

        # [2/5]
        print(f"\n[2/5] cards.json 준비 — {pick['title']}")
        src, ok = save_article(pick, today)
        if src:
            print(f"  원문 보관: {src.relative_to(ROOT)}")
        else:
            print(f"  ※ {ok} (원문 보관은 건너뛰고 계속해요)")
        photo, credit, why = save_photo(pick, today)
        if photo and credit:
            print(f"  제품 사진 저장: {photo.relative_to(ROOT)} (사진 출처: {credit})")
            print("    → 제품 사진이 맞는지 한 번 열어서 확인해 주세요.")
            if src and "사진:" not in src.read_text(encoding="utf-8")[:600]:
                txt = src.read_text(encoding="utf-8")
                src.write_text(txt.replace("\n\n", f"\n사진: {photo.relative_to(ROOT).as_posix()} (출처: {credit})\n\n", 1),
                               encoding="utf-8")
        elif photo:
            print(f"  제품 사진: {photo.relative_to(ROOT)} ({why})")
        else:
            print(f"  ※ 제품 사진: {why}. assets\\products 에 직접 넣어 주세요.")
        if not cards_match(pick):
            raise StepError(
                "2/5 cards.json 준비",
                "이 소식으로 쓴 cards.json 이 아직 없어요.\n"
                "       카드 문구는 기사를 읽고 '내 말로' 새로 써야 해서 자동으로 만들지 않아요.\n"
                "       Claude에게 이렇게 말해 주세요:\n"
                f"         \"오늘 picks {pick['rank']}위 소식으로 cards.json 만들어 줘\"\n"
                "       cards.json 이 생기면 make.bat 를 다시 실행하세요.")
        bad = check_lengths()
        if bad:
            print("  ※ 글자 수 규칙을 넘는 카드가 있어요: " + ", ".join(bad))
        else:
            print("  cards.json 확인 완료 (글자 수 규칙 통과)")

        # [3/5]
        print(f"\n[3/5] 카드 이미지 만들기 — 방식 {mode_name}", flush=True)
        if mode == "HTML":
            r = subprocess.run([sys.executable, str(ROOT / "templates" / "make_html_cards.py")])
        else:
            r = subprocess.run([sys.executable, str(ROOT / "templates" / "make_cards.py"), "--mode", mode])
        if r.returncode != 0:
            raise StepError("3/5 카드 이미지 만들기", "그림을 만드는 중에 문제가 생겼어요. 바로 위 안내를 확인해 주세요.")

        # [4/5]
        print("\n[4/5] 캡션 만들기", flush=True)
        r = subprocess.run([sys.executable, str(ROOT / "templates" / "make_caption.py")])
        if r.returncode != 0:
            raise StepError("4/5 캡션 만들기", "캡션을 만드는 중에 문제가 생겼어요. 바로 위 안내를 확인해 주세요.")

        # [5/5]
        print("\n[5/5] 폴더 열기")
        try:
            os.startfile(ROOT / "output")
            print("  output 폴더를 열었어요.")
        except Exception as e:
            raise StepError("5/5 폴더 열기", f"폴더를 열지 못했어요 ({e}). 직접 output 폴더를 열어 주세요.")

        print("\n완료! 카드 이미지와 caption.txt 가 output 폴더에 있어요.")
    except StepError as e:
        print(f"\n[오류] {e.step} 단계에서 멈췄어요.\n       {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n중간에 멈췄어요.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[오류] 예상하지 못한 문제가 생겼어요: {type(e).__name__}: {e}")
        print("       이 화면을 Claude에게 보여 주시면 고쳐 드릴게요.")
        sys.exit(1)


if __name__ == "__main__":
    main()
