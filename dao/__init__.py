import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import psycopg2
from psycopg2 import sql
from sklearn.linear_model import LinearRegression


def conectardb():
    con = psycopg2.connect(
        host='localhost',
        database='Analise',
        user='postgres',
        password='root'
    )
    return con

def inseriruser(login, senha, cargo, foto_data, conexao):
    cur = conexao.cursor()
    exito = False
    try:
        sql = "INSERT INTO usuarios (login, senha, cargo, path_foto) VALUES (%s, %s, %s, %s)"
        cur.execute(sql, (login, senha, cargo, foto_data))
    except psycopg2.IntegrityError:
        conexao.rollback()
    else:
        conexao.commit()
        exito = True
    finally:
        cur.close()
        conexao.close()
    return exito

def verificarlogin(nome, senha, conexao):
    cur = conexao.cursor()
    cur.execute(f"SELECT cargo FROM usuarios WHERE login = '{nome}' AND senha = '{senha}'")
    cargo = cur.fetchone()
    conexao.close()
    if cargo:
        return True, cargo[0]
    else:
        return False, None

def adicionar_produto(id, nome, marca, data_validade, preco, quantidade, path):
    conexao = conectardb()
    cur = conexao.cursor()
    exito = False
    try:
        sql = f"INSERT INTO produtos (id, nome, marca, data_validade, preco, quantidade, pathft) VALUES ('{id}', '{nome}', '{marca}','{data_validade}','{preco}','{quantidade}', '{path}' )"
        cur.execute(sql)
    except psycopg2.IntegrityError:
        conexao.rollback()
        exito = False
    else:
        conexao.commit()
        exito = True

    conexao.close()
    return exito

def excluir_produto(id):
    conexao = conectardb()
    cur = conexao.cursor()
    try:
        cur.execute("DELETE FROM produtos WHERE id = %s", (id,))
        conexao.commit()
        sucesso = True
    except psycopg2.Error as e:
        conexao.rollback()
        sucesso = False
        print(e)
    finally:
        conexao.close()
    return sucesso

def buscar_cliente(nome, conexao):
    cur = conexao.cursor()
    cur.execute("SELECT id, login, cargo FROM usuarios WHERE login LIKE %s", ('%' + nome + '%',))
    clientes = cur.fetchall()
    cur.close()
    return clientes

def remover_cliente(id, conexao):
    cur = conexao.cursor()
    try:
        cur.execute("DELETE FROM usuarios WHERE id = %s", (id,))
        conexao.commit()
        sucesso = True
    except psycopg2.Error:
        conexao.rollback()
        sucesso = False
    finally:
        cur.close()
    return sucesso


def listar_produtos(conexao):
    cur = conexao.cursor()
    cur.execute("SELECT id, nome, marca, data_validade, preco, quantidade, pathft FROM produtos")
    produtos = cur.fetchall()
    conexao.close()
    return produtos

def atualizar_estoque_produto(produto_id, quantidade_pedido, conexao):
    cur = conexao.cursor()
    try:
        cur.execute("SELECT quantidade FROM produtos WHERE id = %s", (produto_id,))
        quantidade_atual = cur.fetchone()[0]

        if quantidade_pedido > quantidade_atual:
            return False

        quantidade_restante = quantidade_atual - quantidade_pedido
        cur.execute("UPDATE produtos SET quantidade = %s WHERE id = %s", (quantidade_restante, produto_id))
        sucesso = True
    except psycopg2.IntegrityError as e:
        conexao.rollback()
        sucesso = False
    finally:
        cur.close()
    return sucesso


def salvar_pedido(produto_id, quantidade, usuario, data_pedido, data_validade, conexao, preco):
    cur = conexao.cursor()
    try:
        cur.execute("INSERT INTO pedidos (produto_id, quantidade, usuario, data_pedido, data_validade, preco) VALUES (%s, %s, %s, %s, %s, %s)",
                    (produto_id, quantidade, usuario, data_pedido, data_validade, preco))
        conexao.commit()
    except psycopg2.Error as e:
        print("Erro ao salvar o pedido:", e)
        conexao.rollback()
    finally:
        cur.close()

def buscar_produto_por_id(produto_id, conexao):
    cur = conexao.cursor()
    cur.execute("SELECT * FROM produtos WHERE id = %s", (produto_id,))
    produto = cur.fetchone()
    cur.close()
    if produto:
        return {
            'id': produto[0],
            'nome': produto[1],
            'marca': produto[2],
            'data_validade': produto[3],
            'preco': produto[4],
            'quantidade': produto[5],
            'pathft': produto[6]
        }
    else:
        return None

def obter_data_validade_produto(produto_id, conexao):
    cur = conexao.cursor()
    try:
        cur.execute("SELECT data_validade FROM produtos WHERE id = %s", (produto_id,))
        data_validade = cur.fetchone()[0]
    except psycopg2.Error as e:
        print("Erro ao obter a data de validade do produto:", e)
        data_validade = None
    finally:
        cur.close()
    return data_validade

def realizar_pedido(self, produto_id, quantidade, usuario, data_pedido, data_validade, preco):
        cur = self.conexao.cursor()
        try:
            cur.execute("INSERT INTO pedidos (produto_id, quantidade, usuario, data_pedido, data_validade, preco) "
                        "VALUES (%s, %s, %s, %s, %s, %s)",
                        (produto_id, quantidade, usuario, data_pedido, data_validade, preco))
            self.conexao.commit()
            sucesso = True
        except psycopg2.Error as e:
            print("Erro ao realizar o pedido:", e)
            self.conexao.rollback()
            sucesso = False
        finally:
            cur.close()
        return sucesso

def buscar_produto_por_nome(self, nome_produto):
    cur = self.conexao.cursor()
    cur.execute("SELECT * FROM produtos WHERE nome = %s", (nome_produto,))
    produto = cur.fetchone()
    cur.close()
    return produto


def get_pedidos_mes(product_id):
    con = conectardb()
    cur = con.cursor()

    try:
        query = sql.SQL("""
            SELECT EXTRACT(MONTH FROM data_pedido) AS mes_pedido, CAST(preco AS NUMERIC) AS preco
            FROM pedidos
            WHERE produto_id = %s
            ORDER BY mes_pedido
        """)

        cur.execute(query, [product_id])
        orders = cur.fetchall()
        df_orders = pd.DataFrame(orders, columns=['mes_pedido', 'preco'])

        # Convertendo Decimal para float
        df_orders['preco'] = df_orders['preco'].astype(float)

    except psycopg2.Error as e:
        print("Erro ao obter os pedidos:", e)
        df_orders = pd.DataFrame()

    finally:
        cur.close()
        con.close()

    return df_orders

def criar_regres_linear(df_orders):
    x = df_orders['mes_pedido'].values.reshape(-1, 1).astype(float)
    y = df_orders['preco'].values.astype(float)

    model = LinearRegression()
    model.fit(x, y)

    x_range = np.linspace(x.min(), x.max(), 12)
    y_range = model.predict(x_range.reshape(-1, 1))

    fig = px.scatter(df_orders, x='mes_pedido', y='preco', opacity=0.65, title='Regressão Linear do Preço por Mês')
    fig.add_traces(go.Scatter(x=x_range, y=y_range, name='Regression Fit', mode='lines'))

    return fig.to_html(full_html=False)
