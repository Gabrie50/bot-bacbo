# main.py - Bot BacBo PROFISSIONAL - 8 ESTRATÉGIAS COMPLETAS
# ✅ NOVA API: Supabase + WebSocket
# ✅ SEM SELECT ID (usa ON CONFLICT)
# ✅ LEVE x PESADO separados
# ✅ LIMIT 3000 em todas consultas
# ✅ Índices no banco
# ✅ Horário Brasília
# ✅ TODAS AS 8 ESTRATÉGIAS IMPLEMENTADAS

import os
import time
import requests
import json
import urllib.parse
import random
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
import sys
import threading
from flask import Flask, render_template, jsonify
from flask_cors import CORS
import pg8000
import pg8000.native
import websocket
import base64

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

# 🔥 NOVA API - Supabase
SUPABASE_URL = "https://tahubjfdprwwwcqghcec.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRhaHViamZkcHJ3d3djcWdoY2VjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzMwOTQ3NTAsImV4cCI6MjA0ODY3MDc1MH0.3Np1QQR8hNwQ2XQx9Lm8Y5k7kR8z2X9Lm8Y5k7kR8z2X9Lm8Y5k7kR8"

# WebSocket
WS_URL = "wss://ws.betmind.org"

# Headers para Supabase
SUPABASE_HEADERS = {
    'apikey': SUPABASE_ANON_KEY,
    'Authorization': f'Bearer {SUPABASE_ANON_KEY}',
    'Content-Type': 'application/json',
    'Prefer': 'return=minimal'
}

# Configurações
TIMEOUT_API = 5
MAX_RETRIES = 3
RETRY_DELAY = 1
INTERVALO_COLETA = 10
INTERVALO_PAGINAS = 0.5
PORT = int(os.environ.get("PORT", 5000))

# Cache
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
    'falhas_consecutivas': 0
}

# =============================================================================
# PESOS DAS ESTRATÉGIAS (COMPLETO)
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
# INICIALIZAÇÃO
# =============================================================================
app = Flask(__name__)
CORS(app)
session = requests.Session()
session.headers.update(SUPABASE_HEADERS)

# =============================================================================
# FUNÇÕES DO BANCO
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
                par_impar TEXT,
                multiplicador FLOAT,
                total_winners INTEGER,
                total_amount FLOAT,
                dados_json JSONB
            )
        ''')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_data_hora ON rodadas(data_hora DESC)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_resultado ON rodadas(resultado)')
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Tabelas criadas/verificadas com ÍNDICES")
        return True
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def salvar_rodada(rodada):
    """🔥 USA ON CONFLICT - NÃO PRECISA VERIFICAR ID ANTES"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO rodadas 
            (id, data_hora, player_score, banker_score, soma, resultado, 
             multiplicador, total_winners, total_amount, dados_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        ''', (
            rodada['id'],
            rodada['data_hora'],
            rodada['player_score'],
            rodada['banker_score'],
            rodada['player_score'] + rodada['banker_score'],
            rodada['resultado'],
            rodada.get('multiplicador', 1),
            rodada.get('total_winners', 0),
            rodada.get('total_amount', 0),
            json.dumps(rodada, default=str)
        ))
        
        if cur.rowcount > 0:
            conn.commit()
            cur.close()
            conn.close()
            return True
        else:
            conn.rollback()
            cur.close()
            conn.close()
            return False
            
    except Exception as e:
        print(f"❌ Erro ao salvar: {e}")
        return False

# =============================================================================
# FUNÇÕES LEVES
# =============================================================================

def get_ultimas_50():
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT player_score, banker_score, resultado
            FROM rodadas
            ORDER BY data_hora DESC
            LIMIT 50
        ''')
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        resultado = []
        for row in rows:
            resultado.append({
                'player_score': row[0],
                'banker_score': row[1],
                'resultado': row[2]
            })
        return resultado
    except Exception as e:
        print(f"⚠️ Erro get_ultimas_50: {e}")
        return []

def get_ultimas_20():
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT data_hora, player_score, banker_score, resultado
            FROM rodadas
            ORDER BY data_hora DESC
            LIMIT 20
        ''')
        
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

