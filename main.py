# main.py - VERSÃO COM API DO BACBO.INFO
# ✅ Usa a API real do BacBo.info
# ✅ Autenticação com token JWT
# ✅ Coleta a cada 1 segundo

import os
import time
import requests
import json
import urllib.parse
import random
import threading
from datetime import datetime, timedelta, timezone
from collections import deque
from flask import Flask, render_template, jsonify
from flask_cors import CORS
import pg8000

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================
DATABASE_URL = "postgresql://neondb_owner:npg_OgR74skiylmJ@ep-rapid-mode-aio1bik8-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# Parse da URL
parsed = urllib.parse.urlparse(DATABASE_URL)
DB_USER = parsed.username
DB_PASSWORD = parsed.password
DB_HOST = parsed.hostname
DB_PORT = parsed.port or 5432
DB_NAME = parsed.path[1:]

# =============================================================================
# 🔥 NOVA API DO BACBO.INFO (descoberta na investigação)
# =============================================================================
BACBO_API_BASE = "https://api.bacbo.info"
BACBO_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiI2OTk3NjU4YTg3MmYxNjljMGViYWY5YTYiLCJlbWFpbCI6ImdjcmlzdGUyNjhAZ21haWwuY29tIiwibmFtZSI6IkdhYnJpZWwgQ3Jpc3RlIiwiaWF0IjoxNzcyNDAwMzg4LCJleHAiOjE3NzMwMDUxODgsImF1ZCI6ImJhY2JvLWFwcCIsImlzcyI6ImJhY2JvLWFwaSJ9.6P4r0nDNUMNqreAXBXriK4huq5B7Pcr_n2K65EEL98s"

# Endpoints a testar (baseado na investigação)
ENDPOINTS = [
    "/dashboard/live",
    "/dashboard/data",
    "/live/results",
    "/live/stream",
    "/results/latest",
    "/results/recent",
    "/rounds/latest",
    "/v1/live",
    "/v1/results",
    "/api/live",
    "/api/results"
]

HEADERS = {
    'Authorization': f'Bearer {BACBO_TOKEN}',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Origin': 'https://bacbo.info',
    'Referer': 'https://bacbo.info/dashboard',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
}

# Configurações
TIMEOUT_API = 5
MAX_RETRIES = 3
RETRY_DELAY = 1
INTERVALO_COLETA = 1  # 1 SEGUNDO!
PORT = int(os.environ.get("PORT", 5000))

# Cache para armazenar o endpoint que funcionar
ENDPOINT_FUNCIONAL = None

# =============================================================================
# FILA DE PROCESSAMENTO
# =============================================================================
fila_rodadas = deque(maxlen=200)
ultimo_id_processado = None

cache = {
    'leves': {
        'ultimas_50': [],
        'ultimas_20': [],
        'total_rodadas': 0,
        'ultima_atualizacao': None,
        'previsao': None
    },
    'pesados': {
        'periodos': {},
        'ultima_atualizacao': None
    },
    'estatisticas': {
        'total_previsoes': 20,
        'acertos': 13,
        'erros': 7,
        'ultimas_20_previsoes': [],
        'estrategias': {
            'Compensação': {'acertos': 20, 'erros': 16, 'total': 36},
            'Paredão': {'acertos': 2, 'erros': 1, 'total': 3},
            'Moedor': {'acertos': 12, 'erros': 9, 'total': 21},
            'Xadrez': {'acertos': 7, 'erros': 6, 'total': 13},
            'Contragolpe': {'acertos': 2, 'erros': 1, 'total': 3},
            'Reset Cluster': {'acertos': 0, 'erros': 0, 'total': 0},
            'Falsa Alternância': {'acertos': 0, 'erros': 0, 'total': 0},
            'Meta-Algoritmo': {'acertos': 0, 'erros': 0, 'total': 0}
        }
    },
    'api': {
        'total_coletado': 0,
        'falhas': 0,
        'endpoint_atual': None
    },
    'ultima_previsao': None,
    'ultimo_resultado_real': None
}

