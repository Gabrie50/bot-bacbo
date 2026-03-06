# main.py - SISTEMA TURBO COM 3 FONTES + HISTÓRICO (COMPLETO E CORRIGIDO)
# ✅ WebSocket (tempo real) - PRIORIDADE MÁXIMA
# ✅ API Latest (polling inteligente) - PRIORIDADE MÉDIA  
# ✅ API Normal (fallback histórico) - PRIORIDADE BAIXA
# ✅ Sistema anti-duplicação por ID (FUNCIONANDO!)
# ✅ 8 Estratégias completas (ATUALIZANDO!)
# ✅ Histórico de previsões no banco

import os
import time
import requests
import json
import urllib.parse
import random
import threading
import websocket
from datetime import datetime, timedelta, timezone
from collections import deque
from flask import Flask, render_template, jsonify
from flask_cors import CORS
import pg8000

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================
DATABASE_URL = "postgresql://neondb_owner:npg_B5MPOgfYA1Ik@ep-holy-hall-addv9tiz-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
# Parse da URL
parsed = urllib.parse.urlparse(DATABASE_URL)
DB_USER = parsed.username
DB_PASSWORD = parsed.password
DB_HOST = parsed.hostname
DB_PORT = parsed.port or 5432
DB_NAME = parsed.path[1:]

# =============================================================================
# CONFIGURAÇÕES DAS 3 FONTES
# =============================================================================

# FONTE 1: WebSocket (Tempo Real)
WS_URL = "wss://api-cs.casino.org/svc-evolution-game-events/ws/bacbo"

# FONTE 2: API Latest (Polling Inteligente)
LATEST_API_URL = "https://api-cs.casino.org/svc-evolution-game-events/api/bacbo/latest"

# FONTE 3: API Normal (Fallback Histórico)
API_URL = "https://api-cs.casino.org/svc-evolution-game-events/api/bacbo"
API_PARAMS = {
    "page": 0,
    "size": 30,
    "sort": "data.settledAt,desc",
    "duration": 4320,
    "wheelResults": "PlayerWon,BankerWon,Tie"
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
}

# Configurações gerais
TIMEOUT_API = 5
MAX_RETRIES = 3
RETRY_DELAY = 1
INTERVALO_LATEST = 2  # 2 segundos para /latest
INTERVALO_NORMAL = 10  # 10 segundos para API normal (fallback)
PORT = int(os.environ.get("PORT", 5000))

# =============================================================================
# CACHE DE IDS PARA EVITAR DUPLICAÇÃO
# =============================================================================
ids_processados = set()  # Guarda todos os IDs já processados
fila_rodadas = deque(maxlen=500)

# Status das fontes
fontes_status = {
    'websocket': {'status': 'desconectado', 'total': 0, 'falhas': 0},
    'latest': {'status': 'ativo', 'total': 0, 'falhas': 0},
    'api_normal': {'status': 'ativo', 'total': 0, 'falhas': 0}
}

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
        'total_previsoes': 0,
        'acertos': 0,
        'erros': 0,
        'ultimas_20_previsoes': [],
        'estrategias': {
            'Compensação': {'acertos': 0, 'erros': 0, 'total': 0},
            'Paredão': {'acertos': 0, 'erros': 0, 'total': 0},
            'Moedor': {'acertos': 0, 'erros': 0, 'total': 0},
            'Xadrez': {'acertos': 0, 'erros': 0, 'total': 0},
            'Contragolpe': {'acertos': 0, 'erros': 0, 'total': 0},
            'Reset Cluster': {'acertos': 0, 'erros': 0, 'total': 0},
            'Falsa Alternância': {'acertos': 0, 'erros': 0, 'total': 0},
            'Meta-Algoritmo': {'acertos': 0, 'erros': 0, 'total': 0}
        }
    },
    'ultima_previsao': None,
    'ultimo_resultado_real': None
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
session = requests.Session()
session.headers.update(HEADERS)

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
                fonte TEXT,
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
                simbolo TEXT,
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

