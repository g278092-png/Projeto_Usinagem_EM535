# -*- coding: utf-8 -*-
"""Memoria de calculo - EM535A - engrenagem m = 6, z = 24 (desenho PROTEC), aco SAE 8620.

Metodologia das aulas de EM535 (Profa. Milla Gomes):
  Aula 2 / 13 : cinematica e tempos (tc = lf / vf; integracao quando n varia)
  Aula 6 / 6_1: Kienzle  Fc = Ks1 . h^(1-z) . b  (8620: Ks1 = 2100 N/mm2, 1-z = 0,74); desgaste ate +30 %
  Aula 6      : Pm = Pc / eta
  Aula 17     : fresamento  Ksm = Ks1 . hm^-z ;  Pc = Ksm . ae . ap . vf / 60e6
  Aula 19     : furacao (Kronenberg / Daar)
Uso:  python memoria_de_calculo.py resultados.json
"""
import json, math, sys

R = lambda x, n=3: round(x, n)
KS1, UMZ = 2100.0, 0.74
Z_K = 1 - UMZ
DESG = 1.30
ETA = {"torno": 0.80, "fresadora": 0.70, "cu": 0.80, "ret_plana": 0.75, "ret_int": 0.80, "prensa": 0.70}
PNOM = {"torno": 9.0, "fresadora": 5.5, "cu": 18.5, "ret_plana": 4.0}

def fc_kienzle(h, b):
    return KS1 * h ** UMZ * b

def ks(h):
    return KS1 * h ** (-Z_K)

def pc_kw(fc, vc):
    return fc * vc / 60e3

out, ops = {}, {}

# ------------------------------------------------------------------ geometria (desenho PROTEC)
m, z, alpha = 6.0, 24, math.radians(20)
d, da = m * z, m * z + 2 * m
h_dente = 13.0                      # ha = m = 6 ; hf = 1,167 m = 7
rf = (da - 2 * h_dente) / 2         # 65 mm
db = d * math.cos(alpha)
inv = lambda a: math.tan(a) - a
k_med = 3
Wk = m * math.cos(alpha) * (math.pi * (k_med - 0.5) + z * inv(alpha))
s_prim = math.pi * m / 2
L_aro, L_cubo, alma = 48.0, 51.0, 14.0
rebaixo = (L_aro - alma) / 2        # 17 mm a partir da face do aro
SR = 0.15                           # sobremetal de retifica por face do cubo
L_cubo_t = L_cubo + 2 * SR          # 51,3 torneado
L_bruto = 58.0
S_face = (L_bruto - L_cubo_t) / 2   # 3,35 por face

rp_, ra_, rb_ = d / 2, da / 2, db / 2
def meia_esp(r):
    r = max(r, rb_)
    return s_prim / (2 * rp_) + inv(alpha) - inv(math.acos(rb_ / r))

def area_dente(r1, r2, n=4000):
    A, dr = 0.0, (r2 - r1) / n
    for i in range(n):
        r = r1 + (i + 0.5) * dr
        A += max(0.0, 2 * meia_esp(r)) * r * dr
    return A

def area_vao(r1, r2):
    return (math.pi * (r2 ** 2 - r1 ** 2) - z * area_dente(r1, r2)) / z

ae_desb = 2.1 * m                   # catalogo ZPS-FN: ae = 2,1 m por passe
A_vao = area_vao(rf, ra_)
sobremetal_flanco = (h_dente - ae_desb) * math.tan(alpha)
A_desb = area_vao(ra_ - ae_desb, ra_) - 2 * sobremetal_flanco * ae_desb
A_acab = A_vao - A_desb
out["geometria"] = dict(d=d, da=da, df=2 * rf, db=R(db, 2), Wk=R(Wk, 2), A_vao=R(A_vao, 1), A_desb=R(A_desb, 1),
                        A_acab=R(A_acab, 1), sobremetal_flanco=R(sobremetal_flanco, 3), L_aro=L_aro, L_cubo=L_cubo,
                        rebaixo=rebaixo, L_bruto=L_bruto, S_face=S_face)

# massa
rho = 7.85e-6
V_bruto = math.pi / 4 * 160 ** 2 * L_bruto
V = math.pi / 4 * 156 ** 2 * L_aro
V -= 2 * math.pi / 4 * (110 ** 2 - 46 ** 2) * rebaixo
V += 2 * math.pi / 4 * 46 ** 2 * 1.5
V -= math.pi / 4 * 25 ** 2 * L_cubo + 8 * (16 - 12.5) * L_cubo
V -= 4 * (39 * math.radians(45) * 18 + math.pi * 81) * alma
V -= z * A_vao * L_aro
out["massas"] = dict(m_bruto=R(V_bruto * rho, 2), m_final=R(V * rho, 2), aproveitamento=R(V / V_bruto * 100, 1),
                     V_cavaco=R((V_bruto - V) / 1e3, 0))

