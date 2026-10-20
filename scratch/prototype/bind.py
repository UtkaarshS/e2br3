import sys, time
sys.path.insert(0, sys.argv[1])
from xsdata.formats.dataclass.parsers import XmlParser
import icsr
cls = getattr(icsr, "McciIn200100Uv01")
p = XmlParser()
for f in sys.argv[2:]:
    t=time.time()
    try:
        obj = p.parse(f, cls); print("OK", round(time.time()-t,2), f.split('/')[-1])
    except Exception as e: print("ERR", f.split('/')[-1], str(e)[:150])
