# =============================================================================
# main.py - BACBO PREDICTOR - AGENTES INFINITOS (VERSÃO COMPLETA CORRIGIDA)
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
import hashlib
import copy
from datetime import datetime, timedelta, timezone
from collections import deque
from typing import List, Dict, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from pathlib import Path

# =============================================================================
# WEB FRAMEWORK
# =============================================================================
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS

# =============================================================================
# HTTP REQUESTS E WEBSOCKET
# =============================================================================
import requests
import websocket

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
DEVICE_STR = 'cpu'

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    DEVICE_STR = str(DEVICE)  # Guardar como string para JSON
    print(f"✅ PyTorch disponível - Device: {DEVICE}")
except ImportError as e:
    print(f"⚠️ PyTorch não disponível: {e}")
    print("   Os agentes turbinados usarão modo fallback")

# =============================================================================
# MULTIPROCESSING
# =============================================================================
import multiprocessing as mp
from multiprocessing import Queue as MPQueue

# =============================================================================
# 🚀 INICIAR FLASK
# =============================================================================
app = Flask(__name__)
CORS(app)

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
WS_URL = "wss://api-cs.casino.org/svc-evolution-game-events/ws/bacbo"
API_URL = "https://api-cs.casino.org/svc-evolution-game-events/api/bacbo"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
}

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
fila_rodadas = deque(maxlen=1000)
ultimo_id_latest = None
ultimo_id_websocket = None
ultimo_id_api = None

# =============================================================================
# CACHE GLOBAL
# =============================================================================
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
        'ultimas_20_previsoes': []
    },
    'todos_agentes': {},
    'agentes_por_padrao': {},
    'agentes_por_contexto': {},
    'fila_criacao_agentes': deque(maxlen=100),
    'ultima_previsao': None,
    'ultimo_resultado_real': None,
    'contador_agentes': 0,
    'lock_agentes': threading.Lock(),
    'sistema': None,
    'indice_confianca': 50,
    'padroes_descobertos': [],
    'ultra_precisao': None,
    'curto_prazo': None,
    'estrategia_surto': None,
    'analisador_erros': None,
    'memoria_erros': None,
    'votacao': None,
    'simulador': None,
    'historico_rodadas': deque(maxlen=500)  # Adicionado
}


# =============================================================================
# 1. REDE NEURAL PARA AGENTES TURBINADOS
# =============================================================================

if TORCH_AVAILABLE:
    class RedeNeuralAgente(nn.Module):
        """Rede neural profunda para agentes turbinados"""
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
        def __init__(self, *args, **kwargs):
            pass
        def to(self, *args):
            return self
        def train(self):
            pass
        def eval(self):
            pass
        def __call__(self, *args, **kwargs):
            return np.array([[0.5, 0.5]])


# =============================================================================
# 2. INDICADORES BASE (TODOS OS QUE VOCÊ DESCOBRIU)
# =============================================================================

class IndicadoresBase:
    """TODOS os indicadores que você descobriu no arquivo JSON"""
    def __init__(self):
        # =====================================================================
        # 1. LIMITE DE STREAK
        # =====================================================================
        self.LIMITE_STREAK_PLAYER = 5
        self.LIMITE_STREAK_BANKER = 4
        self.REVERSAO_APOS_3 = 0.80
        
        # =====================================================================
        # 2. PROBABILIDADE DE TIE COMO "VIBRADOR"
        # =====================================================================
        self.PROB_TIE_VIBRADOR = 0.208
        self.PROB_TIE_POS_TIE = 0.311
        
        # =====================================================================
        # 3. DELTA
        # =====================================================================
        self.LIMITE_CORRECAO_INICIO = 15
        self.LIMITE_CORRECAO_GARANTIDA = 20
        self.DELTA_MAX_POSITIVO = 23
        self.DELTA_MAX_NEGATIVO = -19
        
        # =====================================================================
        # 4. EMPATE 6 (SUA DESCOBERTA MAIS IMPORTANTE!)
        # =====================================================================
        self.TIE_6_PROXIMO_PLAYER = 1.0
        
        # =====================================================================
        # 5. PADRÃO DUPLO TIE + 7:2
        # =====================================================================
        self.DUPLO_TIE_BANKER_PCT = 0.77
        self.DUPLO_TIE_PLAYER_PCT = 0.22
        
        # =====================================================================
        # 6. DISTRIBUIÇÃO DE SOMAS
        # =====================================================================
        self.COMBINACOES_POR_SOMA = {
            2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6,
            8: 5, 9: 4, 10: 3, 11: 2, 12: 1
        }
        
        # =====================================================================
        # 7. VIBRAÇÃO (Ruído probabilístico)
        # =====================================================================
        self.VIBRACAO_DIFERENCA_1 = 0.30
        self.VIBRACAO_RANGE = (-2, 2)
        
        # =====================================================================
        # 8. REVERSÃO FORÇADA
        # =====================================================================
        self.REVERSAO_BONUS_MIN = 1
        self.REVERSAO_BONUS_MAX = 3
        
        # =====================================================================
        # 9. ALTERNÂNCIA
        # =====================================================================
        self.ALTERNANCIA_PCT = 0.60
        self.REPETICAO_PCT = 0.40
        
        # =====================================================================
        # 10. SCORES MAIS COMUNS
        # =====================================================================
        self.SCORES_COMUNS = [6, 7, 8]
        self.SCORES_POUCO_COMUNS = [2, 3, 11, 12]
        
        print("✅ Indicadores Base carregados")
        self._mostrar_resumo()
    
    def _mostrar_resumo(self):
        print("\n" + "="*70)
        print("📊 INDICADORES DESCOBERTOS:")
        print("="*70)
        print(f"   🔴 Streak máximo PLAYER: {self.LIMITE_STREAK_PLAYER}")
        print(f"   🔵 Streak máximo BANKER: {self.LIMITE_STREAK_BANKER}")
        print(f"   🎯 Reversão após 3: {self.REVERSAO_APOS_3*100:.0f}%")
        print(f"   📈 Delta início correção: ±{self.LIMITE_CORRECAO_INICIO}")
        print(f"   📈 Delta correção garantida: ±{self.LIMITE_CORRECAO_GARANTIDA}")
        print(f"   🟡 TIE como vibrador: {self.PROB_TIE_VIBRADOR*100:.1f}%")
        print(f"   🟡 TIE após TIE: {self.PROB_TIE_POS_TIE*100:.1f}%")
        print(f"   🎲 Empate 6 → PLAYER: {self.TIE_6_PROXIMO_PLAYER*100:.0f}% (2/2)")
        print(f"   🔄 Duplo TIE → BANKER: {self.DUPLO_TIE_BANKER_PCT*100:.0f}%")
        print(f"   🌊 Vibração (dif=1): {self.VIBRACAO_DIFERENCA_1*100:.0f}% vira TIE")
        print(f"   🔄 Alternância: {self.ALTERNANCIA_PCT*100:.0f}% | Repetição: {self.REPETICAO_PCT*100:.0f}%")
        print("="*70)


# =============================================================================
# 3. MEMÓRIA DE ERROS (Aprende com os erros)
# =============================================================================

