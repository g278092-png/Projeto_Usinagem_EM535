# -*- coding: utf-8 -*-
"""Croquis das operacoes, no estilo de desenho tecnico simples:
peca em linha preta com secao hachurada, material removido na operacao em vermelho claro,
trajetoria de corte em vermelho continuo, movimento rapido em vermelho tracejado,
apoios/referencias com triangulos vazados e fixacao com setas pretas.
Croquis esquematicos (dimensoes em mm; trajetorias deslocadas da superficie para leitura).
Uso:  python croquis.py <pasta_de_saida>
"""
import math, sys, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle, Circle, Wedge, Arc, Patch
from matplotlib.lines import Line2D

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5, "hatch.color": "0.45",
                     "hatch.linewidth": 0.5, "savefig.dpi": 300})
RED = "#d62020"
REM = "#f6caca"
LW = 0.9
RB = 12.25

# ------------------------------------------------------------------ utilitarios
def arc(cz, cr, rad, a0, a1, n=8):
    return [(cz + rad * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cr + rad * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]

def section(ax, pts, hatch="////", fc="white", lw=LW, z=3):
    ax.add_patch(Polygon(pts, closed=True, fc=fc, ec="black", lw=lw, hatch=hatch, zorder=z))

def removed(ax, pts, z=2, ec="none"):
    ax.add_patch(Polygon(pts, closed=True, fc=REM, ec=ec, lw=0.5, zorder=z))

def blank(ax, pts, z=2.5):
    ax.add_patch(Polygon(pts, closed=True, fc="white", ec="none", zorder=z))

def path(ax, pts, rapid=False, lw=1.3, arrow=True, z=8):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=RED, lw=lw if not rapid else 0.9, ls="--" if rapid else "-", zorder=z,
            solid_capstyle="round")
    if arrow:
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
        ax.annotate("", xy=(x1, y1), xytext=(x1 - 0.01 * (x1 - x0), y1 - 0.01 * (y1 - y0)),
                    arrowprops=dict(arrowstyle="-|>", color=RED, lw=lw if not rapid else 0.9,
                                    mutation_scale=9, shrinkA=0, shrinkB=0), zorder=z)

def tag(ax, x, y, s, color=RED, size=7, ha="center", va="center", bold=True):
    ax.text(x, y, s, color=color, fontsize=size, ha=ha, va=va, fontweight="bold" if bold else "normal",
            zorder=10, bbox=dict(fc="white", ec="none", pad=0.5, alpha=0.9))

def note(ax, x, y, s, size=6.3, ha="left", va="center", color="black", rot=0):
    ax.text(x, y, s, fontsize=size, ha=ha, va=va, color=color, zorder=10, rotation=rot)

def tri(ax, x, y, direction, s=3.0, z=9):
    """triangulo vazado de apoio/referencia com a ponta em (x, y), apontando para a peca"""
    d = {"up": (0, -1), "down": (0, 1), "left": (1, 0), "right": (-1, 0)}[direction]
    bx, by = x + d[0] * s * 1.5, y + d[1] * s * 1.5
    px, py = -d[1], d[0]
    ax.add_patch(Polygon([(x, y), (bx + px * s * 0.8, by + py * s * 0.8), (bx - px * s * 0.8, by - py * s * 0.8)],
                         closed=True, fc="white", ec="black", lw=0.9, zorder=z))

def clamp(ax, x, y, direction, L=9, z=9):
    """seta preta de fixacao (forca de aperto) com a ponta em (x, y)"""
    d = {"up": (0, -1), "down": (0, 1), "left": (1, 0), "right": (-1, 0)}[direction]
    ax.annotate("", xy=(x, y), xytext=(x + d[0] * L, y + d[1] * L),
                arrowprops=dict(arrowstyle="-|>", color="black", lw=1.4, mutation_scale=11), zorder=z)

def axisline(ax, x0, x1, y=0, vertical=False):
    if vertical:
        ax.plot([y, y], [x0, x1], color="0.3", lw=0.6, ls=(0, (12, 3, 2, 3)), zorder=1)
    else:
        ax.plot([x0, x1], [y, y], color="0.3", lw=0.6, ls=(0, (12, 3, 2, 3)), zorder=1)

