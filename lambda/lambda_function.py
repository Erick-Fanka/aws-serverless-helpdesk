import json
import boto3

dynamodb = boto3.resource("dynamodb")
chamados = dynamodb.Table("chamados")
contadores = dynamodb.Table("contadores")

SETORES = ["TI", "RH", "FINANCEIRO"]


def resposta(status, corpo):
    # default=int converte os Decimal que o DynamoDB devolve para número
    return {"statusCode": status, "body": json.dumps(corpo, default=int, ensure_ascii=False)}


def proximo_numero():
    resp = contadores.update_item(
        Key={"nome": "chamado"},
        UpdateExpression="ADD valor :um",
        ExpressionAttributeValues={":um": 1},
        ReturnValues="UPDATED_NEW",
    )
    return 1000 + int(resp["Attributes"]["valor"])


def criar_chamado(event):
    dados = json.loads(event["body"]) if "body" in event else event

    nome = str(dados.get("nome", "")).strip()
    assunto = str(dados.get("assunto", "")).strip()
    setor = str(dados.get("setor", "")).upper().strip()

    if not nome or not assunto:
        return resposta(400, {"erro": "Nome e assunto são obrigatórios."})
    if setor not in SETORES:
        return resposta(400, {"erro": f"Setor inválido. Use: {', '.join(SETORES)}."})

    numero = proximo_numero()
    chamados.put_item(Item={
        "numero": numero, "nome": nome, "assunto": assunto,
        "setor": setor, "status": "Aberto",
    })
    return resposta(201, {"numero": numero, "status": "Aberto"})


def consultar_chamado(numero):
    item = chamados.get_item(Key={"numero": numero}).get("Item")
    if not item:
        return resposta(404, {"erro": f"Chamado {numero} não encontrado."})
    return resposta(200, item)


def encerrar_chamado(numero):
    try:
        chamados.update_item(
            Key={"numero": numero},
            UpdateExpression="SET #s = :encerrado",
            ConditionExpression="attribute_exists(numero) AND #s = :aberto",
            ExpressionAttributeNames={"#s": "status"},  # "status" é palavra reservada
            ExpressionAttributeValues={":encerrado": "Encerrado", ":aberto": "Aberto"},
        )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return resposta(409, {"erro": "Chamado inexistente ou já encerrado."})
    return resposta(200, {"numero": numero, "status": "Encerrado"})


def relatorio():
    itens = chamados.scan()["Items"]
    por_setor = {s: 0 for s in SETORES}
    for item in itens:
        por_setor[item["setor"]] += 1
    return resposta(200, {"por_setor": por_setor, "total": len(itens)})


def lambda_handler(event, context):
    rota = event.get("routeKey", "POST /chamados")
    params = event.get("pathParameters") or {}

    if rota == "POST /chamados":
        return criar_chamado(event)
    if rota == "GET /chamados/relatorio":
        return relatorio()

    if rota in ("GET /chamados/{numero}", "PATCH /chamados/{numero}/encerrar"):
        try:
            numero = int(params["numero"])
        except (KeyError, ValueError):
            return resposta(400, {"erro": "O número do chamado deve ser um inteiro."})
        if rota.startswith("GET"):
            return consultar_chamado(numero)
        return encerrar_chamado(numero)

    return resposta(404, {"erro": "Rota não encontrada."})