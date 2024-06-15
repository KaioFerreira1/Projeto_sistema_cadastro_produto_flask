import os

import numpy as np
import psycopg2
from datetime import datetime, timedelta
import dao
import matplotlib.pyplot as plt
import pandas as pd
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from sklearn.linear_model import LinearRegression

app = Flask(__name__)
app.secret_key = 'your_secret_key'


@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('nome', None)
    session.clear()
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nome = request.form['nome']
        senha = request.form['senha']
        conexao = dao.conectardb()
        sucesso, cargo = dao.verificarlogin(nome, senha, conexao)
        if sucesso:
            session['nome'] = nome
            session['cargo'] = cargo  # Armazena o cargo do usuário na sessão
            return redirect('/menu')
        else:
            return render_template('login.html', error="Credenciais inválidas. Tente novamente.")
    return render_template('login.html')

@app.route('/cadastrarusuario', methods=['GET', 'POST'])
def cadastrar_usuario():
    if request.method == 'POST':
        login = request.form['nome']
        senha = request.form['senha']
        cargo = request.form['cargo']
        f = request.files['file']
        path = 'static/imagens/usuarios/' + f.filename
        if not os.path.exists('static/imagens/usuarios/'):
            os.makedirs('static/imagens/usuarios/')
        conexao = dao.conectardb()
        if dao.inseriruser(login, senha, cargo, path, conexao):
            f.save(path)
            return redirect('/login')
        else:
            return render_template('cadastro.html', error="Erro ao cadastrar usuário. Tente novamente.")
    return render_template('cadastro.html')

@app.route('/adicionar_produto', methods=['POST', 'GET'])
def adicionar_produto():
    if 'nome' not in session:
        return redirect('/login')
    elif 'cargo' in session and session['cargo'] == 'ADM':
        if request.method == 'POST':
            id_produto = request.form.get('id')
            nome = request.form.get('nome')
            marca = request.form.get('marca')
            data_validade = request.form.get('data_de_validade')
            preco = request.form.get('preco')
            quantidade = request.form.get('quantidade')
            f = request.files['file']
            path = 'static/imagens/produtos/' + f.filename

            if not os.path.exists('static/imagens/produtos/'):
                os.makedirs('static/imagens/produtos/')

            if dao.adicionar_produto(id_produto, nome, marca, data_validade, preco, quantidade, path):
                f.save(path)
                texto = 'Produto cadastrado com sucesso'
                return render_template('produto_registrado.html', texto=texto)
            else:
                texto = 'Erro ao cadastrar produto. Tente novamente'
                return render_template('erro.html', texto=texto)
        else:
            return render_template('adicionar_produto.html')
    else:
        return "Apenas o administrador pode acessar esta página."

@app.route('/produto-registrado')
def produto_registrado():
    return render_template('produto_registrado.html')

@app.route('/listagem_produtos', methods=['GET', 'POST'])
def listagem_produtos():
    if request.method == 'GET':
        conexao = dao.conectardb()
        cur = conexao.cursor()
        cur.execute("SELECT id, nome, marca, data_validade, preco, quantidade, pathft FROM produtos")
        produtos = cur.fetchall()
        conexao.close()

        # Pega todos os dados dos produtos
        dados_produtos = [{'id': p[0], 'nome': p[1], 'marca': p[2], 'data_validade': p[3], 'preco': p[4], 'quantidade': p[5]} for p in produtos]

        # Verificar se a solicitação espera JSON
        if request.headers.get('Content-Type') == 'application/json':
            # Se a solicitação espera JSON, retornar apenas os dados dos produtos em JSON
            return jsonify(dados_produtos)
        else:
            # Caso contrário, renderizar o template HTML
            return render_template('produtos.html', produtos=produtos)


@app.route('/buscar_produto', methods=['GET'])
def buscar_produto():
    # Obter o parâmetro de busca da query da URL
    termo_busca = request.args.get('search')

    # Verificar se o parâmetro de busca foi fornecido
    if termo_busca:
        conexao = dao.conectardb()
        cur = conexao.cursor()
        # Usar uma consulta SQL parametrizada para evitar SQL Injection
        cur.execute("SELECT id, nome, marca, data_validade, preco, quantidade, pathft FROM produtos WHERE nome LIKE %s", ('%' + termo_busca + '%',))
        produtos = cur.fetchall()
        conexao.close()

        # Extrair os dados dos produtos encontrados
        dados_produtos = [{'id': p[0], 'nome': p[1], 'marca': p[2], 'data_validade': p[3], 'preco': p[4], 'quantidade': p[5]} for p in produtos]

        # Verificar se a solicitação espera JSON
        if request.headers.get('Content-Type') == 'application/json':
            # Se a solicitação espera JSON, retornar apenas os dados dos produtos em JSON
            return jsonify(dados_produtos)
        else:
            # Caso contrário, renderizar o template HTML
            return render_template('produtos.html', produtos=produtos)
    else:
        return "Por favor, forneça um termo de busca."


@app.route('/menu')
def menu():
    if 'nome' in session:
        conexao = dao.conectardb()
        cur = conexao.cursor()
        cur.execute("SELECT login, cargo, path_foto  FROM usuarios WHERE login = %s", (session['nome'],))
        perfil = cur.fetchone()
        conexao.close()
        return render_template('menu_principal.html', nome=perfil[0], foto=perfil[2], cargo=perfil[1])
    else:
        return redirect('/login')

