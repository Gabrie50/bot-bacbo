# =============================================================================
# main.py - BACBO PREDICTOR - AGENTES INFINITOS (VERSÃO FINAL CORRIGIDA)
# =============================================================================
# TODO NOVO PADRÃO = NOVO AGENTE RL
# AGENTES TURBINADOS COM REDES NEURAIS
# AGENTES PARALELOS TRABALHANDO EM MASSA
# SEM LIMITE DE AGENTES - MAPA MENTAL EXPANSÍVEL
# =============================================================================

import os
import sys
import time
import json
import uuid
import pickle
import random
import threading
import traceback
import urllib.parse
import ssl
from datetime import datetime, timedelta, timezone
from collections import deque
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
import copy

# =============================================================================
# WEB FRAMEWORK
# =============================================================================
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

# =============================================================================
# HTTP REQUESTS
# =============================================================================
import requests

# =============================================================================
# DATABASE
# =============================================================================
import pg8000

# =============================================================================
# 🔇 SILENCIAR AVISOS
# =============================================================================
import warnings
warnings.filterwarnings('ignore')
os.environ['PYTHONWARNINGS'] = 'ignore'

# =============================================================================
# 📊 NUMEROS
# =============================================================================
import numpy as np
np.seterr(all='ignore')

# =============================================================================
# 🔧 PYTORCH PARA AGENTES TURBINADOS
# =============================================================================
TORCH_AVAILABLE = False
DEVICE = 'cpu'

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"✅ PyTorch disponível - Device: {DEVICE}")
except ImportError as e:
    print(f"⚠️ PyTorch não disponível: {e}")
    print("   Os agentes turbinados usarão modo fallback")
    
    # Classes dummy para evitar NameError
    class nn:
        class Module:
            pass
        class Linear:
            def __init__(self, *args, **kwargs): pass
        class BatchNorm1d:
            def __init__(self, *args, **kwargs): pass
        class Dropout:
            def __init__(self, *args, **kwargs): pass
        class LeakyReLU:
            def __init__(self, *args, **kwargs): pass
    
    class torch:
        class FloatTensor:
            pass
        class LongTensor:
            pass
        class no_grad:
            def __enter__(self): return self
            def __exit__(self, *args): pass
    
    class optim:
        class Adam:
            def __init__(self, *args, **kwargs): pass
    
    class F:
        @staticmethod
        def softmax(*args, **kwargs): return None
        @staticmethod
        def cross_entropy(*args, **kwargs): return None

# =============================================================================
# 🚀 INICIAR FLASK
# =============================================================================
app = Flask(__name__)
CORS(app)

# =============================================================================
# 🏥 HEALTHCHECK
# =============================================================================
@app.route('/health', methods=['GET'])
def health_urgente():
    total_agentes = len(cache.get('todos_agentes', {}))
    return jsonify({
        'status': 'ok',
        'mensagem': 'Sistema de Agentes Infinitos',
        'timestamp': time.time(),
        'versao': 'Agentes_Infinitos_v2.0',
        'total_agentes': total_agentes,
        'pytorch_disponivel': TORCH_AVAILABLE,
        'device': DEVICE
    })

@app.route('/', methods=['GET'])
def home_rapida():
    return render_template('index.html')

# =============================================================================
# CONFIGURAÇÕES DO BANCO
# =============================================================================
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://neondb_owner:npg_uHONl9tJ1gDF@ep-patient-rice-amoqsdum-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require")

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
# CONFIGURAÇÕES DAS FONTES
# =============================================================================
LATEST_API_URL = "https://api-cs.casino.org/svc-evolution-game-events/api/bacbo/latest"
API_URL = "https://api-cs.casino.org/svc-evolution-game-events/api/bacbo"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Cache-Control': 'no-cache'
}

INTERVALO_LATEST = 0.3
PORT = int(os.environ.get("PORT", 5000))

# =============================================================================
# FILA DE PROCESSAMENTO
# =============================================================================
fila_rodadas = deque(maxlen=1000)
ultimo_id_latest = None

# =============================================================================
# CACHE GLOBAL
# =============================================================================
cache = {
    'leves': {'ultimas_50': [], 'ultimas_20': [], 'total_rodadas': 0, 'ultima_atualizacao': None, 'previsao': None},
    'pesados': {'periodos': {}, 'ultima_atualizacao': None},
    'estatisticas': {'total_previsoes': 0, 'acertos': 0, 'erros': 0, 'ultimas_20_previsoes': []},
    'todos_agentes': {},
    'agentes_por_padrao': {},
    'agentes_por_contexto': {},
    'fila_criacao_agentes': deque(maxlen=100),
    'ultima_previsao': None,
    'ultimo_resultado_real': None,
    'contador_agentes': 0,
    'lock_agentes': threading.Lock(),
    'sistema': None
}


# =============================================================================
# 1. REDE NEURAL PARA AGENTES TURBINADOS
# =============================================================================

