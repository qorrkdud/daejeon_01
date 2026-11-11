# -*- coding: utf-8 -*-
"""
매일 아침 실행하는 프로그램 (식당으로 치면 '아침 장보기 + 재료 고르기')

1) sources/rss_list.txt 의 RSS 주소에서 최근 24시간 글을 모읍니다  -> candidates/날짜.md
2) CLAUDE.md 의 선별 기준 5가지로 채점해서 상위 5개를 고릅니다     -> picks/날짜.md
3) 고른 5개의 링크를 used.txt 에 적어, 다음 날부터는 후보에서 뺍니다

파이썬 기본 기능만 사용합니다. 따로 설치할 것은 없습니다.
"""
import html
import re
import socket
import ssl
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

KST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
RSS_LIST = ROOT / "sources" / "rss_list.txt"
CAND_DIR = ROOT / "candidates"
PICK_DIR = ROOT / "picks"
USED_FILE = ROOT / "used.txt"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) cardnews-bot/1.0"
TOP_N = 5
HOURS = 24


# ----------------------------------------------------------------------
# 채점에 쓰는 단어 목록 (마음껏 추가/삭제해도 됩니다)
# ----------------------------------------------------------------------
TARGET_KW = [
    "올리브영", "올영", "세안", "클렌징", "클렌저", "폼클렌저", "팩클렌저", "선크림", "선케어",
    "자외선", "토너", "패드", "세럼", "앰플", "에센스", "크림", "로션", "마스크팩", "시트팩",
    "립밤", "틴트", "쿠션", "파운데이션", "루틴", "사용법", "피부", "보습", "각질", "모공",
    "트러블", "여드름", "민감", "신제품", "신상", "출시", "리뉴얼", "한정", "기획세트", "스킨케어",
    "skincare", "skin care", "cleanser", "cleansing", "sunscreen", "spf", "serum",
    "moisturizer", "toner", "routine", "olive young", "k-beauty", "korean beauty",
    "launch", "new product", "acne", "pore", "dry skin",
    # 각질 관리 (2026-11-06 추가)
    "각질", "필링", "스크럽", "토너패드", "피부결", "PHA", "AHA", "BHA",
    "exfoliant", "exfoliants", "exfoliator", "exfoliators", "exfoliation", "exfoliating",
    "peel", "peeling", "toner pad", "toner pads", "glass skin", "korean skincare", "korean skin care",
    "smoothing", "brightening",
]
INDUSTRY_KW = [  # 초보 타깃에게는 덜 흥미로운 업계 뉴스
    "실적", "매출", "영업이익", "순이익", "주가", "증권", "투자", "인수", "합병", "상장",
    "대표이사", "선임", "취임", "분기", "공장", "수출", "관세", "ODM", "OEM", "협약", "MOU",
    "전시회", "박람회", "earnings", "revenue", "acquisition", "acquire", "merger",
    "investor", "funding", "ceo", "appoint", "quarter", "tariff", "layoff", "stock",
    "shares", "private equity", "ipo",
]
VISUAL_KW = [
    "제형", "텍스처", "컬러", "색상", "패키지", "용기", "사용법", "방법", "단계", "순서", "팁",
    "비포", "애프터", "전후", "신제품", "출시", "texture", "shade", "color", "packaging",
    "how to", "step", "tips", "before and after", "launch",
    "추천", "비교", "best", "pads", "skin type",   # 제품 모아 보기·비교 글 (2026-11-06 추가)
]
SPECULATIVE_KW = [
    "전망", "예정", "알려졌다", "것으로 보인다", "루머", "소문", "가능성",
    "reportedly", "rumor", "expected to", "plans to",
]
FRESH_KW = ["신상", "신제품", "출시", "론칭", "런칭", "한정", "new", "launch"]
INGREDIENT_KW = [
    "PDRN", "레티놀", "나이아신아마이드", "세라마이드", "히알루론산", "비타민", "펩타이드", "시카",
    "병풀", "AHA", "BHA", "PHA", "콜라겐", "retinol", "niacinamide", "ceramide",
    "hyaluronic", "peptide", "vitamin c",
]
CLAIM_KW = [
    "효과", "개선", "완화", "임상", "인증", "1위", "최초", "유일", "완판", "특허", "치료",
    "clinical", "proven", "first", "award", "best-selling",
]
EN_TO_KO = {
    "sunscreen": "선크림", "spf": "선크림", "serum": "세럼", "cleanser": "클렌저",
    "cleansing": "클렌징", "moisturizer": "보습크림", "toner": "토너", "routine": "루틴",
    "skincare": "스킨케어", "skin care": "스킨케어", "acne": "트러블", "pore": "모공",
    "dry skin": "건조 피부", "olive young": "올리브영", "k-beauty": "K뷰티",
    "korean beauty": "K뷰티", "launch": "신상", "new product": "신상",
    "exfoliant": "각질", "exfoliants": "각질", "exfoliator": "각질", "exfoliators": "각질",
    "exfoliation": "각질", "exfoliating": "각질", "peel": "필링", "peeling": "필링",
    "toner pad": "토너 패드", "toner pads": "토너 패드", "glass skin": "물광 피부",
    "korean skincare": "K스킨케어", "korean skin care": "K스킨케어", "smoothing": "피부결", "brightening": "톤 케어",
}


