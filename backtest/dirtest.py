import bt, random
T,O,H,L,C,S = bt.load('h1.csv')
d,_,_,_ = bt.motor(T,O,H,L,C)
for N in (1,4,12,24):
    ok=tot=0; s=0.0
    for i in range(len(C)-N):
        if d[i]==0: continue
        r = C[i+N]-C[i]; tot+=1; ok += (r*d[i]>0); s += r*d[i]
    print(f'1H dir -> próximas {N:2d}h: acierta el sentido {100*ok/tot:5.1f}%  media {s/tot:+.2f} puntos')
