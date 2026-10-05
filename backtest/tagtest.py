import bt, math
bt.DATA = {k: bt.load(k + '.csv') for k in ('h1', 'm5', 'm1')}
bt.M5 = {2.0: bt.motor(*bt.DATA['m5'][:5])}; bt.MH = {2.0: bt.motor(*bt.DATA['h1'][:5])}
def st(l):
    n=len(l); w=sum(x['res']>0 for x in l); rc=sum(x['res']-x['spread']/x['riesgo'] for x in l)/n
    return f"n={n:5d} acierto={100*w/n:5.1f}% R/op={rc:+.3f} (±{4*math.sqrt(.1875/n):.3f})"
for name,v in (('base',{}),('solo zonas tras manipulación (+manip 5m)',{'solo_tag':True}),('solo zonas tras manipulación, sin manip 5m',{'solo_tag':True,'sin_man5':True})):
    tr=[x for x in bt.run(v) if x['res'] is not None]
    mid=sorted(x['t'] for x in tr)[len(tr)//2]
    print(f"{name:44s} ENTRENO {st([x for x in tr if x['t']<mid])} | PRUEBA {st([x for x in tr if x['t']>=mid])}")