def salvar_rodada(rodada, fonte):
    """Salva rodada no banco com identificação da fonte"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO rodadas 
            (id, data_hora, player_score, banker_score, soma, resultado, fonte, dados_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        ''', (
            rodada['id'],
            rodada['data_hora'],
            rodada['player_score'],
            rodada['banker_score'],
            rodada['player_score'] + rodada['banker_score'],
            rodada['resultado'],
            fonte,
            json.dumps(rodada, default=str)
        ))
        
        if cur.rowcount > 0:
            conn.commit()
            cur.close()
            conn.close()
            return True
        conn.rollback()
        cur.close()
        conn.close()
        return False
    except Exception as e:
        print(f"❌ Erro ao salvar: {e}")
        return False

def salvar_previsao(previsao, resultado_real, acertou):
    """Salva previsão no banco de dados"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO historico_previsoes 
            (data_hora, previsao, simbolo, confianca, resultado_real, acertou, estrategias, modo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            datetime.now(timezone.utc),
            previsao['previsao'],
            previsao['simbolo'],
            previsao['confianca'],
            resultado_real,
            acertou,
            ','.join(previsao['estrategias']),
            previsao['modo']
        ))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar previsão: {e}")
        return False

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
# 🔥 FUNÇÃO ÚNICA PARA PROCESSAR RODADA (EVITA DUPLICAÇÃO) - CORRIGIDA!
# =============================================================================

def processar_rodada(rodada, fonte):
    """
    Processa uma rodada de qualquer fonte.
    Retorna True se foi nova, False se já existia.
    """
    global ids_processados
    
    rodada_id = rodada['id']
    
    # 🔥 VERIFICA SE JÁ FOI PROCESSADO
    if rodada_id in ids_processados:
        print(f"   ⏭️ [DUPLICADO] {fonte} - {rodada['player_score']} vs {rodada['banker_score']} (já processado)")
        return False
    
    # MARCA COMO PROCESSADO
    ids_processados.add(rodada_id)
    
    # Limita o tamanho do set
    if len(ids_processados) > 10000:
        ids_processados = set(list(ids_processados)[-5000:])
    
    # 🔥 ADICIONA A FONTE NA RODADA!
    rodada_com_fonte = rodada.copy()
    rodada_com_fonte['fonte'] = fonte
    
    # Adiciona à fila
    fila_rodadas.append(rodada_com_fonte)
    
    # Atualiza estatísticas da fonte
    if fonte in fontes_status:
        fontes_status[fonte]['total'] += 1
    
    print(f"\n✅ [{fonte.upper()}] NOVO: {rodada['player_score']} vs {rodada['banker_score']} - {rodada['resultado']}")
    
    return True

# =============================================================================
# 🔥 FONTE 1: WEBSOCKET (TEMPO REAL) - CORRIGIDO
# =============================================================================

def on_ws_message(ws, message):
    """Recebe mensagens do WebSocket"""
    try:
        data = json.loads(message)
        
        if 'data' in data and 'result' in data['data']:
            game_data = data['data']
            result = game_data['result']
            
            novo_id = game_data.get('id')
            
            if novo_id:
                player_dice = result.get('playerDice', {})
                banker_dice = result.get('bankerDice', {})
                
                player_score = player_dice.get('first', 0) + player_dice.get('second', 0)
                banker_score = banker_dice.get('first', 0) + banker_dice.get('second', 0)
                
                outcome = result.get('outcome', '')
                if outcome == 'PlayerWon':
                    resultado = 'PLAYER'
                elif outcome == 'BankerWon':
                    resultado = 'BANKER'
                else:
                    resultado = 'TIE'
                
                rodada = {
                    'id': novo_id,
                    'data_hora': datetime.now(timezone.utc),
                    'player_score': player_score,
                    'banker_score': banker_score,
                    'resultado': resultado
                }
                
                # USA A FUNÇÃO ÚNICA
                processar_rodada(rodada, 'websocket')
                
    except Exception as e:
        print(f"⚠️ Erro WS: {e}")

def on_ws_error(ws, error):
    fontes_status['websocket']['status'] = 'erro'
    fontes_status['websocket']['falhas'] += 1
    print(f"🔌 WS Erro: {error}")