def dim(ax, p0, p1, text, size=6.3, side=1.3):
    (x0, y0), (x1, y1) = p0, p1
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="<|-|>", color="0.25", lw=0.5, mutation_scale=6, shrinkA=0, shrinkB=0),
                zorder=6)
    ax.text((x0 + x1) / 2, (y0 + y1) / 2 + side, text, fontsize=size, ha="center",
            va="bottom" if side > 0 else "top", color="0.15", zorder=6)

def legenda(fig, itens, y=0.0, ncol=None):
    H = {"corte": Line2D([], [], color=RED, lw=1.3, label="trajetória de corte"),
         "rapido": Line2D([], [], color=RED, lw=0.9, ls="--", label="movimento rápido"),
         "apoio": Line2D([], [], marker=">", ls="none", mfc="white", mec="black", ms=6, label="apoio / referência"),
         "fixacao": Line2D([], [], marker="v", ls="none", color="black", ms=6, label="fixação"),
         "removido": Patch(fc=REM, ec="0.5", lw=0.4, label="material removido na operação")}
    hs = [H[i] for i in itens]
    fig.legend(handles=hs, loc="lower center", ncol=ncol or len(hs), frameon=False, fontsize=6.6,
               bbox_to_anchor=(0.5, y), handlelength=2.2, columnspacing=1.4)

def save(fig, name):
    fig.savefig(os.path.join(OUT, name), bbox_inches="tight", pad_inches=0.04, facecolor="white")
    plt.close(fig)

def setup(ax, xlim, ylim):
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect("equal"); ax.axis("off")

# ------------------------------------------------------------------ geometria (meia-secao, z = eixo, r = raio)
def final_profile(z0=0.0):
    """peca torneada: face B do cubo em z0, face A em z0 - 51,3 (meia-secao superior)"""
    zA = z0 - 51.3
    b, a = z0 - 18.65, zA + 18.65            # fundos dos rebaixos B e A
    p = [(z0, RB), (z0, 21), (z0 - 2, 23), (b + 3, 23)]
    p += arc(b + 3, 26, 3, 270, 180)[1:] + [(b, 52)] + arc(b + 3, 52, 3, 180, 90)[1:]
    p += [(z0 - 1.65, 55), (z0 - 1.65, 78), (zA + 1.65, 78), (zA + 1.65, 55), (a - 3, 55)]
    p += arc(a - 3, 52, 3, 90, 0)[1:] + [(a, 26)] + arc(a - 3, 26, 3, 0, -90)[1:]
    p += [(zA + 2, 23), (zA, 21), (zA, RB)]
    return p

def mirror(pts):
    return [(z, -r) for z, r in pts]

def recess_final(zface):
    """contorno do rebaixo acabado (face do aro em zface, fundo 17 mm abaixo); z decresce para dentro"""
    bt = zface - 17
    return ([(zface, 55), (bt + 3, 55)] + arc(bt + 3, 52, 3, 90, 180)[1:] + [(bt, 26)] +
            arc(bt + 3, 26, 3, 180, 270)[1:] + [(zface, 23)])

def recess_rough(zface):
    """rebaixo desbastado pelos 8 mergulhos a partir da face do aro acabada zface
    (0,3 mm nas paredes e no fundo; mergulhos extremos 3 mm mais curtos para preservar os raios R3)"""
    d1, d2 = zface - 13.7, zface - 16.7
    return [(zface + 1.0, 23.3), (d1, 23.3), (d1, 27.07), (d2, 27.07), (d2, 50.93), (d1, 50.93), (d1, 54.7),
            (zface + 1.0, 54.7)]

PLUNGES = [52.2, 48.43, 44.66, 40.89, 37.11, 33.34, 29.57, 25.8]

