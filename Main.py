import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, ClientsideFunction
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import os.path

import numpy as np
import pandas as pd
import json
from operator import itemgetter
import openpyxl
import sqlalchemy
from sqlalchemy import create_engine

#===================================== CONEXÃO COM BASE DE DADOS =============================================================================
ssl_args = {'ssl_ca': 'cacert-2023-08-22.pem','ssl_verify_identity' : True}
engine = create_engine("mysql+mysqlconnector://tjjxv95ij8rn6ubf6w94:pscale_pw_OahZFxycc7txvnKm9oBDKYRcgQsTrmUwwYreJjQzeBk@aws.connect.psdb.cloud/projeto_eleicoes_2020",
                           connect_args=ssl_args)
#======================================CARREGAMENTO DOS DADOS ==========================================================
query_localizacao = "SELECT * FROM projeto_eleicoes_2020.TB_LOCALIZACAO"
localizacao = pd.read_sql(query_localizacao,engine)
#localizacao = pd.read_excel("Dados/localizacao.xlsx") #carregando dados de localização
query_cidade = "SELECT * FROM projeto_eleicoes_2020.TB_VOTOS_LOCALIDADE WHERE SG_UF = 'MG' AND CD_MUNICIPIO = '50415'"
dados_cidade = pd.read_sql(query_cidade,engine)
dados_cidade = pd.merge(dados_cidade,localizacao,on=["NR_LOCAL_VOTACAO"]) #Juntando dados de localização dos da cidade

#======================================= SEPARAÇÃO DOS DADOS ==========================================================

#----------------------------------------dados de estado e municipio ----------------------------------------------
#dados_estado_municipio = pd.read_csv("Dados/dados_estado_municipio.csv",sep = ';',encoding = 'ISO-8859-1')
query_estado_municipio = "SELECT SG_UF,CD_MUNICIPIO,NM_MUNICIPIO FROM TB_MUNICIPIOS"
dados_estado_municipio = pd.read_sql(query_estado_municipio,engine)
dados_estado_municipio.sort_values(by = ["SG_UF","NM_MUNICIPIO"],ascending=True,inplace = True) #ordenação de dados de estado e municipio
dados_municipios = dados_estado_municipio[["CD_MUNICIPIO","NM_MUNICIPIO"]]
dados_municipios.sort_values(by = 'NM_MUNICIPIO',ascending=True,inplace = True)
dados_municipios= dict(zip(dados_municipios["CD_MUNICIPIO"].unique(),dados_municipios['NM_MUNICIPIO'].unique()))

#---------------------------------------dados de cargo ------------------------------------------------------------
#dados_cargo = dados_cidade[["CD_CARGO","DS_CARGO"]]
dados_cargo = pd.read_sql("SELECT CD_CARGO,DS_CARGO FROM TB_CARGO",engine)
dados_cargo.sort_values(by = 'DS_CARGO',ascending=True,inplace = True)
dados_cargo= dict(zip(dados_cargo["CD_CARGO"].unique(),dados_cargo['DS_CARGO'].unique()))

#-------------------------------------------dados dos votos da eleicao -----------------------------------------------
dados_votos =  dados_cidade.groupby(['NM_LOCAL_VOTACAO_y','Latitude','Longitude'])['QT_VOTOS'].sum().reset_index()
dados_votos.sort_values(by='QT_VOTOS',ascending=False, inplace=True)
#print(dados_votos[['Latitude','Longitude']])

#------------------------------------------- Dados de candidatos -----------------------------------------------------
query_dados_candidato = "SELECT DISTINCT NR_CANDIDATO,NM_URNA_CANDIDATO FROM TB_CANDIDATOS WHERE SG_UF = 'MG' AND CD_MUNICIPIO = '50415'"
dados_candidato = pd.read_sql(query_dados_candidato,engine)
dados_candidato.sort_values(by = 'NM_URNA_CANDIDATO',ascending=True,inplace = True)
dados_candidato= dict(zip(dados_candidato["NR_CANDIDATO"].unique(),dados_candidato['NM_URNA_CANDIDATO'].unique()))

