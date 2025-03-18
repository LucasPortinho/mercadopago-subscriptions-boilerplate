

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask import Flask, redirect, url_for, jsonify, request, render_template, Response

from dotenv import load_dotenv
import os

import requests

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mercado_pago_boilerplate.db'  # Utilize o banco de dados de sua preferência
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    assinaturas = relationship('Assinatura', back_populates='usuario')

class Plano(db.Model):
    __tablename__ = 'planos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    preco = db.Column(db.Float, nullable=False)
    frequencia = db.Column(db.Integer, nullable=False)
    assinaturas = relationship('Assinatura', back_populates='plano')

class Assinatura(db.Model):
    __tablename__ = 'assinaturas'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    plano_id = db.Column(db.Integer, db.ForeignKey('planos.id'), nullable=False)
    data_inicio = db.Column(db.DateTime)
    data_fim = db.Column(db.DateTime)
    ativo = db.Column(db.Boolean, default=False)
    usuario = relationship('Usuario', back_populates='assinaturas')
    plano = relationship('Plano', back_populates='assinaturas')

with app.app_context():
    db.create_all()


def create_payment(usuario, plano, Assinatura: Assinatura):
    payment_json = {
        'back_url': 'https://mercadopago-subscriptions-boilerplate.onrender.com/mercadopago/sucesso',  # Url de redirect
        'reason': f"Plano {plano.nome}",
        "auto_recurring": {  # Cobrança automática
            'frequency': {plano.frequencia},
            'frequency_types': "months",
            "transaction_amount": float(plano.preco),
            "currency_id": "BRL"
        },
    }

    headers = {"Authorization": f"Bearer {os.getenv('MERCADO_PAGO_ACCESS_TOKEN')}", "Content-Type": "application/json"}
    response = requests.post("https://api.mercadopago.com/preapproval_plan", json=payment_json, headers=headers)

    if response.status_code == 201:
        preapproval_id = response.json()["id"]
        init_point = response.json()["init_point"]
        assinatura = Assinatura(usuario=usuario, plano=plano, preapproval_id=preapproval_id)
        
        return redirect(init_point)
    else:
        return redirect(url_for('index'))

@app.route('/', methods=['GET', 'POST'])
def index():
    planos = Plano.query.all()  # Busca todos os planos disponíveis
    
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        plano_id = request.form['plano_id']

        novo_usuario = Usuario(nome=nome, email=email)
        db.session.add(novo_usuario)
        db.session.commit()

        plano = Plano.query.get(plano_id)  # Obtém o plano escolhido pelo usuário
        
        if plano:
            create_payment(novo_usuario, plano)
        else:
            redirect(url_for('index'))

    return render_template('index.html', planos=planos)

@app.route('/mercadopago/notificacao', methods=['POST', 'GET'])
def notificacao():
    dados = request.data
    print('Dados:', dados)
    return jsonify({"status": "Recebido com sucesso"}), 200

@app.route('/mercadopago/sucesso')
def sucesso():
    return Response("Deu tudo certo")


if __name__ == '__main__':
    app.run()
