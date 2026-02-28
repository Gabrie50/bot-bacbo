# main.py - Bot BacBo com 8 Estratégias e Previsão 94% (VERSÃO COM BANCO NEON)

import os
import time
import requests
import json
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta, timezone
import sys
import threading
from flask import Flask, render_template, jsonify
from flask_cors import CORS

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================
# STRING DO BANCO NEON (AGORA PODE COLOCAR DIRETO POIS O REPO É PRIVADO)
DATABASE_URL = "postgresql://neondb_owner:npg_OgR74skiylmJ@ep-long-pond-ai793l7o-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

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

# Configurações
TIMEOUT_API = 5
MAX_RETRIES = 3
RETRY_DELAY = 1
INTERVALO_COLETA = 10
INTERVALO_PAGINAS = 0.5
MAX_PAGINAS = 50
PORT = int(os.environ.get("PORT", 5000))

# Cache
cache = {
    'ultima_atualizacao': None,
    'estatisticas': {},
    'previsao': None,
    'total_rodadas': 0,
    'falhas_consecutivas': 0,
    'ultimo_id': None
}

# =============================================================================
# INICIALIZAÇÃO DO FLASK
# =============================================================================
app = Flask(__name__)
CORS(app)

# Sessão HTTP
session = requests.Session()
session.headers.update(HEADERS)

# =============================================================================
# FUNÇÕES DO BANCO POSTGRESQL
# =============================================================================

