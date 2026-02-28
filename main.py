# main.py - Bot BacBo com PostgreSQL (pg8000) - VERSÃO FINAL

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
DATABASE_URL = "postgresql://neondb_owner:npg_OgR74skiylmJ@ep-long-pond-ai793l7o-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

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
    "size": 50,
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
MAX_PAGINAS = 50
PORT = int(os.environ.get("PORT", 5000))

# Cache em memória
cache = {
    'ultima_atualizacao': None,
    'estatisticas': {},
    'previsao': None,
    'total_rodadas': 0,
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
            ssl_context=True  # Necessário para Neon
        )
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco: {e}")
        return None

def init_db():
    """Inicializa as tabelas no PostgreSQL."""
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
        
        # Criar índices para consultas rápidas
        cur.execute('CREATE INDEX IF NOT EXISTS idx_data_hora ON rodadas(data_hora DESC)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_resultado ON rodadas(resultado)')
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Tabelas criadas/verificadas no PostgreSQL")
        return True
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        return False

def salvar_rodada(rodada):
    """Salva uma rodada no banco de dados."""
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
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar rodada: {e}")
        return False

def buscar_rodadas(horas, limite=3000):
    """Busca rodadas de um período específico."""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
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
            # Converter para dicionário
            data_hora = row[0]
            player = row[1]
            banker = row[2]
            resultado_str = row[3]
            mult = row[4]
            winners = row[5]
            amount = row[6] if row[6] else 0
            
            # Determinar cor
            if resultado_str == 'BANKER':
                cor = '🔴'
            elif resultado_str == 'PLAYER':
                cor = '🔵'
            else:
                cor = '🟡'
            
            resultado.append({
                'data': data_hora.strftime('%d/%m %H:%M:%S'),
                'player': player,
                'banker': banker,
                'resultado': resultado_str,
                'cor': cor,
                'mult': f"{mult}x",
                'winners': winners,
                'premio': f"€{amount:,.0f}" if amount else '€0'
            })
        
        return resultado
    except Exception as e:
        print(f"❌ Erro ao buscar rodadas: {e}")
        return []

def contar_rodadas(horas):
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
        print(f"❌ Erro ao contar rodadas: {e}")
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
            player = row[1]
            banker = row[2]
            resultado_str = row[3]
            
            # Determinar cor
            if resultado_str == 'BANKER':
                cor = '🔴'
            elif resultado_str == 'PLAYER':
                cor = '🔵'
            else:
                cor = '🟡'
            
            resultado.append({
                'hora': data_hora.strftime('%H:%M:%S'),
                'resultado': resultado_str,
                'cor': cor,
                'player': player,
                'banker': banker
            })
        
        # Ordenar por hora
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

        # Mapear resultado
        if resultado_api == 'PlayerWon':
            resultado = 'PLAYER'
        elif resultado_api == 'BankerWon':
            resultado = 'BANKER'
        elif resultado_api == 'Tie':
            resultado = 'TIE'
        else:
            resultado = 'DESCONHECIDO'

        # Converter data
        data_hora_str = data.get('settledAt', '')
        data_hora = datetime.fromisoformat(data_hora_str.replace('Z', '+00:00'))

        # Determinar par/ímpar
        soma = player_score + banker_score
        par_impar = 'PAR' if soma % 2 == 0 else 'IMPAR'

        return {
            'id': data.get('id'),
            'data_hora': data_hora,
            'player_score': player_score,
            'banker_score': banker_score,
            'soma': soma,
            'resultado': resultado,
            'par_impar': par_impar,
            'multiplicador': result.get('multiplier', 1),
            'total_winners': item.get('totalWinners', 0),
            'total_amount': item.get('totalAmount', 0)
        }
    except Exception as e:
        print(f"⚠️ Erro ao processar item: {e}")
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
            
            # Sucesso - resetar contador de falhas
            cache['falhas_consecutivas'] = 0
            return response.json()
            
        except requests.exceptions.Timeout:
            print(f"⏱️ Timeout na tentativa {tentativa + 1}/{MAX_RETRIES}")
        except requests.exceptions.ConnectionError:
            print(f"🔌 Erro de conexão na tentativa {tentativa + 1}/{MAX_RETRIES}")
        except Exception as e:
            print(f"⚠️ Erro na tentativa {tentativa + 1}/{MAX_RETRIES}: {e}")
        
        # Aguardar antes de tentar novamente
        if tentativa < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY)
    
    # Todas as tentativas falharam
    cache['falhas_consecutivas'] += 1
    print(f"❌ Todas as {MAX_RETRIES} tentativas falharam. Falhas consecutivas: {cache['falhas_consecutivas']}")
    return None

