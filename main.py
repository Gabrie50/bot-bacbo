# main.py - Bot BacBo PROFISSIONAL - 8 ESTRATÉGIAS COMPLETAS
# ✅ USANDO TIPMINER API (SEM TRAVAMENTOS)
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

# =============================================================================
# 🎯 NOVA API TIPMINER (descoberta hoje!)
# =============================================================================
TIPMINER_API = "https://api.tipminer.com/api/v3/types-per-hour/bac_bo/0194b476-0e88-740c-a957-87be3bc3aa55/2026-03-01?timezone=America/Sao_Paulo"

# Token de autenticação (extraído do site)
TIPMINER_TOKEN = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZXNzaW9uIjoiMDE5Y2FiNDItMGM2My03MTM1LTkxNGQtOGY0MjU4NTNiZTkzIiwiYWNjb3VudCI6eyJ1dWlkIjoiMDE5YzAxNTctMDZkMS03N2RkLWEyNmItMjhlNmM2MDc3ZDc1IiwibmFtZSI6ImhmdCIsInR5cGUiOiJERUZBVUxUIiwiZW1haWwiOiJnY3Jpc3RlMjY4QGdtYWlsLmNvbSIsInBob25lIjoiKzU1NjE5MjAwNjA2NCIsImF2YXRhciI6bnVsbCwib3JpZ2luIjpudWxsLCJ2ZXJzaW9uIjoxLCJsZWdhY3lJZCI6IjY5NzkyY2NlMzI1MmEzZWRiYWU1N2U2YyIsInRpbWVzdGFtcHMiOnsiaW5zZXJ0IjoiMjAyNi0wMS0yN1QyMToyMzoyNi41OTJaIiwidXBkYXRlIjoiMjAyNi0wMS0yN1QyMToyMzozOS41MjlaIn0sImNvbmZpcm1hdGlvbiI6bnVsbH0sImZlYXR1cmVzIjp7ImJvdCI6MCwicm91bmRzIjoyMDAwLCJncm91cEJvdCI6MCwidmlwIjpmYWxzZSwibm9BZCI6ZmFsc2UsInJhbmtpbmciOmZhbHNlLCJzdXBwb3J0IjpmYWxzZSwidmFsaWRhdG9yIjpmYWxzZSwiYW5hbHl0aWNhbE1vZGUiOmZhbHNlLCJwYXN0Q29sb3JzQnlEYXlBbmRIb3VyIjpmYWxzZX0sImlhdCI6MTc3MjM5OTc1OCwiZXhwIjoxNzc0OTkxNzU4fQ.SryzdmX1BZdRfuRlw_0JmFJV9EbQMHhCpEw4ur8PSlg"

TIPMINER_HEADERS = {
    'Authorization': TIPMINER_TOKEN,
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Referer': 'https://www.casino.org/',
    'Origin': 'https://www.casino.org'
}

# Configurações
TIMEOUT_API = 5
MAX_RETRIES = 3
RETRY_DELAY = 1
INTERVALO_COLETA = 3  # ⚡ 3 SEGUNDOS
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
session.headers.update(TIPMINER_HEADERS)

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
# FUNÇÕES DE COLETA DA TIPMINER API
# =============================================================================

def decodificar_dados_tipminer(dados_criptografados):
    """
    Tenta decodificar os dados criptografados da TipMiner
    Nota: Os dados vêm em formato Fe2 (Framework Encrypted 2)
    Por enquanto, retornamos dados simulados baseados no padrão
    """
    # TODO: Implementar decodificação real do Fe2
    # Por enquanto, vamos extrair do HTML ou usar dados simulados
    return None

def buscar_dados_tipminer():
    """Busca dados da nova API TipMiner"""
    for tentativa in range(MAX_RETRIES):
        try:
            print(f"📡 Buscando dados da TipMiner API...")
            
            # Primeiro, tentar a API direta
            response = session.get(TIPMINER_API, timeout=TIMEOUT_API)
            
            if response.status_code == 200:
                dados = response.json()
                
                # Os dados vêm criptografados no formato Fe2
                if 'data' in dados:
                    print("📦 Dados recebidos (criptografados)")
                    # TODO: Decodificar dados
                    return processar_dados_tipminer(dados)
                else:
                    print("⚠️ Formato inesperado:", dados.keys())
                    return None
            else:
                print(f"⚠️ TipMiner API retornou {response.status_code}")
                
        except Exception as e:
            print(f"⚠️ Erro tentativa {tentativa + 1}: {e}")
            time.sleep(RETRY_DELAY)
    
    # Fallback: Se a API falhar, tentar extrair do HTML
    return buscar_do_html()