#------------------------------------------- Dados Partido ----------------------------------------------------------
query_partidos = "SELECT NR_PARTIDO,SG_PARTIDO FROM TB_PARTIDOS"
dados_partido = pd.read_sql(query_partidos,engine)
dados_partido.sort_values(by = 'SG_PARTIDO',ascending=True,inplace = True)
dados_partido= dict(zip(dados_partido["NR_PARTIDO"].unique(),dados_partido['SG_PARTIDO'].unique()))

#=========================INICIO DA CRIAÇÃO DO DASHBOARD ============================================================
app = dash.Dash(__name__,external_stylesheets=[dbc.themes.CYBORG])

#=========================== GRAFICO DO MAPA ===================================================================
fig = px.scatter_mapbox(dados_votos,
                        lat="Latitude",
                        lon="Longitude",
                        mapbox_style="open-street-map",
                        size="QT_VOTOS",
                        size_max=40,
                        hover_name = 'NM_LOCAL_VOTACAO_y',
                        #hover_data = ['QT_VOTOS'],
                        hover_data=dict(QT_VOTOS=True,
                                    Latitude=False, #not lon=False
                                    Longitude=False),
                        zoom = 13.5,
                        color="QT_VOTOS",
                        color_continuous_scale = "turbo_r"
            )

lat_initial = dados_votos["Latitude"].mean()
#print(lat_initial)
lon_initial = dados_votos["Longitude"].mean()
#print(lon_initial)
fig.update_layout(
   # width = 600,
    height = 700,
    autosize = True,
    margin= {"r": 0, "t": 0, "b": 0, "l": 0},
    mapbox_center = dict(
        lat=lat_initial,
        lon=lon_initial
    )
    #template="plotly_dark",
    #paper_bgcolor="rgba(0, 0, 0, 0)"

)


#================================================= TABELA DE VOTOS ============================================================================
fig2 = go.Figure(data=[go.Table(
                     columnwidth = [350,150],
                     header = dict(values = ['Local','Qtd de Votos'],line_color='#565656',font = dict(color= "Black",size = 20),height = 40),
                      cells = dict(values = [dados_votos["NM_LOCAL_VOTACAO_y"],
                                             dados_votos["QT_VOTOS"]],
                                             fill_color = "#242424",
                                             font = dict(color= "lightgrey",size = 14),
                                             line_color='#565656',
                                             height = 35
                                             ),
                        )
                       ])

fig2.update_layout(
    autosize = True,
    #height = 200,
    margin= {"r": 1, "t": 1, "b": 0, "l": 1},
    #background-color = "#242424"
)