class MemoriaDeErros:
    def __init__(self, capacidade=500):
        self.capacidade = capacidade
        self.erros = deque(maxlen=capacidade)
        self.padroes_que_mais_erram = {}
        self.erros_por_padrao = {}
        self.acertos_por_padrao = {}
        print(f"💾 Memória de Erros: {capacidade} posições")
    
    def registrar_erro(self, erro_info):
        self.erros.append(erro_info)
        padrao = erro_info.get('padrao', 'desconhecido')
        self.erros_por_padrao[padrao] = self.erros_por_padrao.get(padrao, 0) + 1
        
        if self.erros_por_padrao.get(padrao, 0) > 5:
            if padrao not in self.padroes_que_mais_erram:
                self.padroes_que_mais_erram[padrao] = 0
            self.padroes_que_mais_erram[padrao] += 1
            print(f"⚠️ ALERTA: Padrão '{padrao}' errou {self.erros_por_padrao[padrao]} vezes!")
    
    def registrar_acerto(self, padrao):
        self.acertos_por_padrao[padrao] = self.acertos_por_padrao.get(padrao, 0) + 1
    
    def get_precisao_por_padrao(self, padrao):
        acertos = self.acertos_por_padrao.get(padrao, 0)
        erros = self.erros_por_padrao.get(padrao, 0)
        total = acertos + erros
        return (acertos / total) if total > 0 else None
    
    def sugerir_ajustes(self):
        ajustes = {}
        for padrao, erros in self.erros_por_padrao.items():
            acertos = self.acertos_por_padrao.get(padrao, 0)
            total = acertos + erros
            if total >= 10:
                precisao = acertos / total
                if precisao < 0.4:
                    ajustes[padrao] = {'acao': 'REDUZIR', 'fator': 0.7, 'precisao': precisao}
                elif precisao > 0.7:
                    ajustes[padrao] = {'acao': 'AUMENTAR', 'fator': 1.2, 'precisao': precisao}
        return ajustes
    
    def get_stats(self):
        stats = []
        for padrao in set(list(self.erros_por_padrao.keys()) + list(self.acertos_por_padrao.keys())):
            acertos = self.acertos_por_padrao.get(padrao, 0)
            erros = self.erros_por_padrao.get(padrao, 0)
            total = acertos + erros
            if total > 0:
                stats.append({
                    'padrao': padrao,
                    'acertos': acertos,
                    'erros': erros,
                    'precisao': round((acertos / total) * 100, 1)
                })
        return sorted(stats, key=lambda x: x['precisao'])


# =============================================================================
# 4. VOTAÇÃO INTELIGENTE
# =============================================================================

class VotacaoInteligente:
    def __init__(self):
        self.pesos_padroes = {
            'streak_3_reversao': 0.75,
            'streak_4_reversao': 0.80,
            'delta_correcao': 0.80,
            'tie_6_player': 0.95,
            'duplo_tie_72': 0.77,
            'vibracao_tie': 0.55,
            'alternancia': 0.60,
            'repeticao': 0.40
        }
        self.historico_votacoes = deque(maxlen=200)
        self.confianca_media = 50
        print("🗳️ Votação Inteligente inicializada")
    
    def ajustar_peso(self, padrao, novo_peso):
        if padrao in self.pesos_padroes:
            self.pesos_padroes[padrao] = max(0.3, min(0.95, novo_peso))
    
    def aplicar_ajustes(self, ajustes):
        for padrao, ajuste in ajustes.items():
            if padrao in self.pesos_padroes:
                novo_peso = self.pesos_padroes[padrao] * ajuste['fator']
                self.ajustar_peso(padrao, novo_peso)
    
    def votar(self, previsoes):
        votos = {'BANKER': 0, 'PLAYER': 0, 'TIE': 0}
        votos_detalhados = []
        
        for p in previsoes:
            previsao = p['previsao']
            confianca = p['confianca'] / 100
            padrao = p.get('padrao', 'desconhecido')
            peso = self.pesos_padroes.get(padrao, 0.5)
            peso_voto = confianca * peso
            votos[previsao] += peso_voto
            votos_detalhados.append({
                'padrao': padrao,
                'previsao': previsao,
                'confianca': p['confianca'],
                'peso': round(peso, 3),
                'peso_voto': round(peso_voto, 3)
            })
        
        previsao_final = max(votos, key=votos.get)
        total_votos = sum(votos.values())
        confianca_final = (votos[previsao_final] / total_votos) * 100 if total_votos > 0 else 50
        
        self.historico_votacoes.append({
            'timestamp': datetime.now(),
            'votos': votos_detalhados,
            'resultado': previsao_final,
            'confianca': confianca_final
        })
        
        self.confianca_media = self.confianca_media * 0.9 + confianca_final * 0.1
        
        return previsao_final, round(confianca_final), votos_detalhados
    
    def get_stats(self):
        return {
            'pesos': self.pesos_padroes,
            'confianca_media': round(self.confianca_media, 1),
            'total_votacoes': len(self.historico_votacoes)
        }


# =============================================================================
# 5. CÉLULA DE MEMÓRIA (Mapa Mental)
# =============================================================================

@dataclass
class CelulaMemoria:
    id: int
    padrao: str
    contexto: List[str]
    previsao: str
    confianca: float = 0.5
    acertos: int = 0
    erros: int = 0
    criado_em: datetime = field(default_factory=datetime.now)
    ultimo_uso: datetime = field(default_factory=datetime.now)
    
    @property
    def precisao(self) -> float:
        total = self.acertos + self.erros
        return (self.acertos / total) if total > 0 else 0.5
    
    @property
    def peso(self) -> float:
        return self.precisao * self.confianca
    
    def atualizar(self, acertou: bool):
        if acertou:
            self.acertos += 1
            self.confianca = min(0.95, self.confianca * 1.05)
        else:
            self.erros += 1
            self.confianca = max(0.3, self.confianca * 0.95)
        self.ultimo_uso = datetime.now()


# =============================================================================
# 6. MAPA MENTAL (Repositório de memórias)
# =============================================================================

class MapaMental:
    def __init__(self, capacidade=2000):
        self.celulas: Dict[int, CelulaMemoria] = {}
        self.proximo_id = 0
        self.capacidade = capacidade
        self.indice_por_contexto = {}
        print(f"🗺️ Mapa Mental: {capacidade} células")
    
    def _hash_contexto(self, contexto: List[str]) -> str:
        filtrados = [r for r in contexto if r != 'TIE'][:5]
        return '_'.join(filtrados) if filtrados else 'vazio'
    
    def adicionar_memoria(self, padrao: str, contexto: List[str], previsao: str) -> int:
        ch = self._hash_contexto(contexto)
        if ch in self.indice_por_contexto:
            for cell_id in self.indice_por_contexto[ch]:
                if self.celulas[cell_id].padrao == padrao:
                    return cell_id
        
        nova = CelulaMemoria(id=self.proximo_id, padrao=padrao, contexto=contexto.copy(), previsao=previsao)
        self.celulas[self.proximo_id] = nova
        
        if ch not in self.indice_por_contexto:
            self.indice_por_contexto[ch] = []
        self.indice_por_contexto[ch].append(self.proximo_id)
        
        if len(self.celulas) > self.capacidade:
            self._limpar_memorias_fracas()
        
        self.proximo_id += 1
        return self.proximo_id - 1
    
    def consultar(self, contexto: List[str]) -> Optional[CelulaMemoria]:
        ch = self._hash_contexto(contexto)
        if ch in self.indice_por_contexto:
            melhores = []
            for cell_id in self.indice_por_contexto[ch]:
                cell = self.celulas[cell_id]
                relevancia = cell.peso * (1 - (datetime.now() - cell.ultimo_uso).seconds / 86400)
                melhores.append((cell, relevancia))
            melhores.sort(key=lambda x: x[1], reverse=True)
            return melhores[0][0] if melhores else None
        return None
    
    def atualizar_memoria(self, cell_id: int, acertou: bool):
        if cell_id in self.celulas:
            self.celulas[cell_id].atualizar(acertou)
    
    def _limpar_memorias_fracas(self):
        fracas = [(id, c.peso) for id, c in self.celulas.items() if c.precisao < 0.4]
        fracas.sort(key=lambda x: x[1])
        remover = len(fracas) // 10
        for i in range(min(remover, len(fracas))):
            del self.celulas[fracas[i][0]]
    
    def get_stats(self):
        if not self.celulas:
            return {'total_celulas': 0, 'precisao_media': 0}
        precisao_media = sum(c.precisao for c in self.celulas.values()) / len(self.celulas)
        return {
            'total_celulas': len(self.celulas),
            'precisao_media': round(precisao_media * 100, 1)
        }
    
    def salvar(self, arquivo='mapa_mental.pkl'):
        estado = {
            'proximo_id': self.proximo_id,
            'celulas': {id: {
                'id': c.id, 'padrao': c.padrao, 'contexto': c.contexto, 'previsao': c.previsao,
                'confianca': c.confianca, 'acertos': c.acertos, 'erros': c.erros,
                'criado_em': c.criado_em.isoformat(), 'ultimo_uso': c.ultimo_uso.isoformat()
            } for id, c in self.celulas.items()}
        }
        with open(arquivo, 'wb') as f:
            pickle.dump(estado, f)
    
    def carregar(self, arquivo='mapa_mental.pkl'):
        if not os.path.exists(arquivo):
            return False
        with open(arquivo, 'rb') as f:
            estado = pickle.load(f)
        self.proximo_id = estado['proximo_id']
        self.celulas = {}
        for id_str, data in estado['celulas'].items():
            self.celulas[id_str] = CelulaMemoria(
                id=data['id'], padrao=data['padrao'], contexto=data['contexto'],
                previsao=data['previsao'], confianca=data['confianca'],
                acertos=data['acertos'], erros=data['erros'],
                criado_em=datetime.fromisoformat(data['criado_em']),
                ultimo_uso=datetime.fromisoformat(data['ultimo_uso'])
            )
        self.indice_por_contexto = {}
        for cell in self.celulas.values():
            ch = self._hash_contexto(cell.contexto)
            if ch not in self.indice_por_contexto:
                self.indice_por_contexto[ch] = []
            self.indice_por_contexto[ch].append(cell.id)
        return True