# ------------------------------------------------------------------ torno ROMI Centur 30D (cabecote A2-6")
NMAX, TMAX = 3000.0, 140.0
def n_de(vc, D):
    return 1000 * vc / (math.pi * D)

def p_disp(n):
    return min(PNOM["torno"], TMAX * 2 * math.pi * n / 60 / 1000)

def t_face_css(R_ext, R_int, f, vc):
    """faceamento com vc constante: t = pi (R^2 - r_lim^2)/(1000 f vc) + (r_lim - R_int)/(f nmax)"""
    r_lim = 1000 * vc / (2 * math.pi * NMAX)
    if R_int >= r_lim:
        return math.pi * (R_ext ** 2 - R_int ** 2) / (1000 * f * vc)
    return math.pi * (R_ext ** 2 - r_lim ** 2) / (1000 * f * vc) + (r_lim - R_int) / (f * NMAX)

def torneamento(nome, ap, f, vc, kr, D, lf=None, face=None):
    h, b = f * math.sin(math.radians(kr)), ap / math.sin(math.radians(kr))
    fc = fc_kienzle(h, b)
    n = min(n_de(vc, D), NMAX)
    vcr = math.pi * D * n / 1000
    pc = pc_kw(fc, vcr)
    pm = pc * DESG / ETA["torno"]
    r = dict(ap=ap, f=f, vc=R(vcr, 0), D=D, kr=kr, h=R(h, 4), b=R(b, 3), Ks=R(fc / (ap * f), 0), Fc=R(fc, 0),
             n=R(n, 0), vf=R(f * n, 1), Pc=R(pc, 2), Pc_desg=R(pc * DESG, 2), Pm=R(pm, 2), Pdisp=R(p_disp(n), 2),
             M=R(pm * 1e3 / (2 * math.pi * n / 60), 0))
    if face:
        r["tc"] = R(t_face_css(face[0], face[1], f, vc), 3)
    else:
        r["lf"] = lf; r["tc"] = R(lf / (f * n), 3)
    ops[nome] = r
    return r

# verificacao com os valores iniciais do catalogo
verif = {}
def verifica(nome, ap, f, vc, kr, D):
    fc = fc_kienzle(f * math.sin(math.radians(kr)), ap / math.sin(math.radians(kr)))
    n = min(n_de(vc, D), NMAX)
    pm = pc_kw(fc, math.pi * D * n / 1000) * DESG / ETA["torno"]
    verif[nome] = dict(ap=ap, f=f, vc=vc, n=R(n, 0), Pm=R(pm, 1), Pdisp=R(p_disp(n), 1),
                       M=R(pm * 1e3 / (2 * math.pi * n / 60), 0))
verifica("Faceamento de desbaste", 2.85, 0.30, 335, 95, 160)
verifica("Torneamento externo de desbaste", 1.5, 0.30, 335, 95, 160)

# Operacao 20 - lado A
for i in (1, 2):
    torneamento(f"20.1 faceamento passe {i}", 1.425, 0.22, 300, 95, 160, face=(82, 0))
torneamento("20.2 torneamento externo", 1.5, 0.22, 280, 95, 160, lf=1.65 + 34 + 2)
torneamento("20.3 degrau do aro", 1.15, 0.22, 300, 95, 157, face=(80, 23.5))
torneamento("20.4 acabamento", 0.5, 0.15, 400, 93, 157, face=(80.5, 0))
ops["20.4 acabamento"]["tc"] = R(ops["20.4 acabamento"]["tc"] + (1.65 + 34 + 2) / (0.15 * n_de(400, 157)), 3)

# furacao Ø23 - CoroDrill 880
D = 23.0
pc_cat = ks(0.13 * math.sin(math.radians(88))) * 0.13 * D * 200 / 240e3
verif["Furação Ø23"] = dict(ap=11.5, f=0.13, vc=200, n=R(n_de(200, D), 0), Pm=R(pc_cat * DESG / ETA["torno"], 1),
                            Pdisp=9.0, M=None)