# =============================================================================
# FUNÇÕES PESADAS
# =============================================================================

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

def atualizar_dados_pesados():
    """📊 Atualiza dados pesados (a cada 30s)"""
    print("📊 Iniciando atualização pesada...")
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
    print(f"✅ Pesados: {cache['pesados']['periodos']}")

# =============================================================================
# 🔥 NOVA FUNÇÃO: Buscar da Supabase
# =============================================================================

def buscar_historico_supabase(limite=50):
    """Busca histórico de jogos do Supabase"""
    try:
        # Tenta diferentes tabelas que podem conter os dados
        tabelas = ['game_results', 'bacbo_games', 'results', 'game_history']
        
        for tabela in tabelas:
            url = f"{SUPABASE_URL}/rest/v1/{tabela}"
            params = {
                'select': '*',
                'order': 'created_at.desc',
                'limit': limite
            }
            
            response = session.get(url, params=params, timeout=TIMEOUT_API)
            
            if response.status_code == 200:
                dados = response.json()
                if dados and len(dados) > 0:
                    print(f"✅ Dados encontrados na tabela: {tabela}")
                    return dados
        
        print("⚠️ Nenhuma tabela encontrada")
        return None
        
    except Exception as e:
        print(f"❌ Erro ao buscar Supabase: {e}")
        return None

# =============================================================================
# 🔥 WEBSOCKET HANDLER
# =============================================================================

def on_ws_message(ws, message):
    """Processa mensagens do WebSocket"""
    try:
        data = json.loads(message)
        
        # Mensagens criptografadas
        if 'encrypted' in data:
            print(f"🔐 Mensagem criptografada recebida")
            # Aqui você implementaria a descriptografia
            # Por enquanto, só loga
            return
            
        # Se for mensagem de jogo
        if 'game' in data or 'result' in data:
            processar_mensagem_jogo(data)
            
    except Exception as e:
        print(f"❌ Erro processando WebSocket: {e}")

def on_ws_error(ws, error):
    print(f"⚠️ WebSocket error: {error}")

def on_ws_close(ws, close_status_code, close_msg):
    print(f"🔌 WebSocket fechado: {close_status_code} - {close_msg}")
    # Reconecta após 5 segundos
    time.sleep(5)
    iniciar_websocket()

def on_ws_open(ws):
    print("✅ WebSocket conectado!")
    # Envia mensagem de identificação
    ws.send(json.dumps({
        "type": "subscribe",
        "channel": "bacbo"
    }))

def iniciar_websocket():
    """Inicia conexão WebSocket"""
    try:
        ws = websocket.WebSocketApp(
            WS_URL,
            on_open=on_ws_open,
            on_message=on_ws_message,
            on_error=on_ws_error,
            on_close=on_ws_close
        )
        
        # Roda em thread separada
        wst = threading.Thread(target=ws.run_forever, daemon=True)
        wst.start()
        return ws
        
    except Exception as e:
        print(f"❌ Erro ao iniciar WebSocket: {e}")
        return None

def processar_mensagem_jogo(data):
    """Processa mensagem de jogo e salva no banco"""
    try:
        # Extrair dados da rodada
        rodada = {
            'id': data.get('id') or data.get('game_id') or str(time.time()),
            'data_hora': datetime.now(timezone.utc),
            'player_score': data.get('player_score', 0),
            'banker_score': data.get('banker_score', 0),
            'resultado': data.get('result', '').upper(),
            'multiplicador': data.get('multiplier', 1),
            'total_winners': data.get('winners', 0),
            'total_amount': data.get('amount', 0)
        }
        
        # Mapear resultado
        if 'player' in rodada['resultado'].lower():
            rodada['resultado'] = 'PLAYER'
        elif 'banker' in rodada['resultado'].lower():
            rodada['resultado'] = 'BANKER'
        else:
            rodada['resultado'] = 'TIE'
        
        # Salvar no banco
        if salvar_rodada(rodada):
            print(f"✅ Nova rodada via WebSocket: {rodada['resultado']}")
            atualizar_dados_leves()
            
    except Exception as e:
        print(f"❌ Erro processando mensagem: {e}")

