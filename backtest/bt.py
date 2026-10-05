# Backtest: réplica en Python de las reglas del indicador Pine (versión actual, modo historial)
import csv, datetime as dt, bisect, json, sys

PIV = 3; MAXVELAS = 4; MAXDIST = 2.0; MAXDENTRO = 4; MAXZONAS = 15; MAXNIVEL = 30; RR = 3.0

def load(fn):
    T, O, H, L, C, S = [], [], [], [], [], []
    with open(fn) as f:
        r = csv.reader(f, delimiter='\t'); next(r)
        for row in r:
            t = dt.datetime.strptime(row[0] + ' ' + row[1], '%Y.%m.%d %H:%M:%S')
            T.append(int(t.timestamp()) // 60)  # minutos
            O.append(float(row[2])); H.append(float(row[3])); L.append(float(row[4])); C.append(float(row[5])); S.append(int(row[8]))
    return T, O, H, L, C, S

class Niv:
    __slots__ = ('p', 'alto', 'estado', 'cuenta', 'ext', 'vivo')
    def __init__(s, p, alto): s.p = p; s.alto = alto; s.estado = 0; s.cuenta = 0; s.ext = None; s.vivo = True

class Zon:
    __slots__ = ('top', 'bot', 'alc', 'fvg', 'tocado', 'dentro', 'tag')
    def __init__(s, top, bot, alc, fvg, tag=False): s.top = top; s.bot = bot; s.alc = alc; s.fvg = fvg; s.tocado = False; s.dentro = 0; s.tag = tag

def motor(T, O, H, L, C, maxdist=MAXDIST, f=None):
    f = f or {}
    """Devuelve por vela (estado DESPUÉS de cerrar la vela): dir, zonas, manipulaciones confirmadas, motivo del cambio."""
    nv, fv, ob = [], [], []
    d = 0; oOrig = None; oToq = None; oUmb = None; ult = 0; uA = None; uB = None
    rIdx = None; rO = rC = None; vIdx = None; vO = vC = None
    out_dir, out_z, out_m, out_why = [], [], [], []
    lastManUp = -999; lastManDn = -999
    n = len(T)
    for i in range(n):
        o, h, l, c = O[i], H[i], L[i], C[i]
        nueva = False; man = []; why = None
        if d != 0 and oOrig is not None and (c < oOrig if d == 1 else c > oOrig):
            if f.get('origen') == 'nada': pass
            elif f.get('origen') == 'neutro': d = 0; oOrig = None; oUmb = None; why = 'rompe_origen'
            else: d = -d; oOrig = l if d == 1 else h; nueva = True; why = 'rompe_origen'
        elif d != 0 and oUmb is not None and (c > oUmb if d == 1 else c < oUmb):
            oOrig = l if d == 1 else h; nueva = True; why = 'continuacion_objetivo'
        libre = d == 0 or oUmb is None
        for k in range(len(nv) - 1, -1, -1):
            nn = nv[k]
            if not nn.vivo:
                nv.pop(k); continue
            manip = roto = cf = False
            dentro = (c <= nn.p) if nn.alto else (c >= nn.p)
            if nn.estado == 0:
                pasa = (h > nn.p) if nn.alto else (l < nn.p)
                if pasa: nn.ext = h if nn.alto else l
                manip = pasa and dentro; cf = pasa and not dentro
            else:
                nn.cuenta += 1
                nn.ext = max(nn.ext, h) if nn.alto else min(nn.ext, l)
                manip = dentro; roto = (not dentro) and nn.cuenta >= MAXVELAS
            if manip and nn.ext is not None and abs(nn.ext - nn.p) > maxdist:
                manip = False; roto = True
            if cf and f.get('sin_rupturas'):
                nn.estado = 1
            if cf and not f.get('sin_rupturas'):
                nn.estado = 1
                dR = 1 if nn.alto else -1
                if libre or dR == -d:
                    d = dR; oOrig = l if dR == 1 else h; nueva = True; libre = False; why = 'ruptura_nivel'
                elif dR == d:
                    oOrig = l if dR == 1 else h; nueva = True; why = why or 'continuacion_nivel'
            if manip:
                man.append((nn.p, nn.alto))
                if nn.alto: lastManDn = i
                else: lastManUp = i
            if manip or roto:
                dM = -1 if nn.alto else 1
                if manip and (libre or dM == -d):
                    d = dM; oOrig = nn.ext; nueva = True; libre = False; why = 'manipulacion'
                nn.vivo = False; nv.pop(k)
        # pivotes (vela i-PIV)
        if i >= 2 * PIV:
            j = i - PIV
            ph = H[j] if all(H[j] > H[j - a] for a in range(1, PIV + 1)) and all(H[j] >= H[j + a] for a in range(1, PIV + 1)) else None
            pl = L[j] if all(L[j] < L[j - a] for a in range(1, PIV + 1)) and all(L[j] <= L[j + a] for a in range(1, PIV + 1)) else None
            if ph is not None:
                rep = ult == 1
                if not rep or ph > uA.p:
                    if rep and uA.vivo and uA.estado == 0: uA.vivo = False
                    uA = Niv(ph, True); nv.append(uA); ult = 1
            if pl is not None:
                rep = ult == -1
                if not rep or pl < uB.p:
                    if rep and uB.vivo and uB.estado == 0: uB.vivo = False
                    uB = Niv(pl, False); nv.append(uB); ult = -1
        while len(nv) > MAXNIVEL:
            v = nv.pop(0); v.vivo = False
        for arr, nm in ((fv, 'fvg'), (ob, 'ob')):
            dz = 0; borde = None; rup = 0
            for k in range(len(arr) - 1, -1, -1):
                z = arr[k]
                mid = (z.top + z.bot) / 2
                toca = ((l <= mid) if z.alc else (h >= mid)) if z.fvg else ((l <= z.top) if z.alc else (h >= z.bot))
                inval = (c < z.bot) if z.alc else (c > z.top)
                if l <= z.top and h >= z.bot: z.dentro += 1
                atas = (not z.fvg) and z.dentro > MAXDENTRO
                afav = (c > o) if z.alc else (c < o)
                reac = afav and (toca or z.tocado)
                if inval or atas:
                    if inval: rup = -1 if z.alc else 1
                    arr.pop(k)
                elif reac:
                    dz = 1 if z.alc else -1; borde = z.bot if z.alc else z.top; arr.pop(k)
                else:
                    z.tocado = toca
            if dz != 0 and (libre or dz == -d):
                d = dz; oOrig = borde; nueva = True; libre = False; why = 'reaccion_' + nm
            if rup != 0 and not f.get('sin_rupturas'):
                if libre or rup == -d:
                    d = rup; oOrig = l if rup == 1 else h; nueva = True; libre = False; why = 'ruptura_' + nm
                elif rup == d:
                    oOrig = l if rup == 1 else h; nueva = True; why = why or ('continuacion_' + nm)
        if i >= 2:
            if l > H[i - 2]: fv.append(Zon(l, H[i - 2], True, True, i - lastManUp <= 6))
            if h < L[i - 2]: fv.append(Zon(L[i - 2], h, False, True, i - lastManDn <= 6))
        while len(fv) > MAXZONAS: fv.pop(0)
        if rIdx is not None and c > rO:
            ob.append(Zon(rO, rC, True, False, i - lastManUp <= 6)); rIdx = None
        if vIdx is not None and c < vO:
            ob.append(Zon(vC, vO, False, False, i - lastManDn <= 6)); vIdx = None
        while len(ob) > MAXZONAS: ob.pop(0)
        if c < o: rIdx = i; rO = o; rC = c
        if c > o: vIdx = i; vO = o; vC = c
        if nueva:
            best = None; toq = None; umb = None
            for nn in nv:
                if nn.vivo and ((nn.alto and nn.p > c) if d == 1 else ((not nn.alto) and nn.p < c)):
                    ds = abs(nn.p - c)
                    if best is None or ds < best: best = ds; toq = nn.p; umb = nn.p
            for arr in (ob, fv):
                for z in arr:
                    if ((not z.alc) and z.bot > c) if d == 1 else (z.alc and z.top < c):
                        ds = abs((z.bot if d == 1 else z.top) - c)
                        if best is None or ds < best:
                            best = ds; toq = z.bot if d == 1 else z.top; umb = z.top if d == 1 else z.bot
            oToq = toq; oUmb = umb
        out_dir.append(d)
        out_z.append([(z.top, z.bot, z.alc, True, z.tag) for z in fv] + [(z.top, z.bot, z.alc, False, z.tag) for z in ob])
        out_m.append(man)
        out_why.append(why)
    return out_dir, out_z, out_m, out_why

def run(variant=None):
    v = variant or {}
    maxdist = v.get('maxdist', MAXDIST)
    T1, O1, H1, L1, C1, S1 = DATA['m1']
    T5 = DATA['m5'][0]; TH = DATA['h1'][0]
    d5, z5, m5, _ = M5[maxdist]
    dh, zh, mh, wh = MH[maxdist]
    nH = len(TH); n5 = len(T5)
    hi = -1   # última vela de 1H cerrada (para la dirección, lookahead_off)
    trades = []
    busq = []      # lista de dicts
    obs1 = []
    abiertas = []
    usadas = []
    tocadas = []
    prevDir = None
    tCambio = None
    dirWhy = None
    v5h = v5l = v5c = None
    rIdx = rO = rC = None; vIdx = vO = vC = None
    p5 = 0  # índice de la vela de 5m en curso
    pH = 0
    for j in range(len(T1)):
        t = T1[j]; o, h, l, c = O1[j], H1[j], L1[j], C1[j]
        # dirección 1H: última vela de 1H con cierre <= cierre de esta vela de 1m
        while hi + 1 < nH and TH[hi + 1] + 60 <= t + 1: hi += 1
        dirHTF = dh[hi] if hi >= 0 else 0
        if hi >= 0 and wh[hi]: pass
        # snapshots: última vela de 5m / 1H cerrada antes de que empiece esta vela de 1m
        while p5 < n5 and T5[p5] + 5 <= t: p5 += 1
        i5 = p5 - 1
        while pH < nH and TH[pH] + 60 <= t: pH += 1
        iH = pH - 1
        zz5 = z5[i5] if i5 >= 0 else []
        mm5 = m5[i5] if i5 >= 0 else []
        zzH = zh[iH] if iH >= 0 else []
        T5open = t - (t % 5)
        nueva5 = (t % 5 == 0)
        if prevDir is None or dirHTF != prevDir:
            busq.clear(); obs1.clear(); tCambio = t
            # motivo de la señal de 1H vigente
            k = hi
            while k >= 0 and wh[k] is None: k -= 1
            dirWhy = wh[k] if k >= 0 else None
        prevDir = dirHTF
        if nueva5 and v5c is not None:
            for b in busq:
                if b['tipo'] == 0:
                    if v5l <= b['top'] and v5h >= b['bot']: b['dentro5'] += 1
                    if (v5c < b['bot'] if b['dir'] == 1 else v5c > b['top']) or b['dentro5'] > MAXDENTRO: b['viva'] = False
                elif b['tipo'] == 1:
                    if (v5c < b['bot'] if b['dir'] == 1 else v5c > b['top']): b['viva'] = False
                else:
                    b['fuera5'] = b['fuera5'] + 1 if (v5c < b['nivel'] if b['dir'] == 1 else v5c > b['nivel']) else 0
                    if b['fuera5'] > MAXVELAS: b['viva'] = False
            busq = [b for b in busq if b['viva']]
        # bloqueo por OB de 1H contrario
        bloqueo = False
        if dirHTF != 0 and v.get('bloqueo', True):
            for (top, bot, alc, fvg, _tg) in zzH:
                if not fvg and alc == (dirHTF == -1):
                    key = (top, bot)
                    if l <= top and h >= bot and key not in tocadas: tocadas.append(key)
                    if key in tocadas: bloqueo = True
        while len(tocadas) > 100: tocadas.pop(0)
        if bloqueo:
            busq.clear(); obs1.clear()
        desp = tCambio is None or t > tCambio
        desp5 = tCambio is None or (T5open - 5) >= tCambio
        if v.get('sin_despues'): desp = desp5 = True
        if desp and not bloqueo and not abiertas and not busq and dirHTF != 0:
            for (top, bot, alc, fvg, tg) in zz5:
                if alc == (dirHTF == 1) and not busq:
                    if fvg and v.get('sin_fvg5'): continue
                    if (not fvg) and v.get('sin_ob5'): continue
                    if v.get('solo_tag') and not tg: continue
                    mid = (top + bot) / 2
                    toca = ((l <= mid) if alc else (h >= mid)) if fvg else ((l <= top) if alc else (h >= bot))
                    key = (1 if fvg else 0, top, bot)
                    if toca and key not in usadas:
                        usadas.append(key)
                        busq.append(dict(dir=dirHTF, tipo=1 if fvg else 0, top=top, bot=bot, nivel=None, t=t, dentro5=0, fuera5=0, viva=True, tag=tg))
        if desp5 and not bloqueo and not abiertas and not busq and dirHTF != 0 and not v.get('sin_man5'):
            for (p, alto) in mm5:
                key = (2, p, p)
                if not busq and key not in usadas and (not alto if dirHTF == 1 else alto):
                    usadas.append(key)
                    busq.append(dict(dir=dirHTF, tipo=2, top=None, bot=None, nivel=p, t=t, dentro5=0, fuera5=0, viva=True, tag=True))
        while len(usadas) > 200: usadas.pop(0)
        if not busq: obs1.clear()
        # gestión de la operación abierta
        for op in list(abiertas):
            tsl = (l <= op['sl']) if op['compra'] else (h >= op['sl'])
            ttp = (h >= op['tp']) if op['compra'] else (l <= op['tp'])
            if tsl or ttp:
                op['res'] = -1.0 if tsl else RR; op['tsal'] = t; abiertas.remove(op)
        # OB de 1m → entrada
        entro = False
        for k in range(len(obs1) - 1, -1, -1):
            ob1 = obs1[k]
            ob1['ext'] = min(ob1['ext'], l) if ob1['alc'] else max(ob1['ext'], h)
            toca = (l <= ob1['top']) if ob1['alc'] else (h >= ob1['bot'])
            inval = (c < ob1['bot']) if ob1['alc'] else (c > ob1['top'])
            if l <= ob1['top'] and h >= ob1['bot']: ob1['dentro'] += 1
            entra = (ob1['tocado'] or toca) and ((c > ob1['top']) if ob1['alc'] else (c < ob1['bot']))
            borrar = False
            if inval or ob1['dentro'] > MAXDENTRO:
                borrar = True
            elif entra and dirHTF == (1 if ob1['alc'] else -1):
                buf = v.get('buf', 0.0)
                sl = (ob1['ext'] - buf) if ob1['alc'] else (ob1['ext'] + buf); riesgo = (c - sl) if ob1['alc'] else (sl - c)
                if riesgo > 0:
                    tp = c + RR * riesgo if ob1['alc'] else c - RR * riesgo
                    b0 = busq[0] if busq else None
                    op = dict(j=j, t=t, compra=ob1['alc'], ent=c, sl=sl, tp=tp, riesgo=riesgo, spread=S1[j] * 0.01,
                              zona=(['ob5', 'fvg5', 'man5'][b0['tipo']] if b0 else '?'), t_zona=(b0['t'] if b0 else None),
                              why1h=dirWhy, tag=(b0.get('tag') if b0 else None), ob1_size=ob1['top'] - ob1['bot'], ob1_t=ob1['t'], res=None, tsal=None)
                    abiertas.append(op); trades.append(op); entro = True
                borrar = True
            else:
                ob1['tocado'] = ob1['tocado'] or toca
            if borrar: obs1.pop(k)
            if entro: break
        if entro:
            busq.clear(); obs1.clear()
        # vela de 5m construida
        if nueva5: v5h = h; v5l = l
        else:
            v5h = h if v5h is None else max(v5h, h); v5l = l if v5l is None else min(v5l, l)
        v5c = c
        # OB de 1m nuevos
        hayC = any(b['dir'] == 1 for b in busq); hayV = any(b['dir'] == -1 for b in busq)
        if rIdx is not None and c > rO:
            if hayC:
                obs1.append(dict(top=rO, bot=rC, alc=True, tocado=False, dentro=0, ext=min(L1[rIdx:j + 1]), t=t))
            rIdx = None
        if vIdx is not None and c < vO:
            if hayV:
                obs1.append(dict(top=vC, bot=vO, alc=False, tocado=False, dentro=0, ext=max(H1[vIdx:j + 1]), t=t))
            vIdx = None
        if c < o: rIdx = j; rO = o; rC = c
        if c > o: vIdx = j; vO = o; vC = c
    return trades

def excursion(tr, maxbars=3000):
    """MFE (en R) antes de tocar el SL, recorriendo las velas de 1m después de la entrada."""
    T1, O1, H1, L1, C1, S1 = DATA['m1']
    j0 = tr['j']; sl = tr['sl']; e = tr['ent']; R = tr['riesgo']; mfe = 0.0
    for j in range(j0 + 1, min(len(T1), j0 + maxbars)):
        h, l = H1[j], L1[j]
        if tr['compra']:
            if l <= sl: break
            mfe = max(mfe, (h - e) / R)
        else:
            if h >= sl: break
            mfe = max(mfe, (e - l) / R)
    return mfe

if __name__ == '__main__':
    DATA = {k: load(k + '.csv') for k in ('h1', 'm5', 'm1')}
    M5 = {}; MH = {}
    for md in (MAXDIST,):
        M5[md] = motor(*DATA['m5'][:5], maxdist=md)
        MH[md] = motor(*DATA['h1'][:5], maxdist=md)
    import pickle
    tr = run()
    for x in tr: x['mfe'] = excursion(x)
    pickle.dump(dict(trades=tr, wh=MH[MAXDIST][3], dh=MH[MAXDIST][0], TH=DATA['h1'][0]), open('res.pkl', 'wb'))
    n = len(tr); w = sum(1 for x in tr if x['res'] == RR); ls = sum(1 for x in tr if x['res'] == -1)
    print('trades', n, 'ganadas', w, 'perdidas', ls, 'abiertas', n - w - ls)
