# main.py - Bot BacBo PROFISSIONAL - 8 ESTRATÉGIAS COMPLETAS
# ✅ SEM SELECT ID (usa ON CONFLICT)
# ✅ LEVE x PESADO separados
# ✅ LIMIT 3000 em todas consultas
# ✅ Índices no banco
# ✅ Horário Brasília
# ✅ TODAS AS 8 ESTRATÉGIAS IMPLEMENTADAS
# ⚡ INTERVALO DE COLETA: 3 SEGUNDOS

import os
import time
import requests
import json
import urllib.parse
import random
from datetime import datetime, timedelta, timezone
import sys
import threading
from flask import Flask, render_template, jsonify
from flask_cors import CORS
import pg8000
import pg8000.native

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

# API
API_URL = "https://api-cs.casino.org/svc-evolution-game-events/api/bacbo"
PARAMS = {
    "page": 0,
    "size": 50,
    "sort": "data.settledAt,desc",
    "duration": 4320,
    "wheelResults": "PlayerWon,BankerWon,Tie"
}
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json'
}

# =============================================================================
# CONFIGURAÇÕES DE PERFORMANCE (AJUSTADAS)
# =============================================================================
TIMEOUT_API = 5
MAX_RETRIES = 3
RETRY_DELAY = 1
INTERVALO_COLETA = 3  # ⚡ 3 SEGUNDOS (mais rápido)
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
    'falhas_consecutivas': 0,
    'ultimo_id': None
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
        
        # Verificar se inseriu
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
            return {'banker': 0, 'player': peso}  # Player precisa subir
        else:
            return {'banker': peso, 'player': 0}  # Banker precisa subir
    
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
    
    # Contar empates nas últimas 5 rodadas
    ties = sum(1 for r in dados[:5] if r['resultado'] == 'TIE')
    
    # Tie > 13% ou 2+ empates em 5 rodadas
    tie_pct = (ties / 5) * 100
    if tie_pct >= 13 or ties >= 2:
        # Encontrar última cor não-empate
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
            return {'banker': 0, 'player': peso}  # Próximo PLAYER
        else:
            return {'banker': peso, 'player': 0}  # Próximo BANKER
    
    return {'banker': 0, 'player': 0}

# =============================================================================
# ESTRATÉGIA #5: CONTRAGOLPE
# =============================================================================
def estrategia_contragolpe(dados, modo):
    """⚫ ESTRATÉGIA #5: CONTRAGOLPE - 3+ iguais → 1 diferente → volta"""
    if len(dados) < 5:
        return {'banker': 0, 'player': 0}
    
    # Pega últimas 5 rodadas
    seq = [r['resultado'] for r in dados[:5]]
    
    # Padrão: B,B,B,P,B ou P,P,P,B,P
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
    
    # Contar empates nas últimas 6 rodadas
    ties = sum(1 for r in dados[:6] if r['resultado'] == 'TIE')
    
    if ties >= 2:
        # Encontrar cor antes do cluster
        antes_cluster = None
        for r in dados:
            if r['resultado'] != 'TIE':
                antes_cluster = r
                break
        
        if antes_cluster:
            # 70% volta à dominante, 30% vai à oposta
            peso = PESOS['reset_cluster'][modo]
            if random.random() < 0.7:
                # Volta à dominante
                if antes_cluster['resultado'] == 'BANKER':
                    return {'banker': peso, 'player': 0}
                else:
                    return {'banker': 0, 'player': peso}
            else:
                # Vai à oposta
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
# ESTRATÉGIA #8: META-ALGORITMO (aplicado no final)
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
# FUNÇÃO PRINCIPAL DE PREVISÃO (COM TODAS AS 8 ESTRATÉGIAS)
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
    
    # ✅ ESTRATÉGIA 1: Compensação
    e1 = estrategia_compensacao(dados, modo)
    votos_banker += e1.get('banker', 0)
    votos_player += e1.get('player', 0)
    if e1.get('banker') or e1.get('player'):
        estrategias.append('Compensação')
    
    # ✅ ESTRATÉGIA 2: Paredão
    e2 = estrategia_paredao(dados, modo)
    votos_banker += e2.get('banker', 0)
    votos_player += e2.get('player', 0)
    if e2.get('banker') or e2.get('player'):
        estrategias.append('Paredão')
    
    # ✅ ESTRATÉGIA 3: Moedor
    e3 = estrategia_moedor(dados, modo)
    votos_banker += e3.get('banker', 0)
    votos_player += e3.get('player', 0)
    if e3.get('banker') or e3.get('player'):
        estrategias.append('Moedor')
    
    # ✅ ESTRATÉGIA 4: Xadrez
    e4 = estrategia_xadrez(dados, modo)
    votos_banker += e4.get('banker', 0)
    votos_player += e4.get('player', 0)
    if e4.get('banker') or e4.get('player'):
        estrategias.append('Xadrez')
    
    # ✅ ESTRATÉGIA 5: Contragolpe
    e5 = estrategia_contragolpe(dados, modo)
    votos_banker += e5.get('banker', 0)
    votos_player += e5.get('player', 0)
    if e5.get('banker') or e5.get('player'):
        estrategias.append('Contragolpe')
    
    # ✅ ESTRATÉGIA 6: Reset Pós-Cluster
    e6 = estrategia_reset_cluster(dados, modo)
    votos_banker += e6.get('banker', 0)
    votos_player += e6.get('player', 0)
    if e6.get('banker') or e6.get('player'):
        estrategias.append('Reset Cluster')
    
    # ✅ ESTRATÉGIA 7: Falsa Alternância
    e7 = estrategia_falsa_alternancia(dados, modo)
    votos_banker += e7.get('banker', 0)
    votos_player += e7.get('player', 0)
    if e7.get('banker') or e7.get('player'):
        estrategias.append('Falsa Alternância')
    
    # ✅ ESTRATÉGIA 8: Meta-Algoritmo
    if modo == "AGRESSIVO":
        if banker_pct > player_pct:
            votos_banker = int(votos_banker * 1.5)
            estrategias.append('Meta AGRESSIVO')
        else:
            votos_player = int(votos_player * 1.5)
            estrategias.append('Meta AGRESSIVO')
    elif modo == "PREDATORIO":
        # No modo predatório, dar peso extra para contragolpe e falsa alternância
        if any(s in estrategias for s in ['Contragolpe', 'Falsa Alternância']):
            if banker_pct > player_pct:
                votos_banker = int(votos_banker * 1.3)
            else:
                votos_player = int(votos_player * 1.3)
            estrategias.append('Meta PREDATÓRIO')
    
    # ✅ DECISÃO FINAL
    total_votos = votos_banker + votos_player
    
    if votos_banker > votos_player:
        previsao = 'BANKER'
        confianca = round((votos_banker / total_votos) * 100) if total_votos > 0 else 50
    elif votos_player > votos_banker:
        previsao = 'PLAYER'
        confianca = round((votos_player / total_votos) * 100) if total_votos > 0 else 50
    else:
        # Empate técnico: usar porcentagem do gráfico
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
        'estrategias': estrategias[:4]  # Mostra até 4 estratégias
    }