def on_ws_close(ws, close_status_code, close_msg):
    fontes_status['websocket']['status'] = 'desconectado'
    print(f"🔌 WS Fechado. Reconectando em 5s...")
    time.sleep(5)
    iniciar_websocket()

def on_ws_open(ws):
    fontes_status['websocket']['status'] = 'conectado'
    print("✅ WEBSOCKET CONECTADO! Modo tempo real ativado!")

def iniciar_websocket():
    def run():
        ws = websocket.WebSocketApp(
            WS_URL,
            on_open=on_ws_open,
            on_message=on_ws_message,
            on_error=on_ws_error,
            on_close=on_ws_close
        )
        ws.run_forever()
    
    threading.Thread(target=run, daemon=True).start()

# =============================================================================
# 🔥 FONTE 2: API LATEST (POLLING INTELIGENTE) - CORRIGIDO
# =============================================================================

def buscar_latest():
    """Busca apenas a última rodada"""
    try:
        response = requests.get(LATEST_API_URL, headers=HEADERS, timeout=3)
        
        if response.status_code == 200:
            dados = response.json()
            
            novo_id = dados.get('id')
            data = dados.get('data', {})
            result = data.get('result', {})
            
            if novo_id:
                player_dice = result.get('playerDice', {})
                banker_dice = result.get('bankerDice', {})
                
                player_score = player_dice.get('first', 0) + player_dice.get('second', 0)
                banker_score = banker_dice.get('first', 0) + banker_dice.get('second', 0)
                
                outcome = result.get('outcome', '')
                if outcome == 'PlayerWon':
                    resultado = 'PLAYER'
                elif outcome == 'BankerWon':
                    resultado = 'BANKER'
                else:
                    resultado = 'TIE'
                
                rodada = {
                    'id': novo_id,
                    'data_hora': datetime.now(timezone.utc),
                    'player_score': player_score,
                    'banker_score': banker_score,
                    'resultado': resultado
                }
                
                return rodada
        
        return None
    except Exception as e:
        fontes_status['latest']['falhas'] += 1
        return None

def loop_latest():
    """Loop da fonte Latest"""
    print("📡 Coletor LATEST iniciado (2s)...")
    while True:
        try:
            rodada = buscar_latest()
            if rodada:
                # USA A FUNÇÃO ÚNICA
                processar_rodada(rodada, 'latest')
            time.sleep(INTERVALO_LATEST)
        except Exception as e:
            print(f"❌ Erro Latest: {e}")
            time.sleep(INTERVALO_LATEST)

# =============================================================================
# 🔥 FONTE 3: API NORMAL (FALLBACK HISTÓRICO) - CORRIGIDO
# =============================================================================

def buscar_api_normal():
    """Busca histórico da API normal"""
    try:
        params = API_PARAMS.copy()
        params['_t'] = int(time.time() * 1000)
        
        response = session.get(API_URL, params=params, timeout=TIMEOUT_API)
        response.raise_for_status()
        dados = response.json()
        
        if dados and len(dados) > 0:
            rodadas = []
            for item in dados[:10]:
                try:
                    data = item.get('data', {})
                    result = data.get('result', {})
                    player_dice = result.get('playerDice', {})
                    banker_dice = result.get('bankerDice', {})
                    
                    player_score = player_dice.get('first', 0) + player_dice.get('second', 0)
                    banker_score = banker_dice.get('first', 0) + banker_dice.get('second', 0)
                    
                    outcome = result.get('outcome', '')
                    if outcome == 'PlayerWon':
                        resultado = 'PLAYER'
                    elif outcome == 'BankerWon':
                        resultado = 'BANKER'
                    else:
                        resultado = 'TIE'
                    
                    data_hora = datetime.fromisoformat(data.get('settledAt', '').replace('Z', '+00:00'))
                    
                    rodada = {
                        'id': data.get('id'),
                        'data_hora': data_hora,
                        'player_score': player_score,
                        'banker_score': banker_score,
                        'resultado': resultado
                    }
                    rodadas.append(rodada)
                except:
                    continue
            
            return rodadas
        
        return None
    except Exception as e:
        fontes_status['api_normal']['falhas'] += 1
        return None

