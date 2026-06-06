#!/usr/bin/env python

import sys,argparse,json
from openai import OpenAI

parser = argparse.ArgumentParser()
parser.add_argument("--KeyBench", help='json file from KeyBench', required=True)
parser.add_argument("--output", help='file name for json', required=True)
parser.add_argument("--model", helkp='defaults to gpt-4o-mini', default="gpt-4o-mini")
args = parser.parse_args()

with open(args.KeyBench, 'r') as fd:
    KeyBench = json.loads(fd.read())

# The client automatically picks up the OPENAI_API_KEY environment variable
client = OpenAI()

def clean_response(s):
    try:
        start = s.find('[')
        end = s.rfind(']')+1
        return json.loads(s[start:end])
    except:
        return s

def do_it(k):
    
    if k in KeyBench:
        j = KeyBench[k]
        if 'title' in j and 'abstract' in j:
            prompt = f"""Return a valid Python list containing keywords from the following text.  Include acronyms and abbreviations as well.

[START OF DOCUMENT]
Title: {j['title']}
           
Abstract: {j['abstract']}
[END OF DOCUMENT]

"""            
            response = client.chat.completions.create(
                model=args.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a researcher with extensive knowledge about all the scientific fields."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.7 # Balances focus and creativity
            )
            
        try:
            return clean_response(response.choices[0].message.content)
        except:
            return []

with open(args.output, 'w') as fd:
    for k in sys.stdin:
        k = k.rstrip()
        print({k : {'keywords_from_bot' : do_it(k)}}, file=fd)
        fd.flush()