# ------------------------------------------------------------------ operacoes 20 e 30 (torno)
def torno_fig(op):
    """op = 20 (face A, peca presa no Ø160 bruto) ou 30 (face B, peca presa no Ø156)"""
    fig, axs = plt.subplots(1, 3, figsize=(7.6, 3.55))
    if op == 20:
        zf = -3.35                                          # face A torneada do cubo
        raw = [(0, 0), (0, 80), (-58, 80), (-58, 0)]
        stateA = [(-2.85, 0), (-2.85, 23.5), (-4.5, 23.5), (-4.5, 78.5), (-37.65, 78.5), (-37.65, 80), (-58, 80),
                  (-58, 0)]
        # perfil completo apos a operacao 20
        final = ([(-3.35, RB), (-3.35, 21), (-5.35, 23)] + recess_final(-5)[::-1][1:] +
                 [(-5, 78), (-39, 78), (-39, 80), (-58, 80), (-58, RB)])
        bore_rough = [(1, 0), (1, 11.5), (-59, 11.5), (-59, 0)]
        zA_face, z_aro = -3.35, -5.0
        left, right = -66, 18
        title = ["(a) 20.1 a 20.3 – desbaste (T01)", "(b) 20.4 e 20.5 – furação e mergulhos (T03, T05)",
                 "(c) 20.6 a 20.8 – acabamento (T02, T05, T04)"]
    else:
        zf = 0.0
        m = lambda z: -54.65 - z                           # espelha a geometria da operacao 20
        inc = [(-3.35, RB), (-3.35, 21), (-5.35, 23)] + recess_final(-5)[::-1][1:] + \
              [(-5, 78), (-39, 78), (-39, 80), (-58, 80), (-58, RB)]
        raw = [(m(z), r) for z, r in inc]
        stateA = [(m(z), r) for z, r in inc[:-4]] + [(-15.65, 78), (-15.65, 78.5), (-1.15, 78.5), (-1.15, 23.5),
                                                   (0.5, 23.5), (0.5, RB)]
        final = final_profile(0.0)
        bore_rough = None
        zA_face, z_aro = 0.0, -1.65
        left, right = -66, 14
        title = ["(a) 30.1 a 30.3 – desbaste (T01)", "(b) 30.4 – mergulhos (T05)",
                 "(c) 30.5 a 30.7 – acabamento (T02, T05, T04)"]
    for k, ax in enumerate(axs):
        ax.set_title(title[k], fontsize=6.9)
        if k == 0:
            removed(ax, raw); section(ax, stateA)
        elif k == 1:
            section(ax, stateA)
            rr = recess_rough(z_aro)
            removed(ax, rr, z=4, ec="black")
            if bore_rough:
                removed(ax, bore_rough, z=4, ec="black")
        else:
            removed(ax, stateA)
            blank(ax, recess_rough(z_aro))
            if op == 20:
                blank(ax, [(1, 0), (1, 11.5), (-59, 11.5), (-59, 0)])
                removed(ax, [(1, 11.5), (1, RB), (-59, RB), (-59, 11.5)], z=2.6)
            else:
                blank(ax, [(5, 0), (5, RB), (-52, RB), (-52, 0)])
            section(ax, final)
        axisline(ax, left, right)
        # fixacao
        ax.add_patch(Rectangle((left, 0), 8, 96, fc="0.65", ec="black", lw=0.7, zorder=4))
        if op == 20:
            ax.add_patch(Rectangle((-58, 80), 15, 7, fc="0.82", ec="black", lw=0.7, zorder=4))
            clamp(ax, -50.5, 87, "down")
            tri(ax, -58, 45, "right")
            if k == 0:
                note(ax, left, 104, "placa de 3 castanhas duras\npega de 15 mm no Ø160", va="bottom")
        else:
            ax.add_patch(Rectangle((-49.65, 78), 15, 7, fc="0.82", ec="black", lw=0.7, zorder=4))
            ax.add_patch(Rectangle((-58, 13), 6.7, 8, fc="0.88", ec="black", lw=0.6, zorder=4))
            clamp(ax, -42.2, 85, "down")
            tri(ax, -51.3, 17, "right", s=2.4)
            if k == 0:
                note(ax, left, 104, "castanhas moles no Ø156\nface A no anel de encosto", va="bottom")
        setup(ax, (left - 1, right), (-14, 116))
    # trajetorias
    sfx = str(op)
    ax = axs[0]
    zfacebr = 0.0 if op == 20 else 3.35
    path(ax, [(zfacebr + 5, 86), (zfacebr + 5, 4)]); tag(ax, zfacebr + 5, 45, sfx + ".1", size=6.5)
    if op == 20:
        path(ax, [(4, 83), (-37.65, 83)])
    else:
        path(ax, [(6, 83), (-17.65, 83)])
    tag(ax, -16 if op == 20 else -4, 89, sfx + ".2", size=6.5)
    zdeg = -3.7 if op == 20 else -0.3
    path(ax, [(zdeg, 76), (zdeg, 25)], lw=1.0); tag(ax, zdeg - 7, 62, sfx + ".3", size=6.5)
    ax = axs[1]
    if op == 20:
        path(ax, [(8, 5), (-62, 5)]); tag(ax, -46, 5, "20.4", size=6.5)
    for c in PLUNGES:
        d = (z_aro - 16.7) if c not in (52.2, 25.8) else (z_aro - 13.7)
        path(ax, [(z_aro + 5, c), (d, c)], lw=0.8)
    tag(ax, z_aro + 9, 64, sfx + (".5" if op == 20 else ".4"), size=6.5)
    note(ax, z_aro + 1, 96, "8 mergulhos axiais\npasso radial 3,77 mm", size=6, color=RED, va="bottom")
    ax = axs[2]
    zA = zA_face
    if op == 20:
        ext = [(-39.5, 80.5), (-4.4, 80.5), (-4.4, 57)]
        hub = [(-5.8, 25.2), (-2.6, 21.2), (-2.6, 13.5)]
    else:
        ext = [(-17.65, 80.5), (-1.0, 80.5), (-1.0, 57)]
        hub = [(-2.4, 25.2), (0.8, 21.2), (0.8, 13.5)]
    path(ax, ext, lw=1.0); path(ax, [ext[-1], hub[0]], rapid=True, arrow=False); path(ax, hub, lw=1.0)
    tag(ax, -22 if op == 20 else -9, 88, sfx + (".6" if op == 20 else ".5"), size=6.5)
    rf = recess_final(z_aro)
    off = [(z, r - 0.9 if r > 50 else (r + 0.9 if r < 28 else r)) for z, r in rf]
    off = [(z + 0.9 if abs(z - (z_aro - 17)) < 0.01 else z, r) for z, r in off]
    path(ax, off, lw=1.0); tag(ax, z_aro - 9, 40, sfx + (".7" if op == 20 else ".6"), size=6.5)
    if op == 20:
        path(ax, [(6, 10.6), (-60, 10.6)], lw=1.0); tag(ax, -40, 6, "20.8", size=6.5)
    else:
        path(ax, [(4, 15), (0.6, 11.6)], lw=1.0); tag(ax, 9, 9, "30.7", size=6.5)
    legenda(fig, ["corte", "rapido", "apoio", "fixacao", "removido"], y=-0.04)
    fig.tight_layout(w_pad=0.2)
    # paineis separados, usados como miniaturas na folha de processo
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    for k, ax in enumerate(axs):
        ext = ax.get_tightbbox(rend).transformed(fig.dpi_scale_trans.inverted())
        fig.savefig(os.path.join(OUT, "croqui_op%d_%s.png" % (op, "abc"[k])), bbox_inches=ext.expanded(1.02, 1.02),
                    facecolor="white")
    save(fig, "croqui_op%d.png" % op)

