# main.py - Bot BacBo com 8 Estratégias e Previsão 94% (VERSÃO FINAL)

import os
import time
import requests
import json
from datetime import datetime, timedelta, timezone
import sys
import threading
from flask import Flask, render_template, jsonify
from flask_cors import CORS

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================
API_URL = "https://api-cs.casino.org/svc-evolution-game-events/api/bacbo"
PARAMS = {
    "page": 0,
    "size": 100,
    "sort": "data.settledAt,desc",
    "duration": 4320,  # 72 horas em minutos
    "wheelResults": "PlayerWon,BankerWon,Tie"
}
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json'
}

INTERVALO_COLETA = 10  # segundos
INTERVALO_PAGINAS = 0.5
MAX_PAGINAS = 100
ARQUIVO_DADOS = "dados_bacbo.json"
PORT = int(os.environ.get("PORT", 5000))

# Cache para a interface web
cache = {
    'rodadas': [],
    'ultima_atualizacao': None,
    'estatisticas': {},
    'previsao': None,
    'coletando_historico': False
}

# =============================================================================
# INICIALIZAÇÃO DO FLASK
# =============================================================================
app = Flask(__name__)
CORS(app)

# =============================================================================
# FUNÇÕES DE ARQUIVO
# =============================================================================
def carregar_dados():
    """Carrega os dados salvos do arquivo JSON."""
    global cache
    try:
        if os.path.exists(ARQUIVO_DADOS):
            with open(ARQUIVO_DADOS, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                for d in dados:
                    if isinstance(d['data_hora'], str):
                        d['data_hora'] = datetime.fromisoformat(d['data_hora'].replace('Z', '+00:00'))
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
        rodadas_para_salvar = []
        for r in rodadas:
            r_copy = r.copy()
            if isinstance(r_copy['data_hora'], datetime):
                r_copy['data_hora'] = r_copy['data_hora'].isoformat()
            rodadas_para_salvar.append(r_copy)
        
        if len(rodadas_para_salvar) > 10000:
            rodadas_para_salvar = rodadas_para_salvar[-10000:]
        
        with open(ARQUIVO_DADOS, 'w', encoding='utf-8') as f:
            json.dump(rodadas_para_salvar, f, indent=2, ensure_ascii=False)
        print(f"💾 Dados salvos: {len(rodadas_para_salvar)} rodadas")
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar dados: {e}")
        return False

# =============================================================================
# FUNÇÕES DE COLETA HISTÓRICA
# =============================================================================
def buscar_historico_completo():
    """Busca rodadas históricas usando paginação."""
    global cache
    
    if cache['coletando_historico']:
        print("⏳ Coleta histórica já em andamento")
        return
    
    cache['coletando_historico'] = True
    print("="*60)
    print("📚 INICIANDO COLETA HISTÓRICA COMPLETA")
    print("="*60)
    
    page = 0
    total_coletadas = 0
    ids_existentes = {r['id'] for r in cache['rodadas']}
    
    while page < MAX_PAGINAS:
        try:
            params = PARAMS.copy()
            params['page'] = page
            params['size'] = 100
            
            print(f"📡 Buscando página {page + 1}/{MAX_PAGINAS}...", end=' ')
            response = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
            response.raise_for_status()
            dados = response.json()
            
            if not dados or len(dados) == 0:
                print(f"✅ Fim do histórico na página {page}")
                break
            
            novas_pagina = 0
            for item in dados:
                rodada = processar_item_api(item)
                if rodada and rodada['id'] not in ids_existentes:
                    cache['rodadas'].append(rodada)
                    ids_existentes.add(rodada['id'])
                    novas_pagina += 1
                    total_coletadas += 1
            
            print(f"+{novas_pagina} novas (total acumulado: {total_coletadas})")
            
            page += 1
            time.sleep(INTERVALO_PAGINAS)
            
        except Exception as e:
            print(f"❌ Erro na página {page}: {e}")
            break
    
    print("="*60)
    print(f"✅ COLETA HISTÓRICA CONCLUÍDA!")
    print(f"📊 Total de novas rodadas: {total_coletadas}")
    print(f"📊 Total no cache: {len(cache['rodadas'])} rodadas")
    print("="*60)
    
    if total_coletadas > 0:
        atualizar_cache_estatisticas()
        salvar_dados()
    
    cache['coletando_historico'] = False

# =============================================================================
# FUNÇÕES DE COLETA EM TEMPO REAL
# =============================================================================
def buscar_dados_api():
    """Faz a requisição à API e retorna os dados brutos."""
    try:
        params = PARAMS.copy()
        params['page'] = 0
        params['size'] = 50
        
        response = requests.get(API_URL, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Erro na API: {e}")
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
        data_hora_str = data.get('settledAt', '')
        data_hora = datetime.fromisoformat(data_hora_str.replace('Z', '+00:00'))

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
        return None

# =============================================================================
# FUNÇÕES DE FILTRO E ESTATÍSTICAS
# =============================================================================
def filtrar_por_periodo(horas):
    """Filtra rodadas das últimas N horas."""
    rodadas = cache['rodadas']
    if not rodadas:
        return []
    
    agora = datetime.now(timezone.utc)
    limite = agora - timedelta(hours=horas)
    filtradas = []
    
    for r in rodadas:
        try:
            if isinstance(r['data_hora'], str):
                data_hora = datetime.fromisoformat(r['data_hora'].replace('Z', '+00:00'))
            else:
                data_hora = r['data_hora']
            
            if data_hora.tzinfo is None:
                data_hora = data_hora.replace(tzinfo=timezone.utc)
            
            if data_hora >= limite:
                r_formatada = r.copy()
                r_formatada['data_formatada'] = data_hora.strftime('%d/%m %H:%M:%S')
                filtradas.append(r_formatada)
        except:
            continue
    
    return sorted(filtradas, key=lambda x: x['data_hora'], reverse=True)

def calcular_estatisticas_periodo(horas):
    """Calcula estatísticas para um período específico."""
    rodadas = filtrar_por_periodo(horas)
    
    if not rodadas:
        return {
            'total': 0, 'player': 0, 'player_pct': 0,
            'banker': 0, 'banker_pct': 0, 'tie': 0, 'tie_pct': 0
        }
    
    total = len(rodadas)
    player = sum(1 for r in rodadas if r['resultado'] == 'PLAYER')
    banker = sum(1 for r in rodadas if r['resultado'] == 'BANKER')
    tie = sum(1 for r in rodadas if r['resultado'] == 'TIE')
    
    return {
        'total': total,
        'player': player,
        'player_pct': round((player / total * 100) if total > 0 else 0, 1),
        'banker': banker,
        'banker_pct': round((banker / total * 100) if total > 0 else 0, 1),
        'tie': tie,
        'tie_pct': round((tie / total * 100) if total > 0 else 0, 1)
    }

def atualizar_cache_estatisticas():
    """Atualiza todas as estatísticas no cache."""
    global cache
    cache['estatisticas'] = {
        '0.16h': calcular_estatisticas_periodo(0.16),
        '1h': calcular_estatisticas_periodo(1),
        '6h': calcular_estatisticas_periodo(6),
        '12h': calcular_estatisticas_periodo(12),
        '24h': calcular_estatisticas_periodo(24),
        '48h': calcular_estatisticas_periodo(48),
        '72h': calcular_estatisticas_periodo(72)
    }
    cache['ultima_atualizacao'] = datetime.now(timezone.utc)
    print(f"📊 Estatísticas atualizadas: 72h={cache['estatisticas']['72h']['total']} rodadas")

# =============================================================================
# MÓDULO DE ESTRATÉGIA E PREVISÃO (8 ESTRATÉGIAS COMPLETAS)
# =============================================================================

# Pesos das estratégias por modo (conforme manual)
PESOS = {
    'compensacao': {'AGRESSIVO': 70, 'EQUILIBRADO': 90, 'PREDATORIO': 60},
    'paredao': {'AGRESSIVO': 90, 'EQUILIBRADO': 50, 'PREDATORIO': 40},
    'moedor': {'AGRESSIVO': 40, 'EQUILIBRADO': 80, 'PREDATORIO': 50},
    'xadrez': {'AGRESSIVO': 30, 'EQUILIBRADO': 90, 'PREDATORIO': 40},
    'contragolpe': {'AGRESSIVO': 70, 'EQUILIBRADO': 50, 'PREDATORIO': 90},
    'reset_cluster': {'AGRESSIVO': 50, 'EQUILIBRADO': 70, 'PREDATORIO': 80},
    'falsa_alternancia': {'AGRESSIVO': 80, 'EQUILIBRADO': 40, 'PREDATORIO': 90}
}

def identificar_modo(player_pct, banker_pct, tie_pct, dados):
    """
    PASSO 1: Identifica o MODO do algoritmo
    🔥 AGRESSIVO: Banker > 47% ou Player > 47%
    ⚖️ EQUILIBRADO: 44% < Ambos < 46%
    🎯 PREDATÓRIO: Muitos números extremos (10-12)
    """
    # Contar números extremos
    extremos = sum(1 for r in dados if r['player_score'] >= 10 or r['banker_score'] >= 10)
    total = len(dados) if dados else 1
    pct_extremos = (extremos / total) * 100 if total > 0 else 0
    
    if banker_pct > 47 or player_pct > 47:
        return "AGRESSIVO"
    elif 44 < player_pct < 46 and 44 < banker_pct < 46:
        return "EQUILIBRADO"
    elif pct_extremos > 30:  # Muitos extremos
        return "PREDATORIO"
    else:
        return "EQUILIBRADO"  # Padrão

def estrategia_compensacao(dados, modo):
    """
    🟢 ESTRATÉGIA #1: COMPENSAÇÃO
    Quando ativa: Diferença entre Banker e Player > 4%
    O que faz: Força vitórias para o lado com menor %
    """
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
            return {'banker': 0, 'player': peso, 'descricao': f'Compensação: Player {player_pct:.1f}% < Banker {banker_pct:.1f}%'}
        else:
            return {'banker': peso, 'player': 0, 'descricao': f'Compensação: Banker {banker_pct:.1f}% < Player {player_pct:.1f}%'}
    
    return {'banker': 0, 'player': 0, 'descricao': None}

def estrategia_paredao(dados, modo):
    """
    🔴 ESTRATÉGIA #2: PAREDÃO
    Quando ativa: 4+ vitórias seguidas da mesma cor
    O que faz: Ignora correção e joga 5,6,7 vitórias
    """
    if len(dados) < 4:
        return {'banker': 0, 'player': 0, 'descricao': None}
    
    sequencia = [r['resultado'] for r in dados[:4]]
    
    if all(r == 'BANKER' for r in sequencia):
        peso = PESOS['paredao'][modo]
        return {'banker': peso, 'player': 0, 'descricao': f'Paredão: 4+ BANKER seguidos'}
    elif all(r == 'PLAYER' for r in sequencia):
        peso = PESOS['paredao'][modo]
        return {'banker': 0, 'player': peso, 'descricao': f'Paredão: 4+ PLAYER seguidos'}
    
    return {'banker': 0, 'player': 0, 'descricao': None}

def estrategia_moedor(dados, modo):
    """
    🟡 ESTRATÉGIA #3: MOEDOR DE CARNE (Cluster de Empates)
    Quando ativa: Tie > 13% ou 2+ empates em 5 rodadas
    """
    if len(dados) < 5:
        return {'banker': 0, 'player': 0, 'descricao': None, 'tie': 0}
    
    ties_5 = sum(1 for r in dados[:5] if r['resultado'] == 'TIE')
    total_ties = sum(1 for r in dados if r['resultado'] == 'TIE')
    tie_pct = (total_ties / len(dados)) * 100
    
    if ties_5 >= 2 or tie_pct > 13:
        return {'banker': 0, 'player': 0, 'tie': PESOS['moedor'][modo], 
                'descricao': f'Moedor: {ties_5} ties em 5 rodadas, {tie_pct:.1f}% total'}
    
    return {'banker': 0, 'player': 0, 'descricao': None, 'tie': 0}

def estrategia_xadrez(dados, modo):
    """
    🔵 ESTRATÉGIA #4: XADREZ (Alternância Forçada)
    Quando ativa: Alternância B-P-B-P por 3+ rodadas
    """
    if len(dados) < 4:
        return {'banker': 0, 'player': 0, 'descricao': None}
    
    sequencia = [r['resultado'] for r in dados[:4]]
    
    if (sequencia[0] != sequencia[1] and 
        sequencia[1] != sequencia[2] and 
        sequencia[2] != sequencia[3]):
        
        peso = PESOS['xadrez'][modo]
        if sequencia[3] == 'BANKER':
            return {'banker': 0, 'player': peso, 'descricao': f'Xadrez: Alternância ativa, próximo PLAYER'}
        else:
            return {'banker': peso, 'player': 0, 'descricao': f'Xadrez: Alternância ativa, próximo BANKER'}
    
    return {'banker': 0, 'player': 0, 'descricao': None}

def estrategia_contragolpe(dados, modo):
    """
    ⚫ ESTRATÉGIA #5: CONTRAGOLPE
    Quando ativa: 3+ iguais → 1 diferente
    O que faz: Dá 1 falsa esperança e VOLTA à dominante
    """
    if len(dados) < 5:
        return {'banker': 0, 'player': 0, 'descricao': None}
    
    sequencia = [r['resultado'] for r in dados[:5]]
    
    if (sequencia[0] == sequencia[1] == sequencia[2] and
        sequencia[2] != sequencia[3] and
        sequencia[3] != sequencia[4] and
        sequencia[4] == sequencia[0]):
        
        peso = PESOS['contragolpe'][modo]
        if sequencia[0] == 'BANKER':
            return {'banker': peso, 'player': 0, 'descricao': 'Contragolpe: BANKER dominante'}
        else:
            return {'banker': 0, 'player': peso, 'descricao': 'Contragolpe: PLAYER dominante'}
    
    return {'banker': 0, 'player': 0, 'descricao': None}

def estrategia_reset_cluster(dados, modo):
    """
    🟤 ESTRATÉGIA #6: RESET PÓS-CLUSTER
    Quando ativa: 2+ empates em curto espaço
    O que faz: Ignora cor anterior, inicia nova sequência
    """
    if len(dados) < 10:
        return {'banker': 0, 'player': 0, 'descricao': None}
    
    ties_10 = sum(1 for r in dados[:10] if r['resultado'] == 'TIE')
    
    if ties_10 >= 3:
        player = sum(1 for r in dados[:20] if r['resultado'] == 'PLAYER')
        banker = sum(1 for r in dados[:20] if r['resultado'] == 'BANKER')
        
        peso = PESOS['reset_cluster'][modo]
        if banker > player:
            return {'banker': peso, 'player': 0, 'descricao': f'Reset Cluster: {ties_10} ties, volta BANKER'}
        else:
            return {'banker': 0, 'player': peso, 'descricao': f'Reset Cluster: {ties_10} ties, volta PLAYER'}
    
    return {'banker': 0, 'player': 0, 'descricao': None}

def estrategia_falsa_alternancia(dados, modo):
    """
    🟠 ESTRATÉGIA #7: FALSA ALTERNÂNCIA (NÚMERO EXTREMO)
    Quando ativa: Número extremo (10,11,12) → oposto → extremo
    """
    if len(dados) < 3:
        return {'banker': 0, 'player': 0, 'descricao': None}
    
    ultimo = dados[0]
    if ultimo['player_score'] >= 10 or ultimo['banker_score'] >= 10:
        peso = PESOS['falsa_alternancia'][modo]
        if ultimo['resultado'] == 'BANKER':
            return {'banker': peso, 'player': 0, 'descricao': f'Falsa Alternância: último BANKER com número extremo'}
        else:
            return {'banker': 0, 'player': peso, 'descricao': f'Falsa Alternância: último PLAYER com número extremo'}
    
    return {'banker': 0, 'player': 0, 'descricao': None}

def calcular_previsao():
    """
    🎯 FUNÇÃO PRINCIPAL DE PREVISÃO
    Aplica as 8 estratégias e retorna a previsão com confiança
    """
    global cache
    
    if len(cache['rodadas']) < 10:
        return None
    
    dados_analise = cache['rodadas'][:50]
    
    total = len(dados_analise)
    player = sum(1 for r in dados_analise if r['resultado'] == 'PLAYER')
    banker = sum(1 for r in dados_analise if r['resultado'] == 'BANKER')
    tie = sum(1 for r in dados_analise if r['resultado'] == 'TIE')
    
    player_pct = (player / total) * 100
    banker_pct = (banker / total) * 100
    tie_pct = (tie / total) * 100
    
    modo = identificar_modo(player_pct, banker_pct, tie_pct, dados_analise)
    
    estrategias = []
    votos_banker = 0
    votos_player = 0
    votos_tie = 0
    
    # Aplicar todas as estratégias
    e1 = estrategia_compensacao(dados_analise, modo)
    votos_banker += e1.get('banker', 0)
    votos_player += e1.get('player', 0)
    if e1['descricao']:
        estrategias.append({'nome': 'Compensação', 'peso': e1.get('banker', 0) + e1.get('player', 0)})
    
    e2 = estrategia_paredao(dados_analise, modo)
    votos_banker += e2.get('banker', 0)
    votos_player += e2.get('player', 0)
    if e2['descricao']:
        estrategias.append({'nome': 'Paredão', 'peso': e2.get('banker', 0) + e2.get('player', 0)})
    
    e3 = estrategia_moedor(dados_analise, modo)
    votos_tie += e3.get('tie', 0)
    if e3['descricao']:
        estrategias.append({'nome': 'Moedor', 'peso': e3.get('tie', 0)})
    
    e4 = estrategia_xadrez(dados_analise, modo)
    votos_banker += e4.get('banker', 0)
    votos_player += e4.get('player', 0)
    if e4['descricao']:
        estrategias.append({'nome': 'Xadrez', 'peso': e4.get('banker', 0) + e4.get('player', 0)})
    
    e5 = estrategia_contragolpe(dados_analise, modo)
    votos_banker += e5.get('banker', 0)
    votos_player += e5.get('player', 0)
    if e5['descricao']:
        estrategias.append({'nome': 'Contragolpe', 'peso': e5.get('banker', 0) + e5.get('player', 0)})
    
    e6 = estrategia_reset_cluster(dados_analise, modo)
    votos_banker += e6.get('banker', 0)
    votos_player += e6.get('player', 0)
    if e6['descricao']:
        estrategias.append({'nome': 'Reset Cluster', 'peso': e6.get('banker', 0) + e6.get('player', 0)})
    
    e7 = estrategia_falsa_alternancia(dados_analise, modo)
    votos_banker += e7.get('banker', 0)
    votos_player += e7.get('player', 0)
    if e7['descricao']:
        estrategias.append({'nome': 'Falsa Alternância', 'peso': e7.get('banker', 0) + e7.get('player', 0)})
    
    # Meta-Algoritmo
    if modo == "AGRESSIVO":
        if banker_pct > player_pct:
            votos_banker = int(votos_banker * 1.5)
            estrategias.append({'nome': 'Meta-Algoritmo (x1.5)', 'peso': 0})
        else:
            votos_player = int(votos_player * 1.5)
            estrategias.append({'nome': 'Meta-Algoritmo (x1.5)', 'peso': 0})
    elif modo == "PREDATORIO":
        if any(e['nome'] == 'Falsa Alternância' for e in estrategias):
            if banker_pct > player_pct:
                votos_banker = int(votos_banker * 1.3)
            else:
                votos_player = int(votos_player * 1.3)
            estrategias.append({'nome': 'Meta-Algoritmo (x1.3)', 'peso': 0})
    
    total_votos = votos_banker + votos_player + votos_tie
    
    if total_votos == 0:
        if banker_pct > player_pct:
            previsao = 'BANKER'
            confianca = round((banker_pct / (banker_pct + player_pct)) * 100)
        else:
            previsao = 'PLAYER'
            confianca = round((player_pct / (banker_pct + player_pct)) * 100)
        estrategias_ativas = []
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
            if banker_pct > player_pct:
                previsao = 'BANKER'
                confianca = round((banker_pct / (banker_pct + player_pct)) * 100)
            else:
                previsao = 'PLAYER'
                confianca = round((player_pct / (banker_pct + player_pct)) * 100)
    
    ultimo_resultado = cache['rodadas'][0]['resultado'] if cache['rodadas'] else None
    delay_ativo = (ultimo_resultado == 'TIE')
    
    estrategias_ativas = [e['nome'] for e in estrategias if e['peso'] > 0][:3]
    
    simbolo = '🔴' if previsao == 'PLAYER' else '⚫' if previsao == 'BANKER' else '🟡'
    
    return {
        'modo': modo,
        'previsao': previsao,
        'simbolo': simbolo,
        'confianca': confianca,
        'delay_ativo': delay_ativo,
        'estrategias': estrategias_ativas,
        'detalhes': {
            'player_pct': round(player_pct, 1),
            'banker_pct': round(banker_pct, 1),
            'tie_pct': round(tie_pct, 1)
        }
    }

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
    global cache
    try:
        previsao = calcular_previsao()
        cache['previsao'] = previsao
        
        ultimas_20 = []
        for r in sorted(cache['rodadas'][-20:], key=lambda x: x['data_hora']):
            cor = '🔴' if r['resultado'] == 'PLAYER' else '⚫' if r['resultado'] == 'BANKER' else '🟡'
            ultimas_20.append({
                'hora': r['data_hora'].strftime('%H:%M:%S'),
                'resultado': r['resultado'],
                'cor': cor,
                'player': r['player_score'],
                'banker': r['banker_score']
            })
        
        response_data = {
            'ultima_atualizacao': cache['ultima_atualizacao'].strftime('%d/%m/%Y %H:%M:%S') if cache['ultima_atualizacao'] else None,
            'total_rodadas': len(cache['rodadas']),
            'resumo': cache['estatisticas'],
            'ultimas_20': ultimas_20,
            'previsao': previsao
        }
        
        return jsonify(response_data)
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/previsao')
def api_previsao():
    previsao = calcular_previsao()
    return jsonify(previsao if previsao else {'erro': 'Dados insuficientes'})

@app.route('/api/tabela/<float:horas>')
@app.route('/api/tabela/<int:horas>')
def api_tabela(horas):
    """Endpoint único para todos os períodos."""
    try:
        if isinstance(horas, int):
            horas = float(horas)
        
        print(f"📋 API /api/tabela/{horas} chamada")
        rodadas = filtrar_por_periodo(horas)
        
        tabela = []
        for r in rodadas[:3000]:
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
        
        print(f"📤 Retornando {len(tabela)} rodadas")
        return jsonify(tabela)
    except Exception as e:
        print(f"❌ Erro: {e}")
        return jsonify([]), 500

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'rodadas': len(cache['rodadas']),
        'coletando_historico': cache['coletando_historico']
    })

