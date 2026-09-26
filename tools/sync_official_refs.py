#!/usr/bin/env python3
import hashlib, json, os, re, sys, urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin

UA = "CPC-Trainer-Reference-Sync/1.0 (+public CMS/CDC mirror)"
ICD_PAGE = "https://www.cms.gov/medicare/coding-billing/ICD-10-codes"
HCPCS_PAGE = "https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-system/quarterly-update"
APRIL_GUIDE = "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Publications/ICD10CM/2026-update/ICD-10-CM%20April%201%202026%20Guidelines%20Final.pdf"

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links=[]
        self.href=None
        self.buf=[]
    def handle_starttag(self, tag, attrs):
        if tag.lower()=="a":
            self.href=dict(attrs).get("href")
            self.buf=[]
    def handle_data(self, data):
        if self.href is not None:
            self.buf.append(data)
    def handle_endtag(self, tag):
        if tag.lower()=="a" and self.href is not None:
            text=" ".join("".join(self.buf).split())
            self.links.append((text,self.href))
            self.href=None
            self.buf=[]

def fetch(url):
    req=urllib.request.Request(url, headers={"User-Agent":UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read(), r.geturl(), dict(r.headers)

def links(url):
    b, final, _ = fetch(url)
    p=LinkParser(); p.feed(b.decode("utf-8","ignore"))
    return [(t,urljoin(final,h)) for t,h in p.links if h]

def pick(ls, needles):
    needles=[n.lower() for n in needles]
    for text,href in ls:
        t=text.lower()
        if all(n in t for n in needles):
            return href
    raise RuntimeError("No matching link: "+repr(needles))

def download(url, dest):
    b, final, hdr = fetch(url)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest,"wb") as f: f.write(b)
    return {
        "source_url": final,
        "bytes": len(b),
        "sha256": hashlib.sha256(b).hexdigest(),
        "content_type": hdr.get("Content-Type","")
    }

def main():
    icd=links(ICD_PAGE)
    hcpcs=links(HCPCS_PAGE)

    releases=[
      {
        "id":"2026-04",
        "effective_from":"2026-04-01",
        "effective_through":"2026-09-30",
        "icd_release":"april-1-2026",
        "hcpcs_release":"july-2026",
        "guide_release":"april-1-2026",
        "sources":{
          "icdDesc":pick(icd,["April 1, 2026","Code Descriptions","Tabular Order"]),
          "icdIndex":pick(icd,["April 1, 2026","Code Tables","Tabular","Index"]),
          "hcpcs":pick(hcpcs,["July 2026","Alpha-Numeric HCPCS"]),
          "guidelines":APRIL_GUIDE
        }
      },
      {
        "id":"2026-10",
        "effective_from":"2026-10-01",
        "effective_through":"2027-03-31",
        "icd_release":"fy-2027",
        "hcpcs_release":"october-2026",
        "guide_release":"fy-2027",
        "sources":{
          "icdDesc":pick(icd,["2027","Code Descriptions","Tabular Order"]),
          "icdIndex":pick(icd,["2027","Code Tables","Tabular","Index"]),
          "hcpcs":pick(hcpcs,["October 2026","Alpha-Numeric HCPCS"]),
          "guidelines":pick(icd,["FY 2027","ICD-10-CM Coding Guidelines"])
        }
      }
    ]

    root=os.path.abspath(os.path.join(os.path.dirname(__file__),".."))
    manifest={"schema":1,"generated_by":"GitHub Actions from CMS/CDC public files","releases":[]}
    for rel in releases:
        out={"id":rel["id"],"effective_from":rel["effective_from"],"effective_through":rel["effective_through"],
             "icd_release":rel["icd_release"],"hcpcs_release":rel["hcpcs_release"],"guide_release":rel["guide_release"],
             "files":{}}
        folder=os.path.join(root,"updates",rel["id"])
        names={"icdDesc":"icd-desc.zip","icdIndex":"icd-index.zip","hcpcs":"hcpcs.zip","guidelines":"guidelines.pdf"}
        for kind,url in rel["sources"].items():
            dest=os.path.join(folder,names[kind])
            meta=download(url,dest)
            meta["path"]=f"updates/{rel['id']}/{names[kind]}"
            out["files"][kind]=meta
        manifest["releases"].append(out)

    mpath=os.path.join(root,"updates","manifest.json")
    os.makedirs(os.path.dirname(mpath),exist_ok=True)
    with open(mpath,"w",encoding="utf-8") as f:
        json.dump(manifest,f,indent=2,sort_keys=True)
        f.write("\n")
    print(json.dumps(manifest,indent=2))

if __name__=="__main__":
    main()