# ------------------------------------------------------------------ operacao 40
def tooth_outline(rf=64.5, ra=78.0, m=6, z=24, alpha=20, k_range=range(-4, 5), base_angle=90):
    import numpy as np
    inv = lambda a: math.tan(a) - a
    rp = m * z / 2
    rb = rp * math.cos(math.radians(alpha))
    sp = math.pi * m / 2
    def psi(r):
        r = max(r, rb)
        return sp / (2 * rp) + inv(math.radians(alpha)) - inv(math.acos(rb / r))
    pts = []
    pitch = 2 * math.pi / z
    for k in k_range:
        th0 = math.radians(base_angle) + k * pitch
        rs = list(np.linspace(rf, ra, 14))
        left = [(th0 - psi(r), r) for r in rs]
        right = [(th0 + psi(r), r) for r in rs[::-1]]
        if pts:
            pass
        pts += left + right
        # fundo ate o proximo dente
        pts += [(th0 + psi(rf) + (pitch - 2 * psi(rf)) * i / 6, rf) for i in range(1, 6)]
    return [(r * math.cos(t), r * math.sin(t)) for t, r in pts]

def fig_op40():
    fig, axs = plt.subplots(1, 2, figsize=(7.6, 3.6), gridspec_kw=dict(width_ratios=[1.3, 1]))
    ax = axs[0]
    ax.set_title("(a) vista lateral – fresa de disco F01", fontsize=7.2)
    prof = final_profile(0.0)
    section(ax, prof); section(ax, mirror(prof))
    ax.add_patch(Rectangle((-49.65, 64.5), 48, 13.5, fc=REM, ec="none", zorder=4))
    ax.plot([-49.65, -1.65], [64.5, 64.5], color=RED, lw=0.6, ls="--", zorder=5)
    note(ax, -60, 67, "vão\n(13,5 mm)", size=5.8, ha="right", color=RED)
    ax.add_patch(Rectangle((-80, -12.25), 104, 24.5, fc="0.85", ec="black", lw=0.7, zorder=4))
    note(ax, 26, 0, "mandril Ø24,5", size=6)
    ax.add_patch(Rectangle((-104, -30), 22, 60, fc="0.6", ec="black", lw=0.7, zorder=4))
    note(ax, -93, -34, "cabeçote divisor\n(relação 40:1)", ha="center", va="top")
    ax.add_patch(Polygon([(24, -6), (24, 6), (33, 0)], closed=True, fc="0.6", ec="black", lw=0.7, zorder=4))
    tri(ax, -51.3, -17, "right", s=2.6)
    clamp(ax, 0.3, 17, "left")
    note(ax, 2, 22, "porca", size=6)
    cx, cy = -25.65, 78 - 13.5 + 50
    ax.add_patch(Circle((cx, cy), 50, fc="white", ec="black", lw=0.8, zorder=2))
    ax.add_patch(Circle((cx, cy), 16, fc="0.85", ec="black", lw=0.6, zorder=2))
    note(ax, cx, cy, "árvore\nO32", ha="center", size=6)
    note(ax, cx, cy + 25, "F01  Ø100, z = 12", ha="center", size=6.2)
    ax.add_patch(Arc((cx, cy), 114, 114, theta1=25, theta2=65, color="black", lw=0.8))
    ax.annotate("", xy=(cx + 57 * math.cos(math.radians(25)), cy + 57 * math.sin(math.radians(25))),
                xytext=(cx + 57 * math.cos(math.radians(30)), cy + 57 * math.sin(math.radians(30))),
                arrowprops=dict(arrowstyle="-|>", color="black", lw=0.8, mutation_scale=8))
    note(ax, cx + 42, cy + 48, "n = 60 rpm", size=6.2)
    path(ax, [(30, 86), (-85, 86)])
    note(ax, 32, 92, "avanço da mesa\nvf = 39,6 mm/min", size=6, color=RED, va="bottom")
    path(ax, [(-85, 92), (-85, 172), (30, 172), (30, 92)], rapid=True)
    note(ax, -28, 175, "retorno rápido e divisão de 15° entre vãos", size=6, color=RED, ha="center", va="bottom")
    axisline(ax, -110, 40)
    setup(ax, (-110, 62), (-60, 185))
    ax = axs[1]
    ax.set_title("(b) vista frontal – vão em usinagem", fontsize=7.2)
    to = tooth_outline()
    ax.plot([p[0] for p in to], [p[1] for p in to], color="black", lw=LW)
    ax.add_patch(Arc((0, 0), 144, 144, theta1=50, theta2=130, color="0.4", lw=0.5, ls=(0, (8, 2, 2, 2))))
    note(ax, 58, 51, "Ø144 (primitivo)", size=5.8, color="0.3")
    th = math.radians(90 + 7.5)
    import numpy as np
    inv = lambda a: math.tan(a) - a
    rb, rp = 72 * math.cos(math.radians(20)), 72.0
    psi = lambda r: math.pi * 6 / 2 / (2 * rp) + inv(math.radians(20)) - inv(math.acos(rb / max(r, rb)))
    rs = list(np.linspace(64.5, 78.6, 14))
    g = math.radians(7.5)
    vao = [(r * math.cos(th - (g - psi(r))), r * math.sin(th - (g - psi(r)))) for r in rs]
    vao2 = [(r * math.cos(th + (g - psi(r))), r * math.sin(th + (g - psi(r)))) for r in rs[::-1]]
    ax.add_patch(Polygon(vao + vao2, closed=True, fc=REM, ec=RED, lw=1.0, zorder=5))
    note(ax, -14, 87, "perfil da fresa nº 4\n(21 a 25 dentes)", size=6, color=RED, ha="center", va="bottom")
    ax.add_patch(Arc((0, 0), 118, 118, theta1=65, theta2=82, color=RED, lw=1.0))
    ax.annotate("", xy=(59 * math.cos(math.radians(65)), 59 * math.sin(math.radians(65))),
                xytext=(59 * math.cos(math.radians(68)), 59 * math.sin(math.radians(68))),
                arrowprops=dict(arrowstyle="-|>", color=RED, lw=1.0, mutation_scale=8))
    note(ax, 12, 40, "divisão de 15° = 40/24 volta\nda manivela (1 volta + 2/3)", size=5.9, color=RED)
    setup(ax, (-62, 72), (30, 102))
    legenda(fig, ["corte", "rapido", "apoio", "fixacao", "removido"], y=-0.03)
    fig.tight_layout(w_pad=0.3)
    save(fig, "croqui_op40.png")

