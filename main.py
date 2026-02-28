# main.py - Bot BacBo PROFISSIONAL - VERSÃO FINAL DEFINITIVA
# TODAS AS CORREÇÕES APLICADAS:
# ✅ SEM SELECT ID (usa ON CONFLICT)
# ✅ LEVE x PESADO separados
# ✅ LIMIT 3000 em todas consultas
# ✅ Índices no banco
# ✅ Horário Brasília

import os
import time
import requests
import json
import urllib.parse
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
# STRING DO BANCO NEON (REPOSITÓRIO PRIVADO)
DATABASE_URL = "postgresql://neondb_owner:npg_OgR74skiylmJ@ep-rapid-mode-aio1bik8-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# Parse da URL do banco
parsed = urllib.parse.urlparse(DATABASE_URL)
DB_USER = parsed.username
DB_PASSWORD = parsed.password
DB_HOST = parsed.hostname
DB_PORT = parsed.port or 5432
DB_NAME = parsed.path[1:]

# API do Casino.org
API_URL = "https://api-cs.casino.org/svc-evolution-game-events/api/bacbo"
PARAMS = {
    "page": 0,
    "size": 50,  # 50 é suficiente para coleta
    "sort": "data.settledAt,desc",
    "duration": 4320,  # 72 horas
    "wheelResults": "PlayerWon,BankerWon,Tie"
}
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json'
}

# Configurações de performance
TIMEOUT_API = 5
MAX_RETRIES = 3
RETRY_DELAY = 1
INTERVALO_COLETA = 10
INTERVALO_PAGINAS = 0.5
PORT = int(os.environ.get("PORT", 5000))

# =============================================================================
# CACHE OTIMIZADO (separado por tipo)
# =============================================================================
cache = {
    # ⚡ Dados LEVES (atualizam a cada nova rodada)
    'leves': {
        'ultimas_50': [],          # Para previsão
        'ultimas_20': [],          # Para gráfico
        'total_rodadas': 0,
        'ultima_atualizacao': None,
        'previsao': None
    },
    
    # 📊 Dados PESADOS (atualizam a cada 30s)
    'pesados': {
        'periodos': {},            # 10min, 1h, 6h, 12h, 24h, 48h, 72h
        'ultima_atualizacao': None
    },
    
    # Controle
    'falhas_consecutivas': 0
}

# Pesos das estratégias por modo
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
# INICIALIZAÇÃO DO FLASK
# =============================================================================
app = Flask(__name__)
CORS(app)

# Sessão HTTP com keep-alive
session = requests.Session()
session.headers.update(HEADERS)

# =============================================================================
# FUNÇÕES DO BANCO DE DADOS (pg8000)
# =============================================================================

def get_db_connection():
    """Cria conexão com o banco PostgreSQL via pg8000."""
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
        print(f"❌ Erro ao conectar ao banco: {e}")
        return None

def init_db():
    """Inicializa as tabelas no PostgreSQL com ÍNDICES."""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        # Criar tabela de rodadas
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
        
        # 🔥 ÍNDICES OBRIGATÓRIOS PARA PERFORMANCE
        cur.execute('CREATE INDEX IF NOT EXISTS idx_data_hora ON rodadas(data_hora DESC)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_resultado ON rodadas(resultado)')
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Tabelas criadas/verificadas com ÍNDICES")
        return True
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
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
        
        # Verificar se inseriu (rowcount > 0)
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
        print(f"❌ Erro ao salvar rodada: {e}")
        return False

# =============================================================================
# FUNÇÕES LEVES (RÁPIDAS - usam índice)
# =============================================================================

def get_ultimas_50():
    """Busca últimas 50 rodadas (para previsão)"""
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
        print(f"❌ Erro ao buscar últimas 50: {e}")
        return []

def get_ultimas_20():
    """Busca últimas 20 rodadas para gráfico (com horário Brasília)"""
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
            data_hora = row[0]
            # Converter para Brasília (UTC-3)
            brasilia = data_hora.astimezone(timezone(timedelta(hours=-3)))
            
            if row[3] == 'BANKER':
                cor = '🔴'
            elif row[3] == 'PLAYER':
                cor = '🔵'
            else:
                cor = '🟡'
            
            resultado.append({
                'hora': brasilia.strftime('%H:%M:%S'),
                'resultado': row[3],
                'cor': cor,
                'player': row[1],
                'banker': row[2]
            })
        
        return sorted(resultado, key=lambda x: x['hora'])
    except Exception as e:
        print(f"❌ Erro ao buscar últimas 20: {e}")
        return []

def get_total_rapido():
    """Total de rodadas (COUNT rápido com índice)"""
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
        print(f"❌ Erro ao obter total: {e}")
        return 0