fn, vc = 0.09, 150.0
h = fn * math.sin(math.radians(88))
n = n_de(vc, D)
pc = ks(h) * fn * D * vc / 240e3
lf_furo = (L_bruto - S_face) + 2 + 2
Mt_kron = 37.9 * D ** 1.87 * fn ** 0.77 * 9.81 / 1000
Ff_daar = 33.4 * D ** 1.21 * fn ** 0.60 * 9.81
ops["20.5 furacao"] = dict(D=D, f=fn, vc=vc, h=R(h, 4), Ks=R(ks(h), 0), n=R(n, 0), vf=R(fn * n, 1),
                           Pc=R(pc, 2), Pc_desg=R(pc * DESG, 2), Pm=R(pc * DESG / ETA["torno"], 2), Pdisp=R(p_disp(n), 2),
                           Mt=R(pc * 1e3 / (2 * math.pi * n / 60), 1), Mt_kron=R(Mt_kron, 1), Ff_daar=R(Ff_daar, 0),
                           lf=R(lf_furo, 2), tc=R(lf_furo / (fn * n), 3))

# mandrilamento Ø23 -> Ø24,5
Dm, ap, f = 24.5, 0.75, 0.10
n = NMAX
vcm = math.pi * Dm * n / 1000
h, b = f * math.sin(math.radians(93)), ap / math.sin(math.radians(93))
fc = fc_kienzle(h, b)
pc = pc_kw(fc, vcm)
ops["20.6 mandrilamento"] = dict(ap=ap, f=f, vc=R(vcm, 0), D=Dm, h=R(h, 4), b=R(b, 3), Fc=R(fc, 0), n=n, vf=R(f * n, 0),
                                 Pc=R(pc, 2), Pc_desg=R(pc * DESG, 2), Pm=R(pc * DESG / ETA["torno"], 2), Pdisp=9.0,
                                 Rmax=R(f ** 2 / (8 * 0.4) * 1000, 2), lf=R(lf_furo, 2), tc=R(lf_furo / (f * n), 3))

# rebaixo frontal (canal frontal, CW = 5 mm)
fc0 = fc_kienzle(0.12, 5.0)
n0 = n_de(180, 105)
pm0 = pc_kw(fc0, 180) * DESG / ETA["torno"]
verif["Rebaixo frontal"] = dict(ap=5.0, f=0.12, vc=180, n=R(n0, 0), Pm=R(pm0, 1), Pdisp=R(p_disp(n0), 1),
                                M=R(pm0 * 1e3 / (2 * math.pi * n0 / 60), 0))
CW, fg, vcg = 5.0, 0.07, 160.0
prof = rebaixo - 0.2
R_ext, R_int = 55.0, 23.0
centros, rc = [], R_ext - CW / 2
while True:
    centros.append(rc)
    if rc - CW / 2 <= R_int + 1e-9:
        break
    rc = max(rc - 4.0, R_int + CW / 2)
t_merg, merg = 0.0, []
for rc in centros:
    ng = n_de(vcg, 2 * rc)
    t = (prof + 1.0) / (fg * ng)
    t_merg += t
    merg.append((R(2 * rc, 0), R(ng, 0)))
# acabamento do contorno: parede R55 (17) + raio R3 + fundo (26) + raio R3 + parede R23 (17), f = 0,10 em n medio
perc = 17 + math.pi / 2 * (3 - 0.4) + (32 - 6) + math.pi / 2 * (3 - 0.4) + 17
n_med = n_de(vcg, 78)
t_cont = perc / (0.10 * n_med)
fc = fc_kienzle(fg, CW)
n_crit = n_de(vcg, 2 * centros[0])
pc = pc_kw(fc, vcg)
pm = pc * DESG / ETA["torno"]
ops["20.7 rebaixo"] = dict(CW=CW, f=fg, vc=vcg, prof=rebaixo, n_merg=len(centros), merg=merg, Fc=R(fc, 0),
                           Pc=R(pc, 2), Pc_desg=R(pc * DESG, 2), Pm=R(pm, 2), Pdisp=R(p_disp(n_crit), 2),
                           M=R(pm * 1e3 / (2 * math.pi * n_crit / 60), 0), n_min=R(n_crit, 0),
                           n_max=R(n_de(vcg, 2 * centros[-1]), 0), perc_contorno=R(perc, 1),
                           t_merg=R(t_merg, 3), t_cont=R(t_cont, 3), tc=R(t_merg + t_cont, 3))
ops["20.8 chanfros"] = dict(tc=0.05)

# Operacao 30 - lado B
for i in (1, 2):
    torneamento(f"30.1 faceamento passe {i}", 1.425, 0.22, 300, 95, 156, face=(80, 12.25))
