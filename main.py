# main.py - Bot BacBo com Coleta RÁPIDA (5s) e 3000 registros

import os
import time
import requests
import json
from datetime import datetime, timedelta, timezone
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
    "size": 100,
    "sort": "data.settledAt,desc",
    "duration": 4320,  # 72 horas em minutos
    "wheelResults": "PlayerWon,BankerWon,Tie"
}
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json'
}

# INTERVALOS AJUSTADOS
INTERVALO_COLETA = 5  # ⚡ 5 segundos (tempo real)
INTERVALO_PAGINAS = 0.5  # 0.5 segundo entre páginas históricas
MAX_PAGINAS = 100  # Máximo de páginas para histórico
MAX_REGISTROS_TABELA = 3000  # 📊 3000 registros na tabela

ARQUIVO_DADOS = "dados_bacbo.json"
PORT = int(os.environ.get("PORT", 5000))

# Cache
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
        
        # Manter últimas 10000 rodadas
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
# FUNÇÕES DE COLETA HISTÓRICA (OTIMIZADA)
# =============================================================================
def buscar_historico_completo():
    """Busca rodadas históricas usando paginação rápida."""
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
            
            # Pausa curta entre páginas (0.5 segundos)
            time.sleep(INTERVALO_PAGINAS)
            
        except Exception as e:
            print(f"❌ Erro na página {page}: {e}")
            break
    
    print("="*60)
    print(f"✅ COLETA HISTÓRICA CONCLUÍDA!")
    print(f"📊 Total de novas rodadas: {total_coletadas}")
    print(f"📊 Total no cache: {len(cache['rodadas'])} rodadas")
    print("="*60)
    
    # Atualizar estatísticas e salvar
    if total_coletadas > 0:
        atualizar_cache_estatisticas()
        salvar_dados()
    
    cache['coletando_historico'] = False

# =============================================================================
# FUNÇÕES DE COLETA EM TEMPO REAL (5 SEGUNDOS)
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
                r_formatada['data_formatada'] = data_hora.strftime('%d/%m %H:%M:%S')  # ⏱️ com segundos
                filtradas.append(r_formatada)
        except:
            continue
    
    return sorted(filtradas, key=lambda x: x['data_hora'], reverse=True)

def calcular_estatisticas_periodo(horas):
    """Calcula estatísticas para um período específico."""
    rodadas = filtrar_por_periodo(horas)
    
    if not rodadas:
        return {'total': 0, 'player': 0, 'player_pct': 0, 'banker': 0, 'banker_pct': 0, 'tie': 0, 'tie_pct': 0}
    
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
        '1h': calcular_estatisticas_periodo(1),
        '6h': calcular_estatisticas_periodo(6),
        '12h': calcular_estatisticas_periodo(12),
        '24h': calcular_estatisticas_periodo(24),
        '48h': calcular_estatisticas_periodo(48),
        '72h': calcular_estatisticas_periodo(72)
    }
    cache['ultima_atualizacao'] = datetime.now(timezone.utc)
    print(f"📊 72h: {cache['estatisticas']['72h']['total']} rodadas")

# =============================================================================
# MÓDULO DE ESTRATÉGIA E PREDIÇÃO
# =============================================================================
def identificar_modo(estats):
    diff = abs(estats['banker_pct'] - estats['player_pct'])
    if diff > 4:
        return "AGRESSIVO"
    elif 44 < estats['player_pct'] < 46 and 44 < estats['banker_pct'] < 46:
        return "EQUILIBRADO"
    else:
        return "PREDATORIO"

def analisar_historico(historico):
    if len(historico) < 5:
        return {'PLAYER': 0, 'BANKER': 0, 'detalhes': {}}

    sequencia = [h['resultado'] for h in historico]
    votos = {'PLAYER': 0, 'BANKER': 0}
    detalhes = {}

    # Estratégia #2: PAREDÃO
    if len(sequencia) >= 4 and all(r == sequencia[0] for r in sequencia[:4]):
        votos[sequencia[0]] += 90
        detalhes['Paredao'] = f"+90 {sequencia[0]}"
    
    # Estratégia #4: XADREZ
    if len(sequencia) >= 4:
        if sequencia[0] != sequencia[1] and sequencia[1] != sequencia[2] and sequencia[2] != sequencia[3]:
            proxima = 'PLAYER' if sequencia[0] == 'BANKER' else 'BANKER'
            votos[proxima] += 90
            detalhes['Xadrez'] = f"+90 {proxima}"

    # Estratégia #5: CONTRAGOLPE
    if len(sequencia) >= 4 and sequencia[0] != sequencia[1] and sequencia[1] == sequencia[2] == sequencia[3]:
        votos[sequencia[1]] += 70
        detalhes['Contragolpe'] = f"+70 {sequencia[1]}"

    # Estratégia #7: FALSA ALTERNÂNCIA
    if historico and len(historico) > 0:
        ultimo = historico[0]
        if ultimo['player_score'] >= 10 or ultimo['banker_score'] >= 10:
            votos[ultimo['resultado']] += 80
            detalhes['Falsa'] = f"+80 {ultimo['resultado']}"

    return {'PLAYER': votos['PLAYER'], 'BANKER': votos['BANKER'], 'detalhes': detalhes}