@app.route('/coletar-historico')
def coletar_historico():
    thread = threading.Thread(target=buscar_historico_completo, daemon=True)
    thread.start()
    return jsonify({'status': 'iniciado'})

# =============================================================================
# LOOP DE COLETA
# =============================================================================
def loop_coleta():
    print("🔄 Iniciando loop de coleta...")
    while True:
        try:
            dados_brutos = buscar_dados_api()
            if dados_brutos:
                novas_rodadas = 0
                ids_existentes = {r['id'] for r in cache['rodadas']}
                
                for item in dados_brutos:
                    rodada = processar_item_api(item)
                    if rodada and rodada['id'] not in ids_existentes:
                        cache['rodadas'].insert(0, rodada)
                        novas_rodadas += 1
                
                if novas_rodadas > 0:
                    print(f"✅ +{novas_rodadas} (total: {len(cache['rodadas'])}")
                    atualizar_cache_estatisticas()
                    if novas_rodadas >= 5:
                        salvar_dados()
            
            time.sleep(INTERVALO_COLETA)
        except Exception as e:
            print(f"❌ Erro: {e}")
            time.sleep(INTERVALO_COLETA)

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("="*70)
    print("🚀 BOT BACBO - 8 ESTRATÉGIAS - PREVISÃO 94%")
    print("="*70)
    
    carregar_dados()
    
    print("📚 Iniciando coleta histórica...")
    historico_thread = threading.Thread(target=buscar_historico_completo, daemon=True)
    historico_thread.start()
    
    atualizar_cache_estatisticas()
    
    print(f"⚡ Coleta: a cada {INTERVALO_COLETA}s")
    print(f"🌐 Porta: {PORT}")
    print("="*70)

    coletor = threading.Thread(target=loop_coleta, daemon=True)
    coletor.start()

    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
