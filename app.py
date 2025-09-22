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
        
        # Tabela de configurações de preços
        c.execute('''CREATE TABLE IF NOT EXISTS price_config
                     (id SERIAL PRIMARY KEY,
                      product TEXT NOT NULL,
                      first_quality_price REAL NOT NULL,
                      second_quality_price REAL NOT NULL,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      UNIQUE(product))''')
        
        # Verificar se a tabela price_config está vazia
        c.execute("SELECT COUNT(*) FROM price_config")
        if c.fetchone()[0] == 0:
            default_prices = [
                ("Tomate", 15.0, 8.0),
                ("Alface", 12.0, 6.0),
                ("Pepino", 10.0, 5.0),
                ("Pimentão", 18.0, 9.0),
                ("Morango", 25.0, 12.0)
            ]
            for product, first_price, second_price in default_prices:
                c.execute("INSERT INTO price_config (product, first_quality_price, second_quality_price) VALUES (%s, %s, %s) ON CONFLICT (product) DO NOTHING", 
                         (product, first_price, second_price))
        
        conn.commit()
    except Exception as e:
        st.error(f"Erro ao inicializar banco de dados: {str(e)}")
    finally:
        conn.close()

def save_production(date, local, product, first_quality, second_quality, temperature, humidity, rain, weather_data):
    conn = get_db_connection()
    if conn is None:
        return False
    
    try:
        c = conn.cursor()
        c.execute("INSERT INTO productions (date, local, product, first_quality, second_quality, temperature, humidity, rain, weather_data) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                  (date, local, product, first_quality, second_quality, temperature, humidity, rain, weather_data))
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

def load_price_config():
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()
    
    try:
        df = pd.read_sql_query("SELECT * FROM price_config", conn)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar configurações de preço: {str(e)}")
        return pd.DataFrame()
    finally:
        conn.close()

def save_price_config(product, first_price, second_price):
    conn = get_db_connection()
    if conn is None:
        return False
    
    try:
        c = conn.cursor()
        c.execute("INSERT INTO price_config (product, first_quality_price, second_quality_price) VALUES (%s, %s, %s) ON CONFLICT (product) DO UPDATE SET first_quality_price = %s, second_quality_price = %s",
                  (product, first_price, second_price, first_price, second_price))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar configuração de preço: {str(e)}")
        return False
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
            return None
    except Exception as e:
        return None

# ================================
# FUNÇÕES DE CÁLCULO FINANCEIRO
# ================================
def calculate_financials(productions_df, inputs_df):
    price_config = load_price_config()
    
    if productions_df.empty:
        return {
            "total_revenue": 0,
            "first_quality_revenue": 0,
            "second_quality_revenue": 0,
            "total_costs": 0,
            "profit": 0,
            "profit_margin": 0
        }
    
    # Calcular receita
    revenue_data = []
    for _, row in productions_df.iterrows():
        product = row['product']
        price_row = price_config[price_config['product'] == product]
        
        if not price_row.empty:
            first_price = price_row['first_quality_price'].values[0]
            second_price = price_row['second_quality_price'].values[0]
        else:
            first_price, second_price = 10.0, 5.0
        
        first_revenue = row['first_quality'] * first_price
        second_revenue = row['second_quality'] * second_price
        
        revenue_data.append({
            'product': product,
            'first_revenue': first_revenue,
            'second_revenue': second_revenue,
            'total_revenue': first_revenue + second_revenue
        })
    
    revenue_df = pd.DataFrame(revenue_data)
    total_revenue = revenue_df['total_revenue'].sum()
    first_quality_revenue = revenue_df['first_revenue'].sum()
    second_quality_revenue = revenue_df['second_revenue'].sum()
    
    # Calcular custos
    total_costs = inputs_df['cost'].sum() if not inputs_df.empty else 0
    
    # Calcular lucro e margem
    profit = total_revenue - total_costs
    profit_margin = (profit / total_revenue * 100) if total_revenue > 0 else 0
    
    return {
        "total_revenue": total_revenue,
        "first_quality_revenue": first_quality_revenue,
        "second_quality_revenue": second_quality_revenue,
        "total_costs": total_costs,
        "profit": profit,
        "profit_margin": profit_margin
    }

# ================================
# PÁGINA ADMINISTRATIVA (CRUD COMPLETO)
# ================================
def show_admin_page():
    st.title("🔧 Área Administrativa - Gerenciamento de Dados")
    st.warning("⚠️ **ACESSO RESTRITO** - Esta área permite manipulação direta do banco de dados")
    
    # Verificação simples de segurança
    admin_password = st.text_input("Senha Administrativa", type="password")
    if admin_password != "admin123":
        st.error("Acesso não autorizado")
        return
    
    st.success("Acesso concedido ao modo administrativo")
    
    # Seleção de tabela
    conn = get_db_connection()
    if conn is None:
        st.error("Não foi possível conectar ao banco de dados")
        return
    
    try:
        # Listar tabelas disponíveis
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        selected_table = st.selectbox("Selecione a tabela para gerenciar:", tables)
        
        if not selected_table:
            st.info("Selecione uma tabela para continuar")
            return
            
        # Carregar dados da tabela selecionada
        df = pd.read_sql_query(f"SELECT * FROM {selected_table} ORDER BY id DESC", conn)
        
        # Mostrar estatísticas da tabela
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Registros", len(df))
        with col2:
            st.metric("Colunas", len(df.columns))
        with col3:
            if 'created_at' in df.columns:
                last_update = pd.to_datetime(df['created_at']).max()
                st.metric("Última Atualização", last_update.strftime('%d/%m/%Y'))
        
        # Abas para diferentes operações
        tab1, tab2, tab3, tab4 = st.tabs(["📋 Visualizar Dados", "➕ Adicionar Registro", "✏️ Editar Registro", "🗑️ Excluir Registros"])
        
        with tab1:
            st.subheader(f"Dados da Tabela: {selected_table}")
            
            # Filtros
            col1, col2 = st.columns(2)
            with col1:
                if not df.empty:
                    records_per_page = st.selectbox("Registros por página:", [10, 25, 50, 100], index=0)
                else:
                    records_per_page = 10
                    
            with col2:
                search_term = st.text_input("🔍 Buscar em todos os campos:")
            
            # Aplicar filtro de busca
            if search_term and not df.empty:
                filtered_df = df.copy()
                for col in filtered_df.columns:
                    if filtered_df[col].dtype == 'object':
                        filtered_df = filtered_df[filtered_df[col].astype(str).str.contains(search_term, case=False, na=False)]
            else:
                filtered_df = df
            
            # Paginação
            if not filtered_df.empty:
                total_pages = max(1, len(filtered_df) // records_per_page + (1 if len(filtered_df) % records_per_page else 0))
                page_number = st.number_input("Página:", min_value=1, max_value=total_pages, value=1)
                
                start_idx = (page_number - 1) * records_per_page
                end_idx = min(start_idx + records_per_page, len(filtered_df))
                
                st.write(f"Mostrando registros {start_idx + 1} a {end_idx} de {len(filtered_df)}")
                st.dataframe(filtered_df.iloc[start_idx:end_idx], use_container_width=True)
                
                # Botão de exportação
                csv = filtered_df.to_csv(index=False)
                st.download_button(
                    label="📥 Exportar para CSV",
                    data=csv,
                    file_name=f"{selected_table}_export.csv",
                    mime="text/csv"
                )
            else:
                st.info("Nenhum registro encontrado")
        
        with tab2:
            st.subheader("Adicionar Novo Registro")
            
            if df.empty:
                st.warning("Não é possível determinar a estrutura da tabela vazia")
                return
                
            # Gerar formulário dinamicamente baseado na estrutura da tabela
            with st.form("add_record_form"):
                new_record = {}
                columns = [col for col in df.columns if col not in ['id', 'created_at']]
                
                for col in columns:
                    col_type = df[col].dtype
                    
                    if col_type in ['int64', 'float64']:
                        new_record[col] = st.number_input(f"{col}:", value=0.0)
                    elif 'date' in col.lower():
                        new_record[col] = st.date_input(f"{col}:", value=datetime.now()).isoformat()
                    else:
                        new_record[col] = st.text_input(f"{col}:")
                
                submitted = st.form_submit_button("Adicionar Registro")
                
                if submitted:
                    try:
                        # Construir query INSERT dinamicamente
                        columns_str = ', '.join(new_record.keys())
                        placeholders = ', '.join(['%s'] * len(new_record))
                        values = list(new_record.values())
                        
                        query = f"INSERT INTO {selected_table} ({columns_str}) VALUES ({placeholders})"
                        cursor.execute(query, values)
                        conn.commit()
                        
                        st.success("✅ Registro adicionado com sucesso!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Erro ao adicionar registro: {str(e)}")
        
        with tab3:
            st.subheader("Editar Registro Existente")
            
            if df.empty:
                st.info("Nenhum registro disponível para edição")
                return
                
            # Selecionar registro para editar
            record_options = [f"ID: {row['id']} - {row.get('product', row.get('description', 'Registro'))}" 
                            for _, row in df.iterrows()]
            selected_record = st.selectbox("Selecione o registro para editar:", record_options)
            
            if selected_record:
                record_id = int(selected_record.split('ID: ')[1].split(' -')[0])
                original_record = df[df['id'] == record_id].iloc[0]
                
                with st.form("edit_record_form"):
                    st.write(f"Editando registro ID: {record_id}")
                    updated_record = {}
                    columns = [col for col in df.columns if col != 'id']
                    
                    for col in columns:
                        col_type = df[col].dtype
                        current_value = original_record[col]
                        
                        if col == 'created_at':
                            st.text_input(f"{col}:", value=str(current_value), disabled=True)
                            continue
                            
                        if col_type in ['int64', 'float64']:
                            updated_record[col] = st.number_input(f"{col}:", value=float(current_value) if pd.notna(current_value) else 0.0)
                        elif 'date' in col.lower() and current_value:
                            try:
                                date_val = pd.to_datetime(current_value).date()
                                updated_record[col] = st.date_input(f"{col}:", value=date_val).isoformat()
                            except:
                                updated_record[col] = st.text_input(f"{col}:", value=str(current_value))
                        else:
                            updated_record[col] = st.text_input(f"{col}:", value=str(current_value) if pd.notna(current_value) else "")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        submitted = st.form_submit_button("💾 Salvar Alterações")
                    with col2:
                        if st.form_submit_button("❌ Cancelar"):
                            st.rerun()
                    
                    if submitted:
                        try:
                            # Construir query UPDATE dinamicamente
                            set_clause = ', '.join([f"{col} = %s" for col in updated_record.keys()])
                            values = list(updated_record.values()) + [record_id]
                            
                            query = f"UPDATE {selected_table} SET {set_clause} WHERE id = %s"
                            cursor.execute(query, values)
                            conn.commit()
                            
                            st.success("✅ Registro atualizado com sucesso!")
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Erro ao atualizar registro: {str(e)}")
        
        with tab4:
            st.subheader("Excluir Registros")
            st.error("⚠️ **ATENÇÃO**: Esta operação é irreversível!")
            
            if df.empty:
                st.info("Nenhum registro disponível para exclusão")
                return
            
            # Seleção múltipla para exclusão
            records_to_delete = st.multiselect(
                "Selecione os registros para excluir:",
                options=[f"ID: {row['id']} - {row.get('product', row.get('description', 'Registro'))}" 
                        for _, row in df.iterrows()],
                help="Ctrl+click para selecionar múltiplos registros"
            )
            
            if records_to_delete:
                st.warning(f"🚨 Você está prestes a excluir {len(records_to_delete)} registro(s)")
                
                # Mostrar preview dos registros selecionados
                delete_ids = [int(record.split('ID: ')[1].split(' -')[0]) for record in records_to_delete]
                preview_df = df[df['id'].isin(delete_ids)]
                st.dataframe(preview_df, use_container_width=True)
                
                # Confirmação final
                confirmation = st.text_input("Digite 'CONFIRMAR' para prosseguir com a exclusão:")
                
                if st.button("🗑️ Excluir Permanentemente", disabled=confirmation != "CONFIRMAR"):
                    try:
                        # Construir query DELETE
                        placeholders = ', '.join(['%s'] * len(delete_ids))
                        query = f"DELETE FROM {selected_table} WHERE id IN ({placeholders})"
                        cursor.execute(query, delete_ids)
                        conn.commit()
                        
                        st.success(f"✅ {len(delete_ids)} registro(s) excluído(s) com sucesso!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Erro ao excluir registros: {str(e)}")
    
    except Exception as e:
        st.error(f"Erro ao acessar o banco de dados: {str(e)}")
    finally:
        conn.close()

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
    financials = calculate_financials(filtered_df if not filtered_df.empty else productions_df, inputs_df)
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        if not filtered_df.empty:
            total_boxes = filtered_df['first_quality'].sum() + filtered_df['second_quality'].sum()
        else:
            total_boxes = productions_df['first_quality'].sum() + productions_df['second_quality'].sum() if not productions_df.empty else 0
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
        st.metric("Lucro Líquido", f"R$ {financials['profit']:,.2f}", f"{financials['profit_margin']:.1f}%")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Gráficos
    if not productions_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Produção por Cultura")
            production_by_product = filtered_df.groupby('product')[['first_quality', 'second_quality']].sum().reset_index()
            production_by_product['total'] = production_by_product['first_quality'] + production_by_product['second_quality']
            
            fig = px.bar(production_by_product, x='product', y='total', 
                         color='product', color_discrete_sequence=px.colors.qualitative.Set3)
            fig.update_layout(showlegend=False, plot_bgcolor='rgba(0,0,0,0)', 
                             paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Produção por Área/Local")
            production_by_location = filtered_df.groupby('local')[['first_quality', 'second_quality']].sum().reset_index()
            production_by_location['total'] = production_by_location['first_quality'] + production_by_location['second_quality']
            
            fig = px.pie(production_by_location, values='total', names='local',
                         color_discrete_sequence=px.colors.qualitative.Set3)
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                             font=dict(color='white'))
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Evolução temporal da produção
    if not productions_df.empty:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Evolução Temporal da Produção")
        time_series = filtered_df.copy()
        time_series['date'] = pd.to_datetime(time_series['date'])
        time_series = time_series.groupby('date')[['first_quality', 'second_quality']].sum().reset_index()
        
        fig = px.line(time_series, x='date', y=['first_quality', 'second_quality'],
                     color_discrete_sequence=['#2ecc71', '#f1c40f'])
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                         font=dict(color='white'), yaxis_title="Caixas")
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
                st.write(f"1ª: {row['first_quality']}cx, 2ª: {row['second_quality']}cx")
            with col3:
                st.write(f"T: {row['temperature']}°C, U: {row['humidity']}%")
            with col4:
                if st.button("🗑️", key=f"delete_{row['id']}"):
                    if delete_production(row['id']):
                        st.success("Registro excluído com sucesso!")
                        st.rerun()
                    else:
                        st.error("Erro ao excluir registro.")

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

# ================================
# PÁGINA DE CONFIGURAÇÕES
# ================================
def show_settings_page():
    st.title("⚙️ Configurações de Preços")
    
    price_config = load_price_config()
    
    st.subheader("Preços Atuais por Cultura")
    if not price_config.empty:
        st.dataframe(price_config[['product', 'first_quality_price', 'second_quality_price']], 
                    use_container_width=True)
    else:
        st.info("Nenhum preço configurado. Adicione preços para suas culturas.")
    
    st.subheader("Adicionar/Editar Preços")
    with st.form("price_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            product = st.text_input("Cultura")
        with col2:
            first_price = st.number_input("Preço 1ª Qualidade (R$)", min_value=0.0, step=0.5)
        with col3:
            second_price = st.number_input("Preço 2ª Qualidade (R$)", min_value=0.0, step=0.5)
        
        submitted = st.form_submit_button("Salvar Preços")
        
        if submitted:
            if not all([product, first_price > 0, second_price > 0]):
                st.error("Preencha todos os campos corretamente.")
            else:
                success = save_price_config(product, first_price, second_price)
                if success:
                    st.success("Preços salvos com sucesso!")
                    st.rerun()
                else:
                    st.error("Erro ao salvar preços. Verifique a conexão com o banco de dados.")

# ================================
# PÁGINA DE RELATÓRIOS
# ================================
def show_reports_page():
    st.title("📋 Relatórios")
    
    productions_df = load_productions()
    inputs_df = load_inputs()
    
    if productions_df.empty:
        st.warning("Nenhum dado disponível para gerar relatórios.")
        return
    
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
    
    # Tipo de relatório
    report_type = st.sidebar.selectbox(
        "Tipo de Relatório",
        ["Produção Detalhada", "Resumo Financeiro", "Análise de Qualidade", "Custos e Insumos"]
    )
    
    try:
        start_date, end_date = report_date_range
    except:
        start_date, end_date = min_date, max_date
    
    # Filtrar dados
    filtered_prod = productions_df[
        (pd.to_datetime(productions_df['date']).dt.date >= start_date) &
        (pd.to_datetime(productions_df['date']).dt.date <= end_date)
    ]
    
    filtered_inputs = inputs_df[
        (pd.to_datetime(inputs_df['date']).dt.date >= start_date) &
        (pd.to_datetime(inputs_df['date']).dt.date <= end_date)
    ]
    
    if filtered_prod.empty:
        st.warning("Nenhum dado encontrado para o período selecionado.")
        return
    
    # Gerar relatório selecionado
    if report_type == "Produção Detalhada":
        st.header("Relatório de Produção Detalhada")
        st.write(f"Período: {start_date} a {end_date}")
        
        # Resumo estatístico
        total_first = filtered_prod['first_quality'].sum()
        total_second = filtered_prod['second_quality'].sum()
        total_boxes = total_first + total_second
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Caixas", f"{total_boxes:,.0f}")
        with col2:
            st.metric("1ª Qualidade", f"{total_first:,.0f}")
        with col3:
            st.metric("2ª Qualidade", f"{total_second:,.0f}")
        
        # Dados detalhados
        st.dataframe(filtered_prod, use_container_width=True)
    
    elif report_type == "Resumo Financeiro":
        st.header("Relatório Financeiro")
        
        financials = calculate_financials(filtered_prod, filtered_inputs)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Receita Total", f"R$ {financials['total_revenue']:,.2f}")
        with col2:
            st.metric("Custos Totals", f"R$ {financials['total_costs']:,.2f}")
        with col3:
            st.metric("Lucro Líquido", f"R$ {financials['profit']:,.2f}")
        with col4:
            st.metric("Margem de Lucro", f"{financials['profit_margin']:.1f}%")

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
        
        # Menu de navegação - ADICIONADO ADMINISTRATIVO
        menu_options = ["📊 Dashboard", "📝 Produção", "💰 Insumos", "📋 Relatórios", "⚙️ Configurações", "🔧 Administrativo"]
        
        selected = option_menu(
            menu_title="Navegação",
            options=menu_options,
            icons=["speedometer2", "pencil", "cash-coin", "file-text", "gear", "tools"],
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {"padding": "5px", "background-color": "#1a1a1a"},
                "icon": {"color": "#2d5016", "font-size": "18px"},
                "nav-link": {"font-size": "16px", "text-align": "left", "margin": "0px", "color": "white"},
                "nav-link-selected": {"background-color": "#2d5016"},
            }
        )
    
    # Navegação entre páginas - ADICIONADO ADMINISTRATIVO
    if selected == "📊 Dashboard":
        show_dashboard()
    elif selected == "📝 Produção":
        show_production_page()
    elif selected == "💰 Insumos":
        show_inputs_page()
    elif selected == "📋 Relatórios":
        show_reports_page()
    elif selected == "⚙️ Configurações":
        show_settings_page()
    elif selected == "🔧 Administrativo":
        show_admin_page()

# ================================
# EXECUÇÃO DO APLICATIVO
# ================================
if __name__ == "__main__":
    main()
