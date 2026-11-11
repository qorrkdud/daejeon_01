# -*- coding: utf-8 -*-
"""
카드 이미지들로 인스타 릴스용 세로 영상(1080x1920 mp4)을 만듭니다. 음악 없음.

사용법:
  py templates/make_reel.py <카드 폴더> [저장할 mp4 경로]

  - 카드 폴더 안의 01.png, 02.png ... (없으면 card_01.png ...) 를 순서대로 씁니다.
  - 카드 한 장당 3초, 다음 카드로 0.5초 동안 부드럽게 겹쳐 바뀝니다(크로스페이드).
  - 카드 위아래 빈 곳은 같은 카드를 흐리게 깔아 채웁니다.
  - 릴스 화면 아래쪽(캡션·버튼)에 가리지 않게 카드를 85% 크기로 조금 위에 둡니다.
필요한 도구: Pillow, imageio-ffmpeg  (py -m pip install pillow imageio-ffmpeg)
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter
    import imageio_ffmpeg
except ImportError as e:
    print(f"[오류] 영상 도구가 없어요 ({e.name}). py -m pip install pillow imageio-ffmpeg 로 설치해 주세요.")
    sys.exit(1)

W, H = 1080, 1920
SHOW, FADE, FPS = 3.0, 0.5, 30
CARD_SCALE, CARD_TOP = 0.85, 300
CREAM = (255, 248, 239)


def find_cards(folder):
    nums = sorted((p for p in folder.glob("*.png") if re.fullmatch(r"\d+", p.stem)), key=lambda p: int(p.stem))
    return nums or sorted(folder.glob("card_*.png"))


def frame(card_path):
    card = Image.open(card_path).convert("RGB")
    # 배경: 같은 카드를 화면에 꽉 채우고 흐리게 + 크림색을 살짝 섞어 차분하게
    s = max(W / card.width, H / card.height)
    bg = card.resize((round(card.width * s), round(card.height * s)), Image.LANCZOS)
    l, t = (bg.width - W) // 2, (bg.height - H) // 2
    bg = bg.crop((l, t, l + W, t + H)).filter(ImageFilter.GaussianBlur(40))
    bg = Image.blend(bg, Image.new("RGB", (W, H), CREAM), 0.25)
    # 카드: 85% 크기, 둥근 모서리 + 그림자
    cw, ch = round(card.width * CARD_SCALE), round(card.height * CARD_SCALE)
    card = card.resize((cw, ch), Image.LANCZOS)
    x, y = (W - cw) // 2, CARD_TOP
    shadow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(shadow).rounded_rectangle([x + 10, y + 18, x + cw + 10, y + ch + 18], radius=36, fill=110)
    shadow = shadow.filter(ImageFilter.GaussianBlur(22))
    bg.paste(Image.new("RGB", (W, H), (40, 28, 24)), (0, 0), shadow)
    mask = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, cw - 1, ch - 1], radius=36, fill=255)
    bg.paste(card, (x, y), mask)
    return bg


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    folder = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else folder / "reel.mp4"
    cards = find_cards(folder)
    if len(cards) < 2:
        print(f"[오류] {folder} 에서 카드 이미지를 2장 이상 찾지 못했어요 (01.png, 02.png ... 또는 card_01.png ...).")
        sys.exit(1)

    tmp = Path(tempfile.mkdtemp(prefix="reel_"))
    try:
        print(f"카드 {len(cards)}장으로 세로 영상을 만들어요...")
        frames = []
        for k, c in enumerate(cards, 1):
            f = tmp / f"f{k:02d}.png"
            frame(c).save(f)
            frames.append(f)
        # ffmpeg: 각 카드를 (3초 + 전환 0.5초) 길이로 만들고 xfade 로 이어 붙이기
        clip = SHOW + FADE
        cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error"]
        for f in frames:
            cmd += ["-loop", "1", "-framerate", str(FPS), "-t", f"{clip}", "-i", str(f)]
        chain, last = [], "[0:v]"
        for k in range(1, len(frames)):
            label = f"[v{k}]"
            chain.append(f"{last}[{k}:v]xfade=transition=fade:duration={FADE}:offset={k * SHOW}{label}")
            last = label
        chain.append(f"{last}format=yuv420p[out]")
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp_out = tmp / "reel.mp4"
        cmd += ["-filter_complex", ";".join(chain), "-map", "[out]", "-an", "-r", str(FPS),
                "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-movflags", "+faststart", str(tmp_out)]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0 or not tmp_out.exists():
            print("[오류] 영상을 만들지 못했어요. 아래 내용을 Claude에게 보여 주세요.")
            print(r.stderr[-1500:])
            sys.exit(1)
        shutil.copyfile(tmp_out, out)
        total = len(frames) * SHOW + FADE
        print(f"영상을 만들었어요: {out}")
        print(f"  {len(frames)}장 × {SHOW:g}초, 전환 {FADE:g}초 → 약 {total:g}초, {W}x{H}, 음악 없음, "
              f"{out.stat().st_size / 1024 / 1024:.1f}MB")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