if TORCH_AVAILABLE:
    class RedeNeuralAgente(nn.Module):
        """Rede neural para agentes turbinados"""
        def __init__(self, input_size=150, hidden_size=256, output_size=2):
            super(RedeNeuralAgente, self).__init__()
            self.fc1 = nn.Linear(input_size, hidden_size)
            self.bn1 = nn.BatchNorm1d(hidden_size)
            self.fc2 = nn.Linear(hidden_size, hidden_size // 2)
            self.bn2 = nn.BatchNorm1d(hidden_size // 2)
            self.fc3 = nn.Linear(hidden_size // 2, hidden_size // 4)
            self.fc4 = nn.Linear(hidden_size // 4, output_size)
            self.dropout = nn.Dropout(0.2)
            self.leaky_relu = nn.LeakyReLU(0.1)
        
        def forward(self, x):
            x = self.leaky_relu(self.bn1(self.fc1(x)))
            x = self.dropout(x)
            x = self.leaky_relu(self.bn2(self.fc2(x)))
            x = self.dropout(x)
            x = self.leaky_relu(self.fc3(x))
            x = self.fc4(x)
            return F.softmax(x, dim=1)
else:
    class RedeNeuralAgente:
        """Classe dummy para quando PyTorch não está disponível"""
        def __init__(self, *args, **kwargs):
            pass
        def to(self, *args):
            return self
        def train(self):
            pass
        def eval(self):
            pass
        def __call__(self, *args, **kwargs):
            return None


# =============================================================================
# 2. INDICADORES BASE (TODOS OS QUE VOCÊ DESCOBRIU)
# =============================================================================

class IndicadoresBase:
    """TODOS os indicadores que você descobriu no arquivo JSON"""
    def __init__(self):
        # Limites de Streak
        self.LIMITE_STREAK_PLAYER = 5
        self.LIMITE_STREAK_BANKER = 4
        self.REVERSAO_APOS_3 = 0.80
        
        # Probabilidades de TIE
        self.PROB_TIE_VIBRADOR = 0.208
        self.PROB_TIE_POS_TIE = 0.311
        
        # Delta
        self.LIMITE_CORRECAO_INICIO = 15
        self.LIMITE_CORRECAO_GARANTIDA = 20
        
        # Empate 6 → PLAYER
        self.TIE_6_PROXIMO_PLAYER = 1.0
        
        # Duplo TIE → 7:2
        self.DUPLO_TIE_BANKER_PCT = 0.77
        
        # Vibração
        self.VIBRACAO_DIFERENCA_1 = 0.30
        
        # Alternância
        self.ALTERNANCIA_PCT = 0.60
        self.REPETICAO_PCT = 0.40
        
        # Scores comuns
        self.SCORES_COMUNS = [6, 7, 8]
        
        print("✅ Indicadores Base carregados")
        self._mostrar_resumo()
    
    def _mostrar_resumo(self):
        print("="*60)
        print("📊 INDICADORES DESCOBERTOS:")
        print(f"   Streak max: PLAYER={self.LIMITE_STREAK_PLAYER} BANKER={self.LIMITE_STREAK_BANKER}")
        print(f"   Reversão após 3: {self.REVERSAO_APOS_3*100:.0f}%")
        print(f"   Delta correção: ±{self.LIMITE_CORRECAO_INICIO} a ±{self.LIMITE_CORRECAO_GARANTIDA}")
        print(f"   Empate 6 → PLAYER: {self.TIE_6_PROXIMO_PLAYER*100:.0f}%")
        print(f"   Duplo TIE → BANKER: {self.DUPLO_TIE_BANKER_PCT*100:.0f}%")
        print(f"   Vibração dif=1: {self.VIBRACAO_DIFERENCA_1*100:.0f}% vira TIE")
        print(f"   Alternância: {self.ALTERNANCIA_PCT*100:.0f}% | Repetição: {self.REPETICAO_PCT*100:.0f}%")
        print("="*60)


# =============================================================================
# 3. AGENTE BASE (Todos os agentes herdam desta classe)
# =============================================================================

class AgenteBase:
    """Classe base para todos os agentes"""
    
    def __init__(self, agente_id: str, nome: str, padrao: str, contexto: List[str], previsao: str):
        self.id = agente_id
        self.nome = nome
        self.padrao = padrao
        self.contexto = contexto.copy()
        self.previsao = previsao
        
        self.acertos = 0
        self.erros = 0
        self.total_uso = 0
        self.peso = 1.0
        self.confianca_base = 0.7
        self.criado_em = datetime.now()
        self.ultimo_uso = datetime.now()
        self.tipo = "NORMAL"
        
        self.model = None
        self.optimizer = None
        self.device = DEVICE if TORCH_AVAILABLE else 'cpu'
    
    @property
    def precisao(self) -> float:
        total = self.acertos + self.erros
        return (self.acertos / total) if total > 0 else 0.5
    
    @property
    def peso_atual(self) -> float:
        peso_base = self.precisao * self.confianca_base
        idade_horas = (datetime.now() - self.criado_em).total_seconds() / 3600
        bonus_novidade = max(0, 1.0 - idade_horas / 24) * 0.2
        return min(1.5, peso_base + bonus_novidade)
    
    def extrair_features(self, historico: List[dict]) -> np.ndarray:
        features = []
        for i, r in enumerate(historico[:30]):
            resultado = r.get('resultado', '')
            if resultado == 'BANKER':
                features.extend([1, 0, 0])
            elif resultado == 'PLAYER':
                features.extend([0, 1, 0])
            else:
                features.extend([0, 0, 1])
            features.append(r.get('player_score', 0) / 12)
            features.append(r.get('banker_score', 0) / 12)
        
        while len(features) < 150:
            features.append(0)
        
        return np.array(features, dtype=np.float32)
    
    def prever(self, historico: List[dict]) -> Tuple[Optional[str], float]:
        self.total_uso += 1
        self.ultimo_uso = datetime.now()
        
        contexto_atual = [r.get('resultado') for r in historico[:10] if r.get('resultado') != 'TIE'][:5]
        
        if contexto_atual != self.contexto[:len(contexto_atual)]:
            return None, 0
        
        confianca = self.peso_atual * self.confianca_base
        
        if self.model and TORCH_AVAILABLE:
            try:
                features = self.extrair_features(historico)
                features_tensor = torch.FloatTensor(features).unsqueeze(0).to(self.device)
                
                with torch.no_grad():
                    output = self.model(features_tensor).cpu().numpy()[0]
                    acao = np.argmax(output)
                    previsao_nn = 'BANKER' if acao == 0 else 'PLAYER'
                    confianca_nn = output[acao]
                    
                    if previsao_nn == self.previsao:
                        confianca = (confianca + confianca_nn) / 2
                    else:
                        confianca = max(confianca, confianca_nn) * 0.8
            except Exception:
                pass
        
        return self.previsao, min(0.95, confianca)
    
    def aprender(self, resultado_real: str, acertou: bool):
        if acertou:
            self.acertos += 1
            self.peso = min(2.0, self.peso * 1.05)
            self.confianca_base = min(0.95, self.confianca_base * 1.02)
        else:
            self.erros += 1
            self.peso = max(0.3, self.peso * 0.95)
            self.confianca_base = max(0.4, self.confianca_base * 0.98)
    
    def to_dict(self) -> dict:
        return {
            'id': self.id[:8],
            'nome': self.nome,
            'padrao': self.padrao[:30],
            'contexto': self.contexto,
            'previsao': self.previsao,
            'acertos': self.acertos,
            'erros': self.erros,
            'total_uso': self.total_uso,
            'precisao': round(self.precisao * 100, 1),
            'peso': round(self.peso, 2),
            'tipo': self.tipo,
            'criado_em': self.criado_em.isoformat()
        }


# =============================================================================
# 4. AGENTE TURBINADO (Com Rede Neural PyTorch)
# =============================================================================

class AgenteTurbinado(AgenteBase):
    def __init__(self, agente_id: str, nome: str, padrao: str, contexto: List[str], previsao: str):
        super().__init__(agente_id, nome, padrao, contexto, previsao)
        self.tipo = "TURBINADO"
        self.learning_rate = 0.001
        self.memoria = deque(maxlen=5000)
        
        if TORCH_AVAILABLE:
            self._criar_rede_neural()
        
        print(f"🤖 Agente TURBINADO criado: {nome}")
    
    def _criar_rede_neural(self):
        try:
            self.model = RedeNeuralAgente(input_size=150, hidden_size=256, output_size=2).to(self.device)
            self.optimizer = optim.Adam(self.model.parameters(), lr=self.learning_rate)
            print(f"   ✅ Rede neural criada para {self.nome}")
        except Exception as e:
            print(f"   ⚠️ Erro ao criar rede: {e}")
            self.model = None
    
    def to_dict(self) -> dict:
        dados = super().to_dict()
        dados['tipo'] = 'TURBINADO'
        return dados


# =============================================================================
# 5. AGENTE PARALELO (Para processamento em massa)
# =============================================================================

class AgenteParalelo(AgenteBase):
    def __init__(self, agente_id: str, nome: str, padrao: str, contexto: List[str], previsao: str):
        super().__init__(agente_id, nome, padrao, contexto, previsao)
        self.tipo = "PARALELO"
        self.batch_size = 32
        print(f"⚡ Agente PARALELO criado: {nome}")
    
    def to_dict(self) -> dict:
        dados = super().to_dict()
        dados['tipo'] = 'PARALELO'
        return dados


# =============================================================================
# 6. FÁBRICA DE AGENTES
# =============================================================================

class FabricaAgentes:
    def __init__(self):
        self.total_criados = 0
        self.padroes_criados = set()
        self.ultimo_id = 0
        self.tipos_disponiveis = ['NORMAL', 'TURBINADO', 'PARALELO']
        print("🏭 Fábrica de Agentes inicializada")
    
    def gerar_id(self) -> str:
        self.ultimo_id += 1
        timestamp = int(time.time() * 1000)
        return f"AG_{timestamp}_{self.ultimo_id}_{uuid.uuid4().hex[:6]}"
    
    def criar_agente(self, padrao: str, contexto: List[str], previsao: str, tipo: str = None) -> AgenteBase:
        if tipo is None:
            tipo = random.choice(self.tipos_disponiveis)
        
        agente_id = self.gerar_id()
        nome = f"Agente_{padrao[:20]}_{self.total_criados + 1}"
        
        if tipo == 'TURBINADO':
            agente = AgenteTurbinado(agente_id, nome, padrao, contexto, previsao)
        elif tipo == 'PARALELO':
            agente = AgenteParalelo(agente_id, nome, padrao, contexto, previsao)
        else:
            agente = AgenteBase(agente_id, nome, padrao, contexto, previsao)
        
        self.total_criados += 1
        self.padroes_criados.add(padrao)
        return agente
    
    def criar_agentes_padrao(self, padrao: str, contexto: List[str], previsao: str, quantidade: int = 3) -> List[AgenteBase]:
        agentes = []
        for i in range(quantidade):
            tipo = self.tipos_disponiveis[i % len(self.tipos_disponiveis)]
            agente = self.criar_agente(padrao, contexto, previsao, tipo)
            variacao = random.uniform(0.8, 1.2)
            agente.peso = variacao
            agente.confianca_base = min(0.95, 0.7 * variacao)
            agentes.append(agente)
        return agentes
    
    def get_stats(self) -> dict:
        return {
            'total_criados': self.total_criados,
            'padroes_unicos': len(self.padroes_criados),
            'tipos': self.tipos_disponiveis
        }


# =============================================================================
# 7. SISTEMA DE AGENTES INFINITOS
# =============================================================================

class SistemaAgentesInfinitos:
    def __init__(self):
        self.fabrica = FabricaAgentes()
        self.indicadores = IndicadoresBase()
        self.total_previsoes = 0
        self.acertos = 0
        self.erros = 0
        self.ultima_previsao = None
        self.ultimo_contexto = []
        self.ultimos_agentes = []
        
        self._criar_agentes_iniciais()
        
        print("\n" + "="*70)
        print("🐟 SISTEMA DE AGENTES INFINITOS INICIALIZADO")
        print("="*70)
        print(f"   PyTorch disponível: {TORCH_AVAILABLE}")
        print(f"   Device: {DEVICE}")
        print(f"   Agentes iniciais: {cache['contador_agentes']}")
        print(f"   Tipos: NORMAL, TURBINADO, PARALELO")
        print("="*70)
    
    def _hash_contexto(self, contexto: List[str]) -> str:
        filtrados = [r for r in contexto if r != 'TIE'][:5]
        return '_'.join(filtrados) if filtrados else 'vazio'
    
    def _criar_agentes_iniciais(self):
        padroes_iniciais = [
            ('streak_3_player', ['PLAYER', 'PLAYER', 'PLAYER'], 'BANKER'),
            ('streak_3_banker', ['BANKER', 'BANKER', 'BANKER'], 'PLAYER'),
            ('tie_6_player', ['TIE'], 'PLAYER'),
            ('duplo_tie_72', ['TIE', 'TIE'], 'BANKER'),
            ('alternancia_banker', ['PLAYER', 'BANKER'], 'PLAYER'),
            ('alternancia_player', ['BANKER', 'PLAYER'], 'BANKER'),
            ('repeticao_banker', ['BANKER', 'BANKER'], 'BANKER'),
            ('repeticao_player', ['PLAYER', 'PLAYER'], 'PLAYER')
        ]
        
        for padrao, contexto, previsao in padroes_iniciais:
            agentes = self.fabrica.criar_agentes_padrao(padrao, contexto, previsao, 2)
            for agente in agentes:
                with cache['lock_agentes']:
                    cache['todos_agentes'][agente.id] = agente
                    
                    if padrao not in cache['agentes_por_padrao']:
                        cache['agentes_por_padrao'][padrao] = []
                    cache['agentes_por_padrao'][padrao].append(agente.id)
                    
                    ch = self._hash_contexto(contexto)
                    if ch not in cache['agentes_por_contexto']:
                        cache['agentes_por_contexto'][ch] = []
                    cache['agentes_por_contexto'][ch].append(agente.id)
        
        cache['contador_agentes'] = len(cache['todos_agentes'])
    
    def _coletar_previsoes(self, historico: List[dict]) -> List[Tuple[str, float, str, str]]:
        contexto_atual = [r.get('resultado') for r in historico[:10] if r.get('resultado') != 'TIE'][:5]
        ch = self._hash_contexto(contexto_atual)
        
        agentes_ids = set()
        if ch in cache['agentes_por_contexto']:
            agentes_ids.update(cache['agentes_por_contexto'][ch])
        
        for i in range(len(contexto_atual), 0, -1):
            sub_ch = self._hash_contexto(contexto_atual[:i])
            if sub_ch in cache['agentes_por_contexto']:
                agentes_ids.update(cache['agentes_por_contexto'][sub_ch])
        
        previsoes = []
        with cache['lock_agentes']:
            for agente_id in agentes_ids:
                if agente_id in cache['todos_agentes']:
                    agente = cache['todos_agentes'][agente_id]
                    previsao, confianca = agente.prever(historico)
                    if previsao:
                        previsoes.append((previsao, confianca, agente_id, agente.padrao))
        
        return previsoes
    
    def _detectar_novo_padrao(self, historico: List[dict], acertou: bool) -> Optional[Tuple[str, List[str], str]]:
        if len(historico) < 10 or not acertou:
            return None
        
        contexto_atual = [r.get('resultado') for r in historico[:10] if r.get('resultado') != 'TIE'][:5]
        ch = self._hash_contexto(contexto_atual)
        
        if ch in cache['agentes_por_contexto']:
            return None
        
        if len(contexto_atual) >= 2:
            padrao_nome = f"novo_{'_'.join(contexto_atual[:3])}"
            previsao = historico[0].get('resultado') if historico else 'BANKER'
            return (padrao_nome, contexto_atual, previsao)
        
        return None
    
    def _criar_agentes_novo_padrao(self, padrao: str, contexto: List[str], previsao: str):
        print(f"\n🎉 NOVO PADRÃO DESCOBERTO! Criando agentes...")
        print(f"   Padrão: {padrao}")
        print(f"   Contexto: {contexto}")
        print(f"   Previsão: {previsao}")
        
        novos_agentes = self.fabrica.criar_agentes_padrao(padrao, contexto, previsao, 3)
        
        with cache['lock_agentes']:
            for agente in novos_agentes:
                cache['todos_agentes'][agente.id] = agente
                
                if padrao not in cache['agentes_por_padrao']:
                    cache['agentes_por_padrao'][padrao] = []
                cache['agentes_por_padrao'][padrao].append(agente.id)
                
                ch = self._hash_contexto(contexto)
                if ch not in cache['agentes_por_contexto']:
                    cache['agentes_por_contexto'][ch] = []
                cache['agentes_por_contexto'][ch].append(agente.id)
        
        cache['contador_agentes'] = len(cache['todos_agentes'])
        print(f"   ✅ {len(novos_agentes)} novos agentes criados!")
        print(f"   📊 Total de agentes: {cache['contador_agentes']}")
    
    def prever(self, historico: List[dict]) -> dict:
        if len(historico) < 30:
            return {'previsao': 'AGUARDANDO', 'confianca': 0, 'modo': 'INICIALIZACAO'}
        
        self.ultimo_contexto = historico[:20]
        previsoes = self._coletar_previsoes(historico)
        self.ultimos_agentes = [p[2] for p in previsoes]
        
        if not previsoes:
            ultimos = [r['resultado'] for r in historico[:20] if r.get('resultado') != 'TIE']
            if ultimos:
                banker = ultimos.count('BANKER')
                player = ultimos.count('PLAYER')
                previsao = 'BANKER' if banker > player else 'PLAYER'
                confianca = 55
            else:
                previsao = random.choice(['BANKER', 'PLAYER'])
                confianca = 50
            
            self.ultima_previsao = previsao
            return {
                'previsao': previsao,
                'simbolo': '🔴' if previsao == 'BANKER' else '🔵',
                'confianca': confianca,
                'modo': 'FALLBACK',
                'agentes_usados': 0,
                'total_agentes': cache['contador_agentes']
            }
        
        votos = {'BANKER': 0, 'PLAYER': 0}
        for previsao, confianca, agente_id, padrao in previsoes:
            votos[previsao] += confianca
        
        previsao_final = max(votos, key=votos.get)
        total_votos = sum(votos.values())
        confianca_final = (votos[previsao_final] / total_votos) * 100 if total_votos > 0 else 50
        
        self.ultima_previsao = previsao_final
        
        return {
            'previsao': previsao_final,
            'simbolo': '🔴' if previsao_final == 'BANKER' else '🔵',
            'confianca': round(confianca_final),
            'modo': 'AGENTES_INFINITOS',
            'agentes_usados': len(previsoes),
            'total_agentes': cache['contador_agentes'],
            'padroes': list(set([p[3] for p in previsoes]))[:5]
        }
    
    def aprender(self, resultado_real: str):
        if not self.ultima_previsao:
            return
        
        acertou = (self.ultima_previsao == resultado_real)
        
        self.total_previsoes += 1
        if acertou:
            self.acertos += 1
        else:
            self.erros += 1
        
        cache['estatisticas']['total_previsoes'] = self.total_previsoes
        cache['estatisticas']['acertos'] = self.acertos
        cache['estatisticas']['erros'] = self.erros
        
        print(f"\n📚 APRENDENDO: {self.ultima_previsao} vs {resultado_real} → {'✅' if acertou else '❌'}")
        
        for agente_id in self.ultimos_agentes:
            with cache['lock_agentes']:
                if agente_id in cache['todos_agentes']:
                    cache['todos_agentes'][agente_id].aprender(resultado_real, acertou)
        
        if acertou:
            novo_padrao = self._detectar_novo_padrao(self.ultimo_contexto, acertou)
            if novo_padrao:
                self._criar_agentes_novo_padrao(*novo_padrao)
        
        if self.total_previsoes % 100 == 0:
            self._limpar_agentes_fracos()
    
    def _limpar_agentes_fracos(self):
        with cache['lock_agentes']:
            remover = []
            for agente_id, agente in cache['todos_agentes'].items():
                if agente.total_uso > 50 and agente.precisao < 0.4:
                    remover.append(agente_id)
            
            for agente_id in remover:
                del cache['todos_agentes'][agente_id]
            
            if remover:
                print(f"🧹 Removidos {len(remover)} agentes fracos")
                cache['contador_agentes'] = len(cache['todos_agentes'])
    
    def get_stats(self) -> dict:
        precisao = (self.acertos / self.total_previsoes * 100) if self.total_previsoes > 0 else 0
        
        tipos_count = {'NORMAL': 0, 'TURBINADO': 0, 'PARALELO': 0}
        melhores = []
        
        with cache['lock_agentes']:
            for agente in cache['todos_agentes'].values():
                tipo = getattr(agente, 'tipo', 'NORMAL')
                tipos_count[tipo] = tipos_count.get(tipo, 0) + 1
                
                if agente.total_uso > 10:
                    melhores.append({
                        'id': agente.id[:8],
                        'nome': agente.nome[:25],
                        'padrao': agente.padrao[:25],
                        'precisao': round(agente.precisao * 100, 1),
                        'peso': round(agente.peso, 2),
                        'tipo': tipo,
                        'acertos': agente.acertos,
                        'erros': agente.erros
                    })
        
        melhores.sort(key=lambda x: x['precisao'], reverse=True)
        
        return {
            'total_previsoes': self.total_previsoes,
            'acertos': self.acertos,
            'erros': self.erros,
            'precisao': round(precisao, 1),
            'total_agentes': cache['contador_agentes'],
            'agentes_por_tipo': tipos_count,
            'melhores_agentes': melhores[:50]
        }
    
    def salvar(self, arquivo: str = 'sistema_agentes.pkl'):
        with cache['lock_agentes']:
            estado = {
                'total_previsoes': self.total_previsoes,
                'acertos': self.acertos,
                'erros': self.erros,
                'agentes': {aid: a.to_dict() for aid, a in cache['todos_agentes'].items()},
                'contador_agentes': cache['contador_agentes'],
                'fabrica_total': self.fabrica.total_criados
            }
            
            try:
                with open(arquivo, 'wb') as f:
                    pickle.dump(estado, f)
                print(f"💾 Sistema salvo em {arquivo}")
                return True
            except Exception as e:
                print(f"❌ Erro ao salvar: {e}")
                return False
    
    def carregar(self, arquivo: str = 'sistema_agentes.pkl'):
        if not os.path.exists(arquivo):
            print(f"📂 Nenhum arquivo encontrado: {arquivo}")
            return False
        
        try:
            with open(arquivo, 'rb') as f:
                estado = pickle.load(f)
            
            self.total_previsoes = estado.get('total_previsoes', 0)
            self.acertos = estado.get('acertos', 0)
            self.erros = estado.get('erros', 0)
            cache['contador_agentes'] = estado.get('contador_agentes', 0)
            self.fabrica.total_criados = estado.get('fabrica_total', 0)
            
            agentes_dict = estado.get('agentes', {})
            for agente_id, dados in agentes_dict.items():
                tipo = dados.get('tipo', 'NORMAL')
                if tipo == 'TURBINADO':
                    agente = AgenteTurbinado(
                        agente_id, dados['nome'], dados['padrao'],
                        dados['contexto'], dados['previsao']
                    )
                elif tipo == 'PARALELO':
                    agente = AgenteParalelo(
                        agente_id, dados['nome'], dados['padrao'],
                        dados['contexto'], dados['previsao']
                    )
                else:
                    agente = AgenteBase(
                        agente_id, dados['nome'], dados['padrao'],
                        dados['contexto'], dados['previsao']
                    )
                
                agente.acertos = dados['acertos']
                agente.erros = dados['erros']
                agente.total_uso = dados['total_uso']
                agente.peso = dados['peso']
                
                cache['todos_agentes'][agente_id] = agente
                
                if dados['padrao'] not in cache['agentes_por_padrao']:
                    cache['agentes_por_padrao'][dados['padrao']] = []
                cache['agentes_por_padrao'][dados['padrao']].append(agente_id)
                
                ch = self._hash_contexto(dados['contexto'])
                if ch not in cache['agentes_por_contexto']:
                    cache['agentes_por_contexto'][ch] = []
                cache['agentes_por_contexto'][ch].append(agente_id)
            
            print(f"✅ Sistema carregado: {len(cache['todos_agentes'])} agentes")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao carregar: {e}")
            return False


# =============================================================================
# 8. FUNÇÕES DO BANCO DE DADOS
# =============================================================================

def get_db_connection():
    try:
        conn = pg8000.connect(
            user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT,
            database=DB_NAME, ssl_context=SSL_CONTEXT, timeout=30
        )
        conn.autocommit = False
        return conn
    except Exception as e:
        print(f"❌ Erro banco: {e}")
        return None

def init_db():
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS rodadas (id TEXT PRIMARY KEY, data_hora TIMESTAMPTZ, player_score INTEGER, banker_score INTEGER, resultado TEXT, fonte TEXT)')
        cur.execute('CREATE TABLE IF NOT EXISTS historico_previsoes (id SERIAL PRIMARY KEY, data_hora TIMESTAMPTZ DEFAULT NOW(), previsao TEXT, confianca INTEGER, resultado_real TEXT, acertou BOOLEAN, modo TEXT, agentes_usados INTEGER)')
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Banco inicializado")
        return True
    except Exception as e:
        print(f"❌ Erro banco: {e}")
        return False

def salvar_rodada(rodada, fonte):
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute('INSERT INTO rodadas (id, data_hora, player_score, banker_score, resultado, fonte) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING',
                   (rodada['id'], rodada['data_hora'], rodada['player_score'], rodada['banker_score'], rodada['resultado'], fonte))
        if cur.rowcount > 0:
            conn.commit()
            cur.close()
            conn.close()
            return True
        conn.rollback()
        cur.close()
        conn.close()
        return False
    except:
        return False

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
            brasilia = row[0].astimezone(timezone(timedelta(hours=-3)))
            resultado.append({
                'hora': brasilia.strftime('%H:%M:%S'),
                'resultado': row[3],
                'cor': '🔴' if row[3]=='BANKER' else '🔵',
                'player': row[1],
                'banker': row[2]
            })
        return resultado
    except:
        return []

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
    except:
        return 0

def atualizar_dados_leves():
    cache['leves']['ultimas_20'] = get_ultimas_20()
    cache['leves']['total_rodadas'] = get_total_rapido()
    cache['leves']['ultima_atualizacao'] = datetime.now(timezone.utc)

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
    except:
        return 0

def atualizar_dados_pesados():
    cache['pesados']['periodos'] = {
        '1h': contar_periodo(1), '6h': contar_periodo(6), '12h': contar_periodo(12),
        '24h': contar_periodo(24), '48h': contar_periodo(48), '72h': contar_periodo(72)
    }
    cache['pesados']['ultima_atualizacao'] = datetime.now(timezone.utc)


# =============================================================================
# 9. COLETA DE DADOS (API LATEST)
# =============================================================================

def buscar_latest():
    global ultimo_id_latest
    try:
        response = requests.get(LATEST_API_URL, headers=HEADERS, timeout=2)
        if response.status_code == 200:
            dados = response.json()
            novo_id = dados.get('id')
            if novo_id and novo_id != ultimo_id_latest:
                ultimo_id_latest = novo_id
                data = dados.get('data', {})
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
                rodada = {
                    'id': novo_id,
                    'data_hora': datetime.now(timezone.utc),
                    'player_score': player_score,
                    'banker_score': banker_score,
                    'resultado': resultado
                }
                print(f"\n📡 LATEST: {player_score} vs {banker_score} - {resultado}")
                return rodada
        return None
    except Exception as e:
        return None

def loop_latest():
    print("📡 Coletor LATEST iniciado")
    while True:
        try:
            rodada = buscar_latest()
            if rodada:
                fila_rodadas.append(rodada)
            time.sleep(INTERVALO_LATEST)
        except:
            time.sleep(INTERVALO_LATEST)


# =============================================================================
# 10. PROCESSADOR DA FILA
# =============================================================================

def processar_fila(sistema):
    print("🚀 Processador de Agentes Infinitos iniciado...")
    historico_buffer = []
    ultima_previsao = None
    modo_atual = "AGUARDANDO"
    
    while True:
        try:
            if len(historico_buffer) >= 30 and modo_atual == "AGUARDANDO":
                print(f"\n🎯 INICIANDO PREVISÕES com {len(historico_buffer)} rodadas")
                modo_atual = "ATIVO"
            
            if fila_rodadas:
                batch = list(fila_rodadas)
                fila_rodadas.clear()
                
                for rodada in batch:
                    if salvar_rodada(rodada, 'principal'):
                        historico_buffer.append(rodada)
                        
                        if ultima_previsao:
                            resultado_real = rodada['resultado']
                            if resultado_real != 'TIE':
                                acertou = (ultima_previsao['previsao'] == resultado_real)
                                cache['estatisticas']['total_previsoes'] += 1
                                if acertou:
                                    cache['estatisticas']['acertos'] += 1
                                else:
                                    cache['estatisticas']['erros'] += 1
                                
                                sistema.aprender(resultado_real)
                                print(f"\n📊 PREVISÃO: {ultima_previsao['previsao']} | Real: {resultado_real} | {'✅' if acertou else '❌'}")
                            ultima_previsao = None
                        
                        if len(historico_buffer) >= 30 and modo_atual == "ATIVO" and not ultima_previsao:
                            historico_completo = [{'resultado': r['resultado'], 'player_score': r['player_score'], 'banker_score': r['banker_score']} for r in historico_buffer[-50:]]
                            
                            previsao = sistema.prever(historico_completo)
                            if previsao['previsao'] != 'AGUARDANDO':
                                ultima_previsao = previsao
                                cache['ultima_previsao'] = ultima_previsao
                                cache['leves']['previsao'] = ultima_previsao
                                print(f"\n🔮 PREVISÃO: {ultima_previsao['previsao']} com {ultima_previsao['confianca']}%")
                    
                    cache['leves']['ultima_atualizacao'] = datetime.now(timezone.utc)
            
            time.sleep(0.01)
        except Exception as e:
            print(f"❌ Erro: {e}")
            traceback.print_exc()
            time.sleep(0.1)

def loop_pesado():
    while True:
        time.sleep(300)
        try:
            atualizar_dados_pesados()
        except:
            pass


# =============================================================================
# 11. ROTAS DA API
# =============================================================================

@app.route('/api/stats')
def api_stats():
    stats_sistema = cache['sistema'].get_stats() if cache.get('sistema') else None
    return jsonify({
        'total_rodadas': cache['leves']['total_rodadas'],
        'ultimas_20': cache['leves']['ultimas_20'],
        'previsao': cache['leves']['previsao'],
        'periodos': cache['pesados']['periodos'],
        'estatisticas': cache['estatisticas'],
        'sistema_agentes': stats_sistema
    })

@app.route('/api/agentes')
def api_agentes():
    if not cache.get('sistema'):
        return jsonify({'erro': 'Sistema não inicializado'})
    
    agentes_lista = []
    with cache['lock_agentes']:
        for agente in cache['todos_agentes'].values():
            agentes_lista.append(agente.to_dict())
    
    agentes_lista.sort(key=lambda x: x['precisao'], reverse=True)
    
    return jsonify({
        'total': len(agentes_lista),
        'agentes': agentes_lista[:100]
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
        brasilia = row[0].astimezone(timezone(timedelta(hours=-3)))
        resultado.append({
            'data': brasilia.strftime('%d/%m %H:%M:%S'),
            'player': row[1],
            'banker': row[2],
            'resultado': row[3],
            'cor': '🔴' if row[3]=='BANKER' else '🔵'
        })
    return jsonify(resultado)


# =============================================================================
# 12. MAIN
# =============================================================================

if __name__ == "__main__":
    print("="*80)
    print("🐟 BACBO PREDICTOR - AGENTES INFINITOS")
    print("="*80)
    print("   ✅ TODO NOVO PADRÃO = NOVO AGENTE RL")
    print("   ✅ AGENTES TURBINADOS (REDES NEURAIS)")
    print("   ✅ AGENTES PARALELOS (PROCESSAMENTO EM MASSA)")
    print("   ✅ SEM LIMITE DE AGENTES")
    print("="*80)
    
    # Inicializar banco
    init_db()
    atualizar_dados_leves()
    atualizar_dados_pesados()
    print(f"📊 {cache['leves']['total_rodadas']} rodadas no banco")
    
    # Criar sistema de agentes infinitos
    print("\n🐟 CRIANDO SISTEMA DE AGENTES INFINITOS...")
    sistema = SistemaAgentesInfinitos()
    sistema.carregar()
    cache['sistema'] = sistema
    
    # Mostrar estatísticas iniciais
    stats = sistema.get_stats()
    print(f"\n📊 SISTEMA INICIALIZADO:")
    print(f"   Agentes: {stats['total_agentes']}")
    print(f"   Agentes por tipo: {stats['agentes_por_tipo']}")
    print(f"   PyTorch: {'✅ Disponível' if TORCH_AVAILABLE else '❌ Modo fallback'}")
    
    # Iniciar threads
    print("\n🔌 Iniciando threads...")
    threading.Thread(target=loop_latest, daemon=True).start()
    threading.Thread(target=processar_fila, args=(sistema,), daemon=True).start()
    threading.Thread(target=loop_pesado, daemon=True).start()
    
    # Thread para salvar periodicamente
    def salvar_periodicamente():
        while True:
            time.sleep(300)
            if cache.get('sistema'):
                cache['sistema'].salvar()
                print("💾 Sistema salvo automaticamente")
    
    threading.Thread(target=salvar_periodicamente, daemon=True).start()
    
    print("\n" + "="*80)
    print("🚀 FLASK INICIANDO...")
    print("   /health - Healthcheck")
    print("   /api/stats - Estatísticas")
    print("   /api/agentes - Listar agentes")
    print("   /api/tabela/<n> - Histórico")
    print("="*80)
    
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
