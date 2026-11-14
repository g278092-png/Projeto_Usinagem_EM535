# -*- coding: utf-8 -*-
"""Memoria de calculo - EM535A - engrenagem m = 6, z = 24 (desenho PROTEC), aco SAE 8620.
Versao revisada: torno ROMI Centur 35D, f = 0,28 mm/volta no desbaste, nova ordem das
sub-operacoes 20 e 30, rebaixo com sobremetal de 0,3 mm, profundidade final do dente 13,5 mm.

Metodologia das aulas de EM535 (Profa. Milla Gomes):
  Aula 2  (slide 36) : n = 1000 vc/(pi d); vf = f n; tc = lf/vf
  Aula 13 (slides 9 e 13): tempos; integracao quando n varia (faceamento com vc constante)
  Aula 6  (slide 19) : Pm = Pc/eta (eta = 0,65-0,85 engrenagens/correias; 0,80-0,85 motor acoplado)
  Aula 6_1 (slides 25 e 26): Kienzle Fc = Ks1 h^(1-z) b ; 8620: Ks1 = 2100 N/mm2, 1-z = 0,74 ; +30 % desgaste
  Aula 17 (slides 25 a 28): fresamento Ksm = Ks1 hm^-z ; Pc = Ksm ae ap vf / 60e6
  Aula 19 (slide 39) : Kronenberg Mt = C1 D^x1 f^y1 (aco 1025)
Uso:  python memoria_de_calculo.py resultados.json
"""
import json, math, sys

R = lambda x, n=3: round(x, n)
KS1, UMZ = 2100.0, 0.74
Z_K = 1 - UMZ
DESG = 1.30
ETA = {"torno": 0.80, "fresadora": 0.70, "cu": 0.80, "ret_plana": 0.75, "ret_int": 0.80, "brochadeira": 0.70}
PNOM = {"torno": 11.0, "fresadora": 5.5, "cu": 18.5, "ret_plana": 4.0, "brochadeira": 2.2}

def fc_kienzle(h, b):
    return KS1 * h ** UMZ * b

def ks(h):
    return KS1 * h ** (-Z_K)

def pc_kw(fc, vc):
    return fc * vc / 60e3

out, ops = {}, {}

# ------------------------------------------------------------------ geometria
m, z, alpha = 6.0, 24, math.radians(20)
d, da = m * z, m * z + 2 * m
h_dente = 2.25 * m                  # 13,5 mm = profundidade do perfil da fresa ZPS-FN 890070.06004
rf = (da - 2 * h_dente) / 2
db = d * math.cos(alpha)
inv = lambda a: math.tan(a) - a
k_med = 3
Wk = m * math.cos(alpha) * (math.pi * (k_med - 0.5) + z * inv(alpha))
s_prim = math.pi * m / 2
L_aro, L_cubo, alma = 48.0, 51.0, 14.0
rebaixo = (L_aro - alma) / 2        # 17 mm a partir da face do aro
SR = 0.15
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

ae_desb = 2.1 * m                   # ZPS-FN, grupo P.2: A_e = 2,1 x m por passe
A_vao = area_vao(rf, ra_)
sobremetal_flanco = (h_dente - ae_desb) * math.tan(alpha)
A_desb = area_vao(ra_ - ae_desb, ra_) - 2 * sobremetal_flanco * ae_desb
A_acab = A_vao - A_desb
out["geometria"] = dict(d=d, da=da, df=R(2 * rf, 2), db=R(db, 2), h_dente=h_dente, Wk=R(Wk, 3), A_vao=R(A_vao, 1),
                        A_desb=R(A_desb, 1), A_acab=R(A_acab, 1), L_aro=L_aro, L_cubo=L_cubo, rebaixo=rebaixo,
                        L_bruto=L_bruto, S_face=S_face,
                        W_se_13mm=R(Wk + 2 * (13.5 - 13.0) * math.tan(alpha) * math.cos(alpha), 3))

