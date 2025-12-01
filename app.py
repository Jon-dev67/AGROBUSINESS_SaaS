import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import json
import hashlib
import requests
import time
from streamlit_option_menu import option_menu
import io
import os
from supabase import create_client, Client

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
    .stForm {
        background-color: #1a1a1a;
        border-radius: 10px;
        padding: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

apply_dark_theme()

# ================================
# CONSTANTES E CONFIGURAÇÕES
# ================================
API_KEY = "eef20bca4e6fb1ff14a81a3171de5cec"
DEFAULT_CITY = "Londrina"

# Configurações do Supabase
SUPABASE_URL = "https://uskacaeytkwbstqsbofn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVza2FjYWV5dGt3YnN0cXNib2ZuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIyODk4MTEsImV4cCI6MjA3Nzg2NTgxMX0.v_CqAePnCDIX1NhLoNefLgN_56XUJozUOS8rfXPZyt8"

# ================================
# FUNÇÕES DE BANCO DE DADOS (SUPABASE)
# ================================
def get_supabase_client():
    """Estabelece conexão com o Supabase"""
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        return supabase
    except Exception as e:
        st.error(f"Erro ao conectar com o Supabase: {str(e)}")
        return None

def init_db():
    """Verifica a conexão com o Supabase"""
    supabase = get_supabase_client()
    if supabase is None:
        return False
    
    try:
        # Testa a conexão tentando buscar dados
        result = supabase.table("productions").select("*").limit(1).execute()
        st.success("✅ Conexão com Supabase estabelecida com sucesso!")
        return True
    except Exception as e:
        st.error(f"❌ Erro ao conectar com o banco de dados: {str(e)}")
        return False

def save_production(date, local, product, first_quality, second_quality, 
                    first_price, second_price, temperature, humidity, rain, weather_data):
    supabase = get_supabase_client()
    if supabase is None:
        return False
    
    try:
        data = {
            "date": date,
            "local": local,
            "product": product,
            "first_quality": float(first_quality),
            "second_quality": float(second_quality),
            "first_price": float(first_price),
            "second_price": float(second_price),
            "temperature": float(temperature) if temperature else None,
            "humidity": float(humidity) if humidity else None,
            "rain": float(rain) if rain else None,
            "weather_data": weather_data,
            "created_at": datetime.now().isoformat()
        }
        result = supabase.table("productions").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar produção: {str(e)}")
        return False

def load_productions():
    supabase = get_supabase_client()
    if supabase is None:
        return pd.DataFrame()
    
    try:
        result = supabase.table("productions").select("*").order("created_at", desc=True).execute()
        if hasattr(result, 'data'):
            df = pd.DataFrame(result.data)
            if not df.empty:
                # Converter colunas numéricas
                numeric_cols = ['first_quality', 'second_quality', 'first_price', 'second_price', 
                              'temperature', 'humidity', 'rain']
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar produções: {str(e)}")
        return pd.DataFrame()

def delete_production(production_id):
    supabase = get_supabase_client()
    if supabase is None:
        return False
    
    try:
        result = supabase.table("productions").delete().eq("id", production_id).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao excluir produção: {str(e)}")
        return False

def save_input(date, input_type, description, quantity, unit, cost, location):
    supabase = get_supabase_client()
    if supabase is None:
        return False
    
    try:
        data = {
            "date": date,
            "type": input_type,
            "description": description,
            "quantity": float(quantity),
            "unit": unit,
            "cost": float(cost),
            "location": location,
            "created_at": datetime.now().isoformat()
        }
        result = supabase.table("inputs").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar insumo: {str(e)}")
        return False

def load_inputs():
    supabase = get_supabase_client()
    if supabase is None:
        return pd.DataFrame()
    
    try:
        result = supabase.table("inputs").select("*").order("created_at", desc=True).execute()
        if hasattr(result, 'data'):
            df = pd.DataFrame(result.data)
            if not df.empty:
                # Converter colunas numéricas
                numeric_cols = ['quantity', 'cost']
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar insumos: {str(e)}")
        return pd.DataFrame()

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
                "temperature": float(data["main"]["temp"]),
                "humidity": float(data["main"]["humidity"]),
                "rain": float(data.get("rain", {}).get("1h", 0)) if "rain" in data else 0.0,
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
def calculate_financials(productions_df, inputs_df):
    """Calcula métricas financeiras com base nos dados de produção e insumos"""
    
    if productions_df.empty:
        return {
            "total_revenue": 0,
            "first_quality_revenue": 0,
            "second_quality_revenue": 0,
            "total_costs": 0,
            "profit": 0,
            "profit_margin": 0,
            "avg_first_price": 0,
            "avg_second_price": 0
        }
    
    # Calcular receita com os preços registrados na produção
    productions_df = productions_df.copy()
    
    # Garantir que as colunas de preço existam e sejam numéricas
    if 'first_price' not in productions_df.columns:
        productions_df['first_price'] = 0
    if 'second_price' not in productions_df.columns:
        productions_df['second_price'] = 0
    
    productions_df['first_price'] = pd.to_numeric(productions_df['first_price'], errors='coerce').fillna(0)
    productions_df['second_price'] = pd.to_numeric(productions_df['second_price'], errors='coerce').fillna(0)
    
    # Calcular receitas
    productions_df['first_revenue'] = productions_df['first_quality'] * productions_df['first_price']
    productions_df['second_revenue'] = productions_df['second_quality'] * productions_df['second_price']
    productions_df['total_revenue_item'] = productions_df['first_revenue'] + productions_df['second_revenue']
    
    total_revenue = productions_df['total_revenue_item'].sum()
    first_quality_revenue = productions_df['first_revenue'].sum()
    second_quality_revenue = productions_df['second_revenue'].sum()
    
    # Calcular preços médios
    avg_first_price = productions_df['first_price'].mean() if not productions_df['first_price'].empty else 0
    avg_second_price = productions_df['second_price'].mean() if not productions_df['second_price'].empty else 0
    
    # Calcular custos
    total_costs = inputs_df['cost'].sum() if not inputs_df.empty and 'cost' in inputs_df.columns else 0
    
    # Calcular lucro e margem
    profit = total_revenue - total_costs
    profit_margin = (profit / total_revenue * 100) if total_revenue > 0 else 0
    
    return {
        "total_revenue": total_revenue,
        "first_quality_revenue": first_quality_revenue,
        "second_quality_revenue": second_quality_revenue,
        "total_costs": total_costs,
        "profit": profit,
        "profit_margin": profit_margin,
        "avg_first_price": avg_first_price,
        "avg_second_price": avg_second_price
    }

# ================================
# DASHBOARD PRINCIPAL
# ================================
def show_dashboard():
    st.title("📊 Dashboard AgroGestão")
    
    # Carregar dados
    productions_df = load_productions()
    inputs_df = load_inputs()
    
    # Filtros na sidebar
    st.sidebar.header("Filtros")
    
    if not productions_df.empty:
        # Garantir que a coluna date existe e é datetime
        if 'date' in productions_df.columns:
            productions_df['date'] = pd.to_datetime(productions_df['date'], errors='coerce')
            productions_df = productions_df.dropna(subset=['date'])
            
            if not productions_df.empty:
                min_date = productions_df['date'].min().date()
                max_date = productions_df['date'].max().date()
                
                date_range = st.sidebar.date_input(
                    "Período",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )
                
                locations = st.sidebar.multiselect(
                    "Locais",
                    options=productions_df['local'].unique() if 'local' in productions_df.columns else [],
                    default=productions_df['local'].unique()[:5] if 'local' in productions_df.columns else []
                )
                
                products = st.sidebar.multiselect(
                    "Culturas",
                    options=productions_df['product'].unique() if 'product' in productions_df.columns else [],
                    default=productions_df['product'].unique()[:5] if 'product' in productions_df.columns else []
                )
                
                # Aplicar filtros
                try:
                    start_date, end_date = date_range
                except:
                    start_date, end_date = min_date, max_date
                
                filtered_df = productions_df[
                    (productions_df['date'].dt.date >= start_date) &
                    (productions_df['date'].dt.date <= end_date)
                ]
                
                if locations:
                    filtered_df = filtered_df[filtered_df['local'].isin(locations)]
                if products:
                    filtered_df = filtered_df[filtered_df['product'].isin(products)]
            else:
                filtered_df = pd.DataFrame()
        else:
            filtered_df = productions_df
            st.sidebar.warning("Coluna 'date' não encontrada nos dados")
    else:
        filtered_df = pd.DataFrame()
    
    # Calcular métricas financeiras
    financials = calculate_financials(filtered_df if not filtered_df.empty else productions_df, inputs_df)
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        if not filtered_df.empty and 'first_quality' in filtered_df.columns and 'second_quality' in filtered_df.columns:
            total_boxes = filtered_df['first_quality'].sum() + filtered_df['second_quality'].sum()
        elif not productions_df.empty and 'first_quality' in productions_df.columns and 'second_quality' in productions_df.columns:
            total_boxes = productions_df['first_quality'].sum() + productions_df['second_quality'].sum()
        else:
            total_boxes = 0
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
        profit_color = "green" if financials['profit'] >= 0 else "red"
        st.metric("Lucro Líquido", 
                 f"R$ {financials['profit']:,.2f}", 
                 f"{financials['profit_margin']:.1f}%")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Preços médios
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Preço Médio 1ª Qualidade", f"R$ {financials['avg_first_price']:,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Preço Médio 2ª Qualidade", f"R$ {financials['avg_second_price']:,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Gráficos - Primeira linha
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Produção por Cultura")
        
        if not filtered_df.empty and 'product' in filtered_df.columns:
            production_by_product = filtered_df.groupby('product').agg({
                'first_quality': 'sum',
                'second_quality': 'sum'
            }).reset_index()
            
            if not production_by_product.empty:
                production_by_product['total'] = production_by_product['first_quality'] + production_by_product['second_quality']
                
                fig = px.bar(production_by_product, x='product', y='total', 
                            color='product', color_discrete_sequence=px.colors.qualitative.Set3)
                fig.update_layout(showlegend=False, plot_bgcolor='rgba(0,0,0,0)', 
                                paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'),
                                xaxis_title="Cultura", yaxis_title="Total de Caixas")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Nenhum dado disponível para o gráfico.")
        else:
            st.info("Nenhum dado de produção disponível.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Produção por Área/Local")
        
        if not filtered_df.empty and 'local' in filtered_df.columns:
            production_by_location = filtered_df.groupby('local').agg({
                'first_quality': 'sum',
                'second_quality': 'sum'
            }).reset_index()
            
            if not production_by_location.empty:
                production_by_location['total'] = production_by_location['first_quality'] + production_by_location['second_quality']
                
                fig = px.pie(production_by_location, values='total', names='local',
                            color_discrete_sequence=px.colors.qualitative.Set3)
                fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                font=dict(color='white'), showlegend=True)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Nenhum dado disponível para o gráfico.")
        else:
            st.info("Nenhum dado de produção disponível.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Gráficos - Segunda linha
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Receita por Cultura")
        
        if not filtered_df.empty and 'product' in filtered_df.columns:
            if 'first_revenue' not in filtered_df.columns or 'second_revenue' not in filtered_df.columns:
                # Calcular receitas se não existirem
                filtered_df['first_revenue'] = filtered_df['first_quality'] * filtered_df.get('first_price', 0)
                filtered_df['second_revenue'] = filtered_df['second_quality'] * filtered_df.get('second_price', 0)
                filtered_df['total_revenue_item'] = filtered_df['first_revenue'] + filtered_df['second_revenue']
            
            revenue_by_product = filtered_df.groupby('product').agg({
                'total_revenue_item': 'sum'
            }).reset_index()
            
            if not revenue_by_product.empty:
                fig = px.pie(revenue_by_product, values='total_revenue_item', names='product', 
                            color_discrete_sequence=px.colors.qualitative.Set3)
                fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                font=dict(color='white'), showlegend=True)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Nenhum dado de receita disponível.")
        else:
            st.info("Nenhum dado de produção disponível.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Análise de Qualidade por Cultura")
        
        if not filtered_df.empty and 'product' in filtered_df.columns:
            quality_data = []
            for product in filtered_df['product'].unique():
                product_data = filtered_df[filtered_df['product'] == product]
                total = product_data['first_quality'].sum() + product_data['second_quality'].sum()
                if total > 0:
                    first_percent = (product_data['first_quality'].sum() / total * 100)
                    second_percent = (product_data['second_quality'].sum() / total * 100)
                    
                    quality_data.append({
                        'product': product,
                        '1ª Qualidade': first_percent,
                        '2ª Qualidade': second_percent
                    })
            
            if quality_data:
                quality_df = pd.DataFrame(quality_data)
                fig = px.bar(quality_df, x='product', y=['1ª Qualidade', '2ª Qualidade'], 
                            barmode='stack', color_discrete_sequence=['#2ecc71', '#f1c40f'])
                fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                font=dict(color='white'), yaxis_title="Percentual (%)",
                                xaxis_title="Cultura", showlegend=True)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Nenhum dado de qualidade disponível.")
        else:
            st.info("Nenhum dado de produção disponível.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Evolução temporal da produção
    if not filtered_df.empty and 'date' in filtered_df.columns:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Evolução Temporal da Produção")
        
        time_series = filtered_df.copy()
        time_series['date'] = pd.to_datetime(time_series['date'])
        time_series = time_series.groupby('date').agg({
            'first_quality': 'sum',
            'second_quality': 'sum'
        }).reset_index()
        
        fig = px.line(time_series, x='date', y=['first_quality', 'second_quality'],
                     color_discrete_sequence=['#2ecc71', '#f1c40f'])
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                         font=dict(color='white'), yaxis_title="Caixas",
                         xaxis_title="Data", showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ================================
# PÁGINA DE CADASTRO DE PRODUÇÃO
# ================================
def show_production_page():
    st.title("📝 Cadastro de Produção")
    
    # Buscar dados climáticos automaticamente
    weather_data = get_weather_data(DEFAULT_CITY)
    
    if weather_data:
        st.sidebar.header("🌤️ Dados Climáticos Atuais")
        st.sidebar.success("Dados climáticos carregados automaticamente!")
        st.sidebar.write(f"**Cidade:** {weather_data['city']}")
        st.sidebar.write(f"**Temperatura:** {weather_data['temperature']}°C")
        st.sidebar.write(f"**Umidade:** {weather_data['humidity']}%")
        st.sidebar.write(f"**Chuva:** {weather_data['rain']}mm")
        st.sidebar.write(f"**Condição:** {weather_data['description'].title()}")
    else:
        st.sidebar.warning("⚠️ Não foi possível carregar dados climáticos")
        # Dados padrão caso a API falhe
        weather_data = {
            'temperature': 25.0,
            'humidity': 60.0,
            'rain': 0.0
        }

    with st.form("production_form", clear_on_submit=True):
        st.markdown("### Informações da Produção")
        col1, col2 = st.columns(2)
        
        with col1:
            date = st.date_input("📅 Data", value=datetime.now())
            location = st.text_input("📍 Local/Estufa", placeholder="Ex: Estufa A, Talhão 1")
            product = st.text_input("🌱 Produto", placeholder="Ex: Tomate, Alface, Morango")
        
        with col2:
            first_quality = st.number_input("📦 Caixas 1ª Qualidade", min_value=0.0, step=0.5, value=0.0, format="%.1f")
            second_quality = st.number_input("📦 Caixas 2ª Qualidade", min_value=0.0, step=0.5, value=0.0, format="%.1f")
        
        st.markdown("### Preços por Caixa")
        col3, col4 = st.columns(2)
        
        with col3:
            first_price = st.number_input("💰 Preço por caixa (1ª Qualidade)", 
                                         min_value=0.0, step=0.5, value=10.0,
                                         help="Preço de venda por caixa da 1ª qualidade",
                                         format="%.2f")
        
        with col4:
            second_price = st.number_input("💰 Preço por caixa (2ª Qualidade)", 
                                          min_value=0.0, step=0.5, value=5.0,
                                          help="Preço de venda por caixa da 2ª qualidade",
                                          format="%.2f")
        
        st.markdown("### Dados Climáticos")
        col5, col6, col7 = st.columns(3)
        
        # Usar dados da API automaticamente
        with col5:
            # Converter para float garantindo que seja um número
            temp_value = float(weather_data.get('temperature', 25.0))
            temperature = st.number_input("🌡️ Temperatura (°C)", 
                                        value=temp_value, 
                                        step=0.1,
                                        format="%.1f")
        
        with col6:
            # Converter para float garantindo que seja um número
            humidity_value = float(weather_data.get('humidity', 60.0))
            humidity = st.number_input("💧 Umidade (%)", 
                                      value=humidity_value,
                                      min_value=0.0, 
                                      max_value=100.0, 
                                      step=1.0,
                                      format="%.0f")
        
        with col7:
            # Converter para float garantindo que seja um número
            rain_value = float(weather_data.get('rain', 0.0))
            rain = st.number_input("🌧️ Chuva (mm)", 
                                  value=rain_value,
                                  min_value=0.0, 
                                  step=0.1,
                                  format="%.1f")
        
        # Cálculo automático da receita
        total_revenue = (first_quality * first_price) + (second_quality * second_price)
        
        st.markdown("---")
        st.markdown(f"**💰 Receita total estimada: R$ {total_revenue:,.2f}**")
        
        # CORREÇÃO AQUI: Usar st.form_submit_button() em vez de st.button()
        submitted = st.form_submit_button("💾 Salvar Produção", type="primary")
        
        if submitted:
            if not all([location.strip(), product.strip()]):
                st.error("❌ Preencha todos os campos obrigatórios (Local e Produto).")
            elif first_quality == 0 and second_quality == 0:
                st.error("❌ Informe pelo menos uma quantidade de caixas.")
            else:
                success = save_production(
                    date.isoformat(), 
                    location.strip(), 
                    product.strip(), 
                    first_quality, 
                    second_quality,
                    first_price,
                    second_price,
                    temperature, 
                    humidity, 
                    rain,
                    json.dumps(weather_data) if weather_data else ""
                )
                if success:
                    st.success("✅ Produção registrada com sucesso!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Erro ao salvar produção. Verifique a conexão com o banco de dados.")

# ================================
# PÁGINA DE CADASTRO DE INSUMOS
# ================================
def show_inputs_page():
    st.title("💰 Cadastro de Insumos")
    
    with st.form("inputs_form", clear_on_submit=True):
        st.markdown("### Informações do Insumo")
        col1, col2 = st.columns(2)
        
        with col1:
            date = st.date_input("📅 Data", value=datetime.now())
            input_type = st.selectbox("📦 Tipo de Insumo", 
                                     ["Semente", "Fertilizante", "Defensivo", "Mão de Obra", "Equipamento", "Outros"])
            description = st.text_input("📝 Descrição", placeholder="Ex: Adubo NPK 10-10-10")
        
        with col2:
            quantity = st.number_input("⚖️ Quantidade", min_value=0.0, step=0.1, value=1.0)
            unit = st.selectbox("📏 Unidade", ["kg", "L", "un", "h", "sc", "outro"])
            cost = st.number_input("💵 Custo (R$)", min_value=0.0, step=0.01, value=0.0)
        
        location = st.text_input("📍 Local aplicado", placeholder="Ex: Estufa A, Talhão 1")
        
        submitted = st.form_submit_button("💾 Salvar Insumo", type="primary")
        
        if submitted:
            if not all([input_type, description.strip(), quantity > 0, cost > 0]):
                st.error("❌ Preencha todos os campos obrigatórios.")
            else:
                success = save_input(
                    date.isoformat(), 
                    input_type, 
                    description.strip(), 
                    quantity, 
                    unit, 
                    cost, 
                    location.strip()
                )
                if success:
                    st.success("✅ Insumo registrado com sucesso!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Erro ao salvar insumo. Verifique a conexão com o banco de dados.")
    
    # Mostrar dados recentes
    st.markdown("---")
    st.subheader("📋 Insumos Recentes")
    
    inputs_df = load_inputs()
        
    if not inputs_df.empty:
        # Mostrar apenas colunas relevantes
        display_cols = ['date', 'type', 'description', 'quantity', 'unit', 'cost', 'location']
        
        # Garantir que as colunas existam
        available_cols = [col for col in display_cols if col in inputs_df.columns]
        
        if available_cols:
            display_df = inputs_df[available_cols].head(10)
            st.dataframe(display_df, use_container_width=True)
        
        # Adicionar botão para baixar dados em Excel
        st.markdown("---")
        st.subheader("📤 Exportar Dados")
        
        if not inputs_df.empty:
            # Criar Excel em memória
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                inputs_df.to_excel(writer, sheet_name='Insumos', index=False)
                
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
                for col_num, value in enumerate(inputs_df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # Ajustar largura das colunas
                for idx, col in enumerate(inputs_df.columns):
                    max_len = max(inputs_df[col].astype(str).map(len).max(), len(col)) + 2
                    worksheet.set_column(idx, idx, max_len)
            
            output.seek(0)
            
            # Botão de download
            st.download_button(
                label="📥 Baixar Dados em Excel",
                data=output,
                file_name=f"insumos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
    else:
        st.info("📭 Nenhum insumo registrado ainda.")

# ================================
# PÁGINA DE RELATÓRIOS
# ================================
def show_reports_page():
    st.title("📋 Relatórios")
    
    productions_df = load_productions()
    inputs_df = load_inputs()
    
    if productions_df.empty:
        st.warning("⚠️ Nenhum dado disponível para gerar relatórios.")
        return
    
    # Filtros para relatórios
    st.sidebar.header("🔍 Filtros do Relatório")
    
    if not productions_df.empty:
        # Garantir que a coluna date existe e é datetime
        if 'date' in productions_df.columns:
            productions_df['date'] = pd.to_datetime(productions_df['date'], errors='coerce')
            productions_df = productions_df.dropna(subset=['date'])
            
            if not productions_df.empty:
                min_date = productions_df['date'].min().date()
                max_date = productions_df['date'].max().date()
                
                report_date_range = st.sidebar.date_input(
                    "📅 Período do Relatório",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )
                
                # Filtro por local
                all_locations = productions_df['local'].unique().tolist() if 'local' in productions_df.columns else []
                selected_locations = st.sidebar.multiselect(
                    "📍 Filtrar por Local",
                    options=all_locations,
                    default=all_locations[:5] if all_locations else []
                )
                
                # Filtro por cultura
                all_products = productions_df['product'].unique().tolist() if 'product' in productions_df.columns else []
                selected_products = st.sidebar.multiselect(
                    "🌱 Filtrar por Cultura",
                    options=all_products,
                    default=all_products[:5] if all_products else []
                )
                
                # Tipo de relatório
                report_type = st.sidebar.selectbox(
                    "📊 Tipo de Relatório",
                    ["Produção Detalhada", "Resumo Financeiro", "Análise de Qualidade", "Custos e Insumos"]
                )
                
                try:
                    start_date, end_date = report_date_range
                except:
                    start_date, end_date = min_date, max_date
                
                # Filtrar dados de produção
                filtered_prod = productions_df[
                    (productions_df['date'].dt.date >= start_date) &
                    (productions_df['date'].dt.date <= end_date)
                ]
                
                if selected_locations:
                    filtered_prod = filtered_prod[filtered_prod['local'].isin(selected_locations)]
                if selected_products:
                    filtered_prod = filtered_prod[filtered_prod['product'].isin(selected_products)]
                
                # Filtrar dados de insumos
                if not inputs_df.empty and 'date' in inputs_df.columns:
                    inputs_df['date'] = pd.to_datetime(inputs_df['date'], errors='coerce')
                    filtered_inputs = inputs_df[
                        (inputs_df['date'].dt.date >= start_date) &
                        (inputs_df['date'].dt.date <= end_date)
                    ]
                else:
                    filtered_inputs = pd.DataFrame()
                
                if filtered_prod.empty:
                    st.warning("ℹ️ Nenhum dado encontrado para o período selecionado.")
                    return
                
                # Gerar relatório selecionado
                if report_type == "Produção Detalhada":
                    st.header("📊 Relatório de Produção Detalhada")
                    
                    # Preparar dados para exibição
                    report_cols = ['date', 'product', 'local', 'first_quality', 'second_quality', 
                                 'first_price', 'second_price', 'temperature', 'humidity']
                    
                    # Garantir que as colunas existem
                    available_cols = [col for col in report_cols if col in filtered_prod.columns]
                    
                    if available_cols:
                        report_df = filtered_prod[available_cols].copy()
                        
                        # Calcular totais
                        if 'first_quality' in report_df.columns and 'second_quality' in report_df.columns:
                            report_df['total_quality'] = report_df['first_quality'] + report_df['second_quality']
                        
                        # Calcular receita por item
                        if all(col in report_df.columns for col in ['first_quality', 'second_quality', 'first_price', 'second_price']):
                            report_df['revenue'] = (report_df['first_quality'] * report_df['first_price'] + 
                                                   report_df['second_quality'] * report_df['second_price'])
                        
                        st.dataframe(report_df, use_container_width=True)
                        
                        # Resumo
                        st.subheader("📈 Resumo")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if 'first_quality' in report_df.columns and 'second_quality' in report_df.columns:
                                total_boxes = report_df['first_quality'].sum() + report_df['second_quality'].sum()
                                st.metric("Total de Caixas", f"{total_boxes:,.0f}")
                        
                        with col2:
                            if 'revenue' in report_df.columns:
                                total_revenue = report_df['revenue'].sum()
                                st.metric("Receita Total", f"R$ {total_revenue:,.2f}")
                        
                        with col3:
                            if 'product' in report_df.columns:
                                num_products = report_df['product'].nunique()
                                st.metric("Culturas", f"{num_products}")
                    
                elif report_type == "Resumo Financeiro":
                    st.header("💰 Relatório Financeiro")
                    
                    financials = calculate_financials(filtered_prod, filtered_inputs)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Receita Total", f"R$ {financials['total_revenue']:,.2f}")
                    with col2:
                        st.metric("Custos Totais", f"R$ {financials['total_costs']:,.2f}")
                    with col3:
                        profit_color = "green" if financials['profit'] >= 0 else "red"
                        st.metric("Lucro Líquido", f"R$ {financials['profit']:,.2f}")
                    with col4:
                        st.metric("Margem de Lucro", f"{financials['profit_margin']:.1f}%")
                    
                    # Gráfico de receita vs custos
                    st.subheader("📊 Receita vs Custos")
                    
                    comparison_data = pd.DataFrame({
                        'Categoria': ['Receita', 'Custos', 'Lucro'],
                        'Valor (R$)': [financials['total_revenue'], financials['total_costs'], financials['profit']]
                    })
                    
                    fig = px.bar(comparison_data, x='Categoria', y='Valor (R$)', 
                                color='Categoria', color_discrete_sequence=['#2ecc71', '#e74c3c', '#3498db'])
                    fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                    font=dict(color='white'), showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                        
                elif report_type == "Análise de Qualidade":
                    st.header("🔍 Análise de Qualidade")
                    
                    quality_data = []
                    for product in filtered_prod['product'].unique():
                        product_data = filtered_prod[filtered_prod['product'] == product]
                        total = product_data['first_quality'].sum() + product_data['second_quality'].sum()
                        
                        if total > 0:
                            first_percent = (product_data['first_quality'].sum() / total * 100)
                            second_percent = (product_data['second_quality'].sum() / total * 100)
                            
                            quality_data.append({
                                'Produto': product,
                                'Total Caixas': total,
                                '1ª Qualidade': product_data['first_quality'].sum(),
                                '2ª Qualidade': product_data['second_quality'].sum(),
                                '1ª Qualidade (%)': f"{first_percent:.1f}%",
                                '2ª Qualidade (%)': f"{second_percent:.1f}%"
                            })
                    
                    if quality_data:
                        quality_df = pd.DataFrame(quality_data)
                        st.dataframe(quality_df, use_container_width=True)
                        
                        # Gráfico de qualidade
                        st.subheader("📊 Distribuição de Qualidade")
                        
                        melted_df = quality_df.melt(id_vars=['Produto'], 
                                                   value_vars=['1ª Qualidade', '2ª Qualidade'],
                                                   var_name='Qualidade', value_name='Caixas')
                        
                        fig = px.bar(melted_df, x='Produto', y='Caixas', color='Qualidade',
                                    barmode='group', color_discrete_sequence=['#2ecc71', '#f1c40f'])
                        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                        font=dict(color='white'), yaxis_title="Número de Caixas")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("ℹ️ Nenhum dado de qualidade disponível.")
                    
                elif report_type == "Custos e Insumos":
                    st.header("💸 Análise de Custos e Insumos")
                    
                    if not filtered_inputs.empty:
                        st.subheader("📋 Detalhamento de Insumos")
                        st.dataframe(filtered_inputs, use_container_width=True)
                        
                        # Análise por tipo de insumo
                        st.subheader("📊 Distribuição por Tipo de Insumo")
                        
                        if 'type' in filtered_inputs.columns and 'cost' in filtered_inputs.columns:
                            cost_by_type = filtered_inputs.groupby('type')['cost'].sum().reset_index()
                            
                            fig = px.pie(cost_by_type, values='cost', names='type',
                                        color_discrete_sequence=px.colors.qualitative.Set3)
                            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                            font=dict(color='white'), showlegend=True)
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("ℹ️ Nenhum dado de insumos/custos para o período selecionado.")
            else:
                st.warning("⚠️ Dados de produção não contêm informações de data válidas.")
        else:
            st.warning("⚠️ Coluna 'date' não encontrada nos dados de produção.")

# ================================
# FUNÇÃO PRINCIPAL
# ================================
def main():
    # Inicializar banco de dados
    if not init_db():
        st.error("❌ Falha na conexão com o banco de dados. Algumas funcionalidades podem não estar disponíveis.")
    
    # Menu lateral
    with st.sidebar:
        st.markdown("""
            <div style='text-align: center; margin-bottom: 20px;'>
                <h1 style='color: #2d5016;'>🌱 AgroGestão</h1>
                <p style='color: #666;'>Sistema de Gestão Agrícola</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Menu de navegação
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
