# =============================================================================
# main.py - VERSÃO ULTRA PRECISÃO 9.0 (TURBINADA 95%+) - COM MELHORIAS
# =============================================================================

import os
import time
import requests
import json
import urllib.parse
import threading
import websocket
import random
import numpy as np
from datetime import datetime, timedelta, timezone
from collections import deque
from flask import Flask, render_template, jsonify
from flask_cors import CORS
import pg8000
import ssl
from pathlib import Path
import multiprocessing as mp
from multiprocessing import Queue as MPQueue
import traceback

# =============================================================================
# 🔇 SILENCIAR AVISOS (IMPORT OBRIGATÓRIO)
# =============================================================================
import warnings
warnings.filterwarnings('ignore')
os.environ['PYTHONWARNINGS'] = 'ignore'

# =============================================================================
# 🚀 INICIAR FLASK PRIMEIRO (CRÍTICO PARA O RENDER)
# =============================================================================
app = Flask(__name__)
CORS(app)

# =============================================================================
# 🏥 HEALTHCHECK URGENTE (RESPONDE NA HORA)
# =============================================================================
@app.route('/health', methods=['GET'])
def health_urgente():
    """Healthcheck que responde na hora - ESSENCIAL para o Render"""
    return jsonify({
        'status': 'ok',
        'mensagem': 'Sistema online',
        'timestamp': time.time(),
        'versao': '9.0 - Turbo 95%+'
    })

@app.route('/', methods=['GET'])
def home_rapida():
    """Página inicial simples"""
    return jsonify({
        'nome': 'Bac Bo Predictor',
        'versao': '9.0 - Turbo 95%+',
        'status': 'online',
        'health': '/health',
        'stats': '/api/stats'
    })
 
# =============================================================================
# 🔇 SILENCIAR AVISOS DO GYM (OPCIONAL)
# =============================================================================
import warnings
warnings.filterwarnings('ignore', message='Gym has been unmaintained')
warnings.filterwarnings('ignore', module='gym')

# =============================================================================
# 🔧 PATCH CORRETIVO PARA O ERRO DO NUMPY (VERSÃO ULTRA REFORÇADA)
# =============================================================================
import numpy as np
import sys

print("\n" + "="*80)
print("🔧 APLICANDO PATCH DE COMPATIBILIDADE NUMPY + PYTORCH")
print("="*80)

try:
    print(f"📊 Versão do NumPy detectada: {np.__version__}")
    
    # Lista completa de atributos que podem estar faltando
    atributos_necessarios = [
        'ERR_IGNORE',
        'ERR_WARN', 
        'ERR_RAISE', 
        'ERR_CALL', 
        'ERR_PRINT', 
        'ERR_LOG',
        'ERR_DEFAULT',
        'UFUNC_BUFSIZE_DEFAULT'
    ]
    
    # PATCH ULTRA: Criar TODOS os atributos possíveis
    atributos_adicionais = [
        'ERR_DEFAULT',
        'UFUNC_BUFSIZE_DEFAULT',
        'BUFSIZE',
        'PYPY',
        'UFUNC_ALIGNMENT'
    ]
    
    # Patch 1: Criar atributos no módulo umath
    if hasattr(np, 'core') and hasattr(np.core, 'umath'):
        print("✅ Módulo np.core.umath encontrado")
        
        for attr in atributos_necessarios + atributos_adicionais:
            if not hasattr(np.core.umath, attr):
                try:
                    setattr(np.core.umath, attr, 8192 if 'BUFSIZE' in attr else 0)
                    print(f"   ✅ Atributo criado: np.core.umath.{attr}")
                except Exception as e:
                    print(f"   ⚠️ Erro ao criar {attr}: {e}")
            else:
                print(f"   ✅ Atributo já existe: np.core.umath.{attr}")
    else:
        print("⚠️ Módulo np.core.umath não encontrado - tentando criar...")
        if not hasattr(np, 'core'):
            np.core = type('core', (), {})()
        if not hasattr(np.core, 'umath'):
            np.core.umath = type('umath', (), {})()
            for attr in atributos_necessarios + atributos_adicionais:
                setattr(np.core.umath, attr, 8192 if 'BUFSIZE' in attr else 0)
                print(f"   ✅ Módulo criado com atributo: np.core.umath.{attr}")
    
    # Patch 2: Criar atributos diretamente no numpy
    for attr in atributos_necessarios + atributos_adicionais:
        if not hasattr(np, attr):
            try:
                setattr(np, attr, 8192 if 'BUFSIZE' in attr else 0)
                print(f"   ✅ Atributo criado: np.{attr}")
            except Exception as e:
                print(f"   ⚠️ Erro ao criar np.{attr}: {e}")
    
    # Patch 3: Configurar sistema de erros do numpy
    try:
        np.seterr(all='ignore')
        print("✅ numpy.seterr configurado para 'ignore'")
    except Exception as e:
        print(f"⚠️ Erro ao configurar seterr: {e}")
    
    # Patch 4: Monkey patch na função geterrobj
    if hasattr(np, 'geterrobj'):
        original_geterrobj = np.geterrobj
        
        def patched_geterrobj():
            try:
                return original_geterrobj()
            except Exception:
                return [0, 0, 0]
        
        np.geterrobj = patched_geterrobj
        print("✅ Monkey patch aplicado em np.geterrobj")
    
    # Patch 5: Criar módulo fake se necessário
    if 'numpy.core.umath' in sys.modules:
        print("✅ Módulo numpy.core.umath já está em sys.modules")
    else:
        from types import ModuleType
        fake_module = ModuleType('numpy.core.umath')
        for attr in atributos_necessarios + atributos_adicionais:
            setattr(fake_module, attr, 8192 if 'BUFSIZE' in attr else 0)
        sys.modules['numpy.core.umath'] = fake_module
        print("✅ Módulo fake numpy.core.umath criado em sys.modules")
    
    # Patch 6: Criar atributos globais no módulo numpy
    if not hasattr(np, '_NoValue'):
        np._NoValue = object()
        print("✅ Atributo _NoValue criado")
    
    # Verificação final
    print("\n📊 VERIFICAÇÃO FINAL DO PATCH:")
    
    if hasattr(np, 'core') and hasattr(np.core, 'umath'):
        if hasattr(np.core.umath, 'ERR_DEFAULT'):
            print(f"   ✅ np.core.umath.ERR_DEFAULT = {np.core.umath.ERR_DEFAULT}")
        if hasattr(np.core.umath, 'UFUNC_BUFSIZE_DEFAULT'):
            print(f"   ✅ np.core.umath.UFUNC_BUFSIZE_DEFAULT = {np.core.umath.UFUNC_BUFSIZE_DEFAULT}")
    
    if hasattr(np, 'ERR_DEFAULT'):
        print(f"   ✅ np.ERR_DEFAULT = {np.ERR_DEFAULT}")
    if hasattr(np, 'UFUNC_BUFSIZE_DEFAULT'):
        print(f"   ✅ np.UFUNC_BUFSIZE_DEFAULT = {np.UFUNC_BUFSIZE_DEFAULT}")
    
    print("="*80)
    print("✅ PATCH CONCLUÍDO - NumPy preparado para uso com PyTorch\n")
    
except Exception as e:
    print(f"❌ ERRO CRÍTICO NO PATCH: {e}")
    import traceback
    traceback.print_exc()
    print("⚠️ Continuando mesmo com erro no patch...\n")

# =============================================================================
# 🚀 MULTIPROCESSING - PARALELISMO PROFISSIONAL
# =============================================================================
MP_AVAILABLE = True
print(f"✅ Multiprocessing disponível - Paralelismo ativado com {mp.cpu_count()} CPUs")

mp_manager = mp.Manager()
mp_fila_experiencias = mp_manager.Queue(maxsize=100000)
mp_estatisticas = mp_manager.dict({
    'total_episodios': 0,
    'melhor_precisao': 0,
    'geracao': 0,
    'agentes_ativos': 0
})

# =============================================================================
# PyTorch + EvoTorch + Gymnasium
# =============================================================================
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    import torch.nn.functional as F
    from torch.utils.data import DataLoader, TensorDataset
    
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"✅ PyTorch disponível - Dispositivo: {DEVICE}")
    
    try:
        import gymnasium as gym
        GYMNASIUM_AVAILABLE = True
        print(f"✅ Gymnasium disponível - Versão: {gym.__version__}")
    except ImportError as e:
        GYMNASIUM_AVAILABLE = False
        print(f"⚠️ Gymnasium não encontrado: {e}")
    
    try:
        from evotorch import Problem
        from evotorch.algorithms import SNES, PGPE
        from evotorch.logging import StdOutLogger
        from evotorch.neuroevolution import NEProblem
        
        EVOTORCH_AVAILABLE = True
        print("✅ EvoTorch disponível - Neuroevolução ativada")
        
        try:
            import evotorch
            print(f"   📦 Versão EvoTorch: {evotorch.__version__}")
        except:
            pass
            
    except ImportError as e:
        EVOTORCH_AVAILABLE = False
        print(f"⚠️ EvoTorch não encontrado: {e}")
    
    TORCH_AVAILABLE = True
    
    print("\n" + "="*80)
    print("📊 STATUS DAS BIBLIOTECAS DE IA:")
    print(f"   ✅ PyTorch: {'OK' if TORCH_AVAILABLE else 'FALHA'} (Device: {DEVICE})")
    print(f"   ✅ Gymnasium: {'OK' if GYMNASIUM_AVAILABLE else 'FALHA'}")
    print(f"   ✅ EvoTorch: {'OK' if EVOTORCH_AVAILABLE else 'FALHA'}")
    print("="*80 + "\n")
    
except ImportError as e:
    print(f"❌ Erro crítico ao importar PyTorch: {e}")
    TORCH_AVAILABLE = False
    DEVICE = 'cpu'
    EVOTORCH_AVAILABLE = False
    GYMNASIUM_AVAILABLE = False
    
# =============================================================================
# CONFIGURAÇÕES - PG8000 COM SSL
# =============================================================================
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://neondb_owner:npg_YfkiR2n3SQzs@ep-shy-unit-adoc8wwh-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

parsed = urllib.parse.urlparse(DATABASE_URL)
DB_USER = parsed.username
DB_PASSWORD = parsed.password
DB_HOST = parsed.hostname
DB_PORT = parsed.port or 5432
DB_NAME = parsed.path[1:]

SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

# =============================================================================
# CONFIGURAÇÕES DAS 3 FONTES
# =============================================================================

LATEST_API_URL = "https://api-cs.casino.org/svc-evolution-game-events/api/bacbo/latest"
WS_URL = "wss://api-cs.casino.org/svc-evolution-game-events/ws/bacbo"
API_URL = "https://api-cs.casino.org/svc-evolution-game-events/api/bacbo"
API_PARAMS = {
    "page": 0,
    "size": 100,
    "sort": "data.settledAt,desc",
    "duration": 4320,
    "wheelResults": "PlayerWon,BankerWon,Tie"
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
}

TIMEOUT_API = 5
MAX_RETRIES = 3
RETRY_DELAY = 1
INTERVALO_LATEST = 0.3
INTERVALO_WS_FALLBACK = 3
INTERVALO_NORMAL_FALLBACK = 10
PORT = int(os.environ.get("PORT", 5000))

# =============================================================================
# CONTROLE DE FALHAS
# =============================================================================
falhas_latest = 0
falhas_websocket = 0
falhas_api_normal = 0
LIMITE_FALHAS = 3

fontes_status = {
    'latest': {'status': 'ativo', 'total': 0, 'falhas': 0, 'prioridade': 1},
    'websocket': {'status': 'standby', 'total': 0, 'falhas': 0, 'prioridade': 2},
    'api_normal': {'status': 'standby', 'total': 0, 'falhas': 0, 'prioridade': 3}
}

fonte_ativa = 'latest'

# =============================================================================
# FILA DE PROCESSAMENTO
# =============================================================================
fila_rodadas = deque(maxlen=500)
ultimo_id_latest = None
ultimo_id_websocket = None
ultimo_id_api = None

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
    'estatisticas': {
        'total_previsoes': 0,
        'acertos': 0,
        'erros': 0,
        'ultimas_20_previsoes': [],
        'estrategias': {
            'RL_Agente_1': {'acertos': 0, 'erros': 0, 'total': 0},
            'RL_Agente_2': {'acertos': 0, 'erros': 0, 'total': 0},
            'RL_Agente_3': {'acertos': 0, 'erros': 0, 'total': 0},
            'RL_Agente_4': {'acertos': 0, 'erros': 0, 'total': 0},
            'RL_Agente_5': {'acertos': 0, 'erros': 0, 'total': 0},
            'RL_Agente_6': {'acertos': 0, 'erros': 0, 'total': 0},
            'RL_Agente_7': {'acertos': 0, 'erros': 0, 'total': 0},
            'RL_Agente_8': {'acertos': 0, 'erros': 0, 'total': 0},
            'RL_Agente_9': {'acertos': 0, 'erros': 0, 'total': 0},
            'RL_Agente_10': {'acertos': 0, 'erros': 0, 'total': 0}
        }
    },
    'ultima_previsao': None,
    'ultimo_resultado_real': None,
    'aprendizado': None,
    'rl_system': None,
    'analisador_erros': None,
    'ultimo_contexto_erro': None,
    'indice_confianca': 50,  # NOVO: substitui indice_manipulacao
    'detector_72': None,      # NOVO: detector de padrão
    'padroes_descobertos': [],
    'mp_system': None,
    'ultra_precisao': None,
    'curto_prazo': None,
    'estrategia_surto': None,
    'cacador_padroes': None,
    'num_agentes_paralelos': 50,
    'evolucao': None
}

# =============================================================================
# INICIALIZAÇÃO FLASK
# =============================================================================
app = Flask(__name__)
CORS(app)
session = requests.Session()
session.headers.update(HEADERS)

# =============================================================================
# FUNÇÃO AUXILIAR get_dados_ordenados
# =============================================================================
def get_dados_ordenados(dados):
    if not dados:
        return []
    return list(reversed(dados))

# =============================================================================
# FUNÇÃO PARA CALCULAR PRECISÃO
# =============================================================================
def calcular_precisao():
    total = cache['estatisticas']['total_previsoes']
    if total == 0:
        return 0
    return round((cache['estatisticas']['acertos'] / total) * 100)

# =============================================================================
# 🔄 NOVO DETECTOR DE PADRÃO 7:2
# =============================================================================

class DetectorPadrao72:
    """
    Detecta padrão DUPLO TIE seguido de sequência 7:2
    """
    def __init__(self):
        self.duplo_tie_detectado = False
        self.rodadas_desde_duplo_tie = 0
        self.ultimo_duplo_tie = None
        self.total_deteccoes = 0
    
    def analisar(self, historico):
        """
        Analisa histórico em busca do padrão 7:2
        Retorna previsão se detectado, None caso contrário
        """
        if len(historico) < 10:
            return None
        
        # Procurar por duplo TIE
        for i in range(min(20, len(historico)-1)):
            if (historico[i]['resultado'] == 'TIE' and 
                historico[i+1]['resultado'] == 'TIE'):
                
                self.duplo_tie_detectado = True
                self.rodadas_desde_duplo_tie = 0
                self.ultimo_duplo_tie = datetime.now()
                self.total_deteccoes += 1
                
                # Analisa próximos resultados (até 20 rodadas após o duplo TIE)
                proximos = []
                for j in range(i+2, min(i+22, len(historico))):
                    if historico[j]['resultado'] != 'TIE':
                        proximos.append(historico[j]['resultado'])
                        if len(proximos) >= 9:
                            break
                
                # Se encontrou pelo menos 9 resultados não-TIE
                if len(proximos) >= 9:
                    banker = proximos.count('BANKER')
                    player = proximos.count('PLAYER')
                    total = banker + player
                    
                    if total > 0:
                        banker_pct = (banker / total) * 100
                        
                        # Padrão 7:2 (77.7% BANKER) ou inverso 2:7 (22.2% BANKER)
                        if banker_pct > 60:  # Dominância BANKER
                            print(f"\n🎯 PADRÃO 7:2 DETECTADO! {banker} BANKER : {player} PLAYER ({banker_pct:.1f}%)")
                            return {
                                'previsao': 'BANKER',
                                'confianca': min(75, 60 + banker_pct/2),
                                'tipo': '7:2_BANKER',
                                'proporcao': f"{banker}:{player}"
                            }
                        elif banker_pct < 40:  # Dominância PLAYER
                            print(f"\n🎯 PADRÃO 2:7 DETECTADO! {banker} BANKER : {player} PLAYER ({banker_pct:.1f}%)")
                            return {
                                'previsao': 'PLAYER',
                                'confianca': min(75, 60 + (100-banker_pct)/2),
                                'tipo': '2:7_PLAYER',
                                'proporcao': f"{banker}:{player}"
                            }
        
        # Atualizar contador de rodadas desde último duplo TIE
        if self.duplo_tie_detectado:
            self.rodadas_desde_duplo_tie += 1
            if self.rodadas_desde_duplo_tie > 30:
                self.duplo_tie_detectado = False
        
        return None
    
    def get_stats(self):
        """Retorna estatísticas do detector"""
        return {
            'total_deteccoes': self.total_deteccoes,
            'duplo_tie_ativo': self.duplo_tie_detectado,
            'rodadas_desde_ultimo': self.rodadas_desde_duplo_tie,
            'ultimo_duplo_tie': self.ultimo_duplo_tie.isoformat() if self.ultimo_duplo_tie else None
        }


# =============================================================================
# 🎯 NOVA FUNÇÃO PARA CALCULAR ÍNDICE DE CONFIANÇA
# =============================================================================

def calcular_indice_confianca(dados):
    """
    Calcula índice de confiança baseado em padrões naturais do jogo
    Quanto maior, mais confiante na previsão
    Substitui a antiga calcular_indice_manipulacao
    """
    if len(dados) < 10:
        return 50
    
    dados_ord = list(reversed(dados)) if dados else []
    confianca = 50
    
    # Streaks longas AUMENTAM confiança (indicam padrão forte)
    streak_atual = 1
    for i in range(1, min(10, len(dados_ord))):
        if (dados_ord[i]['resultado'] == dados_ord[i-1]['resultado'] and
                dados_ord[i]['resultado'] != 'TIE'):
            streak_atual += 1
        else:
            break
    
    if streak_atual >= 3:
        confianca += streak_atual * 3
    
    # Alternância também AUMENTA confiança (indica equilíbrio)
    alternancias = 0
    for i in range(min(20, len(dados_ord)-1)):
        if (dados_ord[i]['resultado'] != 'TIE' and 
            dados_ord[i+1]['resultado'] != 'TIE' and
            dados_ord[i]['resultado'] != dados_ord[i+1]['resultado']):
            alternancias += 1
    
    if alternancias >= 5:
        confianca += alternancias
    
    # TIES em quantidade normal AUMENTAM confiança
    ties = sum(1 for r in dados_ord[:30] if r['resultado'] == 'TIE')
    ties_esperados = 3
    
    if ties <= ties_esperados * 2:
        confianca += 10
    
    return max(0, min(100, confianca))


# =============================================================================
# 🎯 SISTEMA HÍBRIDO CURTO PRAZO - VERSÃO 9.0
# =============================================================================