rho = 7.85e-6
V_bruto = math.pi / 4 * 160 ** 2 * L_bruto
V = math.pi / 4 * 156 ** 2 * L_aro
V -= 2 * math.pi / 4 * (110 ** 2 - 46 ** 2) * rebaixo
V += 2 * math.pi / 4 * 46 ** 2 * 1.5
V -= math.pi / 4 * 25 ** 2 * L_cubo + 8 * (16 - 12.5) * L_cubo
V -= 4 * (39 * math.radians(45) * 18 + math.pi * 81) * alma
V -= z * A_vao * L_aro
out["massas"] = dict(m_bruto=R(V_bruto * rho, 2), m_final=R(V * rho, 2), removido=R((1 - V / V_bruto) * 100, 0))

# ------------------------------------------------------------------ torno
TORNOS = {"35D": dict(P=11.0, T=320.0, nmax=3000.0), "30D": dict(P=9.0, T=140.0, nmax=4000.0)}

def n_de(vc, D):
    return 1000 * vc / (math.pi * D)

def make_lathe(tag):
    Pn, Tm, NMAX = TORNOS[tag]["P"], TORNOS[tag]["T"], TORNOS[tag]["nmax"]
    def p_disp(n):
        return min(Pn, Tm * 2 * math.pi * n / 60 / 1000)
    def t_face(R_ext, R_int, f, vc):
        r_lim = 1000 * vc / (2 * math.pi * NMAX)
        if R_int >= r_lim:
            return math.pi * (R_ext ** 2 - R_int ** 2) / (1000 * f * vc)
        return math.pi * (R_ext ** 2 - r_lim ** 2) / (1000 * f * vc) + (r_lim - R_int) / (f * NMAX)
    def turn(ap, f, vc, kr, D, lf=None, face=None, extra=0.0):
        h, b = f * math.sin(math.radians(kr)), ap / math.sin(math.radians(kr))
        fc = fc_kienzle(h, b)
        n = min(n_de(vc, D), NMAX)
        vcr = math.pi * D * n / 1000
        pc = pc_kw(fc, vcr)
        pm = pc * DESG / ETA["torno"]
        r = dict(ap=ap, f=f, vc=R(vcr, 0), D=D, kr=kr, h=R(h, 4), b=R(b, 3), Fc=R(fc, 0), n=R(n, 0),
                 vf=R(f * n, 1), Pc=R(pc, 2), Pm=R(pm, 2), Pdisp=R(p_disp(n), 2),
                 util=R(pm / p_disp(n) * 100, 0), T=R(pm * 1e3 / (2 * math.pi * n / 60), 0))
        if face:
            r["tc"] = t_face(face[0], face[1], f, vc)
        else:
            r["lf"] = lf
            r["tc"] = lf / (f * n)
        r["tc"] = R(r["tc"] + extra, 3)
        return r
    return p_disp, t_face, turn, NMAX

