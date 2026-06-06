#!/usr/bin/env python

import json,sys,gzip
from jsonpath_ng import jsonpath, parse
# pdfurls = parse('content..pdfurls')
# openaccessurl = parse('content..openaccessurl')

text = parse('$..text')
eids = parse('$..externalids')

for fn in sys.argv[1:]:
    with gzip.open(fn, 'rb') as fd:
        for line in fd:
            if len(line) < 3: continue
            j = json.loads(line)
            for mm in text.find(j):
                txt = mm.value
                if not txt or txt is None: continue
                if 'keyw' in txt.lower():
                    for src in ['acl', 'arxiv', 'pubmed', 'pubmedcentral']:
                        for m in eids.find(j):
                            if src in m.value:
                                id = m.value[src]
                                if not id is None:
                                    print('\t'.join(map(str, [ j['corpusid'], src, id])))
                        
                    
