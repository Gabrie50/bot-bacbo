# =============================================================================
# main.py - BACBO PREDICTOR - MIRO FISH COM TODOS OS INDICADORES
# =============================================================================
# Mantém TODOS os indicadores que você descobriu + Aprendizado por Simulação
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
import traceback
import pickle
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

# =============================================================================
# 🔇 SILENCIAR AVISOS
# =============================================================================
import warnings
warnings.filterwarnings('ignore')
os.environ['PYTHONWARNINGS'] = 'ignore'

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
    return jsonify({
        'status': 'ok',
        'mensagem': 'Miro Fish com todos os indicadores',
        'timestamp': time.time(),
        'versao': 'MiroFish_Indicadores_Completos'
    })

@app.route('/', methods=['GET'])
def home_rapida():
    return jsonify({
        'nome': 'Bac Bo Predictor - Miro Fish',
        'versao': 'MiroFish_Indicadores_Completos',
        'status': 'online',
        'health': '/health',
        'stats': '/api/stats'
    })

# =============================================================================
# 🔧 PATCH DE COMPATIBILIDADE NUMPY
# =============================================================================
import numpy as np

print("\n" + "="*80)
print("🔧 INICIALIZANDO SISTEMA MIRO FISH - TODOS OS INDICADORES")
print("="*80)

try:
    print(f"📊 NumPy: {np.__version__}")
    np.seterr(all='ignore')
    print("✅ NumPy configurado")
except Exception as e:
    print(f"⚠️ Erro: {e}")

# =============================================================================
# CONFIGURAÇÕES DO BANCO
# =============================================================================
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://neondb_owner:npg_YfkiR2n3SQzs@ep-shy-unit-adoc8wwh-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require")

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
    'Cache-Control': 'no-cache'
}

INTERVALO_LATEST = 0.3
PORT = int(os.environ.get("PORT", 5000))

# =============================================================================
# CONTROLE DE FALHAS
# =============================================================================
falhas_latest = 0
LIMITE_FALHAS = 3

fontes_status = {'latest': {'status': 'ativo', 'total': 0, 'falhas': 0}}
fonte_ativa = 'latest'

# =============================================================================
# FILA DE PROCESSAMENTO
# =============================================================================
fila_rodadas = deque(maxlen=500)
ultimo_id_latest = None

cache = {
    'leves': {'ultimas_50': [], 'ultimas_20': [], 'total_rodadas': 0, 'ultima_atualizacao': None, 'previsao': None},
    'pesados': {'periodos': {}, 'ultima_atualizacao': None},
    'estatisticas': {'total_previsoes': 0, 'acertos': 0, 'erros': 0, 'ultimas_20_previsoes': []},
    'ultima_previsao': None,
    'ultimo_resultado_real': None,
    'indice_confianca': 50,
    'agente_miro': None,           # AGENTE PRINCIPAL
    'simulador': None,             # SIMULADOR DE CENÁRIOS
    'memoria_erros': None,         # MEMÓRIA DE ERROS
    'votacao': None                # VOTAÇÃO INTELIGENTE
}

# =============================================================================
# 1. INDICADORES BASE (TODOS OS QUE VOCÊ DESCOBRIU)
# =============================================================================

class IndicadoresBase:
    """
    TODOS os indicadores que você descobriu no arquivo JSON
    """
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
        
        print("✅ Indicadores Base carregados da sua tese")
        self._mostrar_resumo()
    
    def _mostrar_resumo(self):
        print("\n" + "="*70)
        print("📊 INDICADORES DESCOBERTOS:")
        print("="*70)
        print(f"   🔴 Streak máximo PLAYER: {self.LIMITE_STREAK_PLAYER}")
        print(f"   🔵 Streak máximo BANKER: {self.LIMITE_STREAK_BANKER}")
        print(f"   🎯 Reversão após 3: {self.REVERSAO_APOS_3*100:.0f}%")
        print(f"   📈 Delta correção: ±{self.LIMITE_CORRECAO_INICIO} a ±{self.LIMITE_CORRECAO_GARANTIDA}")
        print(f"   🎲 Empate 6 → PLAYER: {self.TIE_6_PROXIMO_PLAYER*100:.0f}%")
        print(f"   🔄 Duplo TIE → BANKER: {self.DUPLO_TIE_BANKER_PCT*100:.0f}%")
        print(f"   🌊 Vibração (dif=1): {self.VIBRACAO_DIFERENCA_1*100:.0f}% vira TIE")
        print(f"   🔄 Alternância: {self.ALTERNANCIA_PCT*100:.0f}% | Repetição: {self.REPETICAO_PCT*100:.0f}%")
        print("="*70)


