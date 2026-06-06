#!/usr/bin/env python

# The following explains how to convert pdf to json
# https://www.google.com/search?q=convert+pdf+to+json+with+fitz&oq=convert+pdf+to+json+with+fitz

import sys,json,gzip
from jsonpath_ng import jsonpath, parse

textlines_pat = parse('$..textlines')
text_pat = parse('$..text')
font_pat = parse('$..font')
boxclass_pat = parse('$..boxclass')

def keywordp(j):
    for m in text_pat.find(j):
        if 'keyword' in m.value.lower():
            return True
    return False

def boldp(j):
    for m in font_pat.find(j):
        if 'bold' in m.value.lower():
            return True
    return False

def print_keywords(j):
    for m in text_pat.find(j):
        print(m.value)

freePass=0

# read json from fitz on stdin
# output keywords on first page of pdf

for line in sys.stdin:
    j=json.loads(line.rstrip())
    pages = j['pages']
    for bc in boxclass_pat.find(pages[0]):
        if bc.value == 'section-header' and keywordp(bc.context.value): 
            print_keywords(bc.context.value)
            freePass=1
        if bc.value != 'text': continue
        if freePass or keywordp(bc.context.value):
            if len(text_pat.find(bc.context.value)) < 20:
                print_keywords(bc.context.value)
        freePass=0