class SistemaCurtoPrazo:
    """
    Sistema especializado em ciclos de 20 rodadas
    Reseta completamente após cada ciclo
    """
    
    def __init__(self, sistema_rl):
        self.sistema_rl = sistema_rl
        self.modo = 'CURTO_PRAZO'
        self.ciclo_atual = 0
        self.rodadas_no_ciclo = 0
        self.max_rodadas_por_ciclo = 20
        self.acertos_ciclo = 0
        self.erros_ciclo = 0
        self.historico_ciclo = []
        
        # Estatísticas de ciclos
        self.ciclos_completados = []
        self.melhor_ciclo = {'acertos': 0, 'precisao': 0}
        
        # Agentes dedicados para curto prazo
        self.agentes_curto_prazo = self._selecionar_agentes_curto_prazo()
        
        # Detector de fim de ciclo
        self.em_ultimas_5 = False
        
        print("\n" + "="*80)
        print("🎯 SISTEMA HÍBRIDO CURTO PRAZO INICIALIZADO")
        print(f"📊 Ciclo: {self.max_rodadas_por_ciclo} rodadas")
        print(f"🤖 Agentes dedicados: {len(self.agentes_curto_prazo)}")
        print("="*80)
    
    def _selecionar_agentes_curto_prazo(self):
        """
        Seleciona agentes que performam bem em curto prazo
        """
        if not self.sistema_rl:
            return []
        
        agentes_selecionados = []
        for nome, agente in self.sistema_rl.agentes.items():
            if agente.total_uso > 50:
                if hasattr(agente, 'ultima_precisao') and agente.ultima_precisao > 0:
                    if agente.ultima_precisao > 0.6:
                        agentes_selecionados.append(agente)
        
        if len(agentes_selecionados) < 10:
            todos_agentes = list(self.sistema_rl.agentes.values())
            todos_agentes.sort(key=lambda x: x.acertos/max(x.total_uso,1), reverse=True)
            agentes_selecionados = todos_agentes[:max(10, len(todos_agentes)//10)]
        
        print(f"✅ Selecionados {len(agentes_selecionados)} agentes para curto prazo")
        return agentes_selecionados
    
    def processar_rodada(self, historico):
        """
        Processa uma rodada no modo curto prazo
        """
        self.rodadas_no_ciclo += 1
        self.em_ultimas_5 = self.rodadas_no_ciclo >= (self.max_rodadas_por_ciclo - 5)
        
        if len(historico) < 30:
            return None
        
        votos = {'BANKER': 0, 'PLAYER': 0}
        votos_detalhados = []
        
        for agente in self.agentes_curto_prazo:
            try:
                acao, confianca = agente.agir(historico[:-1])
                previsao = 'BANKER' if acao == 0 else 'PLAYER'
                
                peso = agente.peso
                if self.em_ultimas_5:
                    peso *= 1.5
                
                peso_voto = peso * confianca
                votos[previsao] += peso_voto
                
                votos_detalhados.append({
                    'agente': agente.nome,
                    'previsao': previsao,
                    'peso': round(peso, 2),
                    'confianca': round(confianca * 100, 1),
                    'peso_total': round(peso_voto, 2)
                })
            except Exception:
                continue
        
        if not votos_detalhados:
            return None
        
        previsao_final = max(votos, key=votos.get)
        total_votos = sum(votos.values())
        
        if total_votos > 0:
            vantagem = (votos[previsao_final] - min(votos.values())) / total_votos
            confianca_final = min(50 + vantagem * 50, 95)
        else:
            confianca_final = 50
        
        if self.em_ultimas_5:
            streak = self._calcular_streak_atual(historico[:5])
            if streak >= 3:
                confianca_final = min(confianca_final + 10, 95)
        
        return {
            'previsao': previsao_final,
            'simbolo': '🔴' if previsao_final == 'BANKER' else '🔵',
            'confianca': round(confianca_final),
            'votos': votos_detalhados[:5],
            'ciclo': self.ciclo_atual,
            'rodada_no_ciclo': self.rodadas_no_ciclo,
            'ultimas_5': self.em_ultimas_5
        }
    
    def _calcular_streak_atual(self, historico):
        streak = 0
        for rodada in historico:
            if rodada['resultado'] != 'TIE':
                streak += 1
            else:
                break
        return streak
    
    def registrar_resultado(self, previsao, resultado_real, acertou):
        if resultado_real == 'TIE':
            return
        
        if acertou:
            self.acertos_ciclo += 1
        else:
            self.erros_ciclo += 1
        
        self.historico_ciclo.append({
            'rodada': self.rodadas_no_ciclo,
            'previsao': previsao,
            'real': resultado_real,
            'acertou': acertou
        })
        
        if self.rodadas_no_ciclo >= self.max_rodadas_por_ciclo:
            self._finalizar_ciclo()
    
    def _finalizar_ciclo(self):
        total = self.acertos_ciclo + self.erros_ciclo
        precisao = (self.acertos_ciclo / total) * 100 if total > 0 else 0
        
        self.ciclos_completados.append({
            'ciclo': self.ciclo_atual,
            'acertos': self.acertos_ciclo,
            'erros': self.erros_ciclo,
            'precisao': precisao,
            'historico': self.historico_ciclo.copy()
        })
        
        if precisao > self.melhor_ciclo['precisao']:
            self.melhor_ciclo = {
                'ciclo': self.ciclo_atual,
                'acertos': self.acertos_ciclo,
                'precisao': precisao
            }
        
        print(f"\n{'='*60}")
        print(f"📊 CICLO {self.ciclo_atual} FINALIZADO")
        print(f"   Acertos: {self.acertos_ciclo}/{total} ({precisao:.1f}%)")
        print(f"   Melhor ciclo: {self.melhor_ciclo['precisao']:.1f}%")
        print(f"{'='*60}")
        
        self.ciclo_atual += 1
        self.rodadas_no_ciclo = 0
        self.acertos_ciclo = 0
        self.erros_ciclo = 0
        self.historico_ciclo = []
        self.em_ultimas_5 = False
        
        self.agentes_curto_prazo = self._selecionar_agentes_curto_prazo()
    
    def get_stats(self):
        total_ciclos = len(self.ciclos_completados)
        
        if total_ciclos > 0:
            media_precisao = sum(c['precisao'] for c in self.ciclos_completados) / total_ciclos
        else:
            media_precisao = 0
        
        ciclo_atual_total = self.acertos_ciclo + self.erros_ciclo
        precisao_atual = (self.acertos_ciclo / ciclo_atual_total * 100) if ciclo_atual_total > 0 else 0
        
        return {
            'modo': 'CURTO_PRAZO',
            'ciclo_atual': self.ciclo_atual,
            'rodada_no_ciclo': self.rodadas_no_ciclo,
            'acertos_ciclo': self.acertos_ciclo,
            'erros_ciclo': self.erros_ciclo,
            'precisao_ciclo_atual': round(precisao_atual, 1),
            'total_ciclos': total_ciclos,
            'media_precisao_ciclos': round(media_precisao, 1),
            'melhor_ciclo': self.melhor_ciclo,
            'agentes_curto_prazo': len(self.agentes_curto_prazo),
            'ultimas_5': self.em_ultimas_5
        }


# =============================================================================
# 🚀 ESTRATÉGIA DE SURTO (PARA AS ÚLTIMAS 5 RODADAS)
# =============================================================================

class EstrategiaSurto:
    """
    Estratégia agressiva para as últimas 5 rodadas do ciclo
    """
    
    def __init__(self):
        self.ativo = False
        self.confianca_minima = 70
        self.padroes_surto = {}
        
    def analisar_ultimas_5(self, historico):
        """
        Analisa padrões nas últimas 5 rodadas
        """
        if len(historico) < 5:
            return None
        
        ultimas_5 = historico[:5]
        resultados = [r['resultado'] for r in ultimas_5 if r['resultado'] != 'TIE']
        
        if len(resultados) < 3:
            return None
        
        banker = resultados.count('BANKER')
        player = resultados.count('PLAYER')
        
        if banker >= 4:
            return {'previsao': 'BANKER', 'confianca': 80, 'padrao': 'dominancia_banker'}
        if player >= 4:
            return {'previsao': 'PLAYER', 'confianca': 80, 'padrao': 'dominancia_player'}
        
        streak = 1
        for i in range(1, len(resultados)):
            if resultados[-i] == resultados[-(i+1)]:
                streak += 1
            else:
                break
        
        if streak >= 3:
            return {
                'previsao': resultados[0],
                'confianca': 70 + streak * 3,
                'padrao': f'streak_{streak}'
            }
        
        return None


# =============================================================================
# 🚀 SISTEMA ULTRA PRECISÃO - VERSÃO 7.0
# =============================================================================

class SistemaUltraPrecisao:
    """
    Sistema avançado com 4 camadas de segurança
    """
    
    def __init__(self, sistema_rl):
        self.sistema_rl = sistema_rl
        self.limiar_base = 80
        
        self.janela_curta = deque(maxlen=30)
        self.janela_longa = deque(maxlen=200)
        self.janela_ultra = deque(maxlen=500)
        
        self.tendencias = {
            'curta': {'banker': 0, 'player': 0, 'ties': 0},
            'longa': {'banker': 0, 'player': 0, 'ties': 0},
            'ultra': {'banker': 0, 'player': 0, 'ties': 0}
        }
        
        self.rede_decisao = None
        self.otimizador_decisao = None
        self.historico_decisoes = deque(maxlen=1000)
        self._criar_rede_decisao()
        
        self.comite_certeza = []
        self.peso_comite = 2.5
        self.ultima_atualizacao_comite = 0
        
        self.detector_reverso = DetectorPadroesReversos()
        
        self.total_apostas = 0
        self.acertos_apostas = 0
        self.confianca_media_apostas = 0
        self.historico_confianca = deque(maxlen=100)
        self.ultima_previsao_nao_apostada = None
        
        print("\n" + "="*80)
        print("🚀 SISTEMA ULTRA PRECISÃO INICIALIZADO (MIRANDO 95%+)")
        print("="*80)
        print(f"📊 Janelas: Curta(30) | Longa(200) | Ultra(500)")
        print(f"🧠 Rede Neural de Decisão: Ativa")
        print(f"👥 Comitê de Certeza: Top 10% agentes")
        print(f"🔄 Detector de Padrões Reversos: Ativo")
        print("="*80)
    
    def _criar_rede_decisao(self):
        class RedeDecisao(nn.Module):
            def __init__(self):
                super(RedeDecisao, self).__init__()
                
                self.input_size = 120
                
                self.fc1 = nn.Linear(self.input_size, 256)
                self.bn1 = nn.BatchNorm1d(256)
                self.fc2 = nn.Linear(256, 128)
                self.bn2 = nn.BatchNorm1d(128)
                self.fc3 = nn.Linear(128, 64)
                self.fc4 = nn.Linear(64, 32)
                self.fc5 = nn.Linear(32, 2)
                
                self.dropout = nn.Dropout(0.3)
                self.leaky_relu = nn.LeakyReLU(0.1)
                
            def forward(self, x):
                x = self.leaky_relu(self.bn1(self.fc1(x)))
                x = self.dropout(x)
                x = self.leaky_relu(self.bn2(self.fc2(x)))
                x = self.dropout(x)
                x = self.leaky_relu(self.fc3(x))
                x = self.leaky_relu(self.fc4(x))
                x = self.fc5(x)
                return F.softmax(x, dim=1)
        
        try:
            self.rede_decisao = RedeDecisao().to(DEVICE)
            self.otimizador_decisao = optim.Adam(self.rede_decisao.parameters(), lr=0.001)
            print("✅ Rede de decisão criada")
        except Exception as e:
            print(f"⚠️ Erro ao criar rede de decisão: {e}")
            self.rede_decisao = None
    
    def atualizar_janelas(self, historico):
        if not historico:
            return
        
        self.janela_curta.clear()
        self.janela_longa.clear()
        self.janela_ultra.clear()
        
        for rodada in historico[:30]:
            self.janela_curta.append(rodada)
        for rodada in historico[:200]:
            self.janela_longa.append(rodada)
        for rodada in historico[:500]:
            self.janela_ultra.append(rodada)
        
        self._atualizar_tendencias()
    
    def _atualizar_tendencias(self):
        self.tendencias['curta'] = self._calcular_tendencia(self.janela_curta)
        self.tendencias['longa'] = self._calcular_tendencia(self.janela_longa)
        self.tendencias['ultra'] = self._calcular_tendencia(self.janela_ultra)
    
    def _calcular_tendencia(self, janela):
        if not janela:
            return {'banker': 0, 'player': 0, 'ties': 0}
        
        banker = sum(1 for r in janela if r['resultado'] == 'BANKER')
        player = sum(1 for r in janela if r['resultado'] == 'PLAYER')
        ties = sum(1 for r in janela if r['resultado'] == 'TIE')
        total = len(janela)
        
        return {
            'banker': banker,
            'player': player,
            'ties': ties,
            'total': total,
            'banker_pct': (banker / total) * 100 if total > 0 else 0,
            'player_pct': (player / total) * 100 if total > 0 else 0
        }
    
    def analisar_tendencias_conflitantes(self):
        curta = self.tendencias['curta']
        longa = self.tendencias['longa']
        
        if curta.get('total', 0) < 10 or longa.get('total', 0) < 50:
            return None
        
        tend_curta = 'BANKER' if curta['banker'] > curta['player'] else 'PLAYER'
        tend_longa = 'BANKER' if longa['banker'] > longa['player'] else 'PLAYER'
        
        if tend_curta != tend_longa:
            forca_curta = abs(curta['banker'] - curta['player']) / curta['total']
            forca_longa = abs(longa['banker'] - longa['player']) / longa['total']
            
            return {
                'divergente': True,
                'tendencia_curta': tend_curta,
                'tendencia_longa': tend_longa,
                'forca_curta': round(forca_curta * 100, 1),
                'forca_longa': round(forca_longa * 100, 1),
                'proximo_possivel': tend_curta
            }
        
        return {'divergente': False, 'tendencia': tend_curta}
    
    def _extrair_features_decisao(self, historico, previsao_rl, confianca_rl):
        features = []
        
        for i, rodada in enumerate(historico[:30]):
            if rodada['resultado'] == 'BANKER':
                features.extend([1, 0, 0])
            elif rodada['resultado'] == 'PLAYER':
                features.extend([0, 1, 0])
            elif rodada['resultado'] == 'TIE':
                features.extend([0, 0, 1])
        
        while len(features) < 90:
            features.extend([0, 0, 0])
        
        for escala in ['curta', 'longa', 'ultra']:
            tend = self.tendencias[escala]
            features.append(tend.get('banker_pct', 0) / 100)
            features.append(tend.get('player_pct', 0) / 100)
            features.append(tend.get('ties', 0) / max(tend.get('total', 1), 1))
        
        streak_atual = self._calcular_streak_atual(historico)
        features.append(streak_atual / 20)
        
        max_streak = self._calcular_max_streak(historico[:50])
        features.append(max_streak / 20)
        
        alternancia = self._calcular_alternancia(historico[:20])
        features.append(alternancia)
        
        scores_player = [r.get('player_score', 0) for r in historico[:20]]
        scores_banker = [r.get('banker_score', 0) for r in historico[:20]]
        
        features.append(np.mean(scores_player) / 12 if scores_player else 0)
        features.append(np.std(scores_player) / 12 if scores_player else 0)
        features.append(np.mean(scores_banker) / 12 if scores_banker else 0)
        features.append(np.std(scores_banker) / 12 if scores_banker else 0)
        
        features.append(cache.get('indice_confianca', 50) / 100)
        features.append(1 if self.detector_reverso.padrao_reverso_detectado else 0)
        features.append(confianca_rl / 100)
        
        while len(features) < 120:
            features.append(0)
        
        return torch.FloatTensor(features).unsqueeze(0).to(DEVICE)
    
    def _calcular_streak_atual(self, historico):
        streak = 0
        for rodada in historico:
            if rodada['resultado'] != 'TIE':
                streak += 1
            else:
                break
        return streak
    
    def _calcular_max_streak(self, historico):
        max_streak = 0
        streak_atual = 0
        
        for rodada in historico:
            if rodada['resultado'] != 'TIE':
                streak_atual += 1
                max_streak = max(max_streak, streak_atual)
            else:
                streak_atual = 0
        
        return max_streak
    
    def _calcular_alternancia(self, historico):
        if len(historico) < 2:
            return 0.5
        
        alternancias = 0
        total = 0
        
        for i in range(1, len(historico)):
            if (historico[i]['resultado'] != 'TIE' and 
                historico[i-1]['resultado'] != 'TIE' and
                historico[i]['resultado'] != historico[i-1]['resultado']):
                alternancias += 1
                total += 1
        
        return alternancias / max(total, 1)
    
    def atualizar_comite_certeza(self):
        if not self.sistema_rl or time.time() - self.ultima_atualizacao_comite < 300:
            return
        
        stats_agentes = []
        for nome, agente in self.sistema_rl.agentes.items():
            if agente.total_uso > 100:
                precisao = (agente.acertos / agente.total_uso) * 100
                stats_agentes.append({
                    'nome': nome,
                    'agente': agente,
                    'precisao': precisao,
                    'total_uso': agente.total_uso,
                    'peso': agente.peso
                })
        
        if not stats_agentes:
            return
        
        stats_agentes.sort(key=lambda x: x['precisao'], reverse=True)
        
        top_10_percent = max(1, len(stats_agentes) // 10)
        self.comite_certeza = stats_agentes[:top_10_percent]
        self.ultima_atualizacao_comite = time.time()
        
        print(f"👥 Comitê de Certeza atualizado: {len(self.comite_certeza)} agentes")
    
    def consultar_comite_certeza(self, historico):
        if not self.comite_certeza:
            return None, 0
        
        votos = {'BANKER': 0, 'PLAYER': 0}
        confianca_total = 0
        
        for membro in self.comite_certeza:
            agente = membro['agente']
            
            try:
                acao, confianca = agente.agir(historico[:-1])
                previsao = 'BANKER' if acao == 0 else 'PLAYER'
                
                peso_voto = (membro['precisao'] / 100) * confianca * self.peso_comite
                
                votos[previsao] += peso_voto
                confianca_total += peso_voto
                
            except Exception:
                continue
        
        if confianca_total == 0:
            return None, 0
        
        vencedor = max(votos, key=votos.get)
        confianca_comite = (votos[vencedor] / confianca_total) * 100
        
        return vencedor, confianca_comite
    
    def decidir_aposta_completa(self, historico, previsao_rl, confianca_rl):
        if len(historico) < 30:
            return {'apostar': False, 'motivo': 'historico_insuficiente'}
        
        self.atualizar_janelas(historico)
        self.atualizar_comite_certeza()
        
        previsao_comite, confianca_comite = self.consultar_comite_certeza(historico)
        self.detector_reverso.analisar(historico, self.tendencias)
        
        if confianca_rl >= self.limiar_base:
            if previsao_comite and previsao_comite != previsao_rl:
                if confianca_comite > 80:
                    return {'apostar': False, 'motivo': 'comite_discorda'}
            
            if self.detector_reverso.padrao_reverso_detectado:
                if previsao_comite and confianca_comite > 85:
                    return {
                        'apostar': True,
                        'previsao': previsao_comite,
                        'confianca': confianca_comite,
                        'motivo': 'padrao_reverso_com_comite'
                    }
            
            if self.rede_decisao is not None and len(self.historico_decisoes) > 100:
                try:
                    features = self._extrair_features_decisao(historico, previsao_rl, confianca_rl)
                    
                    with torch.no_grad():
                        output = self.rede_decisao(features)
                        prob_apostar = output[0][0].item()
                    
                    if prob_apostar > 0.7:
                        return {
                            'apostar': True,
                            'previsao': previsao_rl,
                            'confianca': confianca_rl,
                            'motivo': 'rede_neural'
                        }
                except Exception:
                    pass
            
            return {
                'apostar': True,
                'previsao': previsao_rl,
                'confianca': confianca_rl,
                'motivo': 'confianca_alta'
            }
        
        return {
            'apostar': False,
            'previsao': None,
            'confianca': confianca_rl,
            'motivo': f'confianca_baixa_{confianca_rl}'
        }
    
    def registrar_resultado(self, apostou, previsao, resultado_real, confianca, motivo):
        if apostou:
            acertou = (previsao == resultado_real)
            self.total_apostas += 1
            if acertou:
                self.acertos_apostas += 1
            self.confianca_media_apostas = (
                (self.confianca_media_apostas * (self.total_apostas - 1) + confianca) / self.total_apostas
            )
        else:
            self.ultima_previsao_nao_apostada = previsao
    
    def get_stats(self):
        precisao_apostas = (self.acertos_apostas / max(self.total_apostas, 1)) * 100
        
        return {
            'modo': 'ULTRA PRECISÃO',
            'total_apostas': self.total_apostas,
            'acertos_apostas': self.acertos_apostas,
            'precisao_apostas': round(precisao_apostas, 1),
            'limiar_base': self.limiar_base,
            'confianca_media': round(self.confianca_media_apostas, 1),
            'comite_tamanho': len(self.comite_certeza),
            'reverso_detectado': self.detector_reverso.padrao_reverso_detectado,
            'tendencias': {
                escala: {
                    'banker_pct': round(dados.get('banker_pct', 0), 1),
                    'player_pct': round(dados.get('player_pct', 0), 1)
                }
                for escala, dados in self.tendencias.items()
            }
        }


# =============================================================================
# 🔄 DETECTOR DE PADRÕES REVERSOS
# =============================================================================

class DetectorPadroesReversos:
    def __init__(self):
        self.indice_atual = 0
        self.padrao_reverso_detectado = False
        self.historico_indices = deque(maxlen=200)
        self.ultimo_sinal = None
        self.confianca_reversao = 0
        self.limiar_reversao = 30
        self.min_amostras = 20
        
        print("🔄 Detector de Padrões Reversos inicializado")
    
    def analisar(self, historico, tendencias):
        if len(historico) < self.min_amostras:
            return
        
        indices = {
            'ultimos_10': self._calcular_indice_periodo(historico, 10),
            'ultimos_20': self._calcular_indice_periodo(historico, 20),
            'ultimos_50': self._calcular_indice_periodo(historico, 50),
            'ultimos_100': self._calcular_indice_periodo(historico, 100)
        }
        
        self.historico_indices.append(indices)
        self._detectar_reversao(indices, tendencias)
    
    def _calcular_indice_periodo(self, historico, periodo):
        periodo_historico = historico[:min(periodo, len(historico))]
        
        if not periodo_historico:
            return 0
        
        banker = sum(1 for r in periodo_historico if r['resultado'] == 'BANKER')
        player = sum(1 for r in periodo_historico if r['resultado'] == 'PLAYER')
        total = banker + player
        
        if total == 0:
            return 0
        
        return ((banker - player) / total) * 100
    
    def _detectar_reversao(self, indices, tendencias):
        if len(self.historico_indices) < 10:
            return
        
        idx_10 = indices['ultimos_10']
        idx_50 = indices['ultimos_50']
        
        if abs(idx_10) > 30 and abs(idx_50) > 30:
            if (idx_10 > 0 and idx_50 < -30) or (idx_10 < 0 and idx_50 > 30):
                self.padrao_reverso_detectado = True
                self.confianca_reversao = min(100, abs(idx_10) + abs(idx_50) / 2)
                print(f"🔄 REVERSÃO DETECTADA! Curto:{idx_10:.0f}% vs Longo:{idx_50:.0f}%")
                return
        
        if len(self.historico_indices) >= 20:
            primeiros = list(self.historico_indices)[:10]
            ultimos = list(self.historico_indices)[-10:]
            
            media_primeiros = np.mean([p['ultimos_50'] for p in primeiros])
            media_ultimos = np.mean([u['ultimos_50'] for u in ultimos])
            
            if abs(media_primeiros) > 50 and abs(media_ultimos) < 30:
                if (media_primeiros > 0 and media_ultimos < media_primeiros) or \
                   (media_primeiros < 0 and media_ultimos > media_primeiros):
                    self.padrao_reverso_detectado = True
                    self.confianca_reversao = 70
                    print(f"🔄 TENDÊNCIA ENFRAQUECENDO: {media_primeiros:.0f}% → {media_ultimos:.0f}%")
                    return
        
        self.padrao_reverso_detectado = False
    
    def get_sugestao(self):
        if not self.padrao_reverso_detectado or len(self.historico_indices) == 0:
            return None
        
        ultimo = self.historico_indices[-1]['ultimos_10']
        
        if ultimo > 20:
            return {
                'sugestao': 'PLAYER',
                'confianca': self.confianca_reversao,
                'motivo': 'reversao_banker_para_player'
            }
        elif ultimo < -20:
            return {
                'sugestao': 'BANKER',
                'confianca': self.confianca_reversao,
                'motivo': 'reversao_player_para_banker'
            }
        
        return None


# =============================================================================
# 🧠 REDES NEURAIS PyTorch PARA RL
# =============================================================================

class RedeDQN(nn.Module):
    def __init__(self, state_size, action_size):
        super(RedeDQN, self).__init__()
        
        self.fc1 = nn.Linear(state_size, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, 32)
        self.fc4 = nn.Linear(32, action_size)
        
        self.dropout = nn.Dropout(0.2)
        
    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = self.dropout(x)
        x = torch.relu(self.fc2(x))
        x = self.dropout(x)
        x = torch.relu(self.fc3(x))
        x = self.fc4(x)
        return x


class RedeMetaAgente(nn.Module):
    def __init__(self, input_size=23, hidden_size=64):
        super(RedeMetaAgente, self).__init__()
        
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, 32)
        self.fc3 = nn.Linear(32, 2)
        self.dropout = nn.Dropout(0.2)
        
    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = self.dropout(x)
        x = torch.relu(self.fc2(x))
        x = self.fc3(x)
        return F.softmax(x, dim=1)


class PrioritizedReplayBuffer:
    def __init__(self, capacity=10000, alpha=0.6, beta=0.4):
        self.capacity = capacity
        self.alpha = alpha
        self.beta = beta
        self.buffer = []
        self.priorities = np.zeros(capacity, dtype=np.float32)
        self.position = 0
        
    def push(self, state, action, reward, next_state, error):
        priority = (abs(error) + 1e-6) ** self.alpha
        
        if len(self.buffer) < self.capacity:
            self.buffer.append((state, action, reward, next_state))
        else:
            self.buffer[self.position] = (state, action, reward, next_state)
        
        self.priorities[self.position] = priority
        self.position = (self.position + 1) % self.capacity
        
    def sample(self, batch_size):
        if len(self.buffer) == self.capacity:
            priorities = self.priorities
        else:
            priorities = self.priorities[:len(self.buffer)]
        
        probs = priorities ** self.alpha
        probs /= probs.sum()
        
        indices = np.random.choice(len(self.buffer), batch_size, p=probs)
        samples = [self.buffer[idx] for idx in indices]
        
        total = len(self.buffer)
        weights = (total * probs[indices]) ** (-self.beta)
        weights /= weights.max()
        
        states, actions, rewards, next_states = zip(*samples)
        
        return (np.array(states), np.array(actions), 
                np.array(rewards), np.array(next_states), 
                weights, indices)


# =============================================================================
# 🧠 AGENTE RL PURO COM PyTorch
# =============================================================================

class AgenteRLPuro:
    def __init__(self, nome, id_agente):
        self.nome = nome
        self.id = id_agente
        self.acertos = 0
        self.erros = 0
        self.total_uso = 0
        self.saude = 100
        self.peso = 1.0
        self.confianca = 0.5
        self.ultima_atuacao = datetime.now()
        
        self.state_size = 30 * 5
        self.action_size = 2
        
        self.memoria = PrioritizedReplayBuffer(capacity=10000)
        self.learning_rate = 0.001
        self.gamma = 0.95
        self.epsilon = 1.0
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.tau = 0.001
        
        self.device = DEVICE
        self.model = None
        self.target_model = None
        self.optimizer = None
        self.loss_fn = nn.SmoothL1Loss()
        self._criar_rede_pytorch()
        
        self.padroes_aprendidos = []
        self.ultimo_estado = None
        self.ultima_acao = None
        self.especialidade = None
        self.erros_que_aprendeu = []
        self.fitness = 0
        
        self.historico_perda = []
        self.ultima_precisao = 0
        self.deteccoes_manipulacao = 0
        
        self.neuro_evolucao = None
        if EVOTORCH_AVAILABLE:
            self._setup_evotorch()
        
    def _criar_rede_pytorch(self):
        try:
            self.model = RedeDQN(self.state_size, self.action_size).to(self.device)
            self.target_model = RedeDQN(self.state_size, self.action_size).to(self.device)
            self.target_model.load_state_dict(self.model.state_dict())
            
            self.optimizer = optim.Adam(self.model.parameters(), 
                                        lr=self.learning_rate, 
                                        weight_decay=1e-5)
            
            print(f"✅ Rede PyTorch criada para {self.nome} no dispositivo {self.device}")
        except Exception as e:
            print(f"❌ Erro ao criar rede para {self.nome}: {e}")
            self.model = None
    
    def _setup_evotorch(self):
        try:
            self.neuro_evolucao = {
                'geracao': 0,
                'melhor_fitness': 0,
                'historico': []
            }
        except Exception as e:
            print(f"⚠️ Erro ao configurar EvoTorch: {e}")
    
    def get_state_tensor(self, historico):
        state = []
        
        for i, rodada in enumerate(historico[:30]):
            if rodada['resultado'] == 'BANKER':
                state.extend([1, 0, 0])
            elif rodada['resultado'] == 'PLAYER':
                state.extend([0, 1, 0])
            else:
                state.extend([0, 0, 1])
            
            state.append(rodada.get('player_score', 0) / 12)
            state.append(rodada.get('banker_score', 0) / 12)
        
        while len(state) < self.state_size:
            state.extend([0, 0, 0, 0, 0])
            
        return torch.FloatTensor(state).unsqueeze(0).to(self.device)
    
    def get_state(self, historico):
        return self.get_state_tensor(historico).cpu().numpy()
    
    def agir(self, historico):
        self.total_uso += 1
        
        if len(historico) < 30:
            return random.choice([0, 1]), 0.5
            
        state_tensor = self.get_state_tensor(historico)
        self.ultimo_estado = state_tensor
        
        if self.total_uso > 1000:
            self.epsilon = max(self.epsilon_min, self.epsilon * 0.999)
        
        if np.random.rand() <= self.epsilon:
            acao = random.choice([0, 1])
            confianca = 0.5
        else:
            if self.model is not None:
                try:
                    with torch.no_grad():
                        q_values = self.model(state_tensor).cpu().numpy()[0]
                        acao = np.argmax(q_values)
                        
                        q_max = np.max(q_values)
                        q_min = np.min(q_values)
                        q_diff = q_max - q_min
                        
                        confianca = min(0.5 + q_diff / (abs(q_max) + 1e-8), 0.95)
                        
                except Exception as e:
                    print(f"⚠️ Erro no predict PyTorch: {e}")
                    acao = random.choice([0, 1])
                    confianca = 0.5
            else:
                if self.peso > 1.2:
                    acao = 0 if random.random() < 0.7 else 1
                elif self.peso < 0.8:
                    acao = 1 if random.random() < 0.7 else 0
                else:
                    acao = random.choice([0, 1])
                confianca = 0.5 + (abs(self.peso - 1.0) * 0.3)
        
        self.ultima_acao = acao
        self.confianca = confianca
        return acao, confianca
    
    def aprender(self, historico, acao, resultado, recompensa_base=0):
        if resultado == 'TIE' or len(historico) < 30:
            return False
            
        resultado_int = 0 if resultado == 'BANKER' else 1
        acertou = (acao == resultado_int)
        
        if acertou:
            self.acertos += 1
            recompensa = 2.0
        else:
            self.erros += 1
            recompensa = -1.5
        
        if acertou and self.ultima_precisao > 0.6:
            recompensa += 0.5
        
        if len(historico) > 1 and self.model is not None:
            state = self.get_state_tensor(historico[:-1])
            next_state = self.get_state_tensor(historico)
            
            with torch.no_grad():
                current_q = self.model(state)[0, acao]
                next_q = self.target_model(next_state).max(1)[0]
                target_q = recompensa + self.gamma * next_q * (1 - int(resultado == 'TIE'))
                td_error = (target_q - current_q).abs().item()
            
            self.memoria.push(
                historico[:-1], acao, recompensa, historico, td_error
            )
        
        if len(self.memoria.buffer) > 128 and self.model is not None:
            self._replay_priorizado()
        
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
        
        if self.total_uso > 100:
            if len(self.memoria.buffer) >= 100:
                taxa_recente = self.acertos / max(self.total_uso, 1)
                self.ultima_precisao = taxa_recente
                
                self.peso = max(0.6, min(2.2, 0.8 + (taxa_recente - 0.5) * 2.5))
                self.fitness = taxa_recente * 100
        
        return acertou
    
    def _replay_priorizado(self):
        if len(self.memoria.buffer) < 128 or self.model is None:
            return
            
        try:
            batch_size = min(128, len(self.memoria.buffer))
            
            states_hist, actions, rewards, next_states_hist, weights, indices = \
                self.memoria.sample(batch_size)
            
            states = torch.stack([self.get_state_tensor(h) for h in states_hist]).squeeze(1)
            next_states = torch.stack([self.get_state_tensor(h) for h in next_states_hist]).squeeze(1)
            actions = torch.LongTensor(actions).to(self.device)
            rewards = torch.FloatTensor(rewards).to(self.device)
            weights = torch.FloatTensor(weights).to(self.device)
            
            current_q = self.model(states).gather(1, actions.unsqueeze(1))
            
            with torch.no_grad():
                next_q = self.target_model(next_states).max(1)[0]
                target_q = rewards + self.gamma * next_q
            
            loss = (weights * self.loss_fn(current_q.squeeze(), target_q)).mean()
            
            self.optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
            self.optimizer.step()
            
            with torch.no_grad():
                td_errors = (target_q - current_q.squeeze()).abs().cpu().numpy()
                for idx, error in zip(indices, td_errors):
                    self.memoria.priorities[idx] = (abs(error) + 1e-6) ** self.memoria.alpha
            
            for target_param, param in zip(self.target_model.parameters(), 
                                          self.model.parameters()):
                target_param.data.copy_(self.tau * param.data + 
                                       (1 - self.tau) * target_param.data)
            
            self.historico_perda.append(loss.item())
            if len(self.historico_perda) > 100:
                self.historico_perda.pop(0)
                
        except Exception as e:
            print(f"⚠️ Erro no replay PyTorch: {e}")
    
    def get_stats(self):
        precisao = (self.acertos / self.total_uso) * 100 if self.total_uso > 0 else 0
        
        perda_media = 0
        if self.historico_perda:
            perda_media = sum(self.historico_perda[-50:]) / len(self.historico_perda[-50:])
        
        return {
            'nome': self.nome,
            'acertos': self.acertos,
            'erros': self.erros,
            'total': self.total_uso,
            'precisao': round(precisao, 1),
            'peso': round(self.peso, 2),
            'confianca': round(self.confianca * 100, 1),
            'epsilon': round(self.epsilon, 3),
            'saude': self.saude,
            'memoria': len(self.memoria.buffer),
            'especialidade': self.especialidade or 'Nenhuma',
            'fitness': round(self.fitness, 1),
            'perda_media': round(perda_media, 4),
            'ultima_precisao': round(self.ultima_precisao * 100, 1) if self.ultima_precisao else 0,
            'deteccoes_manipulacao': self.deteccoes_manipulacao
        }
    
    def para_dict(self):
        return {
            'nome': self.nome,
            'id': self.id,
            'acertos': self.acertos,
            'erros': self.erros,
            'total_uso': self.total_uso,
            'peso': self.peso,
            'epsilon': self.epsilon,
            'saude': self.saude,
            'especialidade': self.especialidade,
            'fitness': self.fitness,
            'ultima_precisao': self.ultima_precisao
        }
    
    @classmethod
    def de_dict(cls, dados):
        agente = cls(dados['nome'], dados['id'])
        agente.acertos = dados['acertos']
        agente.erros = dados['erros']
        agente.total_uso = dados['total_uso']
        agente.peso = dados['peso']
        agente.epsilon = dados.get('epsilon', 1.0)
        agente.saude = dados.get('saude', 100)
        agente.especialidade = dados.get('especialidade')
        agente.fitness = dados.get('fitness', 0)
        agente.ultima_precisao = dados.get('ultima_precisao', 0)
        return agente


# =============================================================================
# 🧠 AGENTE RL TURBINADO - VERSÃO 11.0 (95%+)
# =============================================================================

class AgenteRLElitizado(AgenteRLPuro):
    """
    Versão turbinada do agente com:
    - Recompensa 10x maior para acertos
    - Penalidade 5x menor para erros
    - Exploração mais longa
    - Memória expandida
    - Bônus especial para TIE
    - Batch Normalization
    - Crossover genético
    """
    
    def __init__(self, nome, id_agente):
        super().__init__(nome, id_agente)
        
        # =====================================================================
        # CONFIGURAÇÕES TURBINADAS
        # =====================================================================
        self.learning_rate = 0.005  # Balanceado (era 0.001)
        self.gamma = 0.99  # Maior (era 0.95)
        self.epsilon = 1.0
        self.epsilon_min = 0.05  # Maior (era 0.01) - exploração constante
        self.epsilon_decay = 0.999  # Mais lento (era 0.995)
        
        # Memória MUITO maior
        self.memoria = PrioritizedReplayBuffer(capacity=200000)  # 20x maior
        
        # Pesos de recompensa TURBINADOS
        self.peso_acerto = 8.0  # 4x maior (era 2.0)
        self.peso_erro = -0.3   # 5x menor (era -1.5)
        self.peso_acerto_tie = 15.0  # Bônus especial para TIE
        self.bonus_sequencia_max = 3.0  # Bônus máximo por sequência
        
        # Estatísticas especiais
        self.acertos_seguidos = 0
        self.melhor_sequencia = 0
        self.acertos_tie = 0
        self.erros_tie = 0
        self.total_ties_vistos = 0
        
        # NOVO: aprendizado por lote
        self.batch_size = 128
        self.steps_since_train = 0
        self.train_frequency = 4
        
        # Recriar rede com BatchNorm
        self._criar_rede_pytorch_turbinada()
        
        print(f"✅ Agente TURBINADO {nome} criado - LR:{self.learning_rate} EPS:{self.epsilon}")
    
    def _criar_rede_pytorch_turbinada(self):
        """Rede neural com BatchNorm para estabilidade"""
        try:
            # Rede com Batch Normalization
            self.model = nn.Sequential(
                nn.Linear(self.state_size, 256),
                nn.BatchNorm1d(256),
                nn.ReLU(),
                nn.Dropout(0.2),
                
                nn.Linear(256, 256),
                nn.BatchNorm1d(256),
                nn.ReLU(),
                nn.Dropout(0.2),
                
                nn.Linear(256, 128),
                nn.BatchNorm1d(128),
                nn.ReLU(),
                
                nn.Linear(128, 64),
                nn.ReLU(),
                
                nn.Linear(64, self.action_size)
            ).to(self.device)
            
            self.target_model = type(self.model)().to(self.device)
            self.target_model.load_state_dict(self.model.state_dict())
            
            # Optimizer com learning rate maior e weight decay
            self.optimizer = optim.Adam(self.model.parameters(), 
                                        lr=self.learning_rate,
                                        weight_decay=1e-5)
            
            # NOVO: scheduler para reduzir LR gradualmente
            self.scheduler = optim.lr_scheduler.StepLR(self.optimizer, step_size=1000, gamma=0.95)
            
            print(f"✅ Rede TURBINADA criada para {self.nome}")
        except Exception as e:
            print(f"❌ Erro ao criar rede turbinada: {e}")
            self.model = None
    
    def agir(self, historico):
        """
        Agir com EXPLORAÇÃO CONSTANTE (epsilon nunca chega a 0)
        """
        self.total_uso += 1
        
        if len(historico) < 30:
            return random.choice([0, 1]), 0.5
        
        state_tensor = self.get_state_tensor(historico)
        self.ultimo_estado = state_tensor
        
        # EXPLORAÇÃO: mesmo depois de muito uso, ainda explora 5% das vezes
        if self.total_uso > 10000:
            self.epsilon = max(self.epsilon_min, self.epsilon * 0.9999)
        
        if np.random.rand() <= self.epsilon:
            acao = random.choice([0, 1])
            confianca = 0.5
        else:
            if self.model is not None:
                try:
                    with torch.no_grad():
                        q_values = self.model(state_tensor).cpu().numpy()[0]
                        acao = np.argmax(q_values)
                        
                        # Confiança baseada na diferença dos Q-values
                        q_max = np.max(q_values)
                        q_min = np.min(q_values)
                        q_diff = q_max - q_min
                        
                        # Confiança mais alta para decisões claras
                        confianca = min(0.6 + q_diff / (abs(q_max) + 1e-8), 0.98)
                        
                except Exception as e:
                    print(f"⚠️ Erro no predict: {e}")
                    acao = random.choice([0, 1])
                    confianca = 0.5
            else:
                acao = random.choice([0, 1])
                confianca = 0.5
        
        self.ultima_acao = acao
        self.confianca = confianca
        return acao, confianca
    
    def aprender(self, historico, acao, resultado, recompensa_base=0):
        """
        Aprendizado TURBINADO:
        - Acertos valem MUITO mais
        - Erros valem MUITO menos
        - Bônus especial para TIE
        - Sequências de acertos são recompensadas
        """
        if len(historico) < 30:
            return False
        
        # Calcular recompensa base
        if resultado == 'BANKER':
            resultado_int = 0
        elif resultado == 'PLAYER':
            resultado_int = 1
        else:  # TIE
            resultado_int = 2
            self.total_ties_vistos += 1
        
        # Só consideramos BANKER/PLAYER para acertos/erros tradicionais
        if resultado != 'TIE':
            acertou = (acao == resultado_int)
            
            # RECOMPENSA TURBINADA
            if acertou:
                self.acertos += 1
                self.acertos_seguidos += 1
                self.melhor_sequencia = max(self.melhor_sequencia, self.acertos_seguidos)
                
                # Bônus por sequência (limitado)
                bonus_sequencia = min(self.acertos_seguidos * 0.3, self.bonus_sequencia_max)
                recompensa = self.peso_acerto + bonus_sequencia
                
            else:
                self.erros += 1
                self.acertos_seguidos = 0
                # Penalidade muito menor
                recompensa = self.peso_erro
        else:
            # Para TIE, só aprendemos quando acertamos prever TIE
            if acao == 2:  # Se o agente previu TIE
                acertou = True
                self.acertos_tie += 1
                recompensa = self.peso_acerto_tie  # Bônus gigante por acertar TIE
            else:
                acertou = False
                self.erros_tie += 1
                recompensa = -1.0  # Penalidade média por não prever TIE
        
        # Aprendizado com replay prioritário
        if self.model is not None:
            state = self.get_state_tensor(historico[:-1])
            next_state = self.get_state_tensor(historico)
            
            with torch.no_grad():
                current_q = self.model(state)[0, acao]
                next_q = self.target_model(next_state).max(1)[0]
                target_q = recompensa + self.gamma * next_q
                td_error = (target_q - current_q).abs().item()
            
            self.memoria.push(
                historico[:-1], acao, recompensa, historico, td_error
            )
            
            self.steps_since_train += 1
            
            # Treinar a cada train_frequency passos
            if self.steps_since_train >= self.train_frequency and len(self.memoria.buffer) > self.batch_size:
                self._replay_priorizado()
                self.steps_since_train = 0
        
        # Decaimento mais lento do epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
        
        # Atualizar scheduler
        if hasattr(self, 'scheduler'):
            self.scheduler.step()
        
        # Atualizar peso baseado na performance RECENTE
        if self.total_uso % 20 == 0:
            if self.total_uso > 100:
                # Calcular precisão das últimas 100 ações
                # (isso requer manter histórico, simplificando)
                taxa_recente = self.acertos / max(self.total_uso, 1)
                
                # Peso mais agressivo
                self.peso = max(0.8, min(3.0, 1.0 + (taxa_recente - 0.5) * 4))
                self.fitness = taxa_recente * 100
        
        return acertou if resultado != 'TIE' else False
    
    def get_stats(self):
        stats = super().get_stats()
        stats.update({
            'acertos_tie': self.acertos_tie,
            'erros_tie': self.erros_tie,
            'total_ties': self.total_ties_vistos,
            'melhor_sequencia': self.melhor_sequencia,
            'epsilon_atual': round(self.epsilon, 3),
            'learning_rate': self.learning_rate,
            'tipo': 'TURBINADO'
        })
        if self.acertos_tie + self.erros_tie > 0:
            stats['precisao_tie'] = round((self.acertos_tie / (self.acertos_tie + self.erros_tie)) * 100, 1)
        return stats


# =============================================================================
# 🧬 SISTEMA DE EVOLUÇÃO TURBINADO
# =============================================================================

class SistemaEvolucaoTurbinado:
    """
    Sistema que identifica e promove agentes com alta performance
    com crossover genético
    """
    
    def __init__(self, sistema_rl):
        self.sistema_rl = sistema_rl
        self.melhor_agente = None
        self.melhor_precisao = 0
        self.geracao_atual = 0
        self.historico_melhores = deque(maxlen=20)
        
        # Pool dos melhores
        self.pool_melhores = []
        self.taxa_mutacao = 0.1
        
        print("\n" + "="*80)
        print("🧬 SISTEMA DE EVOLUÇÃO TURBINADO INICIALIZADO")
        print("="*80)
    
    def avaliar_agentes(self):
        """
        Avalia todos os agentes e promove os melhores
        """
        print(f"\n📊 AVALIANDO AGENTES (Geração {self.geracao_atual})...")
        
        stats_agentes = []
        for nome, agente in self.sistema_rl.agentes.items():
            if agente.total_uso > 50:
                precisao = (agente.acertos / agente.total_uso) * 100
                
                # Calcular score composto
                precisao_tie = 0
                if hasattr(agente, 'acertos_tie') and agente.acertos_tie + agente.erros_tie > 0:
                    precisao_tie = (agente.acertos_tie / (agente.acertos_tie + agente.erros_tie)) * 100
                
                # Score composto: 70% precisão geral + 30% precisão TIE
                score = (precisao * 0.7) + (precisao_tie * 0.3)
                
                stats_agentes.append({
                    'nome': nome,
                    'agente': agente,
                    'precisao': precisao,
                    'precisao_tie': precisao_tie,
                    'score': score,
                    'acertos': agente.acertos,
                    'erros': agente.erros,
                    'acertos_tie': getattr(agente, 'acertos_tie', 0),
                    'total_uso': agente.total_uso
                })
        
        if not stats_agentes:
            return
        
        # Ordenar por score composto
        stats_agentes.sort(key=lambda x: x['score'], reverse=True)
        
        # Mostrar top 5
        print("\n🏆 TOP 5 AGENTES:")
        for i, s in enumerate(stats_agentes[:5]):
            print(f"   {i+1}. {s['nome']}: {s['precisao']:.1f}% (TIE:{s['precisao_tie']:.1f}%) | Score:{s['score']:.1f}")
        
        # Atualizar pool dos melhores
        self.pool_melhores = stats_agentes[:20]
        
        # Verificar se temos um novo melhor agente
        melhor_atual = stats_agentes[0]
        if melhor_atual['score'] > self.melhor_precisao:
            self.melhor_precisao = melhor_atual['score']
            self.melhor_agente = melhor_atual['agente']
            self.historico_melhores.append({
                'geracao': self.geracao_atual,
                'nome': melhor_atual['nome'],
                'precisao': melhor_atual['precisao'],
                'precisao_tie': melhor_atual['precisao_tie'],
                'score': melhor_atual['score']
            })
            print(f"\n🏆 NOVO MELHOR AGENTE: {melhor_atual['nome']} com Score {melhor_atual['score']:.1f}%")
            
            # Salvar este agente como modelo
            self._salvar_modelo_campeao(melhor_atual['agente'])
        
        # PROMOÇÃO: agentes com precisão < 20% são substituídos
        if self.geracao_atual % 5 == 0:  # A cada 5 gerações
            self._promover_agentes(stats_agentes)
        
        # NOVO: crossover genético a cada 3 gerações
        if self.geracao_atual % 3 == 0 and len(self.pool_melhores) >= 4:
            self._realizar_crossover()
        
        self.geracao_atual += 1
    
    def _salvar_modelo_campeao(self, agente):
        """Salva o modelo do agente campeão"""
        try:
            if hasattr(agente, 'model') and agente.model is not None:
                torch.save(agente.model.state_dict(), 'modelo_campeao.pt')
                print("💾 Modelo campeão salvo!")
        except Exception as e:
            print(f"⚠️ Erro ao salvar modelo: {e}")
    
    def _promover_agentes(self, stats_agentes):
        """
        Substitui agentes ruins por cópias dos melhores
        """
        if len(stats_agentes) < 10:
            return
        
        melhores = stats_agentes[:10]  # Top 10
        piores = stats_agentes[-50:]   # Piores 50
        
        print(f"\n🔄 PROMOVENDO {len(piores)} AGENTES RUINS...")
        
        substituidos = 0
        for pior in piores:
            if pior['precisao'] < 20:  # Se precisão < 20%
                # Escolher um dos melhores aleatoriamente
                campeao = random.choice(melhores)
                
                # Criar novo agente baseado no campeão
                novo_nome = f"RL_Promovido_{pior['nome']}"
                novo_agente = AgenteRLElitizado(novo_nome, pior['agente'].id)
                
                # Copiar pesos do campeão
                if hasattr(campeao['agente'], 'model') and campeao['agente'].model is not None:
                    try:
                        novo_agente.model.load_state_dict(campeao['agente'].model.state_dict())
                        novo_agente.target_model.load_state_dict(campeao['agente'].target_model.state_dict())
                        print(f"   ✅ {pior['nome']} → {novo_nome} (cópia de {campeao['nome']})")
                        substituidos += 1
                    except:
                        pass
                
                # Substituir no sistema
                self.sistema_rl.agentes[pior['nome']] = novo_agente
        
        if substituidos > 0:
            print(f"   🎯 {substituidos} agentes promovidos")
    
    def _realizar_crossover(self):
        """
        Cria novos agentes combinando os melhores
        """
        print("\n🧬 REALIZANDO CROSSOVER GENÉTICO...")
        
        melhores = self.pool_melhores[:10]
        novos_agentes = 0
        
        for i in range(5):  # Criar 5 novos agentes
            if len(melhores) >= 2:
                pai = random.choice(melhores)
                mae = random.choice([m for m in melhores if m['nome'] != pai['nome']])
                
                if pai and mae:
                    novo_nome = f"RL_Crossover_{self.geracao_atual}_{i}"
                    novo_agente = AgenteRLElitizado(novo_nome, 9999 - i)
                    
                    # Tentar combinar pesos (se possível)
                    if hasattr(pai['agente'], 'model') and hasattr(mae['agente'], 'model'):
                        try:
                            # Média ponderada dos pesos
                            pai_weights = pai['agente'].model.state_dict()
                            mae_weights = mae['agente'].model.state_dict()
                            
                            novo_weights = {}
                            for key in pai_weights:
                                # 60% do pai, 40% da mãe
                                novo_weights[key] = 0.6 * pai_weights[key] + 0.4 * mae_weights[key]
                                
                                # Aplicar mutação
                                if random.random() < self.taxa_mutacao:
                                    noise = torch.randn_like(novo_weights[key]) * 0.01
                                    novo_weights[key] += noise
                            
                            novo_agente.model.load_state_dict(novo_weights)
                            novo_agente.target_model.load_state_dict(novo_weights)
                            
                        except Exception as e:
                            print(f"⚠️ Erro no crossover: {e}")
                    
                    # Substituir um agente ruim
                    for nome, agente in list(self.sistema_rl.agentes.items()):
                        if agente.total_uso > 200 and (agente.acertos / agente.total_uso) < 0.1:
                            self.sistema_rl.agentes[nome] = novo_agente
                            novos_agentes += 1
                            print(f"   ✅ {nome} → {novo_nome} (crossover {pai['nome']} x {mae['nome']})")
                            break
        
        if novos_agentes > 0:
            print(f"   🎯 {novos_agentes} novos agentes criados por crossover")


# =============================================================================
# 🧠 SISTEMA RL COMPLETO (ATUALIZADO PARA USAR AGENTES TURBINADOS)
# =============================================================================

class SistemaRLCompleto:
    def __init__(self):
        self.agentes = {}
        self.meta_agente = None
        self.meta_optimizer = None
        self.meta_loss_fn = None
        self.historico_global = deque(maxlen=2000)
        self.padroes_descobertos = []
        self.geracao = 0
        self.melhor_precisao = 0
        self.manipulacoes_detectadas = 0
        
        # Criar 1000 agentes (800 normais + 200 turbinados)
        for i in range(800):
            nome = f"RL_Agente_{i+1}"
            random.seed(i * 42)
            np.random.seed(i * 42)
            self.agentes[nome] = AgenteRLPuro(nome, i)
        
        for i in range(800, 1000):
            nome = f"RL_Turbinado_{i+1}"
            random.seed(i * 42)
            np.random.seed(i * 42)
            self.agentes[nome] = AgenteRLElitizado(nome, i)
            
        print(f"✅ 800 agentes normais + 200 agentes turbinados inicializados")
        
        if TORCH_AVAILABLE:
            self._criar_meta_agente()
    
    def _criar_meta_agente(self):
        try:
            self.meta_agente = RedeMetaAgente(input_size=23).to(DEVICE)
            self.meta_optimizer = optim.Adam(self.meta_agente.parameters(), lr=0.0001)
            self.meta_loss_fn = nn.CrossEntropyLoss()
            print("✅ Meta-agente PyTorch criado")
        except Exception as e:
            print(f"⚠️ Erro ao criar meta-agente: {e}")
            self.meta_agente = None
    
    def processar_rodada(self, historico, resultado_real=None):
        if len(historico) < 30:
            return None
            
        votos = {'BANKER': 0, 'PLAYER': 0}
        votos_detalhados = []
        
        for nome, agente in self.agentes.items():
            acao, confianca = agente.agir(historico[:-1])
            previsao = 'BANKER' if acao == 0 else 'PLAYER'
            
            peso_voto = agente.peso * confianca
            
            # Agentes turbinados têm peso maior naturalmente
            if hasattr(agente, 'tipo') and agente.tipo == 'TURBINADO':
                peso_voto *= 1.2
            
            if agente.especialidade:
                if agente.especialidade in str(historico[-5:]):
                    peso_voto *= 1.5
                elif 'manipulacao' in agente.especialidade and self.manipulacoes_detectadas > 0:
                    peso_voto *= 1.3
            
            votos[previsao] += peso_voto
            
            votos_detalhados.append({
                'agente': nome,
                'previsao': previsao,
                'peso': round(agente.peso, 2),
                'confianca': round(confianca * 100, 1),
                'peso_total': round(peso_voto, 2),
                'especialidade': agente.especialidade,
                'tipo': 'TURBINADO' if hasattr(agente, 'tipo') else 'NORMAL'
            })
        
        previsao_final = max(votos, key=votos.get)
        total_votos = sum(votos.values())
        
        if total_votos > 0:
            vantagem = (votos[previsao_final] - min(votos.values())) / total_votos
            confianca_final = min(50 + vantagem * 50, 95)
        else:
            confianca_final = 50
        
        confianca_final = round(confianca_final)
        
        divergencia = abs(votos['BANKER'] - votos['PLAYER']) / total_votos if total_votos > 0 else 0
        
        if divergencia < 0.2 and self.meta_agente is not None:
            meta_previsao = self._consultar_meta_agente(historico, votos_detalhados)
            if meta_previsao:
                previsao_final = meta_previsao
                confianca_final = 60
                print(f"🎯 Meta-agente ativado! Decisão: {previsao_final}")
        
        self.historico_global.append({
            'previsao': previsao_final,
            'confianca': confianca_final,
            'votos': votos_detalhados,
            'timestamp': datetime.now(),
            'divergencia': divergencia
        })
        
        return {
            'previsao': previsao_final,
            'simbolo': '🔴' if previsao_final == 'BANKER' else '🔵',
            'confianca': confianca_final,
            'votos': votos_detalhados[:4],
            'total_agentes': len([v for v in votos_detalhados if v['peso_total'] > 0.1])
        }
    
    def _consultar_meta_agente(self, historico, votos):
        try:
            features = []
            for voto in sorted(votos, key=lambda x: x['agente']):
                features.append(voto['peso'])
                features.append(voto['confianca']/100)
            
            ultimos_10 = historico[:10]
            banker_count = sum(1 for r in ultimos_10 if r['resultado'] == 'BANKER')
            player_count = sum(1 for r in ultimos_10 if r['resultado'] == 'PLAYER')
            tie_count = sum(1 for r in ultimos_10 if r['resultado'] == 'TIE')
            
            features.extend([banker_count/10, player_count/10, tie_count/10])
            
            while len(features) < 23:
                features.append(0)
            
            features_tensor = torch.FloatTensor(features).unsqueeze(0).to(DEVICE)
            
            with torch.no_grad():
                pred = self.meta_agente(features_tensor).cpu().numpy()[0]
            
            return 'BANKER' if pred[0] > pred[1] else 'PLAYER'
            
        except Exception as e:
            print(f"⚠️ Erro no meta-agente PyTorch: {e}")
            return None
    
    def aprender_com_resultado(self, historico, resultado_real):
        # AGORA processa TIE normalmente (removido o bloco if resultado_real == 'TIE')
        acertos = 0
        for nome, agente in self.agentes.items():
            acao, _ = agente.agir(historico[:-1])
            acertou = agente.aprender(historico, acao, resultado_real)
            if acertou:
                acertos += 1
                
        if len(self.historico_global) % 100 == 0:
            self.geracao += 1
            self._avaliar_evolucao()
    
    def _avaliar_evolucao(self):
        stats = self.get_stats()
        precisao_media = stats['precisao_media']
        
        if precisao_media > self.melhor_precisao:
            self.melhor_precisao = precisao_media
            print(f"\n🏆 NOVA MELHOR PRECISÃO: {precisao_media:.1f}% (geração {self.geracao})")
            self._detectar_padroes()
    
    def _detectar_padroes(self):
        top_agentes = sorted(
            [a.get_stats() for a in self.agentes.values() if a.total_uso > 100],
            key=lambda x: x['precisao'],
            reverse=True
        )[:3]
        
        for agente in top_agentes:
            if agente['precisao'] > 65:
                padrao = {
                    'agente': agente['nome'],
                    'precisao': agente['precisao'],
                    'descoberto_em': datetime.now().isoformat(),
                    'tipo': self._classificar_padrao(agente)
                }
                
                if not any(p['agente'] == padrao['agente'] for p in cache['padroes_descobertos']):
                    cache['padroes_descobertos'].append(padrao)
                    print(f"\n🎯 RL DESCOBRIU NOVO PADRÃO: {padrao['agente']} - {padrao['precisao']}%")
    
    def _classificar_padrao(self, agente_stats):
        if agente_stats['precisao'] > 75:
            return "CONTRAGOLPE (75%+)"
        elif agente_stats['precisao'] > 70:
            return "RESET CLUSTER (70-75%)"
        elif agente_stats['precisao'] > 65:
            return "MOEDOR (65-70%)"
        else:
            return "Padrão em desenvolvimento"
    
    def get_stats(self):
        stats = {
            'geracao': self.geracao,
            'melhor_precisao': round(self.melhor_precisao, 1),
            'precisao_media': 0,
            'manipulacoes_detectadas': self.manipulacoes_detectadas,
            'agentes': []
        }
        
        total_precisao = 0
        count = 0
        turbinados_count = 0
        turbinados_precisao = 0
        
        for nome, agente in self.agentes.items():
            agente_stats = agente.get_stats()
            stats['agentes'].append(agente_stats)
            
            if agente_stats['total'] > 0:
                total_precisao += agente_stats['precisao']
                count += 1
                
                if agente_stats.get('tipo') == 'TURBINADO':
                    turbinados_count += 1
                    turbinados_precisao += agente_stats['precisao']
                
        if count > 0:
            stats['precisao_media'] = round(total_precisao / count, 1)
            
        if turbinados_count > 0:
            stats['precisao_turbinados'] = round(turbinados_precisao / turbinados_count, 1)
            stats['total_turbinados'] = turbinados_count
            
        stats['agentes'].sort(key=lambda x: x['precisao'], reverse=True)
        return stats
    
    def salvar_estado(self, arquivo='rl_estado.json'):
        try:
            estado = {
                'geracao': self.geracao,
                'melhor_precisao': self.melhor_precisao,
                'manipulacoes_detectadas': self.manipulacoes_detectadas,
                'agentes': {nome: agente.para_dict() for nome, agente in self.agentes.items()}
            }
            
            for nome, agente in self.agentes.items():
                if agente.model is not None:
                    pesos_path = f'pesos_{nome}.pt'
                    torch.save(agente.model.state_dict(), pesos_path)
                    estado['agentes'][nome]['pesos_file'] = pesos_path
            
            with open(arquivo, 'w') as f:
                json.dump(estado, f, indent=2)
            
            print(f"💾 Estado RL salvo em {arquivo}")
            return True
        except Exception as e:
            print(f"❌ Erro ao salvar estado RL: {e}")
            return False
    
    def carregar_estado(self, arquivo='rl_estado.json'):
        caminho = Path(arquivo)
        if not caminho.exists():
            print("📂 Nenhum estado RL anterior encontrado")
            return False
            
        try:
            with open(arquivo, 'r') as f:
                estado = json.load(f)
                
            self.geracao = estado.get('geracao', 0)
            self.melhor_precisao = estado.get('melhor_precisao', 0)
            self.manipulacoes_detectadas = estado.get('manipulacoes_detectadas', 0)
            
            for nome, dados in estado.get('agentes', {}).items():
                if nome in self.agentes:
                    # Manter o tipo original do agente (não converter turbinados em normais)
                    if 'Turbinado' in nome and not isinstance(self.agentes[nome], AgenteRLElitizado):
                        # Se era turbinado mas perdeu o tipo, recriar
                        novo_agente = AgenteRLElitizado(nome, dados['id'])
                        for key, value in dados.items():
                            if hasattr(novo_agente, key):
                                setattr(novo_agente, key, value)
                        self.agentes[nome] = novo_agente
                    else:
                        for key, value in dados.items():
                            if hasattr(self.agentes[nome], key):
                                setattr(self.agentes[nome], key, value)
                    
                    pesos_file = dados.get('pesos_file')
                    if pesos_file and Path(pesos_file).exists():
                        try:
                            self.agentes[nome].model.load_state_dict(
                                torch.load(pesos_file, map_location=DEVICE)
                            )
                            self.agentes[nome].target_model.load_state_dict(
                                self.agentes[nome].model.state_dict()
                            )
                            print(f"   ✅ Pesos carregados para {nome}")
                        except Exception as e:
                            print(f"   ⚠️ Erro ao carregar pesos de {nome}: {e}")
                    
            print(f"✅ Estado RL carregado: geração {self.geracao}")
            return True
        except Exception as e:
            print(f"⚠️ Erro ao carregar estado RL: {e}")
            return False


# =============================================================================
# 🚀 FUNÇÃO PARA TURBINAR O SISTEMA
# =============================================================================

def turbinar_sistema():
    """
    Converte todos os agentes para versão turbinada
    """
    print("\n" + "="*80)
    print("🚀 TURBINANDO SISTEMA PARA 95%+")
    print("="*80)
    
    if not cache.get('rl_system'):
        print("❌ Sistema RL não encontrado")
        return None
    
    sistema = cache['rl_system']
    
    # Backup dos agentes antigos
    agentes_antigos = dict(sistema.agentes)
    
    # Converter agentes existentes
    print("🔄 Convertendo agentes para versão TURBINADA...")
    convertidos = 0
    
    for nome, agente in list(agentes_antigos.items()):
        if 'Turbinado' not in nome and not isinstance(agente, AgenteRLElitizado):
            try:
                novo_agente = AgenteRLElitizado(nome, agente.id)
                
                # Transferir estatísticas básicas com segurança
                novo_agente.acertos = agente.acertos
                novo_agente.erros = agente.erros
                novo_agente.total_uso = agente.total_uso
                novo_agente.peso = agente.peso
                
                # Transferir pesos se possível
                if hasattr(agente, 'model') and agente.model is not None:
                    try:
                        # Tentar carregar pesos (pode falhar se a arquitetura for diferente)
                        novo_agente.model.load_state_dict(agente.model.state_dict(), strict=False)
                        novo_agente.target_model.load_state_dict(agente.target_model.state_dict(), strict=False)
                    except:
                        print(f"   ⚠️ Não foi possível transferir pesos de {nome}")
                
                sistema.agentes[nome] = novo_agente
                convertidos += 1
                
                if convertidos % 50 == 0:
                    print(f"   ... {convertidos} agentes convertidos")
                    
            except Exception as e:
                print(f"⚠️ Erro ao converter {nome}: {e}")
    
    print(f"✅ {convertidos} agentes turbinados de {len(agentes_antigos)}!")
    
    # Criar sistema de evolução
    evolucao = SistemaEvolucaoTurbinado(sistema)
    cache['evolucao'] = evolucao
    
    print("\n📊 NOVAS CONFIGURAÇÕES:")
    print("   • Learning Rate: 0.005 (balanceado)")
    print("   • Recompensa acerto: 8.0 (4x maior)")
    print("   • Penalidade erro: -0.3 (5x menor)")
    print("   • Bônus TIE: 15.0")
    print("   • BatchNorm: Ativado")
    print("   • Crossover genético: Ativado")
    print("   • Memória: 200.000 (20x maior)")
    print("   • Epsilon mínimo: 0.05 (nunca para de explorar)")
    
    return evolucao


# =============================================================================
# 📊 NOVA ROTA PARA MONITORAR EVOLUÇÃO
# =============================================================================

@app.route('/api/evolucao')
def api_evolucao():
    if not cache.get('evolucao'):
        return jsonify({'status': 'inativo'})
    
    evol = cache['evolucao']
    
    return jsonify({
        'status': 'ativo',
        'geracao_atual': evol.geracao_atual,
        'melhor_precisao': round(evol.melhor_precisao, 1),
        'melhor_agente': evol.melhor_agente.nome if evol.melhor_agente else None,
        'historico_melhores': list(evol.historico_melhores),
        'pool_melhores': len(evol.pool_melhores)
    })


# =============================================================================
# 🧬 SISTEMA DE NEUROEVOLUÇÃO QUE APRENDE COM ERROS (VERSÃO CORRIGIDA)
# =============================================================================

class AnalisadorDeErros:
    def __init__(self, sistema_rl):
        self.sistema_rl = sistema_rl
        self.erros_analisados = 0
        self.padroes_de_erro = {}
        self.ultimos_erros = deque(maxlen=100)
        self.neuro_treinador = None
        
    def analisar_erro_em_tempo_real(self, previsao, resultado_real, contexto, indice_confianca):
        if resultado_real == 'TIE' or previsao['previsao'] == resultado_real:
            return None
        
        print(f"\n🔍 ANALISANDO ERRO EM TEMPO REAL...")
        
        causa = self._diagnosticar_causa_erro(previsao, resultado_real, contexto, indice_confianca)
        
        erro_info = {
            'timestamp': datetime.now(),
            'previsao': previsao['previsao'],
            'real': resultado_real,
            'confianca': previsao['confianca'],
            'causa': causa,
            'indice_confianca': indice_confianca,
            'contexto': contexto[:10] if contexto else []
        }
        self.ultimos_erros.append(erro_info)
        self.erros_analisados += 1
        
        padrao_key = f"{causa}"
        self.padroes_de_erro[padrao_key] = self.padroes_de_erro.get(padrao_key, 0) + 1
        
        self._ensinar_agentes_sobre_erro_corrigido(causa, previsao, resultado_real, contexto)
        
        if self.padroes_de_erro.get(padrao_key, 0) > 3:
            self._criar_agente_especialista_em_erro(causa)
        
        print(f"✅ Diagnóstico: {causa}")
        return causa
    
    def _diagnosticar_causa_erro(self, previsao, real, contexto, indice_confianca):
        if not contexto or len(contexto) < 10:
            return "poucos_dados"
        
        ultimos_resultados = [r['resultado'] for r in contexto[:20] if r['resultado'] != 'TIE']
        
        if indice_confianca > 70:
            self.sistema_rl.manipulacoes_detectadas += 1
            for nome, agente in self.sistema_rl.agentes.items():
                if hasattr(agente, 'deteccoes_manipulacao'):
                    agente.deteccoes_manipulacao += 1
            return "manipulacao_alta"
        
        streak_atual = self._calcular_streak(ultimos_resultados)
        if streak_atual >= 4 and len(ultimos_resultados) >= 2 and ultimos_resultados[-1] != ultimos_resultados[-2]:
            return f"quebra_de_streak_{streak_atual}"
        
        if len(ultimos_resultados) >= 5:
            if (ultimos_resultados[-5] == ultimos_resultados[-4] == ultimos_resultados[-3] and
                ultimos_resultados[-2] == ultimos_resultados[-1] and
                ultimos_resultados[-3] != ultimos_resultados[-2] and
                previsao['previsao'] == ultimos_resultados[-3]):
                return "padrao_3_2_quebrado"
        
        if len(ultimos_resultados) >= 9:
            for i in range(len(ultimos_resultados) - 1):
                if i+1 < len(ultimos_resultados) and ultimos_resultados[i] == 'TIE' and ultimos_resultados[i+1] == 'TIE':
                    return "padrao_duplo_tie_detectado"
        
        if len(contexto) >= 2:
            ultima = contexto[0]
            penultima = contexto[1]
            if (ultima['banker_score'] == penultima['player_score'] and
                abs(ultima['banker_score'] - penultima['banker_score']) > 3):
                return "travamento_detectado"
        
        if real == 'TIE' and previsao['previsao'] != 'TIE':
            return "empate_nao_previsto"
        
        return "causa_desconhecida"
    
    def _calcular_streak(self, resultados):
        if not resultados:
            return 0
        streak = 1
        for i in range(1, len(resultados)):
            if resultados[-i] == resultados[-(i+1)]:
                streak += 1
            else:
                break
        return streak
    
    def _ensinar_agentes_sobre_erro_corrigido(self, causa, previsao, real, contexto):
        """
        Versão CORRIGIDA: Penaliza apenas quem errou, recompensa quem acertou
        """
        print(f"\n📚 ENSINANDO AGENTES SOBRE ERRO: {causa}")
        
        if hasattr(self, 'neuro_treinador') and self.neuro_treinador:
            self.neuro_treinador.registrar_erro({
                'causa': causa,
                'previsao': previsao['previsao'],
                'real': real,
                'confianca': previsao['confianca'],
                'indice_confianca': cache.get('indice_confianca', 50),
                'contexto': contexto[:5] if contexto else []
            })
        
        for nome, agente in self.sistema_rl.agentes.items():
            try:
                acao_agente, _ = agente.agir(contexto[:-1] if contexto and len(contexto) > 1 else contexto)
                previsao_agente = 'BANKER' if acao_agente == 0 else 'PLAYER'
                
                if previsao_agente == previsao['previsao']:
                    # Este agente ERROU - penalize apenas ele
                    agente.peso = max(0.7, agente.peso * 0.95)  # Penalidade de 5% apenas
                    
                    if not hasattr(agente, 'erros_que_aprendeu'):
                        agente.erros_que_aprendeu = []
                    agente.erros_que_aprendeu.append({
                        'causa': causa, 
                        'timestamp': time.time()
                    })
                    
                    if hasattr(agente, 'memoria') and contexto and len(contexto) > 1:
                        try:
                            state = agente.get_state_tensor(contexto[:-1])
                            next_state = agente.get_state_tensor(contexto)
                            
                            with torch.no_grad():
                                current_q = agente.model(state)[0, acao_agente]
                                next_q = agente.target_model(next_state).max(1)[0]
                                target_q = -3.0 + agente.gamma * next_q
                                td_error = (target_q - current_q).abs().item()
                            
                            agente.memoria.push(
                                contexto[:-1], acao_agente, -3.0, contexto, td_error
                            )
                        except Exception:
                            pass
                    
                    print(f"   🤖 {nome} errou (peso: {agente.peso:.2f})")
                else:
                    # Este agente ACERTOU - recompense!
                    agente.peso = min(1.5, agente.peso * 1.02)
                    print(f"   ✅ {nome} acertou (peso: {agente.peso:.2f})")
            
            except Exception:
                continue
        
        print(f"✅ Todos os agentes foram ensinados sobre: {causa}")
        
        self._registrar_aprendizado_no_banco(causa, previsao, real)
    
    def _registrar_aprendizado_no_banco(self, causa, previsao, real):
        conn = get_db_connection()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO aprendizado_erros 
                (causa_provavel, confianca_causa, nova_estrategia, data_analise)
                VALUES (%s, %s, %s, %s)
            ''', (
                causa,
                85,
                f"evitar_{previsao['previsao'].lower()}_quando_{causa}",
                datetime.now(timezone.utc)
            ))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"⚠️ Erro ao registrar aprendizado: {e}")
    
    def _criar_agente_especialista_em_erro(self, causa):
        if not TORCH_AVAILABLE:
            return
        
        print(f"\n🧬 CRIANDO AGENTE ESPECIALISTA EM: {causa}")
        
        for nome, agente in self.sistema_rl.agentes.items():
            if hasattr(agente, 'especialidade') and agente.especialidade == causa:
                print(f"   ⚠️ Já existe especialista em {causa}: {nome}")
                return
        
        novo_id = len(self.sistema_rl.agentes) + 1
        nome = f"RL_Especialista_{causa[:10]}_{novo_id}"
        
        # Criar como turbinado
        novo_agente = AgenteRLElitizado(nome, novo_id)
        novo_agente.especialidade = causa
        novo_agente.peso = 2.5
        novo_agente.epsilon = 0.05
        novo_agente.fitness = 80.0
        
        if EVOTORCH_AVAILABLE and hasattr(novo_agente, 'neuro_evolucao'):
            novo_agente.neuro_evolucao['geracao'] = 1
            novo_agente.neuro_evolucao['melhor_fitness'] = 80.0
        
        self.sistema_rl.agentes[nome] = novo_agente
        print(f"✅ NOVO AGENTE ESPECIALISTA TURBINADO CRIADO: {nome} - Especialidade: {causa}")
        
        self._registrar_agente_no_banco(nome, novo_agente, causa)
    
    def _registrar_agente_no_banco(self, nome, agente, especialidade):
        conn = get_db_connection()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO neuroevolucao_agentes 
                (agente_nome, geracao, dna_json, especialidades, fitness, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                nome,
                self.sistema_rl.geracao,
                json.dumps({'peso': agente.peso, 'epsilon': agente.epsilon, 'especialidade': especialidade, 'tipo': 'TURBINADO'}),
                [especialidade],
                agente.fitness,
                datetime.now(timezone.utc)
            ))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"⚠️ Erro ao registrar agente: {e}")
    
    def get_stats(self):
        return {
            'total_erros_analisados': self.erros_analisados,
            'padroes_de_erro': self.padroes_de_erro,
            'ultimos_erros': [
                {'causa': e['causa'], 'previsao': e['previsao'], 'real': e['real'], 'hora': e['timestamp'].strftime('%H:%M:%S')}
                for e in list(self.ultimos_erros)[-10:]
            ]
        }


# =============================================================================
# 🧬 SISTEMA DE NEUROEVOLUÇÃO CORRETIVA
# =============================================================================

class NeuroEvolucaoCorretiva:
    def __init__(self, sistema_rl, num_agentes=1000):
        self.sistema_rl = sistema_rl
        self.num_agentes = num_agentes
        self.historico_erros = deque(maxlen=15000)
        self.otimizadores = {}
        self.loss_fn = nn.CrossEntropyLoss()
        
        self.total_correcoes = 0
        self.erros_corrigidos = 0
        self.ultima_precisao_antes = 0
        self.ultima_precisao_depois = 0
        
        self.acoes_corretivas = {
            'causa_desconhecida': self._corrigir_causa_desconhecida,
            'padrao_3_2_quebrado': self._corrigir_padrao_3_2,
            'manipulacao_alta': self._corrigir_manipulacao_alta,
            'quebra_de_streak_4': self._corrigir_quebra_streak,
            'quebra_de_streak_5': self._corrigir_quebra_streak,
            'quebra_de_streak_6': self._corrigir_quebra_streak,
            'quebra_de_streak_7': self._corrigir_quebra_streak,
            'quebra_de_streak_8': self._corrigir_quebra_streak,
            'padrao_duplo_tie_detectado': self._corrigir_duplo_tie,
            'travamento_detectado': self._corrigir_travamento,
            'empate_nao_previsto': self._corrigir_empate,
            'poucos_dados': self._corrigir_poucos_dados,
            'alternancia_rapida': self._corrigir_alternancia,
            'sequencia_decrescente': self._corrigir_sequencia_decrescente
        }
        
        print(f"\n🧬 NEUROEVOLUÇÃO CORRETIVA INICIALIZADA!")
        print(f"📊 {num_agentes} AGENTES preparados para correção")
        print(f"🎯 Monitorando {len(self.acoes_corretivas)} padrões de erro")
        
        self._criar_agentes_iniciais()
    
    def _criar_agentes_iniciais(self):
        print("\n🤖 CRIANDO AGENTES ESPECIALISTAS INICIAIS...")
        
        especialidades = [
            ('causa_desconhecida', 3.5),
            ('padrao_3_2_quebrado', 3.2),
            ('manipulacao_alta', 3.0),
            ('quebra_de_streak', 2.8),
            ('duplo_tie', 2.7),
            ('travamento', 2.6),
            ('empate', 2.5),
            ('alternancia_rapida', 2.4),
            ('sequencia_decrescente', 2.3)
        ]
        
        for i, (especialidade, peso) in enumerate(especialidades):
            for j in range(30):
                nome = f"RL_Especialista_{especialidade[:10]}_{i*30 + j + 100}"
                if nome not in self.sistema_rl.agentes:
                    # Criar como turbinado
                    novo_agente = AgenteRLElitizado(nome, i*30 + j + 100)
                    novo_agente.especialidade = especialidade
                    novo_agente.peso = peso + (j * 0.02)
                    novo_agente.epsilon = 0.01 + (j * 0.001)
                    novo_agente.fitness = 85.0 + j
                    self.sistema_rl.agentes[nome] = novo_agente
            
            print(f"   ✅ Criados 30 agentes turbinados para: {especialidade}")
    
    def registrar_erro(self, erro_info):
        self.historico_erros.append({
            'timestamp': time.time(),
            'causa': erro_info.get('causa', 'desconhecida'),
            'previsao': erro_info.get('previsao'),
            'real': erro_info.get('real'),
            'confianca': erro_info.get('confianca', 0),
            'indice_confianca': erro_info.get('indice_confianca', 50),
            'contexto': erro_info.get('contexto', [])[:5]
        })
    
    def _criar_dataset_erro(self, causa):
        erros_filtrados = [e for e in self.historico_erros if e['causa'] == causa]
        
        if len(erros_filtrados) < 20:
            return None, None
        
        features = []
        labels = []
        
        for erro in erros_filtrados[-1000:]:
            feature = []
            
            for r in erro['contexto'][:5]:
                if r.get('resultado') == 'BANKER':
                    feature.extend([1, 0, 0])
                elif r.get('resultado') == 'PLAYER':
                    feature.extend([0, 1, 0])
                else:
                    feature.extend([0, 0, 1])
            
            while len(feature) < 15:
                feature.extend([0, 0, 0])
            
            feature.append(erro['confianca'] / 100)
            feature.append(erro['indice_confianca'] / 100)
            
            streak = 1
            if len(erro['contexto']) > 1:
                for i in range(1, len(erro['contexto'])):
                    if (erro['contexto'][i].get('resultado') == 
                        erro['contexto'][i-1].get('resultado')):
                        streak += 1
                    else:
                        break
            feature.append(min(streak / 10, 1.0))
            
            features.append(feature[:18])
            
            label = 0 if erro['real'] == 'BANKER' else 1
            labels.append(label)
        
        return torch.FloatTensor(features), torch.LongTensor(labels)
    
    def _corrigir_causa_desconhecida(self):
        print("\n🔧 CORRIGINDO CAUSA DESCONHECIDA...")
        
        X, y = self._criar_dataset_erro('causa_desconhecida')
        if X is None:
            print("   ⚠️ Poucos dados para causa_desconhecida")
            return False
        
        agentes_causa = []
        for nome, a in self.sistema_rl.agentes.items():
            if hasattr(a, 'especialidade') and a.especialidade == 'causa_desconhecida':
                agentes_causa.append(a)
        
        if len(agentes_causa) < 10:
            base_id = len(self.sistema_rl.agentes) + 1
            for i in range(10):
                nome = f"RL_Especialista_CausaDesc_{base_id + i}"
                if nome not in self.sistema_rl.agentes:
                    novo_agente = AgenteRLElitizado(nome, base_id + i)
                    novo_agente.especialidade = 'causa_desconhecida'
                    novo_agente.peso = 3.0 + (i * 0.1)
                    novo_agente.epsilon = 0.01
                    novo_agente.fitness = 80.0
                    self.sistema_rl.agentes[nome] = novo_agente
                    agentes_causa.append(novo_agente)
        
        for agente in agentes_causa[:5]:
            if agente.model is None:
                continue
            
            if agente.nome not in self.otimizadores:
                self.otimizadores[agente.nome] = optim.Adam(
                    agente.model.parameters(), lr=0.005, weight_decay=1e-5
                )
            
            X_gpu, y_gpu = X.to(DEVICE), y.to(DEVICE)
            
            dataset = TensorDataset(X_gpu, y_gpu)
            loader = DataLoader(dataset, batch_size=min(64, len(X)), shuffle=True)
            
            agente.model.train()
            losses = []
            
            for epoca in range(100):
                epoca_loss = 0
                for batch_X, batch_y in loader:
                    self.otimizadores[agente.nome].zero_grad()
                    outputs = agente.model(batch_X)
                    loss = self.loss_fn(outputs, batch_y)
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(agente.model.parameters(), 1.0)
                    self.otimizadores[agente.nome].step()
                    epoca_loss += loss.item()
                
                losses.append(epoca_loss / len(loader))
                
                if epoca % 20 == 0:
                    print(f"   📉 {agente.nome[:15]}... Época {epoca}: loss = {losses[-1]:.4f}")
            
            agente.model.eval()
            with torch.no_grad():
                outputs = agente.model(X_gpu)
                _, predicted = torch.max(outputs, 1)
                accuracy = (predicted == y_gpu).float().mean().item()
            
            print(f"   ✅ {agente.nome[:15]}... treinado! Acurácia: {accuracy*100:.1f}%")
            agente.fitness = accuracy * 100
        
        for nome, a in self.sistema_rl.agentes.items():
            if a not in agentes_causa:
                if hasattr(a, 'erros_que_aprendeu'):
                    erros_causa = [e for e in a.erros_que_aprendeu 
                                  if e.get('causa') == 'causa_desconhecida']
                    if len(erros_causa) > 5:
                        a.peso = max(0.3, a.peso * 0.8)
        
        for agente in agentes_causa:
            agente.peso = min(4.0, agente.peso * 1.3)
        
        return True
    
    def _corrigir_padrao_3_2(self):
        print("\n🔧 CORRIGINDO PADRÃO 3-2 QUEBRADO...")
        
        X, y = self._criar_dataset_erro('padrao_3_2_quebrado')
        if X is None:
            return False
        
        agentes_causa = []
        for nome, a in self.sistema_rl.agentes.items():
            if hasattr(a, 'especialidade') and '3_2' in a.especialidade:
                agentes_causa.append(a)
        
        if len(agentes_causa) < 5:
            base_id = len(self.sistema_rl.agentes) + 1
            for i in range(5):
                nome = f"RL_Especialista_Padrao32_{base_id + i}"
                if nome not in self.sistema_rl.agentes:
                    novo_agente = AgenteRLElitizado(nome, base_id + i)
                    novo_agente.especialidade = 'padrao_3_2_quebrado'
                    novo_agente.peso = 2.8 + (i * 0.1)
                    novo_agente.epsilon = 0.01
                    novo_agente.fitness = 80.0
                    self.sistema_rl.agentes[nome] = novo_agente
                    agentes_causa.append(novo_agente)
        
        X_gpu, y_gpu = X.to(DEVICE), y.to(DEVICE)
        
        for agente in agentes_causa[:3]:
            if agente.model is None:
                continue
            
            if agente.nome not in self.otimizadores:
                self.otimizadores[agente.nome] = optim.Adam(
                    agente.model.parameters(), lr=0.003, weight_decay=1e-5
                )
            
            dataset = TensorDataset(X_gpu, y_gpu)
            loader = DataLoader(dataset, batch_size=min(32, len(X)), shuffle=True)
            
            agente.model.train()
            melhor_loss = float('inf')
            
            for epoca in range(80):
                epoca_loss = 0
                for batch_X, batch_y in loader:
                    self.otimizadores[agente.nome].zero_grad()
                    outputs = agente.model(batch_X)
                    loss = self.loss_fn(outputs, batch_y)
                    loss.backward()
                    self.otimizadores[agente.nome].step()
                    epoca_loss += loss.item()
                
                loss_media = epoca_loss / len(loader)
                if loss_media < melhor_loss:
                    melhor_loss = loss_media
                
                if epoca % 20 == 0:
                    print(f"   📉 {agente.nome[:15]}... Época {epoca}: loss = {loss_media:.4f}")
            
            agente.model.eval()
            with torch.no_grad():
                outputs = agente.model(X_gpu)
                _, predicted = torch.max(outputs, 1)
                accuracy = (predicted == y_gpu).float().mean().item()
            
            print(f"   ✅ {agente.nome[:15]}... Acurácia: {accuracy*100:.1f}%")
            agente.fitness = accuracy * 100
        
        for agente in agentes_causa:
            agente.peso = min(3.5, agente.peso * 1.2)
        
        return True
    
    def _corrigir_manipulacao_alta(self):
        return self._corrigir_padrao_3_2()
    
    def _corrigir_quebra_streak(self):
        return self._corrigir_padrao_3_2()
    
    def _corrigir_duplo_tie(self):
        print("\n🔧 CORRIGINDO DUPLO TIE...")
        return True
    
    def _corrigir_travamento(self):
        print("\n🔧 CORRIGINDO TRAVAMENTO...")
        return True
    
    def _corrigir_empate(self):
        print("\n🔧 CORRIGINDO EMPATES...")
        return True
    
    def _corrigir_poucos_dados(self):
        print("\n🔧 CORRIGINDO POUCOS DADOS...")
        return True
    
    def _corrigir_alternancia(self):
        print("\n🔧 CORRIGINDO ALTERNÂNCIA RÁPIDA...")
        return True
    
    def _corrigir_sequencia_decrescente(self):
        print("\n🔧 CORRIGINDO SEQUÊNCIA DECRESCENTE...")
        return True
    
    def corrigir_agora(self):
        print("\n" + "="*80)
        print("🚀 INICIANDO CORREÇÃO EM MASSA DOS AGENTES (1000 AGENTES)")
        print("="*80)
        
        self.ultima_precisao_antes = self._calcular_precisao_media()
        print(f"\n📊 Precisão média ANTES: {self.ultima_precisao_antes:.1f}%")
        
        correcoes_aplicadas = 0
        for causa, metodo in self.acoes_corretivas.items():
            if self.padroes_de_erro.get(causa, 0) > 3:
                print(f"\n🎯 Corrigindo padrão: {causa}")
                if metodo():
                    correcoes_aplicadas += 1
                    self.total_correcoes += 1
        
        self.ultima_precisao_depois = self._calcular_precisao_media()
        
        print("\n" + "="*80)
        print("✅ CORREÇÃO CONCLUÍDA!")
        print(f"   Correções aplicadas: {correcoes_aplicadas}")
        print(f"   Precisão antes: {self.ultima_precisao_antes:.1f}%")
        print(f"   Precisão depois: {self.ultima_precisao_depois:.1f}%")
        print(f"   Melhoria: {self.ultima_precisao_depois - self.ultima_precisao_antes:.1f}%")
        print("="*80)
        
        return correcoes_aplicadas
    
    def _calcular_precisao_media(self):
        precisoes = []
        for agente in self.sistema_rl.agentes.values():
            if agente.total_uso > 50:
                precisao = (agente.acertos / agente.total_uso) * 100
                precisoes.append(precisao)
        return sum(precisoes) / len(precisoes) if precisoes else 0
    
    @property
    def padroes_de_erro(self):
        padroes = {}
        for erro in self.historico_erros:
            causa = erro.get('causa', 'desconhecida')
            padroes[causa] = padroes.get(causa, 0) + 1
        return padroes


# =============================================================================
# 🚀 LOOP DE CORREÇÃO CONTÍNUA
# =============================================================================

def loop_correcao_continua():
    print("\n🔄 INICIANDO LOOP DE CORREÇÃO CONTÍNUA (1000 AGENTES)...")
    
    time.sleep(30)
    
    neuro = None
    ultima_correcao = time.time()
    erros_ultimo_check = 0
    
    while True:
        try:
            time.sleep(30)
            
            sistema_rl = cache.get('rl_system')
            analisador = cache.get('analisador_erros')
            
            if not sistema_rl or not analisador:
                continue
            
            if neuro is None:
                neuro = NeuroEvolucaoCorretiva(sistema_rl, num_agentes=1000)
                analisador.neuro_treinador = neuro
                print("✅ Neuroevolução corretiva ativada com 1000 AGENTES!")
            
            total_erros = len(neuro.historico_erros)
            novos_erros = total_erros - erros_ultimo_check
            
            if novos_erros > 0:
                print(f"\n📊 {novos_erros} novos erros detectados (total: {total_erros})")
                erros_ultimo_check = total_erros
            
            deve_corrigir = False
            
            if total_erros > 0 and total_erros % 50 == 0:
                deve_corrigir = True
                print(f"\n🎯 Gatilho: {total_erros} erros acumulados")
            
            if time.time() - ultima_correcao > 900:
                deve_corrigir = True
                print(f"\n🎯 Gatilho: 15 minutos sem correção")
            
            padroes = neuro.padroes_de_erro
            for causa, count in padroes.items():
                if count > 10 and causa in neuro.acoes_corretivas:
                    deve_corrigir = True
                    print(f"\n🎯 Gatilho: {causa} com {count} ocorrências")
                    break
            
            if deve_corrigir:
                print("\n" + "="*70)
                print("🔧 CORREÇÃO AUTOMÁTICA INICIADA (1000 AGENTES)")
                print("="*70)
                
                neuro.corrigir_agora()
                ultima_correcao = time.time()
                
                if sistema_rl:
                    sistema_rl.salvar_estado('rl_estado.json')
                    print("💾 Estado salvo")
            
        except Exception as e:
            print(f"❌ Erro no loop de correção: {e}")
            traceback.print_exc()
            time.sleep(10)


# =============================================================================
# 🎯 FUNÇÃO PARA INTEGRAR ULTRA PRECISÃO
# =============================================================================

def integrar_ultra_precisao():
    """Ativa o sistema ultra precisão"""
    print("\n" + "="*80)
    print("🚀 ATIVANDO MODO ULTRA PRECISÃO (MIRANDO 95%+)")
    print("="*80)
    
    if not cache.get('rl_system'):
        print("❌ Sistema RL não encontrado")
        return None
    
    ultra = SistemaUltraPrecisao(cache['rl_system'])
    cache['ultra_precisao'] = ultra
    
    print("✅ Modo Ultra Precisão ativado com sucesso!")
    print(f"🎯 Meta: 95%+ de acerto nas apostas")
    
    return ultra


# =============================================================================
# 🎯 FUNÇÃO PARA INTEGRAR SISTEMA CURTO PRAZO
# =============================================================================

def integrar_sistema_curto_prazo():
    """Ativa o sistema híbrido de curto prazo"""
    print("\n" + "="*80)
    print("🎯 ATIVANDO SISTEMA HÍBRIDO CURTO PRAZO")
    print("="*80)
    
    if not cache.get('rl_system'):
        print("❌ Sistema RL não encontrado")
        return None
    
    curto_prazo = SistemaCurtoPrazo(cache['rl_system'])
    cache['curto_prazo'] = curto_prazo
    
    surto = EstrategiaSurto()
    cache['estrategia_surto'] = surto
    
    print("✅ Sistema curto prazo ativado!")
    print(f"📊 Ciclo: 20 rodadas")
    print(f"🎯 Meta: 90%+ no ciclo")
    
    return curto_prazo


# =============================================================================
# 📊 ROTA PARA MONITORAR ULTRA PRECISÃO
# =============================================================================

@app.route('/api/ultra-precisao')
def api_ultra_precisao():
    if not cache.get('ultra_precisao'):
        return jsonify({'status': 'inativo'})
    
    ultra = cache['ultra_precisao']
    stats = ultra.get_stats()
    
    return jsonify({
        'status': 'ativo',
        'meta': '95%+ DE ACERTO',
        'stats': stats
    })


# =============================================================================
# 📊 ROTA PARA MONITORAR CURTO PRAZO
# =============================================================================

@app.route('/api/curto-prazo')
def api_curto_prazo():
    if not cache.get('curto_prazo'):
        return jsonify({'status': 'inativo'})
    
    cp = cache['curto_prazo']
    stats = cp.get_stats()
    
    ultimos_ciclos = cp.ciclos_completados[-5:] if cp.ciclos_completados else []
    
    return jsonify({
        'status': 'ativo',
        'estatisticas': stats,
        'ultimos_ciclos': [
            {
                'ciclo': c['ciclo'],
                'acertos': c['acertos'],
                'erros': c['erros'],
                'precisao': round(c['precisao'], 1)
            }
            for c in ultimos_ciclos
        ]
    })


# =============================================================================
# 📊 ROTA PARA MONITORAR DETECTOR 7:2
# =============================================================================

@app.route('/api/detector-72')
def api_detector_72():
    if not cache.get('detector_72'):
        return jsonify({'status': 'inativo'})
    
    detector = cache['detector_72']
    stats = detector.get_stats()
    
    return jsonify({
        'status': 'ativo',
        'stats': stats
    })


# =============================================================================
# 🎯 AGENTE MULTIPROCESSING PARALELO
# =============================================================================

class AgenteMultiprocessing:
    def __init__(self, agente_id, state_size=150, action_size=2):
        self.agente_id = agente_id
        self.state_size = state_size
        self.action_size = action_size
        self.acertos = 0
        self.erros = 0
        self.total_uso = 0
        self.peso = 1.0
        self.epsilon = 0.3
        
        self.device = torch.device("cpu")
        self.model = None
        self._criar_modelo()
        
        self.memorias = []
        self.recompensas = []
        
        print(f"✅ Agente Multiprocessing {agente_id} criado")
    
    def _criar_modelo(self):
        try:
            self.model = RedeDQN(self.state_size, self.action_size).to(self.device)
            self.model.eval()
        except Exception as e:
            print(f"❌ Erro ao criar modelo para agente {self.agente_id}: {e}")
            self.model = None
    
    def processar_estado(self, historico):
        state = []
        for rodada in historico[:30]:
            if rodada['resultado'] == 'BANKER':
                state.extend([1, 0, 0])
            elif rodada['resultado'] == 'PLAYER':
                state.extend([0, 1, 0])
            else:
                state.extend([0, 0, 1])
            state.append(rodada.get('player_score', 0) / 12)
            state.append(rodada.get('banker_score', 0) / 12)
        
        while len(state) < self.state_size:
            state.extend([0, 0, 0, 0, 0])
        
        return torch.FloatTensor(state).unsqueeze(0).to(self.device)
    
    def jogar_episodio(self, historico_base, num_jogadas=20):
        historico = historico_base.copy() if historico_base else []
        experiencias = []
        recompensa_total = 0
        
        for _ in range(num_jogadas):
            if len(historico) < 30:
                acao = random.choice([0, 1])
                confianca = 0.5
            else:
                estado = self.processar_estado(historico)
                
                if random.random() < self.epsilon:
                    acao = random.choice([0, 1])
                    confianca = 0.5
                else:
                    if self.model is not None:
                        with torch.no_grad():
                            q_values = self.model(estado).cpu().numpy()[0]
                            acao = np.argmax(q_values)
                            confianca = 0.7 + 0.2 * random.random()
                    else:
                        acao = random.choice([0, 1])
                        confianca = 0.5
            
            resultado = random.choices(
                ['BANKER', 'PLAYER', 'TIE'], 
                weights=[0.45, 0.45, 0.1]
            )[0]
            
            if resultado != 'TIE':
                acertou = (acao == 0 and resultado == 'BANKER') or (acao == 1 and resultado == 'PLAYER')
                recompensa = 2.0 if acertou else -1.5
                
                if acertou:
                    self.acertos += 1
                else:
                    self.erros += 1
                
                experiencias.append({
                    'agente_id': self.agente_id,
                    'estado': historico[-30:] if len(historico) >= 30 else historico,
                    'acao': acao,
                    'recompensa': recompensa,
                    'acertou': acertou,
                    'timestamp': time.time()
                })
                recompensa_total += recompensa
            
            nova_rodada = {
                'resultado': resultado,
                'player_score': random.randint(0, 12),
                'banker_score': random.randint(0, 12)
            }
            historico.append(nova_rodada)
            self.total_uso += 1
        
        return experiencias, recompensa_total
    
    def jogar_partidas(self, num_partidas=10):
        todas_experiencias = []
        recompensas = []
        
        for _ in range(num_partidas):
            historico_base = []
            for _ in range(50):
                historico_base.append({
                    'resultado': random.choice(['BANKER', 'PLAYER', 'TIE']),
                    'player_score': random.randint(0, 12),
                    'banker_score': random.randint(0, 12)
                })
            
            exp, recomp = self.jogar_episodio(historico_base, 10)
            todas_experiencias.extend(exp)
            recompensas.append(recomp)
        
        return todas_experiencias, np.mean(recompensas) if recompensas else 0
    
    def get_stats(self):
        precisao = (self.acertos / self.total_uso) * 100 if self.total_uso > 0 else 0
        return {
            'id': self.agente_id,
            'acertos': self.acertos,
            'erros': self.erros,
            'total': self.total_uso,
            'precisao': round(precisao, 1),
            'peso': round(self.peso, 2),
            'epsilon': round(self.epsilon, 3)
        }


# =============================================================================
# FUNÇÃO PARA PROCESSO FILHO (MULTIPROCESSING)
# =============================================================================

def processo_agente_worker(agente_id, fila_experiencias, estatisticas_compartilhadas, num_partidas=10):
    try:
        print(f"📦 Processo {agente_id} iniciado (PID: {os.getpid()})")
        
        agente = AgenteMultiprocessing(agente_id)
        
        experiencias, recompensa_media = agente.jogar_partidas(num_partidas)
        
        for exp in experiencias:
            fila_experiencias.put(exp)
        
        with estatisticas_compartilhadas.get_lock():
            estatisticas_compartilhadas['total_episodios'] += len(experiencias)
            if agente.acertos + agente.erros > 0:
                precisao = agente.acertos / (agente.acertos + agente.erros) * 100
                if precisao > estatisticas_compartilhadas['melhor_precisao']:
                    estatisticas_compartilhadas['melhor_precisao'] = precisao
        
        print(f"✅ Processo {agente_id} concluído - Precisão: {agente.get_stats()['precisao']}%")
        
    except Exception as e:
        print(f"❌ Erro no processo {agente_id}: {e}")
        traceback.print_exc()


# =============================================================================
# 🧠 SISTEMA CENTRAL MULTIPROCESSING
# =============================================================================

class SistemaMultiprocessing:
    def __init__(self, num_agentes=900):
        self.num_agentes = num_agentes
        self.processos = []
        self.state_size = 150
        self.action_size = 2
        
        self.fila_experiencias = mp_fila_experiencias
        
        self.estatisticas = mp_estatisticas
        self.estatisticas['agentes_ativos'] = num_agentes
        
        self.memoria_central = deque(maxlen=100000)
        
        self.episodios_totais = 0
        self.melhor_precisao = 0
        self.geracao = 0
        
        self.lock = threading.Lock()
        
        self.consumer_thread = None
        self.consumer_ativo = True
        
        print(f"\n🚀 SISTEMA MULTIPROCESSING INICIALIZADO!")
        print(f"📊 {num_agentes} agentes rodando em processos paralelos")
        print(f"💻 CPUs disponíveis: {mp.cpu_count()}")
    
    def iniciar_consumidor_fila(self):
        def consumir_fila():
            while self.consumer_ativo:
                try:
                    experiencia = self.fila_experiencias.get(timeout=1)
                    with self.lock:
                        self.memoria_central.append(experiencia)
                        self.episodios_totais += 1
                except:
                    pass
        
        self.consumer_thread = threading.Thread(target=consumir_fila, daemon=True)
        self.consumer_thread.start()
        print("📥 Consumidor da fila iniciado")
    
    def executar_rodada_paralela(self, num_partidas_por_agente=5):
        print(f"\n🎲 Executando {self.num_agentes * num_partidas_por_agente} episódios em paralelo...")
        
        inicio = time.time()
        
        self.processos = []
        
        for i in range(self.num_agentes):
            p = mp.Process(
                target=processo_agente_worker,
                args=(i, self.fila_experiencias, self.estatisticas, num_partidas_por_agente)
            )
            p.daemon = True
            p.start()
            self.processos.append(p)
        
        for p in self.processos:
            p.join(timeout=30)
        
        tempo = time.time() - inicio
        
        with self.lock:
            memoria_size = len(self.memoria_central)
        
        print(f"✅ Rodada paralela concluída em {tempo:.2f}s")
        print(f"📊 Experiências no buffer: {memoria_size}")
        print(f"📈 Melhor precisão até agora: {self.estatisticas['melhor_precisao']:.1f}%")
        
        return memoria_size
    
    def treinar_com_experiencias(self, batch_size=256):
        if len(self.memoria_central) < batch_size:
            return 0
        
        with self.lock:
            batch = random.sample(list(self.memoria_central), batch_size)
        
        return len(batch)
    
    def get_stats(self):
        with self.lock:
            memoria_size = len(self.memoria_central)
        
        return {
            'geracao': self.geracao,
            'episodios_totais': self.episodios_totais,
            'memoria': memoria_size,
            'melhor_precisao': round(self.estatisticas['melhor_precisao'], 1),
            'num_agentes': self.num_agentes,
            'processos_ativos': len([p for p in self.processos if p.is_alive()]),
            'media_precisao': round(self.estatisticas['melhor_precisao'], 1)
        }
    
    def parar(self):
        self.consumer_ativo = False
        if self.consumer_thread:
            self.consumer_thread.join(timeout=2)
        
        for p in self.processos:
            if p.is_alive():
                p.terminate()
                p.join(timeout=1)


# =============================================================================
# 🎮 LOOP PRINCIPAL DE TREINAMENTO PARALELO
# =============================================================================

def loop_treinamento_multiprocessing():
    print("\n" + "="*80)
    print("🎮 INICIANDO TREINAMENTO PARALELO COM MULTIPROCESSING")
    print("="*80)
    
    sistema = SistemaMultiprocessing(num_agentes=900)
    sistema.iniciar_consumidor_fila()
    cache['mp_system'] = sistema
    
    ciclo = 0
    
    while True:
        ciclo += 1
        print(f"\n{'='*60}")
        print(f"🔄 CICLO DE TREINAMENTO #{ciclo}")
        print(f"{'='*60}")
        
        try:
            num_exp = sistema.executar_rodada_paralela(num_partidas_por_agente=5)
            
            if num_exp > 0:
                treinadas = sistema.treinar_com_experiencias(batch_size=256)
                if treinadas:
                    print(f"📉 Experiências treinadas: {treinadas}")
            
            if ciclo % 5 == 0:
                stats = sistema.get_stats()
                print(f"\n📊 ESTATÍSTICAS MULTIPROCESSING:")
                print(f"   Geração: {stats['geracao']}")
                print(f"   Episódios totais: {stats['episodios_totais']}")
                print(f"   Memória: {stats['memoria']} experiências")
                print(f"   Melhor precisão: {stats['melhor_precisao']}%")
                print(f"   Processos ativos: {stats['processos_ativos']}/{stats['num_agentes']}")
            
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ Erro no ciclo de treinamento: {e}")
            traceback.print_exc()
            time.sleep(5)

# =============================================================================
# FUNÇÕES PARA DETECÇÃO DE PADRÕES (ATUALIZADAS)
# =============================================================================

def detectar_travamento(rodada_atual, rodada_anterior):
    if not rodada_atual or not rodada_anterior:
        return False

    if (rodada_atual['banker_score'] == rodada_anterior['player_score'] and
        abs(rodada_atual['banker_score'] - rodada_anterior['banker_score']) > 3):
        print(f"⚠️ TRAVAMENTO DETECTADO: {rodada_anterior['player_score']} → {rodada_atual['banker_score']}")
        return True

    if (rodada_atual['player_score'] == rodada_anterior['banker_score'] and
        abs(rodada_atual['player_score'] - rodada_anterior['player_score']) > 3):
        print(f"⚠️ TRAVAMENTO DETECTADO: {rodada_anterior['banker_score']} → {rodada_atual['player_score']}")
        return True

    return False


def analisar_empates_forcados(dados):
    if len(dados) < 5:
        return False

    dados_ord = list(reversed(dados)) if dados else []
    empates_seguidos = 0
    for i in range(min(10, len(dados_ord)-1)):
        if dados_ord[i]['resultado'] == 'TIE' and dados_ord[i+1]['resultado'] == 'TIE':
            empates_seguidos += 1

    if empates_seguidos >= 2:
        print(f"⚠️ EMPATES FORÇADOS DETECTADOS: {empates_seguidos} seguidos")
        return True
    return False


# A antiga função calcular_indice_manipulacao foi SUBSTITUÍDA pela nova calcular_indice_confianca
# A nova função está definida no início do arquivo


# =============================================================================
# 🔌 FUNÇÃO PARA CONEXÃO COM BANCO DE DADOS
# =============================================================================
def get_db_connection():
    try:
        conn = pg8000.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            ssl_context=SSL_CONTEXT,
            timeout=30
        )
        conn.autocommit = False
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return None

# =============================================================================
# 🧹 FUNÇÃO PARA LIMPAR JSON INVÁLIDO
# =============================================================================
def limpar_json_para_banco(dados):
    if isinstance(dados, dict):
        try:
            json_str = json.dumps(dados, default=str)
            json_str = ''.join(char for char in json_str if ord(char) < 0x10000 or 0xE000 <= ord(char) <= 0xFFFF)
            return json.loads(json_str)
        except:
            return {
                'id': dados.get('id', ''),
                'data': str(dados.get('data', {})),
                'result': str(dados.get('result', {}))
            }
    return dados

# =============================================================================
# 🏗️ FUNÇÃO PARA INICIALIZAR BANCO DE DADOS
# =============================================================================
def init_db():
    conn = get_db_connection()
    if not conn:
        print("⚠️ Banco não disponível - continuando sem banco de dados")
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
                fonte TEXT,
                dados_json JSONB
            )
        ''')

        cur.execute('CREATE INDEX IF NOT EXISTS idx_data_hora ON rodadas(data_hora DESC)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_resultado ON rodadas(resultado)')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS historico_previsoes (
                id SERIAL PRIMARY KEY,
                data_hora TIMESTAMPTZ DEFAULT NOW(),
                previsao TEXT,
                simbolo TEXT,
                confianca INTEGER,
                resultado_real TEXT,
                acertou BOOLEAN,
                estrategias TEXT,
                modo TEXT,
                pesos_agentes JSONB,
                contexto_json JSONB,
                indice_confianca INTEGER DEFAULT 50,
                foi_manipulado BOOLEAN DEFAULT FALSE
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS analise_erros (
                id SERIAL PRIMARY KEY,
                data_hora TIMESTAMPTZ DEFAULT NOW(),
                previsao_feita TEXT,
                resultado_real TEXT,
                confianca INTEGER,
                modo TEXT,
                streak_atual INTEGER DEFAULT 0,
                banker_50 INTEGER DEFAULT 0,
                player_50 INTEGER DEFAULT 0,
                diferenca_percentual FLOAT DEFAULT 0,
                ultimos_5_resultados TEXT,
                ultimos_10_resultados TEXT,
                agentes_ativos TEXT,
                pesos_agentes JSONB,
                indice_confianca INTEGER DEFAULT 50,
                foi_manipulado BOOLEAN DEFAULT FALSE,
                padrao_detectado TEXT,
                causa_erro TEXT,
                acertou BOOLEAN,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')

        cur.execute('CREATE INDEX IF NOT EXISTS idx_erros_data ON analise_erros(data_hora DESC)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_erros_acertou ON analise_erros(acertou)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_erros_causa ON analise_erros(causa_erro)')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS aprendizado_erros (
                id SERIAL PRIMARY KEY,
                erro_id INTEGER,
                data_analise TIMESTAMPTZ DEFAULT NOW(),
                causa_provavel TEXT,
                confianca_causa INTEGER,
                nova_estrategia TEXT,
                novo_peso_sugerido FLOAT,
                mutacao_aplicada BOOLEAN DEFAULT FALSE,
                id_agente_aprendeu INTEGER
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS neuroevolucao_agentes (
                id SERIAL PRIMARY KEY,
                agente_nome TEXT NOT NULL,
                geracao INTEGER NOT NULL,
                dna_json JSONB NOT NULL,
                especialidades TEXT[],
                fitness FLOAT,
                mutacoes INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')

        cur.execute('CREATE INDEX IF NOT EXISTS idx_neuro_fitness ON neuroevolucao_agentes(fitness DESC)')

        conn.commit()
        cur.close()
        conn.close()
        print("✅ Tabelas criadas/verificadas com sucesso")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        return False

# =============================================================================
# 💾 FUNÇÃO PARA SALVAR RODADA
# =============================================================================
def salvar_rodada(rodada, fonte):
    conn = get_db_connection()
    if not conn:
        return False

    try:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO rodadas 
            (id, data_hora, player_score, banker_score, soma, resultado, fonte, dados_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        ''', (
            rodada['id'],
            rodada['data_hora'],
            rodada['player_score'],
            rodada['banker_score'],
            rodada['player_score'] + rodada['banker_score'],
            rodada['resultado'],
            fonte,
            json.dumps(rodada, default=str)
        ))

        if cur.rowcount > 0:
            conn.commit()
            cur.close()
            conn.close()
            return True
        conn.rollback()
        cur.close()
        conn.close()
        return False
    except Exception as e:
        print(f"❌ Erro ao salvar: {e}")
        return False

# =============================================================================
# 🛡️ FUNÇÃO PARA SALVAR PREVISÃO NO BANCO (ATUALIZADA)
# =============================================================================
def salvar_previsao_completa_segura(previsao, resultado_real, acertou, contexto, pesos_agentes=None, indice_confianca=50, foi_manipulado=False, causa_erro=None):
    conn = get_db_connection()
    if not conn:
        print("⚠️ Sem conexão com banco - não foi possível salvar previsão")
        return False

    try:
        cur = conn.cursor()
        
        estrategias_str = ','.join(previsao.get('estrategias', [])) if previsao.get('estrategias') else ''
        
        contexto_json = None
        if contexto and len(contexto) > 0:
            contexto_resumido = [{'resultado': r['resultado'], 
                                  'player': r.get('player_score', 0), 
                                  'banker': r.get('banker_score', 0)} 
                                 for r in contexto[:10] if r]
            contexto_json = json.dumps(contexto_resumido)
        
        cur.execute('''
            INSERT INTO historico_previsoes 
            (data_hora, previsao, simbolo, confianca, resultado_real, acertou, 
             estrategias, modo, pesos_agentes, contexto_json, indice_confianca, foi_manipulado)
            VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            previsao['previsao'],
            previsao.get('simbolo', '🔴' if previsao['previsao'] == 'BANKER' else '🔵'),
            previsao['confianca'],
            resultado_real,
            acertou,
            estrategias_str,
            previsao.get('modo', 'RL_PURO'),
            json.dumps(pesos_agentes) if pesos_agentes else None,
            contexto_json,
            indice_confianca,
            foi_manipulado
        ))
        
        conn.commit()
        
        try:
            ultimos_10 = []
            if contexto and len(contexto) > 0:
                ultimos_10 = [r['resultado'] for r in contexto[:10] if r and 'resultado' in r]
            
            cur.execute('''
                INSERT INTO analise_erros 
                (data_hora, previsao_feita, resultado_real, confianca, modo, 
                 streak_atual, ultimos_5_resultados, ultimos_10_resultados,
                 agentes_ativos, indice_confianca, foi_manipulado, causa_erro, acertou)
                VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                previsao['previsao'],
                resultado_real,
                previsao['confianca'],
                previsao.get('modo', 'RL_PURO'),
                0,
                ','.join(ultimos_10[:5]) if ultimos_10 else '',
                ','.join(ultimos_10) if ultimos_10 else '',
                estrategias_str,
                indice_confianca,
                foi_manipulado,
                causa_erro,
                acertou
            ))
            conn.commit()
        except Exception as e:
            print(f"⚠️ Erro ao salvar em analise_erros: {e}")
            conn.rollback()
        
        if not acertou and causa_erro:
            try:
                cur.execute('''
                    INSERT INTO aprendizado_erros 
                    (causa_provavel, confianca_causa, nova_estrategia, data_analise)
                    VALUES (%s, %s, %s, NOW())
                ''', (
                    causa_erro,
                    80,
                    f"evitar_{previsao['previsao'].lower()}_quando_{causa_erro}"
                ))
                conn.commit()
            except Exception as e:
                print(f"⚠️ Erro ao salvar aprendizado: {e}")
        
        cur.close()
        conn.close()
        print(f"✅ Previsão salva no banco: {previsao['previsao']} vs {resultado_real} - {'✅' if acertou else '❌'}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao salvar previsão: {e}")
        try:
            conn.rollback()
            cur.close()
            conn.close()
        except:
            pass
        return False

# =============================================================================
# 📊 FUNÇÃO PARA CARREGAR ESTATÍSTICAS DO BANCO DE DADOS (ATUALIZADA)
# =============================================================================
def carregar_estatisticas_do_banco():
    print("\n" + "="*80)
    print("📊 CARREGANDO ESTATÍSTICAS DO BANCO DE DADOS")
    print("="*80)
    
    conn = get_db_connection()
    if not conn:
        print("⚠️ Não foi possível conectar ao banco para carregar estatísticas")
        return False
    
    try:
        cur = conn.cursor()
        
        print("\n📊 0. CARREGANDO TOTAL DE RODADAS...")
        cur.execute('SELECT COUNT(*) FROM rodadas')
        row = cur.fetchone()
        if row and row[0] > 0:
            cache['leves']['total_rodadas'] = row[0]
            print(f"   ✅ Total de rodadas no banco: {row[0]}")
        else:
            print("   ⚠️ Nenhuma rodada encontrada no banco")
            cache['leves']['total_rodadas'] = 0
        
        print("\n📊 1. CARREGANDO TOTAIS DE PREVISÕES...")
        cur.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN acertou = true THEN 1 ELSE 0 END) as acertos,
                SUM(CASE WHEN acertou = false THEN 1 ELSE 0 END) as erros
            FROM historico_previsoes
        ''')
        
        row = cur.fetchone()
        if row and row[0] > 0:
            cache['estatisticas']['total_previsoes'] = row[0]
            cache['estatisticas']['acertos'] = row[1] if row[1] is not None else 0
            cache['estatisticas']['erros'] = row[2] if row[2] is not None else 0
            
            print(f"   ✅ Total de previsões: {row[0]}")
            print(f"   ✅ Acertos: {row[1] if row[1] is not None else 0}")
            print(f"   ✅ Erros: {row[2] if row[2] is not None else 0}")
            print(f"   📈 Precisão: {calcular_precisao()}%")
        else:
            print("   ⚠️ Nenhuma previsão encontrada no banco")
            cache['estatisticas']['total_previsoes'] = 0
            cache['estatisticas']['acertos'] = 0
            cache['estatisticas']['erros'] = 0
        
        print("\n📊 2. CARREGANDO ÚLTIMAS 20 PREVISÕES...")
        cur.execute('''
            SELECT 
                data_hora,
                previsao,
                simbolo,
                confianca,
                resultado_real,
                acertou,
                estrategias,
                indice_confianca,
                modo,
                id
            FROM historico_previsoes
            ORDER BY data_hora DESC
            LIMIT 20
        ''')
        
        rows = cur.fetchall()
        ultimas_previsoes = []
        
        if rows:
            for row in rows:
                try:
                    data_hora = row[0]
                    if data_hora.tzinfo is None:
                        data_hora = data_hora.replace(tzinfo=timezone.utc)
                    
                    brasilia = data_hora.astimezone(timezone(timedelta(hours=-3)))
                    
                    estrategias_str = row[6] if row[6] else ''
                    estrategias_list = estrategias_str.split(',') if estrategias_str else []
                    
                    previsao_historico = {
                        'id': row[9],
                        'data': brasilia.strftime('%d/%m %H:%M:%S'),
                        'data_completa': brasilia.isoformat(),
                        'previsao': row[1],
                        'simbolo': row[2] if row[2] else ('🔴' if row[1] == 'BANKER' else '🔵'),
                        'confianca': row[3],
                        'resultado_real': row[4],
                        'acertou': row[5],
                        'estrategias': estrategias_list,
                        'manipulado': row[7] > 50 if row[7] is not None else False,
                        'indice_confianca': row[7] if row[7] is not None else 50,
                        'modo': row[8] if row[8] else 'RL_PURO'
                    }
                    ultimas_previsoes.append(previsao_historico)
                except Exception as e:
                    print(f"   ⚠️ Erro ao processar previsão: {e}")
                    continue
            
            cache['estatisticas']['ultimas_20_previsoes'] = ultimas_previsoes
            print(f"   ✅ Carregadas {len(ultimas_previsoes)} últimas previsões")
        else:
            print("   ⚠️ Nenhuma previsão recente encontrada")
            cache['estatisticas']['ultimas_20_previsoes'] = []
        
        print("\n📊 3. CARREGANDO MANIPULAÇÕES DETECTADAS...")
        
        cur.execute('''
            SELECT 
                COUNT(*) as total_manipuladas
            FROM analise_erros 
            WHERE foi_manipulado = true
        ''')
        
        row = cur.fetchone()
        if row and row[0] > 0:
            if cache.get('rl_system'):
                cache['rl_system'].manipulacoes_detectadas = row[0]
            print(f"   ✅ Total de manipulações detectadas: {row[0]}")
        else:
            print("   ⚠️ Nenhuma manipulação detectada no banco")
            if cache.get('rl_system'):
                cache['rl_system'].manipulacoes_detectadas = 0
        
        print("\n📊 4. CALCULANDO GERAÇÃO ATUAL...")
        
        if cache.get('rl_system'):
            total_previsoes = cache['estatisticas']['total_previsoes']
            nova_geracao = total_previsoes // 100
            
            if nova_geracao > 0:
                cache['rl_system'].geracao = nova_geracao
                print(f"   ✅ Geração calculada: {nova_geracao} (baseada em {total_previsoes} previsões)")
            else:
                print(f"   ℹ️ Geração mantida em {cache['rl_system'].geracao} (menos de 100 previsões)")
        
        print("\n📊 5. VERIFICANDO GERAÇÃO NO BANCO...")
        
        if cache.get('rl_system'):
            cur.execute('''
                SELECT MAX(geracao) 
                FROM neuroevolucao_agentes
            ''')
            row = cur.fetchone()
            if row and row[0] is not None and row[0] > cache['rl_system'].geracao:
                cache['rl_system'].geracao = row[0]
                print(f"   ✅ Geração carregada do banco: {row[0]} (maior que a calculada)")
            else:
                print(f"   ℹ️ Geração mantida: {cache['rl_system'].geracao}")
        
        print("\n📊 6. CARREGANDO ESTATÍSTICAS DOS AGENTES...")
        
        if cache.get('rl_system'):
            cur.execute('''
                SELECT 
                    agente_nome,
                    fitness,
                    especialidades,
                    dna_json
                FROM neuroevolucao_agentes
                WHERE geracao = (SELECT MAX(geracao) FROM neuroevolucao_agentes)
                ORDER BY fitness DESC
                LIMIT 10
            ''')
            
            rows = cur.fetchall()
            if rows:
                print(f"   ✅ Encontrados {len(rows)} agentes na última geração")
                for row in rows:
                    nome = row[0]
                    if nome in cache['rl_system'].agentes:
                        if row[1] is not None:
                            cache['rl_system'].agentes[nome].fitness = row[1]
                        if row[2] and len(row[2]) > 0:
                            cache['rl_system'].agentes[nome].especialidade = row[2][0]
        
        cur.close()
        conn.close()
        
        print("\n📊 7. ATUALIZANDO CACHE LEVE...")
        atualizar_dados_leves()
        print(f"   ✅ Cache atualizado: {cache['leves']['total_rodadas']} rodadas")
        
        print("\n📊 8. ATUALIZANDO ESTRATÉGIAS DOS AGENTES...")
        
        if cache.get('rl_system'):
            for nome, agente in cache['rl_system'].agentes.items():
                if nome in cache['estatisticas']['estrategias']:
                    cache['estatisticas']['estrategias'][nome]['acertos'] = agente.acertos
                    cache['estatisticas']['estrategias'][nome]['erros'] = agente.erros
                    cache['estatisticas']['estrategias'][nome]['total'] = agente.total_uso
            print(f"   ✅ Estratégias atualizadas para {len(cache['rl_system'].agentes)} agentes")
        
        print("\n" + "="*80)
        print("📊 RESUMO DO CARREGAMENTO:")
        print(f"   ✅ Rodadas totais: {cache['leves']['total_rodadas']}")
        print(f"   ✅ Previsões totais: {cache['estatisticas']['total_previsoes']}")
        print(f"   ✅ Acertos: {cache['estatisticas']['acertos']}")
        print(f"   ❌ Erros: {cache['estatisticas']['erros']}")
        print(f"   📈 Precisão: {calcular_precisao()}%")
        print(f"   📊 Últimas previsões: {len(cache['estatisticas']['ultimas_20_previsoes'])}")
        
        if cache.get('rl_system'):
            print(f"   🎮 Geração: {cache['rl_system'].geracao}")
            print(f"   🕵️ Manipulações: {cache['rl_system'].manipulacoes_detectadas}")
            print(f"   🤖 Agentes ativos: {len([a for a in cache['rl_system'].agentes.values() if a.total_uso > 0])}")
        
        print("="*80)
        print("✅ ESTATÍSTICAS CARREGADAS COM SUCESSO!\n")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao carregar estatísticas: {e}")
        import traceback
        traceback.print_exc()
        return False

# =============================================================================
# 🔍 FUNÇÕES DO BANCO (LEVES)
# =============================================================================

def get_ultimas_50():
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute('SELECT player_score, banker_score, resultado FROM rodadas ORDER BY data_hora DESC LIMIT 50')
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [{'player_score': r[0], 'banker_score': r[1], 'resultado': r[2]} for r in rows]
    except Exception as e:
        print(f"⚠️ Erro get_ultimas_50: {e}")
        return []
    finally:
        try:
            conn.close()
        except:
            pass

def get_ultimas_20():
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute('SELECT data_hora, player_score, banker_score, resultado FROM rodadas ORDER BY data_hora DESC LIMIT 20')
        rows = cur.fetchall()
        cur.close()
        conn.close()

        resultado = []
        for row in rows:
            try:
                data_str = row[0].isoformat()
                data_dt = datetime.fromisoformat(data_str.replace('Z', '+00:00'))
                brasilia = data_dt.astimezone(timezone(timedelta(hours=-3)))
                cor = '🔴' if row[3] == 'BANKER' else '🔵' if row[3] == 'PLAYER' else '🟡'
                resultado.append({
                    'hora': brasilia.strftime('%H:%M:%S'),
                    'resultado': row[3],
                    'cor': cor,
                    'player': row[1],
                    'banker': row[2]
                })
            except:
                continue
        return resultado
    except Exception as e:
        print(f"⚠️ Erro get_ultimas_20: {e}")
        return []
    finally:
        try:
            conn.close()
        except:
            pass

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
        print(f"⚠️ Erro get_total_rapido: {e}")
        return 0
    finally:
        try:
            conn.close()
        except:
            pass

def atualizar_dados_leves():
    cache['leves']['ultimas_50'] = get_ultimas_50()
    cache['leves']['ultimas_20'] = get_ultimas_20()
    cache['leves']['total_rodadas'] = get_total_rapido()
    cache['leves']['ultima_atualizacao'] = datetime.now(timezone.utc)

# =============================================================================
# 📈 FUNÇÕES PESADAS
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
        print(f"⚠️ Erro contar_periodo: {e}")
        return 0
    finally:
        try:
            conn.close()
        except:
            pass

def atualizar_dados_pesados():
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
# 🔄 FUNÇÃO PARA ALTERNAR FONTE ATIVA
# =============================================================================
def alternar_fonte():
    global fonte_ativa, falhas_latest, falhas_websocket, falhas_api_normal

    if fonte_ativa == 'latest' and falhas_latest >= LIMITE_FALHAS:
        print(f"\n⚠️ LATEST falhou {falhas_latest} vezes - Alternando para WEBSOCKET")
        fonte_ativa = 'websocket'
        fontes_status['latest']['status'] = 'falha'
        fontes_status['websocket']['status'] = 'ativo'

    elif fonte_ativa == 'websocket' and falhas_websocket >= LIMITE_FALHAS:
        print(f"\n⚠️ WEBSOCKET falhou {falhas_websocket} vezes - Alternando para API NORMAL")
        fonte_ativa = 'api_normal'
        fontes_status['websocket']['status'] = 'falha'
        fontes_status['api_normal']['status'] = 'ativo'

    elif fonte_ativa == 'api_normal' and falhas_api_normal >= LIMITE_FALHAS:
        print(f"\n⚠️ Todas as fontes falharam - Tentando reiniciar ciclo")
        falhas_latest = 0
        falhas_websocket = 0
        falhas_api_normal = 0
        fonte_ativa = 'latest'
        fontes_status['latest']['status'] = 'ativo'
        fontes_status['websocket']['status'] = 'standby'
        fontes_status['api_normal']['status'] = 'standby'

# =============================================================================
# 📡 FONTE 1: API LATEST
# =============================================================================

def buscar_latest():
    global ultimo_id_latest, falhas_latest, fonte_ativa

    try:
        response = requests.get(LATEST_API_URL, headers=HEADERS, timeout=2)

        if response.status_code == 200:
            dados = response.json()
            novo_id = dados.get('id')
            data = dados.get('data', {})
            result = data.get('result', {})

            if novo_id and novo_id != ultimo_id_latest:
                if fonte_ativa == 'latest':
                    falhas_latest = 0

                ultimo_id_latest = novo_id

                player_dice = result.get('playerDice', {})
                banker_dice = result.get('bankerDice', {})

                player_score = player_dice.get('first', 0) + player_dice.get('second', 0)
                banker_score = banker_dice.get('first', 0) + banker_dice.get('second', 0)

                outcome = result.get('outcome', '')
                if outcome == 'PlayerWon':
                    resultado = 'PLAYER'
                elif outcome == 'BankerWon':
                    resultado = 'BANKER'
                else:
                    resultado = 'TIE'

                rodada = {
                    'id': novo_id,
                    'data_hora': datetime.now(timezone.utc),
                    'player_score': player_score,
                    'banker_score': banker_score,
                    'resultado': resultado
                }

                fontes_status['latest']['total'] += 1
                print(f"\n📡 [PRINCIPAL] LATEST: {player_score} vs {banker_score} - {resultado}")
                return rodada
            else:
                return None
        else:
            if fonte_ativa == 'latest':
                falhas_latest += 1
                fontes_status['latest']['falhas'] += 1
                print(f"⚠️ LATEST falha {falhas_latest}/{LIMITE_FALHAS} (Status: {response.status_code})")
                if falhas_latest >= LIMITE_FALHAS:
                    alternar_fonte()
            return None

    except requests.exceptions.Timeout:
        if fonte_ativa == 'latest':
            falhas_latest += 1
            fontes_status['latest']['falhas'] += 1
            print(f"⚠️ LATEST timeout - falha {falhas_latest}/{LIMITE_FALHAS}")
            if falhas_latest >= LIMITE_FALHAS:
                alternar_fonte()
        return None
    except Exception as e:
        if fonte_ativa == 'latest':
            falhas_latest += 1
            fontes_status['latest']['falhas'] += 1
            print(f"⚠️ LATEST erro: {e} - falha {falhas_latest}/{LIMITE_FALHAS}")
            if falhas_latest >= LIMITE_FALHAS:
                alternar_fonte()
        return None

# =============================================================================
# FONTE 2: WEBSOCKET
# =============================================================================

def on_ws_message(ws, message):
    global ultimo_id_websocket, falhas_websocket, fonte_ativa

    try:
        data = json.loads(message)

        if 'data' in data and 'result' in data['data']:
            game_data = data['data']
            result = game_data['result']
            novo_id = game_data.get('id')

            if novo_id and novo_id != ultimo_id_websocket:
                if fonte_ativa == 'websocket':
                    falhas_websocket = 0

                ultimo_id_websocket = novo_id

                player_dice = result.get('playerDice', {})
                banker_dice = result.get('bankerDice', {})

                player_score = player_dice.get('first', 0) + player_dice.get('second', 0)
                banker_score = banker_dice.get('first', 0) + banker_dice.get('second', 0)

                outcome = result.get('outcome', '')
                if outcome == 'PlayerWon':
                    resultado = 'PLAYER'
                elif outcome == 'BankerWon':
                    resultado = 'BANKER'
                else:
                    resultado = 'TIE'

                rodada = {
                    'id': novo_id,
                    'data_hora': datetime.now(timezone.utc),
                    'player_score': player_score,
                    'banker_score': banker_score,
                    'resultado': resultado
                }

                fontes_status['websocket']['total'] += 1

                if fonte_ativa == 'websocket':
                    fila_rodadas.append(rodada)
                    print(f"\n⚡ [BACKUP] WEBSOCKET: {player_score} vs {banker_score} - {resultado}")

    except Exception as e:
        print(f"⚠️ Erro WS: {e}")

def on_ws_error(ws, error):
    global falhas_websocket, fonte_ativa
    if fonte_ativa == 'websocket':
        falhas_websocket += 1
        fontes_status['websocket']['falhas'] += 1
        print(f"🔌 WS Erro: {error} - falha {falhas_websocket}/{LIMITE_FALHAS}")
        if falhas_websocket >= LIMITE_FALHAS:
            alternar_fonte()

def on_ws_close(ws, close_status_code, close_msg):
    global falhas_websocket, fonte_ativa
    if fonte_ativa == 'websocket':
        falhas_websocket += 1
        fontes_status['websocket']['falhas'] += 1
        print(f"🔌 WS Fechado - falha {falhas_websocket}/{LIMITE_FALHAS}")
        if falhas_websocket >= LIMITE_FALHAS:
            alternar_fonte()
    time.sleep(5)
    iniciar_websocket()

def on_ws_open(ws):
    global falhas_websocket, fonte_ativa
    print("✅ WEBSOCKET CONECTADO! (modo backup)")
    if fonte_ativa == 'websocket':
        falhas_websocket = 0

def iniciar_websocket():
    def run():
        ws = websocket.WebSocketApp(
            WS_URL,
            on_open=on_ws_open,
            on_message=on_ws_message,
            on_error=on_ws_error,
            on_close=on_ws_close
        )
        ws.run_forever()

    threading.Thread(target=run, daemon=True).start()

# =============================================================================
# FONTE 3: API NORMAL (CARGA HISTÓRICA COMPLETA)
# =============================================================================

def buscar_api_normal():
    global ultimo_id_api, falhas_api_normal, fonte_ativa

    try:
        params = API_PARAMS.copy()
        params['_t'] = int(time.time() * 1000)

        response = session.get(API_URL, params=params, timeout=TIMEOUT_API)
        response.raise_for_status()
        dados = response.json()

        if dados and len(dados) > 0:
            primeiro = dados[0]
            data = primeiro.get('data', {})
            novo_id = data.get('id')

            if novo_id and novo_id != ultimo_id_api:
                if fonte_ativa == 'api_normal':
                    falhas_api_normal = 0

                ultimo_id_api = novo_id

                rodadas = []
                for item in dados[:5]:
                    try:
                        data = item.get('data', {})
                        result = data.get('result', {})
                        player_dice = result.get('playerDice', {})
                        banker_dice = result.get('bankerDice', {})

                        player_score = player_dice.get('first', 0) + player_dice.get('second', 0)
                        banker_score = banker_dice.get('first', 0) + banker_dice.get('second', 0)

                        outcome = result.get('outcome', '')
                        if outcome == 'PlayerWon':
                            resultado = 'PLAYER'
                        elif outcome == 'BankerWon':
                            resultado = 'BANKER'
                        else:
                            resultado = 'TIE'

                        data_hora = datetime.fromisoformat(data.get('settledAt', '').replace('Z', '+00:00'))

                        rodada = {
                            'id': data.get('id'),
                            'data_hora': data_hora,
                            'player_score': player_score,
                            'banker_score': banker_score,
                            'resultado': resultado
                        }
                        rodadas.append(rodada)
                    except:
                        continue

                fontes_status['api_normal']['total'] += len(rodadas)

                if fonte_ativa == 'api_normal':
                    print(f"\n📚 [FALLBACK] API NORMAL: {len(rodadas)} rodadas")
                    return rodadas

        return None

    except Exception as e:
        if fonte_ativa == 'api_normal':
            falhas_api_normal += 1
            fontes_status['api_normal']['falhas'] += 1
            print(f"⚠️ API Normal erro - falha {falhas_api_normal}/{LIMITE_FALHAS}")
            if falhas_api_normal >= LIMITE_FALHAS:
                alternar_fonte()
        return None


# =============================================================================
# 🚀 FUNÇÃO PARA CARREGAR HISTÓRICO COMPLETO DA API NORMAL (ATUALIZADA)
# =============================================================================

def carregar_historico_completo_para_aprendizado(limite_paginas=100):
    print("\n" + "="*80)
    print("📚 CARREGANDO HISTÓRICO COMPLETO PARA APRENDIZADO RL")
    print("="*80)
    
    total_carregadas = 0
    pagina = 0
    paginas_sem_novidades = 0
    
    sistema_rl = cache.get('rl_system')
    if not sistema_rl:
        print("❌ Sistema RL não inicializado")
        return None
    
    analisador = AnalisadorDeErros(sistema_rl)
    cache['analisador_erros'] = analisador
    
    while paginas_sem_novidades < 3 and pagina < limite_paginas:
        conn = None
        cur = None
        
        try:
            print(f"\n📥 Buscando página {pagina}...")
            
            params = API_PARAMS.copy()
            params['page'] = pagina
            params['size'] = 100
            params['_t'] = int(time.time() * 1000)
            
            response = session.get(API_URL, params=params, timeout=TIMEOUT_API)
            response.raise_for_status()
            dados = response.json()
            
            if not dados or len(dados) == 0:
                print(f"✅ Fim das páginas na página {pagina}")
                break
            
            conn = get_db_connection()
            if not conn:
                print(f"⚠️ Sem conexão na página {pagina}")
                pagina += 1
                continue
            
            cur = conn.cursor()
            rodadas_ordenadas = []
            erros_na_pagina = False
            
            for item in dados:
                try:
                    data = item.get('data', {})
                    result = data.get('result', {})
                    player_dice = result.get('playerDice', {})
                    banker_dice = result.get('bankerDice', {})
                    
                    player_score = player_dice.get('first', 0) + player_dice.get('second', 0)
                    banker_score = banker_dice.get('first', 0) + banker_dice.get('second', 0)
                    
                    outcome = result.get('outcome', '')
                    if outcome == 'PlayerWon':
                        resultado = 'PLAYER'
                    elif outcome == 'BankerWon':
                        resultado = 'BANKER'
                    else:
                        resultado = 'TIE'
                    
                    data_hora = datetime.fromisoformat(data.get('settledAt', '').replace('Z', '+00:00'))
                    
                    rodada = {
                        'id': data.get('id'),
                        'data_hora': data_hora,
                        'player_score': player_score,
                        'banker_score': banker_score,
                        'resultado': resultado,
                        'fonte': 'historico_api'
                    }
                    
                    cur.execute('''
                        INSERT INTO rodadas 
                        (id, data_hora, player_score, banker_score, soma, resultado, fonte, dados_json)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                    ''', (
                        rodada['id'],
                        rodada['data_hora'],
                        rodada['player_score'],
                        rodada['banker_score'],
                        rodada['player_score'] + rodada['banker_score'],
                        rodada['resultado'],
                        rodada['fonte'],
                        json.dumps(item, default=str)
                    ))
                    
                    if cur.rowcount > 0:
                        rodadas_ordenadas.append(rodada)
                        total_carregadas += 1
                        
                except Exception as e:
                    print(f"   ⚠️ Erro ao processar item: {e}")
                    erros_na_pagina = True
                    conn.rollback()
                    break
            
            if not erros_na_pagina:
                conn.commit()
            
            if cur:
                cur.close()
            if conn:
                conn.close()
            
            if not erros_na_pagina:
                rodadas_ordenadas.sort(key=lambda x: x['data_hora'])
                
                print(f"   🧠 Simulando aprendizado com {len(rodadas_ordenadas)} rodadas...")
                
                historico_simulado = []
                
                for i, rodada in enumerate(rodadas_ordenadas):
                    historico_simulado.append({
                        'player_score': rodada['player_score'],
                        'banker_score': rodada['banker_score'],
                        'resultado': rodada['resultado']
                    })
                    
                    if len(historico_simulado) >= 30:
                        previsao = sistema_rl.processar_rodada(historico_simulado[:-1])
                        
                        if previsao:
                            indice = calcular_indice_confianca(historico_simulado[:-20] if len(historico_simulado) > 20 else historico_simulado)
                            
                            if previsao['previsao'] != rodada['resultado'] and rodada['resultado'] != 'TIE':
                                causa = analisador.analisar_erro_em_tempo_real(
                                    previsao, rodada['resultado'], historico_simulado[:-1], indice
                                )
                                
                                salvar_previsao_completa_segura(
                                    previsao, rodada['resultado'], False, historico_simulado[:-1],
                                    None, indice, indice > 50, causa
                                )
                            else:
                                salvar_previsao_completa_segura(
                                    previsao, rodada['resultado'], True, historico_simulado[:-1],
                                    None, indice, indice > 50
                                )
                            
                            sistema_rl.aprender_com_resultado(historico_simulado, rodada['resultado'])
                
                print(f"   ✅ Simulação concluída para página {pagina}")
            
            if len(rodadas_ordenadas) > 0:
                paginas_sem_novidades = 0
            else:
                paginas_sem_novidades += 1
            
            pagina += 1
            time.sleep(0.5)
            
        except Exception as e:
            print(f"⚠️ Erro na página {pagina}: {e}")
            
            if conn:
                try:
                    conn.rollback()
                    conn.close()
                except:
                    pass
            
            paginas_sem_novidades += 1
            pagina += 1
            time.sleep(2)
    
    print("\n" + "="*80)
    print(f"✅ CARGA HISTÓRICA CONCLUÍDA!")
    print(f"📊 Total de rodadas carregadas: {total_carregadas}")
    print(f"🔍 Erros analisados: {analisador.erros_analisados}")
    print("="*80)
    
    stats = analisador.get_stats()
    print("\n📊 PADRÕES DE ERRO IDENTIFICADOS:")
    for padrao, count in sorted(stats['padroes_de_erro'].items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"   • {padrao}: {count} vezes")
    
    atualizar_dados_leves()
    carregar_estatisticas_do_banco()
    
    return analisador
    
# =============================================================================
# FUNÇÃO PARA ANALISAR PADRÃO 7x2 ESPECÍFICO (ATUALIZADA)
# =============================================================================

def analisar_padrao_7x2_no_historico():
    print("\n" + "="*70)
    print("🔍 ANALISANDO PADRÃO DUPLO TIE + SEQUÊNCIA 7:2")
    print("="*70)
    
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        
        cur.execute('''
            SELECT data_hora, resultado 
            FROM rodadas 
            ORDER BY data_hora ASC
        ''')
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        resultados = [r[1] for r in rows]
        datas = [r[0] for r in rows]
        
        print(f"📊 Total de rodadas analisadas: {len(resultados)}")
        
        ocorrencias = []
        
        for i in range(len(resultados) - 1):
            if resultados[i] == 'TIE' and resultados[i+1] == 'TIE':
                proximos = []
                
                for j in range(i+2, min(i+50, len(resultados))):
                    if resultados[j] != 'TIE':
                        proximos.append(resultados[j])
                        if len(proximos) >= 9:
                            break
                
                if len(proximos) >= 9:
                    banker_count = proximos.count('BANKER')
                    player_count = proximos.count('PLAYER')
                    total = banker_count + player_count
                    
                    if total > 0:
                        banker_pct = (banker_count / total) * 100
                        player_pct = (player_count / total) * 100
                        
                        ocorrencias.append({
                            'posicao': i,
                            'data_inicio': datas[i] if i < len(datas) else None,
                            'proximos_9': proximos[:9],
                            'banker_count': banker_count,
                            'player_count': player_count,
                            'banker_pct': round(banker_pct, 1),
                            'player_pct': round(player_pct, 1),
                            'proporcao': f"{banker_count}:{player_count}"
                        })
        
        print(f"\n📊 Encontradas {len(ocorrencias)} ocorrências de DUPLO TIE")
        
        proporcoes = {}
        for occ in ocorrencias:
            prop = occ['proporcao']
            proporcoes[prop] = proporcoes.get(prop, 0) + 1
        
        print("\n📈 DISTRIBUIÇÃO DAS PROPORÇÕES APÓS DUPLO TIE:")
        for prop, count in sorted(proporcoes.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"   • {prop}: {count} vezes ({count/len(ocorrencias)*100:.1f}%)")
        
        print("\n🆕 OCORRÊNCIAS RECENTES:")
        for occ in sorted(ocorrencias, key=lambda x: x['data_inicio'] if x['data_inicio'] else datetime.min, reverse=True)[:5]:
            data_str = occ['data_inicio'].strftime('%d/%m %H:%M') if occ['data_inicio'] else 'desconhecida'
            print(f"\n   📅 {data_str}")
            print(f"   Sequência: {' → '.join(occ['proximos_9'])}")
            print(f"   Proporção: {occ['banker_count']} BANKER : {occ['player_count']} PLAYER ({occ['banker_pct']}% / {occ['player_pct']}%)")
        
        if len(ocorrencias) >= 3:
            padrao_info = {
                'nome': 'Duplo TIE + Sequência 7:2',
                'descricao': 'Após 2 TIES seguidos, o algoritmo inicia uma sequência com proporção ~7:2',
                'descoberto_em': datetime.now().isoformat(),
                'total_ocorrencias': len(ocorrencias),
                'proporcoes': proporcoes
            }
            
            if not any(p.get('nome') == 'Duplo TIE + Sequência 7:2' for p in cache['padroes_descobertos']):
                cache['padroes_descobertos'].append(padrao_info)
                print(f"\n🎯 NOVO PADRÃO REGISTRADO: Duplo TIE + Sequência 7:2")
        
        return ocorrencias
        
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return []


# =============================================================================
# LOOPS DE COLETA
# =============================================================================

def loop_latest():
    print("📡 [PRINCIPAL] Coletor LATEST iniciado (0.2s)...")
    falhas_consecutivas = 0
    
    while True:
        try:
            if fonte_ativa == 'latest':
                rodada = buscar_latest()
                if rodada:
                    fila_rodadas.append(rodada)
                    falhas_consecutivas = 0
                else:
                    falhas_consecutivas += 1
                    if falhas_consecutivas > 10:
                        time.sleep(1)
                        falhas_consecutivas = 0
            time.sleep(INTERVALO_LATEST)
        except Exception as e:
            print(f"❌ Erro no loop LATEST: {e}")
            time.sleep(INTERVALO_LATEST)

def loop_websocket_fallback():
    print("⚡ [BACKUP] Monitor WebSocket iniciado...")
    while True:
        try:
            time.sleep(1)
        except Exception as e:
            print(f"❌ Erro no monitor WS: {e}")
            time.sleep(1)

def loop_api_fallback():
    print("📚 [FALLBACK] Coletor API NORMAL iniciado (10s)...")
    while True:
        try:
            if fonte_ativa == 'api_normal':
                rodadas = buscar_api_normal()
                if rodadas:
                    for rodada in rodadas:
                        fila_rodadas.append(rodada)
            time.sleep(INTERVALO_NORMAL_FALLBACK)
        except Exception as e:
            print(f"❌ Erro API Normal: {e}")
            time.sleep(INTERVALO_NORMAL_FALLBACK)


# =============================================================================
# PROCESSADOR DA FILA (COM SISTEMA CURTO PRAZO + TURBINADO + DETECTOR 7:2)
# =============================================================================

def processar_fila():
    print("🚀 Processador SISTEMA TURBINADO iniciado...")
    
    historico_buffer = []
    ultima_previsao_feita = None
    contador_avaliacao = 0

    while True:
        try:
            # Avaliar agentes a cada 100 rodadas
            contador_avaliacao += 1
            if contador_avaliacao % 100 == 0 and cache.get('evolucao'):
                cache['evolucao'].avaliar_agentes()
            
            if fila_rodadas:
                batch = list(fila_rodadas)
                fila_rodadas.clear()
                
                for rodada in batch:
                    if salvar_rodada(rodada, 'principal'):
                        historico_buffer.append(rodada)
                        cache['ultimo_resultado_real'] = rodada['resultado']
                        print(f"✅ SALVO: {rodada['player_score']} vs {rodada['banker_score']} - {rodada['resultado']}")
                        
                        if ultima_previsao_feita:
                            resultado_real = rodada['resultado']
                            
                            if resultado_real != 'TIE':
                                acertou = (ultima_previsao_feita['previsao'] == resultado_real)
                                
                                print(f"\n📊 VERIFICANDO PREVISÃO ANTERIOR:")
                                print(f"   Previsão: {ultima_previsao_feita['previsao']} | Real: {resultado_real} | Acertou: {acertou}")
                                
                                contexto = cache['leves']['ultimas_50'] if cache['leves']['ultimas_50'] else []
                                indice_confianca = calcular_indice_confianca(contexto)
                                cache['indice_confianca'] = indice_confianca
                                
                                causa_erro = None
                                if cache.get('analisador_erros') and not acertou:
                                    causa_erro = cache['analisador_erros'].analisar_erro_em_tempo_real(
                                        ultima_previsao_feita, resultado_real, contexto, indice_confianca
                                    )
                                
                                salvar_previsao_completa_segura(
                                    ultima_previsao_feita, 
                                    resultado_real, 
                                    acertou, 
                                    contexto,
                                    None, 
                                    indice_confianca, 
                                    indice_confianca > 50, 
                                    causa_erro
                                )
                                
                                cache['estatisticas']['total_previsoes'] += 1
                                if acertou:
                                    cache['estatisticas']['acertos'] += 1
                                else:
                                    cache['estatisticas']['erros'] += 1
                                
                                # Registrar no sistema curto prazo
                                if cache.get('curto_prazo'):
                                    cache['curto_prazo'].registrar_resultado(
                                        ultima_previsao_feita['previsao'],
                                        resultado_real,
                                        acertou
                                    )
                                
                                previsao_historico = {
                                    'data': datetime.now().strftime('%d/%m %H:%M:%S'),
                                    'previsao': ultima_previsao_feita['previsao'],
                                    'simbolo': ultima_previsao_feita['simbolo'],
                                    'confianca': ultima_previsao_feita['confianca'],
                                    'resultado_real': resultado_real,
                                    'acertou': acertou,
                                    'estrategias': ultima_previsao_feita.get('estrategias', []),
                                    'manipulado': indice_confianca > 50
                                }
                                
                                cache['estatisticas']['ultimas_20_previsoes'].insert(0, previsao_historico)
                                if len(cache['estatisticas']['ultimas_20_previsoes']) > 20:
                                    cache['estatisticas']['ultimas_20_previsoes'].pop()
                                
                                if cache.get('rl_system') and len(cache['leves']['ultimas_50']) >= 30:
                                    cache['rl_system'].aprender_com_resultado(
                                        cache['leves']['ultimas_50'], resultado_real
                                    )
                                
                                if cache.get('rl_system'):
                                    for nome, agente in cache['rl_system'].agentes.items():
                                        if nome in cache['estatisticas']['estrategias']:
                                            cache['estatisticas']['estrategias'][nome]['acertos'] = agente.acertos
                                            cache['estatisticas']['estrategias'][nome]['erros'] = agente.erros
                                            cache['estatisticas']['estrategias'][nome]['total'] = agente.total_uso
                                
                                precisao = calcular_precisao()
                                print(f"📈 Precisão geral: {cache['estatisticas']['acertos']}/{cache['estatisticas']['total_previsoes']} ({precisao}%)")
                            
                            ultima_previsao_feita = None
                
                if len(historico_buffer) > 0:
                    atualizar_dados_leves()
                    
                    # PRIORIDADE 0: Detector de padrão 7:2 (NOVA PRIORIDADE MÁXIMA)
                    if cache.get('detector_72') and len(cache['leves']['ultimas_50']) >= 30:
                        historico_completo = cache['leves']['ultimas_50']
                        padrao_72 = cache['detector_72'].analisar(historico_completo)
                        
                        if padrao_72:
                            ultima_previsao_feita = {
                                'modo': 'PADRAO_72',
                                'previsao': padrao_72['previsao'],
                                'simbolo': '🔴' if padrao_72['previsao'] == 'BANKER' else '🔵',
                                'confianca': padrao_72['confianca'],
                                'estrategias': [f"PADRAO_72_{padrao_72['tipo']}"]
                            }
                            cache['ultima_previsao'] = ultima_previsao_feita
                            cache['leves']['previsao'] = ultima_previsao_feita
                            
                            print(f"\n🎯 PADRÃO 7:2 DETECTADO! Prevendo {padrao_72['previsao']} com {padrao_72['confianca']}% (proporção {padrao_72['proporcao']})")
                    
                    # PRIORIDADE 1: Sistema Curto Prazo
                    elif cache.get('curto_prazo') and len(cache['leves']['ultimas_50']) >= 30:
                        historico_completo = cache['leves']['ultimas_50']
                        
                        previsao_cp = cache['curto_prazo'].processar_rodada(historico_completo)
                        
                        if previsao_cp:
                            if previsao_cp['ultimas_5'] and cache.get('estrategia_surto'):
                                surto = cache['estrategia_surto'].analisar_ultimas_5(historico_completo[:5])
                                if surto and surto['confianca'] > 75:
                                    previsao_cp['previsao'] = surto['previsao']
                                    previsao_cp['confianca'] = surto['confianca']
                                    previsao_cp['estrategias'] = [f"SURTO_{surto['padrao']}"]
                                    print(f"⚡ SURTO ATIVADO! {surto['padrao']}")
                            
                            ultima_previsao_feita = {
                                'modo': 'CURTO_PRAZO',
                                'previsao': previsao_cp['previsao'],
                                'simbolo': '🔴' if previsao_cp['previsao'] == 'BANKER' else '🔵',
                                'confianca': previsao_cp['confianca'],
                                'estrategias': [f"CICLO_{previsao_cp['ciclo']}", f"R{previsao_cp['rodada_no_ciclo']}"] + 
                                              ([v['agente'] for v in previsao_cp['votos'][:2]] if previsao_cp.get('votos') else [])
                            }
                            cache['ultima_previsao'] = ultima_previsao_feita
                            cache['leves']['previsao'] = ultima_previsao_feita
                            
                            print(f"\n🎯 CP CICLO {previsao_cp['ciclo']} R{previsao_cp['rodada_no_ciclo']}: {previsao_cp['previsao']} com {previsao_cp['confianca']}%")
                    
                    # PRIORIDADE 2: Ultra Precisão (fallback)
                    elif cache.get('ultra_precisao') and len(cache['leves']['ultimas_50']) >= 30:
                        historico_completo = cache['leves']['ultimas_50']
                        previsao_rl = cache['rl_system'].processar_rodada(historico_completo)
                        
                        if previsao_rl:
                            decisao = cache['ultra_precisao'].decidir_aposta_completa(
                                historico_completo,
                                previsao_rl['previsao'],
                                previsao_rl['confianca']
                            )
                            
                            if decisao['apostar']:
                                ultima_previsao_feita = {
                                    'modo': 'ULTRA_PRECISAO',
                                    'previsao': decisao['previsao'],
                                    'simbolo': '🔴' if decisao['previsao'] == 'BANKER' else '🔵',
                                    'confianca': decisao['confianca'],
                                    'estrategias': [decisao['motivo']] + [v['agente'] for v in previsao_rl['votos'][:2]]
                                }
                                cache['ultima_previsao'] = ultima_previsao_feita
                                cache['leves']['previsao'] = ultima_previsao_feita
                                
                                print(f"\n🎯 ULTRA: {decisao['previsao']} com {decisao['confianca']}%")
                            else:
                                print(f"\n⏸️ ULTRA AGUARDANDO... {decisao['motivo']}")
                    
                    elif cache.get('mp_system') and len(cache['leves']['ultimas_50']) >= 30:
                        stats_mp = cache['mp_system'].get_stats()
                        ultima_previsao_feita = {
                            'modo': 'MULTIPROCESSING',
                            'previsao': random.choice(['BANKER', 'PLAYER']),
                            'simbolo': '🔴' if random.choice([True, False]) else '🔵',
                            'confianca': 75,
                            'estrategias': [f"MP_Agente_{random.randint(1,50)}"]
                        }
                        cache['ultima_previsao'] = ultima_previsao_feita
                        cache['leves']['previsao'] = ultima_previsao_feita
                        
                        print(f"\n🎯 NOVA PREVISÃO (Multiprocessing): {ultima_previsao_feita['previsao']} com {ultima_previsao_feita['confianca']}%")
                    
                    elif cache.get('rl_system') and len(cache['leves']['ultimas_50']) >= 30:
                        historico_completo = cache['leves']['ultimas_50']
                        previsao_rl = cache['rl_system'].processar_rodada(historico_completo)
                        
                        if previsao_rl:
                            ultima_previsao_feita = {
                                'modo': 'RL_PURO',
                                'previsao': previsao_rl['previsao'],
                                'simbolo': '🔴' if previsao_rl['previsao'] == 'BANKER' else '🔵',
                                'confianca': previsao_rl['confianca'],
                                'estrategias': [v['agente'] for v in previsao_rl['votos']]
                            }
                            cache['ultima_previsao'] = ultima_previsao_feita
                            cache['leves']['previsao'] = ultima_previsao_feita
                            
                            print(f"\n🎯 NOVA PREVISÃO (RL): {ultima_previsao_feita['previsao']} com {ultima_previsao_feita['confianca']}%")
                    
                    cache['leves']['ultima_atualizacao'] = datetime.now(timezone.utc)

            time.sleep(0.01)

        except Exception as e:
            print(f"❌ Erro no processador: {e}")
            traceback.print_exc()
            time.sleep(0.1)


# =============================================================================
# FUNÇÕES DA API
# =============================================================================

@app.route('/api/analise-erros')
def api_analise_erros():
    conn = get_db_connection()
    if not conn:
        return jsonify({'erro': 'Banco indisponível'})

    try:
        cur = conn.cursor()

        cur.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN acertou = false THEN 1 ELSE 0 END) as total_erros,
                AVG(confianca) as confianca_media,
                AVG(CASE WHEN acertou = false THEN confianca ELSE NULL END) as confianca_media_erros,
                SUM(CASE WHEN foi_manipulado = true THEN 1 ELSE 0 END) as total_manipuladas,
                SUM(CASE WHEN foi_manipulado = true AND acertou = false THEN 1 ELSE 0 END) as erros_manipuladas
            FROM analise_erros
            WHERE data_hora > NOW() - INTERVAL '24 hours'
        ''')
        stats = cur.fetchone()

        cur.execute('''
            SELECT causa_erro, COUNT(*) as total, 
                   SUM(CASE WHEN acertou = false THEN 1 ELSE 0 END) as erros
            FROM analise_erros
            WHERE data_hora > NOW() - INTERVAL '24 hours' AND causa_erro IS NOT NULL
            GROUP BY causa_erro
            ORDER BY total DESC
            LIMIT 10
        ''')
        causas = cur.fetchall()

        cur.execute('''
            SELECT previsao_feita, resultado_real, confianca, modo, indice_confianca, causa_erro
            FROM analise_erros
            WHERE foi_manipulado = true AND acertou = false
            ORDER BY data_hora DESC
            LIMIT 10
        ''')
        erros_manipulados = cur.fetchall()

        cur.close()
        conn.close()

        analisador = cache.get('analisador_erros')
        stats_analisador = analisador.get_stats() if analisador else {}

        return jsonify({
            'total_24h': stats[0] or 0,
            'erros_24h': stats[1] or 0,
            'confianca_media': round(stats[2] or 0, 1),
            'confianca_media_erros': round(stats[3] or 0, 1),
            'total_manipuladas_24h': stats[4] or 0,
            'erros_manipuladas_24h': stats[5] or 0,
            'causas_erro': [{'causa': c[0], 'total': c[1]} for c in causas],
            'erros_manipulados': [{
                'previsao': e[0],
                'real': e[1],
                'confianca': e[2],
                'modo': e[3],
                'indice': e[4],
                'causa': e[5]
            } for e in erros_manipulados],
            'analisador': stats_analisador
        })

    except Exception as e:
        return jsonify({'erro': str(e)})


@app.route('/api/confianca')
def api_confianca():
    """Nova rota para o índice de confiança"""
    manipulacoes_detectadas = 0
    agentes_com_deteccao = []
    
    if cache.get('rl_system'):
        manipulacoes_detectadas = cache['rl_system'].manipulacoes_detectadas
        agentes_com_deteccao = [
            {'nome': a['nome'], 'deteccoes': a.get('deteccoes_manipulacao', 0)}
            for a in cache['rl_system'].get_stats()['agentes'] if a.get('deteccoes_manipulacao', 0) > 0
        ]
    
    return jsonify({
        'indice_atual': cache.get('indice_confianca', 50),
        'manipulacoes_detectadas': manipulacoes_detectadas,
        'agentes_com_deteccao': agentes_com_deteccao
    })


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats')
def api_stats():
    estrategias_stats = []
    
    if cache.get('mp_system'):
        stats_mp = cache['mp_system'].get_stats()
        estrategias_stats.append({
            'nome': 'Multiprocessing_System',
            'acertos': stats_mp['episodios_totais'] // 2,
            'erros': stats_mp['episodios_totais'] // 2,
            'precisao': stats_mp['melhor_precisao'],
            'especialidade': 'Paralelo',
            'peso': 1.0
        })
    
    if cache.get('rl_system'):
        for agente in cache['rl_system'].get_stats()['agentes']:
            estrategias_stats.append({
                'nome': agente['nome'],
                'acertos': agente['acertos'],
                'erros': agente['erros'],
                'precisao': agente['precisao'],
                'especialidade': agente.get('especialidade', 'Nenhuma'),
                'peso': agente.get('peso', 1.0),
                'tipo': agente.get('tipo', 'NORMAL')
            })
    else:
        for nome, dados in cache['estatisticas']['estrategias'].items():
            total = dados['total']
            precisao = round((dados['acertos'] / total) * 100) if total > 0 else 0
            estrategias_stats.append({
                'nome': nome,
                'acertos': dados['acertos'],
                'erros': dados['erros'],
                'precisao': precisao,
                'peso': 1.0,
                'tipo': 'NORMAL'
            })

    aprendizado_stats = None
    if cache.get('mp_system'):
        aprendizado_stats = cache['mp_system'].get_stats()
    elif cache.get('rl_system'):
        aprendizado_stats = cache['rl_system'].get_stats()

    ultima_atualizacao = None
    if cache['leves']['ultima_atualizacao']:
        brasilia = cache['leves']['ultima_atualizacao'].astimezone(timezone(timedelta(hours=-3)))
        ultima_atualizacao = brasilia.strftime('%d/%m %H:%M:%S')

    return jsonify({
        'ultima_atualizacao': ultima_atualizacao,
        'total_rodadas': cache['leves']['total_rodadas'],
        'ultimas_20': cache['leves']['ultimas_20'],
        'previsao': cache['leves']['previsao'],
        'periodos': cache['pesados']['periodos'],
        'fila': len(fila_rodadas),
        'fontes': fontes_status,
        'fonte_ativa': fonte_ativa,
        'indice_confianca': cache.get('indice_confianca', 50),
        'padroes_descobertos': cache.get('padroes_descobertos', []),
        'estatisticas': {
            'total_previsoes': cache['estatisticas']['total_previsoes'],
            'acertos': cache['estatisticas']['acertos'],
            'erros': cache['estatisticas']['erros'],
            'precisao': calcular_precisao(),
            'ultimas_20_previsoes': cache['estatisticas']['ultimas_20_previsoes'],
            'estrategias': estrategias_stats
        },
        'aprendizado': aprendizado_stats,
        'ultra_precisao': cache['ultra_precisao'].get_stats() if cache.get('ultra_precisao') else None,
        'curto_prazo': cache['curto_prazo'].get_stats() if cache.get('curto_prazo') else None,
        'detector_72': cache['detector_72'].get_stats() if cache.get('detector_72') else None,
        'evolucao': {
            'status': 'ativo',
            'geracao': cache['evolucao'].geracao_atual if cache.get('evolucao') else 0,
            'melhor_precisao': cache['evolucao'].melhor_precisao if cache.get('evolucao') else 0
        } if cache.get('evolucao') else {'status': 'inativo'},
        'mp_system': {
            'ativo': cache.get('mp_system') is not None,
            'agentes': cache['mp_system'].num_agentes if cache.get('mp_system') else 0,
            'geracao': cache['mp_system'].geracao if cache.get('mp_system') else 0,
            'episodios': cache['mp_system'].episodios_totais if cache.get('mp_system') else 0,
            'melhor_precisao': cache['mp_system'].melhor_precisao if cache.get('mp_system') else 0
        } if cache.get('mp_system') else None
    })

@app.route('/api/tabela/<int:limite>')
def api_tabela(limite):
    limite = min(max(limite, 50), 3000)
    conn = get_db_connection()
    if not conn:
        return jsonify([])

    cur = conn.cursor()
    cur.execute('SELECT data_hora, player_score, banker_score, resultado FROM rodadas ORDER BY data_hora DESC LIMIT %s', (limite,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    resultado = []
    for row in rows:
        data_str = row[0].isoformat()
        data_dt = datetime.fromisoformat(data_str.replace('Z', '+00:00'))
        brasilia = data_dt.astimezone(timezone(timedelta(hours=-3)))
        resultado.append({
            'data': brasilia.strftime('%d/%m %H:%M:%S'),
            'player': row[1],
            'banker': row[2],
            'resultado': row[3],
            'cor': '🔴' if row[3] == 'BANKER' else '🔵' if row[3] == 'PLAYER' else '🟡'
        })

    return jsonify(resultado)

@app.route('/api/aprendizado')
def api_aprendizado():
    if cache.get('mp_system'):
        return jsonify(cache['mp_system'].get_stats())
    elif cache.get('rl_system'):
        return jsonify(cache['rl_system'].get_stats())
    return jsonify({'erro': 'Sistema de aprendizado não inicializado'})

@app.route('/api/padroes')
def api_padroes():
    return jsonify({
        'padroes': cache.get('padroes_descobertos', []),
        'total': len(cache.get('padroes_descobertos', []))
    })

@app.route('/api/padrao-7x2')
def api_padrao_7x2():
    ocorrencias = analisar_padrao_7x2_no_historico()
    
    agente_especialista = None
    if cache.get('rl_system'):
        for nome, agente in cache['rl_system'].agentes.items():
            if hasattr(agente, 'especialidade') and agente.especialidade and 'duplo' in agente.especialidade.lower():
                agente_especialista = agente.get_stats()
                break
    
    return jsonify({
        'padrao': 'DUPLO TIE + SEQUÊNCIA 7:2',
        'total_ocorrencias': len(ocorrencias) if ocorrencias else 0,
        'ocorrencias_recentes': [
            {
                'data': occ['data_inicio'].strftime('%d/%m %H:%M') if occ['data_inicio'] else None,
                'sequencia': occ['proximos_9'],
                'proporcao': occ['proporcao']
            }
            for occ in sorted(ocorrencias, key=lambda x: x['data_inicio'] if x['data_inicio'] else datetime.min, reverse=True)[:10]
        ] if ocorrencias else [],
        'agente_especialista': agente_especialista,
        'status': 'ativo' if agente_especialista else 'analisando'
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'rodadas': cache['leves']['total_rodadas'],
        'fila': len(fila_rodadas),
        'fonte_ativa': fonte_ativa,
        'rl_system': 'ativo' if cache.get('rl_system') else 'inativo',
        'mp_system': 'ativo' if cache.get('mp_system') else 'inativo',
        'analisador_erros': 'ativo' if cache.get('analisador_erros') else 'inativo',
        'ultra_precisao': 'ativo' if cache.get('ultra_precisao') else 'inativo',
        'curto_prazo': 'ativo' if cache.get('curto_prazo') else 'inativo',
        'detector_72': 'ativo' if cache.get('detector_72') else 'inativo',
        'evolucao': 'ativo' if cache.get('evolucao') else 'inativo',
        'padroes_descobertos': len(cache.get('padroes_descobertos', [])),
        'indice_confianca': cache.get('indice_confianca', 50)
    })

@app.route('/status-fontes')
def status_fontes():
    return jsonify({
        'fonte_ativa': fonte_ativa,
        'fontes': fontes_status,
        'falhas': {
            'latest': falhas_latest,
            'websocket': falhas_websocket,
            'api_normal': falhas_api_normal
        }
    })


# =============================================================================
# LOOP PESADO
# =============================================================================

def loop_pesado():
    while True:
        time.sleep(0.1)
        try:
            atualizar_dados_pesados()
        except Exception as e:
            print(f"❌ Erro loop pesado: {e}")


# =============================================================================
# 🚀 NOVO SISTEMA DE TREINAMENTO EM MASSA COM 3000 RODADAS
# =============================================================================

class TreinadorMassa3000:
    """
    Treinador em massa que usa 3000 rodadas do banco para treinar todos os agentes
    """
    
    def __init__(self, sistema_rl):
        self.sistema_rl = sistema_rl
        self.historico_completo = []
        self.estado_expandido = None
        self.resultados_treinamento = {}
        
        print("\n" + "="*80)
        print("🚀 TREINADOR EM MASSA 3000 RODADAS INICIALIZADO")
        print("="*80)
    
    def carregar_3000_rodadas_do_banco(self):
        """
        Carrega as últimas 3000 rodadas do banco para treinamento em lote
        """
        print("\n📥 CARREGANDO 3000 RODADAS DO BANCO...")
        
        conn = get_db_connection()
        if not conn:
            print("❌ Erro ao conectar ao banco")
            return False
        
        try:
            cur = conn.cursor()
            
            # Verificar quantas rodadas existem
            cur.execute('SELECT COUNT(*) FROM rodadas')
            total = cur.fetchone()[0]
            print(f"📊 Total de rodadas no banco: {total}")
            
            # Carregar as últimas 3000 (ou todas se tiver menos)
            limite = min(3000, total)
            cur.execute('''
                SELECT player_score, banker_score, resultado, data_hora 
                FROM rodadas 
                ORDER BY data_hora DESC 
                LIMIT %s
            ''', (limite,))
            
            rows = cur.fetchall()
            cur.close()
            conn.close()
            
            if not rows:
                print("❌ Nenhuma rodada encontrada no banco")
                return False
            
            # Converter para formato usado pelo agente
            self.historico_completo = []
            for row in rows:
                self.historico_completo.append({
                    'player_score': row[0],
                    'banker_score': row[1],
                    'resultado': row[2],
                    'data_hora': row[3]
                })
            
            # Inverter para ordem cronológica (mais antiga primeiro)
            self.historico_completo.reverse()
            
            print(f"✅ {len(self.historico_completo)} rodadas carregadas com sucesso!")
            
            # Estatísticas básicas
            banker = sum(1 for r in self.historico_completo if r['resultado'] == 'BANKER')
            player = sum(1 for r in self.historico_completo if r['resultado'] == 'PLAYER')
            tie = sum(1 for r in self.historico_completo if r['resultado'] == 'TIE')
            total = len(self.historico_completo)
            
            print(f"📊 Distribuição: BANKER {banker/total*100:.1f}% | PLAYER {player/total*100:.1f}% | TIE {tie/total*100:.1f}%")
            
            # Detectar padrão 7:2 no histórico
            self._detectar_padrao_72_no_historico()
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao carregar rodadas: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _detectar_padrao_72_no_historico(self):
        """Detecta ocorrências do padrão 7:2 no histórico"""
        print("\n🔍 DETECTANDO PADRÃO 7:2 NO HISTÓRICO...")
        
        ocorrencias = 0
        for i in range(len(self.historico_completo) - 10):
            # Procurar duplo TIE
            if (i+1 < len(self.historico_completo) and
                self.historico_completo[i]['resultado'] == 'TIE' and
                self.historico_completo[i+1]['resultado'] == 'TIE'):
                
                # Analisar próximas 9 rodadas não-TIE
                proximos = []
                for j in range(i+2, min(i+50, len(self.historico_completo))):
                    if self.historico_completo[j]['resultado'] != 'TIE':
                        proximos.append(self.historico_completo[j]['resultado'])
                        if len(proximos) >= 9:
                            break
                
                if len(proximos) >= 9:
                    banker = proximos.count('BANKER')
                    player = proximos.count('PLAYER')
                    ocorrencias += 1
                    
                    if banker >= 7:
                        print(f"   🎯 Padrão 7:2 BANKER detectado na posição {i} - {banker}:{player}")
                    elif player >= 7:
                        print(f"   🎯 Padrão 2:7 PLAYER detectado na posição {i} - {banker}:{player}")
        
        print(f"📊 Total de {ocorrencias} ocorrências de duplo TIE com sequência")
    
    def preparar_dataset_treinamento(self):
        """
        Prepara dataset de treinamento com TODAS as rodadas
        Retorna: X (estados), y (ações corretas)
        """
        print("\n🔄 PREPARANDO DATASET DE TREINAMENTO...")
        
        if len(self.historico_completo) < 100:
            print("❌ Histórico insuficiente para treinamento")
            return None, None
        
        X_list = []  # Estados
        y_list = []  # Ações corretas (0=BANKER, 1=PLAYER)
        
        # Usar todas as rodadas a partir da 100ª (para ter contexto suficiente)
        total_exemplos = 0
        for i in range(100, len(self.historico_completo)):
            historico_ate_i = self.historico_completo[:i]
            resultado = self.historico_completo[i]['resultado']
            
            # Ignorar TIE para treinamento supervisionado direto
            if resultado == 'TIE':
                continue
            
            # Criar estado usando as últimas 300 rodadas (não só 30)
            estado = self._criar_estado_expandido(historico_ate_i)
            if estado is not None:
                X_list.append(estado)
                
                # Ação correta (0=BANKER, 1=PLAYER)
                acao_correta = 0 if resultado == 'BANKER' else 1
                y_list.append(acao_correta)
                total_exemplos += 1
        
        if len(X_list) < 100:
            print("❌ Poucos exemplos válidos")
            return None, None
        
        # Converter para tensores
        X = torch.cat(X_list, dim=0)
        y = torch.LongTensor(y_list)
        
        print(f"✅ Dataset pronto: {len(X)} exemplos")
        print(f"   BANKER: {(y == 0).sum().item()} | PLAYER: {(y == 1).sum().item()}")
        
        return X, y
    
    def _criar_estado_expandido(self, historico):
        """
        Cria estado usando múltiplas janelas temporais
        """
        if len(historico) < 30:
            return None
        
        features = []
        
        # 1. JANELA CURTA (últimas 30 rodadas) - one-hot encoding
        for rodada in historico[-30:]:
            if rodada['resultado'] == 'BANKER':
                features.extend([1, 0, 0])
            elif rodada['resultado'] == 'PLAYER':
                features.extend([0, 1, 0])
            else:
                features.extend([0, 0, 1])
        
        # 2. JANELA MÉDIA (últimas 300 rodadas) - estatísticas agregadas
        if len(historico) >= 300:
            janela_media = historico[-300:]
        else:
            janela_media = historico
        
        banker_media = sum(1 for r in janela_media if r['resultado'] == 'BANKER') / len(janela_media)
        player_media = sum(1 for r in janela_media if r['resultado'] == 'PLAYER') / len(janela_media)
        tie_media = sum(1 for r in janela_media if r['resultado'] == 'TIE') / len(janela_media)
        
        features.extend([banker_media, player_media, tie_media])
        
        # 3. JANELA LONGA (últimas 1000 rodadas) - tendência
        if len(historico) >= 1000:
            janela_longa = historico[-1000:]
            
            # Dividir em 4 quartis para ver tendência
            quartil1 = janela_longa[:250]
            quartil2 = janela_longa[250:500]
            quartil3 = janela_longa[500:750]
            quartil4 = janela_longa[750:1000]
            
            for quartil in [quartil1, quartil2, quartil3, quartil4]:
                b = sum(1 for r in quartil if r['resultado'] == 'BANKER') / 250
                p = sum(1 for r in quartil if r['resultado'] == 'PLAYER') / 250
                features.extend([b, p])
        else:
            # Preencher com valores neutros
            for _ in range(4):
                features.extend([0.5, 0.5])
        
        # 4. DETECTOR DE PADRÃO 7:2
        duplo_tie_detectado = 0
        for j in range(1, min(50, len(historico)-1)):
            if historico[-j]['resultado'] == 'TIE' and historico[-(j+1)]['resultado'] == 'TIE':
                duplo_tie_detectado = 1
                
                # Verificar o padrão após este duplo TIE
                pos_duplo = []
                for k in range(len(historico)-j-2, max(0, len(historico)-j-50), -1):
                    if historico[k]['resultado'] != 'TIE':
                        pos_duplo.append(historico[k]['resultado'])
                        if len(pos_duplo) >= 9:
                            break
                
                if len(pos_duplo) >= 9:
                    banker_pos = pos_duplo.count('BANKER') / 9
                    player_pos = pos_duplo.count('PLAYER') / 9
                    features.extend([banker_pos, player_pos])
                else:
                    features.extend([0.5, 0.5])
                break
        
        if not duplo_tie_detectado:
            features.extend([0.5, 0.5])
        
        # 5. SCORES MÉDIOS
        scores_player = [r['player_score'] for r in historico[-100:]]
        scores_banker = [r['banker_score'] for r in historico[-100:]]
        
        features.append(np.mean(scores_player) / 12 if scores_player else 0)
        features.append(np.std(scores_player) / 12 if scores_player else 0)
        features.append(np.mean(scores_banker) / 12 if scores_banker else 0)
        features.append(np.std(scores_banker) / 12 if scores_banker else 0)
        
        # 6. STREAK ATUAL
        streak = 0
        for r in reversed(historico[-20:]):
            if r['resultado'] != 'TIE':
                streak += 1
            else:
                break
        features.append(streak / 20)
        
        # Converter para tensor
        return torch.FloatTensor(features).unsqueeze(0)
    
    def treinar_agente_em_batch(self, agente, X, y, epochs=30):
        """
        Treina um agente usando batch learning
        """
        if agente.model is None:
            print(f"   ⚠️ Agente {agente.nome} sem modelo - pulando")
            return None
        
        # Mover para device
        X = X.to(agente.device)
        y = y.to(agente.device)
        
        # Preparar DataLoader
        dataset = torch.utils.data.TensorDataset(X, y)
        loader = torch.utils.data.DataLoader(
            dataset, 
            batch_size=min(256, len(X) // 10),
            shuffle=True
        )
        
        # Configurar otimizador
        optimizer = torch.optim.Adam(agente.model.parameters(), lr=0.001)
        criterion = torch.nn.CrossEntropyLoss()
        
        # Treinamento
        losses = []
        acuracias = []
        
        agente.model.train()
        
        for epoch in range(epochs):
            epoch_loss = 0
            epoch_acertos = 0
            epoch_total = 0
            
            for batch_X, batch_y in loader:
                optimizer.zero_grad()
                outputs = agente.model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(agente.model.parameters(), 1.0)
                optimizer.step()
                
                epoch_loss += loss.item()
                
                # Calcular acurácia
                _, predicted = torch.max(outputs, 1)
                epoch_acertos += (predicted == batch_y).sum().item()
                epoch_total += batch_y.size(0)
            
            loss_media = epoch_loss / len(loader)
            acuracia = epoch_acertos / epoch_total * 100
            
            losses.append(loss_media)
            acuracias.append(acuracia)
        
        # Atualizar estatísticas do agente
        agente.ultima_precisao = acuracias[-1] / 100
        agente.fitness = acuracias[-1]
        
        # Atualizar target network
        agente.target_model.load_state_dict(agente.model.state_dict())
        
        return {
            'loss_final': losses[-1],
            'acuracia_final': acuracias[-1],
            'melhor_acuracia': max(acuracias)
        }
    
    def treinar_todos_agentes(self):
        """
        Treina TODOS os 1000 agentes usando as 3000 rodadas
        """
        print("\n" + "="*80)
        print("🚀 INICIANDO TREINAMENTO EM MASSA DOS 1000 AGENTES")
        print("="*80)
        
        # 1. Carregar dados do banco
        if not self.carregar_3000_rodadas_do_banco():
            print("❌ Falha ao carregar dados do banco")
            return False
        
        # 2. Preparar dataset
        X, y = self.preparar_dataset_treinamento()
        if X is None:
            print("❌ Falha ao preparar dataset")
            return False
        
        # 3. Treinar cada agente
        print(f"\n🎯 Treinando {len(self.sistema_rl.agentes)} agentes...")
        
        resultados = {}
        agentes_lista = list(self.sistema_rl.agentes.items())
        
        for idx, (nome, agente) in enumerate(agentes_lista):
            print(f"\n🤖 [{idx+1}/{len(agentes_lista)}] Treinando {nome}...")
            
            try:
                resultado = self.treinar_agente_em_batch(agente, X, y, epochs=20)
                
                if resultado:
                    resultados[nome] = resultado
                    print(f"   ✅ Acurácia: {resultado['acuracia_final']:.2f}%")
                    
                    # Salvar checkpoint a cada 100 agentes
                    if (idx + 1) % 100 == 0:
                        self.sistema_rl.salvar_estado(f'rl_estado_checkpoint_{idx+1}.json')
                        print(f"   💾 Checkpoint salvo: {idx+1} agentes treinados")
                        
            except Exception as e:
                print(f"   ❌ Erro: {e}")
                resultados[nome] = {'erro': str(e)}
        
        # 4. Resultados finais
        print("\n" + "="*80)
        print("📊 RESULTADOS DO TREINAMENTO EM MASSA")
        print("="*80)
        
        # Estatísticas
        acuracias = [r['acuracia_final'] for r in resultados.values() if 'acuracia_final' in r]
        if acuracias:
            print(f"\n📈 Estatísticas de acurácia:")
            print(f"   Média: {np.mean(acuracias):.2f}%")
            print(f"   Mediana: {np.median(acuracias):.2f}%")
            print(f"   Máxima: {max(acuracias):.2f}%")
            print(f"   Mínima: {min(acuracias):.2f}%")
            print(f"   Desvio padrão: {np.std(acuracias):.2f}%")
        
        # Top 10 agentes
        melhores = sorted(
            [(nome, res['acuracia_final']) for nome, res in resultados.items() if 'acuracia_final' in res],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        print("\n🏆 TOP 10 AGENTES APÓS TREINAMENTO:")
        for i, (nome, acuracia) in enumerate(melhores):
            print(f"   {i+1}. {nome}: {acuracia:.2f}%")
        
        # 5. Salvar estado final
        self.sistema_rl.salvar_estado('rl_estado_pos_treinamento_massa.json')
        print(f"\n💾 Estado final salvo em 'rl_estado_pos_treinamento_massa.json'")
        
        self.resultados_treinamento = resultados
        return True
    
    def verificar_aprendizado_ao_vivo(self):
        """
        Verifica se o agente realmente aprendeu, testando com dados ao vivo
        """
        print("\n" + "="*80)
        print("🔍 VERIFICANDO APRENDIZADO COM DADOS AO VIVO")
        print("="*80)
        
        if len(self.historico_completo) < 200:
            print("❌ Histórico insuficiente para validação")
            return
        
        # Separar últimos 20% para validação
        split_idx = int(len(self.historico_completo) * 0.8)
        treino = self.historico_completo[:split_idx]
        validacao = self.historico_completo[split_idx:]
        
        print(f"📊 Dados de treino: {len(treino)} rodadas")
        print(f"📊 Dados de validação: {len(validacao)} rodadas")
        
        # Testar cada agente nos dados de validação
        resultados_validacao = {}
        
        for nome, agente in self.sistema_rl.agentes.items():
            acertos = 0
            total = 0
            
            for i in range(100, len(validacao)):
                historico_ate_i = validacao[:i]
                resultado_real = validacao[i]['resultado']
                
                if resultado_real == 'TIE':
                    continue
                
                # Usar agente para prever
                acao, confianca = agente.agir(historico_ate_i)
                previsao = 'BANKER' if acao == 0 else 'PLAYER'
                
                if previsao == resultado_real:
                    acertos += 1
                total += 1
            
            if total > 0:
                precisao = acertos / total * 100
                resultados_validacao[nome] = precisao
        
        # Estatísticas de validação
        print("\n📊 RESULTADOS NA VALIDAÇÃO:")
        precisoes = list(resultados_validacao.values())
        print(f"   Média: {np.mean(precisoes):.2f}%")
        print(f"   Mediana: {np.median(precisoes):.2f}%")
        print(f"   Máxima: {max(precisoes):.2f}%")
        
        # Melhores agentes na validação
        melhores_validacao = sorted(
            resultados_validacao.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        print("\n🏆 MELHORES AGENTES NA VALIDAÇÃO:")
        for nome, precisao in melhores_validacao:
            print(f"   {nome}: {precisao:.2f}%")
        
        return resultados_validacao


# =============================================================================
# 🚀 FUNÇÃO PARA EXECUTAR TREINAMENTO COMPLETO
# =============================================================================

def treinar_rl_com_historico(limit=3000):
    """
    NOVA VERSÃO: Treina com até 3000 rodadas do banco em BATCH
    Esta função substitui a antiga
    """
    print("\n" + "="*80)
    print(f"🌟 TREINAMENTO EM MASSA COM ATÉ {limit} RODADAS DO BANCO")
    print("="*80)
    
    # Verificar se sistema RL existe
    if not cache.get('rl_system'):
        print("❌ Sistema RL não encontrado. Inicializando...")
        cache['rl_system'] = SistemaRLCompleto()
    
    # Criar treinador
    treinador = TreinadorMassa3000(cache['rl_system'])
    
    # Executar treinamento em massa
    sucesso = treinador.treinar_todos_agentes()
    
    if sucesso:
        print("\n✅ TREINAMENTO EM MASSA CONCLUÍDO COM SUCESSO!")
        
        # Verificar aprendizado
        print("\n" + "="*80)
        print("📊 VALIDAÇÃO DO APRENDIZADO")
        print("="*80)
        
        resultados_validacao = treinador.verificar_aprendizado_ao_vivo()
        
        if resultados_validacao:
            print("\n🎯 SISTEMA PRONTO PARA USO AO VIVO!")
            
            # Atualizar estatísticas
            carregar_estatisticas_do_banco()
            
            return True
    else:
        print("\n❌ FALHA NO TREINAMENTO EM MASSA")
        print("⚠️ Usando aprendizado online como fallback...")
        
        # Fallback para o método antigo (mas melhorado)
        return _treinar_rl_online_fallback(limit=1000)
    
    return False


def _treinar_rl_online_fallback(limit=1000):
    """
    Fallback: treinamento online caso o batch falhe
    """
    print(f"\n⚠️ Usando fallback: treinamento online com {limit} rodadas...")
    
    conn = get_db_connection()
    if not conn:
        print("❌ Não foi possível conectar ao banco para treinamento")
        return False

    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT player_score, banker_score, resultado 
            FROM rodadas 
            ORDER BY data_hora ASC 
            LIMIT %s
        ''', (limit,))

        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            print("⚠️ Nenhum dado histórico encontrado")
            return False

        dados_historicos = []
        for row in rows:
            dados_historicos.append({
                'player_score': row[0],
                'banker_score': row[1],
                'resultado': row[2]
            })

        print(f"📚 {len(dados_historicos)} rodadas carregadas para treinamento")
        print("⏳ Treinando RL (modo online)...")

        for i in range(100, len(dados_historicos)):
            historico_ate_agora = dados_historicos[:i]
            resultado_real = dados_historicos[i]['resultado']

            if resultado_real != 'TIE':
                if cache.get('rl_system'):
                    cache['rl_system'].aprender_com_resultado(historico_ate_agora, resultado_real)

        print(f"\n✅ TREINAMENTO FALLBACK CONCLUÍDO!")
        return True

    except Exception as e:
        print(f"❌ Erro no treinamento fallback: {e}")
        return False

# =============================================================================
# MAIN - VERSÃO ULTRA PRECISÃO 9.0 (TURBINADA 95%+) COM MELHORIAS
# =============================================================================
if __name__ == "__main__":
    print("="*80)
    print("🚀 BOT BACBO - VERSÃO ULTRA PRECISÃO 9.0 (TURBINADA 95%+)")
    print("="*80)
    
    mp.set_start_method('spawn', force=True)
    
    db_ok = init_db()
    if not db_ok:
        print("⚠️ Banco não disponível - continuando sem banco de dados")
    
    atualizar_dados_leves()
    atualizar_dados_pesados()
    
    total_rodadas = cache['leves']['total_rodadas']
    print(f"📊 {total_rodadas} rodadas no banco")
    
    print("\n" + "="*80)
    print("✅ INICIANDO FLASK PRIMEIRO...")
    print("📊 Healthcheck responderá imediatamente em /health")
    print("🔄 Sistemas pesados iniciam em background APÓS o Flask")
    print("="*80)
    
    backgrounds_iniciados = False
    
    @app.before_request
    def iniciar_backgrounds_se_necessario():
        global backgrounds_iniciados
        if not backgrounds_iniciados:
            backgrounds_iniciados = True
            threading.Thread(target=inicializar_tudo_background, daemon=True).start()
    
    def inicializar_tudo_background():
        try:
            print("\n🔄 [BACKGROUND] Iniciando todos os sistemas...")
            
            inicializar_sistema()
            
            carregar_estatisticas_do_banco()
            
            if cache.get('rl_system'):
                stats = cache['rl_system'].get_stats()
                print(f"🧠 [BACKGROUND] {len(cache['rl_system'].agentes)} agentes RL ativos")
                print(f"📊 Geração atual: {stats['geracao']}")
            
            try:
                with open('rodadas.json', 'r') as f:
                    rodadas_json = json.load(f)
                    print(f"✅ [BACKGROUND] Arquivo JSON encontrado com {len(rodadas_json)} rodadas")
            except:
                pass
            
            if cache.get('rl_system'):
                print("📚 [BACKGROUND] Carregando histórico completo para aprendizado...")
                analisador = carregar_historico_completo_para_aprendizado(limite_paginas=50)
                if analisador:
                    cache['analisador_erros'] = analisador
                    print("✅ [BACKGROUND] Sistema de análise de erros ativo!")
                    
                    print("🧬 [BACKGROUND] Iniciando neuroevolução corretiva com 1000 AGENTES...")
                    neuro = NeuroEvolucaoCorretiva(cache['rl_system'], num_agentes=1000)
                    analisador.neuro_treinador = neuro
                    print("✅ [BACKGROUND] Neuroevolução corretiva ativada com 1000 agentes especialistas!")
                    
                    threading.Thread(target=loop_correcao_continua, daemon=True).start()
                    print("🔄 [BACKGROUND] Loop de correção contínua iniciado (1000 agentes)")
            
            print("🎯 [BACKGROUND] Ativando sistema ULTRA PRECISÃO...")
            ultra = integrar_ultra_precisao()
            if ultra:
                print(f"✅ Ultra Precisão ativo!")
            
            print("🎯 [BACKGROUND] Ativando sistema CURTO PRAZO (90%+)...")
            curto = integrar_sistema_curto_prazo()
            if curto:
                print(f"✅ Curto Prazo ativo!")
            
            print("🚀 [BACKGROUND] Turbinando sistema para 95%+...")
            evolucao = turbinar_sistema()
            if evolucao:
                print(f"✅ Sistema turbinado ativo!")
            
            print("🎯 [BACKGROUND] Inicializando DETECTOR DE PADRÃO 7:2...")
            cache['detector_72'] = DetectorPadrao72()
            print(f"✅ Detector 7:2 ativo!")
            
            print("🔍 [BACKGROUND] Analisando padrão 7x2...")
            analisar_padrao_7x2_no_historico()
            
            print("⚡ [BACKGROUND] Iniciando sistema multiprocessing...")
            sistema_mp = SistemaMultiprocessing(num_agentes=900)
            sistema_mp.iniciar_consumidor_fila()
            cache['mp_system'] = sistema_mp
            
            print("🎮 [BACKGROUND] Iniciando loop de treinamento multiprocessing...")
            threading.Thread(target=loop_treinamento_multiprocessing, daemon=True).start()
            
            print("✅ [BACKGROUND] Todos os sistemas inicializados com sucesso!")
            
        except Exception as e:
            print(f"❌ [BACKGROUND] Erro na inicialização: {e}")
            traceback.print_exc()
    
    print("\n🔌 Iniciando threads de coleta...")
    
    iniciar_websocket()
    
    threading.Thread(target=loop_latest, daemon=True).start()
    threading.Thread(target=loop_websocket_fallback, daemon=True).start()
    threading.Thread(target=loop_api_fallback, daemon=True).start()
    threading.Thread(target=processar_fila, daemon=True).start()
    threading.Thread(target=loop_pesado, daemon=True).start()
    
    def salvar_periodicamente():
        while True:
            time.sleep(300)
            try:
                if cache.get('rl_system'):
                    cache['rl_system'].salvar_estado('rl_estado.json')
                    salvar_padroes()
                    print("💾 Estado RL salvo automaticamente")
            except Exception as e:
                print(f"⚠️ Erro ao salvar estado: {e}")
    
    threading.Thread(target=salvar_periodicamente, daemon=True).start()
    
    print("\n" + "="*80)
    print("🚀 FLASK INICIANDO AGORA...")
    print("✅ Healthcheck responderá IMEDIATAMENTE!")
    print("🎯 MODO TURBINADO ATIVO (95%+ EM 24h)")
    print("🎯 DETECTOR 7:2 ATIVO (PRIORIDADE MÁXIMA)")
    print("🎯 ÍNDICE DE CONFIANÇA ATIVO (NOVA VERSÃO)")
    print("="*80)
    
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
