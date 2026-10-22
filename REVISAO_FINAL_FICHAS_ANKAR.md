# Revisão final antes da importação

- Bulbasaur (Vínculo) (Manu): forma própria, sem mudar o Bulbasaur normal; tipos Grama/Veneno, atributos base 70/9/9/12/11/9, imagens fornecidas.
- Braz: seis naturezas da Box corrigidas na ordem informada.
- Nanda: vinte naturezas da Box corrigidas na ordem informada. Axew, Prinplup e Simipour continuam Shiny.
- Lucas: doze naturezas da Box corrigidas na ordem informada. Corsola continua Shiny.
- Vini: doze naturezas da Box corrigidas na ordem informada.
- Mari: PV 30/30 preparado, sem aviso de 30/24.
- Manu: PV inicial 30 da etapa anterior; esse aviso permanece porque estava em branco na ficha original.

**Importante:** nenhum registro é gravado sem a opção `--aplicar`.

```powershell
flask --app app.py jogadores-planilhas importar
flask --app app.py jogadores-planilhas importar --aplicar
flask --app app.py usuarios verificar
flask --app app.py pokemon verificar
flask --app app.py inventario verificar
```

Não são necessárias migrations.
