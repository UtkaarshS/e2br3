import sys, glob, collections, xml.etree.ElementTree as ET
for f in sorted(sys.argv[1:]):
    t=ET.parse(f); r=t.getroot()
    tags=collections.Counter(); nf=collections.Counter(); roots=set()
    for e in r.iter():
        tags[e.tag.split('}')[-1]]+=1
        if 'nullFlavor' in e.attrib: nf[e.attrib['nullFlavor']]+=1
        for k,v in e.attrib.items():
            if k=='codeSystem': roots.add(v)
    ns=r.tag.split('}')[0].strip('{')
    print(f.split('/')[-1], '| root=',r.tag.split('}')[-1], r.attrib.get('ITSVersion'),'| ns=',ns,'| elems=',sum(tags.values()),'| subjects=',tags['subject'],'| controlMessages=', tags['PORR_IN049016UV'],'| nullFlavors=',dict(nf))
    print('   codeSystems:', sorted(roots)[:40])