@app.route('/excluir_produto/<int:id>', methods=['POST'])
def excluir_produto(id):
    if 'nome' not in session:
        return redirect('/login')
    elif 'cargo' in session and session['cargo'] == 'ADM':
        if dao.excluir_produto(id):
            return render_template('produto_excluido.html', texto='Produto excluído com sucesso')
        else:
            return render_template('erro.html', texto='Erro ao excluir produto. Tente novamente')
    else:
        return "Apenas o administrador pode excluir um produto."

@app.route('/buscar_cliente', methods=['GET'])
def buscar_cliente():
    if 'nome' not in session or session.get('cargo') != 'ADM':
        return "Apenas o administrador pode buscar um cliente"

    termo_busca = request.args.get('search')
    if termo_busca:
        conexao = dao.conectardb()
        clientes = dao.buscar_cliente(termo_busca, conexao)
        conexao.close()

        return render_template('clientes.html', clientes=clientes)
    else:
        return render_template('buscar_cliente.html')


@app.route('/remover_cliente/<int:id>', methods=['GET'])
def remover_cliente(id):
    if 'nome' not in session or session.get('cargo') != 'ADM':
        return "Apenas o administrador pode excluir um cliente"
    conexao = dao.conectardb()
    sucesso = dao.remover_cliente(id, conexao)
    conexao.close()

    if sucesso:
        return redirect(url_for('buscar_cliente'))
    else:
        return render_template('erro.html', texto="Erro ao remover cliente. Tente novamente.")


@app.route('/fazer_pedido', methods=['GET', 'POST'])
def fazer_pedido():
    if 'nome' not in session or session.get('cargo') != 'Cliente':
        return "Apenas clientes podem fazer pedidos."

    if request.method == 'POST':
        # Processar o pedido
        conexao = dao.conectardb()
        try:
            with conexao:
                for key, value in request.form.items():
                    if key.startswith('produto_id_'):
                        produto_id = key.replace('produto_id_', '')
                        quantidade = int(value)
                        # Verificar se a quantidade é válida
                        if quantidade < 0:
                            return "Quantidade inválida."
                        # Obter a data de validade e preço do produto
                        produto = dao.buscar_produto_por_id(produto_id, conexao)
                        if produto is None:
                            return "Erro ao obter informações do produto."
                        data_validade = produto['data_validade']
                        preco = produto['preco']
                        # Atualizar o estoque do produto (se necessário)
                        sucesso = dao.atualizar_estoque_produto(produto_id, quantidade, conexao)
                        if not sucesso:
                            return "Erro ao processar o pedido. Estoque insuficiente."
                        # Salvar o pedido no banco de dados
                        usuario = session['nome']
                        data_pedido = datetime.now().date()  # Data atual
                        dao.salvar_pedido(produto_id, quantidade, usuario, data_pedido, data_validade, conexao, preco)
        except psycopg2.Error as e:
            # Tratar erros específicos
            return f"Erro no banco de dados: {e}"
        finally:
            conexao.close()

        # Redirecionar para a página de confirmação
        return redirect(url_for('pedido_confirmado'))
    else:
        conexao = dao.conectardb()
        produtos = dao.listar_produtos(conexao)
        conexao.close()
        return render_template('pedido_produto.html', produtos=produtos)


@app.route('/pedidos_validade_semana', methods=['GET'])
def pedidos_validade_semana():
    if 'nome' not in session:
        return "Apenas usuários logados podem acessar esta página."

    if 'nome' in session:
        conexao = dao.conectardb()
        cur = conexao.cursor()
        # Calculo da data atual e a data da última semana
        data_atual = datetime.now().date()
        data_ultima_semana = data_atual - timedelta(days=7)
        # Faz uma consulta dos pedidos na última semana de validade
        cur.execute("SELECT * FROM pedidos WHERE data_validade >= %s AND data_validade <= %s AND usuario = %s ORDER BY data_validade", (data_ultima_semana, data_atual, session['nome']))
        pedidos = cur.fetchall()
        conexao.close()

        # Formatar os pedidos como uma lista de dicionários
        pedidos_formatados = []
        for pedido in pedidos:
            pedido_formatado = {
                'id': pedido[0],
                'usuario': pedido[1],
                'produto_id': pedido[2],
                'quantidade': pedido[3],
                'data_validade': str(pedido[4])  # Convertendo para string para JSON
            }
            pedidos_formatados.append(pedido_formatado)

        return jsonify(pedidos_formatados)

    return "Apenas usuários logados podem acessar esta página."

@app.route('/graf_regressao_linear/<int:product_id>', methods=['GET'])
def graf_regressao_linear(product_id):
    df_orders = dao.get_pedidos_mes(product_id)
    if not df_orders.empty:
        fig_html = dao.criar_regres_linear(df_orders)
        return render_template('grafico.html', fig_html=fig_html)
    else:
        return "Nenhum dado disponível para criar o gráfico."


@app.route('/pedido_confirmado')
def pedido_confirmado():
    return render_template('pedido_confirmado.html')
if __name__ == '__main__':
    app.run(debug=True)
