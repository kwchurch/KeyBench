#!/usr/bin/env python

import sys,json,gzip,fitz
from jsonpath_ng import jsonpath, parse

errors = 0

try:
    doc = fitz.open(sys.argv[1])
    print(doc[0].get_text())
except:
    errors += 1