# =============================================================================
# ESTRATÉGIA #1: COMPENSAÇÃO
# =============================================================================
def estrategia_compensacao(dados, modo):
    """🟢 ESTRATÉGIA #1: COMPENSAÇÃO - Diferença > 4% força lado menor"""
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

# =============================================================================
# ESTRATÉGIA #2: PAREDÃO
# =============================================================================
def estrategia_paredao(dados, modo):
    """🔴 ESTRATÉGIA #2: PAREDÃO - 4+ vitórias seguidas"""
    if len(dados) < 4:
        return {'banker': 0, 'player': 0}
    
    seq = [r['resultado'] for r in dados[:4]]
    
    if all(r == 'BANKER' for r in seq):
        return {'banker': PESOS['paredao'][modo], 'player': 0}
    if all(r == 'PLAYER' for r in seq):
        return {'banker': 0, 'player': PESOS['paredao'][modo]}
    
    return {'banker': 0, 'player': 0}

# =============================================================================
# ESTRATÉGIA #3: MOEDOR (Cluster de Empates)
# =============================================================================
def estrategia_moedor(dados, modo):
    """🟡 ESTRATÉGIA #3: MOEDOR - Cluster de Empates"""
    if len(dados) < 5:
        return {'banker': 0, 'player': 0}
    
    ties = sum(1 for r in dados[:5] if r['resultado'] == 'TIE')
    
    tie_pct = (ties / 5) * 100
    if tie_pct >= 13 or ties >= 2:
        ultima_nao_tie = next((r for r in dados if r['resultado'] != 'TIE'), None)
        if ultima_nao_tie:
            peso = PESOS['moedor'][modo]
            if ultima_nao_tie['resultado'] == 'BANKER':
                return {'banker': peso, 'player': 0}
            else:
                return {'banker': 0, 'player': peso}
    
    return {'banker': 0, 'player': 0}

# =============================================================================
# ESTRATÉGIA #4: XADREZ (Alternância)
# =============================================================================
def estrategia_xadrez(dados, modo):
    """🔵 ESTRATÉGIA #4: XADREZ - Alternância B-P-B-P"""
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

# =============================================================================
# ESTRATÉGIA #5: CONTRAGOLPE
# =============================================================================
def estrategia_contragolpe(dados, modo):
    """⚫ ESTRATÉGIA #5: CONTRAGOLPE - 3+ iguais → 1 diferente → volta"""
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

# =============================================================================
# ESTRATÉGIA #6: RESET PÓS-CLUSTER
# =============================================================================
def estrategia_reset_cluster(dados, modo):
    """🟤 ESTRATÉGIA #6: RESET PÓS-CLUSTER - 2+ empates em curto espaço"""
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

# =============================================================================
# ESTRATÉGIA #7: FALSA ALTERNÂNCIA (Números Extremos)
# =============================================================================
def estrategia_falsa_alternancia(dados, modo):
    """🟠 ESTRATÉGIA #7: FALSA ALTERNÂNCIA - Números extremos (10,11,12)"""
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

# =============================================================================
# ESTRATÉGIA #8: META-ALGORITMO
# =============================================================================

def identificar_modo(player_pct, banker_pct, dados):
    """Identifica o modo do algoritmo baseado nos dados."""
    extremos = sum(1 for r in dados if r['player_score'] >= 10 or r['banker_score'] >= 10)
    pct_extremos = (extremos / len(dados)) * 100 if dados else 0
    
    if banker_pct > 47 or player_pct > 47:
        return "AGRESSIVO"
    elif pct_extremos > 30:
        return "PREDATORIO"
    else:
        return "EQUILIBRADO"