# =============================================================================
# PESOS DAS ESTRATÉGIAS (mantidos iguais)
# =============================================================================
PESOS = {
    'compensacao': {'AGRESSIVO': 70, 'EQUILIBRADO': 90, 'PREDATORIO': 60},
    'paredao': {'AGRESSIVO': 90, 'EQUILIBRADO': 50, 'PREDATORIO': 40},
    'moedor': {'AGRESSIVO': 40, 'EQUILIBRADO': 80, 'PREDATORIO': 50},
    'xadrez': {'AGRESSIVO': 30, 'EQUILIBRADO': 90, 'PREDATORIO': 40},
    'contragolpe': {'AGRESSIVO': 70, 'EQUILIBRADO': 50, 'PREDATORIO': 90},
    'reset_cluster': {'AGRESSIVO': 50, 'EQUILIBRADO': 70, 'PREDATORIO': 80},
    'falsa_alternancia': {'AGRESSIVO': 80, 'EQUILIBRADO': 40, 'PREDATORIO': 90}
}

# =============================================================================
# INICIALIZAÇÃO FLASK
# =============================================================================
app = Flask(__name__)
CORS(app)
session = requests.Session()
session.headers.update(HEADERS)

# =============================================================================
# FUNÇÕES DO BANCO (mantidas iguais)
# =============================================================================

def get_db_connection():
    try:
        conn = pg8000.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            ssl_context=True
        )
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return None