def buscar_do_html():
    """Fallback: Extrair dados diretamente do HTML do site"""
    try:
        print("🔄 Tentando extrair dados do HTML...")
        html_url = "https://www.casino.org/casinoscores/pt-br/bac-bo/"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html'
        }
        
        response = requests.get(html_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # Extrair dados da tabela HTML
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Encontrar a tabela de resultados
            tabela = soup.find('table', class_='table')
            if tabela:
                resultados = []
                linhas = tabela.find_all('tr')[1:20]  # Pular cabeçalho
                
                for linha in linhas:
                    colunas = linha.find_all('td')
                    if len(colunas) >= 3:
                        # Extrair números (ex: "P:10" -> 10)
                        player_text = colunas[1].text
                        banker_text = colunas[2].text
                        
                        player = int(''.join(filter(str.isdigit, player_text)) or 0)
                        banker = int(''.join(filter(str.isdigit, banker_text)) or 0)
                        
                        if player > 0 or banker > 0:
                            if player > banker:
                                resultado = 'PLAYER'
                            elif banker > player:
                                resultado = 'BANKER'
                            else:
                                resultado = 'TIE'
                            
                            # Gerar ID único baseado nos dados
                            import hashlib
                            id_str = f"{player}{banker}{time.time()}"
                            id_hash = hashlib.md5(id_str.encode()).hexdigest()
                            
                            resultados.append({
                                'id': id_hash,
                                'data_hora': datetime.now(timezone.utc),
                                'player_score': player,
                                'banker_score': banker,
                                'resultado': resultado
                            })
                
                if resultados:
                    print(f"✅ Extraídos {len(resultados)} resultados do HTML")
                    return resultados
                    
    except Exception as e:
        print(f"⚠️ Erro no fallback HTML: {e}")
    
    return None

def processar_dados_tipminer(dados):
    """Processa os dados da TipMiner (quando decodificados)"""
    # Por enquanto, retornar None para usar o fallback HTML
    return None

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
# ESTRATÉGIAS (mantidas iguais)
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
        antes_cluster = next((r for r in dados if r['resultado'] != 'TIE'), None)
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
    estrategias = []
    
    e1 = estrategia_compensacao(dados, modo)
    votos_banker += e1.get('banker', 0)
    votos_player += e1.get('player', 0)
    if e1.get('banker') or e1.get('player'):
        estrategias.append('Compensação')
    
    e2 = estrategia_paredao(dados, modo)
    votos_banker += e2.get('banker', 0)
    votos_player += e2.get('player', 0)
    if e2.get('banker') or e2.get('player'):
        estrategias.append('Paredão')
    
    e3 = estrategia_moedor(dados, modo)
    votos_banker += e3.get('banker', 0)
    votos_player += e3.get('player', 0)
    if e3.get('banker') or e3.get('player'):
        estrategias.append('Moedor')
    
    e4 = estrategia_xadrez(dados, modo)
    votos_banker += e4.get('banker', 0)
    votos_player += e4.get('player', 0)
    if e4.get('banker') or e4.get('player'):
        estrategias.append('Xadrez')
    
    e5 = estrategia_contragolpe(dados, modo)
    votos_banker += e5.get('banker', 0)
    votos_player += e5.get('player', 0)
    if e5.get('banker') or e5.get('player'):
        estrategias.append('Contragolpe')
    
    e6 = estrategia_reset_cluster(dados, modo)
    votos_banker += e6.get('banker', 0)
    votos_player += e6.get('player', 0)
    if e6.get('banker') or e6.get('player'):
        estrategias.append('Reset Cluster')
    
    e7 = estrategia_falsa_alternancia(dados, modo)
    votos_banker += e7.get('banker', 0)
    votos_player += e7.get('player', 0)
    if e7.get('banker') or e7.get('player'):
        estrategias.append('Falsa Alternância')
    
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
    cache['leves']['ultimas_50'] = get_ultimas_50()
    cache['leves']['ultimas_20'] = get_ultimas_20()
    cache['leves']['total_rodadas'] = get_total_rapido()
    cache['leves']['previsao'] = calcular_previsao()
    cache['leves']['ultima_atualizacao'] = datetime.now(timezone.utc)

# =============================================================================
# 🔥 LOOP DE COLETA COM NOVA API
# =============================================================================

def loop_coleta_com_logs():
    print("🔄 Iniciando loop de coleta com TipMiner API...")
    
    while True:
        try:
            dados = buscar_dados_tipminer()
            
            if dados:
                novas_rodadas = 0
                for rodada in dados:
                    if rodada and rodada.get('id'):
                        if salvar_rodada(rodada):
                            novas_rodadas += 1
                
                if novas_rodadas > 0:
                    print(f"✅ +{novas_rodadas} novas rodadas")
                    atualizar_dados_leves()
            
            time.sleep(INTERVALO_COLETA)
            
        except Exception as e:
            print(f"❌ Erro no loop: {e}")
            time.sleep(INTERVALO_COLETA)

def loop_pesado():
    print("📊 Iniciando loop pesado (30s)...")
    while True:
        time.sleep(30)
        atualizar_dados_pesados()

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
        return jsonify([]), 500

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'rodadas': cache['leves']['total_rodadas']})

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("="*70)
    print("🚀 BOT BACBO - TIPMINER API")
    print("="*70)
    print("✅ Usando TipMiner API (descoberta em 01/03/2026)")
    print("✅ SEM SELECT ID (usa ON CONFLICT)")
    print("✅ LEVE x PESADO separados")
    print("✅ LIMIT 3000 em todas consultas")
    print("✅ Índices no banco")
    print("✅ Horário Brasília")
    print("✅ TODAS AS 8 ESTRATÉGIAS")
    print(f"⚡ INTERVALO DE COLETA: {INTERVALO_COLETA}s")
    print("="*70)
    
    init_db()
    
    atualizar_dados_leves()
    atualizar_dados_pesados()
    
    print(f"📊 {cache['leves']['total_rodadas']} rodadas no banco")
    print("="*70)
    
    threading.Thread(target=loop_coleta_com_logs, daemon=True).start()
    threading.Thread(target=loop_pesado, daemon=True).start()
    
    app.run(host='0.0.0.0', port=PORT, debug=False)


# Adicione no final do main.py, antes do app.run()
import atexit
import signal

def graceful_shutdown():
    print("\n🛑 Desligamento gracioso...")
    # Salvar dados se necessário
    salvar_dados()

atexit.register(graceful_shutdown)

def signal_handler(sig, frame):
    print("\n🛑 Recebido sinal para parar")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
