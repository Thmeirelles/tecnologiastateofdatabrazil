import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import warnings
import csv
import re
from io import StringIO
warnings.filterwarnings('ignore')

# Configuração da página
st.set_page_config(
    page_title="State of Data Brazil - Análise de Tecnologias",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título principal
st.title("🛠️ State of Data Brazil 2021 - Análise de Tecnologias")
st.markdown("""
**UFBa - Estatística | Análise Exploratória de Dados**  
**Professor:** Ricardo Rocha | **Dataset:** State of Data Brazil 2021  
**Foco da Análise:** Tecnologias e Ferramentas Utilizadas por Profissionais de Dados no Brasil
""")

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================
def limpar_nome_coluna(nome):
    """Remove sufixos .1, .2, etc. dos nomes das colunas"""
    if isinstance(nome, str):
        nome = re.sub(r'\.\d+$', '', nome)
        nome = nome.strip()
    return nome

def consolidar_colunas_duplicadas(df):
    """
    Consolida colunas com nomes iguais (mas com sufixos .1, .2, etc.)
    mantendo o valor máximo (1 se pelo menos uma coluna for 1)
    """
    col_map = {}
    for col in df.columns:
        nome_limpo = limpar_nome_coluna(col)
        if nome_limpo != col:
            col_map[col] = nome_limpo
    
    df = df.rename(columns=col_map)
    
    colunas_agrupadas = {}
    for col in df.columns:
        if col not in colunas_agrupadas:
            colunas_agrupadas[col] = []
        colunas_agrupadas[col].append(col)
    
    colunas_para_remover = []
    novas_colunas = {}
    
    for nome_base, colunas in colunas_agrupadas.items():
        if len(colunas) > 1:
            df_temp = df[colunas]
            nova_col = df_temp.max(axis=1)
            novas_colunas[nome_base] = nova_col
            colunas_para_remover.extend(colunas)
    
    df = df.drop(columns=colunas_para_remover)
    
    for nome, valores in novas_colunas.items():
        df[nome] = valores
    
    return df

# ============================================================================
# FUNÇÕES DE AGRUPAMENTO CORRIGIDAS - AGORA JUNTANDO SQL, DADOS RELACIONAIS E BANCOS RELACIONAIS
# ============================================================================
def calcular_uso_individual(df_filtrado, tech_columns):
    """Calcula uso individual de cada tecnologia sem agrupamento"""
    tech_data = []
    for tech in tech_columns:
        if tech in df_filtrado.columns:
            try:
                uso = df_filtrado[tech].mean() * 100
                usuarios = int(df_filtrado[tech].sum())
                total = len(df_filtrado)
                tech_data.append({
                    'Tecnologia': limpar_nome_coluna(tech),
                    'Uso (%)': uso,
                    'Usuários': usuarios,
                    'Total': total,
                    'Coluna Original': tech
                })
            except:
                continue
    
    if not tech_data:
        return None
    
    df_tech = pd.DataFrame(tech_data)
    df_tech = df_tech.drop_duplicates(subset='Tecnologia', keep='first')
    return df_tech

def calcular_uso_com_grupos_unificado(df_filtrado, tech_columns):
    """
    Calcula uso de tecnologias com agrupamento UNIFICADO
    Agora SQL, Dados relacionais e Bancos relacionais estão em um único grupo "SQL"
    """
    # Primeiro, calcular uso individual de todas as tecnologias
    df_individual = calcular_uso_individual(df_filtrado, tech_columns)
    if df_individual is None:
        return None
    
    # Dicionário de agrupamentos UNIFICADO
    grupos_tecnologias = {
        # GRUPO UNIFICADO SQL - INCLUI LINGUAGEM, DADOS E BANCOS RELACIONAIS
        'SQL (linguagem, dados relacionais e bancos)': [
            # Linguagem SQL
            'SQL',
            # Dados relacionais (fonte de dados)
            'Dados relacionais',
            # Bancos de dados relacionais
            'MySQL', 'PostgreSQL', 'SQL SERVER', 'SQLite', 
            'MariaDB', 'Oracle', 'DB2', 'Microsoft Access', 'Sybase'
        ],
        
        # Grupo Cloud AWS
        'AWS (serviços diversos)': [
            'Amazon Aurora ou RDS', 'Amazon DynamoDB', 
            'Amazon Redshift', 'Amazon Athena', 'S3'
        ],
        
        # Grupo Google Cloud
        'Google Cloud (BigQuery, Firestore)': ['Google BigQuery', 'Google Firestore'],
        
        # Grupo NoSQL
        'Bancos NoSQL (MongoDB, Cassandra, Redis, etc.)': [
            'MongoDB', 'Cassandra', 'Redis', 'Neo4J', 
            'CoachDB', 'Datomic', 'HBase', 'Firebird'
        ],
        
        # Grupo Ferramentas BI
        'Ferramentas BI (Tableau, Power BI, etc.)': ['Tableau', 'Power BI', 'Looker', 'Qlik'],
        
        # Grupo Big Data
        'Plataformas Big Data (Spark, Hadoop, etc.)': [
            'Spark', 'Hadoop', 'Kafka', 'Hive', 'Presto', 
            'Snowflake', 'Databricks', 'HBase'
        ]
    }
    
    # Inverter o dicionário para mapear cada tecnologia para seu grupo
    mapa_tecnologia_grupo = {}
    for grupo, tecnologias in grupos_tecnologias.items():
        for tech in tecnologias:
            mapa_tecnologia_grupo[tech.lower()] = grupo
    
    # Preparar lista para dados agrupados
    dados_agrupados = []
    tecnologias_processadas = set()
    
    # Processar grupos primeiro
    for grupo, tecnologias in grupos_tecnologias.items():
        # Encontrar colunas originais correspondentes a este grupo
        colunas_grupo = []
        for tech in tecnologias:
            # Procurar por esta tecnologia no df_individual
            for _, row in df_individual.iterrows():
                if tech.lower() in row['Tecnologia'].lower():
                    colunas_grupo.append(row['Coluna Original'])
                    tecnologias_processadas.add(row['Tecnologia'])
                    break
        
        if colunas_grupo:
            # Abordagem correta: criar coluna temporária para o grupo
            temp_col_name = f'_temp_{grupo[:10]}'
            df_temp = df_filtrado.copy()
            
            # Inicializar com 0
            df_temp[temp_col_name] = 0
            
            # Para cada coluna do grupo, marcar como 1 se usar
            for col in colunas_grupo:
                if col in df_temp.columns:
                    df_temp.loc[df_temp[col] == 1, temp_col_name] = 1
            
            # Calcular estatísticas do grupo
            uso_grupo = df_temp[temp_col_name].mean() * 100
            usuarios_grupo = int(df_temp[temp_col_name].sum())
            
            dados_agrupados.append({
                'Tecnologia': grupo,
                'Uso (%)': uso_grupo,
                'Usuários': usuarios_grupo,
                'Total': len(df_filtrado),
                'Coluna Original': ', '.join(colunas_grupo[:3]) + ('...' if len(colunas_grupo) > 3 else '')
            })
    
    # Adicionar tecnologias não agrupadas (excluindo as que já estão no grupo SQL)
    for _, row in df_individual.iterrows():
        if row['Tecnologia'] not in tecnologias_processadas:
            # Verificar se esta tecnologia não pertence a nenhum grupo
            tech_lower = row['Tecnologia'].lower()
            pertence_grupo = False
            for tech_key, grupo in mapa_tecnologia_grupo.items():
                if tech_key in tech_lower:
                    pertence_grupo = True
                    break
            
            if not pertence_grupo:
                dados_agrupados.append({
                    'Tecnologia': row['Tecnologia'],
                    'Uso (%)': row['Uso (%)'],
                    'Usuários': row['Usuários'],
                    'Total': row['Total'],
                    'Coluna Original': row['Coluna Original']
                })
    
    # Criar DataFrame final
    df_agrupado = pd.DataFrame(dados_agrupados)
    
    # Ordenar por uso
    df_agrupado = df_agrupado.sort_values('Uso (%)', ascending=False)
    
    return df_agrupado

# ============================================================================
# FUNÇÃO PARA CARREGAR O DATASET COMPLETO COM CORREÇÕES
# ============================================================================
@st.cache_data
def load_complete_dataset():
    """
    Carrega o dataset completo (2.645 linhas) com tratamento de erros
    """
    try:
        file_path = r"C:\Users\Pichau\OneDrive\Área de Trabalho\State of Data Brazil\Banco\State of Data Brazil 2021.csv"
        
        if not os.path.exists(file_path):
            st.error(f"❌ Arquivo não encontrado: {file_path}")
            return None, []
        
        st.sidebar.info(f"📂 Carregando arquivo: {file_path}")
        st.sidebar.info(f"📏 Tamanho do arquivo: {os.path.getsize(file_path) / 1024**2:.2f} MB")
        
        # MÉTODO 1: Tentar ler com engine python e tratamento de erros
        try:
            df = pd.read_csv(
                file_path, 
                encoding='utf-8',
                engine='python',
                on_bad_lines='skip',  # Pular linhas com problemas
                quoting=csv.QUOTE_MINIMAL,
                sep=','
            )
            st.sidebar.success(f"✅ Método 1: {len(df)} linhas carregadas")
        except Exception as e:
            st.sidebar.warning(f"⚠️ Método 1 falhou: {str(e)[:50]}")
            df = None
        
        # MÉTODO 2: Se não carregou tudo, tentar com encoding latin-1
        if df is None or len(df) < 2000:
            try:
                df = pd.read_csv(
                    file_path,
                    encoding='latin-1',
                    engine='python',
                    on_bad_lines='skip',
                    sep=','
                )
                st.sidebar.success(f"✅ Método 2: {len(df)} linhas carregadas")
            except:
                pass
        
        # MÉTODO 3: Ler linha por linha e limpar
        if df is None or len(df) < 2000:
            st.sidebar.info("🔄 Tentando método 3: leitura linha por linha...")
            try:
                lines = []
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for i, line in enumerate(f):
                        if i == 0:
                            header = line.strip()
                            lines.append(header)
                        elif len(line.strip()) > 10:  # Ignorar linhas muito curtas
                            lines.append(line.strip())
                
                # Tentar criar DataFrame a partir das linhas
                if len(lines) > 0:
                    data_string = '\n'.join(lines)
                    df = pd.read_csv(StringIO(data_string), sep=',', engine='python')
                    st.sidebar.success(f"✅ Método 3: {len(df)} linhas carregadas")
            except Exception as e:
                st.sidebar.error(f"❌ Método 3 falhou: {str(e)[:50]}")
        
        if df is None:
            st.error("❌ Não foi possível carregar o dataset")
            return None, []
        
        # Verificar se temos colunas suficientes
        if len(df.columns) < 5:
            st.error(f"❌ Muito poucas colunas: {len(df.columns)}")
            return None, []
        
        st.sidebar.success(f"🎉 Dataset carregado: {len(df)} linhas × {len(df.columns)} colunas")
        
        # ================================================================
        # CORRIGIR NOMES DE COLUNAS E CONSOLIDAR DUPLICATAS
        # ================================================================
        st.sidebar.info("🔄 Consolidando colunas duplicadas...")
        
        def corrigir_coluna(nome):
            """Corrige problemas de encoding em nomes das colunas"""
            if isinstance(nome, str):
                try:
                    return nome.encode('latin-1').decode('utf-8')
                except:
                    try:
                        return nome.encode('utf-8').decode('utf-8')
                    except:
                        return nome
            return nome
        
        df.columns = [corrigir_coluna(col) for col in df.columns]
        
        df = consolidar_colunas_duplicadas(df)
        
        st.sidebar.success(f"✅ Colunas após consolidação: {len(df.columns)}")
        
        # ================================================================
        # IDENTIFICAR COLUNAS DE TECNOLOGIAS (0/1)
        # ================================================================
        
        tech_columns = []
        
        tecnologias_esperadas = [
            # Linguagens
            'SQL', 'R', 'Python', 'C/C++/C#', '.NET', 'Java', 'Julia',
            'SAS/Stata', 'Visual Basic/VBA', 'Scala', 'Matlab', 'PHP',
            'Javascript', 'Não utilizo nenhuma linguagem',
            
            # Fontes de dados
            'Dados relacionais', 'Dados em bancos NoSQL', 'Imagens',
            'Textos/Documentos', 'Vídeos', 'Áudios', 'Planilhas',
            'Dados georreferenciados',
            
            # Bancos de dados
            'MySQL', 'Oracle', 'SQL SERVER', 'SAP', 'Amazon Aurora ou RDS',
            'Amazon DynamoDB', 'CoachDB', 'Cassandra', 'MongoDB', 'MariaDB',
            'Datomic', 'S3', 'PostgreSQL', 'ElasticSearch', 'DB2',
            'Microsoft Access', 'SQLite', 'Sybase', 'Firebase', 'Vertica',
            'Redis', 'Neo4J', 'Google BigQuery', 'Google Firestore',
            'Amazon Redshift', 'Amazon Athena', 'Snowflake', 'Databricks',
            'HBase', 'Presto', 'Splunk', 'SAP HANA', 'Hive', 'Firebird',
            
            # Cloud
            'AWS', 'Google Cloud', 'Azure', 'Oracle Cloud', 'IBM',
            'Servidores On Premise/Não utilizamos Cloud', 'Cloud Própria'
        ]
        
        for tech in tecnologias_esperadas:
            for col in df.columns:
                if tech.lower() in col.lower():
                    tech_columns.append(col)
                    break
        
        padroes_tech = [
            'sql', 'python', 'r$', 'java', 'javascript', 'c\+\+', 'c#', '\.net',
            'scala', 'julia', 'sas', 'stata', 'matlab', 'php', 'visual basic',
            'mysql', 'postgres', 'oracle', 'mongodb', 'redis', 'firebase',
            'aws', 'azure', 'google', 'cloud', 'ibm', 'dados relacionais',
            'nosql', 'imagens', 'textos', 'documentos', 'vídeos', 'áudios',
            'planilhas', 'georreferenciados', 'bigquery', 'databricks',
            'snowflake', 'spark', 'kafka', 'hadoop', 'tableau', 'power bi',
            'looker', 'qlik', 'excel'
        ]
        
        for padrao in padroes_tech:
            for col in df.columns:
                col_lower = col.lower()
                if padrao in col_lower and col not in tech_columns:
                    if not ('?' in col or 'quais' in col_lower or 'entre' in col_lower):
                        tech_columns.append(col)
        
        tech_columns_unicos = []
        nomes_vistos = set()
        
        for col in tech_columns:
            nome_limpo = limpar_nome_coluna(col)
            if nome_limpo not in nomes_vistos:
                nomes_vistos.add(nome_limpo)
                tech_columns_unicos.append(col)
        
        tech_columns = tech_columns_unicos
        
        st.sidebar.success(f"🔧 {len(tech_columns)} colunas de tecnologia identificadas")
        
        # Converter colunas de tecnologia para binário (0/1)
        for col in tech_columns:
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
                if df[col].isna().all():
                    df[col] = df[col].astype(str).str.strip().str.lower()
                    
                    df[col] = df[col].replace({
                        '1': 1, '1.0': 1, 'sim': 1, 'yes': 1, 'true': 1, 's': 1, 'y': 1,
                        '0': 0, '0.0': 0, 'não': 0, 'nao': 0, 'no': 0, 'false': 0, 'n': 0
                    })
                    
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                df[col] = df[col].fillna(0)
                df[col] = df[col].astype(int)
                
            except Exception as e:
                st.sidebar.warning(f"⚠️ Não foi possível converter {col}: {str(e)[:50]}")
                if col in tech_columns:
                    tech_columns.remove(col)
        
        # ================================================================
        # PROCESSAMENTO DE COLUNAS ESPECÍFICAS
        # ================================================================
        
        processed_df = df.copy()
        
        # Processar Idade
        if 'Idade' in processed_df.columns:
            processed_df['Idade'] = pd.to_numeric(processed_df['Idade'], errors='coerce')
            
            if processed_df['Idade'].isna().any():
                median_age = processed_df['Idade'].median()
                processed_df['Idade'] = processed_df['Idade'].fillna(median_age)
            
            bins = [0, 25, 35, 45, 55, 100]
            labels = ['<25', '25-34', '35-44', '45-54', '55+']
            processed_df['faixa_etaria'] = pd.cut(processed_df['Idade'], bins=bins, labels=labels, right=False)
        
        # Processar UF e Região
        if 'UF' in processed_df.columns:
            processed_df['UF'] = processed_df['UF'].astype(str).str.strip().str.upper()
            
            regioes = {
                'AC': 'Norte', 'AL': 'Nordeste', 'AP': 'Norte', 'AM': 'Norte',
                'BA': 'Nordeste', 'CE': 'Nordeste', 'DF': 'Centro-Oeste',
                'ES': 'Sudeste', 'GO': 'Centro-Oeste', 'MA': 'Nordeste',
                'MT': 'Centro-Oeste', 'MS': 'Centro-Oeste', 'MG': 'Sudeste',
                'PA': 'Norte', 'PB': 'Nordeste', 'PR': 'Sul', 'PE': 'Nordeste',
                'PI': 'Nordeste', 'RJ': 'Sudeste', 'RN': 'Nordeste',
                'RS': 'Sul', 'RO': 'Norte', 'RR': 'Norte', 'SC': 'Sul',
                'SP': 'Sudeste', 'SE': 'Nordeste', 'TO': 'Norte'
            }
            
            processed_df['regiao'] = processed_df['UF'].map(regioes)
            processed_df['regiao'] = processed_df['regiao'].fillna('Outros')
        
        # Processar Senioridade
        if 'Senioridade' in processed_df.columns:
            processed_df['Senioridade'] = processed_df['Senioridade'].astype(str).str.strip()
            
            if 'Gestor?' in processed_df.columns:
                processed_df['Gestor?'] = pd.to_numeric(processed_df['Gestor?'], errors='coerce')
                
                mask_gestor = (processed_df['Senioridade'].isin(['nan', 'NaN', '', 'None', 'null'])) & (processed_df['Gestor?'] == 1)
                processed_df.loc[mask_gestor, 'Senioridade'] = 'Gestor'
            
            senioridade_map = {
                'junior': 'Júnior',
                'pleno': 'Pleno',
                'senior': 'Sênior',
                'sênior': 'Sênior',
                'especialista': 'Especialista',
                'gestor': 'Gestor',
                'coordenador': 'Coordenador',
                'gerente': 'Gerente',
                'diretor': 'Diretor',
                'lider': 'Líder',
                'head': 'Head',
                'estagiário': 'Estagiário',
                'trainee': 'Trainee',
                'assistente': 'Assistente'
            }
            
            for key, value in senioridade_map.items():
                mask = processed_df['Senioridade'].str.lower().str.contains(key, na=False)
                processed_df.loc[mask, 'Senioridade'] = value
            
            mask_nan = processed_df['Senioridade'].isin(['nan', 'NaN', '', 'None', 'null'])
            processed_df.loc[mask_nan, 'Senioridade'] = 'Não informado'
        
        # Processar Gênero (mantido para análise, mas sem filtro)
        if 'Gênero' in processed_df.columns:
            processed_df['Gênero'] = processed_df['Gênero'].astype(str).str.strip()
            
            genero_map = {
                'masculino': 'Masculino',
                'feminino': 'Feminino',
                'm': 'Masculino',
                'f': 'Feminino',
                'homem': 'Masculino',
                'mulher': 'Feminino'
            }
            
            for key, value in genero_map.items():
                mask = processed_df['Gênero'].str.lower().str.contains(key)
                processed_df.loc[mask, 'Gênero'] = value
        
        # Processar outras colunas categóricas
        categorias_para_limpar = [
            'Nível de Ensino', 'Área de Formação', 'Setor', 
            'Faixa salarial', 'Forma de trabalho', 'Atuação'
        ]
        
        for col in categorias_para_limpar:
            if col in processed_df.columns:
                processed_df[col] = processed_df[col].astype(str).str.strip()
        
        return processed_df, tech_columns
        
    except Exception as e:
        st.error(f"❌ Erro ao processar dados: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None, []

# ============================================================================
# FUNÇÕES DE ANÁLISE DE TECNOLOGIAS UNIFICADAS
# ============================================================================
def calcular_uso_tecnologias(df_filtrado, tech_columns, usar_grupos=True):
    """
    Analisa e retorna dados de uso de tecnologias
    """
    if not tech_columns or df_filtrado.empty:
        return None
    
    if usar_grupos:
        return calcular_uso_com_grupos_unificado(df_filtrado, tech_columns)
    else:
        return calcular_uso_individual(df_filtrado, tech_columns)

def categorizar_tecnologias(df_tech):
    """Categoriza as tecnologias em grupos"""
    categorias = {
        'Linguagens de Programação': [],
        'Bancos de Dados': [],
        'Plataformas Cloud': [],
        'Fontes de Dados': [],
        'Ferramentas BI/Visualização': [],
        'Big Data/Processamento': [],
        'Outras Ferramentas': []
    }
    
    for _, row in df_tech.iterrows():
        tech = row['Tecnologia'].lower()
        
        # Verificar se é o grupo SQL unificado
        if 'sql (linguagem, dados relacionais e bancos)' in tech:
            categorias['Bancos de Dados'].append(row['Tecnologia'])
        # Outras categorizações
        elif any(padrao in tech for padrao in ['python', 'r', 'java', 'javascript', 
                                            'c++', 'c#', '.net', 'scala', 'julia', 'php',
                                            'sas', 'stata', 'matlab', 'visual basic', 'vba']):
            if not any(padrao in tech for padrao in ['banco', 'database', 'mysql', 'postgres', 'oracle']):
                categorias['Linguagens de Programação'].append(row['Tecnologia'])
        elif any(padrao in tech for padrao in ['mysql', 'postgres', 'oracle', 'mongodb',
                                              'redis', 'firebase', 'sql server', 'database',
                                              'cassandra', 'elasticsearch', 'sqlite', 'neo4j',
                                              'bigquery', 'snowflake', 'databricks', 'hbase',
                                              'hive', 'firebird', 'mariadb', 'db2', 'access',
                                              'nosql', 'dados relacionais', 'banco']):
            categorias['Bancos de Dados'].append(row['Tecnologia'])
        elif any(padrao in tech for padrao in ['aws', 'azure', 'google cloud', 'ibm',
                                              'cloud', 'oracle cloud', 'amazon']):
            categorias['Plataformas Cloud'].append(row['Tecnologia'])
        elif any(padrao in tech for padrao in ['dados relacionais', 'nosql', 'imagens',
                                              'textos', 'documentos', 'vídeos', 'áudios',
                                              'planilhas', 'georreferenciados', 'fontes']):
            categorias['Fontes de Dados'].append(row['Tecnologia'])
        elif any(padrao in tech for padrao in ['tableau', 'power bi', 'looker', 'qlik',
                                              'bi', 'visualização']):
            categorias['Ferramentas BI/Visualização'].append(row['Tecnologia'])
        elif any(padrao in tech for padrao in ['spark', 'hadoop', 'kafka', 'presto',
                                              'databricks', 'snowflake', 'big data',
                                              'processamento']):
            categorias['Big Data/Processamento'].append(row['Tecnologia'])
        else:
            categorias['Outras Ferramentas'].append(row['Tecnologia'])
    
    # Remover categorias vazias
    categorias = {k: v for k, v in categorias.items() if v}
    
    return categorias

# ============================================================================
# CONFIGURAÇÃO DE GRÁFICOS
# ============================================================================
def configurar_grafico(fig, altura_minima=400):
    """Configurações comuns para todos os gráficos"""
    fig.update_layout(
        height=altura_minima,
        margin=dict(l=20, r=20, t=50, b=20),
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="Arial"
        ),
        xaxis=dict(
            title_font=dict(size=14),
            tickfont=dict(size=12)
        ),
        yaxis=dict(
            title_font=dict(size=14),
            tickfont=dict(size=12)
        )
    )
    return fig

# ============================================================================
# VERIFICAÇÃO DO DATASET
# ============================================================================
st.sidebar.header("📂 VERIFICAÇÃO DO DATASET")

if st.sidebar.button("🔍 Verificar integridade do arquivo"):
    try:
        file_path = r"C:\Users\Pichau\OneDrive\Área de Trabalho\State of Data Brazil\Banco\State of Data Brazil 2021.csv"
        
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                line_count = sum(1 for line in f)
            
            st.sidebar.info(f"📏 Linhas totais no arquivo: {line_count}")
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                header = f.readline().strip()
                st.sidebar.info(f"📝 Cabeçalho: {header[:100]}...")
                
                num_cols = len(header.split(','))
                st.sidebar.info(f"🔢 Colunas no cabeçalho: {num_cols}")
        else:
            st.sidebar.error("❌ Arquivo não encontrado")
    except Exception as e:
        st.sidebar.error(f"❌ Erro na verificação: {str(e)}")

# ============================================================================
# CARREGAMENTO DOS DADOS
# ============================================================================
if 'df' not in st.session_state:
    with st.spinner("Carregando dataset..."):
        df, tech_columns = load_complete_dataset()
        if df is not None:
            st.session_state['df'] = df
            st.session_state['tech_columns'] = tech_columns
            st.session_state['data_loaded'] = True
            st.rerun()
        else:
            st.error("❌ Não foi possível carregar o dataset")
            st.stop()

df = st.session_state['df']
tech_columns = st.session_state['tech_columns']

# ============================================================================
# FILTROS INTERATIVOS (SEM GÊNERO)
# ============================================================================
st.sidebar.header("🔍 FILTROS DE ANÁLISE")

# Filtro de idade (mantido)
if 'Idade' in df.columns:
    idade_min = int(df['Idade'].min())
    idade_max = int(df['Idade'].max())
    idade_range = st.sidebar.slider(
        "Faixa de Idade", 
        idade_min, idade_max, 
        (max(20, idade_min), min(60, idade_max))
    )

# Filtro de UF (mantido)
if 'UF' in df.columns:
    uf_opcoes = df['UF'].dropna().unique()
    ufs_selecionadas = st.sidebar.multiselect(
        "UF", 
        uf_opcoes, 
        default=uf_opcoes[:min(5, len(uf_opcoes))]
    )

# Filtro de senioridade - EXCLUIR "Não informado" dos filtros
if 'Senioridade' in df.columns:
    senioridade_opcoes = [s for s in df['Senioridade'].dropna().unique() if s != 'Não informado']
    senioridades_selecionadas = st.sidebar.multiselect(
        "Senioridade", 
        senioridade_opcoes, 
        default=senioridade_opcoes[:min(4, len(senioridade_opcoes))]
    )

# Filtro de forma de trabalho (mantido)
if 'Forma de trabalho' in df.columns:
    forma_opcoes = df['Forma de trabalho'].dropna().unique()
    formas_selecionadas = st.sidebar.multiselect(
        "Forma de Trabalho", 
        forma_opcoes, 
        default=forma_opcoes[:min(3, len(forma_opcoes))]
    )

# ============================================================================
# APLICAR FILTROS (SEM FILTRO DE GÊNERO)
# ============================================================================
df_filtrado = df.copy()

if 'Idade' in df_filtrado.columns and 'idade_range' in locals():
    df_filtrado = df_filtrado[
        (df_filtrado['Idade'] >= idade_range[0]) & 
        (df_filtrado['Idade'] <= idade_range[1])
    ]

# FILTRO DE GÊNERO REMOVIDO

if 'ufs_selecionadas' in locals() and ufs_selecionadas:
    df_filtrado = df_filtrado[df_filtrado['UF'].isin(ufs_selecionadas)]

if 'senioridades_selecionadas' in locals() and senioridades_selecionadas:
    df_filtrado = df_filtrado[df_filtrado['Senioridade'].isin(senioridades_selecionadas)]

if 'formas_selecionadas' in locals() and formas_selecionadas:
    df_filtrado = df_filtrado[df_filtrado['Forma de trabalho'].isin(formas_selecionadas)]

# ============================================================================
# METADADOS DA ANÁLISE
# ============================================================================
st.sidebar.header("📊 METADADOS")
st.sidebar.metric("Respondentes", f"{len(df_filtrado):,}")
st.sidebar.metric("Tecnologias", len(tech_columns))

# ============================================================================
# SEÇÃO 1: VISÃO GERAL
# ============================================================================
st.header("📊 VISÃO GERAL DA ANÁLISE")

col1, col2, col3, col4 = st.columns(4)

with col1:
    total = len(df_filtrado)
    st.metric("RESPONDENTES FILTRADOS", f"{total:,}".replace(",", "."))

with col2:
    if 'Idade' in df_filtrado.columns:
        idade_media = df_filtrado['Idade'].mean()
        st.metric("IDADE MÉDIA", f"{idade_media:.1f} anos")

with col3:
    if 'Senioridade' in df_filtrado.columns:
        senior_counts = df_filtrado[df_filtrado['Senioridade'] != 'Não informado']['Senioridade'].value_counts()
        if not senior_counts.empty:
            st.metric("SENIORIDADE PRINCIPAL", senior_counts.index[0])
        else:
            st.metric("SENIORIDADE", "N/A")

with col4:
    if 'regiao' in df_filtrado.columns:
        regiao_counts = df_filtrado['regiao'].value_counts()
        if not regiao_counts.empty:
            st.metric("REGIÃO PRINCIPAL", regiao_counts.index[0])

# ============================================================================
# SEÇÃO 2: TOP TECNOLOGIAS MAIS UTILIZADAS (COM SQL UNIFICADO)
# ============================================================================
st.header("🏆 TOP TECNOLOGIAS MAIS UTILIZADAS")

# Adicionar informação sobre o novo agrupamento SQL
st.info("""
**Novo agrupamento SQL:** 
- **SQL (linguagem)** + **Dados relacionais (fonte)** + **Bancos relacionais (MySQL, PostgreSQL, etc.)** = **Grupo SQL unificado**
- Este grupo representa pessoas que usam PELO MENOS UMA dessas tecnologias relacionais
- **Resultado esperado:** Grupo SQL deve aparecer com uso muito alto (provavelmente >80%)
""")

usar_grupos = st.checkbox("Agrupar tecnologias similares (SQL unificado, AWS, NoSQL, etc.)", value=True)

# Calcular uso de tecnologias com ou sem grupos
df_tech = calcular_uso_tecnologias(df_filtrado, tech_columns, usar_grupos=usar_grupos)

if df_tech is None or df_tech.empty:
    st.error("Não foi possível calcular o uso de tecnologias. Verifique os dados.")
    st.stop()

# Categorizar tecnologias
categorias = categorizar_tecnologias(df_tech)

# Top 10 geral - AGORA COM SQL UNIFICADO
st.subheader("Top 10 - Todas as Tecnologias")
df_top10 = df_tech.sort_values('Uso (%)', ascending=False).head(10)

fig1 = px.bar(
    df_top10,
    x='Uso (%)',
    y='Tecnologia',
    orientation='h',
    title='Top 10 Tecnologias Mais Utilizadas (%)' + (' - Com Agrupamentos' if usar_grupos else ' - Sem Agrupamentos'),
    color='Uso (%)',
    color_continuous_scale='Viridis',
    text='Uso (%)'
)
fig1.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
fig1.update_layout(
    yaxis={'categoryorder': 'total ascending'},
    height=500
)
fig1 = configurar_grafico(fig1, 500)
st.plotly_chart(fig1, use_container_width=True)

# Mostrar estatísticas do grupo SQL unificado
if usar_grupos:
    sql_grupo = df_tech[df_tech['Tecnologia'].str.contains('SQL (linguagem, dados relacionais e bancos)', case=False, na=False)]
    if not sql_grupo.empty:
        uso_sql_grupo = sql_grupo.iloc[0]['Uso (%)']
        usuarios_sql_grupo = sql_grupo.iloc[0]['Usuários']
        total_respondentes = sql_grupo.iloc[0]['Total']
        
        st.success(f"""
        **📊 Grupo SQL Unificado:**
        - **Uso:** {uso_sql_grupo:.1f}% dos respondentes
        - **Usuários:** {usuarios_sql_grupo:,} de {total_respondentes:,} respondentes
        - **Interpretação:** {uso_sql_grupo:.1f}% dos profissionais usam pelo menos uma tecnologia relacionada a SQL
        """)

# ============================================================================
# SEÇÃO 3: TOP POR CATEGORIA
# ============================================================================
st.subheader("📊 Top por Categoria")

# Seletor de categoria
categorias_disponiveis = ['Todas'] + list(categorias.keys())
categoria_selecionada_top = st.selectbox(
    "Selecione uma categoria para ver o top:",
    categorias_disponiveis,
    key='top_categoria'
)

if categoria_selecionada_top == 'Todas':
    df_categoria_top = df_tech.copy()
    titulo_categoria = "Top Tecnologias - Todas as Categorias"
else:
    techs_categoria = [t for t in df_tech['Tecnologia'] if t in categorias[categoria_selecionada_top]]
    df_categoria_top = df_tech[df_tech['Tecnologia'].isin(techs_categoria)]
    titulo_categoria = f"Top Tecnologias - {categoria_selecionada_top}"

# Ordenar e limitar a 10
df_categoria_top = df_categoria_top.sort_values('Uso (%)', ascending=False).head(10)

if not df_categoria_top.empty:
    fig_categoria = px.bar(
        df_categoria_top,
        x='Uso (%)',
        y='Tecnologia',
        orientation='h',
        title=titulo_categoria,
        color='Uso (%)',
        color_continuous_scale='Blues',
        text='Uso (%)'
    )
    fig_categoria.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig_categoria.update_layout(
        height=max(400, len(df_categoria_top) * 35),
        yaxis={'categoryorder': 'total ascending'}
    )
    fig_categoria = configurar_grafico(fig_categoria, max(400, len(df_categoria_top) * 35))
    st.plotly_chart(fig_categoria, use_container_width=True)
else:
    st.warning(f"Nenhuma tecnologia encontrada na categoria {categoria_selecionada_top}")

# ============================================================================
# SEÇÃO 4: ANÁLISE DETALHADA POR CATEGORIA
# ============================================================================
st.header("📊 ANÁLISE DETALHADA POR CATEGORIA")

if usar_grupos:
    st.info("ℹ️ **Tecnologias similares estão agrupadas** (SQL unificado, AWS, NoSQL, etc.)")

categoria_selecionada = st.selectbox(
    "Selecione uma categoria para análise detalhada:",
    ['Todas as Categorias'] + list(categorias.keys()),
    key='categoria_detalhada'
)

if categoria_selecionada == 'Todas as Categorias':
    df_analise = df_tech.copy()
    titulo_analise = 'Todas as Tecnologias'
else:
    techs_categoria = [t for t in df_tech['Tecnologia'] if t in categorias[categoria_selecionada]]
    df_analise = df_tech[df_tech['Tecnologia'].isin(techs_categoria)]
    titulo_analise = f'{categoria_selecionada}'

# Ordenar por uso
df_analise = df_analise.sort_values('Uso (%)', ascending=False)

# Mostrar estatísticas da categoria
if categoria_selecionada != 'Todas as Categorias':
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(f"Tecnologias em {categoria_selecionada}", len(df_analise))
    with col2:
        st.metric("Uso Médio", f"{df_analise['Uso (%)'].mean():.1f}%")
    with col3:
        st.metric("Tecnologia Mais Usada", df_analise.iloc[0]['Tecnologia'] if len(df_analise) > 0 else "N/A")

# Mostrar gráfico
if not df_analise.empty:
    fig2 = px.bar(
        df_analise.head(20),
        x='Uso (%)',
        y='Tecnologia',
        orientation='h',
        title=f'Uso de Tecnologias - {titulo_analise}',
        color='Uso (%)',
        color_continuous_scale='Plasma',
        text='Uso (%)',
        height=max(500, len(df_analise.head(20)) * 30)
    )
    fig2.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig2.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        uniformtext_minsize=8,
        uniformtext_mode='hide'
    )
    fig2 = configurar_grafico(fig2, max(500, len(df_analise.head(20)) * 30))
    st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': True})
    
    # Adicionar tabela de dados
    with st.expander("📋 Ver dados detalhados"):
        st.dataframe(
            df_analise[['Tecnologia', 'Uso (%)', 'Usuários']].sort_values('Uso (%)', ascending=False),
            use_container_width=True,
            height=400
        )
