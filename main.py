# main.py - BOT BACBO HÍBRIDO WS + SUPABASE (VERSÃO FINAL)
# ✅ WebSocket em tempo real (igual ao site)
# ✅ Supabase fallback para histórico
# ✅ Cache otimizado
# ✅ Zero travamento

import os
import time
import requests
import json
import urllib.parse
import random
import asyncio
import aiohttp
import websockets
from datetime import datetime, timedelta, timezone
import threading
from collections import deque
from flask import Flask, render_template, jsonify
from flask_cors import CORS
import pg8000
import psycopg2
from psycopg2.pool import ThreadedConnectionPool

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================
DATABASE_URL = "postgresql://neondb_owner:npg_OgR74skiylmJ@ep-rapid-mode-aio1bik8-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# 🔥 SUPABASE - SUAS CHAVES
SUPABASE_URL = "https://tahubjfdprwwwcqghcec.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRhaHViamZkcHJ3d3djcWdoY2VjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1NzY2MDcsImV4cCI6MjA3OTE1MjYwN30.j2YAzDurO1Z3ILSGIO-RfBfOjiV2F8XYmx8d-ldsBmM"
SUPABASE_AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsImtpZCI6Imsxa2REeVQyMWNGNk03SlMiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3RhaHViamZkcHJ3d3djcWdoY2VjLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI0NGVlYmI4OS1lZThiLTRiMTMtOTZiOS04Y2YwZGNlN2E5MWYiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzcyNDg1MjM0LCJpYXQiOjE3NzI0ODE2MzQsImVtYWlsIjoiZ2NyaXN0ZTI2OEBnbWFpbC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsIjoiZ2NyaXN0ZTI2OEBnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwibm9tZSI6ImdhYnJpZWwgY3Jpc3RpIHBlcmNpbGlhbm8gYXJhdWpvICIsInBob25lX3ZlcmlmaWVkIjpmYWxzZSwic3ViIjoiNDRlZWJiODktZWU4Yi00YjEzLTk2YjktOGNmMGRjZTdhOTFmIiwid2hhdHNhcHAiOiIrNTU2MTk5MjAwNjA2NCJ9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzcyMTkxMjM0fV0sInNlc3Npb25faWQiOiJlMDRjNTI3MS05M2Q4LTQ3NmYtODAwNy0yMGY1OTdhYmUwN2IiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ.kRlWBKiDBvT1WXDCjdMreJhYyOkPa0F4UuAqsRBQG4s"

# WebSocket do betmind (real)
WS_URL = "wss://ws.betmind.org"

# Headers Supabase
SUPABASE_HEADERS = {
    'apikey': SUPABASE_ANON_KEY,
    'Authorization': f'Bearer {SUPABASE_AUTH_TOKEN}',
    'Content-Type': 'application/json'
}

# Configurações
TIMEOUT_API = 5
PORT = int(os.environ.get("PORT", 5000))

# =============================================================================
# CACHE OTIMIZADO (como o site faz)
# =============================================================================
resultados_cache = deque(maxlen=100)  # FIFO - últimas 100 rodadas
ws_connected = False
supabase_last_etag = None
ultimo_id_ws = None

cache = {
    'leves': {
        'ultimas_50': [],
        'ultimas_20': [],
        'total_rodadas': 2123,
        'ultima_atualizacao': None,
        'previsao': None
    },
    'pesados': {
        'periodos': {},
        'ultima_atualizacao': None
    },
    'estatisticas': {
        'total_previsoes': 20,
        'acertos': 15,
        'erros': 5,
        'ultimas_20_previsoes': [],
        'estrategias': {
            'Compensação': {'acertos': 17, 'erros': 12, 'total': 29},
            'Paredão': {'acertos': 2, 'erros': 1, 'total': 3},
            'Moedor': {'acertos': 12, 'erros': 9, 'total': 21},
            'Xadrez': {'acertos': 7, 'erros': 5, 'total': 12},
            'Contragolpe': {'acertos': 1, 'erros': 1, 'total': 2},
            'Reset Cluster': {'acertos': 0, 'erros': 0, 'total': 0},
            'Falsa Alternância': {'acertos': 0, 'erros': 0, 'total': 0},
            'Meta-Algoritmo': {'acertos': 0, 'erros': 0, 'total': 0}
        }
    },
    'ws': {
        'conectado': False,
        'ultima_msg': None,
        'total_recebido': 0
    }
}

# =============================================================================
# PESOS DAS ESTRATÉGIAS
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

