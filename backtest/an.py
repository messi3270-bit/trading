import pickle, datetime as dt, statistics as st
from collections import defaultdict
D = pickle.load(open('res.pkl', 'rb'))
tr = [x for x in D['trades'] if x['res'] is not None]
RR = 3.0

def stats(lst, name=''):
    n = len(lst)
    if n == 0: return f'{name:28s} n=0'
    w = sum(1 for x in lst if x['res'] > 0)
    R = sum(x['res'] for x in lst)
    Rc = sum(x['res'] - x['spread'] / x['riesgo'] for x in lst)
    return f'{name:28s} n={n:5d}  acierto={100*w/n:5.1f}%  R={R:8.1f}  R/op={R/n:+.3f}  con_spread R={Rc:8.1f} ({Rc/n:+.3f}/op)'

def wr_at(lst, k):
    return 100 * sum(1 for x in lst if x['mfe'] >= k) / len(lst)

print(stats(tr, 'TOTAL'))
days = len(set(dt.datetime.fromtimestamp(x['t'] * 60).date() for x in tr))
print('dias con operaciones', days, ' operaciones/dia', round(len(tr) / days, 1))
print()
print('--- dirección')
for d in (True, False): print(stats([x for x in tr if x['compra'] == d], 'COMPRA' if d else 'VENTA'))
print('--- zona de 5m que activó')
for z in ('ob5', 'fvg5', 'man5'): print(stats([x for x in tr if x['zona'] == z], z))
print('--- señal de 1H vigente')
g = defaultdict(list)
for x in tr: g[x['why1h']].append(x)
for k, v in sorted(g.items(), key=lambda a: -len(a[1])): print(stats(v, str(k)))
print('--- tamaño del SL (puntos)')
bk = [(0, 0.5), (0.5, 1), (1, 2), (2, 3), (3, 5), (5, 100)]
for a, b in bk: print(stats([x for x in tr if a <= x['riesgo'] < b], f'SL {a}-{b}'))
print('--- spread / riesgo medio:', round(st.mean(x['spread'] / x['riesgo'] for x in tr), 3), ' mediana SL:', round(st.median(x['riesgo'] for x in tr), 2))
print('--- hora del servidor')
for hh in range(24):
    print(stats([x for x in tr if dt.datetime.fromtimestamp(x['t'] * 60).hour == hh], f'h{hh:02d}'))
print('--- minutos desde el toque de 5m hasta la entrada')
for a, b in [(0, 5), (5, 15), (15, 30), (30, 60), (60, 10000)]:
    print(stats([x for x in tr if x['t_zona'] is not None and a <= x['t'] - x['t_zona'] < b], f'{a}-{b} min'))
print('--- % que llega a X R antes del SL (TP alternativo)')
for k in (0.5, 1, 1.5, 2, 2.5, 3, 4, 5):
    wr = wr_at(tr, k); print(f'  {k}R: {wr:5.1f}%   esperanza aprox {wr/100*k - (1-wr/100):+.3f} R/op')
print('--- duración de la dirección de 1H')
dh = D['dh']; TH = D['TH']; runs = []; cur = dh[0]; ln = 1
for x in dh[1:]:
    if x == cur: ln += 1
    else: runs.append(ln); cur = x; ln = 1
print('cambios de dirección', len(runs), ' duración media (velas 1H)', round(st.mean(runs), 1), ' mediana', st.median(runs))
w = defaultdict(int)
for x in D['wh']:
    if x: w[x] += 1
print('motivos de cambio/actualización en 1H:', dict(w))
print('--- mitades (robustez)')
mid = sorted(x['t'] for x in tr)[len(tr) // 2]
print(stats([x for x in tr if x['t'] < mid], '1a mitad'))
print(stats([x for x in tr if x['t'] >= mid], '2a mitad'))
print('--- tamaño del OB de 1m (puntos)')
for a, b in [(0, 0.2), (0.2, 0.5), (0.5, 1), (1, 100)]:
    print(stats([x for x in tr if a <= x['ob1_size'] < b], f'OB1 {a}-{b}'))