else:
    st.warning(f"Nenhuma tecnologia encontrada na categoria {categoria_selecionada}")

# ============================================================================
# SEÇÃO 5: ANÁLISE POR PERFIL DEMOGRÁFICO (SEM FILTRO DE GÊNERO)
# ============================================================================
st.header("👥 ANÁLISE POR PERFIL DEMOGRÁFICO")

col1, col2 = st.columns(2)

with col1:
    # Seletor de variável demográfica - MANTÉM GÊNERO PARA ANÁLISE, MAS SEM FILTRO
    variaveis_disp = []
    for var in ['Gênero', 'faixa_etaria', 'UF', 'regiao', 'Senioridade', 
                'Nível de Ensino', 'Área de Formação', 'Forma de trabalho', 'Atuação']:
        if var in df_filtrado.columns:
            if var == 'Senioridade':
                valores_unicos = df_filtrado[df_filtrado['Senioridade'] != 'Não informado'][var].unique()
            else:
                valores_unicos = df_filtrado[var].unique()
            
            if len(valores_unicos) > 1:
                variaveis_disp.append(var)
    
    if variaveis_disp:
        variavel_demografica = st.selectbox(
            "Selecione a variável demográfica:",
            variaveis_disp
        )

with col2:
    # Seletor de tecnologia
    tecnologias_disp = df_tech.sort_values('Uso (%)', ascending=False)['Tecnologia'].head(20).tolist()
    if tecnologias_disp:
        tecnologia_demografica = st.selectbox(
            "Selecione a tecnologia para análise:",
            tecnologias_disp
        )