def hits(text, words):
    """text 안에 들어 있는 단어들을 찾아 돌려줍니다."""
    found = []
    for w in words:
        if w.isascii():
            if re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", text, re.I):
                found.append(w)
        elif w in text:
            found.append(w)
    return found


def clamp(n):
    return max(1, min(5, n))


# ----------------------------------------------------------------------
# 1) RSS 가져오기
# ----------------------------------------------------------------------
def read_rss_list():
    if not RSS_LIST.exists():
        raise SystemExit(f"[오류] RSS 목록 파일이 없어요: {RSS_LIST}\n"
                         "       sources 폴더에 rss_list.txt 를 만들어 주세요.")
    feeds = []
    for line in RSS_LIST.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "|" in line:
            name, url = [p.strip() for p in line.split("|", 1)]
        else:
            name, url = line, line
        feeds.append((name, url))
    if not feeds:
        raise SystemExit("[오류] rss_list.txt 안에 주소가 하나도 없어요.")
    return feeds


def explain_error(e):
    """오류를 쉬운 한국어로 바꿔 줍니다."""
    if isinstance(e, urllib.error.HTTPError):
        msg = {
            403: "사이트가 자동 접속을 막았어요 (403)",
            404: "이 주소에 RSS가 없어요. 주소가 바뀌었을 수 있어요 (404)",
            410: "이 주소는 더 이상 쓰지 않는대요 (410)",
            429: "너무 자주 접속해서 잠시 막혔어요. 나중에 다시 해 보세요 (429)",
        }
        return msg.get(e.code, f"사이트에서 오류를 보냈어요 (HTTP {e.code})")
    if isinstance(e, urllib.error.URLError):
        r = e.reason
        if isinstance(r, (socket.timeout, TimeoutError)) or "timed out" in str(r):
            return "사이트 응답이 너무 느려서 기다리다 멈췄어요 (시간 초과)"
        if isinstance(r, socket.gaierror):
            return "사이트 주소를 찾지 못했어요. 인터넷 연결이나 주소를 확인해 주세요"
        if isinstance(r, ssl.SSLError):
            return "보안 연결(SSL)에 실패했어요"
        return f"사이트에 접속하지 못했어요 ({r})"
    if isinstance(e, (socket.timeout, TimeoutError)):
        return "사이트 응답이 너무 느려서 기다리다 멈췄어요 (시간 초과)"
    if isinstance(e, ET.ParseError):
        return "받아 온 내용이 RSS 형식이 아니에요 (사이트가 바뀌었을 수 있어요)"
    return f"알 수 없는 문제가 생겼어요 ({type(e).__name__}: {e})"