def loop_api_normal():
    """Loop da API Normal (fallback)"""
    print("📚 Coletor API NORMAL iniciado (10s fallback)...")
    while True:
        try:
            # Só executa se WebSocket estiver desconectado (fallback)
            if fontes_status['websocket']['status'] != 'conectado':
                rodadas = buscar_api_normal()
                if rodadas:
                    for rodada in rodadas:
                        # USA A FUNÇÃO ÚNICA
                        processar_rodada(rodada, 'api_normal')
            time.sleep(INTERVALO_NORMAL)
        except Exception as e:
            print(f"❌ Erro API Normal: {e}")
            time.sleep(INTERVALO_NORMAL)

# =============================================================================
# 🔥 PROCESSADOR DA FILA (CORRIGIDO - USA A FONTE DA RODADA!)
# =============================================================================

def processar_fila():
    """Processa a fila instantaneamente"""
    print("🚀 Processador TURBO iniciado...")
    
    while True:
        try:
            if fila_rodadas:
                batch = list(fila_rodadas)
                fila_rodadas.clear()
                
                saved = 0
                for rodada in batch:
                    # 🔥 PEGA A FONTE QUE FOI SALVA NA RODADA
                    fonte = rodada.get('fonte', 'desconhecida')
                    if salvar_rodada(rodada, fonte):
                        saved += 1
                        if saved == 1:
                            cache['ultimo_resultado_real'] = rodada['resultado']
                
                if saved > 0:
                    print(f"💾 TURBO: salvou {saved}/{len(batch)} rodadas")
                    atualizar_dados_leves()
            
            time.sleep(0.01)
            
        except Exception as e:
            print(f"❌ Erro TURBO: {e}")
            time.sleep(0.1)
            
# =============================================================================
# 🧹 FUNÇÃO PARA LIMPAR DUPLICATAS DO BANCO (EXECUTE UMA VEZ!)
# =============================================================================

def limpar_duplicatas():
    """Remove rodadas duplicadas do banco"""
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cur = conn.cursor()
        
        # Encontra e remove duplicatas (mantém a mais antiga)
        cur.execute('''
            DELETE FROM rodadas 
            WHERE id IN (
                SELECT id FROM (
                    SELECT id, 
                           ROW_NUMBER() OVER (
                               PARTITION BY player_score, banker_score, resultado, 
                                            DATE_TRUNC('minute', data_hora)
                               ORDER BY data_hora
                           ) as rn
                    FROM rodadas
                ) t
                WHERE t.rn > 1
            )
        ''')
        
        removidas = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        
        if removidas > 0:
            print(f"✅ Removidas {removidas} duplicatas do banco")
        
    except Exception as e:
        print(f"❌ Erro ao limpar duplicatas: {e}")
        
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
    
    if ties >= 2:
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
# FUNÇÃO PARA IDENTIFICAR O MODO
# =============================================================================
def identificar_modo(player_pct, banker_pct, dados):
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
    estrategias_ativas = []
    
    # ESTRATÉGIA 1: Compensação
    e1 = estrategia_compensacao(dados, modo)
    votos_banker += e1.get('banker', 0)
    votos_player += e1.get('player', 0)
    if e1.get('banker') or e1.get('player'):
        estrategias_ativas.append('Compensação')
    
    # ESTRATÉGIA 2: Paredão
    e2 = estrategia_paredao(dados, modo)
    votos_banker += e2.get('banker', 0)
    votos_player += e2.get('player', 0)
    if e2.get('banker') or e2.get('player'):
        estrategias_ativas.append('Paredão')
    
    # ESTRATÉGIA 3: Moedor
    e3 = estrategia_moedor(dados, modo)
    votos_banker += e3.get('banker', 0)
    votos_player += e3.get('player', 0)
    if e3.get('banker') or e3.get('player'):
        estrategias_ativas.append('Moedor')
    
    # ESTRATÉGIA 4: Xadrez
    e4 = estrategia_xadrez(dados, modo)
    votos_banker += e4.get('banker', 0)
    votos_player += e4.get('player', 0)
    if e4.get('banker') or e4.get('player'):
        estrategias_ativas.append('Xadrez')
    
    # ESTRATÉGIA 5: Contragolpe
    e5 = estrategia_contragolpe(dados, modo)
    votos_banker += e5.get('banker', 0)
    votos_player += e5.get('player', 0)
    if e5.get('banker') or e5.get('player'):
        estrategias_ativas.append('Contragolpe')
    
    # ESTRATÉGIA 6: Reset Pós-Cluster
    e6 = estrategia_reset_cluster(dados, modo)
    votos_banker += e6.get('banker', 0)
    votos_player += e6.get('player', 0)
    if e6.get('banker') or e6.get('player'):
        estrategias_ativas.append('Reset Cluster')
    
    # ESTRATÉGIA 7: Falsa Alternância
    e7 = estrategia_falsa_alternancia(dados, modo)
    votos_banker += e7.get('banker', 0)
    votos_player += e7.get('player', 0)
    if e7.get('banker') or e7.get('player'):
        estrategias_ativas.append('Falsa Alternância')
    
    # ESTRATÉGIA 8: Meta-Algoritmo
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
        estrategias_ativas = ['Análise base']
    
    return {
        'modo': modo,
        'previsao': previsao,
        'simbolo': '🔴' if previsao == 'BANKER' else '🔵' if previsao == 'PLAYER' else '🟡',
        'confianca': confianca,
        'estrategias': estrategias_ativas[:4]
    }

