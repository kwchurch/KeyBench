#!/usr/bin/env python

import json,sys,argparse,re,ast
from jsonpath_ng import jsonpath, parse

from nltk.tokenize import word_tokenize
from nltk.util import ngrams
from nltk.corpus import stopwords
from nltk.metrics import edit_distance
from nltk.stem import PorterStemmer
import json 
from nltk.metrics import jaccard_distance

parser = argparse.ArgumentParser()
parser.add_argument("--KeyBench", help='json file from KeyBench', required=True)
parser.add_argument("--candidates", help='json file', required=True)
parser.add_argument("--candidate_jsonpath", help='row to start on', required=True)
parser.add_argument("--output", help='file name for json', required=True)
args = parser.parse_args()

candidate_pattern = parse(args.candidate_jsonpath)

def clean_str(s):
    s = s.lower()
    s = s.replace("_", " ")
    s = s.replace("- ", "")     # this is typically caused by line breaks
    s = re.sub("^ *", '', s)
    s = re.sub("[.]*$", '', s)
    return s

def clean_strs(strs):
    return [clean_str(s) for s in strs]

def clean_gold(s):
    s = s.lower()
    s = s.replace("keywords and phrases","")
    s = s.replace("author keywords","")
    s = s.replace("keywords","")
    s = s.replace("keyword","")
    s = re.sub("acm classification.*", "", s)
    s = s.replace(":","")
    s = s.replace(" →","")
    s = s.strip()
    if ";" in s:
        return clean_strs(s.split(';'))
    elif "," in s:
        return clean_strs(s.split(','))
    elif "·" in s:
        return clean_strs(s.split('·'))
    else:
        return [s]

with open(args.KeyBench, 'r') as fd:
    KeyBench = json.loads(fd.read())

try:
    with open(args.candidates, 'r') as fd:
        candidates = json.loads(fd.read())
except:
    candidates = {}
    with open(args.candidates, 'r') as fd:
        for line_number,line in enumerate(fd):
            if len(line) > 3:
                try:
                    c = ast.literal_eval(line.rstrip())
                except:
                    assert False, 'cannot parse input line: ' + str(line_number) + '\n' + line
                for k,v in c.items():
                    candidates[k] = v    

def ExactMatches(gold, test):
    res = 0
    for i in test:
        if i in gold: res += 1
    return res

def EditMatches(gold, test, slop):
    res = 0
    for i in gold:
        for j in test:
            if edit_distance(i,j) <= slop: 
                res += 1
                break
    return res

porter = PorterStemmer()
def PorterMatches(gold, test):
    res=0;
    for i in test:
        for j in gold:
            if porter.stem(i) == porter.stem(j): res += 1
    return res

def normalize_scores(j):
    n = j['n_keys']
    for k in ['exact', 'edit2', 'porter']:
        j[k] /= n

killroy = {}
with open(args.output, 'w') as fd:
    scores = {'matches': { 'exact' : 0, 
                           'edit2' : 0,
                           'porter' : 0,
                           'n_keys' : 0,
                           'n_gold' : 0,
                           'n_cand' : 0,
                          },
              'recall' : { 'exact' : 0, 
                           'edit2' : 0,
                           'porter' : 0,
                           'n_keys' : 0,
                          },
              'precision' : { 'exact' : 0, 
                           'edit2' : 0,
                           'porter' : 0,
                           'n_keys' : 0,
                          },
              }

    for k,v in candidates.items():
        for candidates in candidate_pattern.find(v):
            if k in killroy: continue
            killroy[k]=True
            if not 'keywords_from_pdf' in KeyBench[k]: continue
            gold=clean_gold(KeyBench[k]['keywords_from_pdf'])
            cand=clean_strs(candidates.context.value)
            j = {}
            j['key'] = k
            j['gold'] = gold
            j['cand'] = cand
            exact = ExactMatches(gold,cand)
            edit2 = EditMatches(gold,cand,2)
            p = PorterMatches(gold,cand)

            scores['matches']['n_keys'] += 1
            scores['matches']['n_gold'] += len(gold)
            scores['matches']['n_cand'] += len(cand)
            scores['matches']['exact'] += exact
            scores['matches']['edit2'] += edit2
            scores['matches']['porter'] += p

            scores['recall']['n_keys'] += 1
            scores['recall']['exact'] += exact/len(gold)
            scores['recall']['edit2'] += edit2/len(gold)
            scores['recall']['porter'] += p/len(gold)

            scores['precision']['n_keys'] += 1
            scores['precision']['exact'] += exact/len(cand)
            scores['precision']['edit2'] += edit2/len(cand)
            scores['precision']['porter'] += p/len(cand)

            j['matches'] = {'exact' : exact,
                            'edit2' : edit2,
                            'porter' : p}
            print(j, file=fd)
            fd.flush()

    normalize_scores(scores['precision'])
    normalize_scores(scores['recall'])
    print(scores)