#======================================================CONTAINER DO DASHBOARD ============================================================
app.layout = dbc.Container(children=[
            #=================================================== ROW DE ANALISE INDIVIDUAL =======================================================
            dbc.Row([
                html.H5(children="Mapa de votação para vereadores - Eleições 2020",style={"margin-top": "20px","color":"#CCCCCC"}),
                html.Hr(style = {"border":"2px solid #CCCCCC"}),
                #===============================================COLUNA DE FILTRO E TABELA ==========================================================
                dbc.Col([


            #============================================= ROW DE FILTROS DE LOCALIDADE==============================================================
            dbc.Row([
                #----------------------------------------------- Estado -------------------------------------------------------------------------
                html.H5(children="Filtros de localidade",style={"margin-top": "10px","color":"#CCCCCC"}),
                dbc.Col([
                   # html.H6(children="Selecione o Estado:",style={"margin-top": "10px"}),
                    dcc.Dropdown(id="Estado",
                             options=["AC","AL","AM","AP","BA",
                                      "CE","ES","GO","MA","MG",
                                      "MS","MT","PA","PB","PE",
                                      "PI","PR","RJ","RN","RO",
                                      "RR","RS","SC","SE","SP","TO"],
                             placeholder= "Selecione um Estado",
                             style={"background-color": "#242424","color":"black"},
                             value = "MG"
                             )

                ]),

                #---------------------------------------- Municipio --------------------------------------------------------------------------------
                dbc.Col([
                   # html.H6(children="Selecione o Municipio:", style={"margin-top": "10px"}),
                    dcc.Dropdown(id="Municipio",
                                 options=[{"label": i, "value": j} for j,i in dados_municipios.items()],
                                 placeholder="Selecione um Municipio",
                                 style={"background-color": "#242424", "color": "black"},
                                 value = "50415"
                                 )

                ]),
                html.Hr(style = {"border":"2px solid #CCCCCC","margin-top": "10px"}),
            ]),

#============================================= ROW DE FILTROS DE CARGO==============================================================
                    dbc.Row([
                        html.H5(children="Filtro de Cargo",style={"margin-top": "16px","color":"#CCCCCC"}),
                        #html.H6(children="Selecione um Cargo:",style={"margin-top": "10px"}),
                            dcc.Dropdown(id="Cargo",
                                     options=[{"label": j, "value": i} for i,j in dados_cargo.items()],
                                     placeholder= "Selecione um Cargo",
                                     style={"background-color": "#242424","color":"black"},
                                     value = '13'
                                     ),
                        html.Hr(style = {"border":"2px solid #CCCCCC","margin-top": "10px"}),
                    ]),

            #============================================= ROW DE FILTROS DO CANDIDATO ==============================================================
            dbc.Row([
                html.H5(children="Filtros de Candidatura",style={"margin-top": "10px","color":"#CCCCCC"}),
                dbc.Col([
                    #html.H6(children="Selecione o Partido:",style={"margin-top": "10px"}),
                    dcc.Dropdown(id="Partido",
                             options=[{"label": i, "value": j} for j,i in dados_partido.items()],
                             placeholder= "Selecione um Partido",
                             style={"background-color": "#242424","color":"black"}
                             )

                ]),

                dbc.Col([
                   # html.H6(children="Selecione o Candidato:", style={"margin-top": "10px"}),
                    dcc.Dropdown(id="Candidato",
                                 options=[{"label": i, "value": j} for j,i in dados_candidato.items()],
                                 placeholder="Selecione um Candidato",
                                 style={"background-color": "#242424", "color": "black"},
                                 value = '50000'
                                 )

                ]),
                html.Hr(style = {"border":"2px solid #CCCCCC","margin-top": "10px"}),
            ]),
            # ============================================= ROW DE TABELA DE VOTOS ==============================================================
            html.Div([
                html.H6(children="Votos por localidade",style={"margin-top": "10px","font-size":"22px","color":"#CCCCCC"}),
                #dcc.Graph(id="Tabela",figure=fig2),
            ],style={"margin-top": "10px","background-color": "#242424"}),
            dcc.Graph(id="Tabela",figure=fig2,style={"background-color": "#242424"})
        ],md=5,style={"background-color": "#242424"}),


#=================================================== SEGUNDA COLUNA: ==================================================================================
        dbc.Col([
            dbc.Row([
                html.H6(children="Dados do Candidato",style={"margin-top": "10px","font-size":"22px","color":"#CCCCCC"}),

                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Span("Partido"),
                            html.H5("--",style={"color": "#adfc92"}, id="partido_text"),
                        ])
                    ], color="light", outline=True, style={"margin-top": "10px",
                                                            "margin-bottom": "10px",
                                                           "box-shadow": "0 4px 4px 0 rgba(0, 0, 0, 0.15), 0 4px 20px 0 rgba(0, 0, 0, 0.19)",
                                                           "color": "#FFFFFF"}
                    )
                ],md=4),

                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Span("Resultado"),
                            html.H5("--",style={"color": "#389fd6"}, id="resultado_text")
                        ])
                    ], color="light", outline=True, style={"margin-top": "10px",
                                                            "margin-bottom": "10px",
                                                           "box-shadow": "0 4px 4px 0 rgba(0, 0, 0, 0.15), 0 4px 20px 0 rgba(0, 0, 0, 0.19)",
                                                           "color": "#FFFFFF"}
                    )
                ],md=4),


                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Span("Total de Votos", className="card-text"),
                            html.H5("--",style={"color": "#DF2935"}, id="total_votos_text"),
                        ])
                    ], color="light", outline=True, style={"margin-top": "10px",
                                                            "margin-bottom": "10px",
                                                           "box-shadow": "0 4px 4px 0 rgba(0, 0, 0, 0.15), 0 4px 20px 0 rgba(0, 0, 0, 0.19)",
                                                           "color": "#FFFFFF"}
                    )
                ],md=4),
            ]),

            dbc.Row([
                dcc.Loading(id = "loading_map",type = "default", children=[dcc.Graph(id="mapa",figure=fig,style={"heigth":"100hv"})])
            ],style={"heigth":"100hv"}),

        ],md=7),
    ],style={"margin": "-25px", "padding": "25px","background-color": "#242424"})
],fluid=True,style={"autosize":"True"})

