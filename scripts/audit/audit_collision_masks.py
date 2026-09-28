#!/usr/bin/env python3
"""Compare converted sprite collision metadata with legacy GMX definitions."""

import argparse
import ast
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("workspace", type=Path, help="Workspace containing source and modern project trees.")
parser.add_argument(
    "config",
    type=Path,
    help="Python rule pack containing a literal CONFIGS dictionary.",
)
parser.add_argument("--apply", action="store_true", help="Write corrected metadata to the modern projects.")
args = parser.parse_args()

ROOT = args.workspace.resolve()
CONFIG_PATH = args.config.resolve()
ALPHA_SCRIPT = Path(__file__).with_name("sprite_alpha_bounds_batch.mjs")

if not ROOT.is_dir():
    parser.error(f"workspace does not exist or is not a directory: {ROOT}")
if not CONFIG_PATH.is_file():
    parser.error(f"rule pack does not exist: {CONFIG_PATH}")

module=ast.parse(CONFIG_PATH.read_text(encoding="utf-8"))
configs={}
for node in module.body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CONFIGS' for t in node.targets):
        configs=ast.literal_eval(node.value); break
records=[]; groups={}
for project,cfg in configs.items():
    modern=ROOT/'modern'/project/'sprites'; source=ROOT/cfg['source']/'Sprites'
    if not modern.exists() or not source.exists(): continue
    relevant=set()
    for obj_name in cfg.get('objects',()):
        matches=list((ROOT/cfg['source']/'Objects').rglob(obj_name+'.xml'))
        if len(matches)==1:
            obj=ET.parse(matches[0]).getroot()
            relevant.update(filter(None,(obj.findtext('sprite'),obj.findtext('mask'))))
    for name in cfg.get('sprites',()):
        if relevant and name not in relevant: continue
        xs=list(source.rglob(name+'.xml')); ys=list((modern/name).glob('*.yy'))
        if len(xs)!=1 or len(ys)!=1: continue
        x=ET.parse(xs[0]).getroot(); y=json.loads(ys[0].read_text())
        b=x.find('./mask/bounds'); mode=b.attrib.get('mode','AUTO') if b is not None else 'FULL'
        shape=x.findtext('./mask/shape','RECTANGLE'); separate=x.findtext('./mask/separate','false')=='true'
        key=f'{project}/{name}'
        if mode=='AUTO':
            groups[key]=[str(p) for p in (modern/name).glob('*.png')]
        records.append((key,project,name,x,y,b,mode,shape,separate))
proc=subprocess.run(['node',str(ALPHA_SCRIPT)],input=json.dumps(groups),check=True,capture_output=True,text=True)
autos=json.loads(proc.stdout); rows=[]
for key,project,name,x,y,b,mode,shape,separate in records:
    mismatch=[]
    expected_mode={'AUTO':0,'FULL':1,'MANUAL':2}[mode]
    expected_kind={'RECTANGLE':0,'PRECISE':4 if separate else 1,'ELLIPSE':2,'DIAMOND':3}.get(shape,1)
    if y.get('bboxMode')!=expected_mode:mismatch.append(f"mode {y.get('bboxMode')}->{expected_mode}")
    if y.get('collisionKind')!=expected_kind:mismatch.append(f"kind {y.get('collisionKind')}->{expected_kind}")
    vals=None
    if mode=='MANUAL':
        vals={k:int(b.findtext(k,'0')) for k in ('left','right','top','bottom')}
        vals['right']=min(y['width']-1,vals['right']); vals['bottom']=min(y['height']-1,vals['bottom'])
    elif mode=='AUTO': vals=autos.get(key)
    if vals:
        for k,v in vals.items():
            if y.get('bbox_'+k)!=v:mismatch.append(f"{k} {y.get('bbox_'+k)}->{v}")
    if mismatch:
        rows.append((project,name,mode,shape,'; '.join(mismatch)))
        if args.apply:
            y['bboxMode']=expected_mode; y['collisionKind']=expected_kind
            if vals:
                for k,v in vals.items(): y['bbox_'+k]=v
            yy=ROOT/'modern'/project/'sprites'/name/(name+'.yy')
            yy.write_text(json.dumps(y,indent=2)+'\n')
print('project\tsprite\tlegacy_mode\tlegacy_shape\tmismatch')
for r in rows: print('\t'.join(r))
print(f"\n{len(rows)} mismatched sprites across {len(set(r[0] for r in rows))} projects")