# ------------------------------------------------------------------ operacao 50
def slot_poly(a_mid, rc=39.0, half_ang=22.5, w=9.0, n=30):
    a0, a1 = a_mid - half_ang, a_mid + half_ang
    P = lambda r, a: (r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))
    outer = [P(rc + w, a0 + (a1 - a0) * i / n) for i in range(n + 1)]
    e1 = P(rc, a1)
    cap1 = [(e1[0] + w * math.cos(math.radians(a1 + t)), e1[1] + w * math.sin(math.radians(a1 + t))) for t in range(0, 181, 10)]
    inner = [P(rc - w, a1 - (a1 - a0) * i / n) for i in range(n + 1)]
    e0 = P(rc, a0)
    cap0 = [(e0[0] + w * math.cos(math.radians(a0 + 180 + t)), e0[1] + w * math.sin(math.radians(a0 + 180 + t))) for t in range(0, 181, 10)]
    return outer + cap1 + inner + cap0

def vert(pts):
    """meia-secao (z, r) -> desenho com eixo vertical: x = r, y = z (face B para cima)"""
    return [(r, z) for z, r in pts]

def vert_full(ax, z0=0.0):
    P = vert(final_profile(z0))
    section(ax, P); section(ax, [(-x, y) for x, y in P])

def fig_op50():
    fig, axs = plt.subplots(1, 2, figsize=(7.6, 3.6), gridspec_kw=dict(width_ratios=[1.1, 1]))
    ax = axs[0]
    ax.set_title("(a) vista superior – rasgos em arco (F02)", fontsize=7.2)
    ax.add_patch(Circle((0, 0), 78, fc="white", ec="black", lw=LW))
    ax.add_patch(Circle((0, 0), 64.5, fc="none", ec="0.45", lw=0.4, ls="--"))
    ax.add_patch(Circle((0, 0), 55, fc="none", ec="black", lw=0.7))
    ax.add_patch(Circle((0, 0), 23, fc="none", ec="black", lw=0.7))
    ax.add_patch(Circle((0, 0), RB, fc="0.8", ec="black", lw=0.7))
    note(ax, 0, 0, "pino\nO24,5", ha="center", size=5.6)
    for am in (45, 135, 225, 315):
        ax.add_patch(Polygon(slot_poly(am), closed=True, fc=REM, ec="black", lw=0.7, zorder=3))
    cl = [(39 * math.cos(math.radians(a)), 39 * math.sin(math.radians(a))) for a in [22.5 + 45 * i / 20 for i in range(21)]]
    path(ax, cl, lw=1.2)
    note(ax, 50, 70, "desbaste: rampa de 5° sobre a\nlinha de centro R39, 3 níveis", size=5.9, color=RED)
    con = slot_poly(135, w=8.2)
    path(ax, con + [con[0]], lw=0.9)
    note(ax, -112, 72, "acabamento: contorno\ncom ae = 1 mm", size=5.9, color=RED)
    e = (39 * math.cos(math.radians(67.5)), 39 * math.sin(math.radians(67.5)))
    s2 = (39 * math.cos(math.radians(112.5)), 39 * math.sin(math.radians(112.5)))
    path(ax, [e, (0, 50), s2], rapid=True)
    note(ax, 0, -92, "R30 a R48; extremidades R9; 4 rasgos a 90°", ha="center", size=6)
    setup(ax, (-115, 112), (-98, 90))
    ax = axs[1]
    ax.set_title("(b) corte – fixação e níveis de desbaste", fontsize=7.2)
    vert_full(ax)
    ax.add_patch(Rectangle((-34, -51.3 - 9), 68, 9, fc="0.75", ec="black", lw=0.7))
    note(ax, 0, -64, "placa-base", ha="center", va="top")
    ax.add_patch(Rectangle((-12.25, -51.3), 24.5, 56, fc="0.86", ec="black", lw=0.6))
    ax.add_patch(Rectangle((-17, 4.7), 34, 4.5, fc="0.6", ec="black", lw=0.6))
    clamp(ax, 0, 9.2, "down")
    note(ax, 20, 12, "porca e arruela", size=5.9)
    tri(ax, -17, -51.3, "up", s=2.4); tri(ax, 17, -51.3, "up", s=2.4)
    ax.add_patch(Rectangle((30, -32.65), 18, 14.0, fc=REM, ec="black", lw=0.5, zorder=4))
    for lvl in (-23.65, -28.65):
        ax.plot([30, 48], [lvl, lvl], color=RED, lw=0.8, ls="--", zorder=5)
    path(ax, [(39, 14), (39, -17.5)], rapid=True)
    note(ax, 52, -26, "alma 14 mm:\nníveis 5 + 5 + 4", size=5.9, color=RED)
    axisline(ax, -60, 22, vertical=True)
    setup(ax, (-82, 92), (-70, 24))
    legenda(fig, ["corte", "rapido", "apoio", "fixacao", "removido"], y=-0.03)
    fig.tight_layout(w_pad=0.3)
    save(fig, "croqui_op50.png")