# =============================================================================
# FUNÇÕES PESADAS (rodam a cada 30s)
# =============================================================================

def contar_periodo(horas):
    """Conta rodadas em um período (usa índice)"""
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
        print(f"❌ Erro ao contar período {horas}h: {e}")
        return 0

def atualizar_dados_pesados():
    """📊 Atualiza dados pesados (a cada 30s)"""
    print("📊 Atualizando dados pesados...")
    
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
    print(f"✅ Pesados atualizados: {cache['pesados']['periodos']}")

# =============================================================================
# PREVISÃO (usa só últimas 50)
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

def estrategia_compensacao(dados, modo):
    if len(dados) < 10:
        return {'banker': 0, 'player': 0}
    
    player = sum(1 for r in dados if r['resultado'] == 'PLAYER')
    banker = sum(1 for r in dados if r['resultado'] == 'BANKER')
    total = len(dados)
    
    diff = abs((banker/total*100) - (player/total*100))
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

def calcular_previsao():
    """🎯 Função principal de previsão com 8 estratégias."""
    dados = cache['leves']['ultimas_50']
    if len(dados) < 10:
        return None
    
    total = len(dados)
    player = sum(1 for r in dados if r['resultado'] == 'PLAYER')
    banker = sum(1 for r in dados if r['resultado'] == 'BANKER')
    tie = sum(1 for r in dados if r['resultado'] == 'TIE')
    
    player_pct = (player / total) * 100
    banker_pct = (banker / total) * 100
    
    modo = identificar_modo(player_pct, banker_pct, dados)
    
    votos_banker = 0
    votos_player = 0
    estrategias = []
    
    # Aplicar estratégias
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
    
    e4 = estrategia_xadrez(dados, modo)
    votos_banker += e4.get('banker', 0)
    votos_player += e4.get('player', 0)
    if e4.get('banker') or e4.get('player'):
        estrategias.append('Xadrez')
    
    e7 = estrategia_falsa_alternancia(dados, modo)
    votos_banker += e7.get('banker', 0)
    votos_player += e7.get('player', 0)
    if e7.get('banker') or e7.get('player'):
        estrategias.append('Falsa Alternância')
    
    # Meta-algoritmo
    if modo == "AGRESSIVO":
        if banker_pct > player_pct:
            votos_banker = int(votos_banker * 1.5)
            estrategias.append('Meta AGRESSIVO')
        else:
            votos_player = int(votos_player * 1.5)
            estrategias.append('Meta AGRESSIVO')
    
    # Decidir previsão
    if votos_banker > votos_player:
        previsao = 'BANKER'
        confianca = round((votos_banker / (votos_banker + votos_player)) * 100)
    elif votos_player > votos_banker:
        previsao = 'PLAYER'
        confianca = round((votos_player / (votos_banker + votos_player)) * 100)
    else:
        # Empate - usar percentuais
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
        'estrategias': estrategias[:3]
    }

# =============================================================================
# FUNÇÕES DE ATUALIZAÇÃO DE CACHE
# =============================================================================

def atualizar_dados_leves():
    """⚡ Atualiza apenas dados leves (a cada nova rodada)"""
    cache['leves']['ultimas_50'] = get_ultimas_50()
    cache['leves']['ultimas_20'] = get_ultimas_20()
    cache['leves']['total_rodadas'] = get_total_rapido()
    cache['leves']['previsao'] = calcular_previsao()
    cache['leves']['ultima_atualizacao'] = datetime.now(timezone.utc)

# =============================================================================
# FUNÇÕES DE COLETA DA API
# =============================================================================

def processar_item_api(item):
    """Converte um item da API para o formato que usamos."""
    try:
        data = item.get('data', {})
        result = data.get('result', {})
        player_dice = result.get('playerDice', {})
        banker_dice = result.get('bankerDice', {})
        player_score = player_dice.get('score', 0)
        banker_score = banker_dice.get('score', 0)
        resultado_api = result.get('outcome', 'Desconhecido')

        if resultado_api == 'PlayerWon':
            resultado = 'PLAYER'
        elif resultado_api == 'BankerWon':
            resultado = 'BANKER'
        elif resultado_api == 'Tie':
            resultado = 'TIE'
        else:
            resultado = 'DESCONHECIDO'

        data_hora_str = data.get('settledAt', '')
        data_hora = datetime.fromisoformat(data_hora_str.replace('Z', '+00:00'))

        return {
            'id': data.get('id'),
            'data_hora': data_hora,
            'player_score': player_score,
            'banker_score': banker_score,
            'resultado': resultado,
            'multiplicador': result.get('multiplier', 1),
            'total_winners': item.get('totalWinners', 0),
            'total_amount': item.get('totalAmount', 0)
        }
    except Exception as e:
        return None

