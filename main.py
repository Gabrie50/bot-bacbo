# main.py - Bot BacBo com Web Interface Integrada

import os
import time
import requests
import psycopg2
from datetime import datetime, timedelta
import json
import sys
import threading
from collections import Counter

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("❌ ERRO: DATABASE_URL não configurada!")
    print("👉 Vá em Variables no Railway e adicione DATABASE_URL")
    sys.exit(1)

# API do Casino.org
API_URL = "https://api-cs.casino.org/svc-evolution-game-events/api/bacbo"
PARAMS = {
    "page": 0,
    "size": 20,
    "sort": "data.settledAt,desc",
    "duration": 30,
    "wheelResults": "PlayerWon,BankerWon,Tie"
}
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

INTERVALO_COLETA = 10  # segundos

# Cache para estatísticas (para a interface web)
cache_estatisticas = {
    'ultima_atualizacao': None,
    'ultimas_72h': {},
    'ultimas_100': [],
    'resumo': {}
}

# =============================================================================
# FUNÇÕES DO BANCO DE DADOS (Neon)
# =============================================================================
def conectar_banco():
    """Conecta ao banco PostgreSQL no Neon."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        print("✅ Conectado ao banco Neon com sucesso!")
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar no banco: {e}")
        return None

def criar_tabela(conn):
    """Cria a tabela para armazenar as rodadas, se não existir."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS rodadas_bacbo (
                    id TEXT PRIMARY KEY,
                    data_hora TIMESTAMP,
                    player_score INTEGER,
                    banker_score INTEGER,
                    soma INTEGER,
                    resultado TEXT,
                    par_impar TEXT,
                    multiplicador FLOAT,
                    total_winners INTEGER,
                    total_amount FLOAT,
                    dados_completos JSONB
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_data_hora ON rodadas_bacbo(data_hora DESC);")
            conn.commit()
            print("✅ Tabela 'rodadas_bacbo' verificada/criada com sucesso.")
    except Exception as e:
        print(f"❌ Erro ao criar tabela: {e}")
        conn.rollback()

def inserir_rodada(conn, rodada):
    """Insere uma nova rodada no banco, ignorando conflitos."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO rodadas_bacbo 
                (id, data_hora, player_score, banker_score, soma, resultado, par_impar, multiplicador, total_winners, total_amount, dados_completos)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING;
            """, (
                rodada['id'],
                rodada['data_hora'],
                rodada['player_score'],
                rodada['banker_score'],
                rodada['soma'],
                rodada['resultado'],
                rodada['par_impar'],
                rodada['multiplicador'],
                rodada['total_winners'],
                rodada['total_amount'],
                json.dumps(rodada['dados_completos'])
            ))
            conn.commit()
            return cur.rowcount > 0
    except Exception as e:
        print(f"❌ Erro ao inserir rodada {rodada['id']}: {e}")
        conn.rollback()
        return False

def buscar_ultimas_rodadas(conn, limite=100):
    """Busca as últimas N rodadas do banco para análise."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, data_hora, player_score, banker_score, soma, resultado, par_impar
                FROM rodadas_bacbo
                ORDER BY data_hora DESC
                LIMIT %s;
            """, (limite,))
            colunas = [desc[0] for desc in cur.description]
            resultados = [dict(zip(colunas, row)) for row in cur.fetchall()]
            return resultados
    except Exception as e:
        print(f"❌ Erro ao buscar últimas rodadas: {e}")
        return []

def buscar_rodadas_periodo(conn, horas=72):
    """Busca rodadas das últimas N horas para a interface web."""
    try:
        since = datetime.now() - timedelta(hours=horas)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    id,
                    TO_CHAR(data_hora, 'DD/MM HH24:MI') as data_formatada,
                    player_score,
                    banker_score,
                    soma,
                    resultado,
                    par_impar,
                    multiplicador,
                    total_winners,
                    total_amount
                FROM rodadas_bacbo
                WHERE data_hora >= %s
                ORDER BY data_hora DESC;
            """, (since,))
            colunas = [desc[0] for desc in cur.description]
            resultados = [dict(zip(colunas, row)) for row in cur.fetchall()]
            return resultados
    except Exception as e:
        print(f"❌ Erro ao buscar rodadas do período: {e}")
        return []

def calcular_estatisticas_detalhadas(conn):
    """Calcula estatísticas detalhadas para a interface web."""
    try:
        stats = {}
        periodos = [1, 6, 12, 24, 48, 72]  # horas
        
        for horas in periodos:
            since = datetime.now() - timedelta(hours=horas)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        COUNT(*) FILTER (WHERE resultado = 'PlayerWon') as player,
                        COUNT(*) FILTER (WHERE resultado = 'BankerWon') as banker,
                        COUNT(*) FILTER (WHERE resultado = 'Tie') as tie,
                        COUNT(*) as total,
                        AVG(player_score) as media_player,
                        AVG(banker_score) as media_banker,
                        SUM(total_amount) as premios_total,
                        AVG(multiplicador) as media_mult
                    FROM rodadas_bacbo
                    WHERE data_hora >= %s;
                """, (since,))
                row = cur.fetchone()
                if row and row[3] > 0:
                    total = row[3]
                    stats[f"{horas}h"] = {
                        'total': total,
                        'player': row[0],
                        'player_pct': (row[0]/total*100) if total > 0 else 0,
                        'banker': row[1],
                        'banker_pct': (row[1]/total*100) if total > 0 else 0,
                        'tie': row[2],
                        'tie_pct': (row[2]/total*100) if total > 0 else 0,
                        'media_player': float(row[4]) if row[4] else 0,
                        'media_banker': float(row[5]) if row[5] else 0,
                        'premios_total': float(row[6]) if row[6] else 0,
                        'media_mult': float(row[7]) if row[7] else 0
                    }
        
        return stats
    except Exception as e:
        print(f"❌ Erro ao calcular estatísticas detalhadas: {e}")
        return {}

