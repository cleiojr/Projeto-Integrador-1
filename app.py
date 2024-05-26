import colorsys

from flask import Flask, render_template, jsonify,request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, sessionmaker
import folium
import requests
import _sqlite3
import plotly.express as px
import json
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from sqlalchemy import func
import pandas as pd



app = Flask('__name__')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dados.db'
db = SQLAlchemy(app)



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/mapa')
def mapa():
    start_coords = (-20.8202, -49.3797)  # Coordenadas de São josé do rio preto, Brasil
    folium_map = folium.Map(location=start_coords, zoom_start=12)

    # Você pode adicionar marcadores, linhas, ou outras camadas ao mapa se necessário
    folium.Marker(start_coords, popup='São José do Rio Preto').add_to(folium_map)

    # Renderizar o mapa para HTML
    map_html = folium_map._repr_html_()

    return render_template("mapa.html", folium_map=map_html)

@app.route('/informacoes')
def informacoes():
    return render_template('informacoes.html')

@app.route('/EuNaEpidemia')
def EuNaEpidemia():
    return render_template('EuNaEpidemia.html')

@app.route('/municipios/sp')
def get_municipios_sp():
    url = 'https://servicodados.ibge.gov.br/api/v1/localidades/estados/35/municipios'
    response = requests.get(url)
    if response.status_code == 200:
        # Converte a resposta em JSON
        municipios = response.json()
        return jsonify(municipios)
    else:
        return jsonify({"error": "Falha ao buscar dados"}), 404