# =============================================================================
# SISTEMA DE APRENDIZADO CORRIGIDO
# =============================================================================

def verificar_previsoes_anteriores():
    """Verifica se a última previsão acertou e ATUALIZA AS ESTRATÉGIAS"""
    if cache.get('ultima_previsao') and cache.get('ultimo_resultado_real'):
        ultima = cache['ultima_previsao']
        resultado_real = cache['ultimo_resultado_real']
        
        acertou = (ultima['previsao'] == resultado_real)
        
        # SALVA NO BANCO
        salvar_previsao(ultima, resultado_real, acertou)
        
        # ATUALIZA ESTATÍSTICAS GERAIS
        cache['estatisticas']['total_previsoes'] += 1
        if acertou:
            cache['estatisticas']['acertos'] += 1
        else:
            cache['estatisticas']['erros'] += 1
        
        # 🔥 CORREÇÃO: ATUALIZA CADA ESTRATÉGIA INDIVIDUALMENTE
        for estrategia in ultima.get('estrategias', []):
            nome_clean = estrategia.split(' ')[0]
            
            if nome_clean in cache['estatisticas']['estrategias']:
                cache['estatisticas']['estrategias'][nome_clean]['total'] += 1
                if acertou:
                    cache['estatisticas']['estrategias'][nome_clean]['acertos'] += 1
                else:
                    cache['estatisticas']['estrategias'][nome_clean]['erros'] += 1
                
                print(f"   📊 Estratégia {nome_clean}: {cache['estatisticas']['estrategias'][nome_clean]}")
        
        # ADICIONA AO HISTÓRICO LOCAL
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
        
        print(f"\n{'✅' if acertou else '❌'} PREVISÃO: {ultima['simbolo']} {ultima['previsao']} vs {resultado_real}")
        print(f"📊 Total: {cache['estatisticas']['acertos']}/{cache['estatisticas']['total_previsoes']} ({calcular_precisao()}%)")
        
        cache['ultima_previsao'] = None
        cache['ultimo_resultado_real'] = None

def calcular_precisao():
    total = cache['estatisticas']['total_previsoes']
    if total == 0:
        return 0
    return round((cache['estatisticas']['acertos'] / total) * 100)

# =============================================================================
# ATUALIZAÇÃO DE DADOS LEVES
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
    
    # 🔥 LOG PARA VERIFICAR SE AS ESTRATÉGIAS ESTÃO SENDO ENVIADAS
    print(f"📊 Enviando estratégias: {estrategias_stats}")
    
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
        'fontes': fontes_status,
        'estatisticas': {
            'total_previsoes': cache['estatisticas']['total_previsoes'],
            'acertos': cache['estatisticas']['acertos'],
            'erros': cache['estatisticas']['erros'],
            'precisao': calcular_precisao(),
            'ultimas_20_previsoes': cache['estatisticas']['ultimas_20_previsoes'],
            'estrategias': estrategias_stats
        }
    })

