# main.py - Bot BacBo com 8 Estratégias e Banco Neon

import os
import time
import json
import requests
import psycopg2
from psycopg2 import sql
from datetime import datetime, timedelta
from collections import Counter
import sys

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================
# Banco de Dados Neon (substitua pela sua string de conexão)
DATABASE_URL = "postgresql://neondb_owner:npg_OgR74skiylmJ@ep-long-pond-ai793l7o-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require"

# API do Casino.org (fonte dos dados)
API_URL = "https://api-cs.casino.org/svc-evolution-game-events/api/bacbo"
PARAMS = {
    "page": 0,
    "size": 20,  # Pega um lote maior para análise
    "sort": "data.settledAt,desc",
    "duration": 30,
    "wheelResults": "PlayerWon,BankerWon,Tie"
}
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# Intervalo de coleta (segundos) - 10s é bom para tempo real
INTERVALO COLETA = 10

# =============================================================================
# FUNÇÕES DO BANCO DE DADOS (Neon)
# =============================================================================
def conectar_banco():
    """Conecta ao banco PostgreSQL no Neon."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
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
            # Índice para buscas rápidas por data/hora
            cur.execute("CREATE INDEX IF NOT EXISTS idx_data_hora ON rodadas_bacbo(data_hora DESC);")
            conn.commit()
            print("✅ Tabela 'rodadas_bacbo' verificada/criada com sucesso.")
    except Exception as e:
        print(f"❌ Erro ao criar tabela: {e}")
        conn.rollback()

def inserir_rodada(conn, rodada):
    """Insere uma nova rodada no banco, ignorando conflitos (duplicatas)."""
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
            return cur.rowcount > 0  # Retorna True se inseriu (nova rodada)
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

def calcular_estatisticas_gerais(conn, periodo_minutos=30):
    """Calcula Player%, Banker%, Tie% para um período recente."""
    try:
        since = datetime.now() - timedelta(minutes=periodo_minutos)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) FILTER (WHERE resultado = 'PlayerWon') as player_count,
                    COUNT(*) FILTER (WHERE resultado = 'BankerWon') as banker_count,
                    COUNT(*) FILTER (WHERE resultado = 'Tie') as tie_count,
                    COUNT(*) as total
                FROM rodadas_bacbo
                WHERE data_hora >= %s;
            """, (since,))
            row = cur.fetchone()
            if row and row[3] > 0:
                total = row[3]
                return {
                    'player_pct': (row[0] / total) * 100,
                    'banker_pct': (row[1] / total) * 100,
                    'tie_pct': (row[2] / total) * 100,
                    'total': total
                }
            else:
                return {'player_pct': 0, 'banker_pct': 0, 'tie_pct': 0, 'total': 0}
    except Exception as e:
        print(f"❌ Erro ao calcular estatísticas: {e}")
        return {'player_pct': 0, 'banker_pct': 0, 'tie_pct': 0, 'total': 0}

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

        # Mapear resultado para o formato que usamos
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
# MÓDULO DE ESTRATÉGIA E PREDIÇÃO (Baseado no seu manual)
# =============================================================================
def identificar_modo(estats):
    """Passo 1: Identifica o modo do algoritmo com base nas estatísticas."""
    diff = abs(estats['banker_pct'] - estats['player_pct'])
    if diff > 4:
        return "🔥 AGRESSIVO"
    elif 44 < estats['player_pct'] < 46 and 44 < estats['banker_pct'] < 46:
        return "⚖️ EQUILIBRADO"
    else:
        # Lógica para detectar modo Predatório (pode ser refinada com análise de extremos)
        return "🎯 PREDATÓRIO"