torneamento("30.2 degrau do aro", 1.15, 0.22, 300, 95, 157, face=(80, 23.5))
torneamento("30.3 torneamento externo", 1.5, 0.22, 280, 95, 160, lf=16 + 2)
torneamento("30.4 acabamento", 0.5, 0.15, 400, 93, 157, face=(80.5, 12.25))
ops["30.4 acabamento"]["tc"] = R(ops["30.4 acabamento"]["tc"] + 18 / (0.15 * n_de(400, 157)), 3)
ops["30.5 rebaixo"] = dict(ops["20.7 rebaixo"])
ops["30.6 chanfros"] = dict(tc=0.05)

# ------------------------------------------------------------------ Operacao 40 - fresamento de forma (UWF 5)
Dc, zc, fz = 100.0, 12, 0.055
n_cat = n_de(15, Dc)
n = 60.0
vcf = math.pi * Dc * n / 1000
vf = fz * zc * n
def hm_tang(ae):
    c0 = 1 - 2 * ae / Dc
    phi = math.acos(c0)
    return (1 - c0) / phi * fz, math.degrees(phi), phi
hm1, phi1d, phi1 = hm_tang(ae_desb)
ae2 = h_dente - ae_desb
hm2, phi2d, _ = hm_tang(ae2)
pc1 = ks(hm1) * A_desb * vf / 60e6
pc2 = ks(hm2) * A_acab * vf / 60e6
la1 = math.sqrt(ae_desb * (Dc - ae_desb))
la2 = math.sqrt(h_dente * (Dc - h_dente))
lf1, lf2 = L_aro + la1 + 5, L_aro + la2 + 5
ops["40 dentes"] = dict(Dc=Dc, zc=zc, n_cat=R(n_cat, 1), n=n, vc=R(vcf, 1), fz=fz, vf=R(vf, 1), ae1=ae_desb, ae2=R(ae2, 1),
                        phi1=R(phi1d, 1), phi1_rad=R(phi1, 3), hm1=R(hm1, 4), hm2=R(hm2, 4), Ksm1=R(ks(hm1), 0),
                        Ksm1_tab=R(1700 * hm1 ** -0.25, 0), Ksm2=R(ks(hm2), 0), A1=R(A_desb, 1), A2=R(A_acab, 1),
                        Pc1=R(pc1, 3), Pc1_desg=R(pc1 * DESG, 3), Pm1=R(pc1 * DESG / ETA["fresadora"], 2),
                        Pc2=R(pc2, 3), Pm2=R(pc2 * DESG / ETA["fresadora"], 2),
                        M=R(pc1 * DESG * 1e3 / (2 * math.pi * n / 60), 0), la1=R(la1, 1), la2=R(la2, 1),
                        lf1=R(lf1, 1), lf2=R(lf2, 1), t1=R(lf1 / vf, 3), t2=R(lf2 / vf, 3),
                        tc=R(z * (lf1 + lf2) / vf, 1), Pdisp=PNOM["fresadora"])

# ------------------------------------------------------------------ Operacao 50 - rasgos em arco (ROMI D 800)
Df, zf, vcr = 16.0, 2, 275.0
n = n_de(vcr, Df)
fz1, ap = 0.10, 5.0
vf1 = fz1 * zf * n
hm = 2 * fz1 / math.pi
pc1 = ks(hm) * Df * ap * vf1 / 60e6
fz2, ae2 = 0.20, 1.0
phi = math.acos(1 - 2 * ae2 / Df)
vf2 = fz2 * zf * n
hm2 = (1 - math.cos(phi)) / phi * fz2
pc2 = ks(hm2) * ae2 * ap * vf2 / 60e6
niveis = [5.0, 5.0, 4.5]
arco = 39 * math.radians(45)
p1 = sum(l / math.tan(math.radians(5)) + arco for l in niveis)
p2 = len(niveis) * (40 * math.radians(45) + 38 * math.radians(45) + 2 * math.pi) + 10
ops["50 rasgos"] = dict(D=Df, z=zf, vc=vcr, n=R(n, 0), fz1=fz1, vf1=R(vf1, 0), ap=ap, hm1=R(hm, 4), Ksm1=R(ks(hm), 0),
                        Pc1=R(pc1, 2), Pc1_desg=R(pc1 * DESG, 2), Pm1=R(pc1 * DESG / ETA["cu"], 2),
                        M=R(pc1 * DESG / ETA["cu"] * 1e3 / (2 * math.pi * n / 60), 1),
                        fz2=fz2, vf2=R(vf2, 0), hex2=R(fz2 * math.sin(phi), 3), hm2=R(hm2, 4), Ksm2=R(ks(hm2), 0),
                        Pc2=R(pc2, 2), Pm2=R(pc2 * DESG / ETA["cu"], 2), arco=R(arco, 1), p1=R(p1, 0), p2=R(p2, 0),
                        tc=R(4 * (p1 / vf1 + p2 / vf2), 2), Pdisp=PNOM["cu"])