# =============================================================================
# 7. SIMULADOR DE CENÁRIOS (Baseado nos seus indicadores)
# =============================================================================

class SimuladorCenarios:
    def __init__(self, indicadores):
        self.ind = indicadores
        print("🎲 Simulador de Cenários inicializado")
    
    def _calcular_streak(self, historico):
        streak = 0
        ultimo = None
        for r in historico[:10]:
            if r.get('resultado') != 'TIE':
                if ultimo is None:
                    streak = 1
                    ultimo = r['resultado']
                elif r['resultado'] == ultimo:
                    streak += 1
                else:
                    break
        return streak
    
    def _calcular_delta(self, historico):
        player = sum(1 for r in historico[:100] if r.get('resultado') == 'PLAYER')
        banker = sum(1 for r in historico[:100] if r.get('resultado') == 'BANKER')
        return player - banker
    
    def _gerar_proxima_rodada(self, historico):
        if len(historico) < 10:
            return random.choice(['BANKER', 'PLAYER'])
        
        streak = self._calcular_streak(historico)
        delta = self._calcular_delta(historico)
        ultimo = historico[0].get('resultado') if historico else None
        ultimo_score_player = historico[0].get('player_score', 0) if historico else 0
        ultimo_score_banker = historico[0].get('banker_score', 0) if historico else 0
        
        # 1. Duplo TIE → 77% BANKER
        if len(historico) >= 2 and historico[0].get('resultado') == 'TIE' and historico[1].get('resultado') == 'TIE':
            if random.random() < self.ind.DUPLO_TIE_BANKER_PCT:
                return 'BANKER'
        
        # 2. TIE 6 → PLAYER (100%)
        if ultimo == 'TIE' and ultimo_score_player == 6 and ultimo_score_banker == 6:
            if random.random() < self.ind.TIE_6_PROXIMO_PLAYER:
                return 'PLAYER'
        
        # 3. Delta correção
        if abs(delta) >= self.ind.LIMITE_CORRECAO_GARANTIDA:
            if random.random() < 0.85:
                return 'BANKER' if delta > 0 else 'PLAYER'
        elif abs(delta) >= self.ind.LIMITE_CORRECAO_INICIO:
            if random.random() < 0.70:
                return 'BANKER' if delta > 0 else 'PLAYER'
        
        # 4. Streak reversão (após 3)
        if streak >= 3 and ultimo:
            if random.random() < self.ind.REVERSAO_APOS_3:
                return 'BANKER' if ultimo == 'PLAYER' else 'PLAYER'
        
        # 5. Alternância / Repetição
        ultimos = [r['resultado'] for r in historico[:5] if r.get('resultado') != 'TIE']
        if len(ultimos) >= 2:
            if ultimos[0] != ultimos[1]:
                if random.random() < self.ind.ALTERNANCIA_PCT:
                    return 'BANKER' if ultimos[0] == 'PLAYER' else 'PLAYER'
                else:
                    return ultimos[0]
            else:
                if random.random() < self.ind.REPETICAO_PCT:
                    return ultimos[0]
                else:
                    return 'BANKER' if ultimos[0] == 'PLAYER' else 'PLAYER'
        
        return random.choice(['BANKER', 'PLAYER'])
    
    def gerar_episodio(self, num_rodadas=100):
        episodio = []
        historico = []
        
        for _ in range(50):
            historico.append({
                'resultado': random.choice(['BANKER', 'PLAYER']),
                'player_score': random.randint(2, 12),
                'banker_score': random.randint(2, 12)
            })
        
        for _ in range(num_rodadas):
            resultado = self._gerar_proxima_rodada(historico)
            
            if resultado == 'PLAYER':
                player = random.randint(5, 9)
                banker = random.randint(2, player - 1)
            elif resultado == 'BANKER':
                banker = random.randint(5, 9)
                player = random.randint(2, banker - 1)
            else:
                soma = random.choice([6, 7, 8])
                player = banker = soma
            
            rodada = {'resultado': resultado, 'player_score': player, 'banker_score': banker}
            episodio.append((historico.copy(), resultado))
            historico.insert(0, rodada)
        
        return episodio


# =============================================================================
# 8. AGENTE BASE
# =============================================================================

class AgenteBase:
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
# 9. AGENTE TURBINADO
# =============================================================================

class AgenteTurbinado(AgenteBase):
    def __init__(self, agente_id: str, nome: str, padrao: str, contexto: List[str], previsao: str):
        super().__init__(agente_id, nome, padrao, contexto, previsao)
        self.tipo = "TURBINADO"
        self.learning_rate = 0.001
        self.gamma = 0.95
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
    
    def treinar_rede(self, historico: List[dict], acao_correta: int):
        if not self.model or not TORCH_AVAILABLE:
            return
        try:
            features = self.extrair_features(historico)
            features_tensor = torch.FloatTensor(features).unsqueeze(0).to(self.device)
            target = torch.LongTensor([acao_correta]).to(self.device)
            self.model.train()
            self.optimizer.zero_grad()
            output = self.model(features_tensor)
            loss = F.cross_entropy(output, target)
            loss.backward()
            self.optimizer.step()
            self.model.eval()
        except Exception:
            pass
    
    def to_dict(self) -> dict:
        dados = super().to_dict()
        dados['tipo'] = 'TURBINADO'
        dados['learning_rate'] = self.learning_rate
        dados['memoria_tamanho'] = len(self.memoria)
        return dados


# =============================================================================
# 10. AGENTE PARALELO
# =============================================================================

class AgenteParalelo(AgenteBase):
    def __init__(self, agente_id: str, nome: str, padrao: str, contexto: List[str], previsao: str):
        super().__init__(agente_id, nome, padrao, contexto, previsao)
        self.tipo = "PARALELO"
        self.batch_size = 32
        self.pending_updates = []
        print(f"⚡ Agente PARALELO criado: {nome}")
    
    def processar_lote(self, historicos: List[List[dict]]) -> List[Tuple[str, float]]:
        resultados = []
        for historico in historicos:
            previsao, confianca = self.prever(historico)
            resultados.append((previsao, confianca))
        return resultados
    
    def aprender_lote(self, resultados: List[Tuple[str, bool]]):
        for resultado_real, acertou in resultados:
            super().aprender(resultado_real, acertou)
    
    def to_dict(self) -> dict:
        dados = super().to_dict()
        dados['tipo'] = 'PARALELO'
        dados['batch_size'] = self.batch_size
        return dados


# =============================================================================
# 11. FÁBRICA DE AGENTES
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
# 12. DETECTOR DE PADRÃO 7:2
# =============================================================================

