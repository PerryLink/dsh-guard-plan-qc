# dsh-guard-plan-qc — Verificação da tabela de configuração de equipamentos de proteção laboral e de segurança

`dsh-guard-plan-qc` lê uma tabela de configuração de equipamentos de proteção laboral —o número de pessoas e o período de configuração que o material declara, mais uma linha por produto configurado— e verifica a completude e a coerência interna dessa tabela: se cada linha preenche 品名 (nome), 规格型号 (especificação) e 配置数量 (quantidade), se a quantidade é analisável como um número maior que zero, se pode ser deduzida do número de pessoas declarado pelo fator por pessoa que você configurar, se a 发放日期 (data de entrega) cai dentro do período de configuração, se a 有效截止日期 (data de validade) é posterior à data de entrega e se a tabela cobre as categorias de produtos que você exige.

## O que ele responde

| Você pergunta | O que ele responde |
|---|---|
| Uma linha tem o nome, mas deixa 规格型号 vazio. Isso é reportado? | Sim. `GP-001` exige que cada linha preencha os campos de `requiredFields` —de fábrica 品名, 规格型号 e 配置数量, substituíveis pelas colunas da sua própria tabela— e reporta a linha juntamente com os campos que faltam; uma célula vazia conta como não preenchida. Verifica que as colunas estão preenchidas, não que o produto ou a sua especificação estejam corretos. |
| A célula de 配置数量 diz 若干. É o mesmo que uma quantidade zero? | Não. `GP-002` reporta os dois em separado: um valor que não consegue analisar (como 若干) é reportado como não sendo um número, enquanto um valor que analisa mas não é maior que zero é reportado com a própria cifra. «2双», «１，２００» e «2 件» são analisados, com a unidade junta. Não verifica se a cifra é real nem se a quantidade chega; com `checkQuantity` em false a regra não é executada. |
| O número de pessoas é 20 e `factors` dá 2 luvas isolantes por pessoa, mas a linha configura 30. Isso é detetado? | Sim, depois de configurar `factors`. `GP-003` multiplica o fator por pessoa pelo número de pessoas e reporta a linha correspondente cuja quantidade difere mais do que a sua `tolerance`. `factors` vem vazio de fábrica, portanto tal como é entregue a regra declara-se em `skipped` com esse motivo em vez de passar em silêncio; também se declara aí se o material não declarar o número de pessoas. O fator é o dado que você consultou, não uma cifra nacional: a regra não julga se é razoável. |
| O período de configuração é 2026-03-01 a 2026-03-31 e uma 发放日期 diz 2026-02-20. É reportado? | Sim. `GP-004` reporta que essa linha é anterior a `periodFrom`. O período vem de `periodFrom` / `periodTo` no topo do material; se faltarem ambos, a regra declara-se em `skipped` em vez de presumir um período, e uma data que não consegue analisar é reportada à parte em vez de ser omitida em silêncio. |
| A 有效截止日期 é o mesmo dia da 发放日期. Passa? | Não. `GP-005` exige que a data de validade seja posterior à data de entrega e reporta a linha quando não é, e só é executada se a linha trouxer as duas datas. Se esse período de validade é suficientemente longo —depende do produto e da função— não se julga. |
| A tabela diz 安全帽 e a minha lista de categorias exigidas diz 安全头盔. Será reportado como não coberto? | Sim. `GP-006` compara por contenção literal com 品名 e 规格型号, por isso outra forma de nomear o mesmo produto é reportada como não coberta; inclua também as variantes habituais ou unifique a terminologia da tabela. `requiredCategories` vem vazio de fábrica, portanto tal como é entregue a regra declara-se em `skipped`. Verifica apenas se a categoria aparece, não se o produto serve para a obra. |

## Normas que segue

| Documento | Número | Regras que o citam |
|---|---|---|
| 《个体防护装备配备规范》 | GB 39800.1—2020（个体防护装备配备规范 第1部分：总则；标准号不带"/T"⇒强制性；2020-12-24 发布、2022-01-01 实施；主管部门应急管理部；条号本次未取得） | GP-001, GP-002, GP-003, GP-004, GP-005, GP-006 |

**Boundary:** this plugin checks one **劳动防护用品配置表** for what a table can be held to — that every row
names a product with a specification and a quantity, that the quantity is a positive number, that it
reconciles with the headcount the plan states, that the issue date falls inside the plan period, that an
expiry date follows the issue date, and that the table covers the categories you require. It does **not**
judge whether a given product is the right protection for a given hazard, whether its protection level
suffices, or whether it counts as special protective equipment.