# ------------------------------------------------------------------ Operacao 60 - brochamento (passo e subida estimados)
sz, passo, Lk, vb = 0.06, 6.35, L_cubo_t, 3.0
ze = math.floor(Lk / passo) + 1
Fd = fc_kienzle(sz, 8.0)
F = ze * Fd
ops["60 brochamento"] = dict(sz=sz, passo=passo, ze=ze, Fd=R(Fd, 0), F=R(F, 0), F_desg=R(F * DESG, 0),
                             F_tf=R(F * DESG / 9810, 1), v=vb, Pc=R(F * vb / 60e3, 2), Pm=R(F * DESG * vb / 60e3 / ETA["prensa"], 2),
                             tc=R(2 * (280 + Lk + 10) / (vb * 1000), 2))

# ------------------------------------------------------------------ Operacao 90 - retificacao plana das faces do cubo
Ds, ns = 350.0, 1450.0
vs = math.pi * Ds * ns / 60000
vw, s, a1, a2 = 15.0, 8.0, 0.02, 0.005
n1 = math.ceil((SR - 0.01) / a1); n2, n3 = 2, 2
Lc = 42 + 2 * 20
Bc = 42 + 40
cursos = math.ceil(Bc / s)
t_cam = cursos * (Lc / (vw * 1000) + 0.3 / 60)
u = 40.0
Qw = a1 * s * vw * 1000 / 60
Pg = u * Qw / 1000
ops["90 retifica plana"] = dict(vs=R(vs, 1), vw=vw, s=s, a1=a1, a2=a2, n1=n1, n2=n2, n3=n3, Lc=Lc, cursos=cursos,
                                t_camada=R(t_cam, 3), tc=R(2 * (n1 + n2 + n3) * t_cam, 2), u=u, Qw=R(Qw, 0),
                                Pc=R(Pg, 2), Pc_desg=R(Pg * DESG, 2), Pm=R(Pg * DESG / ETA["ret_plana"], 2),
                                q=R(vs * 60 / vw, 0), Pdisp=PNOM["ret_plana"])

# ------------------------------------------------------------------ Operacao 100 - retificacao interna do furo
Dsi, bs, vsi, vwi = 20.0, 20.0, 30.0, 30.0
nsi = vsi * 60000 / (math.pi * Dsi)
nw = 1000 * vwi / (math.pi * 25)
fa1, fa2 = 0.5 * bs, 0.25 * bs
v1, v2 = fa1 * nw, fa2 * nw
b1, b2 = 0.005, 0.0025
c1 = math.ceil((0.25 - 0.03) / b1); c2 = math.ceil(0.03 / b2); c3 = 4
Ls = L_cubo + 2 * bs / 3 - bs
Qi = math.pi * 25 * b1 * v1 / 60
Pi = u * Qi / 1000
ops["100 retifica interna"] = dict(vs=vsi, ns=R(nsi, 0), vw=vwi, nw=R(nw, 0), q=R(vsi * 60 / vwi, 0), fa1=fa1, fa2=fa2,
                                   v1=R(v1, 0), v2=R(v2, 0), b1=b1, b2=b2, c1=c1, c2=c2, c3=c3, Ls=R(Ls, 1),
                                   tc=R(c1 * Ls / v1 + (c2 + c3) * Ls / v2, 2), Qw=R(Qi, 0), Pc=R(Pi, 2),
                                   Pc_desg=R(Pi * DESG, 2), Pm=R(Pi * DESG / ETA["ret_int"], 2))

# alternativa: fresa-caracol (ordem de grandeza)
n0 = n_de(120, 100)
out["caracol"] = dict(vc=120, fa=2.5, n0=R(n0, 0), tc=R(z * (L_aro + math.sqrt(13 * 87) + 5) / (n0 * 2.5), 1))

out["ops"] = ops
out["verif"] = verif
json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "resultados.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
for k, v in ops.items():
    print(k, {x: v[x] for x in ("Pm", "Pdisp", "M", "Pm1", "tc") if x in v})
print(out["geometria"]); print(out["massas"]); print(out["verif"]); print(out["caracol"])
