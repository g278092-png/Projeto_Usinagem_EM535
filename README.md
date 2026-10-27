# Projeto de Usinagem – EM535A (UNICAMP)

Planejamento da fabricação de uma engrenagem cilíndrica de dentes retos (m = 6 mm, z = 24, aço SAE 8620), conforme o desenho do PROTEC.

## Compilação no Overleaf

- Arquivo principal: `main.tex`
- Compilador: **pdfLaTeX** (padrão do Overleaf)
- Rode a compilação duas vezes para atualizar sumário, listas e referências cruzadas.

## Estrutura

```
main.tex                  preâmbulo, capa, folha de rosto, listas e sumário
capitulos/
  01_introducao.tex
  02_caracterizacao.tex
  03_plano_de_trabalho.tex
  04_ferramentas.tex
  05_parametros.tex
  06_potencias.tex
  07_maquinas.tex
  08_tempos.tex
  09_folha_de_processo.tex   (página em paisagem)
  10_conclusoes.tex
  referencias.tex
figuras/                  desenho do PROTEC, croquis das operações e fluxograma
anexos/                   memória de cálculo (Python) e resultados
```

## Onde editar

- Nomes dos integrantes e número do grupo: comandos `\grupo`, `\autorA`, `\autorB` e `\autorC` no início do `main.tex`.
- Figuras, quadros, tabelas e equações têm rótulos (`fig:`, `quad:`, `tab:`, `eq:`) e são citados com `\ref{}` / `\eqref{}`, então a numeração se ajusta sozinha.
- Para recalcular os valores, rode `python anexos/memoria_de_calculo.py resultados.json`.