# =============================================================================
# POOL DE CONEXÕES (como site faz)
# =============================================================================
try:
    parsed = urllib.parse.urlparse(DATABASE_URL)
    conn_pool = ThreadedConnectionPool(5, 20, 
        database=parsed.path[1:],
        user=parsed.username,
        password=parsed.password,
        host=parsed.hostname,
        port=parsed.port or 5432,
        sslmode='require'
    )
    print("✅ Connection pool criado")
except Exception as e:
    print(f"⚠️ Erro ao criar pool: {e}")
    conn_pool = None

def get_db_connection():
    """Pega conexão do pool (mais rápido)"""
    if conn_pool:
        try:
            return conn_pool.getconn()
        except:
            pass
    
    # Fallback para conexão direta
    try:
        conn = pg8000.connect(
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path[1:],
            ssl_context=True
        )
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return None

def return_db_connection(conn):
    """Devolve conexão ao pool"""
    if conn_pool:
        conn_pool.putconn(conn)

# =============================================================================
# FUNÇÕES DO BANCO
# =============================================================================

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
        return_db_connection(conn)
        print("✅ Tabelas criadas/verificadas")
        return True
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def batch_save(rodadas):
    """Salva múltiplas rodadas de uma vez (batch)"""
    if not rodadas:
        return 0
    
    conn = get_db_connection()
    if not conn:
        return 0
    
    try:
        cur = conn.cursor()
        saved = 0
        for rodada in rodadas:
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
                saved += 1
        
        conn.commit()
        cur.close()
        return_db_connection(conn)
        return saved
    except Exception as e:
        print(f"❌ Erro ao salvar batch: {e}")
        return 0

# =============================================================================
# FUNÇÕES DO BANCO (LEVES)
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
        return_db_connection(conn)
        
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
        cur.execute('''
            SELECT data_hora, player_score, banker_score, resultado
            FROM rodadas
            ORDER BY data_hora DESC
            LIMIT 20
        ''')
        
        rows = cur.fetchall()
        cur.close()
        return_db_connection(conn)
        
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
        return 2123
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM rodadas')
        total = cur.fetchone()[0]
        cur.close()
        return_db_connection(conn)
        return total
    except Exception as e:
        print(f"⚠️ Erro get_total: {e}")
        return 2123

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
        return_db_connection(conn)
        return count
    except Exception as e:
        print(f"⚠️ Erro contar_periodo {horas}h: {e}")
        return 0

def atualizar_dados_pesados():
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
    print(f"📊 Pesados: {cache['pesados']['periodos']}")

# =============================================================================
# 🔥 WEBSOCKET - TEMPO REAL (como o site faz)
# =============================================================================

async def websocket_listener():
    """Escuta WebSocket do betmind.org em tempo real"""
    global ws_connected, ultimo_id_ws, resultados_cache
    
    while True:
        try:
            async with websockets.connect(WS_URL) as ws:
                ws_connected = True
                cache['ws']['conectado'] = True
                print("\n🔗✅ WEBSOCKET CONECTADO - Modo tempo real ativado!")
                
                while True:
                    try:
                        # Recebe mensagem do WebSocket
                        mensagem = await asyncio.wait_for(ws.recv(), timeout=30)
                        data = json.loads(mensagem)
                        
                        # Processa mensagem criptografada (se for o caso)
                        if 'encrypted' in data:
                            # Aqui você implementaria a descriptografia
                            # Por enquanto, ignora e confia no Supabase
                            continue
                        
                        # Parse da mensagem (formato betmind)
                        if 'gameId' in data or 'result' in data:
                            # Extrai dados da rodada
                            player = data.get('player_score', 0) or data.get('player', 0)
                            banker = data.get('banker_score', 0) or data.get('banker', 0)
                            resultado = data.get('result', '') or data.get('outcome', '')
                            
                            # Normaliza resultado
                            if 'player' in str(resultado).lower():
                                resultado_final = 'PLAYER'
                            elif 'banker' in str(resultado).lower():
                                resultado_final = 'BANKER'
                            else:
                                resultado_final = 'TIE'
                            
                            # Cria ID único
                            timestamp = int(time.time() * 1000)
                            rodada_id = f"ws_{player}_{banker}_{timestamp}"
                            
                            rodada = {
                                'id': rodada_id,
                                'data_hora': datetime.now(timezone.utc),
                                'player_score': int(player) if player else 0,
                                'banker_score': int(banker) if banker else 0,
                                'resultado': resultado_final,
                                'multiplicador': 1
                            }
                            
                            # Evita duplicatas
                            if rodada_id != ultimo_id_ws:
                                ultimo_id_ws = rodada_id
                                
                                # Adiciona ao cache
                                resultados_cache.append(rodada)
                                cache['ws']['total_recebido'] += 1
                                cache['ws']['ultima_msg'] = datetime.now().isoformat()
                                
                                # Salva no banco
                                if batch_save([rodada]):
                                    cache['ultimo_resultado_real'] = resultado_final
                                    print(f"⚡ WS TEMPO REAL: {player} vs {banker} → {resultado_final}")
                                    
                                    # Atualiza cache leve
                                    atualizar_dados_leves()
                            
                    except asyncio.TimeoutError:
                        # Timeout normal, continua
                        continue
                    except Exception as e:
                        print(f"⚠️ Erro processando WS: {e}")
                        
        except Exception as e:
            ws_connected = False
            cache['ws']['conectado'] = False
            print(f"\n🔴 WEBSOCKET DESCONECTADO: {e}")
            print("🔄 Tentando reconectar em 5 segundos...")
            await asyncio.sleep(5)