def analisar_historico(historico):
    """
    Passo 5: Roda as 8 estratégias no histórico recente.
    Retorna um dicionário com a contagem de votos para PLAYER, BANKER e os pesos aplicados.
    """
    if len(historico) < 5:
        return {'PLAYER': 0, 'BANKER': 0, 'detalhes': {}}  # Precisa de histórico mínimo

    # Mapear sequência de resultados
    sequencia = [h['resultado'] for h in historico]
    ultimo_resultado = sequencia[0] if sequencia else None
    penultimo = sequencia[1] if len(sequencia) > 1 else None

    # Contadores para estratégias
    votos = {'PLAYER': 0, 'BANKER': 0}
    detalhes = {}

    # --- Estratégia #2: PAREDÃO (Detecta 4+ iguais) ---
    if len(sequencia) >= 4 and all(r == sequencia[0] for r in sequencia[:4]):
        votos[sequencia[0]] += 90
        detalhes['Paredão'] = f"+90 para {sequencia[0]}"
    elif len(sequencia) >= 3 and all(r == sequencia[0] for r in sequencia[:3]):
        votos[sequencia[0]] += 50 # Peso menor para 3 iguais
        detalhes['Paredão (3)'] = f"+50 para {sequencia[0]}"

    # --- Estratégia #4: XADREZ (Alternância B-P-B-P) ---
    if len(sequencia) >= 4:
        if sequencia[0] != sequencia[1] and sequencia[1] != sequencia[2] and sequencia[2] != sequencia[3]:
            # Alternância pura, a próxima seria o oposto do último
            proxima_alternancia = 'PLAYER' if sequencia[0] == 'BANKER' else 'BANKER'
            votos[proxima_alternancia] += 90
            detalhes['Xadrez'] = f"+90 para {proxima_alternancia}"

    # --- Estratégia #5: CONTRAGOLPE (3+ iguais -> 1 diferente) ---
    if len(sequencia) >= 4 and sequencia[0] != sequencia[1] and sequencia[1] == sequencia[2] == sequencia[3]:
        # Padrão: Diferente, Igual, Igual, Igual (ex: P, B, B, B) -> a tendência é voltar para B
        votos[sequencia[1]] += 70
        detalhes['Contragolpe'] = f"+70 para {sequencia[1]} (volta à dominante)"

    # --- Estratégia #7: FALSA ALTERNÂNCIA (Números extremos) ---
    # Simplificação: Se o último resultado foi com um número extremo (>=10) de um lado e o oponente baixo
    ultimo = historico[0]
    if ultimo['player_score'] >= 10 or ultimo['banker_score'] >= 10:
        # Se houve extremo, a tendência é manter a força (ou seja, repetir o mesmo lado)
        votos[ultimo['resultado']] += 80
        detalhes['Falsa Alternância'] = f"+80 para {ultimo['resultado']} (extremo)"

    # --- Outras estratégias podem ser implementadas aqui (Compensação, Moedor, etc.) ---

    return {'PLAYER': votos['PLAYER'], 'BANKER': votos['BANKER'], 'detalhes': detalhes}

