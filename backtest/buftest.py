import bt, math
bt.DATA = {k: bt.load(k + '.csv') for k in ('h1', 'm5', 'm1')}
bt.M5 = {2.0: bt.motor(*bt.DATA['m5'][:5])}; bt.MH = {2.0: bt.motor(*bt.DATA['h1'][:5])}
def st(l):
    n=len(l); w=sum(x['res']>0 for x in l); rc=sum(x['res']-x['spread']/x['riesgo'] for x in l)/n
    return f"n={n:5d} acierto={100*w/n:5.1f}% R/op={rc:+.3f} (±{4*math.sqrt(.1875/n):.3f})"
for buf in (0.0, 0.3, 1.0, 3.0):
    tr=[x for x in bt.run({'buf':buf}) if x['res'] is not None]
    for x in tr: x['mfe']=bt.excursion(x)
    mid=sorted(x['t'] for x in tr)[len(tr)//2]
    r=[100*sum(x['mfe']>=k for x in tr)/len(tr) for k in (1,2,3)]
    sl=sorted(x['riesgo'] for x in tr)[len(tr)//2]
    print(f"margen {buf:3.1f}: SL mediano {sl:4.2f} | ENTRENO {st([x for x in tr if x['t']<mid])} | PRUEBA {st([x for x in tr if x['t']>=mid])} | llega 1R/2R/3R = {r[0]:.0f}/{r[1]:.0f}/{r[2]:.0f}%")
