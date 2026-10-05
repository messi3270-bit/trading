# Añade a cada operación características de contexto y evalúa filtros (entreno 1a mitad, prueba 2a mitad)
import pickle, bisect, datetime as dt, math
import bt
D = pickle.load(open('res.pkl', 'rb'))
tr = [x for x in D['trades'] if x['res'] is not None]
TH, OH, HH, LH, CH, _ = bt.load('h1.csv')
T5, O5, H5, L5, C5, _ = bt.load('m5.csv')

def pivots(T, H, L, P=3, tf=60):
    """lista (tiempo_disponible, precio, esAlto) de pivotes alternados, disponibles al cerrar la vela i"""
    out = []; ult = 0; last = None
    for i in range(2 * P, len(T)):
        j = i - P
        ph = all(H[j] > H[j - a] for a in range(1, P + 1)) and all(H[j] >= H[j + a] for a in range(1, P + 1))
        pl = all(L[j] < L[j - a] for a in range(1, P + 1)) and all(L[j] <= L[j + a] for a in range(1, P + 1))
        tav = T[i] + tf
        if ph:
            if ult == 1 and out and H[j] > out[-1][1]: out[-1] = (tav, H[j], True)
            elif ult != 1: out.append((tav, H[j], True)); ult = 1
        if pl:
            if ult == -1 and out and L[j] < out[-1][1]: out[-1] = (tav, L[j], False)
            elif ult != -1: out.append((tav, L[j], False)); ult = -1
    return out

def ctx(piv, t):
    k = bisect.bisect_right([p[0] for p in piv], t)
    pv = piv[:k]
    highs = [p[1] for p in pv if p[2]][-2:]; lows = [p[1] for p in pv if not p[2]][-2:]
    if len(highs) < 2 or len(lows) < 2: return None
    estr = 1 if (highs[1] > highs[0] and lows[1] > lows[0]) else -1 if (highs[1] < highs[0] and lows[1] < lows[0]) else 0
    return estr, highs[1], lows[1]

PH = pivots(TH, HH, LH, 3, 60)
P5 = pivots(T5, H5, L5, 3, 5)
PHt = [p[0] for p in PH]; P5t = [p[0] for p in P5]
def ctx2(piv, pt, t):
    k = bisect.bisect_right(pt, t); pv = piv[max(0, k - 6):k]
    highs = [p[1] for p in pv if p[2]][-2:]; lows = [p[1] for p in pv if not p[2]][-2:]
    if len(highs) < 2 or len(lows) < 2: return None
    estr = 1 if (highs[1] > highs[0] and lows[1] > lows[0]) else -1 if (highs[1] < highs[0] and lows[1] < lows[0]) else 0
    return estr, highs[1], lows[1]

# EMA 1H de 50 velas (tendencia de fondo)
ema = []; a = 2 / 51; e = CH[0]
for c in CH: e = a * c + (1 - a) * e; ema.append(e)

dcount = {}
for x in tr:
    t = x['t']; d = 1 if x['compra'] else -1
    c1 = ctx2(PH, PHt, t); c5 = ctx2(P5, P5t, t)
    x['estr1h'] = (c1[0] * d) if c1 else 0          # +1 a favor, -1 en contra, 0 lateral
    x['estr5m'] = (c5[0] * d) if c5 else 0
    if c1 and c1[1] > c1[2]:
        pos = (x['ent'] - c1[2]) / (c1[1] - c1[2])  # 0 = en el bajo, 1 = en el alto
        x['pos1h'] = pos if d == 1 else 1 - pos     # <0.5 = descuento (compra) / premium (venta)
    else: x['pos1h'] = None
    k = bisect.bisect_right(TH, t - 60) - 1          # última vela 1H cerrada
    x['ema'] = (1 if CH[k] > ema[k] else -1) * d if k >= 0 else 0
    hr = dt.datetime.fromtimestamp(t * 60).hour
    x['hora'] = hr
    day = dt.datetime.fromtimestamp(t * 60).date()
    dcount[day] = dcount.get(day, 0) + 1; x['n_dia'] = dcount[day]

mid = sorted(x['t'] for x in tr)[len(tr) // 2]
A = [x for x in tr if x['t'] < mid]; B = [x for x in tr if x['t'] >= mid]

def st(l):
    n = len(l)
    if n == 0: return '   n=0'
    w = sum(x['res'] > 0 for x in l)
    rc = sum(x['res'] - x['spread'] / x['riesgo'] for x in l) / n
    se = 4 * math.sqrt(0.25 * 0.75 / n)  # error típico aprox del R/op con 1:3
    return f'n={n:5d} acierto={100*w/n:5.1f}% R/op={rc:+.3f} (±{se:.3f})'

def show(name, f):
    print(f'{name:44s} ENTRENO {st([x for x in A if f(x)])} | PRUEBA {st([x for x in B if f(x)])}')

show('BASE (todas)', lambda x: True)
show('Estructura 1H a favor (HH-HL / LH-LL)', lambda x: x['estr1h'] == 1)
show('Estructura 1H en contra', lambda x: x['estr1h'] == -1)
show('Estructura 5m a favor', lambda x: x['estr5m'] == 1)
show('Estructura 1H y 5m a favor', lambda x: x['estr1h'] == 1 and x['estr5m'] == 1)
show('Descuento/premium 1H (<50 %)', lambda x: x['pos1h'] is not None and x['pos1h'] < 0.5)
show('Zona cara (>50 %)', lambda x: x['pos1h'] is not None and x['pos1h'] >= 0.5)
show('EMA50 1H a favor', lambda x: x['ema'] == 1)
show('Estructura 1H + descuento', lambda x: x['estr1h'] == 1 and x['pos1h'] is not None and x['pos1h'] < 0.5)
show('Sesión Londres+NY (09-19 servidor)', lambda x: 9 <= x['hora'] < 19)
show('Solo 1a operación del día', lambda x: x['n_dia'] == 1)
show('Primeras 3 del día', lambda x: x['n_dia'] <= 3)
show('SL 1-3 puntos', lambda x: 1 <= x['riesgo'] < 3)
show('SL >= 2 puntos', lambda x: x['riesgo'] >= 2)
show('Estructura 1H + desc. + Londres/NY', lambda x: x['estr1h'] == 1 and x['pos1h'] is not None and x['pos1h'] < 0.5 and 9 <= x['hora'] < 19)

print('\n% que llega a k R antes del SL en el mejor filtro (estructura 1H + descuento), todo el periodo:')
sel = [x for x in tr if x['estr1h'] == 1 and x['pos1h'] is not None and x['pos1h'] < 0.5]
for k in (1, 2, 3):
    print(f'  {k}R: {100*sum(x["mfe"]>=k for x in sel)/len(sel):5.1f}%  (azar {100/(1+k):.0f}%)')
pickle.dump(tr, open('feat.pkl', 'wb'))