# =============================================================================
# 2. MEMÓRIA DE ERROS (Aprende com os erros)
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
# 3. VOTAÇÃO INTELIGENTE
# =============================================================================

class VotacaoInteligente:
    def __init__(self):
        self.pesos_padroes = {
            'streak_reversao': 0.75,
            'delta_correcao': 0.80,
            'tie_6_player': 0.95,
            'duplo_tie_72': 0.77,
            'vibracao_tie': 0.55,
            'alternancia': 0.60,
            'repeticao': 0.40
        }
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
        for p in previsoes:
            previsao = p['previsao']
            confianca = p['confianca'] / 100
            padrao = p.get('padrao', 'desconhecido')
            peso = self.pesos_padroes.get(padrao, 0.5)
            votos[previsao] += confianca * peso
        
        previsao_final = max(votos, key=votos.get)
        total_votos = sum(votos.values())
        confianca_final = (votos[previsao_final] / total_votos) * 100 if total_votos > 0 else 50
        
        self.confianca_media = self.confianca_media * 0.9 + confianca_final * 0.1
        return previsao_final, round(confianca_final)
    
    def get_stats(self):
        return {'pesos': self.pesos_padroes, 'confianca_media': round(self.confianca_media, 1)}


# =============================================================================
# 4. SIMULADOR DE CENÁRIOS (Baseado nos seus indicadores)
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
        """Gera a próxima rodada seguindo os padrões que você descobriu"""
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
        
        # Fallback
        return random.choice(['BANKER', 'PLAYER'])
    
    def gerar_episodio(self, num_rodadas=100):
        """Gera um episódio completo de treinamento"""
        episodio = []
        historico = []
        
        # Histórico inicial
        for _ in range(50):
            historico.append({
                'resultado': random.choice(['BANKER', 'PLAYER']),
                'player_score': random.randint(2, 12),
                'banker_score': random.randint(2, 12)
            })
        
        for _ in range(num_rodadas):
            resultado = self._gerar_proxima_rodada(historico)
            
            # Gerar scores compatíveis
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
# 5. MAPA MENTAL (MiRo Fish - Memória)
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
        precisao_media = sum(c.precisao for c in self.celulas.values()) / max(1, len(self.celulas))
        return {'total_celulas': len(self.celulas), 'precisao_media': round(precisao_media * 100, 1)}
    
    def salvar(self, arquivo='mapa_mental.pkl'):
        estado = {'proximo_id': self.proximo_id, 'celulas': {id: c for id, c in self.celulas.items()}}
        with open(arquivo, 'wb') as f:
            pickle.dump(estado, f)
    
    def carregar(self, arquivo='mapa_mental.pkl'):
        if not os.path.exists(arquivo):
            return False
        with open(arquivo, 'rb') as f:
            estado = pickle.load(f)
        self.proximo_id = estado['proximo_id']
        self.celulas = estado['celulas']
        self.indice_por_contexto = {}
        for cell in self.celulas.values():
            ch = self._hash_contexto(cell.contexto)
            if ch not in self.indice_por_contexto:
                self.indice_por_contexto[ch] = []
            self.indice_por_contexto[ch].append(cell.id)
        return True