class DetectorPadrao72:
    def __init__(self):
        self.duplo_tie_detectado = False
        self.rodadas_desde_duplo_tie = 0
        self.ultimo_duplo_tie = None
        self.total_deteccoes = 0
        print("🔄 Detector de Padrão 7:2 inicializado")
    
    def analisar(self, historico):
        if len(historico) < 10:
            return None
        
        for i in range(min(20, len(historico)-1)):
            if (historico[i].get('resultado') == 'TIE' and 
                historico[i+1].get('resultado') == 'TIE'):
                self.duplo_tie_detectado = True
                self.rodadas_desde_duplo_tie = 0
                self.ultimo_duplo_tie = datetime.now()
                self.total_deteccoes += 1
                
                proximos = []
                for j in range(i+2, min(i+22, len(historico))):
                    if historico[j].get('resultado') != 'TIE':
                        proximos.append(historico[j]['resultado'])
                        if len(proximos) >= 9:
                            break
                
                if len(proximos) >= 9:
                    banker = proximos.count('BANKER')
                    player = proximos.count('PLAYER')
                    total = banker + player
                    if total > 0:
                        banker_pct = (banker / total) * 100
                        if banker_pct > 60:
                            return {
                                'previsao': 'BANKER',
                                'confianca': min(75, 60 + banker_pct/2),
                                'tipo': '7:2_BANKER',
                                'proporcao': f"{banker}:{player}"
                            }
                        elif banker_pct < 40:
                            return {
                                'previsao': 'PLAYER',
                                'confianca': min(75, 60 + (100-banker_pct)/2),
                                'tipo': '2:7_PLAYER',
                                'proporcao': f"{banker}:{player}"
                            }
        
        if self.duplo_tie_detectado:
            self.rodadas_desde_duplo_tie += 1
            if self.rodadas_desde_duplo_tie > 30:
                self.duplo_tie_detectado = False
        
        return None
    
    def get_stats(self):
        return {
            'total_deteccoes': self.total_deteccoes,
            'duplo_tie_ativo': self.duplo_tie_detectado,
            'rodadas_desde_ultimo': self.rodadas_desde_duplo_tie,
            'ultimo_duplo_tie': self.ultimo_duplo_tie.isoformat() if self.ultimo_duplo_tie else None
        }


# =============================================================================
# 13. ESTRATÉGIA DE SURTO
# =============================================================================

class EstrategiaSurto:
    def __init__(self):
        self.ativo = False
        self.confianca_minima = 70
        print("⚡ Estratégia de Surto inicializada")
    
    def analisar_ultimas_5(self, historico):
        if len(historico) < 5:
            return None
        
        ultimas_5 = historico[:5]
        resultados = [r.get('resultado') for r in ultimas_5 if r.get('resultado') != 'TIE']
        
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
# 14. SISTEMA CURTO PRAZO
# =============================================================================

class SistemaCurtoPrazo:
    def __init__(self):
        self.ciclo_atual = 0
        self.rodadas_no_ciclo = 0
        self.max_rodadas = 20
        self.acertos_ciclo = 0
        self.erros_ciclo = 0
        self.historico_ciclo = []
        self.ciclos_completados = []
        self.melhor_ciclo = {'acertos': 0, 'precisao': 0}
        self.em_ultimas_5 = False
        self.agentes_curto_prazo = []
        print(f"🎯 Sistema Curto Prazo inicializado - Ciclo de {self.max_rodadas} rodadas")
    
    def processar_rodada(self, historico):
        self.rodadas_no_ciclo += 1
        self.em_ultimas_5 = self.rodadas_no_ciclo >= (self.max_rodadas - 5)
        
        if len(historico) < 30:
            return None
        
        ultimos_10 = [r.get('resultado') for r in historico[:10] if r.get('resultado') != 'TIE']
        
        if len(ultimos_10) < 5:
            return None
        
        banker_count = ultimos_10.count('BANKER')
        player_count = ultimos_10.count('PLAYER')
        
        confianca_base = 50 + abs(banker_count - player_count) * 5
        confianca_base = min(95, confianca_base)
        
        if banker_count > player_count:
            previsao = 'BANKER'
        else:
            previsao = 'PLAYER'
        
        if self.em_ultimas_5:
            confianca_base = min(95, confianca_base + 10)
        
        return {
            'previsao': previsao,
            'simbolo': '🔴' if previsao == 'BANKER' else '🔵',
            'confianca': round(confianca_base),
            'ciclo': self.ciclo_atual,
            'rodada_no_ciclo': self.rodadas_no_ciclo,
            'ultimas_5': self.em_ultimas_5
        }
    
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
        
        if self.rodadas_no_ciclo >= self.max_rodadas:
            self._finalizar_ciclo()
    
    def _finalizar_ciclo(self):
        total = self.acertos_ciclo + self.erros_ciclo
        precisao = (self.acertos_ciclo / total) * 100 if total > 0 else 0
        
        self.ciclos_completados.append({
            'ciclo': self.ciclo_atual,
            'acertos': self.acertos_ciclo,
            'erros': self.erros_ciclo,
            'precisao': precisao
        })
        
        if precisao > self.melhor_ciclo['precisao']:
            self.melhor_ciclo = {
                'ciclo': self.ciclo_atual,
                'acertos': self.acertos_ciclo,
                'precisao': precisao
            }
        
        print(f"\n📊 CICLO {self.ciclo_atual} FINALIZADO: {precisao:.1f}%")
        
        self.ciclo_atual += 1
        self.rodadas_no_ciclo = 0
        self.acertos_ciclo = 0
        self.erros_ciclo = 0
        self.historico_ciclo = []
        self.em_ultimas_5 = False
    
    def get_stats(self):
        total_ciclos = len(self.ciclos_completados)
        media_precisao = sum(c['precisao'] for c in self.ciclos_completados) / total_ciclos if total_ciclos > 0 else 0
        
        ciclo_atual_total = self.acertos_ciclo + self.erros_ciclo
        precisao_atual = (self.acertos_ciclo / ciclo_atual_total * 100) if ciclo_atual_total > 0 else 0
        
        return {
            'modo': 'CURTO_PRAZO',
            'ciclo_atual': self.ciclo_atual,
            'rodada_no_ciclo': self.rodadas_no_ciclo,
            'precisao_ciclo_atual': round(precisao_atual, 1),
            'total_ciclos': total_ciclos,
            'media_precisao_ciclos': round(media_precisao, 1),
            'melhor_ciclo': self.melhor_ciclo,
            'ultimas_5': self.em_ultimas_5
        }


# =============================================================================
# 15. SISTEMA ULTRA PRECISÃO
# =============================================================================