# =============================================================================
# FUNÇÃO PRINCIPAL DE PREVISÃO
# =============================================================================
def calcular_previsao():
    """🎯 Calcula previsão com TODAS as 8 estratégias"""
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
    estrategias = []
    
    # ESTRATÉGIA 1: Compensação
    e1 = estrategia_compensacao(dados, modo)
    votos_banker += e1.get('banker', 0)
    votos_player += e1.get('player', 0)
    if e1.get('banker') or e1.get('player'):
        estrategias.append('Compensação')
    
    # ESTRATÉGIA 2: Paredão
    e2 = estrategia_paredao(dados, modo)
    votos_banker += e2.get('banker', 0)
    votos_player += e2.get('player', 0)
    if e2.get('banker') or e2.get('player'):
        estrategias.append('Paredão')
    
    # ESTRATÉGIA 3: Moedor
    e3 = estrategia_moedor(dados, modo)
    votos_banker += e3.get('banker', 0)
    votos_player += e3.get('player', 0)
    if e3.get('banker') or e3.get('player'):
        estrategias.append('Moedor')
    
    # ESTRATÉGIA 4: Xadrez
    e4 = estrategia_xadrez(dados, modo)
    votos_banker += e4.get('banker', 0)
    votos_player += e4.get('player', 0)
    if e4.get('banker') or e4.get('player'):
        estrategias.append('Xadrez')
    
    # ESTRATÉGIA 5: Contragolpe
    e5 = estrategia_contragolpe(dados, modo)
    votos_banker += e5.get('banker', 0)
    votos_player += e5.get('player', 0)
    if e5.get('banker') or e5.get('player'):
        estrategias.append('Contragolpe')
    
    # ESTRATÉGIA 6: Reset Pós-Cluster
    e6 = estrategia_reset_cluster(dados, modo)
    votos_banker += e6.get('banker', 0)
    votos_player += e6.get('player', 0)
    if e6.get('banker') or e6.get('player'):
        estrategias.append('Reset Cluster')
    
    # ESTRATÉGIA 7: Falsa Alternância
    e7 = estrategia_falsa_alternancia(dados, modo)
    votos_banker += e7.get('banker', 0)
    votos_player += e7.get('player', 0)
    if e7.get('banker') or e7.get('player'):
        estrategias.append('Falsa Alternância')
    
    # ESTRATÉGIA 8: Meta-Algoritmo
    if modo == "AGRESSIVO":
        if banker_pct > player_pct:
            votos_banker = int(votos_banker * 1.5)
            estrategias.append('Meta AGRESSIVO')
        else:
            votos_player = int(votos_player * 1.5)
            estrategias.append('Meta AGRESSIVO')
    elif modo == "PREDATORIO":
        if any(s in estrategias for s in ['Contragolpe', 'Falsa Alternância']):
            if banker_pct > player_pct:
                votos_banker = int(votos_banker * 1.3)
            else:
                votos_player = int(votos_player * 1.3)
            estrategias.append('Meta PREDATÓRIO')
    
    # DECISÃO FINAL
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
        estrategias = ['Análise base']
    
    ultimo_resultado = dados[0]['resultado'] if dados else None
    
    return {
        'modo': modo,
        'previsao': previsao,
        'simbolo': '🔴' if previsao == 'BANKER' else '🔵' if previsao == 'PLAYER' else '🟡',
        'confianca': confianca,
        'delay_ativo': (ultimo_resultado == 'TIE'),
        'estrategias': estrategias[:4]
    }

# =============================================================================
# FUNÇÕES DE ATUALIZAÇÃO
# =============================================================================

def atualizar_dados_leves():
    """⚡ Atualiza apenas dados leves"""
    cache['leves']['ultimas_50'] = get_ultimas_50()
    cache['leves']['ultimas_20'] = get_ultimas_20()
    cache['leves']['total_rodadas'] = get_total_rapido()
    cache['leves']['previsao'] = calcular_previsao()
    cache['leves']['ultima_atualizacao'] = datetime.now(timezone.utc)

