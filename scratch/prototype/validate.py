import sys, time, glob
from lxml import etree
xsd = sys.argv[1]
t=time.time(); schema = etree.XMLSchema(etree.parse(xsd)); print("schema load s:", round(time.time()-t,2))
for f in sys.argv[2:]:
    try:
        doc = etree.parse(f, etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False))
        ok = schema.validate(doc)
        errs = [f"{e.line}:{e.message[:120]}" for e in schema.error_log][:2]
        print(("PASS" if ok else "FAIL"), f.split('/')[-1], "" if ok else errs)
    except Exception as ex:
        print("ERR", f.split('/')[-1], str(ex)[:150])
