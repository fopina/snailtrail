from pathlib import Path
from collections import defaultdict

p = Path('a.csv')

tadapts = set()

for i in p.read_text().splitlines()[1:]:
    i = i.split('\t')
    if not i[0]:
        continue
    if int(i[2]) < 15:
        continue
    ads = tuple([i[1]] + i[4:7])
    tadapts.add(ads)

alw = defaultdict(set)
ala = defaultdict(set)
awa = defaultdict(set)

for x in tadapts:
    alw[(x[0],x[1],x[2])].add(x[3])

for x in tadapts:
    ala[(x[0],x[1],x[3])].add(x[2])

for x in tadapts:
    alw[(x[0],x[2],x[3])].add(x[1])

print('== Unique adapt pairs')

for k, v in alw.items():
    if len(v) == 4:
        print(k)

for k, v in ala.items():
    if len(v) == 6:
        print(k)

for k, v in awa.items():
    if len(v) == 6:
        print(k)

print('== Burn candidates based')

for i in p.read_text().splitlines()[1:]:
    i = i.split('\t')
    if not i[0]:
        continue
    if int(i[2]) >= 15:
        continue
    klw = (i[1], i[4], i[5])
    kla = (i[1], i[4], i[6])
    kwa = (i[1], i[5], i[6])
    
    vlw = alw.get(klw, [])
    if len(vlw) == 4:
        print(i)
    
    vla = ala.get(kla, [])
    if len(vla) == 6:
        print(i)
    
    vwa = awa.get(kwa, [])
    if len(vwa) == 6:
        print(i)