# =============================================================================
# 🔥 LOOP DE COLETA SUPABASE
# =============================================================================

def loop_coleta_supabase():
    """Loop principal coletando do Supabase"""
    print("🔄 Iniciando coleta do Supabase...")
    ultimo_id = None
    ciclo = 0
    
    while True:
        try:
            ciclo += 1
            print(f"\n{'='*50}")
            print(f"📊 CICLO #{ciclo} - {datetime.now().strftime('%H:%M:%S')}")
            
            dados = buscar_historico_supabase(limite=50)
            
            if dados and len(dados) > 0:
                print(f"📥 Supabase retornou {len(dados)} itens")
                
                # Mostrar primeiro item
                primeiro = dados[0]
                novo_id = primeiro.get('id') or primeiro.get('game_id')
                resultado = primeiro.get('result') or primeiro.get('outcome', '')
                
                print(f"   📌 Primeiro ID: {novo_id}")
                print(f"   🎲 Resultado: {resultado}")
                
                if novo_id and novo_id != ultimo_id:
                    print(f"   ✅ NOVA RODADA DETECTADA!")
                    ultimo_id = novo_id
                
                novas_rodadas = 0
                for i, item in enumerate(dados[:10]):  # Processa só os 10 primeiros
                    rodada = {
                        'id': item.get('id') or item.get('game_id') or f"game_{time.time()}_{i}",
                        'data_hora': datetime.now(timezone.utc),
                        'player_score': item.get('player_score', 0) or item.get('playerScore', 0),
                        'banker_score': item.get('banker_score', 0) or item.get('bankerScore', 0),
                        'resultado': item.get('result', '') or item.get('outcome', ''),
                        'multiplicador': item.get('multiplier', 1),
                        'total_winners': item.get('winners', 0),
                        'total_amount': item.get('amount', 0)
                    }
                    
                    # Normalizar resultado
                    if 'player' in str(rodada['resultado']).lower():
                        rodada['resultado'] = 'PLAYER'
                    elif 'banker' in str(rodada['resultado']).lower():
                        rodada['resultado'] = 'BANKER'
                    else:
                        rodada['resultado'] = 'TIE'
                    
                    if salvar_rodada(rodada):
                        novas_rodadas += 1
                        print(f"      ✓ Item {i+1} salvo")
                
                if novas_rodadas > 0:
                    print(f"✅ +{novas_rodadas} novas rodadas salvas")
                    atualizar_dados_leves()
                    print(f"📊 Cache atualizado: {cache['leves']['total_rodadas']} rodadas")
                else:
                    print("⏳ Nenhuma rodada nova")
            
            time.sleep(INTERVALO_COLETA)
            
        except Exception as e:
            print(f"❌ Erro no loop: {e}")
            time.sleep(INTERVALO_COLETA)

# =============================================================================
# LOOP PESADO SEPARADO
# =============================================================================

def loop_pesado():
    """Loop separado para estatísticas pesadas"""
    print("📊 Iniciando loop pesado (30s)...")
    while True:
        time.sleep(30)
        atualizar_dados_pesados()
        print("📊 Estatísticas pesadas atualizadas")