# =============================================================================
# FUNÇÕES DE ATUALIZAÇÃO
# =============================================================================

def atualizar_dados_leves():
    """⚡ Atualiza apenas dados leves (a cada nova rodada)"""
    cache['leves']['ultimas_50'] = get_ultimas_50()
    cache['leves']['ultimas_20'] = get_ultimas_20()
    cache['leves']['total_rodadas'] = get_total_rapido()
    cache['leves']['previsao'] = calcular_previsao()
    cache['leves']['ultima_atualizacao'] = datetime.now(timezone.utc)

# =============================================================================
# PROCESSAMENTO DA API
# =============================================================================

def processar_item_api(item):
    try:
        data = item.get('data', {})
        result = data.get('result', {})
        player_dice = result.get('playerDice', {})
        banker_dice = result.get('bankerDice', {})
        
        resultado_api = result.get('outcome', '')
        if resultado_api == 'PlayerWon':
            resultado = 'PLAYER'
        elif resultado_api == 'BankerWon':
            resultado = 'BANKER'
        else:
            resultado = 'TIE'

        data_hora = datetime.fromisoformat(data.get('settledAt', '').replace('Z', '+00:00'))

        return {
            'id': data.get('id'),
            'data_hora': data_hora,
            'player_score': player_dice.get('score', 0),
            'banker_score': banker_dice.get('score', 0),
            'resultado': resultado,
            'multiplicador': result.get('multiplier', 1),
            'total_winners': item.get('totalWinners', 0),
            'total_amount': item.get('totalAmount', 0)
        }
    except Exception as e:
        print(f"⚠️ Erro processar item: {e}")
        return None

def buscar_dados_api_com_retry():
    for tentativa in range(MAX_RETRIES):
        try:
            params = PARAMS.copy()
            params['page'] = 0
            params['size'] = 50
            response = session.get(API_URL, params=params, timeout=TIMEOUT_API)
            response.raise_for_status()
            cache['falhas_consecutivas'] = 0
            return response.json()
        except requests.exceptions.Timeout:
            print(f"⏱️ Timeout tentativa {tentativa + 1}")
            time.sleep(RETRY_DELAY)
        except Exception as e:
            print(f"⚠️ Erro tentativa {tentativa + 1}: {e}")
            time.sleep(RETRY_DELAY)
    
    cache['falhas_consecutivas'] += 1
    print(f"❌ Todas as {MAX_RETRIES} tentativas falharam")
    return None

# =============================================================================
# 🔥 LOOP DE COLETA COM LOGS DETALHADOS (INTERVALO 3s)
# =============================================================================