# ------------------------------------------------------------------ operacao 60
def fig_op60():
    fig, ax = plt.subplots(figsize=(4.4, 3.9))
    vert_full(ax)
    ax.add_patch(Rectangle((-90, -51.3 - 8), 180, 8, fc="0.75", ec="black", lw=0.7))
    note(ax, 0, -62, "suporte da brochadeira, com pino de orientação em um rasgo em arco", ha="center", va="top", size=5.9)
    ax.add_patch(Rectangle((-12.25, -51.3 - 8), 24.5, 66, fc="0.88", ec="black", lw=0.6, zorder=4))
    note(ax, -3, -22, "bucha-guia Ø24,5", rot=90, ha="center", size=5.8)
    ax.add_patch(Rectangle((2.7, -86), 9.52, 118, fc="white", ec=RED, lw=0.9, zorder=5))
    ax.add_patch(Rectangle((12.25, -51.3), 3.5, 51.3, fc=REM, ec="black", lw=0.5, zorder=6))
    note(ax, 18, 26, "brocha 8 mm (B01)\n+ calço de 1,27 mm\nnos 2º e 3º passes", size=6, color=RED, va="bottom")
    path(ax, [(7.5, 44), (7.5, 34)], lw=1.4)
    note(ax, -20, 40, "3 passes, curso ≈ 341 mm", size=6, color=RED, ha="right")
    tri(ax, -40, -51.3, "up", s=2.6); tri(ax, 40, -51.3, "up", s=2.6)
    tri(ax, -12.25, -12, "right", s=2.2)
    legenda(fig, ["corte", "apoio", "removido"], y=-0.04)
    setup(ax, (-92, 92), (-88, 60))
    save(fig, "croqui_op60.png")