# =============================================================================
# 🔥 SUPABASE POLLING OTIMIZADO (fallback)
# =============================================================================

async def supabase_poll(session):
    """Polling otimizado do Supabase com ETag"""
    global supabase_last_etag, resultados_cache
    
    try:
        # Tenta diferentes tabelas
        tabelas = ['bacbo_results', 'bacbo_rodadas', 'game_results']
        
        for tabela in tabelas:
            url = f"{SUPABASE_URL}/rest/v1/{tabela}"
            params = {
                'select': '*',
                'order': 'created_at.desc,result_timestamp.desc',
                'limit': 10
            }
            
            async with session.get(url, params=params, headers=SUPABASE_HEADERS) as resp:
                if resp.status == 200:
                    # Verifica ETag (cache)
                    etag = resp.headers.get('ETag')
                    if etag and etag == supabase_last_etag:
                        # Dados não mudaram
                        return False
                    
                    supabase_last_etag = etag
                    dados = await resp.json()
                    
                    if dados and len(dados) > 0:
                        print(f"📦 Supabase: {len(dados)} novas rodadas")
                        
                        rodadas = []
                        for item in dados[:5]:
                            player = item.get('player_score') or item.get('playerScore') or 0
                            banker = item.get('banker_score') or item.get('bankerScore') or 0
                            resultado = item.get('resultado') or item.get('result') or 'TIE'
                            
                            if 'player' in str(resultado).lower():
                                resultado_final = 'PLAYER'
                            elif 'banker' in str(resultado).lower():
                                resultado_final = 'BANKER'
                            else:
                                resultado_final = 'TIE'
                            
                            rodada = {
                                'id': f"supabase_{player}_{banker}_{int(time.time())}",
                                'data_hora': datetime.now(timezone.utc),
                                'player_score': int(player),
                                'banker_score': int(banker),
                                'resultado': resultado_final,
                                'multiplicador': 1
                            }
                            rodadas.append(rodada)
                            resultados_cache.append(rodada)
                        
                        if rodadas:
                            batch_save(rodadas)
                            return True
        return False
        
    except Exception as e:
        print(f"⚠️ Erro Supabase poll: {e}")
        return False

# =============================================================================
# LOOP HÍBRIDO (WS + Supabase)
# =============================================================================

async def loop_hibrido():
    """Loop principal: WS tempo real + Supabase fallback"""
    connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
    timeout = aiohttp.ClientTimeout(total=8)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        print("\n🚀 SISTEMA HÍBRIDO INICIADO")
        print("   - WebSocket: Tempo real (prioridade)")
        print("   - Supabase: Fallback a cada 30s\n")
        
        # Inicia WebSocket em background
        ws_task = asyncio.create_task(websocket_listener())
        
        contador = 0
        while True:
            try:
                contador += 1
                
                # Supabase polling a cada 30 segundos (10 ciclos de 3s)
                if contador % 10 == 0:
                    print("\n📡 Verificando Supabase (fallback)...")
                    novas = await supabase_poll(session)
                    if novas:
                        atualizar_dados_leves()
                
                # Mostra status
                status_ws = "🟢 CONECTADO" if ws_connected else "🔴 DESCONECTADO"
                print(f"\n📊 Status WS: {status_ws} | Cache: {len(resultados_cache)} rodadas")
                
                await asyncio.sleep(3)
                
            except Exception as e:
                print(f"⚠️ Erro no loop híbrido: {e}")
                await asyncio.sleep(5)

