# dsh-guard-plan-qc — Verificación de la tabla de configuración de equipos de protección laboral y de seguridad

[![DSH Market](https://raw.githubusercontent.com/2BingLing/dsh-market/master/assets/readme/badge-listed-en.svg)](https://dsh.market/)

`dsh-guard-plan-qc` lee una tabla de configuración de equipos de protección laboral —el número de personas y el periodo de configuración que declara el material, más una fila por producto configurado— y comprueba la completitud y la coherencia interna de esa tabla: que cada fila rellene 品名 (nombre), 规格型号 (especificación) y 配置数量 (cantidad), que la cantidad se analice como un número mayor que cero, que se pueda deducir del número de personas declarado por el factor por persona que usted configure, que la 发放日期 (fecha de entrega) caiga dentro del periodo de configuración, que la 有效截止日期 (fecha de caducidad) sea posterior a la fecha de entrega y que la tabla cubra las categorías de productos que usted exige.

## Cómo se ve la salida

![Terminal demo of dsh-guard-plan-qc: real output over its GP-002 fixture](https://raw.githubusercontent.com/PerryLink/dsh-guard-plan-qc/main/docs/assets/dsh-guard-plan-qc-demo.png)

Salida real de este plugin sobre su propio fixture de prueba `GP-002` — no es un montaje. El paquete de reglas no inventa citas, así que cada hallazgo nombra la cláusula aplicada y advierte que su texto no se obtuvo.

## Qué responde

| Usted pregunta | Qué responde |
|---|---|
| Una fila tiene el nombre, pero deja 规格型号 vacío. ¿Se informa? | Sí. `GP-001` exige que cada fila rellene los campos de `requiredFields` —de fábrica 品名, 规格型号 y 配置数量, sustituibles por las columnas de su propia tabla— e informa de la fila junto con los campos que le faltan; una celda vacía cuenta como no rellenada. Comprueba que las columnas estén rellenas, no que el producto o su especificación sean los correctos. |
| La celda de 配置数量 dice 若干. ¿Es lo mismo que una cantidad de cero? | No. `GP-002` informa de ambos por separado: un valor que no puede analizar (como 若干) se informa como que no es un número, mientras que un valor que sí analiza pero no es mayor que cero se informa con la propia cifra. «2双», «１，２００» y «2 件» se analizan, con la unidad pegada. No comprueba si la cifra es real ni si la cantidad basta; con `checkQuantity` en false la regla no se ejecuta. |
| El número de personas es 20 y `factors` da 2 guantes aislantes por persona, pero la fila configura 30. ¿Se detecta? | Sí, una vez configurado `factors`. `GP-003` multiplica el factor por persona por el número de personas e informa de la fila coincidente cuya cantidad difiere más de su `tolerance`. `factors` viene vacío de fábrica, así que tal como se entrega la regla se declara en `skipped` con ese motivo en lugar de pasar en silencio; también se declara ahí si el material no declara el número de personas. El factor es el dato que usted consultó, no una cifra nacional: la regla no juzga si es razonable. |
| El periodo de configuración es 2026-03-01 a 2026-03-31 y una 发放日期 dice 2026-02-20. ¿Se informa? | Sí. `GP-004` informa de que esa fila es anterior a `periodFrom`. El periodo procede de `periodFrom` / `periodTo` en el nivel superior del material; si faltan los dos, la regla se declara en `skipped` en lugar de suponer un periodo, y una fecha que no puede analizar se informa aparte en vez de omitirse en silencio. |
| La 有效截止日期 es el mismo día que la 发放日期. ¿Pasa? | No. `GP-005` exige que la fecha de caducidad sea posterior a la fecha de entrega e informa de la fila cuando no lo es, y solo se ejecuta si la fila trae ambas fechas. Si ese periodo de validez es lo bastante largo —depende del producto y del puesto de trabajo— no se juzga. |
| La tabla pone 安全帽 y mi lista de categorías requeridas pone 安全头盔. ¿Se informará como no cubierta? | Sí. `GP-006` compara por contención literal contra 品名 y 规格型号, así que otra forma de nombrar el mismo producto se informa como no cubierta; incluya también las variantes habituales o unifique la terminología de la tabla. `requiredCategories` viene vacío de fábrica, así que tal como se entrega la regla se declara en `skipped`. Solo comprueba si la categoría aparece, no si el producto es apto para la obra. |

## Normas que sigue

| Documento | Número | Reglas que lo citan |
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

| Superficie | Estado |
|---|---|
| Harness | Rango de peers `>=0.1.2-rc.1 <0.2.0 \|\| >=0.2.0-0 <0.3.0` — verificado para aceptar tanto `0.2.0-rc.2` como `0.2.1-alpha.1`. **No se declara `engines.dsh`**: no tiene lector y no puede rechazar ningún host |
| Node | `^22.19.0 || >=24.0.0` |
| Plataformas | Todas (ESM puro; sin código nativo, sin red, sin llamada al modelo) |
| Modo de herramienta | Funciona en `native`, `ptc` y `both`; para un directorio completo use `ptc` |

## What it does

La tabla de reglas, los campos y el comportamiento detallado están en [README.md](README.md#what-it-does) (versión principal en inglés). El plugin sólo enumera divergencias literales frente a las cláusulas citadas e indica en `skipped` cada comprobación que no pudo ejecutarse.

## Install

```sh
dsh plugin --profile <name> add dsh-guard-plan-qc
dsh --profile <name> --dump-config | grep 'dsh-guard-plan-qc'
```

## Configuration

Todos los parámetros ajustables viven en el esquema Schemastery de `src/config.ts`, por lo que se cambian desde `cordis.yml` sin tocar el código; los umbrales por regla están en el paquete de reglas bajo `rules/`.

| Clave | Tipo | Predeterminado | Descripción |
|---|---|---|---|
| `rulesFile` | string | `rules/guard-plan-qc.yaml` | Ruta del paquete de reglas, relativa a la raíz del paquete |
| `disabledRules` | string[] | `[]` | Ids de reglas que se dejan de ejecutar; cada una aparece en `skipped` |
| `onlyRules` | string[] | `[]` | Ejecutar solo estas reglas; vacío ejecuta todas |
| `skipNotes` | string | `""` | Nota añadida a cada motivo de `skipped` |
| `timeoutMs` | number | `120000` | Presupuesto de tiempo de espera cooperativo de la herramienta |

## Material format

Acepta JSON o YAML. El ejemplo completo de campos está en [README.md](README.md#material-format) (versión principal en inglés). Los campos son opcionales en la capa de lectura y los valida el motor, de modo que una exportación parcial produce hallazgos sobre lo que falta en lugar de un fallo.

## Rule sources

Los datos de las reglas están separados del código: cada regla lleva documento, número, cláusula en la numeración propia de la fuente, extracto literal y URL de origen. El cargador impone que el extracto sea una cita real de al menos ocho caracteres y que una comprobación basada sólo en un principio general (`kind: derived-from-principle`, tope `warn`) o en una política local (`kind: institutional-configuration`, tope `info`) nunca se declare `error`.

Los límites verificados y las conclusiones deliberadamente **no** afirmadas están en [README.md](README.md#rule-sources) (versión principal en inglés) y en `rules/evidence/`.

## Troubleshooting

- **El plugin se instala pero la herramienta no aparece**: compruebe que `main` resuelve a `lib/index.mjs` y que `pnpm run build` lo generó.
- **`dsh plugin add` rechaza el paquete**: la faixa de peers cubre `0.1.x` y `0.2.x`; fuera de ella, conceda una exención explícita con `dsh plugin --profile <name> allow-version <pkg@ver> --dsh-version <runtime> --accept-risk`.
- **Una regla no se ejecutó**: lea el arreglo `skipped`.
- **`check` informa `manifest-peers` como fallo**: es un problema conocido de `dsh-plugin-dev`; el runtime aplica la compatibilidad al instalar.
- **Los horarios parecen desplazados**: toda la aritmética es de hora local sobre las cadenas entregadas.

## Development

```sh
pnpm install
pnpm run typecheck
pnpm test
pnpm run build
node ../scripts/sync-shared.mjs dsh-guard-plan-qc
```

El último comando copia el kit compartido de `../_shared` a `src/shared/`; vuelva a ejecutarlo tras cada cambio compartido.

## License

[Apache License 2.0](LICENSE) © 2026 dsh-guard-plan-qc contributors.
