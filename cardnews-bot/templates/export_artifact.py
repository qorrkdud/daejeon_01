# -*- coding: utf-8 -*-
"""
HTML 카드뉴스(아티팩트)를 인스타용 PNG(1080 x 1350)로 한 장씩 저장합니다.
이 PC에 있는 Microsoft Edge 를 화면 없이 실행해서 찍습니다. (따로 설치할 것 없음)

사용법:
  py templates/export_artifact.py <index.html 이 있는 폴더> <저장할 폴더> [묶음 크기]

  - 카드는 HTML 안의 class="holder" 순서대로 01.png, 02.png ... 로 저장됩니다.
  - 묶음 크기(예: 7)를 주면 7장씩 vol1, vol2 ... 하위 폴더로 나눠 저장합니다.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

EDGE = [Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")]
W, H = 1080, 1350

INJECT = """
<style>
html,body{margin:0!important;padding:0!important;background:#fff!important;overflow:hidden!important}
:root{padding:0!important}
body.one .wrap{display:block!important;padding:0!important;gap:0!important}
body.one .set-title{display:none!important}
body.one .holder{display:none!important;width:%dpx!important;height:%dpx!important;margin:0!important}
body.one .holder.on{display:block!important}
body.one .holder .card{transform:none!important}
</style>
<script>
(function(){
  var m = location.search.match(/card=(\\d+)/); if(!m) return;
  document.body.classList.add('one');
  var h = document.querySelectorAll('.holder')[+m[1]-1]; if(h) h.classList.add('on');
})();
</script>
""" % (W, H)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    group = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    page = src / "index.html"
    if not page.exists():
        print(f"[오류] {page} 가 없어요.")
        sys.exit(1)
    edge = next((p for p in EDGE if p.exists()), None)
    if not edge:
        print("[오류] Microsoft Edge 를 찾지 못했어요.")
        sys.exit(1)

    html = page.read_text(encoding="utf-8")
    n = html.count('class="holder"')
    if n == 0:
        print('[오류] HTML 안에서 카드(class="holder")를 찾지 못했어요.')
        sys.exit(1)
    render = src / "_render.html"
    render.write_text(html.replace("</body>", INJECT + "</body>") if "</body>" in html else html + INJECT,
                      encoding="utf-8")

    tmp = Path(tempfile.mkdtemp(prefix="cardshot_"))
    profile = tmp / "edge-profile"
    saved = []
    for i in range(1, n + 1):
        shot = tmp / f"{i:02d}.png"
        url = render.resolve().as_uri() + f"?card={i}"
        cmd = [str(edge), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
               f"--user-data-dir={profile}", "--force-device-scale-factor=1",
               f"--window-size={W},{H}", "--virtual-time-budget=15000",
               f"--screenshot={shot}", url]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        if not shot.exists():
            print(f"  ✗ {i}번 카드를 찍지 못했어요.")
            continue
        if group:
            dest = out / f"vol{(i - 1) // group + 1}" / f"{(i - 1) % group + 1:02d}.png"
        else:
            dest = out / f"{i:02d}.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(shot, dest)
        saved.append(dest)
        print(f"  ✓ {i}/{n} → {dest}")
    shutil.rmtree(tmp, ignore_errors=True)
    render.unlink(missing_ok=True)
    print(f"\n{len(saved)}/{n}장을 저장했어요: {out}")
    if len(saved) < n:
        sys.exit(1)


if __name__ == "__main__":
    main()
