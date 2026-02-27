# main.py - Bot BacBo SEM Banco de Dados (usa JSON local)

import os
import time
import requests
import json
from datetime import datetime, timedelta
import sys
from collections import Counter

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================
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

# Arquivo para salvar os dados
ARQUIVO_DADOS = "dados_bacbo.json"

# =============================================================================
# FUNÇÕES DE ARQUIVO (substituem o banco de dados)
# =============================================================================
def carregar_dados():
    """Carrega os dados salvos do arquivo JSON."""
    try:
        if os.path.exists(ARQUIVO_DADOS):
            with open(ARQUIVO_DADOS, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                print(f"✅ Carregados {len(dados)} rodadas do arquivo")
                return dados
        else:
            print("📁 Arquivo de dados não encontrado, iniciando novo")
            return []
    except Exception as e:
        print(f"⚠️ Erro ao carregar dados: {e}")
        return []

def salvar_dados(rodadas):
    """Salva os dados no arquivo JSON."""
    try:
        # Manter apenas últimas 5000 rodadas para não ficar muito grande
        if len(rodadas) > 5000:
            rodadas = rodadas[-5000:]
        
        with open(ARQUIVO_DADOS, 'w', encoding='utf-8') as f:
            json.dump(rodadas, f, indent=2, ensure_ascii=False, default=str)
        print(f"💾 Dados salvos: {len(rodadas)} rodadas")
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar dados: {e}")
        return False

def buscar_rodadas_periodo(rodadas, horas=72):
    """Filtra rodadas das últimas N horas."""
    if not rodadas:
        return []
    
    limite = datetime.now() - timedelta(hours=horas)
    filtradas = []
    
    for r in rodadas:
        try:
            # Converter string para datetime
            data_hora = datetime.fromisoformat(r['data_hora'].replace('Z', '+00:00')) if isinstance(r['data_hora'], str) else r['data_hora']
            if data_hora >= limite:
                filtradas.append(r)
        except:
            continue
    
    return filtradas

def calcular_estatisticas(rodadas, horas=72):
    """Calcula estatísticas para um período."""
    periodo = buscar_rodadas_periodo(rodadas, horas)
    
    if not periodo:
        return {
            'total': 0, 'player': 0, 'player_pct': 0,
            'banker': 0, 'banker_pct': 0, 'tie': 0, 'tie_pct': 0
        }
    
    total = len(periodo)
    player = sum(1 for r in periodo if r['resultado'] == 'PLAYER')
    banker = sum(1 for r in periodo if r['resultado'] == 'BANKER')
    tie = sum(1 for r in periodo if r['resultado'] == 'TIE')
    
    return {
        'total': total,
        'player': player,
        'player_pct': (player / total * 100) if total > 0 else 0,
        'banker': banker,
        'banker_pct': (banker / total * 100) if total > 0 else 0,
        'tie': tie,
        'tie_pct': (tie / total * 100) if total > 0 else 0
    }

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
    """Converte um item da API para o formato que usamos."""
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
            'data_hora': datetime.fromisoformat(data.get('settledAt', '').replace('Z', '+00:00')).isoformat(),
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

def prever_proxima_cor(rodadas):
    """Faz a previsão da próxima cor."""
    print("\n" + "="*60)
    print("🧠 INICIANDO ANALISE PARA PREDICAO")
    print("="*60)

    # Estatísticas dos últimos 30 min
    recentes = [r for r in rodadas if datetime.fromisoformat(r['data_hora']) > datetime.now() - timedelta(minutes=30)]
    
    if not recentes:
        print("⚠️ Dados insuficientes para análise")
        return None
    
    estats = calcular_estatisticas(rodadas, 0.5)  # 30 min
    
    print(f"📊 Estatisticas (ultimos 30 min): Player {estats['player_pct']:.1f}%, Banker {estats['banker_pct']:.1f}%, Tie {estats['tie_pct']:.1f}%")

    modo = identificar_modo(estats)
    print(f"🎯 Modo detectado: {modo}")

    # Últimas 20 rodadas para análise
    historico = sorted(rodadas[-20:], key=lambda x: x['data_hora'], reverse=True)
    
    votos = analisar_historico(historico)

    # Aplicar pesos do modo
    if "AGRESSIVO" in modo:
        if estats['banker_pct'] > estats['player_pct'] + 2:
            votos['BANKER'] = int(votos['BANKER'] * 1.5)
        elif estats['player_pct'] > estats['banker_pct'] + 2:
            votos['PLAYER'] = int(votos['PLAYER'] * 1.5)

    print(f"🗳️ Votos: PLAYER={votos['PLAYER']}, BANKER={votos['BANKER']}")
    
    if votos['detalhes']:
        print(f"📋 Estrategias: {votos['detalhes']}")

    # Decidir previsão
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

    print("\n" + "="*60)
    print("🎯 RESULTADO DA PREDICAO")
    print("="*60)
    
    if delay_ativo:
        print("⚠️ DELAY POS-EMPATE ATIVO - Aguardar")
    else:
        simbolo = "🔴" if previsao == "PLAYER" else "⚫" if previsao == "BANKER" else "⚪"
        print(f"{simbolo} PROXIMA COR: {previsao}")
        print(f"📈 CONFIANCA: {confianca:.1f}%")

    return previsao

# =============================================================================
# LOOP PRINCIPAL
# =============================================================================
def main():
    print("="*60)
    print("🚀 BOT BACBO - VERSÃO SEM BANCO DE DADOS")
    print("="*60)
    
    # Carregar dados existentes
    rodadas = carregar_dados()
    
    print(f"⏱️  Coletando dados a cada {INTERVALO_COLETA} segundos.")
    print("="*60)

    ciclo_coleta = 0
    while True:
        try:
            ciclo_coleta += 1
            dados_brutos = buscar_dados_api()

            if dados_brutos:
                novas_rodadas = 0
                ids_existentes = {r['id'] for r in rodadas}
                
                for item in dados_brutos:
                    rodada = processar_item_api(item)
                    if rodada and rodada['id'] not in ids_existentes:
                        rodadas.append(rodada)
                        novas_rodadas += 1

                if novas_rodadas > 0:
                    print(f"✅ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - +{novas_rodadas} novas rodadas (total: {len(rodadas)})")
                    
                    # Salvar a cada 10 novas rodadas
                    if novas_rodadas >= 10:
                        salvar_dados(rodadas)
                    
                    # A cada 6 ciclos (1 minuto), fazer predição
                    if ciclo_coleta % 6 == 0:
                        prever_proxima_cor(rodadas)
                else:
                    print(f"⏳ {datetime.now().strftime('%H:%M:%S')} - Nenhuma rodada nova")

            time.sleep(INTERVALO_COLETA)

        except KeyboardInterrupt:
            print("\n🛑 Bot interrompido")
            salvar_dados(rodadas)
            sys.exit(0)
        except Exception as e:
            print(f"❌ Erro: {e}")
            time.sleep(INTERVALO_COLETA)

if __name__ == "__main__":
    main()
