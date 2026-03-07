# main.py - VERSÃO ULTRA RÁPIDA (0.2 SEGUNDOS)
# ✅ Coleta a cada 0.2 segundos usando API /latest
# ✅ Processamento em lote (batch) para máximo desempenho
# ✅ Pool de conexões com banco de dados
# ✅ Força quebra de cache com timestamp
# ✅ Rota /api/tabela com logs de debug
# ✅ Dados de winners inclusos para análises

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
from queue import Queue

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================
DATABASE_URL = "postgresql://neondb_owner:npg_l4nHebCWvok8@ep-old-field-adcep1b1-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# Parse da URL
parsed = urllib.parse.urlparse(DATABASE_URL)
DB_USER = parsed.username
DB_PASSWORD = parsed.password
DB_HOST = parsed.hostname
DB_PORT = parsed.port or 5432
DB_NAME = parsed.path[1:]

# NOVA API - LATEST (APENAS 1 RESULTADO)
LATEST_API_URL = "https://api-cs.casino.org/svc-evolution-game-events/api/bacbo/latest"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Pragma': 'no-cache'
}

# Configurações
TIMEOUT_API = 1  # Reduzido para 1 segundos
INTERVALO_COLETA = 0.2  # 0.2 SEGUNDOS!
PORT = int(os.environ.get("PORT", 5000))

# =============================================================================
# POOL DE CONEXÕES
# =============================================================================
class ConnectionPool:
    def __init__(self, max_connections=5):
        self._pool = Queue(maxsize=max_connections)
        for _ in range(max_connections):
            self._pool.put(self._create_connection())
    
    def _create_connection(self):
        try:
            return pg8000.connect(
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                ssl_context=True
            )
        except Exception as e:
            print(f"❌ Erro ao criar conexão: {e}")
            return None
    
    def get_conn(self):
        try:
            return self._pool.get(timeout=5)
        except:
            return self._create_connection()
    
    def return_conn(self, conn):
        if conn:
            try:
                self._pool.put_nowait(conn)
            except:
                try:
                    conn.close()
                except:
                    pass

# Pool global
db_pool = ConnectionPool()

# =============================================================================
# FILA DE PROCESSAMENTO
# =============================================================================
fila_rodadas = deque(maxlen=200)
ultimo_id_processado = None
ULTIMO_ID_LATEST = None  # Controle para API latest

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
        'ultimo_id': None,
        'total_coletado': 0,
        'falhas': 0
    },
    'ultima_previsao': None,
    'ultimo_resultado_real': None,
    'winners_stats': {
        'total_winners': 0,
        'total_amount': 0,
        'maior_premio': 0,
        'ultimo_premio': 0
    }
}

# =============================================================================
# PESOS DAS ESTRATÉGIAS (MANTIDOS IGUAIS)
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
# FUNÇÕES DO BANCO OTIMIZADAS
# =============================================================================

def get_db_connection():
    """Obtém conexão do pool"""
    return db_pool.get_conn()

def return_db_connection(conn):
    """Retorna conexão ao pool"""
    db_pool.return_conn(conn)