def get_db_connection():
    """Cria conexão com o banco PostgreSQL Neon."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco: {e}")
        return None

def init_db():
    """Inicializa as tabelas no PostgreSQL."""
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cur = conn.cursor()
        
        # Criar tabela de rodadas
        cur.execute('''
            CREATE TABLE IF NOT EXISTS rodadas (
                id TEXT PRIMARY KEY,
                data_hora TIMESTAMP WITH TIME ZONE,
                player_score INTEGER,
                banker_score INTEGER,
                soma INTEGER,
                resultado TEXT,
                par_impar TEXT,
                multiplicador REAL,
                total_winners INTEGER,
                total_amount REAL,
                dados_json JSONB
            )
        ''')
        
        # Criar índices para consultas rápidas
        cur.execute('CREATE INDEX IF NOT EXISTS idx_data_hora ON rodadas(data_hora DESC)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_resultado ON rodadas(resultado)')
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Tabelas criadas/verificadas no PostgreSQL Neon")
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")

def salvar_rodada_no_db(rodada):
    """Salva uma rodada no PostgreSQL."""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO rodadas 
            (id, data_hora, player_score, banker_score, soma, resultado, par_impar, 
             multiplicador, total_winners, total_amount, dados_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        ''', (
            rodada['id'],
            rodada['data_hora'],
            rodada['player_score'],
            rodada['banker_score'],
            rodada.get('soma', rodada['player_score'] + rodada['banker_score']),
            rodada['resultado'],
            rodada.get('par_impar', ''),
            rodada.get('multiplicador', 1),
            rodada.get('total_winners', 0),
            rodada.get('total_amount', 0),
            json.dumps(rodada, default=str)
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar no banco: {e}")
        return False

def buscar_rodadas_do_db(horas, limite=3000):
    """Busca rodadas do PostgreSQL para um período."""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Calcular timestamp limite
        agora = datetime.now(timezone.utc)
        limite_data = agora - timedelta(hours=horas)
        
        cur.execute('''
            SELECT data_hora, player_score, banker_score, resultado, 
                   multiplicador, total_winners, total_amount
            FROM rodadas
            WHERE data_hora >= %s
            ORDER BY data_hora DESC
            LIMIT %s
        ''', (limite_data, limite))
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        resultado = []
        for row in rows:
            resultado.append({
                'data': row[0].strftime('%d/%m %H:%M:%S'),
                'player': row[1],
                'banker': row[2],
                'resultado': row[3],
                'cor': '🔴' if row[3] == 'BANKER' else '🔵' if row[3] == 'PLAYER' else '🟡',
                'mult': f"{row[4]}x",
                'winners': row[5],
                'premio': f"€{row[6]:,.0f}" if row[6] else '€0'
            })
        
        return resultado
    except Exception as e:
        print(f"❌ Erro ao buscar do banco: {e}")
        return []

def contar_rodadas_do_db(horas):
    """Conta quantas rodadas existem em um período."""
    conn = get_db_connection()
    if not conn:
        return 0
    
    try:
        cur = conn.cursor()
        agora = datetime.now(timezone.utc)
        limite_data = agora - timedelta(hours=horas)
        
        cur.execute('''
            SELECT COUNT(*) FROM rodadas
            WHERE data_hora >= %s
        ''', (limite_data,))
        
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return count
    except Exception as e:
        print(f"❌ Erro ao contar: {e}")
        return 0

def get_total_rodadas():
    """Retorna o total de rodadas no banco."""
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

def get_ultimas_20():
    """Retorna as últimas 20 rodadas para o gráfico."""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
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
            resultado.append({
                'hora': row[0].strftime('%H:%M:%S'),
                'resultado': row[3],
                'cor': '🔴' if row[3] == 'BANKER' else '🔵' if row[3] == 'PLAYER' else '🟡',
                'player': row[1],
                'banker': row[2]
            })
        
        return sorted(resultado, key=lambda x: x['hora'])
    except Exception as e:
        print(f"❌ Erro ao buscar últimas 20: {e}")
        return []

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
            resultado = resultado_api

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
            
        except Exception as e:
            print(f"⏱️ Tentativa {tentativa + 1}/{MAX_RETRIES} falhou: {e}")
            if tentativa < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
    
    cache['falhas_consecutivas'] += 1
    return None

def loop_coleta():
    """Loop principal de coleta - salva no banco."""
    print("🔄 Iniciando loop de coleta...")
    
    while True:
        try:
            inicio_ciclo = time.time()
            dados_brutos = buscar_dados_api_com_retry()
            
            if dados_brutos:
                novas_rodadas = 0
                
                # Verificar IDs existentes
                conn = get_db_connection()
                if conn:
                    cur = conn.cursor()
                    cur.execute('SELECT id FROM rodadas')
                    ids_existentes = {row[0] for row in cur.fetchall()}
                    cur.close()
                    conn.close()
                    
                    for item in dados_brutos:
                        rodada = processar_item_api(item)
                        if rodada and rodada['id'] and rodada['id'] not in ids_existentes:
                            if salvar_rodada_no_db(rodada):
                                novas_rodadas += 1
                    
                    if novas_rodadas > 0:
                        total = get_total_rodadas()
                        print(f"✅ +{novas_rodadas} novas (total: {total})")
                        atualizar_cache_estatisticas()
            
            # Se muitas falhas, aumentar intervalo
            if cache['falhas_consecutivas'] > 5:
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
# FUNÇÕES DE ESTATÍSTICA
# =============================================================================

def atualizar_cache_estatisticas():
    """Atualiza o cache de estatísticas."""
    global cache
    
    cache['estatisticas'] = {
        '0.16h': {'total': contar_rodadas_do_db(0.16)},
        '1h': {'total': contar_rodadas_do_db(1)},
        '6h': {'total': contar_rodadas_do_db(6)},
        '12h': {'total': contar_rodadas_do_db(12)},
        '24h': {'total': contar_rodadas_do_db(24)},
        '48h': {'total': contar_rodadas_do_db(48)},
        '72h': {'total': contar_rodadas_do_db(72)}
    }
    
    cache['total_rodadas'] = get_total_rodadas()
    cache['ultima_atualizacao'] = datetime.now(timezone.utc)
    print(f"📊 Cache atualizado: {cache['total_rodadas']} rodadas")

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
    """Retorna estatísticas."""
    try:
        ultimas_20 = get_ultimas_20()
        
        return jsonify({
            'ultima_atualizacao': cache['ultima_atualizacao'].strftime('%d/%m/%Y %H:%M:%S') if cache['ultima_atualizacao'] else None,
            'total_rodadas': cache['total_rodadas'],
            'resumo': cache['estatisticas'],
            'ultimas_20': ultimas_20,
            'previsao': None  # Por enquanto sem previsão para simplificar
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/tabela/<float:horas>')
@app.route('/api/tabela/<int:horas>')
def api_tabela(horas):
    """Busca rodadas no banco."""
    try:
        if isinstance(horas, int):
            horas = float(horas)
        
        print(f"📋 Buscando {horas}h no banco...")
        resultado = buscar_rodadas_do_db(horas)
        print(f"📤 Retornando {len(resultado)} rodadas")
        return jsonify(resultado)
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return jsonify([]), 500

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'rodadas': cache['total_rodadas'],
        'falhas': cache['falhas_consecutivas']
    })

# =============================================================================
# COLETA HISTÓRICA INICIAL
# =============================================================================

def buscar_historico_completo():
    """Busca rodadas históricas e salva no banco."""
    print("📚 Iniciando coleta histórica...")
    
    page = 0
    total_coletadas = 0
    
    while page < MAX_PAGINAS:
        try:
            params = PARAMS.copy()
            params['page'] = page
            params['size'] = 100
            
            print(f"📡 Página {page + 1}/{MAX_PAGINAS}...", end=' ')
            response = session.get(API_URL, params=params, timeout=TIMEOUT_API)
            response.raise_for_status()
            dados = response.json()
            
            if not dados:
                break
            
            # Verificar IDs existentes
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('SELECT id FROM rodadas')
            ids_existentes = {row[0] for row in cur.fetchall()}
            cur.close()
            conn.close()
            
            novas = 0
            for item in dados:
                rodada = processar_item_api(item)
                if rodada and rodada['id'] and rodada['id'] not in ids_existentes:
                    if salvar_rodada_no_db(rodada):
                        novas += 1
                        total_coletadas += 1
            
            print(f"+{novas} novas")
            
            if novas == 0:
                break
                
            page += 1
            time.sleep(INTERVALO_PAGINAS)
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            break
    
    print(f"✅ Coleta histórica concluída! +{total_coletadas} rodadas")
    atualizar_cache_estatisticas()

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("="*70)
    print("🚀 BOT BACBO - POSTGRESQL NEON (REPO PRIVADO)")
    print("="*70)
    
    # Inicializar banco de dados
    init_db()
    
    # Atualizar cache
    atualizar_cache_estatisticas()
    
    print(f"📊 {cache['total_rodadas']} rodadas no banco")
    print(f"⚡ Timeout: {TIMEOUT_API}s | Retries: {MAX_RETRIES}")
    print(f"🌐 Porta: {PORT}")
    print("="*70)
    
    # Iniciar coleta histórica se banco vazio
    if cache['total_rodadas'] < 100:
        historico_thread = threading.Thread(target=buscar_historico_completo, daemon=True)
        historico_thread.start()
    
    # Iniciar coleta contínua
    coletor = threading.Thread(target=loop_coleta, daemon=True)
    coletor.start()

    # Iniciar Flask
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
