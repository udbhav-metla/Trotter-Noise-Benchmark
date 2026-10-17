"""Render the README animation from saved native QPY circuits and CSV results.
Run from the repository root: python assets/media/generate_intro.py
Requires Pillow (available through the project's Matplotlib installation).
"""
import json, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
from qiskit import qpy
from qiskit.converters import circuit_to_dag

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
W, H = 1200, 700
BG, PANEL, LINE = '#080f21', '#101d33', '#33455f'
WHITE, MUTED, CYAN, PURPLE = '#f0f5ff', '#a1b3cc', '#58dddc', '#b29aff'
FONT_DIR = Path('C:/Windows/Fonts')
def font(size, bold=False):
    # DejaVu fallback keeps the renderer usable outside Windows.
    name = FONT_DIR / ('segoeuib.ttf' if bold else 'segoeui.ttf')
    try: return ImageFont.truetype(str(name) if name.exists() else 'DejaVuSans.ttf', size)
    except OSError: return ImageFont.load_default()
def text(d, xy, value, size=20, fill=WHITE, bold=False, anchor=None):
    d.text(xy, value, font=font(size,bold), fill=fill, anchor=anchor)
def card(d, box): d.rounded_rectangle(box, radius=18, fill=PANEL, outline='#243551', width=2)

configs = {n: json.loads((ROOT/f'processors/processor_{n}.json').read_text()) for n in ['A','B']}
summary = pd.read_csv(ROOT/'results/tables/summary.csv')
def layers(name, steps):
    with (ROOT/f'data/raw/circuits/{name}_fixed_n{steps}_t2.00.qpy').open('rb') as f:
        circuit=qpy.load(f)[0]
    result=[]
    for layer in circuit_to_dag(circuit).layers():
        result.append([(node.op.name,[circuit.find_bit(q).index for q in node.qargs])
                       for node in layer['graph'].op_nodes()])
    assert len(result)==circuit.depth()
    return result

def draw_frame(n, index, schedules):
    im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im)
    text(d,(40,22),'GUARDIANS OF THE GALAXY',15,CYAN,True)
    text(d,(40,48),'More steps. More gates. Better simulation?',34,WHITE,True)
    text(d,(40,100),'PS-S3  /  FOUR-SPIN ISING DYNAMICS  /  QISKIT FALL FEST',15,MUTED)
    d.rounded_rectangle((948,30,1160,98),radius=14,fill='#21344e')
    text(d,(1054,64),f'{n} TROTTER STEP'+('S' if n>1 else ''),19,CYAN,True,'mm')
    for name,x,color in [('A',40,CYAN),('B',620,PURPLE)]:
        card(d,(x,145,x+540,493));cfg=configs[name];seq=schedules[name]
        layer=seq[min(index,len(seq)-1)]
        active={q for gate,qs in layer for q in qs}
        active_edges={tuple(sorted(qs)) for gate,qs in layer if gate=='cx'}
        text(d,(x+24,165),f'PROCESSOR {name}',20,color,True)
        text(d,(x+24,197),'5-qubit line' if name=='A' else '9-qubit V2 reference',16,MUTED)
        if name=='A': pos={i:(x+70+i*100,320) for i in range(5)}
        else:
            pos={i:(x+60+(p[0]+2)/4.5*420,250+(1.5-p[1])/3.5*166) for i,p in [(int(k),v) for k,v in cfg['positions'].items()]}
        for a,b in cfg['undirected_edges']:
            hot=tuple(sorted((a,b))) in active_edges
            d.line([pos[a],pos[b]],fill=color if hot else LINE,width=7 if hot else 3)
        for q,(px,py) in pos.items():
            hot=q in active
            if hot: d.ellipse((px-27,py-27,px+27,py+27),fill='#28445b',outline=color,width=2)
            d.ellipse((px-19,py-19,px+19,py+19),fill=color if hot else '#21324a',outline=color if hot else '#5b708e',width=2)
            text(d,(px,py-1),str(q),18,BG if hot else WHITE,True,'mm')
        label='  '.join(f'{g.upper()}({",".join(map(str,qs))})' for g,qs in layer)
        text(d,(x+24,449),label,14,MUTED)
        text(d,(x+516,173),f'LAYER {min(index+1,len(seq))}/{len(seq)}',13,MUTED,anchor='ra')
    row=summary[(summary.processor=='A')&(summary.layout_mode=='fixed')&(summary.steps==n)].iloc[0]
    metrics=[('NATIVE DEPTH',str(int(row.depth))),('CX GATES',str(int(row.cx_count))),('ROUTING SWAPS','0'),('MEAN EXPECTED Z0 ERROR',f'{row.total_expected_error:.6f}')]
    for i,(label,value) in enumerate(metrics):
        x=40+i*290;card(d,(x,513,x+270,613));text(d,(x+18,527),label,13,MUTED);text(d,(x+18,551),value,30,CYAN if i==3 else WHITE,True)
    frac=(index+1)/max(map(len,schedules.values()))
    d.rounded_rectangle((40,635,1160,640),radius=2,fill=LINE)
    d.rounded_rectangle((40,635,40+1120*frac,640),radius=2,fill=CYAN)
    text(d,(40,659),'Native gate layers at t = 2.0; highlights show scheduled operations, not quantum states.',15,MUTED)
    text(d,(1160,659),'Means: t > 0',15,MUTED,anchor='ra')
    return im

frames=[];schedule_info={}
for n in [1,2,4]:
    schedules={name:layers(name,n) for name in ['A','B']}
    schedule_info[str(n)]={name:len(seq) for name,seq in schedules.items()}
    for idx in range(max(map(len,schedules.values()))): frames.append(draw_frame(n,idx,schedules))
    frames.extend([frames[-1]]*12)
# One shared palette avoids distracting color changes between GIF frames.
palette=frames[0].quantize(colors=128)
frames=[f.quantize(palette=palette,dither=Image.Dither.NONE) for f in frames]
frames[0].save(OUT/'processor_intro.gif',save_all=True,append_images=frames[1:],duration=130,loop=0,optimize=True,disposal=1)
frames[0].convert('RGB').save(OUT/'processor_intro_poster.png')
(OUT/'intro_metadata.json').write_text(json.dumps({'source':'Saved fixed-layout native QPY circuits at t=2.0; positive-time CSV means','steps':[1,2,4],'native_layers':schedule_info,'rendered_frames':len(frames),'frame_duration_ms':130,'note':'Scheduling illustration; not a quantum-state trajectory or hardware timing.'},indent=2)+'\n')
print('Generated looping GIF:',(OUT/'processor_intro.gif').stat().st_size,'bytes')