# ------------------------------------------------------------------ operacao 90
def fig_op90():
    fig, ax = plt.subplots(figsize=(4.8, 3.3))
    vert_full(ax)
    ax.add_patch(Rectangle((-100, -51.3 - 12), 200, 12, fc="0.6", ec="black", lw=0.7))
    note(ax, 0, -57.3, "mesa magnética", ha="center", color="white")
    tri(ax, -17, -51.3, "up", s=2.4); tri(ax, 17, -51.3, "up", s=2.4)
    ax.add_patch(Rectangle((-21, 0), 42, 1.8, fc=REM, ec="black", lw=0.4, zorder=6))
    ax.add_patch(Wedge((0, 175 + 2.5), 175, 252, 288, fc="#efe6d6", ec="black", lw=0.7, zorder=2))
    note(ax, 0, 40, "rebolo R01  350 × 40 × 127\nvs = 26,6 m/s", ha="center", size=6.2)
    path(ax, [(-41, 16), (41, 16)]); path(ax, [(41, 16), (-41, 16)])
    note(ax, 0, 19, "curso da mesa 82 mm, vw = 15 m/min", ha="center", va="bottom", size=6, color=RED)
    path(ax, [(70, 38), (70, 8)]); note(ax, 73, 22, "penetração ae\n0,02 / 0,005 mm", size=6, color=RED)
    note(ax, -102, 48, "avanço transversal\ns = 8 mm por curso\n(perpendicular ao papel)", size=5.8, color=RED)
    note(ax, 0, -70, "a peça é virada para retificar a outra face (apoio na face já retificada)", ha="center", size=5.9)
    legenda(fig, ["corte", "apoio", "removido"], y=-0.05)
    setup(ax, (-102, 102), (-74, 62))
    save(fig, "croqui_op90.png")