#========================================================================================================================

#filtro de estado
@app.callback(
Output("Municipio","options"),
    [Input("Estado","value")]
)
def seleciona_estado_municipio(uf_estado):
    query_municipio = f"SELECT DISTINCT CD_MUNICIPIO,NM_MUNICIPIO FROM TB_MUNICIPIOS WHERE SG_UF = '{uf_estado}'"
    aux = pd.read_sql(query_municipio,engine)
    aux.sort_values(by='NM_MUNICIPIO', ascending=True, inplace=True)
    aux = dict(zip(aux["CD_MUNICIPIO"], aux['NM_MUNICIPIO']))
    return [{"label": i, "value": j} for j,i in aux.items()]

#filtro para selecionar candidato
@app.callback(
    Output("Candidato","options"),
    [Input("Estado","value"),Input("Municipio","value"),Input("Partido","value"),Input("Cargo","value")]
)
def seleciona_candidato(UF_estado,cidade,NR_partido,CD_CARGO):
    if NR_partido is None:
        query_dados_candidato = f"SELECT DISTINCT NR_CANDIDATO,NM_URNA_CANDIDATO FROM TB_CANDIDATOS WHERE SG_UF = '{UF_estado}' AND CD_MUNICIPIO = '{cidade} ' AND CD_CARGO = '{CD_CARGO}'"
        dados_candidato = pd.read_sql(query_dados_candidato,engine)
        dados_candidato.sort_values(by='NM_URNA_CANDIDATO', ascending=True, inplace=True)
        dados_candidato = dict(zip(dados_candidato["NR_CANDIDATO"].unique(), dados_candidato['NM_URNA_CANDIDATO'].unique()))
        return [{"label": i, "value": j} for j,i in dados_candidato.items()]
    else:
        query_dados_candidato = f"SELECT DISTINCT NR_CANDIDATO,NM_URNA_CANDIDATO FROM TB_CANDIDATOS WHERE SG_UF = '{UF_estado}' AND CD_MUNICIPIO = '{cidade} ' AND CD_CARGO = '{CD_CARGO}' AND NR_PARTIDO  = '{NR_partido}' "
        dados_candidato = pd.read_sql(query_dados_candidato, engine)
        dados_candidato.sort_values(by='NM_URNA_CANDIDATO', ascending=True, inplace=True)
        dados_candidato = dict(zip(dados_candidato["NR_CANDIDATO"].unique(), dados_candidato['NM_URNA_CANDIDATO'].unique()))
        return [{"label": i, "value": j} for j, i in dados_candidato.items()]

