# main.py - Bot BacBo com Web Interface e JSON (SEM BANCO DE DADOS)

import os
import time
import requests
import json
from datetime import datetime, timedelta
import sys
import threading
from collections import Counter
from flask import Flask, render_template, jsonify

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
ARQUIVO_DADOS = "dados_bacbo.json"

# Cache para a interface web
cache = {
    'rodadas': [],
    'ultima_atualizacao': None,
    'estatisticas': {},
    'previsao': None
}

# =============================================================================
# INICIALIZAÇÃO DO FLASK
# =============================================================================
app = Flask(__name__)

# =============================================================================
# FUNÇÕES DE ARQUIVO (JSON)
# =============================================================================
def carregar_dados():
    """Carrega os dados salvos do arquivo JSON."""
    global cache
    try:
        if os.path.exists(ARQUIVO_DADOS):
            with open(ARQUIVO_DADOS, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                print(f"✅ Carregadas {len(dados)} rodadas do arquivo")
                cache['rodadas'] = dados
                return dados
        else:
            print("📁 Arquivo de dados não encontrado, iniciando novo")
            cache['rodadas'] = []
            return []
    except Exception as e:
        print(f"⚠️ Erro ao carregar dados: {e}")
        cache['rodadas'] = []
        return []

def salvar_dados():
    """Salva os dados no arquivo JSON."""
    global cache
    try:
        rodadas = cache['rodadas']
        # Manter apenas últimas 10000 rodadas
        if len(rodadas) > 10000:
            rodadas = rodadas[-10000:]
            cache['rodadas'] = rodadas
        
        with open(ARQUIVO_DADOS, 'w', encoding='utf-8') as f:
            json.dump(rodadas, f, indent=2, ensure_ascii=False, default=str)
        print(f"💾 Dados salvos: {len(rodadas)} rodadas")
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar dados: {e}")
        return False

# =============================================================================
# FUNÇÕES DE FILTRO E ESTATÍSTICAS
# =============================================================================
def filtrar_por_periodo(horas):
    """Filtra rodadas das últimas N horas."""
    rodadas = cache['rodadas']
    if not rodadas:
        return []
    
    limite = datetime.now() - timedelta(hours=horas)
    filtradas = []
    
    for r in rodadas:
        try:
            if isinstance(r['data_hora'], str):
                data_hora = datetime.fromisoformat(r['data_hora'].replace('Z', '+00:00'))
            else:
                data_hora = r['data_hora']
            
            if data_hora >= limite:
                # Formatar para exibição
                r_formatada = r.copy()
                r_formatada['data_formatada'] = data_hora.strftime('%d/%m %H:%M')
                filtradas.append(r_formatada)
        except Exception as e:
            continue
    
    return sorted(filtradas, key=lambda x: x['data_hora'], reverse=True)

def calcular_estatisticas_periodo(horas):
    """Calcula estatísticas para um período específico."""
    rodadas = filtrar_por_periodo(horas)
    
    if not rodadas:
        return {
            'total': 0, 'player': 0, 'player_pct': 0,
            'banker': 0, 'banker_pct': 0, 'tie': 0, 'tie_pct': 0,
            'media_player': 0, 'media_banker': 0
        }
    
    total = len(rodadas)
    player = sum(1 for r in rodadas if r['resultado'] == 'PLAYER')
    banker = sum(1 for r in rodadas if r['resultado'] == 'BANKER')
    tie = sum(1 for r in rodadas if r['resultado'] == 'TIE')
    
    media_player = sum(r['player_score'] for r in rodadas) / total
    media_banker = sum(r['banker_score'] for r in rodadas) / total
    
    return {
        'total': total,
        'player': player,
        'player_pct': (player / total * 100) if total > 0 else 0,
        'banker': banker,
        'banker_pct': (banker / total * 100) if total > 0 else 0,
        'tie': tie,
        'tie_pct': (tie / total * 100) if total > 0 else 0,
        'media_player': round(media_player, 1),
        'media_banker': round(media_banker, 1)
    }

def atualizar_cache_estatisticas():
    """Atualiza todas as estatísticas no cache."""
    global cache
    cache['estatisticas'] = {
        '1h': calcular_estatisticas_periodo(1),
        '6h': calcular_estatisticas_periodo(6),
        '12h': calcular_estatisticas_periodo(12),
        '24h': calcular_estatisticas_periodo(24),
        '48h': calcular_estatisticas_periodo(48),
        '72h': calcular_estatisticas_periodo(72)
    }
    cache['ultima_atualizacao'] = datetime.now()

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
            'data_hora': datetime.fromisoformat(data.get('settledAt', '').replace('Z', '+00:00')),
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

def calcular_previsao():
    """Calcula a previsão da próxima cor baseada nos dados atuais."""
    global cache
    
    rodadas = cache['rodadas']
    if len(rodadas) < 10:
        return None
    
    # Estatísticas dos últimos 30 min
    recentes = [r for r in rodadas if r['data_hora'] > datetime.now() - timedelta(minutes=30)]
    
    if not recentes:
        recentes = rodadas[-20:]
    
    # Calcular percentuais
    total = len(recentes)
    player = sum(1 for r in recentes if r['resultado'] == 'PLAYER')
    banker = sum(1 for r in recentes if r['resultado'] == 'BANKER')
    tie = sum(1 for r in recentes if r['resultado'] == 'TIE')
    
    estats = {
        'player_pct': (player / total * 100) if total > 0 else 0,
        'banker_pct': (banker / total * 100) if total > 0 else 0,
        'tie_pct': (tie / total * 100) if total > 0 else 0
    }
    
    modo = identificar_modo(estats)
    
    # Últimas 20 rodadas para análise detalhada
    historico = sorted(rodadas[-20:], key=lambda x: x['data_hora'], reverse=True)
    votos = analisar_historico(historico)
    
    # Aplicar pesos do modo
    if "AGRESSIVO" in modo:
        if estats['banker_pct'] > estats['player_pct'] + 2:
            votos['BANKER'] = int(votos['BANKER'] * 1.5)
        elif estats['player_pct'] > estats['banker_pct'] + 2:
            votos['PLAYER'] = int(votos['PLAYER'] * 1.5)
    
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
    
    return {
        'previsao': previsao,
        'confianca': round(confianca, 1),
        'modo': modo,
        'delay_ativo': delay_ativo,
        'player_pct': round(estats['player_pct'], 1),
        'banker_pct': round(estats['banker_pct'], 1),
        'tie_pct': round(estats['tie_pct'], 1),
        'votos': votos
    }

# =============================================================================
# ROTAS DO FLASK (WEB INTERFACE)
# =============================================================================
@app.route('/')
def index():
    """Página principal."""
    return render_template('index.html')

@app.route('/api/stats')
def api_stats():
    """Retorna estatísticas em JSON."""
    global cache
    
    # Atualizar previsão
    cache['previsao'] = calcular_previsao()
    
    # Últimas 20 rodadas para o gráfico
    ultimas_20 = []
    for r in sorted(cache['rodadas'][-20:], key=lambda x: x['data_hora']):
        cor = '🔴' if r['resultado'] == 'PLAYER' else '⚫' if r['resultado'] == 'BANKER' else '🟡'
        ultimas_20.append({
            'hora': r['data_hora'].strftime('%H:%M'),
            'resultado': r['resultado'],
            'cor': cor,
            'player': r['player_score'],
            'banker': r['banker_score']
        })
    
    return jsonify({
        'ultima_atualizacao': cache['ultima_atualizacao'].strftime('%d/%m/%Y %H:%M:%S') if cache['ultima_atualizacao'] else None,
        'total_rodadas': len(cache['rodadas']),
        'resumo': cache['estatisticas'],
        'ultimas_20': ultimas_20,
        'previsao': cache['previsao']
    })

@app.route('/api/tabela/<int:horas>')
def api_tabela(horas):
    """Retorna tabela de rodadas para um período."""
    rodadas = filtrar_por_periodo(horas)
    
    tabela = []
    for r in rodadas[:100]:  # Limitar a 100 registros
        cor = '🔴' if r['resultado'] == 'PLAYER' else '⚫' if r['resultado'] == 'BANKER' else '🟡'
        tabela.append({
            'data': r['data_formatada'],
            'player': r['player_score'],
            'banker': r['banker_score'],
            'resultado': r['resultado'],
            'cor': cor,
            'mult': f"{r['multiplicador']}x",
            'winners': r['total_winners'],
            'premio': f"€{r['total_amount']:,.0f}" if r['total_amount'] else '€0'
        })
    
    return jsonify(tabela)

# =============================================================================
# LOOP DE COLETA (RODA EM THREAD SEPARADA)
# =============================================================================
def loop_coleta():
    """Loop principal de coleta de dados."""
    global cache
    
    while True:
        try:
            dados_brutos = buscar_dados_api()

            if dados_brutos:
                novas_rodadas = 0
                ids_existentes = {r['id'] for r in cache['rodadas']}
                
                for item in dados_brutos:
                    rodada = processar_item_api(item)
                    if rodada and rodada['id'] not in ids_existentes:
                        cache['rodadas'].append(rodada)
                        novas_rodadas += 1

                if novas_rodadas > 0:
                    print(f"✅ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - +{novas_rodadas} novas (total: {len(cache['rodadas'])}")
                    
                    # Atualizar estatísticas
                    atualizar_cache_estatisticas()
                    
                    # Salvar a cada 10 novas rodadas
                    if novas_rodadas >= 10:
                        salvar_dados()
                else:
                    print(f"⏳ {datetime.now().strftime('%H:%M:%S')} - Nenhuma nova")

            time.sleep(INTERVALO_COLETA)

        except Exception as e:
            print(f"❌ Erro no loop: {e}")
            time.sleep(INTERVALO_COLETA)

# =============================================================================
# MAIN
# =============================================================================
def main():
    print("="*60)
    print("🚀 BOT BACBO COM WEB INTERFACE - INICIANDO")
    print("="*60)
    
    # Carregar dados existentes
    carregar_dados()
    
    # Atualizar estatísticas iniciais
    atualizar_cache_estatisticas()
    
    print(f"⏱️  Coletando dados a cada {INTERVALO_COLETA} segundos")
    print(f"🌐 Interface web: http://localhost:5000 (ou URL do Railway)")
    print("="*60)

    # Iniciar thread de coleta
    coletor = threading.Thread(target=loop_coleta, daemon=True)
    coletor.start()

    # Iniciar Flask (bloqueante)
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n🛑 Bot interrompido")
        salvar_dados()
        sys.exit(0)

if __name__ == "__main__":
    main()
