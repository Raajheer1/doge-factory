"""Import reviewed state LIHTC allocation plans from official PDF sources."""
import argparse
import datetime
import hashlib
import io
import json
import os
import sys
from pypdf import PdfReader
from .ecfr_import import http, upload

SOURCES={'housing':[
 ('IA','Iowa','Iowa Finance Authority','Iowa 2026–2027 second amended 9% QAP','https://opportunityiowa.gov/media/7360/download?inline='),
 ('IA','Iowa','Iowa Finance Authority','Iowa 2026–2027 first amended 4% QAP','https://opportunityiowa.gov/media/7770/download?inline='),
 ('CA','California','California Tax Credit Allocation Committee','California Tax Credit Allocation Committee regulations','https://www.treasurer.ca.gov/sites/default/files/2026-03/regulations.pdf'),
 ('TX','Texas','Texas Department of Housing and Community Affairs','Texas 2026 qualified allocation plan','https://www.tdhca.texas.gov/sites/default/files/multifamily/docs/26-QAP.pdf'),
 ('NY','New York','New York State Housing Finance Agency','New York 4% LIHTC qualified allocation plan','https://hcr.ny.gov/lihtc-4-percent-qualified-allocation-plan-effective-6112025'),
 ('FL','Florida','Florida Housing Finance Corporation','Florida 2026 qualified allocation plan','https://www.floridahousing.org/docs/default-source/programs/non-competitive/2026-qualified-allocation-plan.pdf'),
 ('IL','Illinois','Illinois Housing Development Authority','Illinois 2026 qualified allocation plan','https://www.ihda.org/wp-content/uploads/2025/07/2026-Qualified-Allocation-Plan_7.1.2025.pdf'),
 ('NC','North Carolina','North Carolina Housing Finance Agency','North Carolina 2026 qualified allocation plan','https://www.nchfa.com/sites/default/files/forms_resources/2025-12/2026FinalQAP.pdf'),
 ('CO','Colorado','Colorado Housing and Finance Authority','Colorado 2025–2026 qualified allocation plan, second amendment','https://www.chfainfo.com/getattachment/7535845e-c0fa-4061-9bcb-60d7158ea294/2025-2026-QAP-Second-Amendment.pdf'),
 ('AK','Alaska','Alaska Housing Finance Corporation','Alaska FY2027 GOAL qualified allocation plan','https://www.ahfc.us/application/files/8317/6964/7305/FY2027_GOAL_Qualified_Allocation_Plan_1.28.26.pdf'),
 ('OR','Oregon','Oregon Housing and Community Services','Oregon 2025 qualified allocation plan','https://www.oregon.gov/ohcs/rental-housing/housing-development/development-resources/Documents/QAP/2025-qap-final.pdf'),
 ('MI','Michigan','Michigan State Housing Development Authority','Michigan 2026–2027 qualified allocation plan','https://www.michigan.gov/mshda/-/media/Project/Websites/mshda/developers/lihtc/assets/liqap/mshda_li_qap_2026_2027_qap_final.pdf?hash=BA9BD929A59B4E39542122674D9671F9&rev=1f6c61133a6d4c76bd07e517dc5adbde'),
 ('GA','Georgia','Georgia Department of Community Affairs','Georgia amended 2026–2027 qualified allocation plan','https://dca.georgia.gov/document/document/2026-2027-qap-amended-board-approved-8-12-26/download'),
 ('MA','Massachusetts','Massachusetts Executive Office of Housing and Livable Communities','Massachusetts 2025–2026 qualified allocation plan','https://www.mass.gov/doc/2025-2026-lihtc-qap/download'),
 ('MA','Massachusetts','Massachusetts Executive Office of Housing and Livable Communities','Massachusetts amendment to 2025–2026 qualified allocation plan','https://www.mass.gov/doc/amendment-to-qap-2025-2026-0/download'),
 ('OH','Ohio','Ohio Housing Finance Agency','Ohio 2026–2027 9% LIHTC qualified allocation plan, technical amendment','https://www.ohiohome.org/ppd/documents/2026-2027-9Percent-LIHTC-QAP-TechnicalAmendment.pdf'),
 ('NJ','New Jersey','New Jersey Housing and Mortgage Finance Agency','New Jersey 2026 qualified allocation plan','https://www.nj.gov/dca/hmfa/developers/docs/lihtc/qap/tc_qap_download.pdf'),
 ('WA','Washington','Washington State Housing Finance Commission','Washington qualified allocation plan, amended 2012','https://www.wshfc.org/mhcf/9percent/2026application/ProgramDocs/2026qap.pdf'),
 ('PA','Pennsylvania','Pennsylvania Housing Finance Agency','Pennsylvania 2025–2026 qualified allocation plan','https://www.phfa.org/forms/multifamily_program_notices/qap/2025_and_2026/2025-2026-lihtc-qap.pdf'),
 ('PA','Pennsylvania','Pennsylvania Housing Finance Agency','Pennsylvania 2027–2028 qualified allocation plan','https://www.phfa.org/forms/multifamily_program_notices/qap/2027_and_2028/2027-2028-lihtc-qap.pdf'),
], 'healthcare':[
 ('IA','Iowa','Iowa Department of Health and Human Services','Iowa Medicaid state plan S10: MAGI income methodologies','https://hhs.iowa.gov/media/9711/download?inline='),
 ('IA','Iowa','Iowa Department of Health and Human Services','Iowa Medicaid state plan S94: eligibility process','https://hhs.iowa.gov/media/9729/download?inline='),
]}
def main():
 p=argparse.ArgumentParser();p.add_argument('--domain',choices=SOURCES,default='housing');p.add_argument('--states',help='Comma-separated state abbreviations');p.add_argument('--database',default=os.getenv('HYDRADB_DATABASE_ID','doge-factory'));args=p.parse_args()
 key=os.environ.get('HYDRADB_API_KEY');base=os.getenv('HYDRADB_BASE_URL','https://api.hydradb.com')
 if not key:raise SystemExit('HYDRADB_API_KEY is required')
 failed=[];complete=0
 states=set(args.states.upper().split(',')) if args.states else None
 for state,name,agency,title,url in SOURCES[args.domain]:
  if states and state not in states:continue
  try:
   raw=http(url)
   if not raw.startswith(b'%PDF'):raise ValueError('official URL did not return a PDF')
   reader=PdfReader(io.BytesIO(raw));pages=[(page.extract_text() or '').strip() for page in reader.pages]
   if sum(map(len,pages))<1000:raise ValueError('insufficient extractable PDF text')
   digest=hashlib.sha256(raw).hexdigest();prefix='qap' if args.domain=='housing' else 'healthcare-state-plan';group=f'{prefix}:{state.lower()}:{digest[:16]}'
   # Keep each document part well below hosted BYOG request limits. The part
   # text is exactly the concatenation of the stored ordered page passages.
   groups=[];curr=[];size=0
   for i,page in enumerate(pages,1):
    if not page:continue
    if len(page.encode())>90000:raise ValueError(f'page {i} is too large')
    if curr and size+len(page.encode())>90000:groups.append(curr);curr=[];size=0
    curr.append((i,page));size+=len(page.encode())
   if curr:groups.append(curr)
   total_passages=0
   for n,chunk in enumerate(groups,1):
    first,last=chunk[0][0],chunk[-1][0];doc_id=f'{group}:part:{n:03d}';citation=f'{title}, pages {first}–{last}'
    doc={'id':doc_id,'title':citation,'text':'\n\n'.join(page for _,page in chunk),'source_url':url,'citation':citation,'document_type':'allocation_plan' if args.domain=='housing' else 'state_plan','issuing_agency':agency,'publication_date':'','status':'verify_current_status','topics':'affordable housing,LIHTC,qualified allocation plan' if args.domain=='housing' else 'Medicaid,eligibility,income verification', 'source_snapshot':datetime.date.today().isoformat(),'source_sha256':digest}
    passages=[];edges=[];nex=[];prev=None
    for order,(page_num,text) in enumerate(chunk,1):
     sid=f'{doc_id}:page:{page_num:04d}';passages.append({'id':sid,'title':f'{title}, page {page_num}','text':text,'citation':f'{title}, page {page_num}','order':order,'source_url':url});edges.append({'src':doc_id,'dst':sid})
     if prev:nex.append({'src':prev,'dst':sid})
     prev=sid
    jurisdiction={'id':f'jurisdiction:us:{state.lower()}','name':name,'level':'state'}
    upload(base,key,args.database,args.domain,[doc],passages,edges,nex,jurisdiction);total_passages+=len(passages)
   complete+=1;print(json.dumps({'state':state,'title':title,'parts':len(groups),'pages':total_passages,'sha256':digest}),flush=True)
  except Exception as e:
   failed.append({'state':state,'title':title,'error':str(e)});print(json.dumps(failed[-1]),file=sys.stderr,flush=True)
 print(json.dumps({'completed':complete,'failed':failed}),flush=True)
 if failed:raise SystemExit(1)
if __name__=='__main__':main()
