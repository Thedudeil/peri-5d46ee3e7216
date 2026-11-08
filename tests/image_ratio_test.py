"""PT-040: reserve the asset's actual intrinsic aspect ratio."""
from pathlib import Path
from html.parser import HTMLParser
from PIL import Image
root=Path(__file__).resolve().parents[1]
class Images(HTMLParser):
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='img' and a.get('src')=='/img/before-after.webp':
   actual=Image.open(root/'img/before-after.webp').size
   assert (int(a['width']),int(a['height']))==actual,(a,actual)
   self.found=True
parser=Images();parser.found=False;parser.feed((root/'index.html').read_text());assert parser.found
print('PASS before/after image reserves its real intrinsic dimensions')