# Realizar análise se ambas as seleções foram feitas
if 'variavel_demografica' in locals() and 'tecnologia_demografica' in locals():
    # Encontrar coluna original da tecnologia
    coluna_original = None
    for _, row in df_tech.iterrows():
        if row['Tecnologia'] == tecnologia_demografica:
            if usar_grupos and ', ' in str(row['Coluna Original']):
                coluna_original = str(row['Coluna Original']).split(', ')[0]
            else:
                coluna_original = row['Coluna Original']
            break
    
    if coluna_original and coluna_original in df_filtrado.columns:
        # Calcular uso por grupo
        if variavel_demografica == 'Senioridade':
            df_temp = df_filtrado[df_filtrado['Senioridade'] != 'Não informado']
        else:
            df_temp = df_filtrado
        
        df_grupo = df_temp.groupby(variavel_demografica)[coluna_original].mean() * 100
        df_grupo = df_grupo.reset_index()
        df_grupo.columns = [variavel_demografica, 'Uso (%)']
        
        df_grupo = df_grupo.dropna()
        df_grupo = df_grupo.sort_values('Uso (%)', ascending=False)
        
        # Criar gráfico
        if not df_grupo.empty:
            fig3 = px.bar(
                df_grupo,
                x=variavel_demografica,
                y='Uso (%)',
                title=f'Uso de {tecnologia_demografica} por {variavel_demografica}',
                color='Uso (%)',
                color_continuous_scale='Purples',
                text='Uso (%)'
            )
            fig3.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig3.update_layout(xaxis_tickangle=-45)
            fig3 = configurar_grafico(fig3, 500)
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.warning(f"Não há dados disponíveis para {tecnologia_demografica} por {variavel_demografica}")

