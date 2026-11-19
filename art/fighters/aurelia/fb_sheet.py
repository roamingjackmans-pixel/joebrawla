"""Contact sheet of the clip-check renders: py fb_sheet.py <clipcheck_dir> <out.jpg> [tile]"""
import sys, os, glob
from PIL import Image, ImageDraw

d, out = sys.argv[1], sys.argv[2]
tile = int(sys.argv[3]) if len(sys.argv) > 3 else 300
files = sorted(glob.glob(os.path.join(d, '*.jpg')))
clips = sorted({os.path.basename(f).rsplit('_', 1)[0] for f in files})
cols = 6
rows = len(clips)
sheet = Image.new('RGB', (cols * tile, rows * (tile + 18)), (40, 40, 40))
dr = ImageDraw.Draw(sheet)
for r, c in enumerate(clips):
    fs = sorted(f for f in files if os.path.basename(f).rsplit('_', 1)[0] == c)
    for k, f in enumerate(fs[:cols]):
        im = Image.open(f).convert('RGB').resize((tile, tile))
        sheet.paste(im, (k * tile, r * (tile + 18) + 18))
    dr.text((4, r * (tile + 18) + 3), c, fill=(255, 255, 255))
sheet.save(out, quality=88)
print('sheet', out, sheet.size)
