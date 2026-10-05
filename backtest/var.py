import bt, pickle
bt.DATA = {k: bt.load(k + '.csv') for k in ('h1', 'm5', 'm1')}
bt.M5 = {}; bt.MH = {}
for md in (2.0, 1000.0):
    bt.M5[md] = bt.motor(*bt.DATA['m5'][:5], maxdist=md)
    bt.MH[md] = bt.motor(*bt.DATA['h1'][:5], maxdist=md)
def s(name, tr):
    tr = [x for x in tr if x['res'] is not None]
    for x in tr: x['mfe'] = bt.excursion(x)
    n = len(tr); w = sum(x['res'] > 0 for x in tr)
    Rc = sum(x['res'] - x['spread']/x['riesgo'] for x in tr)
    r1 = sum(x['mfe'] >= 1 for x in tr)/n*100
    print(f"{name:34s} n={n:5d} acierto1:3={100*w/n:5.1f}%  llega1R={r1:5.1f}%  R_con_spread/op={Rc/n:+.3f}")
s('actual', bt.run())
s('sin bloqueo OB 1H', bt.run(dict(bloqueo=False)))
s('sin regla "después de 1H"', bt.run(dict(sin_despues=True)))
s('sin límite de distancia manip', bt.run(dict(maxdist=1000.0)))
s('solo manipulación 5m', bt.run(dict(sin_ob5=True, sin_fvg5=True)))
s('solo OB 5m', bt.run(dict(sin_man5=True, sin_fvg5=True)))
s('solo vacío 5m', bt.run(dict(sin_man5=True, sin_ob5=True)))