# =============================================================================
# 6. AGENTE MIRO FISH COMPLETO (Com todos os indicadores)
# =============================================================================

class AgenteMiroFishCompleto:
    def __init__(self, nome="MiroFish_Master"):
        self.nome = nome
        self.ind = IndicadoresBase()
        self.memoria_erros = MemoriaDeErros()
        self.votacao = VotacaoInteligente()
        self.mapa_mental = MapaMental()
        self.simulador = SimuladorCenarios(self.ind)
        
        self.total_previsoes = 0
        self.acertos = 0
        self.erros = 0
        self.recompensa_total = 0.0
        self.ultimo_contexto = []
        self.ultima_previsao = None
        self.ultimos_padroes = []
        self.ultima_memoria = None
        
        print(f"\n{'='*70}")
        print(f"🐟 AGENTE MIRO FISH COMPLETO: {nome}")
        print(f"{'='*70}")
        print(f"   📊 Indicadores: 10 categorias")
        print(f"   💾 Memória de erros: 500 posições")
        print(f"   🗳️ Padrões monitorados: {len(self.votacao.pesos_padroes)}")
        print(f"   🗺️ Mapa mental: {self.mapa_mental.capacidade} células")
        print(f"{'='*70}\n")
    
    # =========================================================================
    # DETECTORES DE PADRÕES (TODOS OS QUE VOCÊ DESCOBRIU)
    # =========================================================================
    
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
        return streak, ultimo
    
    def _calcular_delta(self, historico):
        player = sum(1 for r in historico[:100] if r.get('resultado') == 'PLAYER')
        banker = sum(1 for r in historico[:100] if r.get('resultado') == 'BANKER')
        return player - banker
    
    def detectar_streak_reversao(self, historico):
        if len(historico) < 4:
            return None
        streak, ultimo = self._calcular_streak(historico)
        if streak >= 3 and ultimo:
            confianca = min(95, 70 + (streak - 2) * 5)
            return {
                'previsao': 'BANKER' if ultimo == 'PLAYER' else 'PLAYER',
                'confianca': confianca,
                'padrao': 'streak_reversao'
            }
        return None
    
    def detectar_delta_correcao(self, historico):
        if len(historico) < 50:
            return None
        delta = self._calcular_delta(historico)
        if abs(delta) >= self.ind.LIMITE_CORRECAO_GARANTIDA:
            return {'previsao': 'BANKER' if delta > 0 else 'PLAYER', 'confianca': 95, 'padrao': 'delta_correcao'}
        elif abs(delta) >= self.ind.LIMITE_CORRECAO_INICIO:
            confianca = 70 + (abs(delta) - 15) * 2
            return {'previsao': 'BANKER' if delta > 0 else 'PLAYER', 'confianca': min(90, confianca), 'padrao': 'delta_correcao'}
        return None
    
    def detectar_tie_6_player(self, historico):
        if not historico:
            return None
        ultimo = historico[0]
        if (ultimo.get('resultado') == 'TIE' and 
            ultimo.get('player_score') == 6 and 
            ultimo.get('banker_score') == 6):
            return {'previsao': 'PLAYER', 'confianca': 95, 'padrao': 'tie_6_player'}
        return None
    
    def detectar_duplo_tie_72(self, historico):
        if len(historico) < 2:
            return None
        for i in range(min(5, len(historico)-1)):
            if historico[i].get('resultado') == 'TIE' and historico[i+1].get('resultado') == 'TIE':
                return {'previsao': 'BANKER', 'confianca': 77, 'padrao': 'duplo_tie_72'}
        return None
    
    def detectar_vibracao_tie(self, historico):
        if not historico:
            return None
        ultimo = historico[0]
        diferenca = abs(ultimo.get('player_score', 0) - ultimo.get('banker_score', 0))
        if diferenca == 1 and random.random() < self.ind.VIBRACAO_DIFERENCA_1:
            return {'previsao': 'TIE', 'confianca': 60, 'padrao': 'vibracao_tie'}
        return None
    
    def detectar_alternancia(self, historico):
        ultimos = [r.get('resultado') for r in historico[:5] if r.get('resultado') != 'TIE']
        if len(ultimos) >= 2 and ultimos[0] != ultimos[1]:
            return {
                'previsao': 'BANKER' if ultimos[0] == 'PLAYER' else 'PLAYER',
                'confianca': 60,
                'padrao': 'alternancia'
            }
        return None
    
    def detectar_repeticao(self, historico):
        ultimos = [r.get('resultado') for r in historico[:5] if r.get('resultado') != 'TIE']
        if len(ultimos) >= 2 and ultimos[0] == ultimos[1]:
            return {'previsao': ultimos[0], 'confianca': 40, 'padrao': 'repeticao'}
        return None
    
    # =========================================================================
    # PREVISÃO PRINCIPAL
    # =========================================================================
    
    def prever(self, historico):
        if len(historico) < 30:
            return {'previsao': 'AGUARDANDO', 'confianca': 0, 'modo': 'INICIALIZACAO'}
        
        # Extrair contexto
        self.ultimo_contexto = [r.get('resultado') for r in historico[:10] if r.get('resultado') != 'TIE'][:5]
        
        # Detectar todos os padrões
        detectores = [
            self.detectar_streak_reversao,
            self.detectar_delta_correcao,
            self.detectar_tie_6_player,
            self.detectar_duplo_tie_72,
            self.detectar_vibracao_tie,
            self.detectar_alternancia,
            self.detectar_repeticao
        ]
        
        previsoes = []
        for detector in detectores:
            p = detector(historico)
            if p:
                previsoes.append(p)
                print(f"   🔍 {p['padrao']}: {p['previsao']} ({p['confianca']}%)")
        
        # Consultar mapa mental
        self.ultima_memoria = self.mapa_mental.consultar(self.ultimo_contexto)
        if self.ultima_memoria:
            previsoes.append({
                'previsao': self.ultima_memoria.previsao,
                'confianca': self.ultima_memoria.confianca * 100,
                'padrao': f"memoria_{self.ultima_memoria.padrao}"
            })
            print(f"   🧠 Memória: {self.ultima_memoria.previsao} (peso={self.ultima_memoria.peso:.2f})")
        
        # Se não detectou nada, fallback
        if not previsoes:
            ultimos = [r['resultado'] for r in historico[:20] if r.get('resultado') != 'TIE']
            if ultimos:
                previsao = 'BANKER' if ultimos.count('BANKER') > ultimos.count('PLAYER') else 'PLAYER'
                confianca = 55
            else:
                previsao = random.choice(['BANKER', 'PLAYER'])
                confianca = 50
            return {'previsao': previsao, 'simbolo': '🔴' if previsao == 'BANKER' else '🔵', 'confianca': confianca, 'modo': 'FALLBACK'}
        
        # Votação
        previsao_final, confianca_final = self.votacao.votar(previsoes)
        self.ultima_previsao = previsao_final
        self.ultimos_padroes = previsoes
        
        return {
            'previsao': previsao_final,
            'simbolo': '🔴' if previsao_final == 'BANKER' else '🔵',
            'confianca': confianca_final,
            'modo': 'MIRO_FISH_COMPLETO',
            'padroes': [p['padrao'] for p in previsoes[:5]]
        }
    
    # =========================================================================
    # APRENDIZADO POR REFORÇO
    # =========================================================================
    
    def aprender(self, resultado_real):
        if not self.ultima_previsao:
            return
        
        acertou = (self.ultima_previsao == resultado_real)
        recompensa = 1.0 if acertou else -1.0
        
        self.total_previsoes += 1
        if acertou:
            self.acertos += 1
        else:
            self.erros += 1
        self.recompensa_total += recompensa
        
        print(f"\n📚 APRENDENDO: {self.ultima_previsao} vs {resultado_real} → {'✅' if acertou else '❌'} (recompensa={recompensa:+.1f})")
        
        # Atualizar memória de erros
        for p in self.ultimos_padroes:
            padrao = p['padrao']
            if not acertou:
                self.memoria_erros.registrar_erro({'padrao': padrao, 'previsao': p['previsao'], 'real': resultado_real})
            else:
                self.memoria_erros.registrar_acerto(padrao)
        
        # Atualizar mapa mental
        if acertou and self.ultimos_padroes:
            melhor_padrao = self.ultimos_padroes[0]
            self.mapa_mental.adicionar_memoria(
                melhor_padrao['padrao'],
                self.ultimo_contexto,
                melhor_padrao['previsao']
            )
        
        # Atualizar memória existente
        if self.ultima_memoria:
            self.mapa_mental.atualizar_memoria(self.ultima_memoria.id, acertou)
        
        # Ajustar pesos baseado em erros
        ajustes = self.memoria_erros.sugerir_ajustes()
        if ajustes:
            self.votacao.aplicar_ajustes(ajustes)
            for padrao, ajuste in ajustes.items():
                print(f"   ⚙️ Ajuste: {padrao} → {ajuste['acao']}")
    
    # =========================================================================
    # TREINAMENTO POR SIMULAÇÃO
    # =========================================================================
    
    def treinar_por_simulacao(self, num_episodios=10, rodadas_por_episodio=100):
        print(f"\n🐟 TREINANDO {self.nome} POR SIMULAÇÃO...")
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
    
    # =========================================================================
    # PERSISTÊNCIA
    # =========================================================================
    
    def salvar(self):
        self.mapa_mental.salvar(f"{self.nome.lower()}_mapa.pkl")
        estado = {
            'total_previsoes': self.total_previsoes,
            'acertos': self.acertos,
            'erros': self.erros,
            'recompensa_total': self.recompensa_total,
            'pesos_padroes': self.votacao.pesos_padroes,
            'erros_por_padrao': self.memoria_erros.erros_por_padrao,
            'acertos_por_padrao': self.memoria_erros.acertos_por_padrao
        }
        with open(f"{self.nome.lower()}_estado.pkl", 'wb') as f:
            pickle.dump(estado, f)
        print(f"💾 {self.nome} salvo")
    
    def carregar(self):
        self.mapa_mental.carregar(f"{self.nome.lower()}_mapa.pkl")
        try:
            with open(f"{self.nome.lower()}_estado.pkl", 'rb') as f:
                estado = pickle.load(f)
            self.total_previsoes = estado.get('total_previsoes', 0)
            self.acertos = estado.get('acertos', 0)
            self.erros = estado.get('erros', 0)
            self.recompensa_total = estado.get('recompensa_total', 0)
            if 'pesos_padroes' in estado:
                for padrao, peso in estado['pesos_padroes'].items():
                    if padrao in self.votacao.pesos_padroes:
                        self.votacao.pesos_padroes[padrao] = peso
            self.memoria_erros.erros_por_padrao = estado.get('erros_por_padrao', {})
            self.memoria_erros.acertos_por_padrao = estado.get('acertos_por_padrao', {})
        except:
            pass
    
    def get_stats(self):
        precisao = (self.acertos / self.total_previsoes * 100) if self.total_previsoes > 0 else 0
        return {
            'nome': self.nome,
            'previsoes': self.total_previsoes,
            'acertos': self.acertos,
            'erros': self.erros,
            'precisao': round(precisao, 1),
            'recompensa': round(self.recompensa_total, 2),
            'votacao': self.votacao.get_stats(),
            'mapa_mental': self.mapa_mental.get_stats(),
            'erros_por_padrao': self.memoria_erros.get_stats()[:5]
        }