def parse_xml(data):
    data = re.sub(rb"[\x00-\x08\x0b\x0c\x0e-\x1f]", b"", data)
    try:
        return ET.fromstring(data)
    except (ET.ParseError, LookupError, ValueError):
        # euc-kr 처럼 기본으로 못 읽는 글자 방식이면 직접 바꿔서 다시 읽기
        m = re.search(rb'encoding=["\']([\w-]+)', data[:300])
        enc = m.group(1).decode() if m else "utf-8"
        text = data.decode(enc, errors="replace").lstrip("﻿").lstrip()
        text = re.sub(r"^<\?xml[^>]*\?>", "", text)
        return ET.fromstring(text.encode("utf-8"))


def local(tag):
    return tag.rsplit("}", 1)[-1].lower()


def child(el, *names):
    for c in el:
        if local(c.tag) in names:
            return c
    return None


def child_text(el, *names):
    c = child(el, *names)
    return (c.text or "").strip() if c is not None else ""


def parse_date(s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        d = parsedate_to_datetime(s)
        return d if d.tzinfo else d.replace(tzinfo=KST)
    except (TypeError, ValueError, IndexError):
        pass
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=KST)  # 시간대가 없으면 한국 시간으로 봄
    except ValueError:
        pass
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=KST)
        except ValueError:
            pass
    return None


