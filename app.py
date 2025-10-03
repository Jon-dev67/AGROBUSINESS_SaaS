import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import json
import sqlite3
import hashlib
import requests
import time
from streamlit_option_menu import option_menu
import io
import psycopg2
from psycopg2.extras import RealDictCursor
import os

# ================================
# CONFIGURAÇÕES INICIAIS
# ================================
st.set_page_config(
    page_title="🌱 AgroGestão - Gestão Agrícola",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🌱"
)

# Aplicar tema escuro personalizado
def apply_dark_theme():
    st.markdown("""
    <style>
    .main {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    .stButton>button {
        background-color: #2d5016;
        color: white;
        border-radius: 8px;
        padding: 10px 24px;
        border: none;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #3a6520;
        color: white;
    }
    .card {
        background-color: #1a1a1a;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: #1a1a1a;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border-left: 4px solid #2d5016;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #FAFAFA;
    }
    .error {
        color: #ff4b4b;
    }
    .success {
        color: #2ecc71;
    }
    </style>
    """, unsafe_allow_html=True)

apply_dark_theme()

# ================================
# CONSTANTES E CONFIGURAÇÕES
# ================================
API_KEY = "eef20bca4e6fb1ff14a81a3171de5cec"
DEFAULT_CITY = "Londrina"

# Configurações do PostgreSQL
DB_CONFIG = {
    "host": "dpg-d361csili9vc738rea90-a.oregon-postgres.render.com",
    "database": "postgresql_agro",
    "user": "postgresql_agro_user",
    "password": "gl5pErtk8tC2vqFLfswn7B7ocoxK7gk5",
    "port": "5432"
}