# =============================================================================
# 7. FUNÇÕES DO BANCO DE DADOS
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
        cur.execute('CREATE TABLE IF NOT EXISTS rodadas (id TEXT PRIMARY KEY, data_hora TIMESTAMPTZ, player_score INTEGER, banker_score INTEGER, resultado TEXT, fonte TEXT)')
        cur.execute('CREATE TABLE IF NOT EXISTS historico_previsoes (id SERIAL PRIMARY KEY, data_hora TIMESTAMPTZ DEFAULT NOW(), previsao TEXT, confianca INTEGER, resultado_real TEXT, acertou BOOLEAN, modo TEXT)')
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
        cur.execute('INSERT INTO rodadas (id, data_hora, player_score, banker_score, resultado, fonte) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING', (rodada['id'], rodada['data_hora'], rodada['player_score'], rodada['banker_score'], rodada['resultado'], fonte))
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

def salvar_previsao(previsao, resultado_real, acertou, modo):
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute('INSERT INTO historico_previsoes (previsao, confianca, resultado_real, acertou, modo) VALUES (%s, %s, %s, %s, %s)', (previsao['previsao'], previsao['confianca'], resultado_real, acertou, modo))
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
            resultado.append({'hora': brasilia.strftime('%H:%M:%S'), 'resultado': row[3], 'cor': '🔴' if row[3]=='BANKER' else '🔵', 'player': row[1], 'banker': row[2]})
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
    cache['pesados']['periodos'] = {'1h': contar_periodo(1), '6h': contar_periodo(6), '12h': contar_periodo(12), '24h': contar_periodo(24), '48h': contar_periodo(48), '72h': contar_periodo(72)}
    cache['pesados']['ultima_atualizacao'] = datetime.now(timezone.utc)