def plano_torno(tag, f_desb, f_reb):
    p_disp, t_face, turn, NMAX = make_lathe(tag)
    o = {}
    lf_ext_A = 1.65 + 34 + 2                       # 37,65 mm
    lf_ext_B = 16 + 2                              # 13,65 restantes + 2,35 de sobreposicao + 2 de aproximacao
    # ---- operacao 20
    p = turn(1.425, f_desb, 300, 95, 160, face=(82, 0))
    p["tc"] = R(2 * p["tc"], 3); o["20.1"] = p
    o["20.2"] = turn(1.5, f_desb, 280, 95, 160, lf=lf_ext_A)
    o["20.3"] = turn(1.15, f_desb, 300, 95, 157, face=(80, 23.5))
    # furacao O23 (CoroDrill 880, KAPR 88 graus)
    D, fn, vc = 23.0, 0.09, 150.0
    h = fn * math.sin(math.radians(88))
    n = min(n_de(vc, D), NMAX)
    pc = ks(h) * fn * D * vc / 240e3
    pm = pc * DESG / ETA["torno"]
    lf_furo = (L_bruto - S_face) + 2 + 2
    o["20.4"] = dict(D=D, f=fn, vc=vc, h=R(h, 4), Ks=R(ks(h), 0), n=R(n, 0), vf=R(fn * n, 1), Pc=R(pc, 2), Pm=R(pm, 2),
                     Pdisp=R(p_disp(n), 2), util=R(pm / p_disp(n) * 100, 0), T=R(pm * 1e3 / (2 * math.pi * n / 60), 0),
                     Mt_kienzle=R(pc * 1e3 / (2 * math.pi * n / 60), 1),
                     Mt_kron=R(37.9 * D ** 1.87 * fn ** 0.77 * 9.81 / 1000, 1), lf=R(lf_furo, 2), tc=R(lf_furo / (fn * n), 3))
    # rebaixo: 8 mergulhos, sobremetal 0,3 mm nas paredes e no fundo
    CW, vcg, sob = 5.0, 160.0, 0.3
    c_ext, c_int = 55 - sob - CW / 2, 23 + sob + CW / 2
    nm = 8
    passo = (c_ext - c_int) / (nm - 1)
    centros = [c_ext - i * passo for i in range(nm)]
    prof = [rebaixo - 3 - sob if i in (0, nm - 1) else rebaixo - sob for i in range(nm)]
    t_merg = sum((p_ + 1.0) / (f_reb * n_de(vcg, 2 * c)) for c, p_ in zip(centros, prof))
    perc = 17 + math.pi / 2 * (3 - 0.4) + (32 - 6) + math.pi / 2 * (3 - 0.4) + 17
    t_cont = perc / (0.10 * n_de(vcg, 78))
    fcg = fc_kienzle(f_reb, CW)
    pcg = pc_kw(fcg, vcg)
    pmg = pcg * DESG / ETA["torno"]
    n1 = n_de(vcg, 2 * centros[0])
    reb = dict(CW=CW, f=f_reb, vc=vcg, passo=R(passo, 2), centros_D=[R(2 * c, 1) for c in centros], prof=prof,
               n=[R(n_de(vcg, 2 * c), 0) for c in centros], Fc=R(fcg, 0), Pc=R(pcg, 2), Pm=R(pmg, 2),
               Pdisp=R(p_disp(n1), 2), util=R(pmg / p_disp(n1) * 100, 0), T=R(pmg * 1e3 / (2 * math.pi * n1 / 60), 0),
               perc_contorno=R(perc, 1), t_merg=R(t_merg, 3), t_cont=R(t_cont, 3))
    o["20.5"] = dict(reb, tc=R(t_merg, 3))
    o["20.6"] = turn(0.5, 0.15, 400, 93, 157, face=(80.5, 10.5), extra=lf_ext_A / (0.15 * n_de(400, 157)))
    o["20.6"]["Rmax_um"] = R(0.15 ** 2 / (8 * 0.4) * 1000, 1)
    o["20.7"] = dict(f=0.10, vc=vcg, perc=R(perc, 1), tc=R(t_cont, 3))
    # mandrilamento O23 -> O24,5 (limitado a nmax)
    Dm, ap, f = 24.5, 0.75, 0.10
    n = NMAX
    vcm = math.pi * Dm * n / 1000
    h, b = f * math.sin(math.radians(93)), ap / math.sin(math.radians(93))
    fc = fc_kienzle(h, b)
    pc = pc_kw(fc, vcm)
    pm = pc * DESG / ETA["torno"]
    o["20.8"] = dict(ap=ap, f=f, vc=R(vcm, 0), D=Dm, h=R(h, 4), Fc=R(fc, 0), n=n, vf=R(f * n, 0), Pc=R(pc, 2), Pm=R(pm, 2),
                     Pdisp=R(p_disp(n), 2), util=R(pm / p_disp(n) * 100, 0), T=R(pm * 1e3 / (2 * math.pi * n / 60), 0),
                     Rmax_um=R(f ** 2 / (8 * 0.4) * 1000, 1), lf=R(lf_furo, 2), tc=R(lf_furo / (f * n) + 0.05, 3))
    # ---- operacao 30
    p = turn(1.425, f_desb, 300, 95, 160, face=(82, 11.25))
    p["tc"] = R(2 * p["tc"], 3); o["30.1"] = p
    o["30.2"] = turn(1.5, f_desb, 280, 95, 160, lf=lf_ext_B)
    o["30.3"] = turn(1.15, f_desb, 300, 95, 157, face=(80, 23.5))
    o["30.4"] = dict(reb, tc=R(t_merg, 3))
    o["30.5"] = turn(0.5, 0.15, 400, 93, 157, face=(80.5, 11.25), extra=lf_ext_B / (0.15 * n_de(400, 157)))
    o["30.6"] = dict(f=0.10, vc=vcg, perc=R(perc, 1), tc=R(t_cont, 3))
    o["30.7"] = dict(tc=0.05)
    tc20 = sum(o[k]["tc"] for k in o if k.startswith("20."))
    tc30 = sum(o[k]["tc"] for k in o if k.startswith("30."))
    return o, R(tc20, 2), R(tc30, 2)