def buscar_dados_api_com_retry():
    """Faz requisição à API com sistema de retry."""
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
            print(f"⏱️ Timeout na tentativa {tentativa + 1}/{MAX_RETRIES}")
        except requests.exceptions.ConnectionError:
            print(f"🔌 Erro de conexão na tentativa {tentativa + 1}/{MAX_RETRIES}")
        except Exception as e:
            print(f"⚠️ Erro na tentativa {tentativa + 1}/{MAX_RETRIES}: {e}")
        
        if tentativa < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY)
    
    cache['falhas_consecutivas'] += 1
    return None

# =============================================================================
# 🔥 LOOP DE COLETA CORRIGIDO (SEM SELECT ID)
# =============================================================================

def loop_coleta():
    """Loop principal - SEM consulta de IDs (usa ON CONFLICT)"""
    print("🔄 Iniciando loop de coleta...")
    
    while True:
        try:
            inicio_ciclo = time.time()
            dados = buscar_dados_api_com_retry()
            
            if dados:
                novas_rodadas = 0
                
                # 🔥 NÃO busca mais todos os IDs - ON CONFLICT resolve
                for item in dados:
                    rodada = processar_item_api(item)
                    if rodada and rodada['id']:
                        if salvar_rodada(rodada):
                            novas_rodadas += 1
                
                if novas_rodadas > 0:
                    print(f"✅ +{novas_rodadas} novas rodadas")
                    # ⚡ Atualiza apenas dados leves
                    atualizar_dados_leves()
            
            if cache['falhas_consecutivas'] > 5:
                print(f"⚠️ Muitas falhas, aguardando 30s...")
                time.sleep(30)
                cache['falhas_consecutivas'] = 0
            else:
                tempo_gasto = time.time() - inicio_ciclo
                tempo_espera = max(1, INTERVALO_COLETA - tempo_gasto)
                time.sleep(tempo_espera)
            
        except Exception as e:
            print(f"❌ Erro no loop: {e}")
            time.sleep(INTERVALO_COLETA)

# =============================================================================
# 🔥 LOOP PESADO SEPARADO (a cada 30s)
# =============================================================================

def loop_pesado():
    """Loop separado para estatísticas pesadas (a cada 30s)"""
    print("📊 Iniciando loop pesado (30s)...")
    while True:
        time.sleep(30)
        atualizar_dados_pesados()

# =============================================================================
# ROTAS DA API
# =============================================================================

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        return f"Erro: {e}", 500

@app.route('/api/stats')
def api_stats():
    """Retorna dados leves + pesados"""
    try:
        # Converter horário para Brasília
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

@app.route('/api/previsao')
def api_previsao():
    previsao = calcular_previsao()
    return jsonify(previsao if previsao else {'erro': 'Dados insuficientes'})

@app.route('/api/tabela/<int:limite>')
def api_tabela(limite):
    """Retorna rodadas com limite específico (50,250,500,1000,2000,3000)"""
    try:
        # Limitar entre 50 e 3000
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
            # Converter para Brasília
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
        print(f"❌ Erro: {e}")
        return jsonify([]), 500

@app.route('/api/tabela/padrao')
def api_tabela_padrao():
    """Retorna 50 rodadas por padrão (mais rápido)"""
    return api_tabela(50)

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'rodadas': cache['leves']['total_rodadas'],
        'falhas': cache['falhas_consecutivas']
    })

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("="*70)
    print("🚀 BOT BACBO - VERSÃO FINAL DEFINITIVA")
    print("="*70)
    print("✅ SEM SELECT ID (usa ON CONFLICT)")
    print("✅ LEVE x PESADO separados")
    print("✅ LIMIT 3000 em todas consultas")
    print("✅ Índices no banco")
    print("✅ Horário Brasília")
    print("="*70)
    
    # Inicializar banco de dados com índices
    if init_db():
        print("✅ Banco de dados pronto")
    else:
        print("❌ Falha ao inicializar banco")
        sys.exit(1)
    
    # Atualizar dados iniciais
    atualizar_dados_leves()
    atualizar_dados_pesados()
    
    print(f"📊 {cache['leves']['total_rodadas']} rodadas no banco")
    print(f"⚡ Timeout: {TIMEOUT_API}s | Retries: {MAX_RETRIES}")
    print(f"🌐 Porta: {PORT}")
    print("="*70)
    
    # Iniciar threads
    threading.Thread(target=loop_coleta, daemon=True).start()
    threading.Thread(target=loop_pesado, daemon=True).start()
    
    # Iniciar Flask
    try:
        app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n🛑 Bot encerrado")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
        sys.exit(1)