def prever_proxima_cor(conn):
    """Função principal que coordena a predição."""
    print("\n" + "="*60)
    print("🧠 INICIANDO ANÁLISE PARA PREDIÇÃO")
    print("="*60)

    # 1. Buscar estatísticas gerais do período
    estats = calcular_estatisticas_gerais(conn, periodo_minutos=30)
    print(f📊 "Estatísticas (últimos 30 min): Player {estats['player_pct']:.1f}%, Banker {estats['banker_pct']:.1f}%, Tie {estats['tie_pct']:.1f}%")

    # 2. Identificar o modo
    modo = identificar_modo(estats)
    print(f"🎯 Modo detectado: {modo}")

    # 3. Buscar histórico recente (últimas 20 rodadas) para análise fina
    historico = buscar_ultimas_rodadas(conn, limite=20)
    if not historico:
        print("⚠️ Histórico insuficiente para predição.")
        return None

    print(f"📜 Histórico (últimas {len(historico)}): {[h['resultado'] for h in historico]}")

    # 4. Aplicar as estratégias no histórico
    votos = analisar_historico(historico)

    # 5. Aplicar pesos do modo (Meta-Algoritmo - Estratégia #8)
    if "AGRESSIVO" in modo:
        # No modo agressivo, dobra o peso da cor dominante (se houver)
        if estats['banker_pct'] > estats['player_pct'] + 2:
            votos['BANKER'] = votos['BANKER'] * 1.5
            print("⚡ Meta-Algoritmo: Modo AGRESSIVO, BANKER dominante -> peso dobrado para BANKER")
        elif estats['player_pct'] > estats['banker_pct'] + 2:
            votos['PLAYER'] = votos['PLAYER'] * 1.5
            print("⚡ Meta-Algoritmo: Modo AGRESSIVO, PLAYER dominante -> peso dobrado para PLAYER")

    print(f"🗳️ Votos finais (ponderados): PLAYER={votos['PLAYER']:.0f}, BANKER={votos['BANKER']:.0f}")
    print(f"📋 Detalhes: {votos['detalhes']}")

    # 6. Decidir a previsão
    if votos['BANKER'] > votos['PLAYER']:
        previsao = 'BANKER'
        confianca = (votos['BANKER'] / (votos['BANKER'] + votos['PLAYER'] + 0.01)) * 100
    elif votos['PLAYER'] > votos['BANKER']:
        previsao = 'PLAYER'
        confianca = (votos['PLAYER'] / (votos['BANKER'] + votos['PLAYER'] + 0.01)) * 100
    else:
        previsao = 'INDEFINIDO (possível TIE)'
        confianca = 0

    # 7. Aplicar regra de delay pós-empate (Estratégia #3 e #6)
    delay_ativo = False
    if historico and historico[0]['resultado'] == 'TIE':
        delay_ativo = True
        print("⏸️ DELAY PÓS-EMPATE ATIVO: Não apostar na próxima rodada.")

    # 8. Exibir resultado final
    print("\n" + "="*60)
    print("🎯 RESULTADO DA PREDIÇÃO")
    print("="*60)
    if delay_ativo:
        print("⚠️ AGUARDE: Delay pós-empate. Próxima rodada deve ser ignorada.")
    else:
        cor_simbolo = '🔴' if previsao == 'PLAYER' else '⚫' if previsao == 'BANKER' else '⚪'
        print(f"{cor_simbolo} PRÓXIMA COR: {previsao}")
        print(f"📈 CONFIANÇA: {confianca:.1f}%")
        print(f"🧠 ESTRATÉGIAS ATIVAS: {', '.join(votos['detalhes'].keys()) if votos['detalhes'] else 'Análise básica'}")
        print(f"🛡️ PROTEÇÃO TIE: {estats['tie_pct']:.1f}% (nos últimos 30min)")

    return previsao

# =============================================================================
# LOOP PRINCIPAL 24/7
# =============================================================================
def main():
    print("🚀 Iniciando Bot BacBo com Banco Neon e Estratégias Avançadas...")
    conn = conectar_banco()
    if not conn:
        print("❌ Falha crítica na conexão com o banco. Encerrando.")
        sys.exit(1)

    criar_tabela(conn)

    print(f"⏱️  Coletando dados a cada {INTERVALO_COLETA} segundos. Modo 24/7 ativo.")
    print("="*60)

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
                    print(f"✅ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {novas_rodadas} novas rodadas inseridas.")
                else:
                    print(f"⏳ {datetime.now().strftime('%H:%M:%S')} - Nenhuma rodada nova.")

                # A cada 6 ciclos (aprox 1 minuto), fazer uma predição
                if ciclo_coleta % 6 == 0:
                    prever_proxima_cor(conn)

            else:
                print(f"⚠️ {datetime.now().strftime('%H:%M:%S')} - Falha ao obter dados da API.")

            time.sleep(INTERVALO_COLETA)

        except KeyboardInterrupt:
            print("\n🛑 Bot interrompido pelo usuário.")
            if conn:
                conn.close()
            sys.exit(0)
        except Exception as e:
            print(f"❌ Erro inesperado no loop principal: {e}")
            time.sleep(INTERVALO_COLETA)

if __name__ == "__main__":
    main()