ops35, tc20, tc30 = plano_torno("35D", 0.28, 0.12)
ops.update(ops35)
_, t20_30D, t30_30D = plano_torno("30D", 0.22, 0.07)
p30, _, turn30, _ = make_lathe("30D")
ext30 = turn30(1.5, 0.22, 280, 95, 160, lf=37.65)
out["comparacao_30D"] = dict(tc_torno=R(t20_30D + t30_30D, 1), ext=ext30)
out["tc_torno_35D"] = R(tc20 + tc30, 2)

# verificacao com os valores iniciais de catalogo no 35D
p_disp, _, _, NMAX = make_lathe("35D")
verif = {}
def verifica(nome, ap, f, vc, kr, D):
    fc = fc_kienzle(f * math.sin(math.radians(kr)), ap / math.sin(math.radians(kr)))
    n = min(n_de(vc, D), NMAX)
    pm = pc_kw(fc, math.pi * D * n / 1000) * DESG / ETA["torno"]
    verif[nome] = dict(ap=ap, f=f, vc=vc, n=R(n, 0), Pm=R(pm, 1), Pdisp=R(p_disp(n), 1))
verifica("Faceamento de desbaste (passe unico)", 2.85, 0.30, 335, 95, 160)
verifica("Torneamento externo de desbaste", 1.5, 0.30, 335, 95, 160)
fc0 = fc_kienzle(0.12, 5.0); n0 = n_de(180, 104.4)
verif["Rebaixo frontal"] = dict(ap=5.0, f=0.12, vc=180, n=R(n0, 0), Pm=R(pc_kw(fc0, 180) * DESG / ETA["torno"], 1), Pdisp=R(p_disp(n0), 1))
D = 23.0
hc = 0.11 * math.sin(math.radians(88))
pcc = ks(hc) * 0.11 * D * 200 / 240e3
verif["Furacao O23"] = dict(ap=11.5, f=0.11, vc=200, n=R(n_de(200, D), 0), Pm=R(pcc * DESG / ETA["torno"], 1), Pdisp=11.0)
out["verif"] = verif

# ------------------------------------------------------------------ Operacao 40 - fresamento de forma (UWF 5)
Dc, zc, fz = 100.0, 12, 0.055
n = 60.0
vcf = math.pi * Dc * n / 1000
vf = fz * zc * n
def hm_tang(ae):
    c0 = 1 - 2 * ae / Dc
    phi = math.acos(c0)
    return (1 - c0) / phi * fz, math.degrees(phi)
hm1, phi1 = hm_tang(ae_desb)
ae2 = h_dente - ae_desb
hm2, phi2 = hm_tang(h_dente)
pc1 = ks(hm1) * A_desb * vf / 60e6
pc2 = ks(hm2) * A_acab * vf / 60e6
pc1_a17 = 1700 * hm1 ** -0.25 * A_desb * vf / 60e6
la1 = math.sqrt(ae_desb * (Dc - ae_desb))
la2 = math.sqrt(h_dente * (Dc - h_dente))
lf1, lf2 = L_aro + la1 + 5, L_aro + la2 + 5
ops["40"] = dict(Dc=Dc, zc=zc, n_cat=R(n_de(15, Dc), 1), n=n, vc=R(vcf, 1), fz=fz, vf=R(vf, 1), ae1=ae_desb, ae2=R(ae2, 1),
                 phi1=R(phi1, 1), hm1=R(hm1, 4), hm2=R(hm2, 4), A1=R(A_desb, 1), A2=R(A_acab, 1),
                 Pc1=R(pc1, 3), Pm1=R(pc1 * DESG / ETA["fresadora"], 2), Pc1_aula17=R(pc1_a17, 3),
                 Pc2=R(pc2, 3), Pm2=R(pc2 * DESG / ETA["fresadora"], 2), Pdisp=PNOM["fresadora"],
                 util=R(pc1 * DESG / ETA["fresadora"] / PNOM["fresadora"] * 100, 0),
                 T=R(pc1 * DESG / ETA["fresadora"] * 1e3 / (2 * math.pi * n / 60), 0),
                 la1=R(la1, 1), la2=R(la2, 1), lf1=R(lf1, 1), lf2=R(lf2, 1), tc=R(z * (lf1 + lf2) / vf, 1),
                 t_corte_lote=R(10 * z * (lf1 + lf2) / vf, 0))

