# main.py - SISTEMA COM API LATEST COMO FONTE PRINCIPAL
# ✅ API Latest: Fonte PRINCIPAL (envia para tabela)
# ✅ WebSocket: Backup quando Latest falha
# ✅ API Normal: Fallback quando todos falham + CARGA HISTÓRICA
# ✅ Alternância automática entre fontes
# ✅ 8 Estratégias completas com aprendizado
# ✅ Histórico de previsões no banco
# ✅ Carga histórica automática na primeira execução

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
DATABASE_URL = "postgresql://neondb_owner:npg_l4nHebCWvok8@ep-old-field-adcep1b1-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
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

# FONTE 1: API Latest (PRINCIPAL - envia para tabela)
LATEST_API_URL = "https://api-cs.casino.org/svc-evolution-game-events/api/bacbo/latest"

# FONTE 2: WebSocket (Backup - quando Latest falha)
WS_URL = "wss://api-cs.casino.org/svc-evolution-game-events/ws/bacbo"

# FONTE 3: API Normal (Fallback - quando todos falham + CARGA HISTÓRICA)
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
INTERVALO_LATEST = 0.3  # 0.3 segundo para /latest (PRINCIPAL)
INTERVALO_WS_FALLBACK = 3  # 1 segundo para WebSocket (backup)
INTERVALO_NORMAL_FALLBACK = 10  # 10 segundos para API normal (último recurso)
PORT = int(os.environ.get("PORT", 5000))

# =============================================================================
# CONTROLE DE FALHAS
# =============================================================================
falhas_latest = 0
falhas_websocket = 0
falhas_api_normal = 0
LIMITE_FALHAS = 3  # Número de falhas consecutivas para trocar de fonte

# Status das fontes
fontes_status = {
    'latest': {'status': 'ativo', 'total': 0, 'falhas': 0, 'prioridade': 1},
    'websocket': {'status': 'standby', 'total': 0, 'falhas': 0, 'prioridade': 2},
    'api_normal': {'status': 'standby', 'total': 0, 'falhas': 0, 'prioridade': 3}
}

fonte_ativa = 'latest'  # Fonte atual que está enviando dados

# =============================================================================
# FILA DE PROCESSAMENTO
# =============================================================================
fila_rodadas = deque(maxlen=500)
ultimo_id_latest = None
ultimo_id_websocket = None
ultimo_id_api = None

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
        print(f"⚠️ Ergo get_ultimas_20: {e}")
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
# 🔥 FUNÇÃO PARA ALTERNAR FONTE ATIVA
# =============================================================================

def alternar_fonte():
    """Alterna para a próxima fonte disponível"""
    global fonte_ativa, falhas_latest, falhas_websocket, falhas_api_normal
    
    if fonte_ativa == 'latest' and falhas_latest >= LIMITE_FALHAS:
        print(f"\n⚠️ LATEST falhou {falhas_latest} vezes - Alternando para WEBSOCKET")
        fonte_ativa = 'websocket'
        fontes_status['latest']['status'] = 'falha'
        fontes_status['websocket']['status'] = 'ativo'
        
    elif fonte_ativa == 'websocket' and falhas_websocket >= LIMITE_FALHAS:
        print(f"\n⚠️ WEBSOCKET falhou {falhas_websocket} vezes - Alternando para API NORMAL")
        fonte_ativa = 'api_normal'
        fontes_status['websocket']['status'] = 'falha'
        fontes_status['api_normal']['status'] = 'ativo'
        
    elif fonte_ativa == 'api_normal' and falhas_api_normal >= LIMITE_FALHAS:
        print(f"\n⚠️ Todas as fontes falharam - Tentando reiniciar ciclo")
        # Reseta contadores e tenta tudo novamente
        falhas_latest = 0
        falhas_websocket = 0
        falhas_api_normal = 0
        fonte_ativa = 'latest'
        fontes_status['latest']['status'] = 'ativo'
        fontes_status['websocket']['status'] = 'standby'
        fontes_status['api_normal']['status'] = 'standby'

# =============================================================================
# 🔥 FONTE 1: API LATEST (PRINCIPAL)
# =============================================================================