def calcular_precisao():
    total = cache['estatisticas']['total_previsoes']
    return round((cache['estatisticas']['acertos'] / total) * 100) if total > 0 else 0


# =============================================================================
# 8. COLETA DE DADOS (API LATEST)
# =============================================================================

def buscar_latest():
    global ultimo_id_latest, falhas_latest
    try:
        response = requests.get(LATEST_API_URL, headers=HEADERS, timeout=2)
        if response.status_code == 200:
            dados = response.json()
            novo_id = dados.get('id')
            data = dados.get('data', {})
            result = data.get('result', {})
            if novo_id and novo_id != ultimo_id_latest:
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
                rodada = {'id': novo_id, 'data_hora': datetime.now(timezone.utc), 'player_score': player_score, 'banker_score': banker_score, 'resultado': resultado}
                fontes_status['latest']['total'] += 1
                print(f"\n📡 LATEST: {player_score} vs {banker_score} - {resultado}")
                return rodada
        else:
            falhas_latest += 1
        return None
    except:
        falhas_latest += 1
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
# 9. PROCESSADOR DA FILA
# =============================================================================

def processar_fila():
    print("🚀 Processador Miro Fish iniciado...")
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
                                salvar_previsao(ultima_previsao, resultado_real, acertou, ultima_previsao.get('modo', 'MIRO_FISH'))
                                
                                # Agente aprende com o resultado
                                if cache.get('agente_miro'):
                                    cache['agente_miro'].aprender(resultado_real)
                                
                                print(f"\n📊 PREVISÃO: {ultima_previsao['previsao']} | Real: {resultado_real} | {'✅' if acertou else '❌'} | Precisão: {calcular_precisao()}%")
                            ultima_previsao = None
                        
                        # Fazer nova previsão
                        if len(historico_buffer) >= 30 and modo_atual == "ATIVO" and not ultima_previsao:
                            historico_completo = [{'resultado': r['resultado'], 'player_score': r['player_score'], 'banker_score': r['banker_score']} for r in historico_buffer[-50:]]
                            
                            if cache.get('agente_miro'):
                                previsao = cache['agente_miro'].prever(historico_completo)
                                if previsao['previsao'] != 'AGUARDANDO':
                                    ultima_previsao = previsao
                                    cache['ultima_previsao'] = ultima_previsao
                                    cache['leves']['previsao'] = ultima_previsao
                                    print(f"\n🔮 PREVISÃO: {ultima_previsao['previsao']} com {ultima_previsao['confianca']}%")
                    
                    cache['leves']['ultima_atualizacao'] = datetime.now(timezone.utc)
            
            time.sleep(0.01)
        except Exception as e:
            print(f"❌ Erro: {e}")
            time.sleep(0.1)

