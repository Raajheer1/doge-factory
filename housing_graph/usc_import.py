"""Import dated U.S. Code statutory body text from the official House site."""
import argparse
import hashlib
import json
import os
import re
import sys
from html.parser import HTMLParser
from .ecfr_import import http, upload

RELEASE='119-120'
SNAPSHOT='2026-10-07'
SOURCES={
 'housing': [(26,'42'),(42,'1437'),(42,'1437a'),(42,'1437d'),(42,'1437f'),(42,'12741'),(42,'12742'),(42,'12745'),(42,'12747'),(42,'12748'),(42,'12771'),(42,'3601'),(42,'3604')],
 'healthcare': [(42,'1395'),(42,'1395c'),(42,'1395d'),(42,'1395f'),(42,'1395w-21'),(42,'1395w-101'),(42,'1396'),(42,'1396a'),(42,'1396b'),(42,'1396d'),(42,'1396u-2'),(42,'300gg'),(42,'300gg-13'),(42,'1320d-2')],
}
class StatuteParser(HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True); self.depth=0; self.container=0; self.buf=[];self.paragraphs=[]
 def handle_starttag(self,tag,attrs):
  attrs=dict(attrs)
  if tag=='div':
   if self.container:self.container+=1
   elif 'statutory-body-container' in attrs.get('class','').split():self.container=1
  if self.container and not self.depth and tag=='p' and any(c.startswith('statutory-body') for c in attrs.get('class','').split()): self.depth=1;self.buf=[]
 def handle_endtag(self,tag):
  if self.depth and tag=='p':
   self.depth=0
   text=re.sub(r'\s+',' ',''.join(self.buf)).strip()
   if text:self.paragraphs.append(text)
  if tag=='div' and self.container:self.container-=1
 def handle_data(self,data):
  if self.depth:self.buf.append(data)

def main():
 p=argparse.ArgumentParser();p.add_argument('--domain',choices=SOURCES,required=True);p.add_argument('--sections',help='Comma-separated title:section entries from the domain manifest');p.add_argument('--database',default=os.getenv('HYDRADB_DATABASE_ID','doge-factory'));args=p.parse_args()
 key=os.environ.get('HYDRADB_API_KEY');base=os.getenv('HYDRADB_BASE_URL','https://api.hydradb.com')
 if not key:raise SystemExit('HYDRADB_API_KEY is required')
 errors=[];completed=0
 selected=set()
 if args.sections:
  for value in args.sections.split(','):
   title,section=value.strip().split(':',1);selected.add((int(title),section))
  unknown=selected-set(SOURCES[args.domain])
  if unknown:raise SystemExit('Sections not in domain manifest: '+', '.join(f'{t}:{s}' for t,s in sorted(unknown)))
 for title,section in SOURCES[args.domain]:
  if selected and (title,section) not in selected:continue
  url=f'https://uscode.house.gov/us/usc/{RELEASE}/t{title}/s{section}/'
  try:
   raw=http(url);parser=StatuteParser();parser.feed(raw.decode('utf-8','replace'));chunks=parser.paragraphs
   if not chunks or len(' '.join(chunks))<100:raise ValueError('no usable statutory body')
   base_id=f'usc:{RELEASE}:{title}:{section}';citation=f'{title} U.S.C. § {section}'
   groups=[];group=[];size=0
   for chunk in chunks:
    n=len(chunk.encode())
    if n>75000:raise ValueError('single paragraph exceeds import limit')
    if group and size+n>75000:groups.append(group);group=[];size=0
    group.append(chunk);size+=n
   if group:groups.append(group)
   for group_index, group in enumerate(groups,1):
    doc_id=base_id if group_index==1 else f'{base_id}:part:{group_index:03d}'
    label=citation if len(groups)==1 else f'{citation}, part {group_index} of {len(groups)}'
    doc={'id':doc_id,'title':label,'text':'\n\n'.join(group),'source_url':url,'citation':citation,'document_type':'statute','issuing_agency':'U.S. Congress','publication_date':SNAPSHOT,'status':'historical_snapshot','topics':'low-income housing credit' if (title,section)==(26,'42') else args.domain,'source_snapshot':SNAPSHOT,'source_sha256':hashlib.sha256(raw).hexdigest()}
    passages=[];edges=[];next_edges=[];previous=None
    for i,chunk in enumerate(group,1):
     sid=f'{doc_id}:passage:{i:04d}';passages.append({'id':sid,'title':f'{label}, passage {i}','text':chunk,'citation':citation,'order':i,'source_url':url});edges.append({'src':doc_id,'dst':sid})
     if previous:next_edges.append({'src':previous,'dst':sid})
     previous=sid
    upload(base,key,args.database,args.domain,[doc],passages,edges,next_edges)
   completed+=1
   print(json.dumps({'citation':citation,'parts':len(groups),'passages':len(chunks),'characters':sum(map(len,chunks))}),flush=True)
  except Exception as e:
   errors.append({'citation':f'{title} USC {section}','error':str(e)});print(json.dumps(errors[-1]),file=sys.stderr,flush=True)
 print(json.dumps({'domain':args.domain,'imported':completed,'failed':errors}),flush=True)
 if errors:raise SystemExit(1)
if __name__=='__main__':main()
