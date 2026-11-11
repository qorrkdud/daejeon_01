# -*- coding: utf-8 -*-
"""
'실제로 따라 하는' 사용법 릴스(1080x1920 mp4)를 만듭니다. 음악 없음.

장면 대본(reel_script.json)에 적힌 순서대로
  - 사람 사진을 크게 보여 주면서 천천히 확대(줌인)하고
  - 위쪽에 단계 라벨과 큰 자막, 사진 아래에 짧은 설명을 띄우고
  - 장면 사이를 부드럽게 겹쳐 넘깁니다(크로스페이드).

사용법:
  py templates/make_usage_reel.py <reel_script.json> [저장할 mp4]
필요한 도구: Pillow, imageio-ffmpeg
"""
import json
import math
import random
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    import imageio_ffmpeg
except ImportError as e:
    print(f"[오류] 영상 도구가 없어요 ({e.name}). py -m pip install pillow imageio-ffmpeg 로 설치해 주세요.")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
W, H, FPS = 1080, 1920, 30
ZOOM = 0.10                       # 장면 동안 10% 확대
INTRO = 0.35                      # 자막이 떠오르는 시간(초)
ACCOUNT = "@weekly.beauty.recipe"
INK, SOFT, MAIN = (59, 42, 36), (138, 118, 108), (201, 115, 90)
CREAM, PAPER, PEACH, BUTTER = (255, 248, 239), (255, 253, 249), (248, 211, 192), (255, 235, 176)
FONT_DIR = Path("C:/Windows/Fonts")


def font(name, size):
    return ImageFont.truetype(str(FONT_DIR / name), size)


def fit_font(draw, lines, name, size, max_w, min_size=56):
    while size > min_size:
        f = font(name, size)
        if all(draw.textlength(l, font=f) <= max_w for l in lines):
            return f, size
        size -= 4
    return font(name, min_size), min_size


def crop_to(img, ar, cy_ratio=0.45):
    """그림을 ar(가로/세로) 비율로 가운데(세로는 살짝 위) 기준으로 자르기"""
    pw, ph = img.size
    if pw / ph > ar:
        cw, ch = round(ph * ar), ph
    else:
        cw, ch = pw, round(pw / ar)
    l = min(max(0, pw / 2 - cw / 2), pw - cw)
    t = min(max(0, ph * cy_ratio - ch / 2), ph - ch)
    return img.crop((round(l), round(t), round(l) + cw, round(t) + ch))


