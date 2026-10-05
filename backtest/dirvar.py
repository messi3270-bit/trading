import bt
bt.DATA = {k: bt.load(k + '.csv') for k in ('h1', 'm5', 'm1')}
T,O,H,L,C,S = bt.DATA['h1']
M5 = bt.motor(*bt.DATA['m5'][:5])
def test(name, f):
    MH = bt.motor(T,O,H,L,C, f=f)
    d = MH[0]
    # duración y poder predictivo
    runs=[]; cur=d[0]; ln=1
    for x in d[1:]:
        if x==cur: ln+=1
        else: runs.append(ln); cur=x; ln=1
    pr=[]
    for N in (4,24):
        ok=tot=0
        for i in range(len(C)-N):
            if d[i]==0: continue
            tot+=1; ok += ((C[i+N]-C[i])*d[i]>0)
        pr.append(100*ok/tot)
    bt.M5={2.0:M5}; bt.MH={2.0:MH}
    tr=[x for x in bt.run() if x['res'] is not None]
    for x in tr: x['mfe']=bt.excursion(x)
    n=len(tr); w=sum(x['res']>0 for x in tr); r1=sum(x['mfe']>=1 for x in tr)/n*100
    Rc=sum(x['res']-x['spread']/x['riesgo'] for x in tr)/n
    print(f"{name:42s} cambios1H={len(runs):5d} dura={sum(runs)/len(runs):5.1f}h  acierta4h={pr[0]:4.1f}% 24h={pr[1]:4.1f}% | ops={n:5d} acierto1:3={100*w/n:4.1f}% 1R={r1:4.1f}% R/op(spread)={Rc:+.3f}")
test('actual', {})
test('romper origen -> sin dirección', {'origen':'neutro'})
test('romper origen -> no hace nada', {'origen':'nada'})
test('sin rupturas como señal', {'sin_rupturas':True})
test('sin rupturas + origen no hace nada', {'sin_rupturas':True,'origen':'nada'})
