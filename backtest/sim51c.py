import bt
bt.DATA = {k: bt.load(k + '.csv') for k in ('m5', 'm1')}
d5, z5, m5, _ = bt.motor(*bt.DATA['m5'][:5])
T1,O1,H1,L1,C1,S1 = bt.DATA['m1']; T5 = bt.DATA['m5'][0]
RR=3; BUF=0.3; MD=4; MV=4
def run(use=('ob','fvg','man')):
    busq=None; obs1=[]; ab=[]; tr=[]; usadas=set(); v5h=v5l=v5c=None
    rIdx=vIdx=None; p5=0; n5=len(T5); lows=[]; highs=[]; P=3
    for j in range(len(T1)):
        t=T1[j]; o,h,l,c=O1[j],H1[j],L1[j],C1[j]
        while p5<n5 and T5[p5]+5<=t: p5+=1
        i5=p5-1; zz=z5[i5] if i5>=0 else []; mm=m5[i5] if i5>=0 else []
        nueva5=(t%5==0)
        lows=[x for x in lows if l>=x]; highs=[x for x in highs if h<=x]
        if j>=2*P:
            q=j-P
            if all(L1[q]<L1[q-a] for a in range(1,P+1)) and all(L1[q]<=L1[q+a] for a in range(1,P+1)): lows.append(L1[q])
            if all(H1[q]>H1[q-a] for a in range(1,P+1)) and all(H1[q]>=H1[q+a] for a in range(1,P+1)): highs.append(H1[q])
        lows=lows[-50:]; highs=highs[-50:]
        for op in list(ab):
            sl_=(l<=op['sl']) if op['c'] else (h>=op['sl']); tp_=(h>=op['tp']) if op['c'] else (l<=op['tp'])
            if sl_ or tp_: op['res']=-1 if sl_ else RR; ab.remove(op)
        if nueva5 and v5c is not None and busq:
            b=busq
            if b['tipo']==0:
                if v5l<=b['top'] and v5h>=b['bot']: b['d5']+=1
                rota=(v5c<b['bot'] if b['dir']==1 else v5c>b['top']) or b['d5']>MD
            elif b['tipo']==1: rota=(v5c<b['bot'] if b['dir']==1 else v5c>b['top'])
            else:
                b['f5']=b['f5']+1 if (v5c<b['niv'] if b['dir']==1 else v5c>b['niv']) else 0; rota=b['f5']>MV
            if rota: busq=None; obs1=[]
        if busq is None and not ab:
            for (top,bot,alc,fvg,tg) in zz:
                if busq: break
                if ('fvg' if fvg else 'ob') not in use: continue
                mid=(top+bot)/2
                toca=((l<=mid) if alc else (h>=mid)) if fvg else ((l<=top) if alc else (h>=bot))
                key=(1 if fvg else 0,top,bot)
                if toca and key not in usadas:
                    usadas.add(key); busq=dict(dir=1 if alc else -1,tipo=1 if fvg else 0,top=top,bot=bot,niv=None,d5=0,f5=0,z='fvg' if fvg else 'ob')
        if busq is None and not ab and 'man' in use:
            for (p,alto) in mm:
                key=(2,p,p)
                if busq is None and key not in usadas:
                    usadas.add(key); busq=dict(dir=-1 if alto else 1,tipo=2,niv=p,d5=0,f5=0,z='man')
        entro=False
        for k in range(len(obs1)-1,-1,-1):
            z=obs1[k]
            z['ext']=min(z['ext'],l) if z['a'] else max(z['ext'],h)
            toca=(l<=z['top']) if z['a'] else (h>=z['bot']); inval=(c<z['lim']) if z['a'] else (c>z['lim'])
            if l<=z['top'] and h>=z['bot']: z['d']+=1
            entra=(z['to'] or toca) and ((c>z['top']) if z['a'] else (c<z['bot']))
            if inval or z['d']>MD: obs1.pop(k)
            elif entra and not entro and busq and busq['dir']==(1 if z['a'] else -1):
                sl=z['ext']-BUF if z['a'] else z['ext']+BUF; r=(c-sl) if z['a'] else (sl-c)
                if r>0:
                    op=dict(c=z['a'],sl=sl,tp=c+RR*r if z['a'] else c-RR*r,r=r,sp=S1[j]*0.01,res=None,t=t,z=busq['z']); ab.append(op); tr.append(op); entro=True
                obs1.pop(k)
            else: z['to']=z['to'] or toca
        if entro: busq=None; obs1=[]
        if nueva5: v5h,v5l=h,l
        else: v5h=h if v5h is None else max(v5h,h); v5l=l if v5l is None else min(v5l,l)
        v5c=c
        if rIdx is not None and c>rO:
            if busq and busq['dir']==1: obs1.append(dict(top=rO,bot=rC,a=True,to=False,d=0,**(lambda m:(lambda r:dict(ext=r,lim=r))(max([x for x in lows if x<=m],default=m)))(min(L1[max(rIdx,j-400):j+1]))))
            rIdx=None
        if vIdx is not None and c<vO:
            if busq and busq['dir']==-1: obs1.append(dict(top=vC,bot=vO,a=False,to=False,d=0,**(lambda m:(lambda r:dict(ext=r,lim=r))(min([x for x in highs if x>=m],default=m)))(max(H1[max(vIdx,j-400):j+1]))))
            vIdx=None
        if c<o: rIdx,rO,rC=j,o,c
        if c>o: vIdx,vO,vC=j,o,c
    return [x for x in tr if x['res'] is not None]
def st(tr,name):
    n=len(tr); w=sum(x['res']>0 for x in tr)
    R=sum(x['res'] for x in tr)/n; Rc=sum(x['res']-x['sp']/x['r'] for x in tr)/n
    mid=sorted(x['t'] for x in tr)[n//2]
    a=[x for x in tr if x['t']<mid]; b=[x for x in tr if x['t']>=mid]
    f=lambda l: sum(x['res']-x['sp']/x['r'] for x in l)/len(l)
    print(f"{name:20s} ops={n:5d} acierto={100*w/n:5.1f}% R/op={R:+.3f} con spread={Rc:+.3f} | 1a mitad {f(a):+.3f} 2a mitad {f(b):+.3f}")
tr=run(); st(tr,'todo (C)')
for z in ('ob','fvg','man'): st([x for x in tr if x['z']==z],'  solo zona '+z)