# ============================================================================
# SEÇÃO 6: CORRELAÇÃO ENTRE TECNOLOGIAS
# ============================================================================
st.header("🔗 CORRELAÇÃO ENTRE TECNOLOGIAS")

# Selecionar tecnologias para análise de correlação
techs_correlacao = st.multiselect(
    "Selecione as tecnologias para análise de correlação:",
    df_tech.sort_values('Uso (%)', ascending=False)['Tecnologia'].head(15).tolist(),
    default=df_tech.sort_values('Uso (%)', ascending=False)['Tecnologia'].head(5).tolist(),
    key='correlacao'
)

if len(techs_correlacao) >= 2:
    colunas_originais = []
    for tech in techs_correlacao:
        for _, row in df_tech.iterrows():
            if row['Tecnologia'] == tech:
                if usar_grupos and ', ' in str(row['Coluna Original']):
                    colunas_originais.append(str(row['Coluna Original']).split(', ')[0])
                else:
                    colunas_originais.append(row['Coluna Original'])
                break
    
    colunas_disponiveis = [col for col in colunas_originais if col in df_filtrado.columns]
    
    if len(colunas_disponiveis) >= 2:
        corr_matrix = df_filtrado[colunas_disponiveis].corr()
        
        nomes_limpos = []
        for col in colunas_disponiveis:
            for _, row in df_tech.iterrows():
                if row['Coluna Original'] == col or (isinstance(row['Coluna Original'], str) and col in row['Coluna Original']):
                    nomes_limpos.append(row['Tecnologia'])
                    break
        
        corr_matrix.columns = nomes_limpos
        corr_matrix.index = nomes_limpos
        
        fig4 = px.imshow(
            corr_matrix,
            title='Matriz de Correlação entre Tecnologias',
            color_continuous_scale='RdBu',
            zmin=-1, zmax=1,
            text_auto='.2f',
            aspect='auto'
        )
        fig4 = configurar_grafico(fig4, 500)
        st.plotly_chart(fig4, use_container_width=True)

