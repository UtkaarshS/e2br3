import sys
from lxml import etree
NS={'h':'urn:hl7-org:v3','xsi':'http://www.w3.org/2001/XMLSchema-instance'}
P=etree.XMLParser(resolve_entities=False,no_network=True)
for f in sys.argv[1:]:
    r=etree.parse(f,P).getroot()
    ie=r.find('.//h:investigationEvent',NS)
    c11=ie.xpath("h:id[@root='2.16.840.1.113883.3.989.2.1.3.1']/@extension",namespaces=NS)
    rx=r.xpath(".//h:observation[h:code[@code='29' and @codeSystem='2.16.840.1.113883.3.989.2.1.1.19']]",namespaces=NS)
    pts=[o.xpath("h:value/@code",namespaces=NS) for o in rx]
    drugs=r.xpath(".//h:organizer[h:code[@code='4']]/h:component/h:substanceAdministration",namespaces=NS)
    narr=ie.findtext('h:text',namespaces=NS) or ''
    batch=len(r.findall('h:PORR_IN049016UV',NS))
    print(f"{f.split('/')[-1][:34]:34} msgs={batch} C.1.1={c11[0][:28] if c11 else None!s:28} E.i={len(rx)} G.k={len(drugs)} H.1chars={len(narr)}")