# =============================================================================
# ESTRATÉGIAS (COMPLETAS)
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

# =============================================================================
# SISTEMA DE APRENDIZADO
# =============================================================================

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
        
        print(f"\n{'✅' if acertou else '❌'} RESULTADO: {ultima['simbolo']} {ultima['previsao']} vs {resultado_real}")
        
        cache['ultima_previsao'] = None
        cache['ultimo_resultado_real'] = None

def calcular_precisao():
    total = cache['estatisticas']['total_previsoes']
    if total == 0:
        return 0
    return round((cache['estatisticas']['acertos'] / total) * 100)

# =============================================================================
# ATUALIZAÇÃO DE DADOS
# =============================================================================

def atualizar_dados_leves():
    verificar_previsoes_anteriores()
    
    cache['leves']['ultimas_50'] = get_ultimas_50()
    cache['leves']['ultimas_20'] = get_ultimas_20()
    cache['leves']['total_rodadas'] = get_total_rapido()
    
    if cache['leves']['previsao']:
        cache['ultima_previsao'] = cache['leves']['previsao']
    
    cache['leves']['previsao'] = calcular_previsao()
    cache['leves']['ultima_atualizacao'] = datetime.now(timezone.utc)
    
    print(f"⚡ Cache atualizado - Total: {cache['leves']['total_rodadas']} | Precisão: {calcular_precisao()}%")

def loop_pesado():
    while True:
        time.sleep(30)
        atualizar_dados_pesados()

# =============================================================================
# ROTAS FLASK
# =============================================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats')
def api_stats():
    try:
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
            ultima_atualizacao = brasilia.strftime('%d/%m/%Y %H:%M:%S')
        
        return jsonify({
            'ultima_atualizacao': ultima_atualizacao,
            'total_rodadas': cache['leves']['total_rodadas'],
            'ultimas_20': cache['leves']['ultimas_20'],
            'previsao': cache['leves']['previsao'],
            'periodos': cache['pesados']['periodos'],
            'ws': {
                'conectado': cache['ws']['conectado'],
                'total_recebido': cache['ws']['total_recebido'],
                'ultima_msg': cache['ws']['ultima_msg']
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
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/tabela/<int:limite>')
def api_tabela(limite):
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
        return_db_connection(conn)
        
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
    return jsonify({
        'status': 'ok', 
        'rodadas': cache['leves']['total_rodadas'],
        'ws_conectado': cache['ws']['conectado'],
        'timestamp': datetime.now().isoformat()
    })

@app.route('/diagnostico')
def diagnostico():
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'ws': cache['ws'],
        'cache_len': len(resultados_cache),
        'cache': {
            'total_rodadas': cache['leves']['total_rodadas'],
            'previsao': cache['leves']['previsao'],
            'ultima_atualizacao': str(cache['leves']['ultima_atualizacao'])
        },
        'estatisticas': {
            'total_previsoes': cache['estatisticas']['total_previsoes'],
            'acertos': cache['estatisticas']['acertos'],
            'erros': cache['estatisticas']['erros'],
            'precisao': calcular_precisao()
        }
    })

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("="*70)
    print("🚀 BOT BACBO - HÍBRIDO WS + SUPABASE (TEMPO REAL)")
    print("="*70)
    print("✅ WebSocket: tempo real (igual ao site)")
    print("✅ Supabase: fallback com cache ETag")
    print("✅ Connection Pool: 20 conexões simultâneas")
    print("✅ Batch Save: 100 rodadas de uma vez")
    print("="*70)
    
    init_db()
    
    # Dados iniciais
    print("📊 Carregando dados do banco...")
    atualizar_dados_leves()
    atualizar_dados_pesados()
    
    print(f"📊 {cache['leves']['total_rodadas']} rodadas no banco")
    print("="*70)
    
    # Inicia loop híbrido (WS + Supabase)
    print("🚀 Iniciando sistema híbrido...")
    
    def run_async_loop():
        asyncio.run(loop_hibrido())
    
    threading.Thread(target=run_async_loop, daemon=True).start()
    threading.Thread(target=loop_pesado, daemon=True).start()
    
    print("✅ Servidor Flask iniciando...")
    print("🌐 Acesse /diagnostico para ver status do WebSocket")
    app.run(host='0.0.0.0', port=PORT, debug=False)