# =============================================================================
# FUNÇÕES DE ESTATÍSTICA E PREVISÃO
# =============================================================================

def identificar_modo(player_pct, banker_pct, tie_pct, dados):
    """Identifica o modo do algoritmo baseado nos dados."""
    # Contar números extremos (10,11,12)
    extremos = sum(1 for r in dados if r['player_score'] >= 10 or r['banker_score'] >= 10)
    total = len(dados) if dados else 1
    pct_extremos = (extremos / total) * 100 if total > 0 else 0
    
    if banker_pct > 47 or player_pct > 47:
        return "AGRESSIVO"
    elif 44 < player_pct < 46 and 44 < banker_pct < 46:
        return "EQUILIBRADO"
    elif pct_extremos > 30:
        return "PREDATORIO"
    else:
        return "EQUILIBRADO"

def estrategia_compensacao(dados, modo):
    """Estratégia #1: Compensação"""
    if len(dados) < 10:
        return {'banker': 0, 'player': 0, 'descricao': None}
    
    player = sum(1 for r in dados if r['resultado'] == 'PLAYER')
    banker = sum(1 for r in dados if r['resultado'] == 'BANKER')
    total = len(dados)
    
    player_pct = (player / total) * 100
    banker_pct = (banker / total) * 100
    diff = abs(banker_pct - player_pct)
    
    if diff > 4:
        peso = PESOS['compensacao'][modo]
        if banker_pct > player_pct:
            return {'banker': 0, 'player': peso, 'descricao': 'Compensação: Player precisa subir'}
        else:
            return {'banker': peso, 'player': 0, 'descricao': 'Compensação: Banker precisa subir'}
    
    return {'banker': 0, 'player': 0, 'descricao': None}

def estrategia_paredao(dados, modo):
    """Estratégia #2: Paredão"""
    if len(dados) < 4:
        return {'banker': 0, 'player': 0, 'descricao': None}
    
    sequencia = [r['resultado'] for r in dados[:4]]
    
    if all(r == 'BANKER' for r in sequencia):
        peso = PESOS['paredao'][modo]
        return {'banker': peso, 'player': 0, 'descricao': 'Paredão: 4+ BANKER'}
    elif all(r == 'PLAYER' for r in sequencia):
        peso = PESOS['paredao'][modo]
        return {'banker': 0, 'player': peso, 'descricao': 'Paredão: 4+ PLAYER'}
    
    return {'banker': 0, 'player': 0, 'descricao': None}

def estrategia_moedor(dados, modo):
    """Estratégia #3: Moedor (Cluster de Empates)"""
    if len(dados) < 5:
        return {'banker': 0, 'player': 0, 'tie': 0, 'descricao': None}
    
    ties_5 = sum(1 for r in dados[:5] if r['resultado'] == 'TIE')
    total_ties = sum(1 for r in dados if r['resultado'] == 'TIE')
    tie_pct = (total_ties / len(dados)) * 100
    
    if ties_5 >= 2 or tie_pct > 13:
        return {
            'banker': 0, 
            'player': 0, 
            'tie': PESOS['moedor'][modo], 
            'descricao': f'Moedor: {ties_5} ties em 5 rodadas'
        }
    
    return {'banker': 0, 'player': 0, 'tie': 0, 'descricao': None}