> ### ⚠️ Read this before trusting a citation in the report
>
> **Every `excerpt` in this plugin's rule pack says, in so many words, that the clause text was not
> obtained.** The regime lives in **GB 39800.1《个体防护装备配备规范》** and 《劳动防护用品监督管理规定》.
> The verification pass for this plugin could not retrieve verbatim clause text from them, so rather than
> paraphrase a quotation the pack states the gap in the `excerpt` field itself and puts the honest
> reasoning in `note`. Everything is therefore capped at `warn` (principle-derived) or `info` (locally
> configured), and a test asserts that no rule claims a quotation it does not have. **When the texts are
> in hand, two things must be done: replace each `excerpt` with the real clause, and raise `kind` to
> `direct`.**
>
> **The two numbers that would make this plugin powerful are the two it refuses to invent.** How many
> items each person needs (`GP-003` `factors`) and which product categories a job must cover (`GP-006`
> `requiredCategories`) depend on the hazard identification for *your* project, not on a national figure.
> Both ship **empty**, and a rule whose list is unset reports itself in `skipped` rather than passing.

## Compatibility

| Superfície | Estado |
|---|---|
| Harness | Faixa de peers `>=0.1.2-rc.1 <0.2.0 \|\| >=0.2.0-0 <0.3.0` — verificada para aceitar tanto `0.2.0-rc.2` quanto `0.2.1-alpha.1`. **`engines.dsh` não é declarado**: não tem leitor e não pode recusar nenhum host |
| Node | `^22.19.0 || >=24.0.0` |
| Plataformas | Todas (ESM puro; sem código nativo, sem rede, sem chamada ao modelo) |
| Modo de ferramenta | Funciona em `native`, `ptc` e `both`; para um diretório inteiro use `ptc` |

## What it does

A tabela de regras, os campos e o comportamento detalhado estão em [README.md](README.md#what-it-does) (versão principal em inglês). O plugin apenas lista divergências literais frente às cláusulas citadas e indica em `skipped` cada verificação que não pôde ser executada.

## Install

```sh
dsh plugin --profile <name> add dsh-guard-plan-qc
dsh --profile <name> --dump-config | grep 'dsh-guard-plan-qc'
```

## Configuration

Todos os parâmetros ajustáveis ficam no esquema Schemastery de `src/config.ts`, portanto mudam pelo `cordis.yml` sem editar código; os limites por regra ficam no pacote de regras sob `rules/`.

| Chave | Tipo | Padrão | Descrição |
|---|---|---|---|
| `rulesFile` | string | `rules/guard-plan-qc.yaml` | Caminho do pacote de regras, relativo à raiz do pacote |
| `disabledRules` | string[] | `[]` | Ids de regras a desativar; cada uma aparece em `skipped` |
| `onlyRules` | string[] | `[]` | Executar apenas estas regras; vazio executa todas |
| `skipNotes` | string | `""` | Nota acrescentada a cada motivo de `skipped` |
| `timeoutMs` | number | `120000` | Orçamento de tempo limite cooperativo da ferramenta |

## Material format

Aceita JSON ou YAML. O exemplo completo de campos está em [README.md](README.md#material-format) (versão principal em inglês). Os campos são opcionais na camada de leitura e validados pelo motor, de modo que uma exportação parcial gera achados sobre o que falta em vez de falhar.

## Rule sources

Os dados das regras ficam separados do código: cada regra traz documento, número, cláusula na numeração própria da fonte, trecho literal e URL de origem. O carregador impõe que o trecho seja citação real de pelo menos oito caracteres e que uma verificação baseada apenas em princípio geral (`kind: derived-from-principle`, teto `warn`) ou em política local (`kind: institutional-configuration`, teto `info`) nunca seja declarada `error`.

Os limites verificados e as conclusões deliberadamente **não** afirmadas estão em [README.md](README.md#rule-sources) (versão principal em inglês) e em `rules/evidence/`.

## Troubleshooting

- **O plugin instala mas a ferramenta não aparece**: confirme que `main` resolve para `lib/index.mjs` e que `pnpm run build` o gerou.
- **`dsh plugin add` recusa o pacote**: a faixa de peers cobre `0.1.x` e `0.2.x`; fora dela, conceda isenção explícita com `dsh plugin --profile <name> allow-version <pkg@ver> --dsh-version <runtime> --accept-risk`.
- **Uma regra não executou**: leia o arranjo `skipped`.
- **`check` informa `manifest-peers` como falha**: problema conhecido do `dsh-plugin-dev`; o runtime aplica a compatibilidade na instalação.
- **Os horários parecem deslocados**: toda a aritmética é de hora local sobre as cadeias fornecidas.

## Development

```sh
pnpm install
pnpm run typecheck
pnpm test
pnpm run build
node ../scripts/sync-shared.mjs dsh-guard-plan-qc
```

O último comando copia o kit compartilhado de `../_shared` para `src/shared/`; execute-o novamente após cada alteração compartilhada.

## License

[Apache License 2.0](LICENSE) © 2026 dsh-guard-plan-qc contributors.