class SistemaUltraPrecisao:
    def __init__(self):
        self.limiar_base = 80
        self.janela_curta = deque(maxlen=30)
        self.janela_longa = deque(maxlen=200)
        self.tendencias = {'curta': {'banker': 0, 'player': 0}, 'longa': {'banker': 0, 'player': 0}}
        self.total_apostas = 0
        self.acertos_apostas = 0
        self.rede_decisao = None
        self._criar_rede()
        print("🚀 Sistema Ultra Precisão inicializado")
    
    def _criar_rede(self):
        if not TORCH_AVAILABLE:
            return
        try:
            class RedeDecisao(nn.Module):
                def __init__(self):
                    super().__init__()
                    self.fc1 = nn.Linear(60, 64)
                    self.fc2 = nn.Linear(64, 32)
                    self.fc3 = nn.Linear(32, 2)
                    self.dropout = nn.Dropout(0.2)
                def forward(self, x):
                    x = torch.relu(self.fc1(x))
                    x = self.dropout(x)
                    x = torch.relu(self.fc2(x))
                    x = self.fc3(x)
                    return F.softmax(x, dim=1)
            self.rede_decisao = RedeDecisao().to(DEVICE)
            print("✅ Rede de decisão criada")
        except Exception as e:
            print(f"⚠️ Erro ao criar rede: {e}")
    
    def atualizar_janelas(self, historico):
        if not historico:
            return
        self.janela_curta.clear()
        self.janela_longa.clear()
        for rodada in historico[:30]:
            self.janela_curta.append(rodada)
        for rodada in historico[:200]:
            self.janela_longa.append(rodada)
        self._atualizar_tendencias()
    
    def _atualizar_tendencias(self):
        self.tendencias['curta'] = self._calcular_tendencia(self.janela_curta)
        self.tendencias['longa'] = self._calcular_tendencia(self.janela_longa)
    
    def _calcular_tendencia(self, janela):
        if not janela:
            return {'banker': 0, 'player': 0, 'banker_pct': 0, 'player_pct': 0}
        banker = sum(1 for r in janela if r.get('resultado') == 'BANKER')
        player = sum(1 for r in janela if r.get('resultado') == 'PLAYER')
        total = len(janela)
        return {
            'banker': banker, 'player': player,
            'banker_pct': (banker / total) * 100 if total > 0 else 0,
            'player_pct': (player / total) * 100 if total > 0 else 0
        }
    
    def _extrair_features(self, historico, previsao, confianca):
        features = []
        for rodada in historico[:20]:
            resultado = rodada.get('resultado', '')
            if resultado == 'BANKER':
                features.extend([1, 0])
            elif resultado == 'PLAYER':
                features.extend([0, 1])
            else:
                features.extend([0, 0])
        while len(features) < 40:
            features.extend([0, 0])
        features.append(self.tendencias['curta'].get('banker_pct', 0) / 100)
        features.append(self.tendencias['curta'].get('player_pct', 0) / 100)
        features.append(self.tendencias['longa'].get('banker_pct', 0) / 100)
        features.append(self.tendencias['longa'].get('player_pct', 0) / 100)
        streak = self._calcular_streak(historico)
        features.append(streak / 10)
        features.append(cache.get('indice_confianca', 50) / 100)
        features.append(confianca / 100)
        while len(features) < 60:
            features.append(0)
        return torch.FloatTensor(features).unsqueeze(0).to(DEVICE) if TORCH_AVAILABLE else None
    
    def _calcular_streak(self, historico):
        streak = 0
        for rodada in historico:
            if rodada.get('resultado') != 'TIE':
                streak += 1
            else:
                break
        return streak
    
    def decidir_aposta(self, historico, previsao, confianca):
        if len(historico) < 30:
            return {'apostar': False, 'motivo': 'historico_insuficiente'}
        
        self.atualizar_janelas(historico)
        
        if confianca >= self.limiar_base:
            curta = self.tendencias['curta']
            longa = self.tendencias['longa']
            
            if curta.get('banker_pct', 0) > 55 and longa.get('banker_pct', 0) > 52:
                return {'apostar': True, 'previsao': 'BANKER', 'confianca': confianca, 'motivo': 'consistencia_banker'}
            elif curta.get('player_pct', 0) > 55 and longa.get('player_pct', 0) > 52:
                return {'apostar': True, 'previsao': 'PLAYER', 'confianca': confianca, 'motivo': 'consistencia_player'}
            
            if self.rede_decisao and TORCH_AVAILABLE:
                try:
                    features = self._extrair_features(historico, previsao, confianca)
                    with torch.no_grad():
                        output = self.rede_decisao(features)
                        prob_apostar = output[0][0].item()
                    if prob_apostar > 0.6:
                        return {'apostar': True, 'previsao': previsao, 'confianca': confianca, 'motivo': 'rede_neural'}
                except Exception:
                    pass
            
            return {'apostar': True, 'previsao': previsao, 'confianca': confianca, 'motivo': 'confianca_alta'}
        
        return {'apostar': False, 'motivo': f'confianca_baixa_{confianca}'}
    
    def registrar_resultado(self, apostou, previsao, resultado_real, confianca, motivo):
        if apostou:
            acertou = (previsao == resultado_real)
            self.total_apostas += 1
            if acertou:
                self.acertos_apostas += 1
    
    def get_stats(self):
        precisao = (self.acertos_apostas / max(self.total_apostas, 1)) * 100
        return {
            'total_apostas': self.total_apostas,
            'acertos': self.acertos_apostas,
            'precisao': round(precisao, 1),
            'limiar': self.limiar_base,
            'tendencias': {
                'curta': round(self.tendencias['curta'].get('banker_pct', 0), 1),
                'longa': round(self.tendencias['longa'].get('banker_pct', 0), 1)
            }
        }


# =============================================================================
# 16. SISTEMA DE AGENTES INFINITOS (PRINCIPAL)
# =============================================================================