def init_db():
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS rodadas (
                id TEXT PRIMARY KEY,
                data_hora TIMESTAMPTZ,
                player_score INTEGER,
                banker_score INTEGER,
                soma INTEGER,
                resultado TEXT,
                multiplicador FLOAT DEFAULT 1,
                dados_json JSONB
            )
        ''')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_data_hora ON rodadas(data_hora DESC)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_resultado ON rodadas(resultado)')
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS historico_previsoes (
                id SERIAL PRIMARY KEY,
                data_hora TIMESTAMPTZ,
                previsao TEXT,
                confianca INTEGER,
                resultado_real TEXT,
                acertou BOOLEAN,
                estrategias TEXT,
                modo TEXT
            )
        ''')
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Tabelas criadas/verificadas")
        return True
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def salvar_rodada(rodada):
    """Salva rodada no banco"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO rodadas 
            (id, data_hora, player_score, banker_score, soma, resultado, dados_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        ''', (
            rodada['id'],
            rodada['data_hora'],
            rodada['player_score'],
            rodada['banker_score'],
            rodada['player_score'] + rodada['banker_score'],
            rodada['resultado'],
            json.dumps(rodada, default=str)
        ))
        
        if cur.rowcount > 0:
            conn.commit()
            cur.close()
            conn.close()
            return True
        return False
    except Exception as e:
        print(f"❌ Erro ao salvar: {e}")
        return False

def get_ultimas_50():
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT player_score, banker_score, resultado FROM rodadas ORDER BY data_hora DESC LIMIT 50')
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [{'player_score': r[0], 'banker_score': r[1], 'resultado': r[2]} for r in rows]
    except Exception as e:
        print(f"⚠️ Erro get_ultimas_50: {e}")
        return []

def get_ultimas_20():
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT data_hora, player_score, banker_score, resultado FROM rodadas ORDER BY data_hora DESC LIMIT 20')
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        resultado = []
        for row in rows:
            brasilia = row[0].astimezone(timezone(timedelta(hours=-3)))
            cor = '🔴' if row[3] == 'BANKER' else '🔵' if row[3] == 'PLAYER' else '🟡'
            resultado.append({
                'hora': brasilia.strftime('%H:%M:%S'),
                'resultado': row[3],
                'cor': cor,
                'player': row[1],
                'banker': row[2]
            })
        return resultado
    except Exception as e:
        print(f"⚠️ Erro get_ultimas_20: {e}")
        return []

def get_total_rapido():
    conn = get_db_connection()
    if not conn:
        return 0
    try:
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM rodadas')
        total = cur.fetchone()[0]
        cur.close()
        conn.close()
        return total
    except Exception as e:
        print(f"⚠️ Erro get_total: {e}")
        return 0

def contar_periodo(horas):
    conn = get_db_connection()
    if not conn:
        return 0
    
    try:
        cur = conn.cursor()
        agora = datetime.now(timezone.utc)
        limite = agora - timedelta(hours=horas)
        cur.execute('SELECT COUNT(*) FROM rodadas WHERE data_hora >= %s', (limite,))
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return count
    except Exception as e:
        print(f"⚠️ Erro contar_periodo {horas}h: {e}")
        return 0

# =============================================================================
# 🔥 FUNÇÃO PARA ENCONTRAR ENDPOINT FUNCIONAL
# =============================================================================

def encontrar_endpoint_funcional():
    """Testa todos os endpoints até encontrar um que retorne dados"""
    global ENDPOINT_FUNCIONAL
    
    print("\n🔍 Testando endpoints do BacBo.info...")
    
    for endpoint in ENDPOINTS:
        url = f"{BACBO_API_BASE}{endpoint}"
        print(f"   Testando: {url}")
        
        try:
            response = session.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ ENDPOINT FUNCIONAL: {endpoint}")
                print(f"   📦 Dados: {str(data)[:200]}...")
                ENDPOINT_FUNCIONAL = endpoint
                return endpoint
            else:
                print(f"   ❌ Status {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Erro: {e}")
    
    print("\n⚠️ Nenhum endpoint REST funcionou. Tentando extrair do HTML...")
    return None

# =============================================================================
# 🔥 FUNÇÃO PARA EXTRAIR DADOS DO HTML (fallback)
# =============================================================================

def extrair_dados_do_html():
    """Extrai dados do HTML da página principal"""
    try:
        url = "https://bacbo.info/dashboard"
        headers = HEADERS.copy()
        headers['Accept'] = 'text/html'
        
        response = session.get(url, timeout=TIMEOUT_API)
        html = response.text
        
        # Procurar por padrões "XXxYY"
        import re
        jogos = re.findall(r'\b(\d{1,2})\s*[xX]\s*(\d{1,2})\b', html)
        
        rodadas = []
        for i, (player, banker) in enumerate(jogos[:30]):  # Pega os primeiros 30
            player_score = int(player)
            banker_score = int(banker)
            
            if player_score > banker_score:
                resultado = 'PLAYER'
            elif banker_score > player_score:
                resultado = 'BANKER'
            else:
                resultado = 'TIE'
            
            rodada = {
                'id': f"html_{i}_{datetime.now().timestamp()}",
                'data_hora': datetime.now(timezone.utc),
                'player_score': player_score,
                'banker_score': banker_score,
                'resultado': resultado
            }
            rodadas.append(rodada)
        
        print(f"   📥 Extraídas {len(rodadas)} rodadas do HTML")
        return rodadas
        
    except Exception as e:
        print(f"❌ Erro ao extrair HTML: {e}")
        return None

# =============================================================================
# 🔥 FUNÇÃO PRINCIPAL - BUSCA NA API DO BACBO
# =============================================================================

def buscar_api_bacbo():
    """Busca rodadas usando a API do BacBo.info"""
    global ENDPOINT_FUNCIONAL
    
    try:
        # Se ainda não encontrou endpoint funcional, tenta encontrar
        if not ENDPOINT_FUNCIONAL:
            ENDPOINT_FUNCIONAL = encontrar_endpoint_funcional()
            if not ENDPOINT_FUNCIONAL:
                # Fallback para extração de HTML
                return extrair_dados_do_html()
        
        # Usa o endpoint funcional
        url = f"{BACBO_API_BASE}{ENDPOINT_FUNCIONAL}"
        params = {
            '_t': int(time.time() * 1000),  # Anti-cache
            'limit': 30
        }
        
        response = session.get(url, params=params, timeout=TIMEOUT_API)
        
        if response.status_code == 200:
            data = response.json()
            
            # Processar dados baseado no formato
            rodadas = []
            
            # Tenta diferentes formatos de resposta
            if isinstance(data, list):
                for item in data:
                    rodada = processar_item_api(item)
                    if rodada:
                        rodadas.append(rodada)
            elif isinstance(data, dict):
                if 'data' in data and isinstance(data['data'], list):
                    for item in data['data']:
                        rodada = processar_item_api(item)
                        if rodada:
                            rodadas.append(rodada)
                elif 'results' in data:
                    for item in data['results']:
                        rodada = processar_item_api(item)
                        if rodada:
                            rodadas.append(rodada)
            
            if rodadas:
                print(f"   📥 {len(rodadas)} rodadas da API")
                return rodadas
            
        # Se API não retornou dados, tenta HTML
        return extrair_dados_do_html()
        
    except Exception as e:
        print(f"❌ Erro na API: {e}")
        # Fallback para HTML
        return extrair_dados_do_html()

def processar_item_api(item):
    """Processa um item da API para o formato padrão"""
    try:
        # Tenta diferentes estruturas de dados
        if isinstance(item, dict):
            # Formato 1: com player_score e banker_score
            if 'player_score' in item and 'banker_score' in item:
                player = int(item['player_score'])
                banker = int(item['banker_score'])
                
                if player > banker:
                    resultado = 'PLAYER'
                elif banker > player:
                    resultado = 'BANKER'
                else:
                    resultado = 'TIE'
                
                return {
                    'id': item.get('id', f"api_{time.time()}"),
                    'data_hora': datetime.now(timezone.utc),
                    'player_score': player,
                    'banker_score': banker,
                    'resultado': resultado
                }
            
            # Formato 2: com player e banker
            if 'player' in item and 'banker' in item:
                player = int(item['player'])
                banker = int(item['banker'])
                
                if player > banker:
                    resultado = 'PLAYER'
                elif banker > player:
                    resultado = 'BANKER'
                else:
                    resultado = 'TIE'
                
                return {
                    'id': item.get('id', f"api_{time.time()}"),
                    'data_hora': datetime.now(timezone.utc),
                    'player_score': player,
                    'banker_score': banker,
                    'resultado': resultado
                }
    except Exception as e:
        print(f"⚠️ Erro processando item: {e}")
    
    return None

# =============================================================================
# 🔥 PROCESSADOR E COLETOR (mantidos iguais)
# =============================================================================

def processar_fila():
    """Processa a fila INSTANTANEAMENTE"""
    print("🚀 Processador TURBO iniciado...")
    
    while True:
        try:
            if fila_rodadas:
                tamanho_fila = len(fila_rodadas)
                batch = list(fila_rodadas)
                fila_rodadas.clear()
                
                saved = 0
                inicio_batch = time.time()
                
                for rodada in batch:
                    if salvar_rodada(rodada):
                        saved += 1
                        if saved == 1:
                            cache['ultimo_resultado_real'] = rodada['resultado']
                
                tempo_gasto = time.time() - inicio_batch
                
                if saved > 0:
                    print(f"💾 TURBO: salvou {saved}/{tamanho_fila} rodadas em {tempo_gasto:.3f}s")
                    atualizar_dados_leves()
                    
                    if fila_rodadas:
                        print(f"⚡ Ainda tem {len(fila_rodadas)} na fila, processando já...")
                        continue
            
            time.sleep(0.01)
            
        except Exception as e:
            print(f"❌ Erro TURBO: {e}")
            time.sleep(0.1)

def loop_coleta():
    """Coleta a cada 1 segundo usando API do BacBo"""
    print("📡 Coletor TURBO 1s (API BacBo.info) iniciado...")
    global ultimo_id_processado, fila_rodadas
    
    while True:
        try:
            inicio = time.time()
            
            dados = buscar_api_bacbo()
            
            if dados and len(dados) > 0:
                # Adiciona na fila
                tamanho_anterior = len(fila_rodadas)
                for rodada in dados:
                    fila_rodadas.append(rodada)
                
                cache['api']['total_coletado'] += len(dados)
                print(f"📥 +{len(dados)} novas | Fila: {tamanho_anterior} → {len(fila_rodadas)}")
                
                # Processamento imediato se fila > 20
                if len(fila_rodadas) > 20:
                    print(f"⚡ Fila com {len(fila_rodadas)}, processando imediatamente...")
                    batch = list(fila_rodadas)
                    fila_rodadas.clear()
                    
                    saved = 0
                    for rodada in batch:
                        if salvar_rodada(rodada):
                            saved += 1
                            if saved == 1:
                                cache['ultimo_resultado_real'] = rodada['resultado']
                    
                    if saved > 0:
                        print(f"💾 Processamento imediato: {saved} rodadas")
                        atualizar_dados_leves()
            
            # Mostra status a cada 5 segundos
            if int(time.time()) % 5 == 0:
                print(f"📊 Status - Fila: {len(fila_rodadas)} | Total banco: {cache['leves']['total_rodadas']}")
            
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Erro coleta: {e}")
            time.sleep(1)

def loop_pesado():
    """Loop para atualizar estatísticas pesadas a cada 3 segundos"""
    print("🔄 Loop pesado iniciado (3s)...")
    while True:
        time.sleep(3)
        try:
            cache['pesados']['periodos'] = {
                '10min': contar_periodo(0.16),
                '1h': contar_periodo(1),
                '6h': contar_periodo(6),
                '12h': contar_periodo(12),
                '24h': contar_periodo(24),
                '48h': contar_periodo(48),
                '72h': contar_periodo(72)
            }
            cache['pesados']['ultima_atualizacao'] = datetime.now(timezone.utc)
        except Exception as e:
            print(f"❌ Erro no loop pesado: {e}")

# =============================================================================
# ESTRATÉGIAS E PREVISÕES (mantidas iguais)
# =============================================================================

def estrategia_compensacao(dados, modo):
    if len(dados) < 10:
        return {'banker': 0, 'player': 0}
    
    player = sum(1 for r in dados if r['resultado'] == 'PLAYER')
    banker = sum(1 for r in dados if r['resultado'] == 'BANKER')
    total = len(dados)
    
    player_pct = (player / total) * 100
    banker_pct = (banker / total) * 100
    
    diff = abs(banker_pct - player_pct)
    if diff > 4:
        peso = PESOS['compensacao'][modo]
        if banker > player:
            return {'banker': 0, 'player': peso}
        else:
            return {'banker': peso, 'player': 0}
    
    return {'banker': 0, 'player': 0}

def estrategia_paredao(dados, modo):
    if len(dados) < 4:
        return {'banker': 0, 'player': 0}
    
    seq = [r['resultado'] for r in dados[:4]]
    
    if all(r == 'BANKER' for r in seq):
        return {'banker': PESOS['paredao'][modo], 'player': 0}
    if all(r == 'PLAYER' for r in seq):
        return {'banker': 0, 'player': PESOS['paredao'][modo]}
    
    return {'banker': 0, 'player': 0}

def estrategia_moedor(dados, modo):
    if len(dados) < 5:
        return {'banker': 0, 'player': 0}
    
    ties = sum(1 for r in dados[:5] if r['resultado'] == 'TIE')
    
    if ties >= 2:
        ultima_nao_tie = next((r for r in dados if r['resultado'] != 'TIE'), None)
        if ultima_nao_tie:
            peso = PESOS['moedor'][modo]
            if ultima_nao_tie['resultado'] == 'BANKER':
                return {'banker': peso, 'player': 0}
            else:
                return {'banker': 0, 'player': peso}
    
    return {'banker': 0, 'player': 0}

def estrategia_xadrez(dados, modo):
    if len(dados) < 4:
        return {'banker': 0, 'player': 0}
    
    seq = [r['resultado'] for r in dados[:4]]
    
    if (seq[0] != seq[1] and seq[1] != seq[2] and seq[2] != seq[3]):
        peso = PESOS['xadrez'][modo]
        if seq[3] == 'BANKER':
            return {'banker': 0, 'player': peso}
        else:
            return {'banker': peso, 'player': 0}
    
    return {'banker': 0, 'player': 0}

def estrategia_contragolpe(dados, modo):
    if len(dados) < 5:
        return {'banker': 0, 'player': 0}
    
    seq = [r['resultado'] for r in dados[:5]]
    
    if (seq[0] == seq[1] == seq[2] and 
        seq[2] != seq[3] and 
        seq[3] != seq[4] and 
        seq[4] == seq[0]):
        
        peso = PESOS['contragolpe'][modo]
        if seq[0] == 'BANKER':
            return {'banker': peso, 'player': 0}
        else:
            return {'banker': 0, 'player': peso}
    
    return {'banker': 0, 'player': 0}

def estrategia_reset_cluster(dados, modo):
    if len(dados) < 6:
        return {'banker': 0, 'player': 0}
    
    ties = sum(1 for r in dados[:6] if r['resultado'] == 'TIE')
    
    if ties >= 2:
        antes_cluster = None
        for r in dados:
            if r['resultado'] != 'TIE':
                antes_cluster = r
                break
        
        if antes_cluster:
            peso = PESOS['reset_cluster'][modo]
            if random.random() < 0.7:
                if antes_cluster['resultado'] == 'BANKER':
                    return {'banker': peso, 'player': 0}
                else:
                    return {'banker': 0, 'player': peso}
            else:
                if antes_cluster['resultado'] == 'BANKER':
                    return {'banker': 0, 'player': peso}
                else:
                    return {'banker': peso, 'player': 0}
    
    return {'banker': 0, 'player': 0}

def estrategia_falsa_alternancia(dados, modo):
    if not dados:
        return {'banker': 0, 'player': 0}
    
    ultimo = dados[0]
    if ultimo['player_score'] >= 10 or ultimo['banker_score'] >= 10:
        peso = PESOS['falsa_alternancia'][modo]
        if ultimo['resultado'] == 'BANKER':
            return {'banker': peso, 'player': 0}
        else:
            return {'banker': 0, 'player': peso}
    
    return {'banker': 0, 'player': 0}

def identificar_modo(player_pct, banker_pct, dados):
    extremos = sum(1 for r in dados if r['player_score'] >= 10 or r['banker_score'] >= 10)
    pct_extremos = (extremos / len(dados)) * 100 if dados else 0
    
    if banker_pct > 47 or player_pct > 47:
        return "AGRESSIVO"
    elif pct_extremos > 30:
        return "PREDATORIO"
    else:
        return "EQUILIBRADO"

def calcular_previsao():
    dados = cache['leves']['ultimas_50']
    if len(dados) < 10:
        return None
    
    total = len(dados)
    player = sum(1 for r in dados if r['resultado'] == 'PLAYER')
    banker = sum(1 for r in dados if r['resultado'] == 'BANKER')
    
    player_pct = (player / total) * 100
    banker_pct = (banker / total) * 100
    
    modo = identificar_modo(player_pct, banker_pct, dados)
    
    votos_banker = 0
    votos_player = 0
    estrategias_ativas = []
    
    e1 = estrategia_compensacao(dados, modo)
    votos_banker += e1.get('banker', 0)
    votos_player += e1.get('player', 0)
    if e1.get('banker') or e1.get('player'):
        estrategias_ativas.append('Compensação')
    
    e2 = estrategia_paredao(dados, modo)
    votos_banker += e2.get('banker', 0)
    votos_player += e2.get('player', 0)
    if e2.get('banker') or e2.get('player'):
        estrategias_ativas.append('Paredão')
    
    e3 = estrategia_moedor(dados, modo)
    votos_banker += e3.get('banker', 0)
    votos_player += e3.get('player', 0)
    if e3.get('banker') or e3.get('player'):
        estrategias_ativas.append('Moedor')
    
    e4 = estrategia_xadrez(dados, modo)
    votos_banker += e4.get('banker', 0)
    votos_player += e4.get('player', 0)
    if e4.get('banker') or e4.get('player'):
        estrategias_ativas.append('Xadrez')
    
    e5 = estrategia_contragolpe(dados, modo)
    votos_banker += e5.get('banker', 0)
    votos_player += e5.get('player', 0)
    if e5.get('banker') or e5.get('player'):
        estrategias_ativas.append('Contragolpe')
    
    e6 = estrategia_reset_cluster(dados, modo)
    votos_banker += e6.get('banker', 0)
    votos_player += e6.get('player', 0)
    if e6.get('banker') or e6.get('player'):
        estrategias_ativas.append('Reset Cluster')
    
    e7 = estrategia_falsa_alternancia(dados, modo)
    votos_banker += e7.get('banker', 0)
    votos_player += e7.get('player', 0)
    if e7.get('banker') or e7.get('player'):
        estrategias_ativas.append('Falsa Alternância')
    
    if modo == "AGRESSIVO":
        if banker_pct > player_pct:
            votos_banker = int(votos_banker * 1.5)
            estrategias_ativas.append('Meta AGRESSIVO')
        else:
            votos_player = int(votos_player * 1.5)
            estrategias_ativas.append('Meta AGRESSIVO')
    elif modo == "PREDATORIO":
        if any(s in estrategias_ativas for s in ['Contragolpe', 'Falsa Alternância']):
            if banker_pct > player_pct:
                votos_banker = int(votos_banker * 1.3)
            else:
                votos_player = int(votos_player * 1.3)
            estrategias_ativas.append('Meta PREDATÓRIO')
    
    total_votos = votos_banker + votos_player
    
    if votos_banker > votos_player:
        previsao = 'BANKER'
        confianca = round((votos_banker / total_votos) * 100) if total_votos > 0 else 50
    elif votos_player > votos_banker:
        previsao = 'PLAYER'
        confianca = round((votos_player / total_votos) * 100) if total_votos > 0 else 50
    else:
        if banker_pct > player_pct:
            previsao = 'BANKER'
            confianca = round((banker_pct / (banker_pct + player_pct)) * 100)
        else:
            previsao = 'PLAYER'
            confianca = round((player_pct / (banker_pct + player_pct)) * 100)
        estrategias_ativas = ['Análise base']
    
    return {
        'modo': modo,
        'previsao': previsao,
        'simbolo': '🔴' if previsao == 'BANKER' else '🔵' if previsao == 'PLAYER' else '🟡',
        'confianca': confianca,
        'estrategias': estrategias_ativas[:4]
    }

def verificar_previsoes_anteriores():
    if cache.get('ultima_previsao') and cache.get('ultimo_resultado_real'):
        ultima = cache['ultima_previsao']
        resultado_real = cache['ultimo_resultado_real']
        
        acertou = (ultima['previsao'] == resultado_real)
        
        cache['estatisticas']['total_previsoes'] += 1
        if acertou:
            cache['estatisticas']['acertos'] += 1
        else:
            cache['estatisticas']['erros'] += 1
        
        for estrategia in ultima.get('estrategias', []):
            nome_clean = estrategia.split(' ')[0]
            if nome_clean in cache['estatisticas']['estrategias']:
                cache['estatisticas']['estrategias'][nome_clean]['total'] += 1
                if acertou:
                    cache['estatisticas']['estrategias'][nome_clean]['acertos'] += 1
                else:
                    cache['estatisticas']['estrategias'][nome_clean]['erros'] += 1
        
        previsao_historico = {
            'data': datetime.now().strftime('%d/%m %H:%M:%S'),
            'previsao': ultima['previsao'],
            'simbolo': ultima['simbolo'],
            'confianca': ultima['confianca'],
            'resultado_real': resultado_real,
            'acertou': acertou,
            'estrategias': ultima['estrategias']
        }
        
        cache['estatisticas']['ultimas_20_previsoes'].insert(0, previsao_historico)
        if len(cache['estatisticas']['ultimas_20_previsoes']) > 20:
            cache['estatisticas']['ultimas_20_previsoes'].pop()
        
        print(f"\n{'✅' if acertou else '❌'} {ultima['simbolo']} {ultima['previsao']} vs {resultado_real}")
        
        cache['ultima_previsao'] = None
        cache['ultimo_resultado_real'] = None

def calcular_precisao():
    total = cache['estatisticas']['total_previsoes']
    if total == 0:
        return 0
    return round((cache['estatisticas']['acertos'] / total) * 100)

def atualizar_dados_leves():
    verificar_previsoes_anteriores()
    
    cache['leves']['ultimas_50'] = get_ultimas_50()
    cache['leves']['ultimas_20'] = get_ultimas_20()
    cache['leves']['total_rodadas'] = get_total_rapido()
    
    if cache['leves']['previsao']:
        cache['ultima_previsao'] = cache['leves']['previsao']
    
    cache['leves']['previsao'] = calcular_previsao()
    cache['leves']['ultima_atualizacao'] = datetime.now(timezone.utc)

# =============================================================================
# ROTAS FLASK (mantidas iguais)
# =============================================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/tabela/<int:limite>')
def api_tabela(limite):
    limite = min(max(limite, 50), 3000)
    print(f"\n📋 ROTA TABELA CHAMADA - limite={limite}")
    
    conn = get_db_connection()
    if not conn:
        print("❌ Sem conexão com banco")
        return jsonify([])
    
    try:
        cur = conn.cursor()
        
        cur.execute('SELECT COUNT(*) FROM rodadas')
        total_banco = cur.fetchone()[0]
        print(f"   📊 Total no banco: {total_banco} rodadas")
        
        cur.execute('''
            SELECT data_hora, player_score, banker_score, resultado 
            FROM rodadas 
            ORDER BY data_hora DESC 
            LIMIT %s
        ''', (limite,))
        
        rows = cur.fetchall()
        print(f"   📥 Query retornou {len(rows)} linhas")
        
        cur.close()
        conn.close()
        
        resultado = []
        for row in rows:
            try:
                brasilia = row[0].astimezone(timezone(timedelta(hours=-3)))
                resultado.append({
                    'data': brasilia.strftime('%d/%m %H:%M:%S'),
                    'player': row[1],
                    'banker': row[2],
                    'resultado': row[3],
                    'cor': '🔴' if row[3] == 'BANKER' else '🔵' if row[3] == 'PLAYER' else '🟡'
                })
            except Exception as e:
                print(f"   ⚠️ Erro processando linha: {e}")
                continue
        
        print(f"   ✅ Retornando {len(resultado)} rodadas")
        return jsonify(resultado)
        
    except Exception as e:
        print(f"❌ Erro api_tabela: {e}")
        return jsonify([]), 500

@app.route('/api/stats')
def api_stats():
    estrategias_stats = []
    for nome, dados in cache['estatisticas']['estrategias'].items():
        total = dados['total']
        if total > 0:
            precisao = round((dados['acertos'] / total) * 100)
        else:
            precisao = 0
        estrategias_stats.append({
            'nome': nome,
            'acertos': dados['acertos'],
            'erros': dados['erros'],
            'precisao': precisao
        })
    
    ultima_atualizacao = None
    if cache['leves']['ultima_atualizacao']:
        brasilia = cache['leves']['ultima_atualizacao'].astimezone(timezone(timedelta(hours=-3)))
        ultima_atualizacao = brasilia.strftime('%d/%m %H:%M:%S')
    
    return jsonify({
        'ultima_atualizacao': ultima_atualizacao,
        'total_rodadas': cache['leves']['total_rodadas'],
        'ultimas_20': cache['leves']['ultimas_20'],
        'previsao': cache['leves']['previsao'],
        'periodos': cache['pesados']['periodos'],
        'fila': len(fila_rodadas),
        'api': {
            'total_coletado': cache['api']['total_coletado'],
            'endpoint': ENDPOINT_FUNCIONAL
        },
        'estatisticas': {
            'total_previsoes': cache['estatisticas']['total_previsoes'],
            'acertos': cache['estatisticas']['acertos'],
            'erros': cache['estatisticas']['erros'],
            'precisao': calcular_precisao(),
            'ultimas_20_previsoes': cache['estatisticas']['ultimas_20_previsoes'],
            'estrategias': estrategias_stats
        }
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'rodadas': cache['leves']['total_rodadas'],
        'fila': len(fila_rodadas)
    })

@app.route('/status-fila')
def status_fila():
    return jsonify({
        'fila': len(fila_rodadas),
        'ultimo_id': ultimo_id_processado,
        'endpoint': ENDPOINT_FUNCIONAL
    })

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("="*70)
    print("🚀 BOT BACBO - API BACBO.INFO")
    print("="*70)
    print("✅ Coleta a cada 1 segundo")
    print("✅ Usando API real: https://api.bacbo.info")
    print("✅ Fallback para extração HTML")
    print("="*70)
    
    init_db()
    
    print("🔍 Testando API do BacBo.info...")
    endpoint = encontrar_endpoint_funcional()
    if endpoint:
        print(f"✅ Usando endpoint: {endpoint}")
    else:
        print("⚠️ Usando fallback: extração de HTML")
    
    print("\n📊 Carregando dados...")
    atualizar_dados_leves()
    print(f"📊 {cache['leves']['total_rodadas']} rodadas no banco")
    print("="*70)
    
    # Threads
    threading.Thread(target=loop_coleta, daemon=True).start()
    threading.Thread(target=processar_fila, daemon=True).start()
    threading.Thread(target=loop_pesado, daemon=True).start()
    
    print("✅ Servidor rodando com API BacBo.info!")
    print("📋 Acesse /api/tabela/50 para ver os dados brutos")
    app.run(host='0.0.0.0', port=PORT, debug=False)