def loop_pesado():
    while True:
        time.sleep(300)
        try:
            atualizar_dados_pesados()
        except:
            pass


# =============================================================================
# 10. ROTAS DA API
# =============================================================================

@app.route('/api/stats')
def api_stats():
    stats_agente = cache['agente_miro'].get_stats() if cache.get('agente_miro') else None
    return jsonify({
        'total_rodadas': cache['leves']['total_rodadas'],
        'ultimas_20': cache['leves']['ultimas_20'],
        'previsao': cache['leves']['previsao'],
        'periodos': cache['pesados']['periodos'],
        'estatisticas': {
            'total_previsoes': cache['estatisticas']['total_previsoes'],
            'acertos': cache['estatisticas']['acertos'],
            'erros': cache['estatisticas']['erros'],
            'precisao': calcular_precisao()
        },
        'agente_miro': stats_agente
    })

@app.route('/api/treinar', methods=['POST'])
def api_treinar():
    if cache.get('agente_miro'):
        cache['agente_miro'].treinar_por_simulacao(5, 100)
        cache['agente_miro'].salvar()
        return jsonify({'status': 'treinado', 'stats': cache['agente_miro'].get_stats()})
    return jsonify({'status': 'erro', 'msg': 'Agente não inicializado'})

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
        resultado.append({'data': brasilia.strftime('%d/%m %H:%M:%S'), 'player': row[1], 'banker': row[2], 'resultado': row[3], 'cor': '🔴' if row[3]=='BANKER' else '🔵'})
    return jsonify(resultado)

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'rodadas': cache['leves']['total_rodadas'], 'precisao': calcular_precisao()})


