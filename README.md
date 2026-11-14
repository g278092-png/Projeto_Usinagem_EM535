# Projeto de Usinagem – EM535A (UNICAMP)

Planejamento da fabricação de uma engrenagem cilíndrica de dentes retos (m = 6 mm, z = 24, aço SAE 8620), conforme o desenho do PROTEC.

## Compilação no Overleaf

- Arquivo principal: `main.tex`
- Compilador: **pdfLaTeX** (padrão do Overleaf)
- Rode a compilação duas vezes para atualizar sumário, listas e referências cruzadas.
- Pacotes novos nesta versão: `tikz` (chaves de código em caixas, comando `\chave`), `multirow` e `url`.

## Estrutura

```
main.tex                  preâmbulo, comando \chave, capa, folha de rosto, listas e sumário
capitulos/
  01_introducao.tex
  02_caracterizacao.tex      dados do dentado, material, sobremetais
  03_plano_de_trabalho.tex   sequência, justificativa da ordem, croquis por operação
  04_ferramentas.tex         chaves de código e justificativa de cada ferramenta
  05_parametros.tex          dados de catálogo x adotados
  06_potencias.tex           rendimentos, validade de Kienzle, resultados
  07_maquinas.tex
  08_tempos.tex
  09_folha_de_processo.tex   (página em paisagem)
  10_conclusoes.tex
  referencias.tex
figuras/                  desenho do PROTEC, croquis das operações e seção bruto x peça
anexos/
  memoria_de_calculo.py   todos os cálculos (forças, potências, tempos)
  resultados_calculo.json saída do script acima
  croquis.py              gera as figuras dos croquis
```

## Onde editar

- Nomes dos integrantes e número do grupo: comandos `\grupo` e `\autorA` a `\autorE` no início do `main.tex`.
- Chave de código em caixas: `\chave{P/1, C/2, L/3, -/x, PM/8}` (o par `-/x` desenha só o separador).
- Para recalcular os valores: `python anexos/memoria_de_calculo.py anexos/resultados_calculo.json`.
- Para redesenhar os croquis: `python anexos/croquis.py figuras`.
- O desenho técnico (`figuras/desenho_protec.png`) será substituído pelo desenho definitivo do grupo.