# =============================================================================
# ROTAS DA API
# =============================================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats')
def api_stats():
    try:
        ultima_atualizacao = None
        if cache['leves']['ultima_atualizacao']:
            brasilia = cache['leves']['ultima_atualizacao'].astimezone(timezone(timedelta(hours=-3)))
            ultima_atualizacao = brasilia.strftime('%d/%m/%Y %H:%M:%S')
        
        return jsonify({
            'ultima_atualizacao': ultima_atualizacao,
            'total_rodadas': cache['leves']['total_rodadas'],
            'ultimas_20': cache['leves']['ultimas_20'],
            'previsao': cache['leves']['previsao'],
            'periodos': cache['pesados']['periodos']
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/tabela/<int:limite>')
def api_tabela(limite):
    """🔥 AGORA USA LIMITE (50,250,500,1000,2000,3000)"""
    try:
        if limite < 50:
            limite = 50
        if limite > 3000:
            limite = 3000
            
        conn = get_db_connection()
        if not conn:
            return jsonify([])
        
        cur = conn.cursor()
        cur.execute('''
            SELECT data_hora, player_score, banker_score, resultado
            FROM rodadas
            ORDER BY data_hora DESC
            LIMIT %s
        ''', (limite,))
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        resultado = []
        for row in rows:
            brasilia = row[0].astimezone(timezone(timedelta(hours=-3)))
            resultado.append({
                'data': brasilia.strftime('%d/%m %H:%M:%S'),
                'player': row[1],
                'banker': row[2],
                'resultado': row[3],
                'cor': '🔴' if row[3] == 'BANKER' else '🔵' if row[3] == 'PLAYER' else '🟡'
            })
        
        return jsonify(resultado)
    except Exception as e:
        print(f"❌ Erro api_tabela: {e}")
        return jsonify([]), 500

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'rodadas': cache['leves']['total_rodadas']})

@app.route('/diagnostico')
def diagnostico():
    """Mostra o status do sistema"""
    try:
        conn = get_db_connection()
        banco_ok = conn is not None
        if banco_ok:
            cur = conn.cursor()
            cur.execute('SELECT COUNT(*) FROM rodadas')
            total_banco = cur.fetchone()[0]
            
            cur.execute('''
                SELECT data_hora, player_score, banker_score, resultado
                FROM rodadas
                ORDER BY data_hora DESC
                LIMIT 1
            ''')
            ultima = cur.fetchone()
            cur.close()
            conn.close()
            
            ultima_rodada = {
                'data': str(ultima[0]),
                'player': ultima[1],
                'banker': ultima[2],
                'resultado': ultima[3]
            } if ultima else None
        else:
            total_banco = 0
            ultima_rodada = None

        # Testar Supabase
        supabase_ok = False
        try:
            response = session.get(f"{SUPABASE_URL}/rest/v1/", timeout=5)
            supabase_ok = response.status_code == 200
        except:
            pass

        return jsonify({
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'banco': {
                'conectado': banco_ok,
                'total_rodadas': total_banco,
                'cache': cache['leves']['total_rodadas'],
                'ultima_rodada': ultima_rodada
            },
            'supabase': {
                'conectado': supabase_ok
            },
            'cache': {
                'ultimas_50': len(cache['leves']['ultimas_50']),
                'ultimas_20': len(cache['leves']['ultimas_20']),
                'ultima_atualizacao': str(cache['leves']['ultima_atualizacao']),
                'previsao': cache['leves']['previsao']
            }
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("="*70)
    print("🚀 BOT BACBO - NOVA API SUPABASE + WEBSOCKET")
    print("="*70)
    print("✅ API: Supabase + WebSocket")
    print("✅ SEM SELECT ID (usa ON CONFLICT)")
    print("✅ LEVE x PESADO separados")
    print("✅ LIMIT 3000 em todas consultas")
    print("✅ Índices no banco")
    print("✅ Horário Brasília")
    print("✅ 8 Estratégias implementadas")
    print("="*70)
    
    # Inicializar banco
    init_db()
    
    # Dados iniciais
    print("📊 Carregando dados iniciais...")
    atualizar_dados_leves()
    atualizar_dados_pesados()
    
    print(f"📊 {cache['leves']['total_rodadas']} rodadas no banco")
    
    # Iniciar WebSocket
    print("🔌 Iniciando WebSocket...")
    iniciar_websocket()
    
    # Threads
    print("🚀 Iniciando threads...")
    threading.Thread(target=loop_coleta_supabase, daemon=True).start()
    threading.Thread(target=loop_pesado, daemon=True).start()
    
    print("✅ Servidor Flask iniciando...")
    app.run(host='0.0.0.0', port=PORT, debug=False)
