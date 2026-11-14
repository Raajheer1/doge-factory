"""Import dated eCFR sections into hosted HydraDB BYOG collections.

Uses only official public eCFR XML. No keys are written to files. Imports are
idempotent for a given snapshot date. Existing collections are never deleted.
"""
import argparse
import gzip
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BASE = 'https://www.ecfr.gov'
PARTS = {
    'housing': {
        24: [5, 8, 35, 91, 92, 93, 200, 202, 203, 245, 247, 882, 883, 884, 886, 891, 905, 908, 912, 960, 964, 966, 982, 983, 984, 985, 1000, 1003, 1005, 1006],
    },
    'healthcare': {
        42: [400, 401, 403, 405, 410, 411, 412, 413, 414, 415, 416, 418, 419, 420, 422, 423, 424, 425, 431, 433, 435, 436, 438, 440, 441, 447, 455, 457, 460, 482, 483, 484, 485, 488, 489, 490, 493, 494, 495, 498, 512, 518, 1001],
        45: [155, 156, 160, 164, 170, 171, 180],
    },
}

def http(url, payload=None, key=None):
    headers = {'User-Agent': 'DOGE-Factory-Policy-Research/1.0', 'Accept-Encoding': 'gzip'}
    if key:
        headers['Authorization'] = 'Bearer ' + key
        headers['Content-Type'] = 'application/json'
    data = json.dumps(payload).encode() if payload is not None else None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=90) as r:
                body = r.read()
                return gzip.decompress(body) if r.headers.get('Content-Encoding') == 'gzip' else body
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise RuntimeError(f'HTTP {e.code} from {urllib.parse.urlsplit(url).netloc}') from e
        except (urllib.error.URLError, TimeoutError):
            if attempt == 3: raise
        time.sleep(2 ** attempt)

def query(base, key, database, collection, cypher, rows):
    payload = {'database': database, 'collection': collection, 'query': cypher, 'params': {'rows': rows}}
    reply = json.loads(http(base.rstrip('/') + '/byog/query', payload, key))
    if not reply.get('success') or not isinstance(reply.get('data'), list):
        raise RuntimeError('HydraDB query failed: ' + str(reply.get('error', 'invalid response')))

def batches(rows, max_bytes=150000, max_rows=250):
    batch, size = [], 0
    for row in rows:
        row_size = len(json.dumps(row).encode())
        if row_size > max_bytes:
            raise ValueError(f'Row {row.get("id", "edge")} exceeds request size limit')
        if batch and (size + row_size > max_bytes or len(batch) >= max_rows):
            yield batch
            batch, size = [], 0
        batch.append(row)
        size += row_size
    if batch: yield batch

def clean(node):
    return re.sub(r'\s+', ' ', ''.join(node.itertext())).strip()

def parse_part(raw, title, part, snapshot):
    root = ET.fromstring(raw)
    sections = [node for node in root.iter() if node.attrib.get('TYPE') == 'SECTION']
    if not sections:
        raise ValueError(f'no sections found for {title} CFR part {part}')
    part_heading = clean(root.find('HEAD')) if root.find('HEAD') is not None else f'Part {part}'
    documents, passages, edges, next_edges = [], [], [], []
    for node in sections:
        number = node.attrib.get('N', '').strip()
        head = node.find('HEAD')
        heading = clean(head) if head is not None else ''
        if not number or not heading:
            continue
        chunks = [clean(child) for child in node if clean(child)]
        full = '\n\n'.join(chunks)
        if not full: continue
        doc_id = f'ecfr:{snapshot}:{title}:{number}'
        url = f'https://www.ecfr.gov/on/{snapshot}/title-{title}/section-{urllib.parse.quote(number, safe=".-")}'
        documents.append({'id': doc_id, 'title': heading, 'text': full, 'source_url': url,
                          'citation': f'{title} CFR {number}', 'document_type': 'regulation',
                          'issuing_agency': 'HUD' if title == 24 else ('HHS/CMS' if title == 42 else 'HHS'),
                          'publication_date': snapshot, 'status': 'verify_current_status',
                          'topics': part_heading, 'source_snapshot': snapshot, 'source_sha256': hashlib.sha256(raw).hexdigest()})
        previous = None
        for i, chunk in enumerate(chunks, 1):
            sid = f'{doc_id}:passage:{i:04d}'
            passages.append({'id': sid, 'title': f'{title} CFR {number}, passage {i}', 'text': chunk,
                             'citation': f'{title} CFR {number}', 'order': i, 'source_url': url})
            edges.append({'src': doc_id, 'dst': sid})
            if previous: next_edges.append({'src': previous, 'dst': sid})
            previous = sid
    if not documents: raise ValueError(f'no readable documents for {title} CFR part {part}')
    return documents, passages, edges, next_edges