def estrategia_xadrez(dados, modo):
    """Estratégia #4: Xadrez (Alternância)"""
    if len(dados) < 4:
        return {'banker': 0, 'player': 0, 'descricao': None}
    
    sequencia = [r['resultado'] for r in dados[:4]]
    
    if (sequencia[0] != sequencia[1] and 
        sequencia[1] != sequencia[2] and 
        sequencia[2] != sequencia[3]):
        
        peso = PESOS['xadrez'][modo]
        if sequencia[3] == 'BANKER':
            return {'banker': 0, 'player': peso, 'descricao': 'Xadrez: próximo PLAYER'}
        else:
            return {'banker': peso, 'player': 0, 'descricao': 'Xadrez: próximo BANKER'}
    
    return {'banker': 0, 'player': 0, 'descricao': None}

def estrategia_contragolpe(dados, modo):
    """Estratégia #5: Contragolpe"""
    if len(dados) < 5:
        return {'banker': 0, 'player': 0, 'descricao': None}
    
    sequencia = [r['resultado'] for r in dados[:5]]
    
    if (sequencia[0] == sequencia[1] == sequencia[2] and
        sequencia[2] != sequencia[3] and
        sequencia[3] != sequencia[4] and
        sequencia[4] == sequencia[0]):
        
        peso = PESOS['contragolpe'][modo]
        if sequencia[0] == 'BANKER':
            return {'banker': peso, 'player': 0, 'descricao': 'Contragolpe: volta BANKER'}
        else:
            return {'banker': 0, 'player': peso, 'descricao': 'Contragolpe: volta PLAYER'}
    
    return {'banker': 0, 'player': 0, 'descricao': None}

def estrategia_reset_cluster(dados, modo):
    """Estratégia #6: Reset Pós-Cluster"""
    if len(dados) < 10:
        return {'banker': 0, 'player': 0, 'descricao': None}
    
    ties_10 = sum(1 for r in dados[:10] if r['resultado'] == 'TIE')
    
    if ties_10 >= 3:
        player = sum(1 for r in dados[:20] if r['resultado'] == 'PLAYER')
        banker = sum(1 for r in dados[:20] if r['resultado'] == 'BANKER')
        
        peso = PESOS['reset_cluster'][modo]
        if banker > player:
            return {'banker': peso, 'player': 0, 'descricao': 'Reset Cluster: volta BANKER'}
        else:
            return {'banker': 0, 'player': peso, 'descricao': 'Reset Cluster: volta PLAYER'}
    
    return {'banker': 0, 'player': 0, 'descricao': None}

def estrategia_falsa_alternancia(dados, modo):
    """Estratégia #7: Falsa Alternância"""
    if len(dados) < 3:
        return {'banker': 0, 'player': 0, 'descricao': None}
    
    ultimo = dados[0]
    if ultimo['player_score'] >= 10 or ultimo['banker_score'] >= 10:
        peso = PESOS['falsa_alternancia'][modo]
        if ultimo['resultado'] == 'BANKER':
            return {'banker': peso, 'player': 0, 'descricao': 'Falsa Alternância: extremo BANKER'}
        else:
            return {'banker': 0, 'player': peso, 'descricao': 'Falsa Alternância: extremo PLAYER'}
    
    return {'banker': 0, 'player': 0, 'descricao': None}