# ------------------------------------------------------------------ Operacao 50 - rasgos em arco (ROMI D 800)
Df, zf, vcr = 16.0, 2, 275.0
n = n_de(vcr, Df)
fz1, ap = 0.10, 5.0
vf1 = fz1 * zf * n
hm = 2 * fz1 / math.pi
pc1 = ks(hm) * Df * ap * vf1 / 60e6
pc1_a17 = 1700 * hm ** -0.25 * Df * ap * vf1 / 60e6
fz2, ae2r = 0.20, 1.0
phi = math.acos(1 - 2 * ae2r / Df)
vf2 = fz2 * zf * n
hm2 = (1 - math.cos(phi)) / phi * fz2
pc2 = ks(hm2) * ae2r * ap * vf2 / 60e6
niveis = [5.0, 5.0, 4.5]
arco = 39 * math.radians(45)
p1 = sum(l / math.tan(math.radians(5)) + arco for l in niveis)
p2 = len(niveis) * (40 * math.radians(45) + 38 * math.radians(45) + 2 * math.pi) + 10
pm1 = pc1 * DESG / ETA["cu"]
ops["50"] = dict(D=Df, z=zf, vc=vcr, n=R(n, 0), fz1=fz1, vf1=R(vf1, 0), ap=ap, hm1=R(hm, 4), Pc1=R(pc1, 2), Pm1=R(pm1, 2),
                 Pc1_aula17=R(pc1_a17, 2), Pm1_aula17=R(pc1_a17 * DESG / ETA["cu"], 2),
                 util=R(pm1 / PNOM["cu"] * 100, 0), T=R(pm1 * 1e3 / (2 * math.pi * n / 60), 1),
                 fz2=fz2, vf2=R(vf2, 0), hex2=R(fz2 * math.sin(phi), 3), hm2=R(hm2, 4), Pc2=R(pc2, 2),
                 Pm2=R(pc2 * DESG / ETA["cu"], 2), p1=R(p1, 0), p2=R(p2, 0), tc=R(4 * (p1 / vf1 + p2 / vf2), 2),
                 Pdisp=PNOM["cu"])

# ------------------------------------------------------------------ Operacao 60 - brochamento
sz, passo, Lk = 0.06, 6.35, L_cubo_t
ze = math.floor(Lk / passo) + 1
Fd = fc_kienzle(sz, 8.0)
F = ze * Fd
v_b = 0.024                                     # m/s (BM25: 24 mm/s)
curso = 280 + Lk + 10                           # parte dentada estimada + cubo + folga
pcb = F * v_b / 1e3
ops["60"] = dict(sz=sz, passo=passo, ze=ze, Fd=R(Fd, 0), F=R(F, 0), F_desg=R(F * DESG, 0), F_tf=R(F * DESG / 9810, 2),
                 F_tf_sem=R(F / 9810, 2), Pc=R(pcb, 2), Pm=R(pcb * DESG / ETA["brochadeira"], 2),
                 util_P=R(pcb * DESG / ETA["brochadeira"] / PNOM["brochadeira"] * 100, 0),
                 curso=R(curso, 1), tc=R(3 * curso / (v_b * 60e3), 2),
                 F_dumont_lbf=4340, F_dumont_kN=R(4340 * 4.448 / 1000, 1),
                 F_dumont_513_kN=R(4340 * 4.448 / 1000 * Lk / 63.5, 1))