def atualizar_cache(conn):
    """Atualiza o cache de estatísticas para a interface web."""
    global cache_estatisticas
    try:
        cache_estatisticas['ultimas_72h'] = buscar_rodadas_periodo(conn, 72)
        cache_estatisticas['ultimas_100'] = buscar_ultimas_rodadas(conn, 100)
        cache_estatisticas['resumo'] = calcular_estatisticas_detalhadas(conn)
        cache_estatisticas['ultima_atualizacao'] = datetime.now()
        print(f"🔄 Cache atualizado: {len(cache_estatisticas['ultimas_72h'])} rodadas")
    except Exception as e:
        print(f"❌ Erro ao atualizar cache: {e}")

# =============================================================================
# FUNÇÕES DE COLETA DA API
# =============================================================================
def buscar_dados_api():
    """Faz a requisição à API e retorna os dados brutos."""
    try:
        response = requests.get(API_URL, params=PARAMS, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Erro na requisição à API: {e}")
        return None

def processar_item_api(item):
    """Converte um item da API para o formato da nossa base."""
    try:
        data = item.get('data', {})
        result = data.get('result', {})
        player_dice = result.get('playerDice', {})
        banker_dice = result.get('bankerDice', {})
        player_score = player_dice.get('score', 0)
        banker_score = banker_dice.get('score', 0)
        soma = player_score + banker_score
        resultado_api = result.get('outcome', 'Desconhecido')

        if resultado_api == 'PlayerWon':
            resultado = 'PLAYER'
        elif resultado_api == 'BankerWon':
            resultado = 'BANKER'
        elif resultado_api == 'Tie':
            resultado = 'TIE'
        else:
            resultado = resultado_api

        par_impar = 'PAR' if soma % 2 == 0 else 'IMPAR'

        return {
            'id': data.get('id'),
            'data_hora': datetime.fromisoformat(data.get('settledAt', '').replace('Z', '+00:00')),
            'player_score': player_score,
            'banker_score': banker_score,
            'soma': soma,
            'resultado': resultado,
            'par_impar': par_impar,
            'multiplicador': result.get('multiplier', 1),
            'total_winners': item.get('totalWinners', 0),
            'total_amount': item.get('totalAmount', 0),
            'dados_completos': item
        }
    except Exception as e:
        print(f"⚠️ Erro ao processar item da API: {e}")
        return None

# =============================================================================
# MÓDULO DE ESTRATÉGIA E PREDIÇÃO
# =============================================================================
def identificar_modo(estats):
    """Identifica o modo do algoritmo com base nas estatísticas."""
    diff = abs(estats['banker_pct'] - estats['player_pct'])
    if diff > 4:
        return "AGRESSIVO"
    elif 44 < estats['player_pct'] < 46 and 44 < estats['banker_pct'] < 46:
        return "EQUILIBRADO"
    else:
        return "PREDATORIO"

def analisar_historico(historico):
    """Analisa o histórico e retorna votos para PLAYER e BANKER."""
    if len(historico) < 5:
        return {'PLAYER': 0, 'BANKER': 0, 'detalhes': {}}

    sequencia = [h['resultado'] for h in historico]
    
    votos = {'PLAYER': 0, 'BANKER': 0}
    detalhes = {}

    # Estratégia #2: PAREDÃO
    if len(sequencia) >= 4 and all(r == sequencia[0] for r in sequencia[:4]):
        votos[sequencia[0]] += 90
        detalhes['Paredao'] = f"+90 para {sequencia[0]}"
    elif len(sequencia) >= 3 and all(r == sequencia[0] for r in sequencia[:3]):
        votos[sequencia[0]] += 50
        detalhes['Paredao_3'] = f"+50 para {sequencia[0]}"

    # Estratégia #4: XADREZ
    if len(sequencia) >= 4:
        if sequencia[0] != sequencia[1] and sequencia[1] != sequencia[2] and sequencia[2] != sequencia[3]:
            proxima = 'PLAYER' if sequencia[0] == 'BANKER' else 'BANKER'
            votos[proxima] += 90
            detalhes['Xadrez'] = f"+90 para {proxima}"

    # Estratégia #5: CONTRAGOLPE
    if len(sequencia) >= 4 and sequencia[0] != sequencia[1] and sequencia[1] == sequencia[2] == sequencia[3]:
        votos[sequencia[1]] += 70
        detalhes['Contragolpe'] = f"+70 para {sequencia[1]}"

    # Estratégia #7: FALSA ALTERNÂNCIA
    ultimo = historico[0]
    if ultimo['player_score'] >= 10 or ultimo['banker_score'] >= 10:
        votos[ultimo['resultado']] += 80
        detalhes['Falsa_Alternancia'] = f"+80 para {ultimo['resultado']}"

    return {'PLAYER': votos['PLAYER'], 'BANKER': votos['BANKER'], 'detalhes': detalhes}

def prever_proxima_cor(conn):
    """Função principal que coordena a predição."""
    print("\n" + "="*60)
    print("🧠 INICIANDO ANALISE PARA PREDICAO")
    print("="*60)

    estats = calcular_estatisticas_gerais(conn, periodo_minutos=30)
    print(f"📊 Estatisticas (ultimos 30 min): Player {estats['player_pct']:.1f}%, Banker {estats['banker_pct']:.1f}%, Tie {estats['tie_pct']:.1f}%")

    modo = identificar_modo(estats)
    print(f"🎯 Modo detectado: {modo}")

    historico = buscar_ultimas_rodadas(conn, limite=20)
    if not historico:
        print("⚠️ Historico insuficiente para predicao.")
        return None

    votos = analisar_historico(historico)

    if "AGRESSIVO" in modo:
        if estats['banker_pct'] > estats['player_pct'] + 2:
            votos['BANKER'] = int(votos['BANKER'] * 1.5)
        elif estats['player_pct'] > estats['banker_pct'] + 2:
            votos['PLAYER'] = int(votos['PLAYER'] * 1.5)

    if votos['BANKER'] > votos['PLAYER']:
        previsao = 'BANKER'
        confianca = (votos['BANKER'] / (votos['BANKER'] + votos['PLAYER'] + 0.01)) * 100
    elif votos['PLAYER'] > votos['BANKER']:
        previsao = 'PLAYER'
        confianca = (votos['PLAYER'] / (votos['BANKER'] + votos['PLAYER'] + 0.01)) * 100
    else:
        previsao = 'INDEFINIDO'
        confianca = 0

    delay_ativo = bool(historico and historico[0]['resultado'] == 'TIE')

    return {
        'previsao': previsao,
        'confianca': confianca,
        'modo': modo,
        'delay_ativo': delay_ativo,
        'player_pct': estats['player_pct'],
        'banker_pct': estats['banker_pct'],
        'tie_pct': estats['tie_pct'],
        'votos': votos
    }

# =============================================================================
# LOOP PRINCIPAL DE COLETA
# =============================================================================
def loop_coleta(conn):
    """Loop principal de coleta de dados."""
    ciclo_coleta = 0
    while True:
        try:
            ciclo_coleta += 1
            dados_brutos = buscar_dados_api()

            if dados_brutos:
                novas_rodadas = 0
                for item in dados_brutos:
                    rodada = processar_item_api(item)
                    if rodada:
                        if inserir_rodada(conn, rodada):
                            novas_rodadas += 1

                if novas_rodadas > 0:
                    print(f"✅ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {novas_rodadas} novas rodadas")
                    # Atualizar cache a cada nova rodada
                    atualizar_cache(conn)
                else:
                    print(f"⏳ {datetime.now().strftime('%H:%M:%S')} - Nenhuma rodada nova")

                # A cada 6 ciclos (1 minuto), fazer predição
                if ciclo_coleta % 6 == 0:
                    previsao = prever_proxima_cor(conn)
                    if previsao:
                        print(f"🎯 Previsão: {previsao['previsao']} com {previsao['confianca']:.1f}%")

            time.sleep(INTERVALO_COLETA)

        except Exception as e:
            print(f"❌ Erro no loop de coleta: {e}")
            time.sleep(INTERVALO_COLETA)

# =============================================================================
# INICIALIZAÇÃO
# =============================================================================
def main():
    print("="*60)
    print("🚀 BOT BACBO COM WEB INTERFACE - INICIANDO")
    print("="*60)
    
    conn = conectar_banco()
    if not conn:
        print("❌ Falha na conexao com o banco. Encerrando.")
        sys.exit(1)

    criar_tabela(conn)
    
    # Atualizar cache inicial
    atualizar_cache(conn)
    
    print(f"⏱️  Coletando dados a cada {INTERVALO_COLETA} segundos.")
    print("🌐 Interface web disponível na porta 5000")
    print("="*60)

    # Iniciar thread da interface web
    try:
        from web_interface import app
        import threading
        web_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False))
        web_thread.daemon = True
        web_thread.start()
        print("✅ Interface web iniciada na porta 5000")
    except Exception as e:
        print(f"⚠️ Erro ao iniciar interface web: {e}")
        print("📝 Certifique-se que web_interface.py está no mesmo diretório")

    # Iniciar loop de coleta (bloqueante)
    try:
        loop_coleta(conn)
    except KeyboardInterrupt:
        print("\n🛑 Bot interrompido")
        if conn:
            conn.close()
        sys.exit(0)

if __name__ == "__main__":
    main()