class Scene:
    def __init__(self, sc, photo_dir, dur, video_dir=None):
        self.sc, self.dur = sc, dur
        path = photo_dir / sc["photo"]
        if not path.exists():
            raise FileNotFoundError(f"사진이 없어요: {path}")
        self.photo = Image.open(path).convert("RGB")
        portrait = self.photo.height > self.photo.width
        # AI 영상 클립이 있으면 사진 대신 클립을 씁니다
        self.video, self.frames, self.vfps = None, None, 30
        vp = (video_dir / sc["video"]) if (video_dir and sc.get("video")) else None
        if vp and vp.exists():
            gen = imageio_ffmpeg.read_frames(str(vp))
            meta = next(gen)
            gen.close()
            vw, vh = meta["size"]
            self.video, self.vfps = vp, float(meta.get("fps") or 30)
            portrait = vh > vw
        self.fw, self.fh = (640, 800) if portrait else (960, 640)
        self.fx, self.fy = (W - self.fw) // 2, 640
        # 사진을 액자 비율로 미리 잘라 두기 (얼굴이 위쪽에 있어 살짝 위를 기준으로)
        pw, ph = self.photo.size
        ar = self.fw / self.fh
        if pw / ph > ar:
            cw, ch = round(ph * ar), ph
        else:
            cw, ch = pw, round(pw / ar)
        cx, cy = pw / 2, ph * 0.45
        l = min(max(0, cx - cw / 2), pw - cw)
        t = min(max(0, cy - ch / 2), ph - ch)
        self.src = self.photo.crop((round(l), round(t), round(l) + cw, round(t) + ch))
        self.mask = Image.new("L", (self.fw, self.fh), 0)
        ImageDraw.Draw(self.mask).rounded_rectangle([0, 0, self.fw - 1, self.fh - 1], radius=40, fill=255)
        self.bg = self._background()
        self.ov_top, self.ov_bottom = self._overlays()
        # 효과 알갱이 미리 정하기 (장면마다 늘 같은 모양이 나오게 고정된 난수)
        rng = random.Random(sc["photo"])
        fx = sc.get("fx")
        n = {"bubbles": 16, "drops": 22, "sparkle": 10}.get(fx, 0)
        self.particles = []
        for _ in range(n):
            if fx == "bubbles":
                self.particles.append({"x": rng.uniform(20, self.fw - 20), "y": rng.uniform(0, self.fh + 60),
                                       "r": rng.uniform(10, 34), "v": rng.uniform(60, 140),
                                       "amp": rng.uniform(8, 24), "f": rng.uniform(0.4, 1.1),
                                       "ph": rng.uniform(0, 6.28)})
            elif fx == "drops":
                self.particles.append({"x": rng.uniform(10, self.fw - 10), "y": rng.uniform(0, self.fh),
                                       "len": rng.uniform(18, 42), "v": rng.uniform(600, 950)})
            else:
                self.particles.append({"x": rng.uniform(30, self.fw - 30), "y": rng.uniform(30, self.fh - 30),
                                       "r": rng.uniform(14, 30), "f": rng.uniform(0.6, 1.4),
                                       "ph": rng.uniform(0, 6.28)})

    def _background(self):
        s = max(W / self.photo.width, H / self.photo.height)
        bg = self.photo.resize((round(self.photo.width * s) + 2, round(self.photo.height * s) + 2), Image.BILINEAR)
        l, t = (bg.width - W) // 2, (bg.height - H) // 2
        bg = bg.crop((l, t, l + W, t + H)).filter(ImageFilter.GaussianBlur(45))
        bg = Image.blend(bg, Image.new("RGB", (W, H), CREAM), 0.45)
        sh = Image.new("L", (W, H), 0)
        ImageDraw.Draw(sh).rounded_rectangle([self.fx + 12, self.fy + 22, self.fx + self.fw + 12, self.fy + self.fh + 22],
                                             radius=40, fill=120)
        bg.paste(Image.new("RGB", (W, H), (40, 28, 24)), (0, 0), sh.filter(ImageFilter.GaussianBlur(24)))
        d = ImageDraw.Draw(bg)
        d.rounded_rectangle([self.fx - 6, self.fy - 6, self.fx + self.fw + 6, self.fy + self.fh + 6], radius=46, fill=INK)
        return bg

    def _overlays(self):
        sc = self.sc
        # 위쪽: 라벨 + 큰 자막 (크림색 판 위)
        top = Image.new("RGBA", (W, 470), (0, 0, 0, 0))
        d = ImageDraw.Draw(top)
        lines = sc["head"].split("\n")
        hf, hs = fit_font(d, lines, "malgunbd.ttf", 84, W - 220)
        lh = round(hs * 1.22)
        panel_h = 60 + 64 + 26 + lh * len(lines) + 44
        d.rounded_rectangle([60, 10, W - 60, 10 + panel_h], radius=36, fill=PAPER + (238,), outline=INK + (255,), width=4)
        lf = font("malgunbd.ttf", 32)
        lw = d.textlength(sc["label"], font=lf)
        pill = INK if sc.get("bad") else MAIN
        d.rounded_rectangle([110, 50, 110 + lw + 56, 50 + 64], radius=32, fill=pill + (255,))
        d.text((110 + 28, 50 + 32), sc["label"], font=lf, fill=(255, 255, 255, 255), anchor="lm")
        y = 50 + 64 + 26
        for k, line in enumerate(lines):
            if k == len(lines) - 1 and not sc.get("bad"):   # 마지막 줄 형광펜
                tw = d.textlength(line, font=hf)
                d.rectangle([108, y + lh * 0.55, 112 + tw, y + lh * 0.88], fill=PEACH + (255,))
            d.text((110, y), line, font=hf, fill=INK + (255,))
            y += lh
        # 아래: 설명 + 출처 (사진 아래)
        bot = Image.new("RGBA", (W, 260), (0, 0, 0, 0))
        d = ImageDraw.Draw(bot)
        sf = font("malgunbd.ttf", 40)
        sub = sc.get("sub", "")
        if sub:
            sw = d.textlength(sub, font=sf)
            if sw > W - 160:
                sf = font("malgunbd.ttf", 34)
                sw = d.textlength(sub, font=sf)
            d.rounded_rectangle([(W - sw) / 2 - 36, 20, (W + sw) / 2 + 36, 20 + 84], radius=42,
                                fill=(BUTTER if sc.get("end") else PAPER) + (245,), outline=INK + (255,), width=3)
            d.text((W / 2, 20 + 42), sub, font=sf, fill=INK + (255,), anchor="mm")
        if sc.get("src"):
            d.text((W / 2, 140), sc["src"], font=font("malgun.ttf", 26), fill=SOFT + (255,), anchor="mm")
        return top, bot

    def camera(self, t):
        """장면마다 다른 카메라 움직임: in(다가가기) out(물러나기) left/right(옆으로) up(위로)"""
        p = min(1.0, max(0.0, t / self.dur))
        p = 0.5 - 0.5 * math.cos(math.pi * p)          # 부드럽게 시작하고 부드럽게 멈추기
        move = self.sc.get("move", "in")
        sw, sh = self.src.size
        if move == "out":
            z, ax, ay = 1 + ZOOM * 1.2 * (1 - p), 0.5, 0.45
        elif move in ("left", "right"):
            z, ay = 1.14, 0.45
            ax = 0.8 - 0.6 * p if move == "left" else 0.2 + 0.6 * p
        elif move == "up":
            z, ax, ay = 1.14, 0.5, 0.85 - 0.7 * p
        else:
            z, ax, ay = 1 + ZOOM * p, 0.5, 0.45
        cw, ch = sw / z, sh / z
        l, tp = (sw - cw) * ax, (sh - ch) * ay
        return (l, tp, l + cw, tp + ch)

    def effects(self, t):
        """사진 위 움직이는 효과 (bubbles 거품 / drops 물방울 / sparkle 반짝임)"""
        fx = self.sc.get("fx")
        if not fx:
            return None
        layer = Image.new("RGBA", (self.fw, self.fh), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        for pt in self.particles:
            if fx == "bubbles":
                span = self.fh + 2 * pt["r"]
                y = (pt["y"] - pt["v"] * t) % span - pt["r"]
                x = pt["x"] + pt["amp"] * math.sin(2 * math.pi * pt["f"] * t + pt["ph"])
                r = pt["r"]
                d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 50), outline=(255, 255, 255, 190), width=3)
                d.ellipse([x - r * 0.55, y - r * 0.6, x - r * 0.15, y - r * 0.2], fill=(255, 255, 255, 210))
            elif fx == "drops":
                span = self.fh + pt["len"] + 20
                y = (pt["y"] + pt["v"] * t) % span - pt["len"]
                x = pt["x"]
                d.line([x, y, x, y + pt["len"]], fill=(235, 246, 255, 150), width=4)
                d.ellipse([x - 5, y + pt["len"] - 5, x + 5, y + pt["len"] + 5], fill=(255, 255, 255, 200))
            elif fx == "sparkle":
                a = (math.sin(2 * math.pi * pt["f"] * t + pt["ph"]) + 1) / 2
                if a < 0.15:
                    continue
                x, y, s = pt["x"], pt["y"], pt["r"] * (0.6 + 0.4 * a)
                pts = [(x, y - s), (x + s * .25, y - s * .25), (x + s, y), (x + s * .25, y + s * .25),
                       (x, y + s), (x - s * .25, y + s * .25), (x - s, y), (x - s * .25, y - s * .25)]
                d.polygon(pts, fill=BUTTER + (round(240 * a),))
        return layer

    def load(self):
        """클립을 장면 길이만큼만 읽어 액자 크기로 맞춰 둡니다 (메모리 절약)"""
        if not self.video or self.frames is not None:
            return
        gen = imageio_ffmpeg.read_frames(str(self.video))
        meta = next(gen)
        size = tuple(meta["size"])
        need = math.ceil((self.dur + 1.0) * self.vfps)
        self.frames = []
        for k, raw in enumerate(gen):
            if k >= need:
                break
            img = Image.frombytes("RGB", size, raw)
            self.frames.append(crop_to(img, self.fw / self.fh).resize((self.fw, self.fh), Image.BILINEAR))
        gen.close()
        if not self.frames:
            raise ValueError(f"영상 클립을 읽지 못했어요: {self.video}")

    def release(self):
        self.frames = None

    def render(self, t, index, total_scenes):
        frame = self.bg.copy()
        if self.video:
            self.load()
            ph = self.frames[min(len(self.frames) - 1, int(t * self.vfps))]   # 클립이 짧으면 마지막 장면 유지
        else:
            ph = self.src.resize((self.fw, self.fh), Image.BILINEAR, box=self.camera(t))
        fx = self.effects(t)
        if fx is not None:
            ph = ph.convert("RGBA")
            ph.alpha_composite(fx)
            ph = ph.convert("RGB")
        frame.paste(ph, (self.fx, self.fy), self.mask)
        d = ImageDraw.Draw(frame)
        if self.sc.get("timer"):   # 1분 타이머 배지 (원이 채워지는 모양)
            cx, cy, r = self.fx + self.fw - 90, self.fy + 90, 70
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=PAPER, outline=INK, width=5)
            d.pieslice([cx - r + 12, cy - r + 12, cx + r - 12, cy + r - 12], -90, -90 + 360 * min(1, t / self.dur),
                       fill=PEACH)
            d.text((cx, cy), "1:00", font=font("consolab.ttf", 40), fill=INK, anchor="mm")
        # 자막: 처음 0.35초 동안 아래에서 떠오르며 나타남
        a = min(1.0, t / INTRO)
        dy = round((1 - a) * 36)
        for ov, y0 in ((self.ov_top, 150), (self.ov_bottom, self.fy + self.fh + 24)):
            if a >= 1:
                frame.paste(ov, (0, y0), ov)
            else:
                alpha = ov.getchannel("A").point(lambda v: round(v * a))
                frame.paste(ov, (0, y0 + dy), alpha)
        # 맨 위: 진행 막대 + 계정명
        seg = (W - 120 - (total_scenes - 1) * 8) / total_scenes
        for k in range(total_scenes):
            x0 = 60 + k * (seg + 8)
            d.rounded_rectangle([x0, 60, x0 + seg, 68], radius=4, fill=(255, 255, 255))
            fill = 1 if k < index else (min(1, t / self.dur) if k == index else 0)
            if fill > 0:
                d.rounded_rectangle([x0, 60, x0 + seg * fill, 68], radius=4, fill=INK)
        d.text((60, 100), ACCOUNT, font=font("consolab.ttf", 28), fill=INK)
        return frame


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    script_path = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else script_path.parent / "reel_사용법.mp4"
    try:
        script = json.loads(script_path.read_text(encoding="utf-8-sig"))
        photo_dir = ROOT / script.get("photo_dir", "assets")
        vd = script.get("video_dir")
        video_dir = (Path(vd) if Path(vd).is_absolute() else ROOT / vd) if vd else None
        base, fade = float(script.get("seconds", 3)), float(script.get("fade", 0.4))
        scenes = [Scene(sc, photo_dir, float(sc.get("seconds", base)), video_dir) for sc in script["scenes"]]
        n_video = sum(1 for s in scenes if s.video)
        print(f"AI 영상 클립 {n_video}개 사용, 나머지 {len(scenes) - n_video}개 장면은 사진 + 움직임 효과")
    except (OSError, json.JSONDecodeError, KeyError, StopIteration, ValueError) as e:
        print(f"[오류] 장면 대본이나 사진을 읽지 못했어요: {e}")
        sys.exit(1)

    starts, s = [], 0.0
    for sc in scenes:
        starts.append(s)
        s += sc.dur
    total = s + fade
    n_frames = round(total * FPS)
    tmp_out = out.with_suffix(".tmp.mp4")
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium",
           "-crf", "19", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(tmp_out)]
    print(f"장면 {len(scenes)}개, 약 {total:.1f}초 영상을 만들어요... (1~2분 걸려요)")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for f in range(n_frames):
            T = f / FPS
            i = max(k for k in range(len(scenes)) if starts[k] <= T)
            for k in range(max(0, i - 1)):          # 지나간 장면의 클립은 메모리에서 비우기
                scenes[k].release()
            img = scenes[i].render(T - starts[i], i, len(scenes))
            if i > 0 and T - starts[i] < fade:   # 앞 장면과 부드럽게 겹치기
                prev = scenes[i - 1].render(T - starts[i - 1], i - 1, len(scenes))
                img = Image.blend(prev, img, (T - starts[i]) / fade)
            proc.stdin.write(img.tobytes())
        proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", "replace")
        proc.wait()
    except BrokenPipeError:
        proc.wait()
        err = proc.stderr.read().decode("utf-8", "replace")
    if proc.returncode != 0 or not tmp_out.exists():
        print("[오류] 영상을 만들지 못했어요. 아래 내용을 Claude에게 보여 주세요.\n" + err[-1500:])
        sys.exit(1)
    tmp_out.replace(out)
    print(f"영상을 만들었어요: {out}  ({total:.1f}초, {W}x{H}, 음악 없음, {out.stat().st_size / 1024 / 1024:.1f}MB)")


if __name__ == "__main__":
    main()