# =============================================================================
# 11. MAIN
# =============================================================================

if __name__ == "__main__":
    print("="*80)
    print("🐟 BACBO PREDICTOR - MIRO FISH COM TODOS OS INDICADORES")
    print("="*80)
    
    # Inicializar banco
    init_db()
    atualizar_dados_leves()
    atualizar_dados_pesados()
    print(f"📊 {cache['leves']['total_rodadas']} rodadas no banco")
    
    # Criar agente Miro Fish completo
    print("\n🐟 CRIANDO AGENTE MIRO FISH COMPLETO...")
    agente = AgenteMiroFishCompleto(nome="MiroFish_Master")
    agente.carregar()
    cache['agente_miro'] = agente
    
    # Treinar por simulação
    print("\n🎯 TREINANDO AGENTE POR SIMULAÇÃO...")
    agente.treinar_por_simulacao(num_episodios=10, rodadas_por_episodio=100)
    agente.salvar()
    
    # Mostrar estatísticas
    stats = agente.get_stats()
    print(f"\n📊 AGENTE TREINADO:")
    print(f"   Previsões: {stats['previsoes']}")
    print(f"   Acertos: {stats['acertos']}")
    print(f"   Precisão: {stats['precisao']}%")
    print(f"   Recompensa: {stats['recompensa']}")
    print(f"   Memórias: {stats['mapa_mental']['total_celulas']}")
    print(f"   Precisão média memórias: {stats['mapa_mental']['precisao_media']}%")
    
    # Iniciar threads
    print("\n🔌 Iniciando threads...")
    threading.Thread(target=loop_latest, daemon=True).start()
    threading.Thread(target=processar_fila, daemon=True).start()
    threading.Thread(target=loop_pesado, daemon=True).start()
    
    print("\n" + "="*80)
    print("🚀 FLASK INICIANDO...")
    print("   /health - Healthcheck")
    print("   /api/stats - Estatísticas")
    print("   /api/treinar - Treinar agente por simulação")
    print("="*80)
    
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