@app.route('/api/tabela/<int:limite>')
def api_tabela(limite):
    limite = min(max(limite, 50), 3000)
    conn = get_db_connection()
    if not conn:
        return jsonify([])
    
    cur = conn.cursor()
    cur.execute('SELECT data_hora, player_score, banker_score, resultado FROM rodadas ORDER BY data_hora DESC LIMIT %s', (limite,))
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

@app.route('/api/historico-previsoes')
def api_historico_previsoes():
    """Retorna o histórico de previsões do banco"""
    conn = get_db_connection()
    if not conn:
        return jsonify([])
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT data_hora, previsao, simbolo, confianca, resultado_real, acertou, estrategias, modo
            FROM historico_previsoes
            ORDER BY data_hora DESC
            LIMIT 50
        ''')
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        resultado = []
        for row in rows:
            brasilia = row[0].astimezone(timezone(timedelta(hours=-3)))
            resultado.append({
                'data': brasilia.strftime('%d/%m %H:%M:%S'),
                'previsao': row[1],
                'simbolo': row[2],
                'confianca': row[3],
                'resultado_real': row[4],
                'acertou': row[5],
                'estrategias': row[6].split(',') if row[6] else [],
                'modo': row[7]
            })
        
        return jsonify(resultado)
    except Exception as e:
        print(f"❌ Erro ao buscar histórico: {e}")
        return jsonify([]), 500

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'rodadas': cache['leves']['total_rodadas'],
        'fila': len(fila_rodadas),
        'fontes': fontes_status
    })

@app.route('/status-fontes')
def status_fontes():
    return jsonify(fontes_status)

# =============================================================================
# LOOP PESADO
# =============================================================================

def loop_pesado():
    while True:
        time.sleep(2)
        try:
            atualizar_dados_pesados()
        except Exception as e:
            print(f"❌ Erro loop pesado: {e}")

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("="*70)
    print("🚀 BOT BACBO - SISTEMA TURBO COM 3 FONTES (COMPLETO E CORRIGIDO)")
    print("="*70)
    print("✅ WebSocket: Tempo real (PRIORIDADE MÁXIMA)")
    print("✅ API Latest: Polling inteligente (PRIORIDADE MÉDIA)")
    print("✅ API Normal: Fallback histórico (PRIORIDADE BAIXA)")
    print("✅ Sistema anti-duplicação por ID (FUNCIONANDO!)")
    print("✅ 8 Estratégias completas (ATUALIZANDO!)")
    print("✅ Histórico de previsões no banco")
    print("="*70)
    
    

    init_db()
    
    print("🧹 Limpando duplicatas...")
    limpar_duplicatas()  # Executa uma vez para limpar o banco

    print("📊 Carregando dados...")
    atualizar_dados_leves()
    atualizar_dados_pesados()
    print(f"📊 {cache['leves']['total_rodadas']} rodadas no banco")
    print("="*70)
    
    # Inicia todas as fontes
    print("🔌 Iniciando WebSocket...")
    iniciar_websocket()
    
    print("📡 Iniciando coletor LATEST (2s)...")
    threading.Thread(target=loop_latest, daemon=True).start()
    
    print("📚 Iniciando coletor API NORMAL (10s fallback)...")
    threading.Thread(target=loop_api_normal, daemon=True).start()
    
    print("🚀 Iniciando processador da fila...")
    threading.Thread(target=processar_fila, daemon=True).start()
    
    print("🔄 Iniciando loop pesado (3s)...")
    threading.Thread(target=loop_pesado, daemon=True).start()
    
    print("✅ Servidor rodando!")
    print("📋 Acesse /status-fontes para ver status das 3 fontes")
    print("📋 Acesse /api/historico-previsoes para ver previsões salvas")
    app.run(host='0.0.0.0', port=PORT, debug=False)