def buscar_latest():
    """Busca apenas a última rodada - FONTE PRINCIPAL"""
    global ultimo_id_latest, falhas_latest, fonte_ativa
    
    try:
        response = requests.get(LATEST_API_URL, headers=HEADERS, timeout=3)
        
        if response.status_code == 200:
            dados = response.json()
            
            novo_id = dados.get('id')
            data = dados.get('data', {})
            result = data.get('result', {})
            
            if novo_id and novo_id != ultimo_id_latest:
                # Reset contador de falhas quando funciona
                if fonte_ativa == 'latest':
                    falhas_latest = 0
                
                ultimo_id_latest = novo_id
                
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
                
                fontes_status['latest']['total'] += 1
                print(f"\n📡 [PRINCIPAL] LATEST: {player_score} vs {banker_score} - {resultado}")
                return rodada
            else:
                # Mesmo ID, mas não é falha - apenas sem novidades
                return None
        else:
            # Incrementa falhas apenas se for a fonte ativa
            if fonte_ativa == 'latest':
                falhas_latest += 1
                fontes_status['latest']['falhas'] += 1
                print(f"⚠️ LATEST falha {falhas_latest}/{LIMITE_FALHAS} (Status: {response.status_code})")
                alternar_fonte()
            return None
            
    except Exception as e:
        if fonte_ativa == 'latest':
            falhas_latest += 1
            fontes_status['latest']['falhas'] += 1
            print(f"⚠️ LATEST erro: {e} - falha {falhas_latest}/{LIMITE_FALHAS}")
            alternar_fonte()
        return None

# =============================================================================
# 🔥 FONTE 2: WEBSOCKET (BACKUP)
# =============================================================================

def on_ws_message(ws, message):
    """Recebe mensagens do WebSocket - USADO COMO BACKUP"""
    global ultimo_id_websocket, falhas_websocket, fonte_ativa
    
    try:
        data = json.loads(message)
        
        if 'data' in data and 'result' in data['data']:
            game_data = data['data']
            result = game_data['result']
            
            novo_id = game_data.get('id')
            
            if novo_id and novo_id != ultimo_id_websocket:
                # Se o WebSocket está funcionando e é a fonte ativa
                if fonte_ativa == 'websocket':
                    falhas_websocket = 0
                
                ultimo_id_websocket = novo_id
                
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
                
                fontes_status['websocket']['total'] += 1
                
                # Só adiciona à fila se for a fonte ativa
                if fonte_ativa == 'websocket':
                    fila_rodadas.append(rodada)
                    print(f"\n⚡ [BACKUP] WEBSOCKET: {player_score} vs {banker_score} - {resultado}")
                
    except Exception as e:
        print(f"⚠️ Erro WS: {e}")

def on_ws_error(ws, error):
    global falhas_websocket, fonte_ativa
    if fonte_ativa == 'websocket':
        falhas_websocket += 1
        fontes_status['websocket']['falhas'] += 1
        print(f"🔌 WS Erro: {error} - falha {falhas_websocket}/{LIMITE_FALHAS}")
        alternar_fonte()

def on_ws_close(ws, close_status_code, close_msg):
    global falhas_websocket, fonte_ativa
    if fonte_ativa == 'websocket':
        falhas_websocket += 1
        fontes_status['websocket']['falhas'] += 1
        print(f"🔌 WS Fechado - falha {falhas_websocket}/{LIMITE_FALHAS}")
        alternar_fonte()
    time.sleep(5)
    iniciar_websocket()

def on_ws_open(ws):
    global falhas_websocket, fonte_ativa
    print("✅ WEBSOCKET CONECTADO! (modo backup)")
    if fonte_ativa == 'websocket':
        falhas_websocket = 0

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
# 🔥 FONTE 3: API NORMAL (FALLBACK FINAL + CARGA HISTÓRICA)
# =============================================================================

def buscar_api_normal():
    """Busca histórico da API normal - ÚLTIMO RECURSO"""
    global ultimo_id_api, falhas_api_normal, fonte_ativa
    
    try:
        params = API_PARAMS.copy()
        params['_t'] = int(time.time() * 1000)
        
        response = session.get(API_URL, params=params, timeout=TIMEOUT_API)
        response.raise_for_status()
        dados = response.json()
        
        if dados and len(dados) > 0:
            primeiro = dados[0]
            data = primeiro.get('data', {})
            novo_id = data.get('id')
            
            if novo_id and novo_id != ultimo_id_api:
                if fonte_ativa == 'api_normal':
                    falhas_api_normal = 0
                
                ultimo_id_api = novo_id
                
                rodadas = []
                for item in dados[:5]:
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
                
                fontes_status['api_normal']['total'] += len(rodadas)
                
                if fonte_ativa == 'api_normal':
                    print(f"\n📚 [FALLBACK] API NORMAL: {len(rodadas)} rodadas")
                    return rodadas
        
        return None
        
    except Exception as e:
        if fonte_ativa == 'api_normal':
            falhas_api_normal += 1
            fontes_status['api_normal']['falhas'] += 1
            print(f"⚠️ API Normal erro - falha {falhas_api_normal}/{LIMITE_FALHAS}")
            alternar_fonte()
        return None