# ------------------------------------------------------------------ operacao 100
def fig_op100():
    fig, ax = plt.subplots(figsize=(4.8, 3.6))
    prof = final_profile(0.0)
    section(ax, prof); section(ax, mirror(prof))
    ax.add_patch(Rectangle((-74, -96), 12, 192, fc="0.65", ec="black", lw=0.7))
    for s in (1, -1):
        ax.add_patch(Rectangle((-62, s * 74 - (10 if s < 0 else 0)), 24, 10, fc="0.82", ec="black", lw=0.7))
        ax.add_patch(Circle((-36, s * 72), 3.0, fc="#f2c94c", ec="black", lw=0.6, zorder=6))
        clamp(ax, -36, s * 75.4, "down" if s > 0 else "up")
        tri(ax, -51.3, s * 17, "right", s=2.4)
    note(ax, -74, 101, "placa com 3 roletes no diâmetro primitivo;\nencosto na face A retificada", va="bottom")
    ax.add_patch(Rectangle((-46, 12.25), 46, 0.25 * 3, fc=REM, ec="black", lw=0.4, zorder=6))
    ax.add_patch(Rectangle((-46, -12.25 - 0.75), 46, 0.75, fc=REM, ec="black", lw=0.4, zorder=6))
    ax.add_patch(Rectangle((-30, -10), 20, 20, fc="#efe6d6", ec="black", lw=0.7, zorder=7))
    ax.add_patch(Rectangle((-10, -3), 78, 6, fc="0.8", ec="black", lw=0.6, zorder=7))
    note(ax, 22, 6, "rebolo R02  Ø20 × 20, ns ≈ 28 650 rpm", va="bottom", size=6)
    path(ax, [(-8, -22), (-44, -22)]); path(ax, [(-44, -22), (-8, -22)])
    note(ax, 2, -22, "oscilação axial\n(curso 44,3 mm)", ha="left", size=6, color=RED)
    axisline(ax, -80, 72)
    legenda(fig, ["corte", "apoio", "fixacao", "removido"], y=-0.04)
    setup(ax, (-78, 74), (-100, 118))
    save(fig, "croqui_op100.png")

# ------------------------------------------------------------------ bruto x peca torneada
def fig_bruto():
    fig, ax = plt.subplots(figsize=(4.4, 3.4))
    ax.add_patch(Polygon([(3.35, -80), (3.35, 80), (-54.65, 80), (-54.65, -80)], closed=True,
                         fc=REM, ec="0.35", lw=0.7, ls="--"))
    prof = final_profile(0.0)
    section(ax, prof); section(ax, mirror(prof))
    axisline(ax, -62, 12)
    dim(ax, (-54.65, 88), (3.35, 88), "bruto 58")
    dim(ax, (-51.3, -88), (0, -88), "cubo torneado 51,3", side=-1.3)
    note(ax, 8, 80, "Ø160 (bruto)", size=6)
    note(ax, 8, 70, "Ø156", size=6)
    note(ax, 8, -14, "furo Ø24,5", size=6)
    legenda(fig, ["removido"], y=-0.04)
    setup(ax, (-64, 40), (-100, 100))
    save(fig, "fig_bruto_peca.png")

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    torno_fig(20); torno_fig(30); fig_op40(); fig_op50(); fig_op60(); fig_op90(); fig_op100(); fig_bruto()
    print("ok")