# ============================================================================
# SEÇÃO 7: COMPARAÇÃO ENTRE GRUPOS
# ============================================================================
st.header("⚖️ COMPARAÇÃO ENTRE GRUPOS")

# Criar abas para diferentes comparações
tab1, tab2, tab3 = st.tabs(["📊 Senioridade", "🌎 Região", "🎓 Nível de Ensino"])

with tab1:
    if 'Senioridade' in df_filtrado.columns:
        senioridades_validas = [s for s in df_filtrado['Senioridade'].unique() if s != 'Não informado']
        
        if len(senioridades_validas) > 1:
            techs_senioridade = st.multiselect(
                "Selecione tecnologias para comparar por senioridade:",
                df_tech.sort_values('Uso (%)', ascending=False)['Tecnologia'].head(10).tolist(),
                default=df_tech.sort_values('Uso (%)', ascending=False)['Tecnologia'].head(3).tolist(),
                key='techs_senioridade'
            )
            
            if techs_senioridade:
                dados_senioridade = []
                for tech in techs_senioridade:
                    col_original = None
                    for _, row in df_tech.iterrows():
                        if row['Tecnologia'] == tech:
                            if usar_grupos and ', ' in str(row['Coluna Original']):
                                col_original = str(row['Coluna Original']).split(', ')[0]
                            else:
                                col_original = row['Coluna Original']
                            break
                    
                    if col_original and col_original in df_filtrado.columns:
                        for senior in senioridades_validas:
                            mask = df_filtrado['Senioridade'] == senior
                            uso = df_filtrado.loc[mask, col_original].mean() * 100
                            if pd.notna(uso):
                                dados_senioridade.append({
                                    'Tecnologia': tech,
                                    'Senioridade': senior,
                                    'Uso (%)': uso
                                })
                
                if dados_senioridade:
                    df_senioridade_plot = pd.DataFrame(dados_senioridade)
                    fig6 = px.bar(
                        df_senioridade_plot,
                        x='Tecnologia',
                        y='Uso (%)',
                        color='Senioridade',
                        barmode='group',
                        title='Comparação do Uso de Tecnologias por Senioridade',
                        text='Uso (%)'
                    )
                    fig6.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                    fig6 = configurar_grafico(fig6, 500)
                    st.plotly_chart(fig6, use_container_width=True)
                else:
                    st.warning("Não há dados disponíveis para comparação por senioridade.")
        else:
            st.info("Não há dados suficientes de senioridade para comparação.")

