"""Import a focused, source-backed Iowa/Texas LIHTC research set into BYOG.

This is not a complete inventory of either state's requirements. PDF text is
machine-extracted and each document node contains at most four consecutive pages.
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import sys

from pypdf import PdfReader

from .ecfr_import import http, upload

# URLs were checked against the agencies' public resource and compliance pages.
SOURCES = [
    ('IA', 'Iowa', 'Iowa Finance Authority', 'Iowa 2026 LIHTC HOME NHTF compliance manual', 'guidance', 'https://opportunityiowa.gov/media/8404/download?inline'),
    ('IA', 'Iowa', 'Iowa Finance Authority', 'Iowa 2026–2027 second amended 9% QAP', 'allocation_plan', 'https://opportunityiowa.gov/media/7360/download?inline='),
    ('IA', 'Iowa', 'Iowa Finance Authority', 'Iowa 2026–2027 first amended 4% QAP', 'allocation_plan', 'https://opportunityiowa.gov/media/7770/download?inline='),
    ('TX', 'Texas', 'Texas Department of Housing and Community Affairs', 'Texas 2026 qualified allocation plan', 'allocation_plan', 'https://www.tdhca.texas.gov/sites/default/files/multifamily/docs/26-QAP.pdf'),
    ('TX', 'Texas', 'Texas Department of Housing and Community Affairs', 'Texas Administrative Code title 10 chapter 10 subchapter F, compliance monitoring PDF', 'regulation', 'https://www.tdhca.texas.gov/sites/default/files/pmcdocs/CM-SubCh-F-Searchable.pdf'),
    ('TX', 'Texas', 'Texas Department of Housing and Community Affairs', 'TDHCA documentation of telephone verification clarification record', 'form', 'https://www.tdhca.texas.gov/sites/default/files/pmcdocs/PhoneVer.pdf'),
    ('TX', 'Texas', 'Texas Department of Housing and Community Affairs', 'TDHCA employment verification form', 'form', 'https://www.tdhca.texas.gov/sites/default/files/pmcdocs/HOTMA-EmployVer.pdf'),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--states', default='IA,TX', help='Comma-separated state abbreviations')
    parser.add_argument('--database', default=os.getenv('HYDRADB_DATABASE_ID', 'doge-factory'))
    args = parser.parse_args()
    states = {s.strip().upper() for s in args.states.split(',')}
    if not states or states - {'IA', 'TX'}:
        parser.error('states must be IA and/or TX')
    key = os.environ.get('HYDRADB_API_KEY')
    if not key:
        raise SystemExit('HYDRADB_API_KEY is required')
    base = os.getenv('HYDRADB_BASE_URL', 'https://api.hydradb.com')
    failed = []
    for state, name, agency, title, kind, url in SOURCES:
        if state not in states:
            continue
        try:
            raw = http(url)
            if not raw.startswith(b'%PDF'):
                raise ValueError('source is not a PDF')
            reader = PdfReader(io.BytesIO(raw))
            pages = [(i, (page.extract_text() or '').strip()) for i, page in enumerate(reader.pages, 1)]
            if sum(len(text) for _, text in pages) < 500:
                raise ValueError('insufficient extractable text')
            digest = hashlib.sha256(raw).hexdigest()
            groups, current, size = [], [], 0
            for number, text in pages:
                if not text:
                    continue
                n = len(text.encode())
                if n > 90000:
                    raise ValueError(f'page {number} exceeds request limit')
                if current and (len(current) >= 4 or size + n > 12000):
                    groups.append(current)
                    current, size = [], 0
                current.append((number, text))
                size += n
            if current:
                groups.append(current)
            docs, passages, edges, next_edges = [], [], [], []
            for chunk in groups:
                first, last = chunk[0][0], chunk[-1][0]
                doc_id = f'lihtc:{state.lower()}:{digest[:16]}:pages:{first:04d}-{last:04d}'
                citation = f'{title}, page {first}' if first == last else f'{title}, pages {first}–{last}'
                docs.append({'id': doc_id, 'title': citation, 'citation': citation,
                             'text': '\n\n'.join(text for _, text in chunk), 'source_url': url,
                             'document_type': kind, 'issuing_agency': agency, 'publication_date': '',
                             'status': 'verify_current_status', 'topics': 'LIHTC, affordable housing, compliance, income verification',
                             'source_snapshot': datetime.date.today().isoformat(), 'source_sha256': digest})
                previous = None
                for order, (number, text) in enumerate(chunk, 1):
                    section_id = f'{doc_id}:page:{number:04d}'
                    passages.append({'id': section_id, 'title': f'{title}, page {number}', 'citation': f'{title}, page {number}',
                                     'text': text, 'order': order, 'source_url': url})
                    edges.append({'src': doc_id, 'dst': section_id})
                    if previous:
                        next_edges.append({'src': previous, 'dst': section_id})
                    previous = section_id
            upload(base, key, args.database, 'housing', docs, passages, edges, next_edges,
                   {'id': f'jurisdiction:us:{state.lower()}', 'name': name, 'level': 'state'})
            print(json.dumps({'state': state, 'title': title, 'pdf_pages': len(pages), 'extracted_pages': len(passages),
                              'document_chunks': len(docs), 'sha256': digest, 'url': url}), flush=True)
        except Exception as exc:
            failed.append({'state': state, 'title': title, 'error': str(exc)})
            print(json.dumps(failed[-1]), file=sys.stderr, flush=True)
    if failed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