# ================================
# FUNÇÕES DE BANCO DE DADOS (POSTGRESQL)
# ================================
def get_db_connection():
    """Estabelece conexão com o PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=DB_CONFIG["host"],
            database=DB_CONFIG["database"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            port=DB_CONFIG["port"]
        )
        return conn
    except Exception as e:
        st.error(f"Erro ao conectar com o banco de dados: {str(e)}")
        return None

def init_db():
    """Inicializa as tabelas no PostgreSQL"""
    conn = get_db_connection()
    if conn is None:
        return
    
    try:
        c = conn.cursor()
        
        # Tabela de produções
        c.execute('''CREATE TABLE IF NOT EXISTS productions
                     (id SERIAL PRIMARY KEY,
                      date TEXT NOT NULL,
                      local TEXT NOT NULL,
                      product TEXT NOT NULL,
                      first_quality REAL NOT NULL,
                      second_quality REAL NOT NULL,
                      third_quality REAL NOT NULL,
                      temperature REAL,
                      humidity REAL,
                      rain REAL,
                      weather_data TEXT,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        # Tabela de insumos
        c.execute('''CREATE TABLE IF NOT EXISTS inputs
                     (id SERIAL PRIMARY KEY,
                      date TEXT NOT NULL,
                      type TEXT NOT NULL,
                      description TEXT NOT NULL,
                      quantity REAL NOT NULL,
                      unit TEXT NOT NULL,
                      cost REAL NOT NULL,
                      location TEXT,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        conn.commit()
        st.success("Banco de dados inicializado com sucesso!")
    except Exception as e:
        st.error(f"Erro ao inicializar banco de dados: {str(e)}")
    finally:
        conn.close()

def save_production(date, local, product, first_quality, second_quality, third_quality, temperature, humidity, rain, weather_data):
    conn = get_db_connection()
    if conn is None:
        return False
    
    try:
        c = conn.cursor()
        c.execute("INSERT INTO productions (date, local, product, first_quality, second_quality, third_quality, temperature, humidity, rain, weather_data) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                  (date, local, product, first_quality, second_quality, third_quality, temperature, humidity, rain, weather_data))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar produção: {str(e)}")
        return False
    finally:
        conn.close()

def load_productions():
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()
    
    try:
        df = pd.read_sql_query("SELECT * FROM productions ORDER BY date DESC", conn)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar produções: {str(e)}")
        return pd.DataFrame()
    finally:
        conn.close()

def delete_production(production_id):
    conn = get_db_connection()
    if conn is None:
        return False
    
    try:
        c = conn.cursor()
        c.execute("DELETE FROM productions WHERE id = %s", (production_id,))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Erro ao excluir produção: {str(e)}")
        return False
    finally:
        conn.close()

def save_input(date, input_type, description, quantity, unit, cost, location):
    conn = get_db_connection()
    if conn is None:
        return False
    
    try:
        c = conn.cursor()
        c.execute("INSERT INTO inputs (date, type, description, quantity, unit, cost, location) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                  (date, input_type, description, quantity, unit, cost, location))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar insumo: {str(e)}")
        return False
    finally:
        conn.close()

def load_inputs():
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()
    
    try:
        df = pd.read_sql_query("SELECT * FROM inputs ORDER BY date DESC", conn)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar insumos: {str(e)}")
        return pd.DataFrame()
    finally:
        conn.close()

# ================================
# FUNÇÕES DE API CLIMÁTICA
# ================================
def get_weather_data(city):
    """Busca dados climáticos da API OpenWeather"""
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric&lang=pt_br"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "temperature": data["main"]["temp"],
                "humidity": data["main"]["humidity"],
                "rain": data.get("rain", {}).get("1h", 0) if "rain" in data else 0,
                "description": data["weather"][0]["description"],
                "city": data["name"],
                "country": data["sys"]["country"],
                "icon": data["weather"][0]["icon"]
            }
        else:
            st.error(f"Erro ao buscar dados climáticos: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Erro de conexão com a API climática: {str(e)}")
        return None

# ================================
# FUNÇÕES DE CÁLCULO FINANCEIRO
# ================================
def calculate_financials(productions_df, inputs_df, price_first, price_second, price_third):
    if productions_df.empty:
        return {
            "total_revenue": 0,
            "first_quality_revenue": 0,
            "second_quality_revenue": 0,
            "third_quality_revenue": 0,
            "total_costs": 0,
            "profit": 0,
            "profit_margin": 0
        }
    
    # Calcular receita
    first_revenue = productions_df['first_quality'].sum() * price_first
    second_revenue = productions_df['second_quality'].sum() * price_second
    third_revenue = productions_df['third_quality'].sum() * price_third
    total_revenue = first_revenue + second_revenue + third_revenue
    
    # Calcular custos
    total_costs = inputs_df['cost'].sum() if not inputs_df.empty else 0
    
    # Calcular lucro e margem
    profit = total_revenue - total_costs
    profit_margin = (profit / total_revenue * 100) if total_revenue > 0 else 0
    
    return {
        "total_revenue": total_revenue,
        "first_quality_revenue": first_revenue,
        "second_quality_revenue": second_revenue,
        "third_quality_revenue": third_revenue,
        "total_costs": total_costs,
        "profit": profit,
        "profit_margin": profit_margin
    }

# ================================
# DASHBOARD PRINCIPAL
# ================================
def show_dashboard():
    st.title("📊 Dashboard AgroGestão")
    
    # Carregar dados
    productions_df = load_productions()
    inputs_df = load_inputs()
    
    # Inputs de preços no dashboard
    st.sidebar.header("💰 Configuração de Preços")
    st.sidebar.info("Configure os preços por qualidade para calcular a receita")
    
    price_first = st.sidebar.number_input("Preço 1ª Qualidade (R$/cx)", min_value=0.0, value=0.0, step=0.5)
    price_second = st.sidebar.number_input("Preço 2ª Qualidade (R$/cx)", min_value=0.0, value=0.0, step=0.5)
    price_third = st.sidebar.number_input("Preço 3ª Qualidade (R$/cx)", min_value=0.0, value=0.0, step=0.5)
    
    # Filtros na sidebar
    st.sidebar.header("Filtros")
    
    if not productions_df.empty:
        min_date = pd.to_datetime(productions_df['date']).min().date()
        max_date = pd.to_datetime(productions_df['date']).max().date()
        
        date_range = st.sidebar.date_input(
            "Período",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        locations = st.sidebar.multiselect(
            "Locais",
            options=productions_df['local'].unique(),
            default=productions_df['local'].unique()
        )
        
        products = st.sidebar.multiselect(
            "Culturas",
            options=productions_df['product'].unique(),
            default=productions_df['product'].unique()
        )
        
        # Aplicar filtros
        try:
            start_date, end_date = date_range
        except:
            start_date, end_date = min_date, max_date
        
        filtered_df = productions_df[
            (pd.to_datetime(productions_df['date']).dt.date >= start_date) &
            (pd.to_datetime(productions_df['date']).dt.date <= end_date) &
            (productions_df['local'].isin(locations)) &
            (productions_df['product'].isin(products))
        ]
    else:
        filtered_df = pd.DataFrame()
    
    # Calcular métricas financeiras
    financials = calculate_financials(
        filtered_df if not filtered_df.empty else productions_df, 
        inputs_df, 
        price_first, 
        price_second, 
        price_third
    )
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        if not filtered_df.empty:
            total_boxes = filtered_df['first_quality'].sum() + filtered_df['second_quality'].sum() + filtered_df['third_quality'].sum()
        else:
            total_boxes = (productions_df['first_quality'].sum() + 
                          productions_df['second_quality'].sum() + 
                          productions_df['third_quality'].sum()) if not productions_df.empty else 0
        st.metric("Total Produzido", f"{total_boxes:,.0f} cx")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Receita Total", f"R$ {financials['total_revenue']:,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Custos Totais", f"R$ {financials['total_costs']:,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Lucro Líquido", f"R$ {financials['profit']:,.2f}", 
                 f"{financials['profit_margin']:.1f}%" if financials['profit_margin'] != 0 else "0%")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Detalhamento da receita por qualidade
    if price_first > 0 or price_second > 0 or price_third > 0:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📈 Detalhamento da Receita")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Receita 1ª Qualidade", f"R$ {financials['first_quality_revenue']:,.2f}")
        with col2:
            st.metric("Receita 2ª Qualidade", f"R$ {financials['second_quality_revenue']:,.2f}")
        with col3:
            st.metric("Receita 3ª Qualidade", f"R$ {financials['third_quality_revenue']:,.2f}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Gráficos - Primeira linha
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Produção por Cultura")
        
        if not filtered_df.empty:
            production_by_product = filtered_df.groupby('product')[['first_quality', 'second_quality', 'third_quality']].sum().reset_index()
            production_by_product['total'] = production_by_product['first_quality'] + production_by_product['second_quality'] + production_by_product['third_quality']
            
            fig = px.bar(production_by_product, x='product', y='total', 
                         color='product', color_discrete_sequence=px.colors.qualitative.Set3)
            fig.update_layout(showlegend=False, plot_bgcolor='rgba(0,0,0,0)', 
                             paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
            st.plotly_chart(fig, use_container_width=True)
        elif not productions_df.empty:
            production_by_product = productions_df.groupby('product')[['first_quality', 'second_quality', 'third_quality']].sum().reset_index()
            production_by_product['total'] = production_by_product['first_quality'] + production_by_product['second_quality'] + production_by_product['third_quality']
            
            fig = px.bar(production_by_product, x='product', y='total', 
                         color='product', color_discrete_sequence=px.colors.qualitative.Set3)
            fig.update_layout(showlegend=False, plot_bgcolor='rgba(0,0,0,0)', 
                             paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum dado de produção disponível.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Produção por Área/Local")
        
        if not filtered_df.empty:
            production_by_location = filtered_df.groupby('local')[['first_quality', 'second_quality', 'third_quality']].sum().reset_index()
            production_by_location['total'] = production_by_location['first_quality'] + production_by_location['second_quality'] + production_by_location['third_quality']
            
            fig = px.pie(production_by_location, values='total', names='local',
                         color_discrete_sequence=px.colors.qualitative.Set3)
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                             font=dict(color='white'))
            st.plotly_chart(fig, use_container_width=True)
        elif not productions_df.empty:
            production_by_location = productions_df.groupby('local')[['first_quality', 'second_quality', 'third_quality']].sum().reset_index()
            production_by_location['total'] = production_by_location['first_quality'] + production_by_location['second_quality'] + production_by_location['third_quality']
            
            fig = px.pie(production_by_location, values='total', names='local',
                         color_discrete_sequence=px.colors.qualitative.Set3)
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                             font=dict(color='white'))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum dado de produção disponível.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Gráficos - Segunda linha
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Distribuição de Qualidade por Cultura")
        
        if not filtered_df.empty:
            quality_data = []
            for product in filtered_df['product'].unique():
                product_data = filtered_df[filtered_df['product'] == product]
                total = product_data['first_quality'].sum() + product_data['second_quality'].sum() + product_data['third_quality'].sum()
                first_percent = (product_data['first_quality'].sum() / total * 100) if total > 0 else 0
                second_percent = (product_data['second_quality'].sum() / total * 100) if total > 0 else 0
                third_percent = (product_data['third_quality'].sum() / total * 100) if total > 0 else 0
                
                quality_data.append({
                    'product': product,
                    '1ª Qualidade': first_percent,
                    '2ª Qualidade': second_percent,
                    '3ª Qualidade': third_percent
                })
            
            quality_df = pd.DataFrame(quality_data)
            fig = px.bar(quality_df, x='product', y=['1ª Qualidade', '2ª Qualidade', '3ª Qualidade'], 
                         barmode='stack', color_discrete_sequence=['#2ecc71', '#f1c40f', '#e74c3c'])
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                             font=dict(color='white'), yaxis_title="Percentual (%)")
            st.plotly_chart(fig, use_container_width=True)
        elif not productions_df.empty:
            quality_data = []
            for product in productions_df['product'].unique():
                product_data = productions_df[productions_df['product'] == product]
                total = product_data['first_quality'].sum() + product_data['second_quality'].sum() + product_data['third_quality'].sum()
                first_percent = (product_data['first_quality'].sum() / total * 100) if total > 0 else 0
                second_percent = (product_data['second_quality'].sum() / total * 100) if total > 0 else 0
                third_percent = (product_data['third_quality'].sum() / total * 100) if total > 0 else 0
                
                quality_data.append({
                    'product': product,
                    '1ª Qualidade': first_percent,
                    '2ª Qualidade': second_percent,
                    '3ª Qualidade': third_percent
                })
            
            quality_df = pd.DataFrame(quality_data)
            fig = px.bar(quality_df, x='product', y=['1ª Qualidade', '2ª Qualidade', '3ª Qualidade'], 
                         barmode='stack', color_discrete_sequence=['#2ecc71', '#f1c40f', '#e74c3c'])
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                             font=dict(color='white'), yaxis_title="Percentual (%)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum dado de produção disponível.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Evolução temporal da produção
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Evolução Temporal da Produção")
    
    if not filtered_df.empty:
        time_series = filtered_df.copy()
        time_series['date'] = pd.to_datetime(time_series['date'])
        time_series = time_series.groupby('date')[['first_quality', 'second_quality', 'third_quality']].sum().reset_index()
        
        fig = px.line(time_series, x='date', y=['first_quality', 'second_quality', 'third_quality'],
                     color_discrete_sequence=['#2ecc71', '#f1c40f', '#e74c3c'])
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                         font=dict(color='white'), yaxis_title="Caixas")
        st.plotly_chart(fig, use_container_width=True)
    elif not productions_df.empty:
        time_series = productions_df.copy()
        time_series['date'] = pd.to_datetime(time_series['date'])
        time_series = time_series.groupby('date')[['first_quality', 'second_quality', 'third_quality']].sum().reset_index()
        
        fig = px.line(time_series, x='date', y=['first_quality', 'second_quality', 'third_quality'],
                     color_discrete_sequence=['#2ecc71', '#f1c40f', '#e74c3c'])
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                         font=dict(color='white'), yaxis_title="Caixas")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhum dado de produção disponível.")
    st.markdown('</div>', unsafe_allow_html=True)

# ================================
# PÁGINA DE CADASTRO DE PRODUÇÃO
# ================================
def show_production_page():
    st.title("📝 Cadastro de Produção")
    
    # Buscar dados climáticos automaticamente
    weather_data = get_weather_data(DEFAULT_CITY)
    
    if weather_data:
        st.sidebar.header("Dados Climáticos Atuais")
        st.sidebar.success("Dados climáticos carregados automaticamente!")
        st.sidebar.write(f"**Cidade:** {weather_data['city']}")
        st.sidebar.write(f"**Temperatura:** {weather_data['temperature']}°C")
        st.sidebar.write(f"**Umidade:** {weather_data['humidity']}%")
        st.sidebar.write(f"**Chuva:** {weather_data['rain']}mm")
        st.sidebar.write(f"**Condição:** {weather_data['description']}")
    else:
        st.sidebar.warning("Não foi possível carregar dados climáticos")

    with st.form("production_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            date = st.date_input("Data", value=datetime.now())
            location = st.text_input("Local/Estufa")
            product = st.text_input("Produto")
        
        with col2:
            first_quality = st.number_input("Caixas 1ª Qualidade", min_value=0.0, step=0.5)
            second_quality = st.number_input("Caixas 2ª Qualidade", min_value=0.0, step=0.5)
            third_quality = st.number_input("Caixas 3ª Qualidade", min_value=0.0, step=0.5)
        
        # Usar dados da API automaticamente
        if weather_data:
            temperature = weather_data['temperature']
            humidity = weather_data['humidity']
            rain = weather_data['rain']
            
            st.info(f"Dados climáticos serão salvos: Temperatura: {temperature}°C, Umidade: {humidity}%, Chuva: {rain}mm")
        else:
            temperature = st.number_input("Temperatura (°C)", value=25.0)
            humidity = st.slider("Umidade (%)", 0, 100, 60)
            rain = st.number_input("Chuva (mm)", min_value=0.0, value=0.0, step=0.1)
        
        submitted = st.form_submit_button("Salvar Produção")
        
        if submitted:
            if not all([location, product]):
                st.error("Preencha todos os campos obrigatórios.")
            else:
                success = save_production(
                    date.isoformat(), 
                    location, 
                    product, 
                    first_quality, 
                    second_quality, 
                    third_quality,
                    temperature, 
                    humidity, 
                    rain,
                    json.dumps(weather_data) if weather_data else ""
                )
                if success:
                    st.success("Produção registrada com sucesso!")
                else:
                    st.error("Erro ao salvar produção. Verifique a conexão com o banco de dados.")
    
    # Mostrar dados recentes com opção de exclusão
    productions_df = load_productions()
        
    if not productions_df.empty:
        st.subheader("Produções Recentes")
        
        # Adicionar opção de exclusão
        for idx, row in productions_df.tail(10).iterrows():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            with col1:
                st.write(f"{row['date']} - {row['product']} em {row['local']}")
            with col2:
                st.write(f"1ª: {row['first_quality']}cx, 2ª: {row['second_quality']}cx, 3ª: {row['third_quality']}cx")
            with col3:
                st.write(f"T: {row['temperature']}°C, U: {row['humidity']}%")
            with col4:
                if st.button("🗑️", key=f"delete_{row['id']}"):
                    if delete_production(row['id']):
                        st.success("Registro excluído com sucesso!")
                        st.rerun()
                    else:
                        st.error("Erro ao excluir registro.")
        
        # Adicionar botão para baixar dados em Excel
        st.markdown("---")
        st.subheader("Exportar Dados")
        
        # Filtrar dados para exportação
        min_date = pd.to_datetime(productions_df['date']).min().date()
        max_date = pd.to_datetime(productions_df['date']).max().date()
        
        export_date_range = st.date_input(
            "Período para Exportação",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="export_date_range"
        )
        
        try:
            export_start_date, export_end_date = export_date_range
        except:
            export_start_date, export_end_date = min_date, max_date
        
        # Filtrar dados para exportação
        export_df = productions_df[
            (pd.to_datetime(productions_df['date']).dt.date >= export_start_date) &
            (pd.to_datetime(productions_df['date']).dt.date <= export_end_date)
        ]
        
        if not export_df.empty:
            # Criar Excel em memória
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                export_df.to_excel(writer, sheet_name='Produções', index=False)
                
                # Adicionar formatação
                workbook = writer.book
                worksheet = writer.sheets['Produções']
                
                # Formatar cabeçalhos
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'fg_color': '#2d5016',
                    'font_color': 'white',
                    'border': 1
                })
                
                # Aplicar formatação aos cabeçalhos
                for col_num, value in enumerate(export_df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # Ajustar largura das colunas
                for idx, col in enumerate(export_df.columns):
                    max_len = max(export_df[col].astype(str).map(len).max(), len(col)) + 2
                    worksheet.set_column(idx, idx, max_len)
            
            output.seek(0)
            
            # Botão de download
            st.download_button(
                label="📥 Baixar Dados em Excel",
                data=output,
                file_name=f"producoes_{export_start_date}_{export_end_date}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("Nenhum dado disponível para o período selecionado.")

# ================================
# PÁGINA DE CADASTRO DE INSUMOS
# ================================
def show_inputs_page():
    st.title("💰 Cadastro de Insumos")
    
    with st.form("inputs_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            date = st.date_input("Data", value=datetime.now())
            input_type = st.selectbox("Tipo de Insumo", 
                                     ["Semente", "Fertilizante", "Defensivo", "Mão de Obra", "Equipamento", "Outros"])
            description = st.text_input("Descrição")
        
        with col2:
            quantity = st.number_input("Quantidade", min_value=0.0, step=0.1)
            unit = st.selectbox("Unidade", ["kg", "L", "un", "h", "sc", "outro"])
            cost = st.number_input("Custo (R$)", min_value=0.0, step=0.01)
        
        location = st.text_input("Local aplicado")
        
        submitted = st.form_submit_button("Salvar Insumo")
        
        if submitted:
            if not all([input_type, description, quantity > 0, cost > 0]):
                st.error("Preencha todos os campos obrigatórios.")
            else:
                success = save_input(
                    date.isoformat(), 
                    input_type, 
                    description, 
                    quantity, 
                    unit, 
                    cost, 
                    location
                )
                if success:
                    st.success("Insumo registrado com sucesso!")
                else:
                    st.error("Erro ao salvar insumo. Verifique a conexão com o banco de dados.")
    
    # Mostrar dados recentes
    inputs_df = load_inputs()
        
    if not inputs_df.empty:
        st.subheader("Insumos Recentes")
        st.dataframe(inputs_df.tail(10), use_container_width=True)
        
        # Adicionar botão para baixar dados em Excel
        st.markdown("---")
        st.subheader("Exportar Dados")
        
        # Filtrar dados para exportação
        min_date = pd.to_datetime(inputs_df['date']).min().date()
        max_date = pd.to_datetime(inputs_df['date']).max().date()
        
        export_date_range = st.date_input(
            "Período para Exportação",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="export_inputs_date_range"
        )
        
        try:
            export_start_date, export_end_date = export_date_range
        except:
            export_start_date, export_end_date = min_date, max_date
        
        # Filtrar dados para exportação
        export_df = inputs_df[
            (pd.to_datetime(inputs_df['date']).dt.date >= export_start_date) &
            (pd.to_datetime(inputs_df['date']).dt.date <= export_end_date)
        ]
        
        if not export_df.empty:
            # Criar Excel em memória
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                export_df.to_excel(writer, sheet_name='Insumos', index=False)
                
                # Adicionar formatação
                workbook = writer.book
                worksheet = writer.sheets['Insumos']
                
                # Formatar cabeçalhos
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'fg_color': '#2d5016',
                    'font_color': 'white',
                    'border': 1
                })
                
                # Aplicar formatação aos cabeçalhos
                for col_num, value in enumerate(export_df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # Ajustar largura das colunas
                for idx, col in enumerate(export_df.columns):
                    max_len = max(export_df[col].astype(str).map(len).max(), len(col)) + 2
                    worksheet.set_column(idx, idx, max_len)
            
            output.seek(0)
            
            # Botão de download
            st.download_button(
                label="📥 Baixar Dados em Excel",
                data=output,
                file_name=f"insumos_{export_start_date}_{export_end_date}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("Nenhum dado disponível para o período selecionado.")

# ================================
# PÁGINA DE RELATÓRIOS (REFATORADA)
# ================================
def show_reports_page():
    st.title("📋 Relatórios")
    
    productions_df = load_productions()
    inputs_df = load_inputs()
    
    if productions_df.empty:
        st.warning("Nenhum dado disponível para gerar relatórios.")
        return
    
    # Inputs de preços para relatórios
    st.sidebar.header("💰 Preços para Relatórios")
    price_first = st.sidebar.number_input("Preço 1ª Qualidade (R$/cx)", min_value=0.0, value=0.0, step=0.5, key="report_price_first")
    price_second = st.sidebar.number_input("Preço 2ª Qualidade (R$/cx)", min_value=0.0, value=0.0, step=0.5, key="report_price_second")
    price_third = st.sidebar.number_input("Preço 3ª Qualidade (R$/cx)", min_value=0.0, value=0.0, step=0.5, key="report_price_third")
    
    # Filtros para relatórios
    st.sidebar.header("Filtros do Relatório")
    
    min_date = pd.to_datetime(productions_df['date']).min().date()
    max_date = pd.to_datetime(productions_df['date']).max().date()
    
    report_date_range = st.sidebar.date_input(
        "Período do Relatório",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    # Filtro por local
    all_locations = productions_df['local'].unique().tolist()
    selected_locations = st.sidebar.multiselect(
        "Filtrar por Local",
        options=all_locations,
        default=all_locations,
        help="Selecione os locais para filtrar"
    )
    
    # Filtro por cultura
    all_products = productions_df['product'].unique().tolist()
    selected_products = st.sidebar.multiselect(
        "Filtrar por Cultura",
        options=all_products,
        default=all_products,
        help="Selecione as culturas para filtrar"
    )
    
    # Tipo de relatório
    report_type = st.sidebar.selectbox(
        "Tipo de Relatório",
        ["Produção Detalhada", "Resumo Financeiro", "Análise de Qualidade", "Custos e Insumos", "Análise por Local"]
    )
    
    try:
        start_date, end_date = report_date_range
    except:
        start_date, end_date = min_date, max_date
    
    # Filtrar dados
    filtered_prod = productions_df[
        (pd.to_datetime(productions_df['date']).dt.date >= start_date) &
        (pd.to_datetime(productions_df['date']).dt.date <= end_date) &
        (productions_df['local'].isin(selected_locations)) &
        (productions_df['product'].isin(selected_products))
    ]
    
    filtered_inputs = inputs_df[
        (pd.to_datetime(inputs_df['date']).dt.date >= start_date) &
        (pd.to_datetime(inputs_df['date']).dt.date <= end_date)
    ]
    
    if filtered_prod.empty:
        st.warning("Nenhum dado encontrado para o período selecionado.")
        return
    
    # Exibir resumo dos filtros aplicados
    st.sidebar.markdown("---")
    st.sidebar.subheader("Resumo dos Filtros")
    st.sidebar.write(f"**Período:** {start_date} a {end_date}")
    st.sidebar.write(f"**Locais selecionados:** {len(selected_locations)}")
    st.sidebar.write(f"**Culturas selecionadas:** {len(selected_products)}")
    st.sidebar.write(f"**Registros encontrados:** {len(filtered_prod)}")
    
    # Gerar relatório selecionado
    if report_type == "Produção Detalhada":
        st.header("📊 Relatório de Produção Detalhada")
        st.write(f"**Período:** {start_date} a {end_date}")
        st.write(f"**Locais:** {', '.join(selected_locations)}")
        st.write(f"**Culturas:** {', '.join(selected_products)}")
        
        # Resumo estatístico
        total_first = filtered_prod['first_quality'].sum()
        total_second = filtered_prod['second_quality'].sum()
        total_third = filtered_prod['third_quality'].sum()
        total_boxes = total_first + total_second + total_third
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total de Caixas", f"{total_boxes:,.0f}")
        with col2:
            st.metric("1ª Qualidade", f"{total_first:,.0f}")
        with col3:
            st.metric("2ª Qualidade", f"{total_second:,.0f}")
        with col4:
            st.metric("3ª Qualidade", f"{total_third:,.0f}")
        
        # Dados detalhados
        st.subheader("Dados Detalhados")
        st.dataframe(filtered_prod, use_container_width=True)
        
        # Exportar dados
        if st.button("📥 Exportar para Excel", key="export_detailed"):
            export_to_excel(filtered_prod, "relatorio_producao_detalhada", start_date, end_date)
    
    elif report_type == "Resumo Financeiro":
        st.header("💰 Relatório Financeiro")
        st.write(f"**Período:** {start_date} a {end_date}")
        st.write(f"**Locais:** {', '.join(selected_locations)}")
        st.write(f"**Culturas:** {', '.join(selected_products)}")
        
        financials = calculate_financials(filtered_prod, filtered_inputs, price_first, price_second, price_third)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Receita Total", f"R$ {financials['total_revenue']:,.2f}")
        with col2:
            st.metric("Custos Totais", f"R$ {financials['total_costs']:,.2f}")
        with col3:
            st.metric("Lucro Líquido", f"R$ {financials['profit']:,.2f}")
        with col4:
            st.metric("Margem de Lucro", f"{financials['profit_margin']:.1f}%")
        
        # Detalhamento da receita
        if price_first > 0 or price_second > 0 or price_third > 0:
            st.subheader("Detalhamento da Receita")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Receita 1ª Qualidade", f"R$ {financials['first_quality_revenue']:,.2f}")
            with col2:
                st.metric("Receita 2ª Qualidade", f"R$ {financials['second_quality_revenue']:,.2f}")
            with col3:
                st.metric("Receita 3ª Qualidade", f"R$ {financials['third_quality_revenue']:,.2f}")
        
        # Exportar dados
        if st.button("📥 Exportar para Excel", key="export_financial"):
            export_to_excel(filtered_prod, "relatorio_financeiro", start_date, end_date)
    
    elif report_type == "Análise de Qualidade":
        st.header("🔍 Análise de Qualidade")
        st.write(f"**Período:** {start_date} a {end_date}")
        st.write(f"**Locais:** {', '.join(selected_locations)}")
        st.write(f"**Culturas:** {', '.join(selected_products)}")
        
        quality_data = []
        for product in filtered_prod['product'].unique():
            product_data = filtered_prod[filtered_prod['product'] == product]
            total = product_data['first_quality'].sum() + product_data['second_quality'].sum() + product_data['third_quality'].sum()
            
            if total > 0:
                first_percent = (product_data['first_quality'].sum() / total * 100)
                second_percent = (product_data['second_quality'].sum() / total * 100)
                third_percent = (product_data['third_quality'].sum() / total * 100)
                
                quality_data.append({
                    'Produto': product,
                    'Total Caixas': total,
                    '1ª Qualidade (%)': first_percent,
                    '2ª Qualidade (%)': second_percent,
                    '3ª Qualidade (%)': third_percent,
                    '1ª Qualidade (cx)': product_data['first_quality'].sum(),
                    '2ª Qualidade (cx)': product_data['second_quality'].sum(),
                    '3ª Qualidade (cx)': product_data['third_quality'].sum()
                })
        
        quality_df = pd.DataFrame(quality_data)
        st.dataframe(quality_df, use_container_width=True)
        
        # Gráfico de qualidade
        fig = px.bar(quality_df, x='Produto', y=['1ª Qualidade (cx)', '2ª Qualidade (cx)', '3ª Qualidade (cx)'], 
                     barmode='stack', title="Distribuição de Qualidade por Produto",
                     color_discrete_sequence=['#2ecc71', '#f1c40f', '#e74c3c'])
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                         font=dict(color='white'))
        st.plotly_chart(fig, use_container_width=True)
        
        # Exportar dados
        if st.button("📥 Exportar para Excel", key="export_quality"):
            export_to_excel(quality_df, "relatorio_qualidade", start_date, end_date)
    
    elif report_type == "Custos e Insumos":
        st.header("💸 Análise de Custos e Insumos")
        st.write(f"**Período:** {start_date} a {end_date}")
        
        if not filtered_inputs.empty:
            # Custos por tipo
            costs_by_type = filtered_inputs.groupby('type')['cost'].sum().reset_index()
            fig = px.pie(costs_by_type, values='cost', names='type', 
                         title="Distribuição de Custos por Tipo",
                         color_discrete_sequence=px.colors.qualitative.Set3)
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                             font=dict(color='white'))
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabela de custos detalhada
            st.subheader("Detalhamento de Custos")
            st.dataframe(filtered_inputs, use_container_width=True)
            
            # Exportar dados
            if st.button("📥 Exportar para Excel", key="export_costs"):
                export_to_excel(filtered_inputs, "relatorio_custos", start_date, end_date)
        else:
            st.info("Nenhum dado de insumos/custos para o período selecionado.")
    
    elif report_type == "Análise por Local":
        st.header("🏭 Análise de Produção por Local")
        st.write(f"**Período:** {start_date} a {end_date}")
        st.write(f"**Culturas:** {', '.join(selected_products)}")
        
        # Análise por local
        production_by_location = filtered_prod.groupby('local').agg({
            'first_quality': 'sum',
            'second_quality': 'sum',
            'third_quality': 'sum',
            'product': 'count'
        }).reset_index()
        
        production_by_location['total'] = (production_by_location['first_quality'] + 
                                          production_by_location['second_quality'] + 
                                          production_by_location['third_quality'])
        production_by_location['percentual_1a'] = (production_by_location['first_quality'] / production_by_location['total'] * 100).round(1)
        
        st.subheader("Produção por Local")
        st.dataframe(production_by_location, use_container_width=True)
        
        # Gráfico de produção por local
        fig = px.bar(production_by_location, x='local', y='total', 
                     title="Produção Total por Local",
                     color='total', color_continuous_scale='viridis')
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                         font=dict(color='white'))
        st.plotly_chart(fig, use_container_width=True)
        
        # Gráfico de qualidade por local
        fig = px.bar(production_by_location, x='local', y=['first_quality', 'second_quality', 'third_quality'], 
                     barmode='stack', title="Qualidade por Local",
                     color_discrete_sequence=['#2ecc71', '#f1c40f', '#e74c3c'])
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                         font=dict(color='white'))
        st.plotly_chart(fig, use_container_width=True)
        
        # Exportar dados
        if st.button("📥 Exportar para Excel", key="export_location"):
            export_to_excel(production_by_location, "relatorio_por_local", start_date, end_date)

# Função auxiliar para exportar dados para Excel
def export_to_excel(dataframe, report_name, start_date, end_date):
    """Exporta dataframe para Excel"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        dataframe.to_excel(writer, sheet_name='Relatório', index=False)
        
        workbook = writer.book
        worksheet = writer.sheets['Relatório']
        
        # Formatar cabeçalhos
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#2d5016',
            'font_color': 'white',
            'border': 1
        })
        
        # Aplicar formatação aos cabeçalhos
        for col_num, value in enumerate(dataframe.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # Ajustar largura das colunas
        for idx, col in enumerate(dataframe.columns):
            max_len = max(dataframe[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(idx, idx, max_len)
    
    output.seek(0)
    
    st.download_button(
        label="⬇️ Baixar Arquivo Excel",
        data=output,
        file_name=f"{report_name}_{start_date}_{end_date}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ================================
# FUNÇÃO PRINCIPAL
# ================================
def main():
    # Inicializar banco de dados
    init_db()
    
    # Menu lateral
    with st.sidebar:
        st.image("https://via.placeholder.com/150x50/2d5016/ffffff?text=AgroGestão", use_container_width=True)
        st.markdown("**Sistema de Gestão Agrícola**")
        st.markdown("---")
        
        # Menu de navegação (removida a página de configurações)
        menu_options = ["📊 Dashboard", "📝 Produção", "💰 Insumos", "📋 Relatórios"]
        
        selected = option_menu(
            menu_title="Navegação",
            options=menu_options,
            icons=["speedometer2", "pencil", "cash-coin", "file-text"],
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {"padding": "5px", "background-color": "#1a1a1a"},
                "icon": {"color": "#2d5016", "font-size": "18px"},
                "nav-link": {"font-size": "16px", "text-align": "left", "margin": "0px", "color": "white"},
                "nav-link-selected": {"background-color": "#2d5016"},
            }
        )
    
    # Navegação entre páginas
    if selected == "📊 Dashboard":
        show_dashboard()
    elif selected == "📝 Produção":
        show_production_page()
    elif selected == "💰 Insumos":
        show_inputs_page()
    elif selected == "📋 Relatórios":
        show_reports_page()

# ================================
# EXECUÇÃO DO APLICATIVO
# ================================
if __name__ == "__main__":
    main()