with tab2:
    if 'regiao' in df_filtrado.columns and df_filtrado['regiao'].nunique() > 1:
        techs_regiao = st.multiselect(
            "Selecione tecnologias para comparar por região:",
            df_tech.sort_values('Uso (%)', ascending=False)['Tecnologia'].head(10).tolist(),
            default=df_tech.sort_values('Uso (%)', ascending=False)['Tecnologia'].head(3).tolist(),
            key='techs_regiao'
        )
        
        if techs_regiao:
            dados_regiao = []
            for tech in techs_regiao:
                col_original = None
                for _, row in df_tech.iterrows():
                    if row['Tecnologia'] == tech:
                        if usar_grupos and ', ' in str(row['Coluna Original']):
                            col_original = str(row['Coluna Original']).split(', ')[0]
                        else:
                            col_original = row['Coluna Original']
                        break
                
                if col_original and col_original in df_filtrado.columns:
                    for regiao in df_filtrado['regiao'].unique():
                        mask = df_filtrado['regiao'] == regiao
                        uso = df_filtrado.loc[mask, col_original].mean() * 100
                        if pd.notna(uso):
                            dados_regiao.append({
                                'Tecnologia': tech,
                                'Região': regiao,
                                'Uso (%)': uso
                            })
            
            if dados_regiao:
                df_regiao_plot = pd.DataFrame(dados_regiao)
                fig7 = px.bar(
                    df_regiao_plot,
                    x='Tecnologia',
                    y='Uso (%)',
                    color='Região',
                    barmode='group',
                    title='Comparação do Uso de Tecnologias por Região',
                    text='Uso (%)'
                )
                fig7.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig7 = configurar_grafico(fig7, 500)
                st.plotly_chart(fig7, use_container_width=True)
            else:
                st.warning("Não há dados disponíveis para comparação por região.")