def clean_text(s):
    s = html.unescape(s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def short_summary(s, limit=140):
    s = clean_text(s)
    if not s:
        return "(요약 없음 - 원문 링크에서 확인)"
    parts = re.split(r"(?<=[.!?。])\s+", s)
    out = ""
    for p in parts[:2]:
        if len(out) + len(p) > limit and out:
            break
        out = (out + " " + p).strip()
    if len(out) > limit:
        out = out[:limit].rstrip() + "…"
    return out


def fetch_feed(name, url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    root = parse_xml(data)
    items = []
    for el in root.iter():
        if local(el.tag) not in ("item", "entry"):
            continue
        title = clean_text(child_text(el, "title"))
        link_el = child(el, "link")
        link = ""
        if link_el is not None:
            link = (link_el.text or "").strip() or link_el.get("href", "")
        if not link:
            link = child_text(el, "guid", "id")
        desc = (child_text(el, "description") or child_text(el, "summary")
                or child_text(el, "encoded") or child_text(el, "content"))
        pub = parse_date(child_text(el, "pubdate", "published", "date", "updated", "issued"))
        if title and link:
            items.append({"source": name, "title": title, "link": link.strip(),
                          "summary": short_summary(desc), "pub": pub})
    if not items:
        raise ValueError("글 목록을 찾지 못했어요 (RSS 형식이 다를 수 있어요)")
    return items


# ----------------------------------------------------------------------
# 2) 채점
# ----------------------------------------------------------------------
def score(item, now):
    text = f"{item['title']} {item['summary']}"
    t_hits = hits(text, TARGET_KW)
    ind = hits(text, INDUSTRY_KW)
    official = "식품의약품안전처" in item["source"] or "식약처" in item["source"]

    s1 = clamp(2 + min(3, len(t_hits)) - (2 if ind else 0))            # 타깃 관심도
    L = len(item["title"])
    s2 = 5 if L <= 30 else 4 if L <= 45 else 3 if L <= 60 else 2 if L <= 80 else 1
    if len(re.findall(r"[,·/…]", item["title"])) >= 2:
        s2 -= 1
    s2 = clamp(s2)                                                      # 한 장 요약
    s3 = clamp(2 + min(3, len(hits(text, VISUAL_KW))))                  # 이미지 표현
    s4 = 3 + (2 if official else 0) - min(2, len(hits(text, SPECULATIVE_KW)))
    if hits(text, ["공식", "발표", "출시", "launch", "announced"]):
        s4 += 1
    s4 = clamp(s4)                                                      # 사실 확인
    hrs = (now - item["pub"]).total_seconds() / 3600
    s5 = 5 if hrs <= 6 else 4 if hrs <= 12 else 3 if hrs <= 18 else 2
    if hits(text, FRESH_KW):
        s5 += 1
    s5 = clamp(s5)                                                      # 시의성

    item["scores"] = {"관심도": s1, "한장요약": s2, "이미지": s3, "사실확인": s4, "시의성": s5}
    item["total"] = s1 + s2 + s3 + s4 + s5
    item["hours"] = hrs
    item["t_hits"] = t_hits
    item["official"] = official


GENERIC_KW = {"피부", "신상", "신제품", "출시", "리뉴얼", "한정", "스킨케어", "launch", "new product"}


def tokens(title):
    return {w for w in re.findall(r"[가-힣A-Za-z0-9]{2,}", title.lower())}


def recent_pick_titles(today, days=7):
    """오늘을 뺀 최근 며칠 동안 picks 파일에 올랐던 소식 제목들"""
    titles = []
    t0 = datetime.strptime(today, "%Y-%m-%d")
    for k in range(1, days + 1):
        f = PICK_DIR / f"{(t0 - timedelta(days=k)).strftime('%Y-%m-%d')}.md"
        if f.exists():
            titles += re.findall(r"^## \d+위 · \d+/25점 · (.+)$", f.read_text(encoding="utf-8"), re.M)
    return titles


def same_story(a, b):
    """제목이 많이 겹치면 같은 소식으로 봅니다 (다른 사이트의 같은 기사)."""
    ta, tb = tokens(a["title"]), tokens(b["title"])
    if not ta or not tb:
        return False
    common = ta & tb
    return len(common) >= 3 or len(common) / min(len(ta), len(tb)) >= 0.5


def keyword_ko(item):
    ko = [w for w in item["t_hits"] if not w.isascii() and w not in GENERIC_KW]
    if ko:
        return ko[0]
    for w in item["t_hits"]:
        if w in EN_TO_KO and w not in GENERIC_KW:
            return EN_TO_KO[w]
    return "뷰티"


def reason_line(item):
    phrases = {
        "관심도": f"타깃이 궁금해할 주제({', '.join(item['t_hits'][:2]) or '뷰티'})",
        "한장요약": "핵심이 하나라 한 장에 정리하기 쉬움",
        "이미지": "제품·사용법을 그림으로 보여 주기 쉬움",
        "사실확인": "공식 자료로 확인하기 쉬움" if item["official"] else "확인할 원문이 분명함",
        "시의성": f"{max(1, round(item['hours']))}시간 전에 올라온 따끈한 소식",
    }
    best = sorted(item["scores"].items(), key=lambda kv: -kv[1])[:2]
    return " + ".join(phrases[k] for k, _ in best)


def draft_title(item):
    kw = keyword_ko(item)
    text = f"{item['title']} {item['summary']}"
    if item["official"]:
        return f"식약처가 알려 준 {kw} 체크포인트"
    if hits(text, ["사용법", "방법", "루틴", "how to", "routine", "tips"]):
        return f"{kw}, 이렇게 쓰면 쉬워요"
    if hits(text, FRESH_KW):
        return f"{kw} 신상, 레시피로 풀어볼게요"
    return f"이번 주 {kw} 소식 한 입 정리"


def fact_checks(item):
    text = f"{item['title']} {item['summary']}"
    notes = []
    nums = re.findall(r"\$\s?\d[\d,.]*|\d[\d,.]*\s?(?:%|원|달러|ml|mL|g|개|종|배|위|명|억|만)", text)
    if nums:
        notes.append("숫자: " + ", ".join(dict.fromkeys(n.strip() for n in nums[:5])))
    ing = hits(text, INGREDIENT_KW)
    if ing:
        notes.append("성분: " + ", ".join(ing[:4]))
    claims = hits(text, CLAIM_KW)
    if claims:
        notes.append("효능·순위 표현: " + ", ".join(claims[:4])
                     + " (약처럼 보이는 표현은 쓰지 않기)")
    notes.append("제품명·브랜드명·가격·출시일은 원문 링크에서 다시 확인")
    return " / ".join(notes)


# ----------------------------------------------------------------------
# 3) used.txt
# ----------------------------------------------------------------------
def load_used():
    used = {}
    if USED_FILE.exists():
        for line in USED_FILE.read_text(encoding="utf-8-sig").splitlines():
            if "\t" in line:
                d, link = line.split("\t", 1)
                used[link.strip()] = d.strip()
            elif line.strip():
                used[line.strip()] = ""
    return used


def save_used(used, today, new_links):
    # 오늘 다시 실행하면 오늘 기록은 새로 고칩니다
    kept = {l: d for l, d in used.items() if d != today}
    for l in new_links:
        kept[l] = today
    lines = [f"{d}\t{l}" for l, d in sorted(kept.items(), key=lambda kv: (kv[1], kv[0]))]
    USED_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ----------------------------------------------------------------------
# 실행
# ----------------------------------------------------------------------
def fmt_time(d):
    return d.astimezone(KST).strftime("%Y-%m-%d %H:%M")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    now = datetime.now(KST)
    today = now.strftime("%Y-%m-%d")
    since = now - timedelta(hours=HOURS)
    feeds = read_rss_list()
    print(f"RSS {len(feeds)}곳에서 최근 {HOURS}시간 소식을 가져오는 중이에요...\n")

    results, failures = [], []

    def job(f):
        name, url = f
        try:
            return name, url, fetch_feed(name, url), None
        except Exception as e:  # 하나가 실패해도 계속 진행
            return name, url, None, explain_error(e)

    with ThreadPoolExecutor(max_workers=6) as ex:
        for name, url, items, err in ex.map(job, feeds):
            if err:
                failures.append((name, url, err))
                print(f"  ✗ {name}: {err}")
            else:
                results.extend(items)
                print(f"  ✓ {name}: 글 {len(items)}개 확인")

    used = load_used()
    seen, cands = set(), []
    no_date = skipped_used = 0
    for it in results:
        if it["pub"] is None:
            no_date += 1
            continue
        if not (since <= it["pub"] <= now + timedelta(hours=1)):
            continue
        if it["link"] in used and used[it["link"]] != today:
            skipped_used += 1
            continue
        key = it["link"]
        if key in seen:
            continue
        seen.add(key)
        cands.append(it)
    cands.sort(key=lambda x: x["pub"], reverse=True)

    CAND_DIR.mkdir(exist_ok=True)
    PICK_DIR.mkdir(exist_ok=True)

    # ---- candidates/날짜.md
    ok = len(feeds) - len(failures)
    lines = [
        f"# {today} 후보 소식 (최근 {HOURS}시간)", "",
        f"- 만든 시각: {fmt_time(now)} (한국 시간)",
        f"- 가져온 사이트: {ok}/{len(feeds)}곳 성공",
        f"- 후보: {len(cands)}개 (이미 사용한 링크 {skipped_used}개 제외"
        + (f", 발행 시간이 없는 글 {no_date}개 제외" if no_date else "") + ")", "",
        "> 요약은 원문 앞부분을 자동으로 잘라 온 것이에요. 카드에는 그대로 쓰지 말고"
        " 내 말로 다시 써 주세요 (CLAUDE.md 규칙).", "",
    ]
    for i, it in enumerate(cands, 1):
        lines += [f"## {i}. {it['title']}", "",
                  f"- 출처: {it['source']}",
                  f"- 발행: {fmt_time(it['pub'])}",
                  f"- 요약: {it['summary']}",
                  f"- 링크: {it['link']}", ""]
    if not cands:
        lines += ["오늘은 조건에 맞는 새 글이 없어요.", ""]
    lines += ["---", "", "## 실패한 주소", ""]
    lines += [f"- {n} | {u} — {e}" for n, u, e in failures] or ["- 없음 (모두 성공)"]
    cand_path = CAND_DIR / f"{today}.md"
    cand_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ---- picks/날짜.md
    for it in cands:
        score(it, now)
    recent = recent_pick_titles(today)
    top, skipped_recent = [], []
    for it in sorted(cands, key=lambda x: (-x["total"], -x["pub"].timestamp())):
        if not it["t_hits"]:
            continue  # 뷰티와 관련된 단어가 하나도 없으면 추천하지 않기
        if any(same_story(it, {"title": r}) for r in recent):
            skipped_recent.append(it["title"])
            continue  # 최근 7일 안에 이미 추천한 소식과 같은 내용이면 건너뛰기 (다른 사이트 기사여도)
        if any(same_story(it, t) for t in top):
            continue  # 같은 소식이 이미 뽑혔으면 건너뛰기
        top.append(it)
        if len(top) == TOP_N:
            break
    pl = [f"# {today} 추천 TOP {TOP_N}", "",
          "> 키워드로 매긴 **1차 점수**예요. 최종 선택은 직접 해 주세요.",
          "> 기준: 관심도 · 한장요약 · 이미지 · 사실확인 · 시의성 (각 5점, 만점 25점)", ""]
    if skipped_recent:
        pl += ["> 최근 7일 안에 추천했던 소식과 같은 내용이라 뺀 글: "
               + " / ".join(dict.fromkeys(skipped_recent)), ""]
    for i, it in enumerate(top, 1):
        sc = " · ".join(f"{k} {v}" for k, v in it["scores"].items())
        pl += [f"## {i}위 · {it['total']}/25점 · {it['title']}", "",
               f"- 출처: {it['source']} / 발행: {fmt_time(it['pub'])}",
               f"- 링크: {it['link']}",
               f"- 점수: {sc}",
               f"- 선정 이유: {reason_line(it)}",
               f"- 예상 카드 제목(가제): {draft_title(it)}",
               f"- 사실 확인 필요: {fact_checks(it)}", ""]
    if not top:
        pl += ["오늘은 추천할 후보가 없어요.", ""]
    pick_path = PICK_DIR / f"{today}.md"
    pick_path.write_text("\n".join(pl) + "\n", encoding="utf-8")

    save_used(used, today, [it["link"] for it in top])

    # ---- 화면 출력
    print("\n" + "=" * 50)
    print(f"  오늘의 추천 {len(top)}개")
    print("=" * 50)
    for i, it in enumerate(top, 1):
        print(f"{i}. [{it['total']}점] {it['title']}")
        print(f"   가제: {draft_title(it)}  ({it['source']})")
    if not top:
        print("  오늘은 추천할 후보가 없어요.")
    if skipped_recent:
        print(f"\n※ 최근에 추천했던 소식과 겹치는 글 {len(set(skipped_recent))}개는 뺐어요.")
    print("\n저장한 파일")
    print(f"  후보: {cand_path.relative_to(ROOT)}  ({len(cands)}개)")
    print(f"  추천: {pick_path.relative_to(ROOT)}")
    if failures:
        print(f"\n※ {len(failures)}곳은 가져오지 못했어요. 이유는 후보 파일 맨 아래에 적어 뒀어요.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if e.code not in (None, 0):
            print(e.code if isinstance(e.code, str) else "[오류] 프로그램이 멈췄어요.")
            sys.exit(1)
    except PermissionError as e:
        print(f"[오류] 파일을 저장하지 못했어요. 파일이 다른 프로그램에서 열려 있는지 확인해 주세요.\n       ({e.filename})")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n중간에 멈췄어요.")
        sys.exit(1)
    except Exception as e:
        print(f"[오류] 예상하지 못한 문제가 생겼어요: {type(e).__name__}: {e}")
        print("       이 메시지를 Claude에게 그대로 보여 주시면 고쳐 드릴게요.")
        sys.exit(1)