def upload(base, key, db, collection, docs, passages, edges, next_edges, jurisdiction=None):
    docs_cypher = ('UNWIND $rows AS row MERGE (n:PolicyDocument {id: row.id}) SET n.title = row.title, n.text = row.text, n.source_url = row.source_url, n.citation = row.citation, n.document_type = row.document_type, n.issuing_agency = row.issuing_agency, n.publication_date = row.publication_date, n.status = row.status, n.topics = row.topics, n.source_snapshot = row.source_snapshot, n.source_sha256 = row.source_sha256')
    passage_cypher = ('UNWIND $rows AS row MERGE (n:PolicySection {id: row.id}) SET n.title = row.title, n.text = row.text, n.citation = row.citation, n.order = row.order, n.source_url = row.source_url')
    edge_cypher = ('UNWIND $rows AS row MATCH (a:PolicyDocument {id: row.src}), (b:PolicySection {id: row.dst}) MERGE (a)-[:HAS_SECTION]->(b)')
    next_cypher = ('UNWIND $rows AS row MATCH (a:PolicySection {id: row.src}), (b:PolicySection {id: row.dst}) MERGE (a)-[:NEXT_SECTION]->(b)')
    for cypher, rows in ((docs_cypher, docs), (passage_cypher, passages), (edge_cypher, edges), (next_cypher, next_edges)):
        for batch in batches(rows): query(base, key, db, collection, cypher, batch)
    jurisdiction = jurisdiction or {'id':'ecfr:jurisdiction:us','name':'United States','level':'federal'}
    query(base,key,db,collection,'UNWIND $rows AS row MERGE (j:Jurisdiction {id: row.id}) SET j.name = row.name, j.level = row.level',[jurisdiction])
    issued = [{'src':jurisdiction['id'],'dst':d['id']} for d in docs]
    for batch in batches(issued): query(base,key,db,collection,'UNWIND $rows AS row MATCH (j:Jurisdiction {id: row.src}), (d:PolicyDocument {id: row.dst}) MERGE (j)-[:ISSUED]->(d)',batch)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--domain', choices=PARTS, required=True)
    parser.add_argument('--parts', help='Comma-separated title:part entries; default is the domain manifest')
    parser.add_argument('--database', default=os.getenv('HYDRADB_DATABASE_ID', 'doge-factory'))
    args=parser.parse_args()
    key=os.environ.get('HYDRADB_API_KEY')
    if not key: raise SystemExit('HYDRADB_API_KEY is required')
    base=os.getenv('HYDRADB_BASE_URL','https://api.hydradb.com')
    titles=json.loads(http(BASE+'/api/versioner/v1/titles.json'))['titles']
    dates={t['number']:t['up_to_date_as_of'] for t in titles}
    targets=[]
    if args.parts:
        for value in args.parts.split(','):
            title,part=value.split(':');targets.append((int(title),int(part)))
    else:
        for title,parts in PARTS[args.domain].items(): targets.extend((title,part) for part in parts)
    failed=[];total_docs=total_passages=0
    for title,part in targets:
        snapshot=dates[title]
        url=f'{BASE}/api/versioner/v1/full/{snapshot}/title-{title}.xml?part={part}'
        try:
            raw=http(url);docs,passages,edges,next_edges=parse_part(raw,title,part,snapshot)
            upload(base,key,args.database,args.domain,docs,passages,edges,next_edges)
            total_docs+=len(docs);total_passages+=len(passages)
            print(json.dumps({'domain':args.domain,'title':title,'part':part,'snapshot':snapshot,'documents':len(docs),'passages':len(passages)}),flush=True)
        except Exception as e:
            failed.append({'title':title,'part':part,'error':str(e)})
            print(json.dumps({'domain':args.domain,'title':title,'part':part,'error':str(e)}),file=sys.stderr,flush=True)
    print(json.dumps({'domain':args.domain,'total_documents':total_docs,'total_passages':total_passages,'failed':failed}),flush=True)
    if failed: raise SystemExit(1)

if __name__ == '__main__': main()