with tab3:
    if 'Nível de Ensino' in df_filtrado.columns and df_filtrado['Nível de Ensino'].nunique() > 1:
        techs_ensino = st.multiselect(
            "Selecione tecnologias para comparar por nível de ensino:",
            df_tech.sort_values('Uso (%)', ascending=False)['Tecnologia'].head(10).tolist(),
            default=df_tech.sort_values('Uso (%)', ascending=False)['Tecnologia'].head(3).tolist(),
            key='techs_ensino'
        )
        
        if techs_ensino:
            dados_ensino = []
            for tech in techs_ensino:
                col_original = None
                for _, row in df_tech.iterrows():
                    if row['Tecnologia'] == tech:
                        if usar_grupos and ', ' in str(row['Coluna Original']):
                            col_original = str(row['Coluna Original']).split(', ')[0]
                        else:
                            col_original = row['Coluna Original']
                        break
                
                if col_original and col_original in df_filtrado.columns:
                    for ensino in df_filtrado['Nível de Ensino'].unique():
                        mask = df_filtrado['Nível de Ensino'] == ensino
                        uso = df_filtrado.loc[mask, col_original].mean() * 100
                        if pd.notna(uso):
                            dados_ensino.append({
                                'Tecnologia': tech,
                                'Nível de Ensino': ensino,
                                'Uso (%)': uso
                            })
            
            if dados_ensino:
                df_ensino_plot = pd.DataFrame(dados_ensino)
                fig8 = px.bar(
                    df_ensino_plot,
                    x='Tecnologia',
                    y='Uso (%)',
                    color='Nível de Ensino',
                    barmode='group',
                    title='Comparação do Uso de Tecnologias por Nível de Ensino',
                    text='Uso (%)'
                )
                fig8.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig8 = configurar_grafico(fig8, 500)
                st.plotly_chart(fig8, use_container_width=True)
            else:
                st.warning("Não há dados disponíveis para comparação por nível de ensino.")