def calcular_previsao():
    """Função principal de previsão com 8 estratégias."""
    # Buscar últimas 50 rodadas do banco
    conn = get_db_connection()
    if not conn:
        return None
    
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
        
        if len(rows) < 10:
            return None
        
        # Converter para lista de dicionários
        dados_analise = []
        for row in rows:
            dados_analise.append({
                'player_score': row[0],
                'banker_score': row[1],
                'resultado': row[2]
            })
        
        # Calcular percentuais
        total = len(dados_analise)
        player = sum(1 for r in dados_analise if r['resultado'] == 'PLAYER')
        banker = sum(1 for r in dados_analise if r['resultado'] == 'BANKER')
        tie = sum(1 for r in dados_analise if r['resultado'] == 'TIE')
        
        player_pct = (player / total) * 100
        banker_pct = (banker / total) * 100
        tie_pct = (tie / total) * 100
        
        # Identificar modo
        modo = identificar_modo(player_pct, banker_pct, tie_pct, dados_analise)
        
        # Aplicar estratégias
        estrategias = []
        votos_banker = 0
        votos_player = 0
        votos_tie = 0
        
        # Estratégia 1: Compensação
        e1 = estrategia_compensacao(dados_analise, modo)
        votos_banker += e1.get('banker', 0)
        votos_player += e1.get('player', 0)
        if e1['descricao']:
            estrategias.append(e1['descricao'])
        
        # Estratégia 2: Paredão
        e2 = estrategia_paredao(dados_analise, modo)
        votos_banker += e2.get('banker', 0)
        votos_player += e2.get('player', 0)
        if e2['descricao']:
            estrategias.append(e2['descricao'])
        
        # Estratégia 3: Moedor
        e3 = estrategia_moedor(dados_analise, modo)
        votos_tie += e3.get('tie', 0)
        if e3['descricao']:
            estrategias.append(e3['descricao'])
        
        # Estratégia 4: Xadrez
        e4 = estrategia_xadrez(dados_analise, modo)
        votos_banker += e4.get('banker', 0)
        votos_player += e4.get('player', 0)
        if e4['descricao']:
            estrategias.append(e4['descricao'])
        
        # Estratégia 5: Contragolpe
        e5 = estrategia_contragolpe(dados_analise, modo)
        votos_banker += e5.get('banker', 0)
        votos_player += e5.get('player', 0)
        if e5['descricao']:
            estrategias.append(e5['descricao'])
        
        # Estratégia 6: Reset Cluster
        e6 = estrategia_reset_cluster(dados_analise, modo)
        votos_banker += e6.get('banker', 0)
        votos_player += e6.get('player', 0)
        if e6['descricao']:
            estrategias.append(e6['descricao'])
        
        # Estratégia 7: Falsa Alternância
        e7 = estrategia_falsa_alternancia(dados_analise, modo)
        votos_banker += e7.get('banker', 0)
        votos_player += e7.get('player', 0)
        if e7['descricao']:
            estrategias.append(e7['descricao'])
        
        # Meta-Algoritmo (Estratégia 8)
        if modo == "AGRESSIVO":
            if banker_pct > player_pct:
                votos_banker = int(votos_banker * 1.5)
                estrategias.append('Meta: AGRESSIVO BANKER (x1.5)')
            else:
                votos_player = int(votos_player * 1.5)
                estrategias.append('Meta: AGRESSIVO PLAYER (x1.5)')
        elif modo == "PREDATORIO":
            if any('Falsa Alternância' in e for e in estrategias):
                if banker_pct > player_pct:
                    votos_banker = int(votos_banker * 1.3)
                else:
                    votos_player = int(votos_player * 1.3)
                estrategias.append('Meta: PREDATÓRIO (x1.3)')
        
        # Determinar vencedor
        total_votos = votos_banker + votos_player + votos_tie
        
        if total_votos == 0:
            # Fallback: usar percentuais
            if banker_pct > player_pct:
                previsao = 'BANKER'
                confianca = round((banker_pct / (banker_pct + player_pct)) * 100)
            else:
                previsao = 'PLAYER'
                confianca = round((player_pct / (banker_pct + player_pct)) * 100)
        else:
            if votos_banker > votos_player and votos_banker > votos_tie:
                previsao = 'BANKER'
                confianca = round((votos_banker / total_votos) * 100)
            elif votos_player > votos_banker and votos_player > votos_tie:
                previsao = 'PLAYER'
                confianca = round((votos_player / total_votos) * 100)
            elif votos_tie > votos_banker and votos_tie > votos_player:
                previsao = 'TIE'
                confianca = round((votos_tie / total_votos) * 100)
            else:
                # Empate - decidir por percentuais
                if banker_pct > player_pct:
                    previsao = 'BANKER'
                    confianca = round((banker_pct / (banker_pct + player_pct)) * 100)
                else:
                    previsao = 'PLAYER'
                    confianca = round((player_pct / (banker_pct + player_pct)) * 100)
        
        # Verificar delay pós-empate
        ultimo_resultado = dados_analise[0]['resultado'] if dados_analise else None
        delay_ativo = (ultimo_resultado == 'TIE')
        
        # Símbolo
        if previsao == 'PLAYER':
            simbolo = '🔵'
        elif previsao == 'BANKER':
            simbolo = '🔴'
        else:
            simbolo = '🟡'
        
        return {
            'modo': modo,
            'previsao': previsao,
            'simbolo': simbolo,
            'confianca': confianca,
            'delay_ativo': delay_ativo,
            'estrategias': estrategias[:3]  # Top 3 estratégias
        }
        
    except Exception as e:
        print(f"❌ Erro na previsão: {e}")
        return None