def calcular_previsao():
    global cache
    rodadas = cache['rodadas']
    
    if len(rodadas) < 10:
        return None
    
    agora = datetime.now(timezone.utc)
    limite = agora - timedelta(minutes=30)
    
    recentes = [r for r in rodadas if r['data_hora'] >= limite]
    if not recentes:
        recentes = rodadas[-20:]
    
    total = len(recentes)
    player = sum(1 for r in recentes if r['resultado'] == 'PLAYER')
    banker = sum(1 for r in recentes if r['resultado'] == 'BANKER')
    tie = sum(1 for r in recentes if r['resultado'] == 'TIE')
    
    estats = {
        'player_pct': (player / total * 100),
        'banker_pct': (banker / total * 100),
        'tie_pct': (tie / total * 100)
    }
    
    modo = identificar_modo(estats)
    historico = sorted(rodadas[-20:], key=lambda x: x['data_hora'], reverse=True)
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
        'confianca': round(confianca, 1),
        'modo': modo,
        'delay_ativo': delay_ativo,
        'player_pct': round(estats['player_pct'], 1),
        'banker_pct': round(estats['banker_pct'], 1),
        'tie_pct': round(estats['tie_pct'], 1)
    }

# =============================================================================
# ROTAS DO FLASK
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
        cache['previsao'] = calcular_previsao()
        
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
        
        return jsonify({
            'ultima_atualizacao': cache['ultima_atualizacao'].strftime('%d/%m/%Y %H:%M:%S') if cache['ultima_atualizacao'] else None,
            'total_rodadas': len(cache['rodadas']),
            'resumo': cache['estatisticas'],
            'ultimas_20': ultimas_20,
            'previsao': cache['previsao']
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/tabela/<int:horas>')
def api_tabela(horas):
    try:
        rodadas = filtrar_por_periodo(horas)
        
        tabela = []
        for r in rodadas[:MAX_REGISTROS_TABELA]:  # 📊 3000 registros!
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
        
        print(f"📋 Tabela {horas}h: {len(tabela)} rodadas")
        return jsonify(tabela)
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

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
# LOOP DE COLETA (5 SEGUNDOS)
# =============================================================================
def loop_coleta():
    """Loop principal de coleta a cada 5 segundos."""
    print("🔄 Iniciando loop de coleta (5s)...")
    
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
                    print(f"⚡ {datetime.now().strftime('%H:%M:%S')} +{novas_rodadas} (total: {len(cache['rodadas'])}")
                    atualizar_cache_estatisticas()
                    
                    if novas_rodadas >= 5:
                        salvar_dados()

            time.sleep(INTERVALO_COLETA)  # 5 segundos

        except Exception as e:
            print(f"❌ Erro: {e}")
            time.sleep(INTERVALO_COLETA)

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("="*70)
    print("🚀 BOT BACBO - COLETA A CADA 5 SEGUNDOS | 3000 REGISTROS")
    print("="*70)
    
    # Carregar dados
    carregar_dados()
    
    # Iniciar coleta histórica em background
    print("📚 Iniciando coleta histórica em background...")
    historico_thread = threading.Thread(target=buscar_historico_completo, daemon=True)
    historico_thread.start()
    
    # Estatísticas iniciais
    atualizar_cache_estatisticas()
    
    print(f"⚡ Coleta em tempo real: a cada {INTERVALO_COLETA} segundos")
    print(f"📊 Máximo na tabela: {MAX_REGISTROS_TABELA} registros")
    print(f"🌐 Porta: {PORT}")
    print(f"📚 Forçar histórico: /coletar-historico")
    print("="*70)

    # Iniciar thread de coleta
    coletor = threading.Thread(target=loop_coleta, daemon=True)
    coletor.start()

    # Iniciar Flask
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