class DadosregistroContagios(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    Reg_Nome = db.Column(db.String(80), nullable=True)
    Reg_Nascimento = db.Column(db.String(10), nullable=True)
    Reg_Email = db.Column(db.String(200), nullable=True)
    Reg_Telefone = db.Column(db.String(15), nullable=True)
    Reg_endereco = db.Column(db.String(100), nullable=True)
    Reg_Bairro = db.Column(db.String(80), nullable=True)
    Reg_Cidade = db.Column(db.String(50), nullable=True)
    Reg_Estado = db.Column(db.String(2), nullable=True)
    Reg_Cep = db.Column(db.String(10), nullable=True)
    Reg_EhDengue = db.Column(db.String(3), nullable=True)

class Sintoma(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    Sintoma_descricao = db.Column(db.String(200), nullable=True)
    pessoa_id = db.Column(db.Integer, nullable=True)






with app.app_context():
    db.create_all()


#geração dos graficos a partir do banco de dados
@app.route('/grafico_endereco')
def grafico_endereco():
    # Consulta os endereços em São José do Rio Preto
    resultados = db.session.query(DadosregistroContagios.Reg_endereco, db.func.count(DadosregistroContagios.id)).\
        filter(DadosregistroContagios.Reg_Cidade == 'São José do Rio Preto').\
        group_by(DadosregistroContagios.Reg_endereco).\
        all()

    # Geração do gráfico
    enderecos = [item[0][:30] + '...' if len(item[0]) > 30 else item[0] for item in resultados]  # truncar endereços longos
    counts = [item[1] for item in resultados]
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(enderecos, counts, color='skyblue')
    ax.set_title('Distribuição de Registros por Endereço em São José do Rio Preto')
    ax.set_xlabel('Frequência')
    ax.set_ylabel('Endereço')

    # Converter gráfico em imagem para incorporar no HTML
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode('utf8')

    return render_template('grafico_endereco.html', plot_url=plot_url)






@app.route('/registroContagios')
def registroContagios():
    return render_template('registroContagios.html')


@app.route('/enviar', methods=['POST','GET'])
def enviar():
    Reg_Nome = request.form['Reg_Nome']
    Reg_Nascimento = request.form['Reg_Nascimento']
    Reg_Email = request.form['Reg_Email']
    Reg_Telefone = request.form['Reg_Telefone']
    Reg_endereco = request.form['Reg_endereco']
    Reg_Bairro = request.form['Reg_Bairro']
    Reg_Cidade = request.form['Reg_Cidade']
    Reg_Estado = request.form['Reg_Estado']
    if 'Reg_Cep' in request.form:
        Reg_Cep = request.form['Reg_Cep']
    Reg_EhDengue= request.form['Reg_EhDengue']
    sintomas = request.form.getlist('sintomas')

    novo_dado = DadosregistroContagios(Reg_Nome=Reg_Nome, Reg_Nascimento=Reg_Nascimento, Reg_Email=Reg_Email,
                                       Reg_Telefone=Reg_Telefone,Reg_endereco=Reg_endereco,Reg_Bairro=Reg_Bairro,
                                       Reg_Cidade=Reg_Cidade,Reg_Estado=Reg_Estado,Reg_Cep=Reg_Cep,Reg_EhDengue=Reg_EhDengue)
    db.session.add(novo_dado)
    db.session.commit()

    for sintoma in sintomas:
        novo_sintoma = Sintoma(Sintoma_descricao=sintoma, pessoa_id=novo_dado.id)
        db.session.add(novo_sintoma)

    db.session.commit()

    return render_template('registroContagios.html')



@app.route('/Listagem')
def Listagem():
    # Busca todos os registros no banco de dados
    dados = DadosregistroContagios.query.all()
    return render_template('Listagem.html',dados=dados)

def get_data_sao_jose_rio_preto():
    # Consultar dados do banco de dados apenas para São José do Rio Preto
    data_sao_jose_rio_preto = DadosregistroContagios.query.filter_by(Reg_Cidade='São José do Rio Preto').all()
    return data_sao_jose_rio_preto

@app.route('/deletar/<int:id>')
def deletar(id):
    # Busca o registro pelo ID e, se não encontrar, retorna erro 404
    dado_para_deletar = DadosregistroContagios.query.get_or_404(id)

    # Deleta o registro do banco de dados
    db.session.delete(dado_para_deletar)
    db.session.commit()

    # Redireciona para a página de listagem
    return redirect(url_for('Listagem'))


@app.route("/dashboard2")
def dashboard2():
    # Consultar dados do banco de dados apenas para São José do Rio Preto
    data_query_bairro = db.session.query(
        DadosregistroContagios.Reg_Bairro,
        func.count(DadosregistroContagios.id).label('infectados')
    ).filter(DadosregistroContagios.Reg_Cidade == 'São José do Rio Preto'
    ).group_by(DadosregistroContagios.Reg_Bairro).all()

    # Transformar dados em formato adequado para o gráfico de pizza
    data_bairro = {'Bairro': [item[0] for item in data_query_bairro],
                   'Infectados': [item[1] for item in data_query_bairro]}

    # Criar DataFrame com base em data_bairro
    df_bairro = pd.DataFrame(data_bairro)

    # Criar gráfico de pizza
    fig = px.pie(df_bairro, values='Infectados', names='Bairro', title='Proporção de Infectados por Bairro em São José do Rio Preto')

    # Converter gráfico para HTML
    graficoHTML = fig.to_html(full_html=False)

    return render_template("dashboard2.html", grafico=graficoHTML)



@app.route("/dashboard")
def dashboard():
    # Consultar dados do banco de dados para São José do Rio Preto
    sao_jose_data_query = db.session.query(
        DadosregistroContagios.Reg_Bairro,
        db.func.count(DadosregistroContagios.id).label('infectados')
    ).filter(DadosregistroContagios.Reg_Cidade == 'São José do Rio Preto').group_by(DadosregistroContagios.Reg_Bairro).all()

    # Transformar dados em formato adequado para os gráficos
    sao_jose_data = {'Regiao': [item[0] for item in sao_jose_data_query],
                     'infectados': [item[1] for item in sao_jose_data_query]}

    # Criar gráficos
    fig1 = px.bar(sao_jose_data, x='Regiao', y='infectados', color='Regiao', barmode='group')
    fig2 = px.pie(sao_jose_data, values='infectados', names='Regiao', title="Proporção de Infectados")
    fig3 = px.histogram(sao_jose_data, x="Regiao", y="infectados", color="Regiao")
    fig4 = px.line(sao_jose_data, x="Regiao", y="infectados")

    # Converter gráficos para HTML
    barrasHTML = fig1.to_html(full_html=False)
    pizzaHTML = fig2.to_html(full_html=False)
    histogramHTML = fig3.to_html(full_html=False)
    linhaHTML = fig4.to_html(full_html=False)

    # Lista de registros da cidade de São José do Rio Preto
    registros_sao_jose = [f"{registro[0]}: {registro[1]} infectados" for registro in sao_jose_data_query]

    return render_template("dashboard.html", barras=barrasHTML, pizza=pizzaHTML, histogram=histogramHTML, linha=linhaHTML, registros_sao_jose=registros_sao_jose)


def get_coordinates(cep):
    # Inicializar o geocodificador com um user_agent, por exemplo, 'my_geocoder'
    geolocator = Nominatim(user_agent="my_geocoder")

    try:
        # Construir o endereço com o código postal e o país para melhor precisão
        location = geolocator.geocode(f'{cep}, Brazil')

        if location:
            return (location.latitude, location.longitude)
        else:
            return None
    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        print(f"Erro de geocodificação: {e}")
        return None


@app.route("/mapaIterativo")
def mapaIterativo():
    # Buscar registros no banco de dados
    registros = DadosregistroContagios.query.all()

    # Verificar se há registros e geocodificar o primeiro para iniciar o mapa
    if registros:
        coords = get_coordinates(registros[0].Reg_Cep)
        if coords:
            start_coords = coords
        else:
            start_coords = (-20.8202, -49.3797)  # Coordenadas padrão se a geocodificação falhar
    else:
        start_coords = (-20.8202, -49.3797)  # Coordenadas padrão se não houver registros

    map_coordenadas = folium.Map(location=start_coords, zoom_start=12)

    # Adicionar marcações para cada região registrada
    for reg in registros:
        coords = get_coordinates(reg.Reg_Cep)
        if coords:
            cor = 'red' if reg.id % 2 == 0 else 'purple'
            soma = 50 if reg.id % 2 == 0 else -100

            folium.Circle(
                location=coords,
                radius=900 + soma,
                color=cor,
                fill=True,
                fill_color=cor,
                popup=f'<i>{reg.Reg_Bairro}</i>'
            ).add_to(map_coordenadas)

    # Renderizar o mapa para HTML
    map_html = map_coordenadas._repr_html_()

    return render_template("mapaIterativo.html", map_circulos=map_html)

if __name__ == "__main__":
    app.run(debug=True)