# =============================================================================
# FUNÇÕES DE ATUALIZAÇÃO DE CACHE
# =============================================================================

def atualizar_cache_estatisticas():
    """Atualiza o cache de estatísticas."""
    global cache
    
    cache['estatisticas'] = {
        '0.16h': {'total': contar_rodadas(0.16)},
        '1h': {'total': contar_rodadas(1)},
        '6h': {'total': contar_rodadas(6)},
        '12h': {'total': contar_rodadas(12)},
        '24h': {'total': contar_rodadas(24)},
        '48h': {'total': contar_rodadas(48)},
        '72h': {'total': contar_rodadas(72)}
    }
    
    cache['total_rodadas'] = get_total_rodadas()
    cache['ultima_atualizacao'] = datetime.now(timezone.utc)
    cache['previsao'] = calcular_previsao()
    
    print(f"📊 Cache atualizado: {cache['total_rodadas']} rodadas")

# =============================================================================
# ROTAS DA API
# =============================================================================

@app.route('/')
def index():
    """Página principal."""
    try:
        return render_template('index.html')
    except Exception as e:
        return f"Erro ao carregar template: {e}", 500

@app.route('/api/stats')
def api_stats():
    """Retorna estatísticas em JSON."""
    try:
        return jsonify({
            'ultima_atualizacao': cache['ultima_atualizacao'].strftime('%d/%m/%Y %H:%M:%S') if cache['ultima_atualizacao'] else None,
            'total_rodadas': cache['total_rodadas'],
            'resumo': cache['estatisticas'],
            'ultimas_20': get_ultimas_20(),
            'previsao': cache['previsao']
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/previsao')
def api_previsao():
    """Endpoint específico para previsão."""
    previsao = calcular_previsao()
    return jsonify(previsao if previsao else {'erro': 'Dados insuficientes'})

@app.route('/api/tabela/<float:horas>')
@app.route('/api/tabela/<int:horas>')
def api_tabela(horas):
    """Retorna tabela de rodadas para um período."""
    try:
        if isinstance(horas, int):
            horas = float(horas)
        
        print(f"📋 Buscando {horas}h no banco...")
        resultado = buscar_rodadas(horas)
        print(f"📤 Retornando {len(resultado)} rodadas")
        return jsonify(resultado)
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return jsonify([]), 500

@app.route('/health')
def health():
    """Health check."""
    return jsonify({
        'status': 'ok',
        'rodadas': cache['total_rodadas'],
        'falhas': cache['falhas_consecutivas']
    })

# =============================================================================
# LOOP DE COLETA EM TEMPO REAL
# =============================================================================

def loop_coleta():
    """Loop principal de coleta em tempo real."""
    print("🔄 Iniciando loop de coleta em tempo real...")
    
    while True:
        try:
            inicio_ciclo = time.time()
            
            # Buscar dados da API
            dados_brutos = buscar_dados_api_com_retry()
            
            if dados_brutos:
                novas_rodadas = 0
                
                # Buscar IDs existentes
                conn = get_db_connection()
                if conn:
                    cur = conn.cursor()
                    cur.execute('SELECT id FROM rodadas')
                    ids_existentes = {row[0] for row in cur.fetchall()}
                    cur.close()
                    conn.close()
                    
                    # Processar cada item
                    for item in dados_brutos:
                        rodada = processar_item_api(item)
                        if rodada and rodada['id'] and rodada['id'] not in ids_existentes:
                            if salvar_rodada(rodada):
                                novas_rodadas += 1
                    
                    if novas_rodadas > 0:
                        print(f"✅ +{novas_rodadas} novas rodadas")
                        atualizar_cache_estatisticas()
            
            # Se muitas falhas, aumentar intervalo
            if cache['falhas_consecutivas'] > 5:
                print(f"⚠️ Muitas falhas, aguardando 30s...")
                time.sleep(30)
                cache['falhas_consecutivas'] = 0
            else:
                # Manter intervalo de 10 segundos
                tempo_gasto = time.time() - inicio_ciclo
                tempo_espera = max(1, INTERVALO_COLETA - tempo_gasto)
                time.sleep(tempo_espera)
            
        except Exception as e:
            print(f"❌ Erro no loop: {e}")
            time.sleep(INTERVALO_COLETA)

# =============================================================================
# COLETA HISTÓRICA INICIAL
# =============================================================================

def coleta_historica_inicial():
    """Busca rodadas históricas para preencher o banco."""
    print("📚 Iniciando coleta histórica inicial...")
    
    page = 0
    total_coletadas = 0
    
    while page < MAX_PAGINAS:
        try:
            params = PARAMS.copy()
            params['page'] = page
            params['size'] = 100
            
            print(f"📡 Buscando página {page + 1}/{MAX_PAGINAS}...", end=' ')
            response = session.get(API_URL, params=params, timeout=TIMEOUT_API)
            response.raise_for_status()
            dados = response.json()
            
            if not dados:
                print("✅ Fim do histórico")
                break
            
            # Buscar IDs existentes
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('SELECT id FROM rodadas')
            ids_existentes = {row[0] for row in cur.fetchall()}
            cur.close()
            conn.close()
            
            novas_pagina = 0
            for item in dados:
                rodada = processar_item_api(item)
                if rodada and rodada['id'] and rodada['id'] not in ids_existentes:
                    if salvar_rodada(rodada):
                        novas_pagina += 1
                        total_coletadas += 1
            
            print(f"+{novas_pagina} novas")
            
            if novas_pagina == 0:
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
    print("🚀 BOT BACBO - POSTGRESQL (pg8000) - VERSÃO FINAL")
    print("="*70)
    
    # Inicializar banco de dados
    if init_db():
        print("✅ Banco de dados pronto")
    else:
        print("❌ Falha ao inicializar banco")
        sys.exit(1)
    
    # Atualizar cache inicial
    atualizar_cache_estatisticas()
    
    print(f"📊 {cache['total_rodadas']} rodadas no banco")
    print(f"⚡ Timeout: {TIMEOUT_API}s | Retries: {MAX_RETRIES}")
    print(f"🌐 Porta: {PORT}")
    print("="*70)
    
    # Se banco vazio, iniciar coleta histórica
    if cache['total_rodadas'] < 100:
        historico_thread = threading.Thread(target=coleta_historica_inicial, daemon=True)
        historico_thread.start()
    else:
        print("✅ Banco já populado, pulando coleta histórica")
    
    # Iniciar coleta em tempo real
    coletor_thread = threading.Thread(target=loop_coleta, daemon=True)
    coletor_thread.start()
    
    # Iniciar Flask
    try:
        app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n🛑 Bot encerrado")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
        sys.exit(1)
