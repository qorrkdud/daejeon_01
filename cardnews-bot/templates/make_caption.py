# -*- coding: utf-8 -*-
"""
cards.json 으로 인스타 캡션을 만듭니다.  ->  output/caption.txt

구성: 호기심 후크 1줄 / 핵심 요약 3줄 / 저장·공유 문장 / 팔로우 안내 / 출처 / 해시태그 8개

- cards.json 에 "caption" 칸이 있으면 그 문구를 그대로 씁니다 (Claude가 원문을 보고 쓴 문구).
- 없으면 카드 내용으로 '초안'을 만들고, 다듬어야 한다고 알려 줍니다.

실행:  py templates/make_caption.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARDS = ROOT / "cards.json"
OUT = ROOT / "output" / "caption.txt"
ACCOUNT = "@weekly.beauty.recipe"   # 계정 이름 (make_cover.py 와 같게)
DEFAULT_TAGS = ["스킨케어", "뷰티신상", "뷰티초보", "뷰티루틴"]   # 일반 해시태그 (부족할 때 채움)
HYPE = ["인생템", "무조건", "역대급", "최고", "완벽", "기적", "100%", "필수템"]   # 과장 표현 검사


def first_sentence(s):
    s = s.replace("\n", " ").strip()
    m = re.match(r"(.+?[.!?요])(\s|$)", s)
    return (m.group(1) if m else s).strip()


def source_line(src):
    parts = [src.get("name", "")]
    if src.get("title"):
        parts.append(f"「{src['title']}」")
    if src.get("date"):
        parts.append(src["date"])
    line = "출처: " + ", ".join(p for p in parts if p)
    if src.get("link"):
        line += f"\n원문: {src['link']}"
    return line


def tag(t):
    return "#" + re.sub(r"[\s#]", "", t)


def build(data):
    cards = sorted(data["cards"], key=lambda c: c["no"])
    cap = data.get("caption")
    draft = cap is None
    if draft:   # 초안: 카드 내용으로 채우기
        cap = {
            "hook": cards[0]["title"],
            "summary": [first_sentence(c["body"]) for c in cards[1:4]],
            "cta": "다시 보고 싶으면 저장, 필요한 친구에게 공유해 주세요 🔖",
            "follow": "팔로우하면 뷰티 신상을 레시피처럼 쉽게 알려 드려요",
            "hashtags": [],
        }
    tags = list(dict.fromkeys(cap.get("hashtags", [])))
    for t in DEFAULT_TAGS:
        if len(tags) >= 8:
            break
        if t not in tags:
            tags.append(t)
    tags = tags[:8]

    lines = [cap["hook"], ""]
    lines += [f"✔ {s}" for s in cap["summary"][:3]]
    lines += ["", cap["cta"], "", f"{ACCOUNT} {cap['follow']}"]
    if cap.get("note"):
        lines += ["", f"※ {cap['note']}"]
    if data.get("source"):
        lines += ["", source_line(data["source"])]
    lines += ["", " ".join(tag(t) for t in tags)]
    text = "\n".join(lines) + "\n"

    warns = []
    if draft:
        warns.append("cards.json 에 caption 칸이 없어서 카드 문장으로 '초안'을 만들었어요. 올리기 전에 다듬어 주세요.")
    if len(cap["summary"]) < 3:
        warns.append(f"핵심 요약이 {len(cap['summary'])}줄뿐이에요 (3줄 필요).")
    if len(tags) < 8:
        warns.append(f"해시태그가 {len(tags)}개예요 (8개 필요).")
    if not data.get("source"):
        warns.append("cards.json 에 source(출처)가 없어요. 출처는 꼭 넣어야 해요.")
    hype = [w for w in HYPE if w in text]
    if hype:
        warns.append("과장 표현이 들어 있어요: " + ", ".join(hype))
    if len(text) > 2200:
        warns.append(f"캡션이 {len(text)}자예요. 인스타 캡션 최대 길이(2,200자)를 넘어요.")
    return text, warns


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if not CARDS.exists():
        print(f"[오류] cards.json 파일이 없어요: {CARDS}")
        sys.exit(1)
    try:
        data = json.loads(CARDS.read_text(encoding="utf-8-sig"))
        text, warns = build(data)
    except json.JSONDecodeError as e:
        print(f"[오류] cards.json 형식이 잘못됐어요 ({e.lineno}번째 줄 근처).")
        sys.exit(1)
    except (KeyError, IndexError, TypeError) as e:
        print(f"[오류] cards.json 의 caption 칸 형식을 확인해 주세요 (없는 칸: {e}).")
        sys.exit(1)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"캡션을 만들었어요: {OUT.relative_to(ROOT)} ({len(text)}자)")
    for w in warns:
        print("  ※ " + w)


if __name__ == "__main__":
    main()