# ------------------------------------------------------------------ Operacao 90 - retificacao plana
Ds, ns = 350.0, 1450.0
vs = math.pi * Ds * ns / 60000
vw, s, a1, a2 = 15.0, 8.0, 0.02, 0.005
n1 = math.ceil((SR - 0.01) / a1); n2, n3 = 2, 2
L_contato = 46 - 2 * 2                              # O46 menos o chanfro de 2 mm
Lc = L_contato + 2 * 20
cursos = math.ceil((L_contato + 40) / s)
t_inv = 0.3 / 60
t_cam = cursos * (Lc / (vw * 1000) + t_inv)
u = 40.0
Qw = a1 * s * vw * 1000 / 60
Pg = u * Qw / 1000
ops["90"] = dict(vs=R(vs, 1), vw=vw, s=s, a1=a1, a2=a2, n1=n1, n2=n2, n3=n3, L_contato=L_contato, Lc=Lc, cursos=cursos,
                 t_inv_s=0.3, t_camada=R(t_cam, 4), tc=R(2 * (n1 + n2 + n3) * t_cam, 2), u=u, Qw=R(Qw, 0),
                 Pc=R(Pg, 2), Pm=R(Pg * DESG / ETA["ret_plana"], 2), Pdisp=PNOM["ret_plana"],
                 util=R(Pg * DESG / ETA["ret_plana"] / PNOM["ret_plana"] * 100, 0))

# ------------------------------------------------------------------ Operacao 100 - retificacao interna
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
Pmi = Pi * DESG / ETA["ret_int"]
P_eixo = min(6.0, 1.8 * 2 * math.pi * nsi / 60 / 1000)   # eixo de referencia O100 mm: 6,0 kW e 1,8 N.m
ops["100"] = dict(vs=vsi, ns=R(nsi, 0), vw=vwi, nw=R(nw, 0), fa1=fa1, fa2=fa2, v1=R(v1, 0), v2=R(v2, 0), b1=b1, b2=b2,
                  c1=c1, c2=c2, c3=c3, Ls=R(Ls, 1), tc=R(c1 * Ls / v1 + (c2 + c3) * Ls / v2, 2), Qw=R(Qi, 0),
                  Pc=R(Pi, 2), Pm=R(Pmi, 2), P_eixo=R(P_eixo, 2), util=R(Pmi / P_eixo * 100, 0))

# alternativa: fresa caracol (ordem de grandeza)
n0 = n_de(120, 100)
out["caracol"] = dict(vc=120, fa=2.5, n0=R(n0, 0), tc=R(z * (L_aro + math.sqrt(h_dente * (100 - h_dente)) + 5) / (n0 * 2.5), 1))

# ------------------------------------------------------------------ tempos totais (ts, ta, tp estimados; lote Z = 10)
Z = 10
tc = {"10": 0.0, "20": tc20, "30": tc30, "40": ops["40"]["tc"], "50": ops["50"]["tc"], "60": ops["60"]["tc"],
      "70": 0.0, "90": ops["90"]["tc"], "100": ops["100"]["tc"], "110": 0.0}
ts = {"10": 3.0, "20": 2.0, "30": 2.5, "40": 5.0, "50": 2.0, "60": 2.0, "70": 20.0, "90": 3.0, "100": 3.0, "110": 15.0}
ta = {"10": 0.0, "20": 1.5, "30": 1.2, "40": 15.4, "50": 0.6, "60": 1.0, "70": 0.0, "90": 1.0, "100": 1.0, "110": 0.0}
tp = {"10": 0, "20": 45, "30": 30, "40": 60, "50": 30, "60": 15, "70": 0, "90": 20, "100": 40, "110": 0}
tt = {k: R(tc[k] + ts[k] + ta[k] + tp[k] / Z, 2) for k in tc}
out["tempos"] = dict(tc=tc, ts=ts, ta=ta, tp=tp, tt=tt, tot_tc=R(sum(tc.values()), 2), tot_ts=sum(ts.values()),
                     tot_ta=R(sum(ta.values()), 1), tot_tp=sum(tp.values()), tot_tt=R(sum(tt.values()), 2))

out["ops"] = ops
json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "resultados.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
if __name__ == "__main__":
    for k, v in ops.items():
        print(k, {x: v[x] for x in ("Fc", "Pc", "Pm", "Pdisp", "util", "T", "n", "vf", "tc") if x in v})
    for k in ("geometria", "massas", "verif", "comparacao_30D", "tc_torno_35D", "caracol", "tempos"):
        print(k, out[k])
