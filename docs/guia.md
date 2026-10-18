# Guia passo a passo

Como montar o `aws-serverless-helpdesk` do zero, com um teste ao final de cada etapa. Só avance quando o teste passar.

**Antes de começar:** use uma única região (ex.: `us-east-1`) em todos os serviços. No Learner Lab, as Lambdas usam a `LabRole`, porque não é possível criar roles novas.

## Etapa 1: DynamoDB

1. Crie a tabela `chamados` com chave de partição `numero` do tipo **Number**.
2. Crie a tabela `contadores` com chave de partição `nome` do tipo **String**.
3. Nas duas, escolha **Customize settings** e capacidade **On-demand**.

**Teste:** em *Explore table items*, crie o item `{"numero": 1, "nome": "Teste"}` em `chamados`, confira que aparece e apague.

> Se `numero` for criada como String, o código falha ao buscar com número inteiro.

## Etapa 2: Lambda

1. Crie a função `suporte` (Python 3.12 ou mais novo) com a role existente **LabRole**.
2. Cole o conteúdo de [`lambda/lambda_function.py`](../lambda/lambda_function.py) e clique em **Deploy**.

**Teste:** use os eventos da pasta [`test-events/`](../test-events/) na aba *Test*.

| Evento | Resultado esperado |
|---|---|
| Criar `{"nome":"Erick","assunto":"Teste","setor":"ti"}` | `201` com `numero` 1001 (o seguinte dá 1002) |
| Setor `xyz` ou nome vazio | `400` |
| `consultar-testes.json` | `200`; com número inexistente, `404` |
| `encerrar-testes.json` | `200`; repetindo, `409` |
| `relatorio-testes.json` | contagem por setor |
| Consultar com `"numero":"abc"` | `400` (e não `500`) |

Se algo falhar, veja *Monitor → View CloudWatch logs*:
- `AccessDeniedException`: a role não é a LabRole.
- `ResourceNotFoundException`: nome da tabela errado ou região diferente.
- Resultado antigo: faltou clicar em **Deploy**.

## Etapa 3: API Gateway (HTTP API)

1. *Create API → HTTP API*, com a integração apontando para a Lambda `suporte`.
2. Crie as 4 rotas, todas com a mesma integração:
   - `POST /chamados`
   - `GET /chamados/relatorio`
   - `GET /chamados/{numero}`
   - `PATCH /chamados/{numero}/encerrar`
3. Stage `$default` com *auto-deploy*. Copie a **Invoke URL**.

**Teste** (troque `URL`):

```bash
curl -i URL/chamados/relatorio                              
curl -i URL/chamados/relatorio       
curl -i -X POST URL/chamados 
  -H "Content-Type: application/json" \
  -d '{"nome":"Erick","assunto":"Via API","setor":"TI"}'    
curl -i URL/chamados/9999            
curl -i URL/qualquercoisa                                 
```

## Etapa 4: CORS

Em *CORS → Edit*, preencha os três campos. Em cada um, digite o valor e clique em **Add** antes de salvar:

- **Allow-Origin:** `*` (depois, troque pela origem do seu site)
- **Allow-Methods:** `GET`, `POST`, `PATCH`, `OPTIONS`
- **Allow-Headers:** `content-type`,

**Teste:**

```bash
curl -i -X OPTIONS URL/chamados \
  -H "Origin: http://exemplo.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type,x-api-key"
```

A resposta deve trazer os três cabeçalhos `access-control-allow-*`.

## Etapa 5: Frontend no S3

1. Em [`frontend/index.html`](../frontend/index.html), preencha `API_URL` (sem barra no final).
2. Crie um bucket, desmarque *Block all public access* e envie o `index.html`.
3. Em *Properties → Static website hosting*, ative o site com `index.html` como documento inicial.
4. Em *Permissions → Bucket policy*, libere `s3:GetObject` para `*` no `arn:aws:s3:::SEU-BUCKET/*`.

**Teste:** abra o endpoint do site, abra um chamado e confira o item no DynamoDB. Depois consulte, encerre, tente encerrar de novo e veja o relatório.

Se der erro, abra o DevTools (F12) → **Console**:
- `blocked by CORS policy`: revise a Etapa 4 (muitas vezes falta `content-type`).
- `Failed to fetch` sem mensagem de CORS: URL errada ou com barra extra.
- `403` ao abrir o site: falta a bucket policy ou o Block Public Access ainda está ligado.

## Limpeza (ordem sugerida)

1. API Gateway (a API).
2. Lambda `suporte`.
3. Tabelas `chamados` e `contadores`.
4. Bucket S3 (esvazie antes de apagar).
5. Confirme que nada responde mais: `curl -i URL/chamados/relatorio` deve falhar.