# =============================================================================
# 🔥 FUNÇÃO PARA CARREGAR HISTÓRICO COMPLETO (TUDO QUE A API NORMAL TIVER)
# =============================================================================

def carregar_historico_completo():
    """Carrega TODO o histórico disponível da API Normal"""
    print("\n📚 INICIANDO CARGA HISTÓRICA COMPLETA...")
    print("⏳ Isso pode levar alguns minutos...")
    
    conn = get_db_connection()
    if not conn:
        print("❌ Erro ao conectar ao banco")
        return
    
    try:
        cur = conn.cursor()
        
        # Verifica quantas rodadas já temos
        cur.execute('SELECT COUNT(*) FROM rodadas')
        total_existente = cur.fetchone()[0]
        print(f"📊 Rodadas existentes: {total_existente}")
        
        page = 0
        total_carregadas = 0
        pagina_sem_novidades = 0
        
        while pagina_sem_novidades < 3:  # Para depois de 3 páginas sem novidades
            params = API_PARAMS.copy()
            params['page'] = page
            params['_t'] = int(time.time() * 1000)
            
            try:
                print(f"\n📥 Buscando página {page}...")
                response = session.get(API_URL, params=params, timeout=TIMEOUT_API)
                response.raise_for_status()
                dados = response.json()
                
                if not dados or len(dados) == 0:
                    print(f"✅ Fim das páginas na página {page}")
                    break
                
                print(f"   → Página {page}: {len(dados)} rodadas")
                
                novas_na_pagina = 0
                for item in dados:
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
                        
                        # Insere no banco
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
                            'historico',
                            json.dumps(rodada, default=str)
                        ))
                        
                        if cur.rowcount > 0:
                            novas_na_pagina += 1
                            
                    except Exception as e:
                        continue
                
                conn.commit()
                total_carregadas += novas_na_pagina
                
                if novas_na_pagina > 0:
                    print(f"   ✅ +{novas_na_pagina} novas rodadas (acumulado: {total_carregadas})")
                    pagina_sem_novidades = 0
                else:
                    print(f"   ⏭️ Nenhuma rodada nova nesta página")
                    pagina_sem_novidades += 1
                
                page += 1
                time.sleep(0.5)  # Pausa entre páginas
                
            except Exception as e:
                print(f"⚠️ Erro na página {page}: {e}")
                break
        
        cur.close()
        conn.close()
        
        print("\n" + "="*50)
        print("📊 CARGA HISTÓRICA CONCLUÍDA!")
        print(f"✅ Total de novas rodadas: {total_carregadas}")
        print(f"📈 Total no banco agora: {total_existente + total_carregadas}")
        print("="*50)
        
    except Exception as e:
        print(f"❌ Erro na carga histórica: {e}")

# =============================================================================
# 🔥 LOOP DE COLETA - APENAS FONTE ATIVA ENVIA
# =============================================================================

def loop_latest():
    """Loop da fonte Latest (PRINCIPAL)"""
    print("📡 [PRINCIPAL] Coletor LATEST iniciado (0.1s)...")
    while True:
        try:
            if fonte_ativa == 'latest':
                rodada = buscar_latest()
                if rodada:
                    fila_rodadas.append(rodada)
            time.sleep(INTERVALO_LATEST)
        except Exception as e:
            print(f"❌ Erro no loop LATEST: {e}")
            time.sleep(INTERVALO_LATEST)

def loop_websocket_fallback():
    """Loop para verificar WebSocket (executa sempre, mas só envia se for ativo)"""
    print("⚡ [BACKUP] Monitor WebSocket iniciado...")
    while True:
        try:
            # O WebSocket já é assíncrono, esse loop só mantém a thread viva
            time.sleep(1)
        except Exception as e:
            print(f"❌ Erro no monitor WS: {e}")
            time.sleep(1)

def loop_api_fallback():
    """Loop da API Normal (FALLBACK)"""
    print("📚 [FALLBACK] Coletor API NORMAL iniciado (10s)...")
    while True:
        try:
            if fonte_ativa == 'api_normal':
                rodadas = buscar_api_normal()
                if rodadas:
                    for rodada in rodadas:
                        fila_rodadas.append(rodada)
            time.sleep(INTERVALO_NORMAL_FALLBACK)
        except Exception as e:
            print(f"❌ Erro API Normal: {e}")
            time.sleep(INTERVALO_NORMAL_FALLBACK)

