"""Original text-only reels in the account's style (no music, no faces, no others' clips).

Timeline (default 10 s @30fps, 1080x1920):
  0.0s  title + hook line already visible (strongest line on screen in the first 2 s)
  ~0.8s remaining lines fade in one by one
  hold
  last ~1.2s the extra lines fade out again -> the final frame equals the first frame,
         so the reel loops seamlessly.
Audio: "silence" or "ambience" (soft brown-noise 'rain/wind', synthesised locally with
ffmpeg -> no licence issues), faded so the loop point is inaudible.
Recitation is supported only from a file you have reuse permission for (audio=<path>).
"""
import html
import shutil
import subprocess
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

from render import STYLE, _font_data_uri

ROOT = Path(__file__).resolve().parents[1]
FPS = 30

PAGE = """<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><style>
@font-face {{ font-family:'Main'; src:url('{font}'); font-weight:100 900; }}
html,body {{ margin:0; width:1080px; height:1920px; background:{bg}; overflow:hidden; }}
body {{ font-family:'Main',serif; color:{fg}; text-align:center; }}
.top {{ position:absolute; left:0; right:0; top:330px; display:flex; flex-direction:column; align-items:center; }}
.title {{ font-size:50px; color:{muted}; }}
.rule {{ width:84px; height:1.5px; background:{muted}; opacity:.6; margin-top:22px; }}
.mid {{ position:absolute; left:80px; right:80px; top:480px; bottom:470px; display:flex; flex-direction:column;
        align-items:center; justify-content:center; gap:10px; overflow:hidden; }}
.ln {{ font-size:{px}px; line-height:1.75; font-weight:{weight}; text-wrap:balance; white-space:pre-line; }}
.ln.hook {{ font-weight:{hook_weight}; }}
.sub {{ font-size:40px; line-height:1.8; color:{fg}; opacity:.92; margin-top:26px; font-weight:400; }}
.bottom {{ position:absolute; left:0; right:0; bottom:330px; font-size:30px; color:{muted}; line-height:1.6; }}
</style></head><body>
<div class="top">{title_html}</div>
<div class="mid">{lines_html}</div>
<div class="bottom" id="b">{bottom}</div>
</body></html>"""


def _ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def make_reel(out: Path, lines, title=None, sub=None, bottom=None, duration=10.0,
              audio="silence", weight=500, px=64):
    """lines[0] is the hook (visible from frame 0). sub = optional smaller line (e.g. tafsir)."""
    esc = html.escape
    blocks = [f'<div class="ln{" hook" if i == 0 else ""}" id="l{i}">{esc(t)}</div>' for i, t in enumerate(lines)]
    if sub:
        blocks.append(f'<div class="sub" id="l{len(lines)}">{esc(sub)}</div>')
    n_extra = len(blocks) - 1
    doc = PAGE.format(font=_font_data_uri(STYLE["font_file"]), bg=STYLE["bg"], fg=STYLE["fg"],
                      muted=STYLE["muted"], px=px, weight=weight, hook_weight=max(weight, 600),
                      title_html=(f'<div class="title">{esc(title)}</div><div class="rule"></div>' if title else ""),
                      lines_html="".join(blocks), bottom=esc(bottom or "").replace("\n", "<br>"))
    total = int(duration * FPS)
    reveal_start, step, fade_in = 0.8, 0.9, 0.7
    fade_out_start, fade_out = duration - 1.3, 1.0

    def opacity(idx, t):  # idx >= 1
        a = _ease((t - (reveal_start + (idx - 1) * step)) / fade_in)
        b = 1 - _ease((t - fade_out_start) / fade_out)
        return min(a, b)

    tmp = Path(tempfile.mkdtemp(prefix="reel_"))
    try:
        with sync_playwright() as p:
            br = p.chromium.launch()
            pg = br.new_page(viewport={"width": 1080, "height": 1920})
            pg.set_content(doc)
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(100)
            # auto-fit: shrink all text lines until the block fits the safe middle area
            pg.evaluate("""() => {
              const mid = document.querySelector('.mid');
              const lns = [...document.querySelectorAll('.ln, .sub')];
              let k = 1.0;
              while (mid.scrollHeight > mid.clientHeight + 1 && k > 0.45) {
                k -= 0.04;
                lns.forEach(e => { if (!e.dataset.px) e.dataset.px = parseFloat(getComputedStyle(e).fontSize);
                                   e.style.fontSize = (e.dataset.px * k) + 'px'; });
              }
            }""")
            for f in range(total):
                t = f / FPS
                ops = [opacity(i, t) for i in range(1, n_extra + 1)]
                pg.evaluate("ops => ops.forEach((o,i)=>{document.getElementById('l'+(i+1)).style.opacity=o})", ops)
                pg.screenshot(path=str(tmp / f"f{f:04d}.jpg"), type="jpeg", quality=92)
            br.close()
        out.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp / "f%04d.jpg")]
        if audio == "ambience":
            cmd += ["-f", "lavfi", "-t", str(duration), "-i",
                    "anoisesrc=color=brown:amplitude=0.5:sample_rate=44100",
                    "-af", f"lowpass=f=900,highpass=f=60,volume=0.35,afade=t=in:d=0.8,"
                           f"afade=t=out:st={duration - 0.8}:d=0.8"]
        elif audio == "silence":
            cmd += ["-f", "lavfi", "-t", str(duration), "-i", "anullsrc=r=44100:cl=stereo"]
        else:  # a recitation file the user has reuse permission for
            cmd += ["-i", str(audio), "-af", f"afade=t=out:st={duration - 0.8}:d=0.8"]
        cmd += ["-map", "0:v", "-map", "1:a", "-shortest", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)]
        subprocess.run(cmd, check=True)
        # poster frame for review pages
        shutil.copyfile(tmp / f"f{int(min(duration - 2, 6) * FPS):04d}.jpg", out.with_suffix(".jpg"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out