def loop_coleta_com_logs():
    """Loop principal com logs detalhados - INTERVALO 3s"""
    print("🔄 Iniciando loop de coleta com logs (intervalo 3s)...")
    ultimo_id = None
    ciclo = 0
    
    while True:
        try:
            ciclo += 1
            inicio_ciclo = time.time()
            dados = buscar_dados_api_com_retry()
            
            if dados:
                # Mostrar primeiro item se for novo
                if len(dados) > 0:
                    primeiro = dados[0]
                    data = primeiro.get('data', {})
                    result = data.get('result', {})
                    novo_id = data.get('id')
                    player = result.get('playerDice', {}).get('score')
                    banker = result.get('bankerDice', {}).get('score')
                    outcome = result.get('outcome', '')
                    
                    if novo_id and novo_id != ultimo_id:
                        print(f"\n📥 NOVA RODADA: {outcome} - {player} vs {banker}")
                        ultimo_id = novo_id
                
                novas_rodadas = 0
                for item in dados:
                    rodada = processar_item_api(item)
                    if rodada and rodada['id']:
                        if salvar_rodada(rodada):
                            novas_rodadas += 1
                
                if novas_rodadas > 0:
                    print(f"✅ +{novas_rodadas} novas rodadas")
                    atualizar_dados_leves()
            
            # Aguarda o intervalo configurado
            time.sleep(INTERVALO_COLETA)
            
        except Exception as e:
            print(f"❌ Erro no loop: {e}")
            time.sleep(INTERVALO_COLETA)

# =============================================================================
# 🔥 LOOP PESADO SEPARADO (a cada 30s)
# =============================================================================

def loop_pesado():
    """Loop separado para estatísticas pesadas"""
    print("📊 Iniciando loop pesado (30s)...")
    while True:
        time.sleep(30)
        atualizar_dados_pesados()
        print("📊 Estatísticas pesadas atualizadas")

# =============================================================================
# 🔥 ROTA DE DIAGNÓSTICO
# =============================================================================

@app.route('/diagnostico')
def diagnostico():
    """Mostra o status do sistema"""
    try:
        conn = get_db_connection()
        banco_ok = conn is not None
        total_banco = 0
        ultima_rodada = None
        
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
            
            if ultima:
                ultima_rodada = {
                    'data': ultima[0].strftime('%H:%M:%S'),
                    'player': ultima[1],
                    'banker': ultima[2],
                    'resultado': ultima[3]
                }

        return jsonify({
            'status': 'ok',
            'intervalo_coleta': INTERVALO_COLETA,
            'banco': {
                'conectado': banco_ok,
                'total_rodadas': total_banco,
                'cache': cache['leves']['total_rodadas']
            },
            'ultima_rodada': ultima_rodada,
            'cache': {
                'ultimas_50': len(cache['leves']['ultimas_50']),
                'ultima_atualizacao': str(cache['leves']['ultima_atualizacao'])
            }
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# =============================================================================
# 🔥 ROTA PARA FORÇAR COLETA
# =============================================================================

@app.route('/forcar-coleta')
def forcar_coleta():
    """Força coleta manual IMEDIATA"""
    try:
        dados = buscar_dados_api_com_retry()
        if not dados:
            return jsonify({'status': 'erro', 'mensagem': 'Sem dados da API'})
        
        novas = 0
        for item in dados:
            rodada = processar_item_api(item)
            if rodada and rodada['id']:
                if salvar_rodada(rodada):
                    novas += 1
        
        if novas > 0:
            atualizar_dados_leves()
            ultima = dados[0].get('data', {}).get('result', {})
            return jsonify({
                'status': 'ok', 
                'novas_rodadas': novas,
                'total_agora': cache['leves']['total_rodadas'],
                'ultima': f"{ultima.get('playerDice', {}).get('score')} vs {ultima.get('bankerDice', {}).get('score')} - {ultima.get('outcome')}"
            })
        else:
            return jsonify({'status': 'ok', 'mensagem': 'Nenhuma rodada nova'})
            
    except Exception as e:
        return jsonify({'status': 'erro', 'erro': str(e)}), 500

# =============================================================================
# ROTAS DA API (originais)
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

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("="*70)
    print("🚀 BOT BACBO - 8 ESTRATÉGIAS - INTERVALO 3s")
    print("="*70)
    print("✅ SEM SELECT ID (usa ON CONFLICT)")
    print("✅ LEVE x PESADO separados")
    print("✅ LIMIT 3000 em todas consultas")
    print("✅ Índices no banco")
    print("✅ Horário Brasília")
    print("✅ TODAS AS 8 ESTRATÉGIAS")
    print(f"⚡ INTERVALO DE COLETA: {INTERVALO_COLETA}s")
    print("="*70)
    
    init_db()
    
    # Dados iniciais
    print("📊 Carregando dados iniciais...")
    atualizar_dados_leves()
    atualizar_dados_pesados()
    
    print(f"📊 {cache['leves']['total_rodadas']} rodadas no banco")
    print("🌐 Rotas disponíveis:")
    print("   - /diagnostico - Ver status do sistema")
    print("   - /forcar-coleta - Forçar coleta manual")
    print("="*70)
    
    # Threads separadas
    print("🚀 Iniciando threads...")
    threading.Thread(target=loop_coleta_com_logs, daemon=True).start()
    threading.Thread(target=loop_pesado, daemon=True).start()
    
    print("✅ Servidor Flask iniciando...")
    app.run(host='0.0.0.0', port=PORT, debug=False)