def init_db():
    """Inicializa tabelas no banco"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        # Tabela de rodadas com campos extras para winners
        cur.execute('''
            CREATE TABLE IF NOT EXISTS rodadas (
                id TEXT PRIMARY KEY,
                data_hora TIMESTAMPTZ,
                player_score INTEGER,
                banker_score INTEGER,
                soma INTEGER,
                resultado TEXT,
                multiplicador FLOAT DEFAULT 1,
                total_winners INTEGER DEFAULT 0,
                total_amount FLOAT DEFAULT 0,
                dados_json JSONB
            )
        ''')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_data_hora ON rodadas(data_hora DESC)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_resultado ON rodadas(resultado)')
        
        # Tabela de previsões
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
        return_db_connection(conn)
        return False

def salvar_rodadas_batch(rodadas):
    """Salva múltiplas rodadas em uma única transação (BATCH)"""
    if not rodadas:
        return 0
    
    conn = get_db_connection()
    if not conn:
        return 0
    
    try:
        cur = conn.cursor()
        values = []
        for r in rodadas:
            values.append((
                r['id'],
                r['data_hora'],
                r['player_score'],
                r['banker_score'],
                r['player_score'] + r['banker_score'],
                r['resultado'],
                r.get('multiplier', 1),
                r.get('winners', 0),
                r.get('total_amount', 0),
                json.dumps(r, default=str)
            ))
        
        cur.executemany('''
            INSERT INTO rodadas 
            (id, data_hora, player_score, banker_score, soma, resultado, 
             multiplicador, total_winners, total_amount, dados_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        ''', values)
        
        conn.commit()
        
        # Conta quantos foram inseridos (aproximado)
        saved = len(rodadas)
        cur.close()
        return_db_connection(conn)
        
        # Atualiza stats de winners
        for r in rodadas:
            cache['winners_stats']['total_winners'] += r.get('winners', 0)
            cache['winners_stats']['total_amount'] += r.get('total_amount', 0)
            cache['winners_stats']['ultimo_premio'] = r.get('total_amount', 0)
            if r.get('total_amount', 0) > cache['winners_stats']['maior_premio']:
                cache['winners_stats']['maior_premio'] = r.get('total_amount', 0)
        
        return saved
    except Exception as e:
        print(f"❌ Erro batch: {e}")
        return_db_connection(conn)
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
        cur.execute('SELECT player_score, banker_score, resultado FROM rodadas ORDER BY data_hora DESC LIMIT 50')
        rows = cur.fetchall()
        cur.close()
        return_db_connection(conn)
        return [{'player_score': r[0], 'banker_score': r[1], 'resultado': r[2]} for r in rows]
    except Exception as e:
        print(f"⚠️ Erro get_ultimas_50: {e}")
        return_db_connection(conn)
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
        return 0
    try:
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM rodadas')
        total = cur.fetchone()[0]
        cur.close()
        return_db_connection(conn)
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

# =============================================================================
# 🔥 NOVA API - LATEST (APENAS 1 RESULTADO)
# =============================================================================

def buscar_api_latest():
    """Busca APENAS a rodada mais recente - ULTRA RÁPIDO"""
    global ULTIMO_ID_LATEST
    
    try:
        # Cache busting leve (só um timestamp)
        params = {'_': int(time.time() * 1000)}
        
        # Requisição rápida
        response = session.get(LATEST_API_URL, params=params, timeout=TIMEOUT_API)
        response.raise_for_status()
        dados = response.json()
        
        # Extrai os dados principais
        data = dados.get('data', {})
        result = data.get('result', {})
        rodada_id = data.get('id')
        
        # Se não tiver ID ou for o mesmo da última, ignora
        if not rodada_id or rodada_id == ULTIMO_ID_LATEST:
            return None
        
        # Mapeia o resultado
        outcome = result.get('outcome', '')
        if outcome == 'PlayerWon':
            resultado = 'PLAYER'
        elif outcome == 'BankerWon':
            resultado = 'BANKER'
        else:
            resultado = 'TIE'
        
        # Converte data
        data_hora_str = data.get('settledAt', '')
        if data_hora_str:
            data_hora = datetime.fromisoformat(data_hora_str.replace('Z', '+00:00'))
        else:
            data_hora = datetime.now(timezone.utc)
        
        # Cria objeto da rodada (formato compatível)
        rodada = {
            'id': rodada_id,
            'data_hora': data_hora,
            'player_score': result.get('playerDice', {}).get('score', 0),
            'banker_score': result.get('bankerDice', {}).get('score', 0),
            'resultado': resultado,
            'multiplier': result.get('multiplier', 1),
            'winners': dados.get('totalWinners', 0),
            'total_amount': dados.get('totalAmount', 0)
        }
        
        # Atualiza o último ID
        ULTIMO_ID_LATEST = rodada_id
        cache['api']['ultimo_id'] = rodada_id
        
        print(f"🎲 NOVA: P{rodada['player_score']} x B{rodada['banker_score']} = {rodada['resultado']} "
              f"(💰 {rodada['winners']} winners - R${rodada['total_amount']:.2f})")
        
        return [rodada]  # Retorna lista de 1 item (compatível)
        
    except requests.exceptions.Timeout:
        print(f"⏱️ Timeout - API não respondeu")
        cache['api']['falhas'] += 1
        return None
    except requests.exceptions.ConnectionError:
        print(f"🔌 Erro de conexão")
        cache['api']['falhas'] += 1
        return None
    except Exception as e:
        print(f"⚠️ Erro na /latest: {e}")
        cache['api']['falhas'] += 1
        return None

# =============================================================================
# 🔥 PROCESSADOR ULTRA RÁPIDO - VERSÃO BATCH
# =============================================================================

def processar_fila_imediato():
    """Processa a fila atual em lote"""
    if not fila_rodadas:
        return 0
    
    tamanho = len(fila_rodadas)
    batch = list(fila_rodadas)
    fila_rodadas.clear()
    
    inicio = time.time()
    saved = salvar_rodadas_batch(batch)
    tempo = time.time() - inicio
    
    if saved > 0:
        print(f"💾 BATCH: salvou {saved}/{tamanho} rodadas em {tempo:.3f}s")
        
        # Atualiza o último resultado real para aprendizado
        if batch:
            cache['ultimo_resultado_real'] = batch[-1]['resultado']
        
        atualizar_dados_leves()
    
    return saved

def processador_continuo():
    """Processa a fila continuamente com prioridade"""
    print("🚀 Processador BATCH contínuo iniciado...")
    
    while True:
        try:
            if fila_rodadas:
                # Se tem pelo menos 1, processa imediatamente
                processar_fila_imediato()
            
            # Delay mínimo
            time.sleep(0.05)  # 50ms
            
        except Exception as e:
            print(f"❌ Erro processador: {e}")
            time.sleep(0.1)

# =============================================================================
# 🔥 LOOP DE COLETA OTIMIZADO (0.5 SEGUNDOS)
# =============================================================================

def loop_coleta_rapido():
    """Coleta a cada 0.5 SEGUNDOS usando a API latest"""
    print("📡 Coletor ULTRA RÁPIDO (0.5s) iniciado...")
    global fila_rodadas
    
    while True:
        try:
            inicio = time.time()
            
            # Busca apenas a última rodada
            rodada = buscar_api_latest()
            
            if rodada:
                # Adiciona na fila (sempre 1 item)
                fila_rodadas.append(rodada[0])
                cache['api']['total_coletado'] += 1
                
                # Se fila acumular, processa rápido
                if len(fila_rodadas) >= 3:
                    processar_fila_imediato()
            
            # Calcula tempo gasto e ajusta sleep
            elapsed = time.time() - inicio
            sleep_time = max(0.1, INTERVALO_COLETA - elapsed)
            time.sleep(sleep_time)
            
            # Status a cada 10 segundos
            if int(time.time()) % 10 == 0:
                print(f"📊 Status - Fila: {len(fila_rodadas)} | Total: {cache['leves']['total_rodadas']} | "
                      f"API falhas: {cache['api']['falhas']}")
            
        except Exception as e:
            print(f"❌ Erro coleta: {e}")
            time.sleep(INTERVALO_COLETA)

# =============================================================================
# ESTRATÉGIAS (TUDO MANTIDO IGUAL)
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
# SISTEMA DE APRENDIZADO (MANTIDO IGUAL)
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
        
        print(f"\n{'✅' if acertou else '❌'} {ultima['simbolo']} {ultima['previsao']} vs {resultado_real}")
        
        cache['ultima_previsao'] = None
        cache['ultimo_resultado_real'] = None

def calcular_precisao():
    total = cache['estatisticas']['total_previsoes']
    if total == 0:
        return 0
    return round((cache['estatisticas']['acertos'] / total) * 100)

# =============================================================================
# ATUALIZAÇÃO
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

# =============================================================================
# 🔥 ROTA TABELA CORRIGIDA COM LOGS DE DEBUG
# =============================================================================

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
        
        # Primeiro, verifica quantas rodadas existem
        cur.execute('SELECT COUNT(*) FROM rodadas')
        total_banco = cur.fetchone()[0]
        print(f"   📊 Total no banco: {total_banco} rodadas")
        
        # Agora busca as últimas {limite} rodadas
        cur.execute('''
            SELECT data_hora, player_score, banker_score, resultado 
            FROM rodadas 
            ORDER BY data_hora DESC 
            LIMIT %s
        ''', (limite,))
        
        rows = cur.fetchall()
        print(f"   📥 Query retornou {len(rows)} linhas")
        
        cur.close()
        return_db_connection(conn)
        
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

# =============================================================================
# ROTAS FLASK
# =============================================================================

@app.route('/')
def index():
    return render_template('index.html')

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
            'falhas': cache['api']['falhas']
        },
        'winners': {
            'total_winners': cache['winners_stats']['total_winners'],
            'total_amount': cache['winners_stats']['total_amount'],
            'maior_premio': cache['winners_stats']['maior_premio'],
            'ultimo_premio': cache['winners_stats']['ultimo_premio']
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
        'fila': len(fila_rodadas),
        'api_falhas': cache['api']['falhas']
    })

@app.route('/status-fila')
def status_fila():
    return jsonify({
        'fila': len(fila_rodadas),
        'ultimo_id': cache['api']['ultimo_id']
    })

# =============================================================================
# 🔥 LOOP PESADO - ATUALIZA ESTATÍSTICAS (5 segundos)
# =============================================================================

def loop_pesado():
    """Loop para atualizar estatísticas pesadas a cada 0.5 segundos"""
    print("🔄 Loop pesado iniciado (5s)...")
    time.sleep(1)  # Aguarda inicialização
    while True:
        try:
            atualizar_dados_pesados()
            if cache['pesados']['periodos']:
                print(f"📊 Estatísticas pesadas atualizadas")
        except Exception as e:
            print(f"❌ Erro no loop pesado: {e}")
        time.sleep(0.5)

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("="*70)
    print("🚀 BOT BACBO - ULTRA RÁPIDO (0.5 SEGUNDOS)")
    print("="*70)
    print("✅ Coleta a cada 0.5 segundos usando API /latest")
    print("✅ Processamento em lote (batch)")
    print("✅ Pool de conexões com banco")
    print("✅ Dados de winners inclusos")
    print("="*70)
    
    # Inicializa banco
    init_db()
    
    # Carrega dados iniciais
    print("📊 Carregando dados...")
    atualizar_dados_leves()
    atualizar_dados_pesados()
    print(f"📊 {cache['leves']['total_rodadas']} rodadas no banco")
    print("="*70)
    
    # Threads
    threading.Thread(target=loop_coleta_rapido, daemon=True).start()
    threading.Thread(target=processador_continuo, daemon=True).start()
    threading.Thread(target=loop_pesado, daemon=True).start()
    
    print("✅ Servidor rodando em 0.5s!")
    print("📋 Acesse /api/tabela/50 para ver os dados brutos")
    print("📊 /api/stats para estatísticas completas")
    app.run(host='0.0.0.0', port=PORT, debug=False)