class SistemaAgentesInfinitos:
    def __init__(self):
        self.fabrica = FabricaAgentes()
        self.indicadores = IndicadoresBase()
        self.memoria_erros = MemoriaDeErros()
        self.votacao = VotacaoInteligente()
        self.mapa_mental = MapaMental()
        self.simulador = SimuladorCenarios(self.indicadores)
        self.detector_72 = DetectorPadrao72()
        self.curto_prazo = SistemaCurtoPrazo()
        self.estrategia_surto = EstrategiaSurto()
        self.ultra_precisao = SistemaUltraPrecisao()
        
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
            ('streak_4_player', ['PLAYER', 'PLAYER', 'PLAYER', 'PLAYER'], 'BANKER'),
            ('streak_4_banker', ['BANKER', 'BANKER', 'BANKER', 'BANKER'], 'PLAYER'),
            ('tie_6_player', ['TIE'], 'PLAYER'),
            ('duplo_tie_72', ['TIE', 'TIE'], 'BANKER'),
            ('alternancia_banker', ['PLAYER', 'BANKER'], 'PLAYER'),
            ('alternancia_player', ['BANKER', 'PLAYER'], 'BANKER'),
            ('repeticao_banker', ['BANKER', 'BANKER'], 'BANKER'),
            ('repeticao_player', ['PLAYER', 'PLAYER'], 'PLAYER'),
            ('delta_correcao_pos', ['PLAYER', 'PLAYER', 'PLAYER', 'PLAYER'], 'BANKER'),
            ('delta_correcao_neg', ['BANKER', 'BANKER', 'BANKER', 'BANKER'], 'PLAYER')
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
    
    def _detectar_padroes_indicadores(self, historico: List[dict]) -> List[dict]:
        """Detecta padrões usando os indicadores descobertos"""
        padroes = []
        
        if len(historico) < 30:
            return padroes
        
        # 1. Streak reversal
        streak = 0
        ultimo = None
        for r in historico[:10]:
            if r.get('resultado') != 'TIE':
                if ultimo is None:
                    streak = 1
                    ultimo = r['resultado']
                elif r['resultado'] == ultimo:
                    streak += 1
                else:
                    break
        
        if streak >= 3 and ultimo:
            padroes.append({
                'padrao': f'streak_{streak}_reversao',
                'previsao': 'BANKER' if ultimo == 'PLAYER' else 'PLAYER',
                'confianca': min(95, 70 + (streak - 2) * 5)
            })
        
        # 2. Delta correction
        delta = self._calcular_delta(historico)
        if abs(delta) >= self.indicadores.LIMITE_CORRECAO_GARANTIDA:
            padroes.append({
                'padrao': 'delta_correcao',
                'previsao': 'BANKER' if delta > 0 else 'PLAYER',
                'confianca': 95
            })
        elif abs(delta) >= self.indicadores.LIMITE_CORRECAO_INICIO:
            confianca = 70 + (abs(delta) - 15) * 2
            padroes.append({
                'padrao': 'delta_correcao',
                'previsao': 'BANKER' if delta > 0 else 'PLAYER',
                'confianca': min(90, confianca)
            })
        
        # 3. Tie 6 -> Player
        if historico and historico[0].get('resultado') == 'TIE' and \
           historico[0].get('player_score') == 6 and historico[0].get('banker_score') == 6:
            padroes.append({
                'padrao': 'tie_6_player',
                'previsao': 'PLAYER',
                'confianca': 95
            })
        
        # 4. Duplo Tie 7:2
        if len(historico) >= 2 and historico[0].get('resultado') == 'TIE' and historico[1].get('resultado') == 'TIE':
            padroes.append({
                'padrao': 'duplo_tie_72',
                'previsao': 'BANKER',
                'confianca': 77
            })
        
        # 5. Vibração TIE
        if historico:
            diferenca = abs(historico[0].get('player_score', 0) - historico[0].get('banker_score', 0))
            if diferenca == 1 and random.random() < self.indicadores.VIBRACAO_DIFERENCA_1:
                padroes.append({
                    'padrao': 'vibracao_tie',
                    'previsao': 'TIE',
                    'confianca': 60
                })
        
        # 6. Alternância
        ultimos = [r.get('resultado') for r in historico[:5] if r.get('resultado') != 'TIE']
        if len(ultimos) >= 2 and ultimos[0] != ultimos[1]:
            padroes.append({
                'padrao': 'alternancia',
                'previsao': 'BANKER' if ultimos[0] == 'PLAYER' else 'PLAYER',
                'confianca': 60
            })
        elif len(ultimos) >= 2 and ultimos[0] == ultimos[1]:
            padroes.append({
                'padrao': 'repeticao',
                'previsao': ultimos[0],
                'confianca': 40
            })
        
        return padroes
    
    def _calcular_delta(self, historico: List[dict]) -> int:
        player = sum(1 for r in historico[:100] if r.get('resultado') == 'PLAYER')
        banker = sum(1 for r in historico[:100] if r.get('resultado') == 'BANKER')
        return player - banker
    
    def _coletar_previsoes_agentes(self, historico: List[dict]) -> List[Tuple[str, float, str, str]]:
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
    
    def _consultar_mapa_mental(self, historico: List[dict]) -> Optional[CelulaMemoria]:
        contexto = [r.get('resultado') for r in historico[:10] if r.get('resultado') != 'TIE'][:5]
        return self.mapa_mental.consultar(contexto)
    
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
        
        cache['padroes_descobertos'].append({
            'padrao': padrao,
            'contexto': contexto,
            'previsao': previsao,
            'agentes': len(novos_agentes),
            'timestamp': datetime.now().isoformat()
        })
    
    def prever(self, historico: List[dict]) -> dict:
        if len(historico) < 30:
            return {'previsao': 'AGUARDANDO', 'confianca': 0, 'modo': 'INICIALIZACAO'}
        
        self.ultimo_contexto = historico[:20]
        
        # 1. Coletar previsões dos agentes
        previsoes_agentes = self._coletar_previsoes_agentes(historico)
        self.ultimos_agentes = [p[2] for p in previsoes_agentes]
        
        # 2. Coletar previsões dos indicadores
        previsoes_indicadores = self._detectar_padroes_indicadores(historico)
        
        # 3. Consultar mapa mental
        memoria = self._consultar_mapa_mental(historico)
        if memoria:
            previsoes_indicadores.append({
                'padrao': f'memoria_{memoria.padrao}',
                'previsao': memoria.previsao,
                'confianca': memoria.confianca * 100
            })
        
        # 4. Verificar detector 7:2
        padrao_72 = self.detector_72.analisar(historico)
        if padrao_72:
            previsoes_indicadores.append({
                'padrao': f'padrao_72_{padrao_72["tipo"]}',
                'previsao': padrao_72['previsao'],
                'confianca': padrao_72['confianca']
            })
        
        # 5. Verificar curto prazo
        previsao_cp = self.curto_prazo.processar_rodada(historico)
        if previsao_cp and previsao_cp.get('ultimas_5'):
            surto = self.estrategia_surto.analisar_ultimas_5(historico[:5])
            if surto and surto['confianca'] > 70:
                previsao_cp['previsao'] = surto['previsao']
                previsao_cp['confianca'] = surto['confianca']
            previsoes_indicadores.append({
                'padrao': 'curto_prazo',
                'previsao': previsao_cp['previsao'],
                'confianca': previsao_cp['confianca']
            })
        
        # 6. Combinar todas as previsões
        todas_previsoes = []
        
        for p in previsoes_agentes:
            todas_previsoes.append({
                'previsao': p[0],
                'confianca': p[1] * 100,
                'padrao': p[3],
                'peso': 1.0
            })
        
        for p in previsoes_indicadores:
            todas_previsoes.append({
                'previsao': p['previsao'],
                'confianca': p['confianca'],
                'padrao': p['padrao'],
                'peso': 0.8
            })
        
        if not todas_previsoes:
            # Fallback baseado em tendência
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
        
        # Votação com pesos
        votos = {'BANKER': 0, 'PLAYER': 0, 'TIE': 0}
        for p in todas_previsoes:
            peso = p['peso'] * self.votacao.pesos_padroes.get(p['padrao'], 0.5)
            votos[p['previsao']] += (p['confianca'] / 100) * peso
        
        previsao_final = max(votos, key=votos.get)
        total_votos = sum(votos.values())
        confianca_final = (votos[previsao_final] / total_votos) * 100 if total_votos > 0 else 50
        
        self.ultima_previsao = previsao_final
        
        return {
            'previsao': previsao_final,
            'simbolo': '🔴' if previsao_final == 'BANKER' else '🔵',
            'confianca': round(confianca_final),
            'modo': 'AGENTES_INFINITOS',
            'agentes_usados': len(previsoes_agentes),
            'total_agentes': cache['contador_agentes'],
            'padroes': list(set([p['padrao'] for p in todas_previsoes]))[:5],
            'indicadores_usados': len(previsoes_indicadores)
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
        
        # Atualizar agentes
        for agente_id in self.ultimos_agentes:
            with cache['lock_agentes']:
                if agente_id in cache['todos_agentes']:
                    cache['todos_agentes'][agente_id].aprender(resultado_real, acertou)
        
        # Atualizar memória de erros
        if not acertou and self.ultimos_agentes:
            for agente_id in self.ultimos_agentes[:3]:
                with cache['lock_agentes']:
                    if agente_id in cache['todos_agentes']:
                        self.memoria_erros.registrar_erro({
                            'padrao': cache['todos_agentes'][agente_id].padrao,
                            'previsao': self.ultima_previsao,
                            'real': resultado_real
                        })
        
        # Ajustar pesos baseado em erros
        ajustes = self.memoria_erros.sugerir_ajustes()
        if ajustes:
            self.votacao.aplicar_ajustes(ajustes)
        
        # Registrar no curto prazo
        self.curto_prazo.registrar_resultado(self.ultima_previsao, resultado_real, acertou)
        
        # Detectar novo padrão
        if acertou:
            novo_padrao = self._detectar_novo_padrao(self.ultimo_contexto, acertou)
            if novo_padrao:
                self._criar_agentes_novo_padrao(*novo_padrao)
        
        # Limpar agentes fracos a cada 100 previsões
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
    
    def treinar_por_simulacao(self, num_episodios=10, rodadas_por_episodio=100):
        print(f"\n🐟 TREINANDO POR SIMULAÇÃO...")
        print(f"   Episódios: {num_episodios} | Rodadas: {rodadas_por_episodio}")
        
        for ep in range(num_episodios):
            episodio = self.simulador.gerar_episodio(rodadas_por_episodio)
            acertos_ep = 0
            
            for contexto, resultado in episodio:
                previsao = self.prever(contexto)
                if previsao['previsao'] != 'AGUARDANDO':
                    acertou = (previsao['previsao'] == resultado)
                    if acertou:
                        acertos_ep += 1
                    self.aprender(resultado)
            
            precisao_ep = (acertos_ep / rodadas_por_episodio) * 100
            print(f"   Episódio {ep+1}: {acertos_ep}/{rodadas_por_episodio} ({precisao_ep:.1f}%)")
        
        print(f"\n✅ TREINAMENTO CONCLUÍDO!")
        print(f"   Precisão total: {(self.acertos/self.total_previsoes*100):.1f}%")
        print(f"   Memórias criadas: {self.mapa_mental.get_stats()['total_celulas']}")
    
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
            'melhores_agentes': melhores[:50],
            'fabrica': self.fabrica.get_stats(),
            'padroes_descobertos': len(cache['padroes_descobertos']),
            'memoria_erros': self.memoria_erros.get_stats()[:5],
            'votacao': self.votacao.get_stats(),
            'mapa_mental': self.mapa_mental.get_stats(),
            'curto_prazo': self.curto_prazo.get_stats(),
            'detector_72': self.detector_72.get_stats()
        }
    
    def salvar(self, arquivo: str = 'sistema_agentes.pkl'):
        with cache['lock_agentes']:
            estado = {
                'total_previsoes': self.total_previsoes,
                'acertos': self.acertos,
                'erros': self.erros,
                'agentes': {aid: a.to_dict() for aid, a in cache['todos_agentes'].items()},
                'contador_agentes': cache['contador_agentes'],
                'fabrica_total': self.fabrica.total_criados,
                'padroes_descobertos': cache['padroes_descobertos']
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
            cache['padroes_descobertos'] = estado.get('padroes_descobertos', [])
            
            agentes_dict = estado.get('agentes', {})
            for agente_id, dados in agentes_dict.items():
                tipo = dados.get('tipo', 'NORMAL')
                if tipo == 'TURBINADO':
                    agente = AgenteTurbinado(agente_id, dados['nome'], dados['padrao'], dados['contexto'], dados['previsao'])
                elif tipo == 'PARALELO':
                    agente = AgenteParalelo(agente_id, dados['nome'], dados['padrao'], dados['contexto'], dados['previsao'])
                else:
                    agente = AgenteBase(agente_id, dados['nome'], dados['padrao'], dados['contexto'], dados['previsao'])
                
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
# 17. FUNÇÕES DO BANCO DE DADOS
# =============================================================================

def get_db_connection():
    try:
        conn = pg8000.connect(user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT, database=DB_NAME, ssl_context=SSL_CONTEXT, timeout=30)
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
        cur.execute('''
            CREATE TABLE IF NOT EXISTS rodadas (
                id TEXT PRIMARY KEY,
                data_hora TIMESTAMPTZ,
                player_score INTEGER,
                banker_score INTEGER,
                resultado TEXT,
                fonte TEXT
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS historico_previsoes (
                id SERIAL PRIMARY KEY,
                data_hora TIMESTAMPTZ DEFAULT NOW(),
                previsao TEXT,
                confianca INTEGER,
                resultado_real TEXT,
                acertou BOOLEAN,
                modo TEXT,
                agentes_usados INTEGER
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS analise_erros (
                id SERIAL PRIMARY KEY,
                data_hora TIMESTAMPTZ DEFAULT NOW(),
                previsao_feita TEXT,
                resultado_real TEXT,
                confianca INTEGER,
                causa_erro TEXT,
                acertou BOOLEAN
            )
        ''')
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

def salvar_previsao(previsao, resultado_real, acertou, modo, agentes_usados):
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute('INSERT INTO historico_previsoes (previsao, confianca, resultado_real, acertou, modo, agentes_usados) VALUES (%s, %s, %s, %s, %s, %s)',
                   (previsao['previsao'], previsao['confianca'], resultado_real, acertou, modo, agentes_usados))
        conn.commit()
        cur.close()
        conn.close()
        return True
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

def calcular_precisao():
    total = cache['estatisticas']['total_previsoes']
    return round((cache['estatisticas']['acertos'] / total) * 100) if total > 0 else 0


# =============================================================================
# 18. COLETA DE DADOS (API LATEST)
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
                print(f"\n📡 LATEST: {player_score} vs {banker_score} - {resultado}")
                return rodada
        else:
            if fonte_ativa == 'latest':
                falhas_latest += 1
                fontes_status['latest']['falhas'] += 1
            return None
    except Exception as e:
        if fonte_ativa == 'latest':
            falhas_latest += 1
            fontes_status['latest']['falhas'] += 1
        return None

def loop_latest():
    print("📡 Coletor LATEST iniciado")
    while True:
        try:
            rodada = buscar_latest()
            if rodada:
                fila_rodadas.append(rodada)
            time.sleep(INTERVALO_LATEST)
        except Exception as e:
            print(f"❌ Erro no loop LATEST: {e}")
            time.sleep(INTERVALO_LATEST)


# =============================================================================
# 19. PROCESSADOR DA FILA
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
                        cache['historico_rodadas'].append(rodada)  # Adicionado ao cache
                        cache['ultimo_resultado_real'] = rodada['resultado']
                        
                        # Verificar previsão anterior
                        if ultima_previsao:
                            resultado_real = rodada['resultado']
                            if resultado_real != 'TIE':
                                acertou = (ultima_previsao['previsao'] == resultado_real)
                                cache['estatisticas']['total_previsoes'] += 1
                                if acertou:
                                    cache['estatisticas']['acertos'] += 1
                                else:
                                    cache['estatisticas']['erros'] += 1
                                
                                # Salvar previsão
                                salvar_previsao(ultima_previsao, resultado_real, acertou, 
                                              ultima_previsao.get('modo', 'AGENTES_INFINITOS'),
                                              ultima_previsao.get('agentes_usados', 0))
                                
                                # Aprender
                                sistema.aprender(resultado_real)
                                
                                print(f"\n📊 PREVISÃO: {ultima_previsao['previsao']} | Real: {resultado_real} | {'✅' if acertou else '❌'} | Precisão: {calcular_precisao()}%")
                                print(f"   Agentes usados: {ultima_previsao.get('agentes_usados', 0)} | Total: {ultima_previsao.get('total_agentes', 0)}")
                            
                            ultima_previsao = None
                        
                        # Fazer nova previsão
                        if len(historico_buffer) >= 30 and modo_atual == "ATIVO" and not ultima_previsao:
                            historico_completo = [{'resultado': r['resultado'], 'player_score': r['player_score'], 'banker_score': r['banker_score']} for r in historico_buffer[-50:]]
                            
                            previsao = sistema.prever(historico_completo)
                            if previsao['previsao'] != 'AGUARDANDO':
                                ultima_previsao = previsao
                                cache['ultima_previsao'] = ultima_previsao
                                cache['leves']['previsao'] = ultima_previsao
                                print(f"\n🔮 PREVISÃO: {ultima_previsao['previsao']} com {ultima_previsao['confianca']}% (usando {ultima_previsao.get('agentes_usados', 0)} agentes)")
                    
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
        except Exception as e:
            print(f"❌ Erro loop pesado: {e}")


# =============================================================================
# 20. ROTAS DA API
# =============================================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health', methods=['GET'])
def health_urgente():
    total_agentes = len(cache.get('todos_agentes', {}))
    agentes_ativos = 0
    for a in cache.get('todos_agentes', {}).values():
        if hasattr(a, 'peso') and a.peso > 0.5:
            agentes_ativos += 1
    return jsonify({
        'status': 'ok',
        'mensagem': 'Sistema de Agentes Infinitos',
        'timestamp': time.time(),
        'versao': 'Agentes_Infinitos_v2.0',
        'total_agentes': total_agentes,
        'agentes_ativos': agentes_ativos,
        'pytorch_disponivel': TORCH_AVAILABLE,
        'device': DEVICE_STR,  # Usar a string em vez do objeto
        'precisao': calcular_precisao()
    })

@app.route('/api/stats')
def api_stats():
    stats_sistema = cache['sistema'].get_stats() if cache.get('sistema') else None
    return jsonify({
        'total_rodadas': cache['leves']['total_rodadas'],
        'ultimas_20': cache['leves']['ultimas_20'],
        'previsao': cache['leves']['previsao'],
        'periodos': cache['pesados']['periodos'],
        'estatisticas': cache['estatisticas'],
        'sistema_agentes': stats_sistema,
        'indice_confianca': cache.get('indice_confianca', 50),
        'padroes_descobertos': cache.get('padroes_descobertos', [])
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

@app.route('/api/aprendizado')
def api_aprendizado():
    if not cache.get('sistema'):
        return jsonify({'erro': 'Sistema não inicializado'})
    
    sistema = cache['sistema']
    stats = sistema.get_stats()
    
    return jsonify({
        'geracao': stats['total_previsoes'] // 100,
        'total_previsoes': stats['total_previsoes'],
        'acertos': stats['acertos'],
        'erros': stats['erros'],
        'precisao': stats['precisao'],
        'total_agentes': stats['total_agentes'],
        'agentes_por_tipo': stats['agentes_por_tipo'],
        'melhores_agentes': stats['melhores_agentes'][:10],
        'memoria_erros': stats.get('memoria_erros', []),
        'votacao': stats.get('votacao', {}),
        'mapa_mental': stats.get('mapa_mental', {})
    })

@app.route('/api/curto-prazo')
def api_curto_prazo():
    if not cache.get('sistema'):
        return jsonify({'status': 'inativo'})
    
    sistema = cache['sistema']
    stats = sistema.curto_prazo.get_stats()
    
    ultimos_ciclos = sistema.curto_prazo.ciclos_completados[-5:] if sistema.curto_prazo.ciclos_completados else []
    
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

@app.route('/api/detector-72')
def api_detector_72():
    if not cache.get('sistema'):
        return jsonify({'status': 'inativo'})
    
    detector = cache['sistema'].detector_72
    return jsonify({
        'status': 'ativo',
        'stats': detector.get_stats()
    })

@app.route('/api/ultra-precisao')
def api_ultra_precisao():
    if not cache.get('sistema'):
        return jsonify({'status': 'inativo'})
    
    ultra = cache['sistema'].ultra_precisao
    return jsonify({
        'status': 'ativo',
        'stats': ultra.get_stats()
    })

@app.route('/api/analise-erros')
def api_analise_erros():
    if not cache.get('sistema'):
        return jsonify({'erro': 'Sistema não inicializado'})
    
    sistema = cache['sistema']
    stats = sistema.memoria_erros.get_stats()
    
    return jsonify({
        'total_erros': len(sistema.memoria_erros.erros),
        'erros_por_padrao': stats,
        'padroes_problematicos': list(sistema.memoria_erros.padroes_que_mais_erram.keys())
    })

@app.route('/api/treinar', methods=['POST'])
def api_treinar():
    if not cache.get('sistema'):
        return jsonify({'erro': 'Sistema não inicializado'})
    
    data = request.get_json() or {}
    episodios = data.get('episodios', 5)
    rodadas = data.get('rodadas', 100)
    
    sistema = cache['sistema']
    sistema.treinar_por_simulacao(episodios, rodadas)
    sistema.salvar()
    
    return jsonify({
        'status': 'treinado',
        'stats': sistema.get_stats()
    })

@app.route('/api/criar_agente', methods=['POST'])
def api_criar_agente():
    if not cache.get('sistema'):
        return jsonify({'erro': 'Sistema não inicializado'})
    
    data = request.get_json() or {}
    padrao = data.get('padrao', 'manual_custom')
    contexto = data.get('contexto', ['PLAYER', 'PLAYER', 'PLAYER'])
    previsao = data.get('previsao', 'BANKER')
    tipo = data.get('tipo', 'TURBINADO')
    
    sistema = cache['sistema']
    agentes = sistema.fabrica.criar_agentes_padrao(padrao, contexto, previsao, 1)
    
    if agentes:
        agente = agentes[0]
        with cache['lock_agentes']:
            cache['todos_agentes'][agente.id] = agente
            if padrao not in cache['agentes_por_padrao']:
                cache['agentes_por_padrao'][padrao] = []
            cache['agentes_por_padrao'][padrao].append(agente.id)
            ch = sistema._hash_contexto(contexto)
            if ch not in cache['agentes_por_contexto']:
                cache['agentes_por_contexto'][ch] = []
            cache['agentes_por_contexto'][ch].append(agente.id)
        
        cache['contador_agentes'] = len(cache['todos_agentes'])
        
        return jsonify({'status': 'criado', 'agente': agente.to_dict()})
    
    return jsonify({'status': 'erro', 'msg': 'Falha ao criar agente'}), 400

@app.route('/api/corrigir-agora')
def api_corrigir_agora():
    if not cache.get('sistema'):
        return jsonify({'erro': 'Sistema não inicializado'})
    
    sistema = cache['sistema']
    sistema._limpar_agentes_fracos()
    
    return jsonify({
        'status': 'correcao_aplicada',
        'agentes_restantes': cache['contador_agentes']
    })

@app.route('/api/manipulacao')
def api_manipulacao():
    """Detecção de manipulação"""
    indicadores = IndicadoresBase()
    
    ultimas_rodadas = list(cache['historico_rodadas']) if cache.get('historico_rodadas') else []
    streak = 0
    ultimo = None
    for r in ultimas_rodadas[:50]:
        if r.get('resultado') != 'TIE':
            if ultimo is None:
                streak = 1
                ultimo = r['resultado']
            elif r['resultado'] == ultimo:
                streak += 1
            else:
                break
    
    reversao_detectada = streak >= 3
    
    return jsonify({
        'indice_manipulacao': 50 if not reversao_detectada else 75,
        'streak_atual': streak,
        'ultimo_resultado': ultimo,
        'reversao_detectada': reversao_detectada
    })

@app.route('/api/padrao-7x2')
def api_padrao_7x2():
    if not cache.get('sistema'):
        return jsonify({'status': 'inativo'})
    
    detector = cache['sistema'].detector_72
    return jsonify({
        'padrao': 'DUPLO TIE + 7:2',
        'total_ocorrencias': detector.total_deteccoes,
        'status': 'ativo' if detector.duplo_tie_detectado else 'analisando',
        'probabilidade_banker': 77,
        'duplo_tie_detectado': detector.duplo_tie_detectado
    })

@app.route('/api/neuro-status')
def api_neuro_status():
    if not cache.get('sistema'):
        return jsonify({'status': 'inativo'})
    
    sistema = cache['sistema']
    stats = sistema.get_stats()
    
    return jsonify({
        'geracao': stats['total_previsoes'] // 100,
        'total_agentes': stats['total_agentes'],
        'agentes_ativos': len([a for a in stats['melhores_agentes'] if a['precisao'] > 50]),
        'agentes_por_tipo': stats['agentes_por_tipo'],
        'saude_media': 85.0,
        'evolucao_ativa': True,
        'pytorch': TORCH_AVAILABLE,
        'device': DEVICE_STR
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
# 21. MAIN
# =============================================================================

if __name__ == "__main__":
    print("="*80)
    print("🐟 BACBO PREDICTOR - AGENTES INFINITOS (VERSÃO COMPLETA)")
    print("="*80)
    print("   ✅ TODO NOVO PADRÃO = NOVO AGENTE RL")
    print("   ✅ AGENTES TURBINADOS (REDES NEURAIS)")
    print("   ✅ AGENTES PARALELOS (PROCESSAMENTO EM MASSA)")
    print("   ✅ SEM LIMITE DE AGENTES")
    print("   ✅ MAPA MENTAL EXPANSÍVEL")
    print("   ✅ MEMÓRIA DE ERROS")
    print("   ✅ VOTAÇÃO INTELIGENTE")
    print("   ✅ SIMULADOR DE CENÁRIOS")
    print("   ✅ DETECTOR 7:2")
    print("   ✅ SISTEMA CURTO PRAZO")
    print("   ✅ ESTRATÉGIA DE SURTO")
    print("   ✅ ULTRA PRECISÃO")
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
    cache['historico_rodadas'] = deque(maxlen=500)
    
    # Mostrar estatísticas iniciais
    stats = sistema.get_stats()
    print(f"\n📊 SISTEMA INICIALIZADO:")
    print(f"   Agentes: {stats['total_agentes']}")
    print(f"   Agentes por tipo: {stats['agentes_por_tipo']}")
    print(f"   PyTorch: {'✅ Disponível' if TORCH_AVAILABLE else '❌ Modo fallback'}")
    print(f"   Precisão atual: {stats['precisao']}%")
    
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
    print("   /api/aprendizado - Aprendizado")
    print("   /api/curto-prazo - Curto prazo")
    print("   /api/detector-72 - Detector 7:2")
    print("   /api/ultra-precisao - Ultra precisão")
    print("   /api/analise-erros - Análise de erros")
    print("   /api/neuro-status - Neuro status")
    print("   /api/manipulacao - Manipulação")
    print("   /api/padrao-7x2 - Padrão 7:2")
    print("   /api/corrigir-agora - Corrigir agentes")
    print("   /api/treinar - Treinar por simulação")
    print("   /api/criar_agente - Criar agente")
    print("   /api/tabela/<n> - Histórico")
    print("="*80)
    
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)