# ============================================================================
# SEÇÃO DE INFORMAÇÕES SOBRE AGRUPAMENTOS ATUALIZADA
# ============================================================================
with st.expander("ℹ️ Sobre o agrupamento de tecnologias (ATUALIZADO)"):
    st.markdown("""
    ### **AGGRUPAMENTO ATUALIZADO:** SQL Unificado
    
    **Mudança principal:** SQL, Dados relacionais e Bancos relacionais agora estão em um único grupo
    
    **Grupo SQL Unificado inclui:**
    
    **1. SQL (linguagem)** - Linguagem de consulta estruturada
    **2. Dados relacionais (fonte)** - Tipo de fonte de dados (bancos relacionais)
    **3. Bancos de dados relacionais:**
      - MySQL
      - PostgreSQL
      - SQL Server
      - Oracle
      - SQLite
      - MariaDB
      - DB2
      - Microsoft Access
      - Sybase
    
    **Por que agrupar?**
    - Todos estão relacionados ao ecossistema SQL
    - Representa profissionais que trabalham com dados relacionais
    - Evita duplicação na análise (uma pessoa que usa MySQL provavelmente também usa SQL)
    
    **Outros agrupamentos mantidos:**
    
    **AWS (serviços diversos)** inclui:
    - Amazon Aurora ou RDS
    - Amazon DynamoDB
    - Amazon Redshift
    - Amazon Athena
    - Amazon S3
    
    **Google Cloud (BigQuery, Firestore)** inclui:
    - Google BigQuery
    - Google Firestore
    
    **Bancos NoSQL** inclui:
    - MongoDB
    - Cassandra
    - Redis
    - Neo4J
    - CoachDB
    - HBase
    
    **Ferramentas BI** inclui:
    - Tableau
    - Power BI
    - Looker
    - Qlik
    
    **Plataformas Big Data** inclui:
    - Spark
    - Hadoop
    - Kafka
    - Snowflake
    - Databricks
    - HBase
    
    ### Como funciona o cálculo de grupos:
    Quando o agrupamento está ativado, o percentual mostra o uso de **pelo menos uma tecnologia** do grupo.
    Ex: Se alguém usa MySQL e PostgreSQL, conta apenas uma vez para "SQL Unificado".
    
    ### Filtro de gênero removido:
    - O filtro de gênero foi removido da barra lateral para simplificar a interface
    - A análise por gênero ainda está disponível na seção "ANÁLISE POR PERFIL DEMOGRÁFICO"
    """)

# ============================================================================
# RODAPÉ
# ============================================================================
st.markdown("---")
st.markdown("**UFBa - Curso de Estatística | Análise Exploratória de Dados | Professor: Ricardo Rocha**")