# =============================================================================
# 🔥 PROCESSADOR DA FILA
# =============================================================================

def processar_fila():
    """Processa a fila"""
    print("🚀 Processador TURBO iniciado...")
    
    while True:
        try:
            if fila_rodadas:
                batch = list(fila_rodadas)
                fila_rodadas.clear()
                
                saved = 0
                for rodada in batch:
                    if salvar_rodada(rodada, 'principal'):
                        saved += 1
                        cache['ultimo_resultado_real'] = rodada['resultado']
                        print(f"✅ SALVO: {rodada['player_score']} vs {rodada['banker_score']} - {rodada['resultado']}")
                
                if saved > 0:
                    print(f"💾 Processadas {saved} rodadas")
                    atualizar_dados_leves()
            
            time.sleep(0.01)
            
        except Exception as e:
            print(f"❌ Erro TURBO: {e}")
            time.sleep(0.1)

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
    if len(dados) < 5:
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
        
        salvar_previsao(ultima, resultado_real, acertou)
        
        cache['estatisticas']['total_previsoes'] += 1
        if acertou:
            cache['estatisticas']['acertos'] += 1
        else:
            cache['estatisticas']['erros'] += 1
        
        for estrategia in ultima.get('estrategias', []):
            nome_clean = estrategia.split(' ')[0]
            
            if nome_clean not in cache['estatisticas']['estrategias']:
                cache['estatisticas']['estrategias'][nome_clean] = {'acertos': 0, 'erros': 0, 'total': 0}
            
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
        
        print(f"\n{'✅' if acertou else '❌'} PREVISÃO: {ultima['simbolo']} {ultima['previsao']} vs {resultado_real}")
        
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
        'fonte_ativa': fonte_ativa,
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

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'rodadas': cache['leves']['total_rodadas'],
        'fila': len(fila_rodadas),
        'fonte_ativa': fonte_ativa
    })

@app.route('/status-fontes')
def status_fontes():
    return jsonify({
        'fonte_ativa': fonte_ativa,
        'fontes': fontes_status,
        'falhas': {
            'latest': falhas_latest,
            'websocket': falhas_websocket,
            'api_normal': falhas_api_normal
        }
    })

# =============================================================================
# LOOP PESADO
# =============================================================================

def loop_pesado():
    while True:
        time.sleep(0.3)
        try:
            atualizar_dados_pesados()
        except Exception as e:
            print(f"❌ Erro loop pesado: {e}")

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("="*70)
    print("🚀 BOT BACBO - API LATEST COMO FONTE PRINCIPAL + CARGA HISTÓRICA")
    print("="*70)
    print("✅ [PRINCIPAL] API Latest: Envia para tabela (0.1s)")
    print("✅ [BACKUP] WebSocket: Ativado quando Latest falha")
    print("✅ [FALLBACK] API Normal: Último recurso + CARGA HISTÓRICA")
    print("✅ Alternância automática entre fontes")
    print("✅ 8 Estratégias completas")
    print("✅ Histórico de previsões no banco")
    print("="*70)
    
    init_db()
    
    # 📚 CARREGAR HISTÓRICO COMPLETO (APENAS NA PRIMEIRA EXECUÇÃO)
    carregar_historico_completo()
    
    print("📊 Carregando dados...")
    atualizar_dados_leves()
    atualizar_dados_pesados()
    print(f"📊 {cache['leves']['total_rodadas']} rodadas no banco")
    print("="*70)
    
    # Inicia todas as fontes (mas só a ativa envia)
    print("🔌 Iniciando WebSocket (modo backup)...")
    iniciar_websocket()
    
    print("📡 [PRINCIPAL] Iniciando coletor LATEST (0.3s)...")
    threading.Thread(target=loop_latest, daemon=True).start()
    
    print("⚡ Iniciando monitor WebSocket...")
    threading.Thread(target=loop_websocket_fallback, daemon=True).start()
    
    print("📚 [FALLBACK] Iniciando coletor API NORMAL (10s)...")
    threading.Thread(target=loop_api_fallback, daemon=True).start()
    
    print("🚀 Iniciando processador da fila...")
    threading.Thread(target=processar_fila, daemon=True).start()
    
    print("🔄 Iniciando loop pesado (0.1s)...")
    threading.Thread(target=loop_pesado, daemon=True).start()
    
    print("✅ Servidor rodando!")
    print("📋 Acesse /status-fontes para ver qual fonte está ativa")
    app.run(host='0.0.0.0', port=PORT, debug=False)