#atualizacao de tabela de votos
@app.callback(
    [Output("Tabela","figure"),
     Output("mapa","figure"),
     Output("total_votos_text","children"),
     Output("partido_text","children"),
     Output("resultado_text","children")
     ],
    [Input("Candidato","value"),
    Input("Partido","value"),
     Input("Estado","value"),
     Input("Municipio","value")]
)
def atualiza_tabela(nr_candidato,nr_partido,estado,municipio):
    if nr_candidato is not None:
        query_cidade = f"SELECT * FROM TB_VOTOS_LOCALIDADE WHERE SG_UF = '{estado}' AND CD_MUNICIPIO = '{municipio}' AND NR_VOTAVEL = '{nr_candidato}'"
        dados_cidade = pd.read_sql(query_cidade, engine)
        query_localizacao = "SELECT * FROM projeto_eleicoes_2020.TB_LOCALIZACAO"
        localizacao = pd.read_sql(query_localizacao, engine)
        dados_cidade = pd.merge(dados_cidade, localizacao, on=["NR_LOCAL_VOTACAO"])  # Juntando dados de localização dos da cidade
        #dados_candidato = dados_cidade[dados_cidade["NR_VOTAVEL"] == int(nr_candidato)]
        dados_votos = dados_cidade.groupby(['NM_LOCAL_VOTACAO_y', 'Latitude', 'Longitude'])['QT_VOTOS'].sum().reset_index()
        dados_votos.sort_values(by='QT_VOTOS', ascending=False, inplace=True)
        initial_tam = 35
        fig2 = go.Figure(data=[go.Table(
            columnwidth=[350, 150],
            header=dict(values=['Local', 'Qtd de Votos'], line_color='#565656', font=dict(color="Black", size=20),
                        height=40),
            cells=dict(values=[dados_votos["NM_LOCAL_VOTACAO_y"],
                               dados_votos["QT_VOTOS"]],
                       fill_color="#242424",
                       font=dict(color="lightgrey", size=14),
                       line_color='#565656',
                       height=initial_tam
                       ),

        )
        ])

        fig = px.scatter_mapbox(dados_votos,
                                lat="Latitude",
                                lon="Longitude",
                                mapbox_style="open-street-map",
                                size="QT_VOTOS",
                                size_max=40,
                                hover_name='NM_LOCAL_VOTACAO_y',
                                hover_data=dict(QT_VOTOS=True,
                                                Latitude=False,  # not lon=False
                                                Longitude=False),
                                zoom=13.5,
                                color="QT_VOTOS",
                                color_continuous_scale = "turbo_r"
                                )

        lat_initial = dados_votos["Latitude"].mean()
        lon_initial = dados_votos["Longitude"].mean()
        fig.update_layout(
            # width = 600,
            height=700,
            autosize=True,
            margin={"r": 0, "t": 0, "b": 0, "l": 0},
            mapbox_center=dict(
                lat=lat_initial,
                lon=lon_initial
            )
            # template="plotly_dark",
            # paper_bgcolor="rgba(0, 0, 0, 0)"

        )


        num_linhas = len(dados_votos.index)
        tam = initial_tam
        if num_linhas > 10:
            tam = 40 + initial_tam*12
        else:
            tam = initial_tam*num_linhas + 40

        fig2.update_layout(
            autosize=True,
            height=tam,
            margin={"r": 1, "t": 1, "b": 0, "l": 1}
        )

        total_votos = dados_votos["QT_VOTOS"].sum()
        #print(total_votos)

        # percent = dados_cidade["QT_VOTOS"].sum()
        # percent_votos_geral = (total_votos/percent)*100
        # percent_votos_geral = round(percent_votos_geral,2)
        # percent_votos_geral = str(percent_votos_geral) + '%'

        query_candidato_2 = f"select * from TB_CONSULTA_CAND where SG_UF = '{estado}' and NR_CANDIDATO = '{nr_candidato}' and SG_UE = '{municipio}' "
        # caminho_2 = "Dados/dados_candidatos/consulta_cand_2020_" + estado + ".csv"
        # #print(caminho_2)
        # candidato = pd.read_csv(caminho_2, sep=";", encoding="ISO-8859-1")
        # #print(candidato)
        # candidato = candidato[(candidato["NR_CANDIDATO"] == int(nr_candidato)) & (candidato["SG_UE"] == int(municipio))]
        candidato = pd.read_sql(query_candidato_2,engine)
        #print(candidato)
        partido = str(candidato["SG_PARTIDO"].iloc[0])
        #print(partido)
        Resultado = str(candidato["DS_SIT_TOT_TURNO"].iloc[0])
        #print(Resultado)
        return (fig2,fig,total_votos,partido,Resultado)



if __name__=="__main__":
    app.run_server(debug=True)








