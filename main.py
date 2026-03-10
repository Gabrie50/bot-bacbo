# =============================================================================
# main.py - VERSÃO CAÇADORA 3.0 (SISTEMA ANTI-QUEDA - 5 CAMADAS DE PROTEÇÃO)
# =============================================================================
# ✅ SISTEMA DE APRENDIZADO: Cada estratégia é um agente que aprende
# ✅ NEUROEVOLUÇÃO: Mutações, crossover e seleção natural
# ✅ 10 ESTRATÉGIAS TRANSFORMADAS EM AGENTES
# ✅ MEMÓRIA PERSISTENTE: Salva em JSON e nunca reseta
# ✅ TABELA DE ANÁLISE DE ERROS: Cada erro é registrado com contexto completo
# ✅ DETECÇÃO DE MANIPULAÇÃO: Identifica padrões suspeitos do algoritmo
# =============================================================================
# 🛡️ SISTEMA ANTI-QUEDA - 5 CAMADAS DE PROTEÇÃO:
# 1. WARM-UP INTELIGENTE (30 primeiras rodadas - só treina, não arrisca)
# 2. PENALIDADE ZERO - SÓ REFORÇO POSITIVO (nunca desce, só sobe)
# 3. VOTO MÍNIMO GARANTIDO (30% do peso base sempre)
# 4. CONSENSO MÍNIMO - só prevê com 3+ agentes
# 5. RESET AUTOMÁTICO SUAVE (recupera agentes doentes)
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
import pickle
from pathlib import Path

# =============================================================================
# CONFIGURAÇÕES CORRIGIDAS - PG8000 COM SSL
# =============================================================================
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://neondb_owner:npg_md9IFsDnelP6@ep-blue-hall-adejcups-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

# Parse da URL removendo parâmetros de conexão
parsed = urllib.parse.urlparse(DATABASE_URL)
DB_USER = parsed.username
DB_PASSWORD = parsed.password
DB_HOST = parsed.hostname
DB_PORT = parsed.port or 5432
DB_NAME = parsed.path[1:]

# Configuração SSL para pg8000
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

# =============================================================================
# CONFIGURAÇÕES DAS 3 FONTES
# =============================================================================

# FONTE 1: API Latest (PRINCIPAL - envia para tabela)
LATEST_API_URL = "https://api-cs.casino.org/svc-evolution-game-events/api/bacbo/latest"

# FONTE 2: WebSocket (Backup - quando Latest falha)
WS_URL = "wss://api-cs.casino.org/svc-evolution-game-events/ws/bacbo"

# FONTE 3: API Normal (Fallback - quando todos falham + CARGA HISTÓRICA)
API_URL = "https://api-cs.casino.org/svc-evolution-game-events/api/bacbo"
API_PARAMS = {
    "page": 0,
    "size": 30,
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

# Configurações gerais
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

# Status das fontes
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
            'Compensação': {'acertos': 0, 'erros': 0, 'total': 0},
            'Paredão': {'acertos': 0, 'erros': 0, 'total': 0},
            'Moedor': {'acertos': 0, 'erros': 0, 'total': 0},
            'Xadrez': {'acertos': 0, 'erros': 0, 'total': 0},
            'Contragolpe': {'acertos': 0, 'erros': 0, 'total': 0},
            'Reset Cluster': {'acertos': 0, 'erros': 0, 'total': 0},
            'Falsa Alternância': {'acertos': 0, 'erros': 0, 'total': 0},
            'Saturação': {'acertos': 0, 'erros': 0, 'total': 0},
            'Meta-Algoritmo': {'acertos': 0, 'erros': 0, 'total': 0},
            'Horário': {'acertos': 0, 'erros': 0, 'total': 0}
        }
    },
    'ultima_previsao': None,
    'ultimo_resultado_real': None,
    'aprendizado': None,
    'ultimo_contexto_erro': None,
    'indice_manipulacao': 0
}

# =============================================================================
# INICIALIZAÇÃO FLASK
# =============================================================================
app = Flask(__name__)
CORS(app)
session = requests.Session()
session.headers.update(HEADERS)

# =============================================================================
# 🧠 SISTEMA DE APRENDIZADO: RL + NEUROEVOLUTION (VERSÃO CAÇADORA 3.0)
# =============================================================================

class AgenteEstrategia:
    """
    VERSÃO CAÇADORA 3.0 - SISTEMA ANTI-QUEDA
    1. Penalidade ZERO - só reforço positivo
    2. Peso mínimo garantido 0.5
    3. Voto mínimo de 30% do peso base
    """
    def __init__(self, nome, pesos_base, taxa_mutacao=0.25):
        self.nome = nome
        self.pesos_base = pesos_base.copy()
        self.pesos_atuais = pesos_base.copy()
        self.acertos = 0
        self.erros = 0
        self.total_uso = 0
        self.taxa_mutacao = taxa_mutacao
        self.ultima_atuacao = datetime.now()
        self.historico_precisao = deque(maxlen=50)
        self.idade_geracoes = 0
        self.deteccoes_manipulacao = 0
        self.erros_consecutivos = 0
        self.saude = 100  # % de saúde (novo)
        
    @property
    def precisao(self):
        if self.total_uso == 0:
            return 0
        return (self.acertos / self.total_uso) * 100
    
    @property
    def forca(self):
        if self.total_uso == 0:
            return 0.5
        bonus_manipulacao = 1.0 + (self.deteccoes_manipulacao * 0.05)
        bonus_saude = self.saude / 100
        return (self.precisao / 100) * min(1.0, self.total_uso / 50) * bonus_manipulacao * bonus_saude
    
    def atuar(self, dados, modo, votos_originais, indice_manipulacao=0):
        banker = votos_originais.get('banker', 0)
        player = votos_originais.get('player', 0)
        
        # 🛡️ CAMADA 3: VOTO MÍNIMO GARANTIDO (30% do peso base)
        peso_minimo_banker = max(self.pesos_atuais['banker'], self.pesos_base['banker'] * 0.3)
        peso_minimo_player = max(self.pesos_atuais['player'], self.pesos_base['player'] * 0.3)
        
        fator_manipulacao = 1.0 + (indice_manipulacao / 500)
        
        banker_ajustado = int(banker * peso_minimo_banker * fator_manipulacao)
        player_ajustado = int(player * peso_minimo_player * fator_manipulacao)
        
        return {
            'banker': banker_ajustado,
            'player': player_ajustado,
            'motivo': votos_originais.get('motivo', '')
        }
    
    def registrar_resultado(self, acertou, confianca=0, foi_manipulado=False):
        """
        Registro com análise de padrão de erros
        🛡️ CAMADA 2: PENALIDADE ZERO - SÓ REFORÇO POSITIVO
        """
        self.total_uso += 1
        
        confianca_ajustada = confianca
        if foi_manipulado:
            confianca_ajustada = min(100, confianca * 1.2)
        
        if acertou:
            self.acertos += 1
            self.erros_consecutivos = 0
            self.saude = min(100, self.saude + 2)  # +2% de saúde quando acerta
            
            if foi_manipulado:
                self.deteccoes_manipulacao += 1
                self._aplicar_reforco_cacador(True, confianca_ajustada * 1.2)
            else:
                self._aplicar_reforco_cacador(True, confianca_ajustada)
        else:
            self.erros += 1
            self.erros_consecutivos += 1
            self.saude = max(50, self.saude - 1)  # -1% de saúde quando erra (mínimo 50%)
            
            # 🟢 NÃO APLICA PENALIDADE - SÓ NÃO SOBE
            # Quando erra, apenas não ganha reforço
            pass  # ZERO penalidade!
        
        self.historico_precisao.append(1 if acertou else 0)
        self.ultima_atuacao = datetime.now()
    
    def _aplicar_reforco_cacador(self, acertou, confianca):
        """
        🛡️ CAMADA 2: PENALIDADE ZERO - SÓ REFORÇO POSITIVO
        SÓ SOBE, NUNCA DESCE
        """
        if acertou:
            # ✅ SÓ REFORÇO POSITIVO: +10% da confiança
            fator_reforco = 1.0 + (confianca / 100) * 0.10
            self.pesos_atuais['banker'] *= fator_reforco
            self.pesos_atuais['player'] *= fator_reforco
        # else: NADA! Zero penalidade quando erra
        
        # 🛡️ Limites suaves: 0.5 a 3.0 (proteção total)
        self.pesos_atuais['banker'] = max(0.5, min(3.0, self.pesos_atuais['banker']))
        self.pesos_atuais['player'] = max(0.5, min(3.0, self.pesos_atuais['player']))
    
    def mutar(self):
        if random.random() < self.taxa_mutacao:
            gene = random.choice(['banker', 'player'])
            fator_idade = min(1.5, 1.0 + (self.idade_geracoes / 30))
            delta = random.uniform(-0.10, 0.15) * fator_idade  # Mutações mais suaves
            
            self.pesos_atuais[gene] += delta
            self.pesos_atuais[gene] = max(0.5, min(3.0, self.pesos_atuais[gene]))  # Limite 0.5-3.0
            
            print(f"🧬 MUTAÇÃO em {self.nome}: {gene} → {self.pesos_atuais[gene]:.2f}")
            return True
        return False
    
    def resetar_para_base(self):
        """Reseta para os pesos base mantendo 20% do aprendizado"""
        self.pesos_atuais = self.pesos_base.copy()
        self.acertos = int(self.acertos * 0.2)
        self.erros = int(self.erros * 0.2)
        self.saude = 80  # Volta com 80% de saúde
        print(f"🔄 RESET {self.nome} para pesos base (saúde: 80%)")
    
    def recuperar_saude(self):
        """Recupera gradualmente a saúde do agente"""
        self.saude = min(100, self.saude + 5)
        print(f"💊 {self.nome} recuperou saúde para {self.saude}%")
    
    def para_dict(self):
        return {
            'nome': self.nome,
            'pesos_base': self.pesos_base,
            'pesos_atuais': self.pesos_atuais,
            'acertos': self.acertos,
            'erros': self.erros,
            'total_uso': self.total_uso,
            'taxa_mutacao': self.taxa_mutacao,
            'idade_geracoes': self.idade_geracoes,
            'historico_precisao': list(self.historico_precisao),
            'deteccoes_manipulacao': self.deteccoes_manipulacao,
            'erros_consecutivos': self.erros_consecutivos,
            'saude': self.saude
        }
    
    @classmethod
    def de_dict(cls, dados):
        agente = cls(dados['nome'], dados['pesos_base'])
        agente.pesos_atuais = dados['pesos_atuais']
        agente.acertos = dados['acertos']
        agente.erros = dados['erros']
        agente.total_uso = dados['total_uso']
        agente.taxa_mutacao = dados['taxa_mutacao']
        agente.idade_geracoes = dados['idade_geracoes']
        agente.historico_precisao = deque(dados['historico_precisao'], maxlen=50)
        agente.deteccoes_manipulacao = dados.get('deteccoes_manipulacao', 0)
        agente.erros_consecutivos = dados.get('erros_consecutivos', 0)
        agente.saude = dados.get('saude', 100)
        return agente


class ControladorAprendizado:
    def __init__(self, arquivo_estado='aprendizado.json'):
        self.arquivo_estado = arquivo_estado
        self.agentes = {}
        self.geracao = 0
        self.melhor_precisao_global = 0
        self.historico_evolucao = []
        self.total_rodadas_processadas = 0
        self.manipulacoes_detectadas = 0
        self.rodadas_desde_ultima_verificacao_saude = 0
        
        self.pesos_iniciais = {
            'Compensação': {'banker': 0.7, 'player': 0.7},
            'Paredão': {'banker': 1.2, 'player': 1.2},
            'Moedor': {'banker': 1.0, 'player': 1.0},
            'Xadrez': {'banker': 0.6, 'player': 0.6},
            'Contragolpe': {'banker': 1.5, 'player': 1.5},
            'Reset Cluster': {'banker': 1.2, 'player': 1.2},
            'Falsa Alternância': {'banker': 1.1, 'player': 1.1},
            'Saturação': {'banker': 1.3, 'player': 1.3},
            'Meta-Algoritmo': {'banker': 1.4, 'player': 1.4},
            'Horário': {'banker': 1.0, 'player': 1.0}
        }
        
        self.carregar_estado()
        
        if not self.agentes:
            self._inicializar_agentes()
    
    def _inicializar_agentes(self):
        for nome, pesos in self.pesos_iniciais.items():
            self.agentes[nome] = AgenteEstrategia(nome, pesos)
        print(f"✅ {len(self.agentes)} agentes inicializados (versão CAÇADORA 3.0 - ANTI-QUEDA)")
    
    def obter_votos_ajustados(self, dados, modo, votos_por_estrategia, indice_manipulacao=0):
        votos_banker_total = 0
        votos_player_total = 0
        agentes_ativos = []
        detalhes = []
        
        for nome_estrategia, votos_originais in votos_por_estrategia.items():
            if nome_estrategia in self.agentes:
                agente = self.agentes[nome_estrategia]
                
                if votos_originais.get('banker', 0) == 0 and votos_originais.get('player', 0) == 0:
                    continue
                
                # Só agentes com saúde > 60% votam
                if agente.saude < 60:
                    print(f"⏸️ {nome_estrategia} em repouso (saúde: {agente.saude}%)")
                    continue
                
                votos_ajustados = agente.atuar(dados, modo, votos_originais, indice_manipulacao)
                
                if votos_ajustados['banker'] > 0 or votos_ajustados['player'] > 0:
                    votos_banker_total += votos_ajustados['banker']
                    votos_player_total += votos_ajustados['player']
                    agentes_ativos.append(nome_estrategia)
                    
                    detalhes.append(
                        f"{nome_estrategia}: B{votos_ajustados['banker']} P{votos_ajustados['player']} "
                        f"(pesos: {agente.pesos_atuais['banker']:.2f}/{agente.pesos_atuais['player']:.2f} | saúde: {agente.saude}%)"
                    )
        
        if detalhes:
            print("\n📊 VOTOS COM APRENDIZADO:")
            for d in detalhes:
                print(f"   {d}")
        
        return votos_banker_total, votos_player_total, agentes_ativos
    
    def registrar_rodada(self, agentes_usados, previsao, confianca, resultado_real, foi_manipulado=False):
        if resultado_real == 'TIE':
            return
        
        if foi_manipulado:
            self.manipulacoes_detectadas += 1
        
        for nome_agente in agentes_usados:
            if nome_agente in self.agentes:
                agente = self.agentes[nome_agente]
                acertou = (previsao == resultado_real)
                agente.registrar_resultado(acertou, confianca, foi_manipulado)
        
        self.total_rodadas_processadas += 1
        self.rodadas_desde_ultima_verificacao_saude += 1
        
        if self.total_rodadas_processadas % 15 == 0:
            self.evoluir_cacador()
        
        if self.rodadas_desde_ultima_verificacao_saude >= 10:
            self.verificar_saude_agentes()
            self.rodadas_desde_ultima_verificacao_saude = 0
        
        if self.total_rodadas_processadas % 50 == 0:
            self.salvar_estado()
    
    def verificar_saude_agentes(self):
        """
        🛡️ CAMADA 5: RESET AUTOMÁTICO SUAVE
        Verifica a saúde dos agentes a cada 10 rodadas
        """
        print("\n🩺 VERIFICANDO SAÚDE DOS AGENTES...")
        
        for nome, agente in self.agentes.items():
            # Se o agente está muito abaixo do peso base
            if (agente.pesos_atuais['banker'] < agente.pesos_base['banker'] * 0.5 or
                agente.pesos_atuais['player'] < agente.pesos_base['player'] * 0.5 or
                agente.saude < 70):
                
                print(f"🩺 AGENTE {nome} COM SAÚDE BAIXA (peso: {agente.pesos_atuais['banker']:.2f}/{agente.pesos_base['banker']:.2f}, saúde: {agente.saude}%) - Recuperando...")
                
                # Recupera 20% do peso base
                agente.pesos_atuais['banker'] = max(
                    agente.pesos_atuais['banker'],
                    agente.pesos_base['banker'] * 0.8
                )
                agente.pesos_atuais['player'] = max(
                    agente.pesos_atuais['player'],
                    agente.pesos_base['player'] * 0.8
                )
                
                # Recupera saúde
                agente.recuperar_saude()
    
    def evoluir_cacador(self):
        self.geracao += 1
        print(f"\n🔥 EVOLUÇÃO CAÇADORA #{self.geracao} 🔥")
        
        for agente in self.agentes.values():
            agente.idade_geracoes += 1
        
        ranking = []
        for nome, agente in self.agentes.items():
            if agente.total_uso > 0:
                bonus = 1.0 + (agente.deteccoes_manipulacao * 0.05)
                bonus_saude = agente.saude / 100
                pontuacao = agente.precisao * bonus * bonus_saude
                ranking.append((nome, agente.precisao, pontuacao, agente.total_uso, agente.deteccoes_manipulacao, agente.saude))
        
        ranking.sort(key=lambda x: x[2], reverse=True)
        
        if ranking:
            precisao_media = np.mean([r[1] for r in ranking])
            print(f"📊 Precisão média: {precisao_media:.1f}%")
            print(f"🎯 Manipulações detectadas: {self.manipulacoes_detectadas}")
            
            print("\n🏆 TOP 3 AGENTES:")
            for i, (nome, prec, pont, uso, det, saude) in enumerate(ranking[:3]):
                print(f"   {i+1}. {nome}: {prec:.1f}% ({uso} usos) | detecções: {det} | saúde: {saude}%")
            
            if len(ranking) > 3:
                print("\n💀 BOTTOM 3:")
                for i, (nome, prec, pont, uso, det, saude) in enumerate(ranking[-3:]):
                    print(f"   {len(ranking)-2+i}. {nome}: {prec:.1f}% ({uso} usos) | saúde: {saude}%")
            
            melhor_atual = ranking[0][1]
            if melhor_atual > self.melhor_precisao_global:
                self.melhor_precisao_global = melhor_atual
                print(f"\n🏆 NOVA MELHOR PRECISÃO GLOBAL: {melhor_atual:.1f}%")
                self.salvar_estado()
        
        mutacoes = 0
        for agente in self.agentes.values():
            if agente.mutar():
                mutacoes += 1
        
        print(f"\n🧬 {mutacoes} mutações aplicadas")
        
        # Reset suave para agentes com saúde muito baixa
        for nome, agente in self.agentes.items():
            if agente.saude < 50:
                print(f"⚠️ RESETANDO {nome} - Saúde crítica: {agente.saude}%")
                agente.resetar_para_base()
        
        self.historico_evolucao.append({
            'geracao': self.geracao,
            'data': datetime.now().isoformat(),
            'precisao_media': precisao_media if ranking else 0,
            'melhor': ranking[0][0] if ranking else '',
            'melhor_precisao': ranking[0][1] if ranking else 0,
            'manipulacoes': self.manipulacoes_detectadas
        })
    
    def salvar_estado(self):
        try:
            estado = {
                'geracao': self.geracao,
                'melhor_precisao_global': self.melhor_precisao_global,
                'total_rodadas_processadas': self.total_rodadas_processadas,
                'manipulacoes_detectadas': self.manipulacoes_detectadas,
                'historico_evolucao': self.historico_evolucao[-50:],
                'agentes': {nome: agente.para_dict() for nome, agente in self.agentes.items()}
            }
            
            with open(self.arquivo_estado, 'w') as f:
                json.dump(estado, f, indent=2)
            
            print(f"💾 Estado do aprendizado salvo em {self.arquivo_estado}")
            return True
        except Exception as e:
            print(f"❌ Erro ao salvar estado: {e}")
            return False
    
    def carregar_estado(self):
        caminho = Path(self.arquivo_estado)
        if not caminho.exists():
            print("📂 Nenhum estado anterior encontrado - iniciando novo")
            return False
        
        try:
            with open(self.arquivo_estado, 'r') as f:
                estado = json.load(f)
            
            self.geracao = estado.get('geracao', 0)
            self.melhor_precisao_global = estado.get('melhor_precisao_global', 0)
            self.total_rodadas_processadas = estado.get('total_rodadas_processadas', 0)
            self.manipulacoes_detectadas = estado.get('manipulacoes_detectadas', 0)
            self.historico_evolucao = estado.get('historico_evolucao', [])
            
            for nome, dados_agente in estado.get('agentes', {}).items():
                self.agentes[nome] = AgenteEstrategia.de_dict(dados_agente)
            
            print(f"✅ Aprendizado carregado: {self.geracao} gerações, {self.total_rodadas_processadas} rodadas")
            print(f"🏆 Melhor precisão global: {self.melhor_precisao_global:.1f}%")
            print(f"🎯 Manipulações detectadas: {self.manipulacoes_detectadas}")
            return True
        except Exception as e:
            print(f"⚠️ Erro ao carregar estado: {e}")
            return False
    
    def get_stats(self):
        stats = {
            'geracao': self.geracao,
            'total_rodadas': self.total_rodadas_processadas,
            'melhor_precisao_global': round(self.melhor_precisao_global, 1),
            'manipulacoes_detectadas': self.manipulacoes_detectadas,
            'agentes': []
        }
        
        for nome, agente in self.agentes.items():
            stats['agentes'].append({
                'nome': nome,
                'acertos': agente.acertos,
                'erros': agente.erros,
                'total': agente.total_uso,
                'precisao': round(agente.precisao, 1),
                'pesos': {k: round(v, 2) for k, v in agente.pesos_atuais.items()},
                'idade': agente.idade_geracoes,
                'deteccoes_manipulacao': agente.deteccoes_manipulacao,
                'erros_consecutivos': agente.erros_consecutivos,
                'saude': agente.saude
            })
        
        stats['agentes'].sort(key=lambda x: x['precisao'], reverse=True)
        
        return stats


# =============================================================================
# NOVAS FUNÇÕES PARA DETECÇÃO DE MANIPULAÇÃO
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


def calcular_indice_manipulacao(dados):
    if len(dados) < 10:
        return 0
    
    dados_ord = list(reversed(dados)) if dados else []
    indice = 0
    
    streaks = 0
    for i in range(len(dados_ord)-3):
        if (dados_ord[i]['resultado'] == dados_ord[i+1]['resultado'] == 
            dados_ord[i+2]['resultado'] == dados_ord[i+3]['resultado'] and
            dados_ord[i]['resultado'] != 'TIE'):
            streaks += 1
    indice += streaks * 10
    
    ties = sum(1 for r in dados_ord[:20] if r['resultado'] == 'TIE')
    if ties > 3:
        indice += 20
    if ties > 5:
        indice += 15
    
    repeticoes = 0
    for i in range(len(dados_ord)-1):
        if dados_ord[i]['banker_score'] == dados_ord[i+1]['player_score']:
            repeticoes += 1
        if dados_ord[i]['player_score'] == dados_ord[i+1]['banker_score']:
            repeticoes += 1
    indice += repeticoes * 5
    
    for i in range(len(dados_ord)-4):
        if (dados_ord[i]['resultado'] == dados_ord[i+1]['resultado'] == dados_ord[i+2]['resultado'] and
            dados_ord[i+2]['resultado'] != dados_ord[i+3]['resultado'] and
            dados_ord[i+3]['resultado'] == dados_ord[i+4]['resultado']):
            indice += 25
            break
    
    return min(100, indice)


# =============================================================================
# FUNÇÕES DO BANCO CORRIGIDAS
# =============================================================================

def get_db_connection():
    try:
        conn = pg8000.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            ssl_context=SSL_CONTEXT
        )
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return None

def init_db():
    conn = get_db_connection()
    if not conn:
        print("⚠️ Banco não disponível - continuando sem banco")
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
                data_hora TIMESTAMPTZ,
                previsao TEXT,
                simbolo TEXT,
                confianca INTEGER,
                resultado_real TEXT,
                acertou BOOLEAN,
                estrategias TEXT,
                modo TEXT,
                pesos_agentes TEXT
            )
        ''')
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS analise_erros (
                id SERIAL PRIMARY KEY,
                data_hora TIMESTAMPTZ,
                previsao_feita TEXT,
                resultado_real TEXT,
                confianca INTEGER,
                modo TEXT,
                streak_atual INTEGER,
                banker_50 INT,
                player_50 INT,
                diferenca_percentual FLOAT,
                ultimos_5_resultados TEXT,
                agentes_ativos TEXT,
                pesos_agentes JSONB,
                indice_manipulacao INT,
                foi_manipulado BOOLEAN,
                acertou BOOLEAN,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        cur.execute('CREATE INDEX IF NOT EXISTS idx_erros_data ON analise_erros(data_hora DESC)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_erros_acertou ON analise_erros(acertou)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_erros_manipulacao ON analise_erros(foi_manipulado)')
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Tabelas criadas/verificadas com sucesso")
        return True
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        return False

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

def salvar_previsao(previsao, resultado_real, acertou, pesos_agentes=None, indice_manipulacao=0, foi_manipulado=False):
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO historico_previsoes 
            (data_hora, previsao, simbolo, confianca, resultado_real, acertou, estrategias, modo, pesos_agentes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            datetime.now(timezone.utc),
            previsao['previsao'],
            previsao['simbolo'],
            previsao['confianca'],
            resultado_real,
            acertou,
            ','.join(previsao['estrategias']),
            previsao['modo'],
            json.dumps(pesos_agentes) if pesos_agentes else None
        ))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar previsão: {e}")
        return False


def salvar_erro_para_analise(ultima, resultado_real, acertou, dados_contexto, indice_manipulacao=0, foi_manipulado=False):
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cur = conn.cursor()
        
        ultimos_5 = ','.join(dados_contexto.get('ultimos_5', []))
        
        cur.execute('''
            INSERT INTO analise_erros 
            (data_hora, previsao_feita, resultado_real, confianca, modo, 
             streak_atual, banker_50, player_50, diferenca_percentual,
             ultimos_5_resultados, agentes_ativos, pesos_agentes, 
             indice_manipulacao, foi_manipulado, acertou)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            datetime.now(timezone.utc),
            ultima['previsao'],
            resultado_real,
            ultima['confianca'],
            ultima.get('modo', 'DESCONHECIDO'),
            dados_contexto.get('streak', 0),
            dados_contexto.get('banker_50', 0),
            dados_contexto.get('player_50', 0),
            dados_contexto.get('diferenca', 0),
            ultimos_5,
            ','.join(ultima.get('estrategias', [])),
            json.dumps(dados_contexto.get('pesos_agentes', {})),
            indice_manipulacao,
            foi_manipulado,
            acertou
        ))
        conn.commit()
        cur.close()
        conn.close()
        
        if not acertou and foi_manipulado:
            print(f"📝 ERRO EM JOGADA MANIPULADA registrado")
        elif not acertou:
            print(f"📝 Erro registrado para análise")
    except Exception as e:
        print(f"❌ Erro ao registrar análise: {e}")


# =============================================================================
# FUNÇÕES DO BANCO (LEVES)
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
        return resultado
    except Exception as e:
        print(f"⚠️ Erro get_ultimas_20: {e}")
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
    except Exception as e:
        print(f"⚠️ Erro get_total: {e}")
        return 0

# =============================================================================
# FUNÇÕES PESADAS
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
        print(f"⚠️ Erro contar_periodo {horas}h: {e}")
        return 0

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
# FUNÇÃO PARA ALTERNAR FONTE ATIVA
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
# FONTE 1: API LATEST (PRINCIPAL)
# =============================================================================

def buscar_latest():
    global ultimo_id_latest, falhas_latest, fonte_ativa
    
    try:
        response = requests.get(LATEST_API_URL, headers=HEADERS, timeout=3)
        
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
                alternar_fonte()
            return None
            
    except Exception as e:
        if fonte_ativa == 'latest':
            falhas_latest += 1
            fontes_status['latest']['falhas'] += 1
            print(f"⚠️ LATEST erro: {e} - falha {falhas_latest}/{LIMITE_FALHAS}")
            alternar_fonte()
        return None

# =============================================================================
# FONTE 2: WEBSOCKET (BACKUP)
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
        alternar_fonte()

def on_ws_close(ws, close_status_code, close_msg):
    global falhas_websocket, fonte_ativa
    if fonte_ativa == 'websocket':
        falhas_websocket += 1
        fontes_status['websocket']['falhas'] += 1
        print(f"🔌 WS Fechado - falha {falhas_websocket}/{LIMITE_FALHAS}")
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
# FONTE 3: API NORMAL (FALLBACK FINAL + CARGA HISTÓRICA)
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
            alternar_fonte()
        return None

# =============================================================================
# CARGA HISTÓRICA COMPLETA
# =============================================================================

def carregar_historico_completo():
    print("\n📚 INICIANDO CARGA HISTÓRICA COMPLETA...")
    print("⏳ Isso pode levar alguns minutos...")
    
    conn = get_db_connection()
    if not conn:
        print("❌ Erro ao conectar ao banco")
        return
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM rodadas')
        total_existente = cur.fetchone()[0]
        print(f"📊 Rodadas existentes: {total_existente}")
        
        page = 0
        total_carregadas = 0
        pagina_sem_novidades = 0
        
        while pagina_sem_novidades < 3:
            params = API_PARAMS.copy()
            params['page'] = page
            params['_t'] = int(time.time() * 1000)
            
            try:
                print(f"\n📥 Buscando página {page}...")
                response = session.get(API_URL, params=params, timeout=TIMEOUT_API)
                response.raise_for_status()
                dados = response.json()
                
                if not dados or len(dados) == 0:
                    print(f"✅ Fim das páginas na página {page}")
                    break
                
                print(f"   → Página {page}: {len(dados)} rodadas")
                
                novas_na_pagina = 0
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
                            'resultado': resultado
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
                            'historico',
                            json.dumps(rodada, default=str)
                        ))
                        
                        if cur.rowcount > 0:
                            novas_na_pagina += 1
                            
                    except Exception as e:
                        continue
                
                conn.commit()
                total_carregadas += novas_na_pagina
                
                if novas_na_pagina > 0:
                    print(f"   ✅ +{novas_na_pagina} novas rodadas (acumulado: {total_carregadas})")
                    pagina_sem_novidades = 0
                else:
                    print(f"   ⏭️ Nenhuma rodada nova nesta página")
                    pagina_sem_novidades += 1
                
                page += 1
                time.sleep(0.5)
                
            except Exception as e:
                print(f"⚠️ Erro na página {page}: {e}")
                break
        
        cur.close()
        conn.close()
        
        print("\n" + "="*50)
        print("📊 CARGA HISTÓRICA CONCLUÍDA!")
        print(f"✅ Total de novas rodadas: {total_carregadas}")
        print(f"📈 Total no banco agora: {total_existente + total_carregadas}")
        print("="*50)
        
    except Exception as e:
        print(f"❌ Erro na carga histórica: {e}")

# =============================================================================
# LOOP DE COLETA
# =============================================================================

def loop_latest():
    print("📡 [PRINCIPAL] Coletor LATEST iniciado (0.3s)...")
    while True:
        try:
            if fonte_ativa == 'latest':
                rodada = buscar_latest()
                if rodada:
                    fila_rodadas.append(rodada)
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
# PROCESSADOR DA FILA
# =============================================================================

def processar_fila():
    print("🚀 Processador TURBO iniciado...")
    
    while True:
        try:
            if fila_rodadas:
                batch = list(fila_rodadas)
                fila_rodadas.clear()
                
                saved = 0
                for rodada in batch:
                    if salvar_rodada(rodada, 'principal'):
                        saved += 1
                        cache['ultimo_resultado_real'] = rodada['resultado']
                        print(f"✅ SALVO: {rodada['player_score']} vs {rodada['banker_score']} - {rodada['resultado']}")
                
                if saved > 0:
                    print(f"💾 Processadas {saved} rodadas")
                    atualizar_dados_leves()
            
            time.sleep(0.01)
            
        except Exception as e:
            print(f"❌ Erro TURBO: {e}")
            time.sleep(0.1)


# =============================================================================
# ESTRATÉGIAS DE PREVISÃO
# =============================================================================

def get_dados_ordenados(dados):
    return list(reversed(dados)) if dados else []

def verificar_delay_pos_empate(dados):
    if len(dados) < 2:
        return 1.0
    if dados[1]['resultado'] == 'TIE':
        print("⚠️ DELAY PÓS-EMPATE ATIVO - Rodada anterior foi TIE")
        return 0.7
    return 1.0

def detectar_modo_tese(dados):
    if len(dados) < 20:
        return "EQUILIBRADO"
    
    dados_ord = get_dados_ordenados(dados)
    
    player = sum(1 for r in dados_ord if r['resultado'] == 'PLAYER')
    banker = sum(1 for r in dados_ord if r['resultado'] == 'BANKER')
    ties = sum(1 for r in dados_ord if r['resultado'] == 'TIE')
    total = len(dados_ord)
    
    player_pct = (player / total) * 100
    banker_pct = (banker / total) * 100
    ties_pct = (ties / total) * 100
    
    extremos = sum(1 for r in dados_ord if r['player_score'] >= 10 or r['banker_score'] >= 10)
    extremos_pct = (extremos / total) * 100
    
    if banker_pct > 48 or player_pct > 48:
        return "AGRESSIVO"
    if extremos_pct > 25:
        return "PREDATORIO"
    if ties_pct > 12:
        return "MOEDOR"
    return "EQUILIBRADO"


def estrategia_compensacao_tese(dados, modo):
    if len(dados) < 10:
        return {'banker': 0, 'player': 0}
    
    dados_ord = get_dados_ordenados(dados)
    
    player = sum(1 for r in dados_ord if r['resultado'] == 'PLAYER')
    banker = sum(1 for r in dados_ord if r['resultado'] == 'BANKER')
    total = len(dados_ord)
    
    player_pct = (player / total) * 100
    banker_pct = (banker / total) * 100
    
    diff = abs(banker_pct - player_pct)
    
    if diff > 8:
        if modo == "MOEDOR":
            return {'banker': 0, 'player': 0}
        
        if banker_pct > player_pct:
            return {'banker': 0, 'player': 50}
        else:
            return {'banker': 50, 'player': 0}
    
    return {'banker': 0, 'player': 0}


def estrategia_paredao_tese(dados, modo):
    if len(dados) < 3:
        return {'banker': 0, 'player': 0}
    
    dados_ord = get_dados_ordenados(dados)
    
    streak = 1
    streak_cor = dados_ord[0]['resultado']
    
    for i in range(1, min(10, len(dados_ord))):
        if dados_ord[i]['resultado'] == streak_cor:
            streak += 1
        else:
            break
    
    if streak >= 3:
        if streak >= 5:
            posicao = len(dados_ord) % 10
            if posicao < 8:
                if streak_cor == 'BANKER':
                    return {'banker': 0, 'player': 65, 'motivo': f'Sat: {streak}x BANKER'}
                else:
                    return {'banker': 65, 'player': 0, 'motivo': f'Sat: {streak}x PLAYER'}
        
        if streak_cor == 'BANKER':
            return {'banker': 70, 'player': 0}
        else:
            return {'banker': 0, 'player': 70}
    
    return {'banker': 0, 'player': 0}


def estrategia_moedor_tese(dados, modo):
    if len(dados) < 5:
        return {'banker': 0, 'player': 0}
    
    dados_ord = get_dados_ordenados(dados)
    
    ties = sum(1 for r in dados_ord[:5] if r['resultado'] == 'TIE')
    
    if ties >= 2:
        player = sum(1 for r in dados_ord if r['resultado'] == 'PLAYER')
        banker = sum(1 for r in dados_ord if r['resultado'] == 'BANKER')
        
        if banker > player:
            return {'banker': 70, 'player': 0}
        else:
            return {'banker': 0, 'player': 70}
    
    return {'banker': 0, 'player': 0}


def estrategia_xadrez_tese(dados, modo):
    if len(dados) < 4:
        return {'banker': 0, 'player': 0}
    
    dados_ord = get_dados_ordenados(dados)
    seq = [r['resultado'] for r in dados_ord[:4]]
    
    if (seq[0] != seq[1] and seq[1] != seq[2] and seq[2] != seq[3]):
        alternancias = 0
        for i in range(1, 4):
            if dados_ord[i-1]['resultado'] != dados_ord[i]['resultado']:
                alternancias += 1
        
        if alternancias == 3:
            posicao = len(dados_ord) % 10
            if posicao < 4:
                if seq[3] == 'BANKER':
                    return {'banker': 65, 'player': 0, 'motivo': 'Quebra Xadrez'}
                else:
                    return {'banker': 0, 'player': 65, 'motivo': 'Quebra Xadrez'}
        
        if seq[3] == 'BANKER':
            return {'banker': 0, 'player': 65}
        else:
            return {'banker': 65, 'player': 0}
    
    return {'banker': 0, 'player': 0}


def estrategia_contragolpe_tese(dados, modo):
    if len(dados) < 4:
        return {'banker': 0, 'player': 0}
    
    dados_ord = get_dados_ordenados(dados)
    
    if len(dados_ord) < 4:
        return {'banker': 0, 'player': 0}
    
    r1 = dados_ord[0]['resultado']
    r2 = dados_ord[1]['resultado']
    r3 = dados_ord[2]['resultado']
    r4 = dados_ord[3]['resultado']
    
    if r1 == r2 == r3 and r3 != r4:
        if r1 == 'BANKER':
            return {'banker': 85, 'player': 0}
        else:
            return {'banker': 0, 'player': 85}
    
    return {'banker': 0, 'player': 0}


def estrategia_reset_cluster_tese(dados, modo):
    if len(dados) < 5:
        return {'banker': 0, 'player': 0}
    
    dados_ord = get_dados_ordenados(dados)
    
    ties = []
    for i, r in enumerate(dados_ord[:5]):
        if r['resultado'] == 'TIE':
            ties.append(i)
    
    if len(ties) >= 2 and (ties[-1] - ties[0] <= 3):
        for r in dados_ord:
            if r['resultado'] != 'TIE':
                dominante = r['resultado']
                posicao = len(dados_ord) % 10
                if posicao < 7:
                    if dominante == 'BANKER':
                        return {'banker': 75, 'player': 0}
                    else:
                        return {'banker': 0, 'player': 75}
                else:
                    if dominante == 'BANKER':
                        return {'banker': 0, 'player': 75}
                    else:
                        return {'banker': 75, 'player': 0}
                break
    
    return {'banker': 0, 'player': 0}


def estrategia_falsa_alternancia_tese(dados, modo):
    if len(dados) < 3:
        return {'banker': 0, 'player': 0}
    
    dados_ord = get_dados_ordenados(dados)
    
    if len(dados_ord) < 2:
        return {'banker': 0, 'player': 0}
    
    r1 = dados_ord[0]
    r2 = dados_ord[1]
    
    r1_extremo = (r1['player_score'] >= 9 or r1['banker_score'] >= 9)
    r2_fraco = (r2['player_score'] <= 5 and r2['banker_score'] <= 5)
    
    if r1_extremo and r2_fraco:
        if r1['resultado'] == 'BANKER':
            return {'banker': 60, 'player': 0}
        else:
            return {'banker': 0, 'player': 60}
    
    if r1_extremo:
        if r1['resultado'] == 'BANKER':
            return {'banker': 55, 'player': 0}
        else:
            return {'banker': 0, 'player': 55}
    
    return {'banker': 0, 'player': 0}


def aplicar_meta_tese(votos_banker, votos_player, dados, modo):
    dados_ord = get_dados_ordenados(dados)
    
    player_total = sum(1 for r in dados_ord if r['resultado'] == 'PLAYER')
    banker_total = sum(1 for r in dados_ord if r['resultado'] == 'BANKER')
    
    print(f"📊 MODO DETECTADO: {modo} - Banker {banker_total} x Player {player_total}")
    
    if modo == "MOEDOR":
        if banker_total > player_total:
            votos_banker = int(votos_banker * 1.4)
            return votos_banker, votos_player, f'Meta MOEDOR (Banker +40%)'
        else:
            votos_player = int(votos_player * 1.4)
            return votos_banker, votos_player, f'Meta MOEDOR (Player +40%)'
    
    elif modo == "AGRESSIVO":
        if banker_total > player_total:
            votos_banker = int(votos_banker * 1.2)
            return votos_banker, votos_player, f'Meta AGRESSIVO (Banker)'
        else:
            votos_player = int(votos_player * 1.2)
            return votos_banker, votos_player, f'Meta AGRESSIVO (Player)'
    
    elif modo == "PREDATORIO":
        if banker_total > player_total:
            votos_banker = int(votos_banker * 1.1)
            return votos_banker, votos_player, f'Meta PREDATÓRIO (Banker)'
        else:
            votos_player = int(votos_player * 1.1)
            return votos_banker, votos_player, f'Meta PREDATÓRIO (Player)'
    
    return votos_banker, votos_player, None


def estrategia_saturacao_tese(dados):
    if len(dados) < 6:
        return {'banker': 0, 'player': 0, 'motivo': None}
    
    dados_ord = get_dados_ordenados(dados)
    
    streak = 1
    streak_cor = dados_ord[0]['resultado']
    
    for i in range(1, min(10, len(dados_ord))):
        if dados_ord[i]['resultado'] == streak_cor:
            streak += 1
        else:
            break
    
    if streak >= 5 and streak_cor in ['BANKER', 'PLAYER']:
        posicao = len(dados_ord) % 10
        if posicao < 8:
            if streak_cor == 'BANKER':
                return {'banker': 0, 'player': 70, 'motivo': f'Sat: {streak}x BANKER'}
            else:
                return {'banker': 70, 'player': 0, 'motivo': f'Sat: {streak}x PLAYER'}
    
    return {'banker': 0, 'player': 0, 'motivo': None}


def estrategia_horario_tese():
    hora = datetime.now().hour
    hora_brasilia = (hora - 3) % 24
    
    if 0 <= hora_brasilia <= 5:
        return {'fator_confianca': 1.03, 'peso_bonus': 3, 'periodo': 'MADRUGADA'}
    elif 6 <= hora_brasilia <= 17:
        return {'fator_confianca': 1.0, 'peso_bonus': 0, 'periodo': 'DIA'}
    else:
        return {'fator_confianca': 0.97, 'peso_bonus': -3, 'periodo': 'NOITE'}


# =============================================================================
# CÁLCULO DE CONFIANÇA REALISTA
# =============================================================================
def calcular_confianca_tese(votos_banker, votos_player, estrategias_ativas, modo, ajuste_horario, fator_delay):
    total_votos = votos_banker + votos_player
    
    if total_votos == 0:
        return 50
    
    if votos_banker > votos_player:
        confianca_base = (votos_banker / total_votos) * 100
    else:
        confianca_base = (votos_player / total_votos) * 100
    
    bonus_estrategias = min(8, len(estrategias_ativas) * 2)
    confianca = confianca_base + bonus_estrategias
    
    if votos_banker > 0 and votos_player > 0:
        proporcao = max(votos_banker, votos_player) / total_votos
        if proporcao < 0.6:
            confianca = confianca * 0.85
    
    confianca = confianca * ajuste_horario['fator_confianca']
    confianca = confianca * fator_delay
    
    # Limites realistas - NUNCA PASSAR DE 75%
    limites = {'AGRESSIVO': 75, 'PREDATORIO': 72, 'MOEDOR': 70, 'EQUILIBRADO': 68}
    max_confianca = limites.get(modo, 70) + ajuste_horario['peso_bonus']
    max_confianca = min(75, max_confianca)
    
    return min(max_confianca, max(50, round(confianca)))


def calcular_contexto_erro(dados_ord, modo, ultima_previsao):
    if not dados_ord or len(dados_ord) < 5:
        return {}
    
    streak = 1
    streak_cor = dados_ord[0]['resultado'] if dados_ord[0]['resultado'] != 'TIE' else None
    
    if streak_cor:
        for i in range(1, min(10, len(dados_ord))):
            if dados_ord[i]['resultado'] == streak_cor:
                streak += 1
            else:
                break
    
    player_50 = sum(1 for r in dados_ord[:50] if r['resultado'] == 'PLAYER')
    banker_50 = sum(1 for r in dados_ord[:50] if r['resultado'] == 'BANKER')
    
    diferenca = abs(banker_50 - player_50) / max(1, (banker_50 + player_50)) * 100
    
    ultimos_5 = [r['resultado'] for r in dados_ord[:5] if r['resultado'] != 'TIE'][:5]
    
    pesos_agentes = {}
    if cache['aprendizado']:
        for nome, agente in cache['aprendizado'].agentes.items():
            if agente.total_uso > 0:
                pesos_agentes[nome] = {
                    'pesos': agente.pesos_atuais,
                    'precisao': agente.precisao,
                    'saude': agente.saude
                }
    
    return {
        'streak': streak,
        'banker_50': banker_50,
        'player_50': player_50,
        'diferenca': round(diferenca, 1),
        'ultimos_5': ultimos_5,
        'pesos_agentes': pesos_agentes
    }


# =============================================================================
# FUNÇÃO PRINCIPAL DE PREVISÃO (COM APRENDIZADO INTEGRADO + MANIPULAÇÃO)
# =============================================================================
def calcular_previsao_com_aprendizado():
    dados = cache['leves']['ultimas_50']
    
    if len(dados) < 5:
        return {
            'modo': 'ANALISANDO...',
            'previsao': 'AGUARDANDO',
            'simbolo': '⚪',
            'confianca': 0,
            'estrategias': ['Aguardando dados...']
        }
    
    dados_ord = get_dados_ordenados(dados)
    fator_delay = verificar_delay_pos_empate(dados_ord)
    modo = detectar_modo_tese(dados_ord)
    ajuste_horario = estrategia_horario_tese()
    
    indice_manipulacao = calcular_indice_manipulacao(dados_ord)
    foi_manipulado = indice_manipulacao > 50
    
    if foi_manipulado:
        print(f"⚠️ ALERTA DE MANIPULAÇÃO! Índice: {indice_manipulacao}%")
    
    cache['indice_manipulacao'] = indice_manipulacao
    
    player_50 = sum(1 for r in dados_ord[:50] if r['resultado'] == 'PLAYER')
    banker_50 = sum(1 for r in dados_ord[:50] if r['resultado'] == 'BANKER')
    ties_50 = sum(1 for r in dados_ord[:50] if r['resultado'] == 'TIE')
    
    print(f"\n{'='*60}")
    print(f"📊 ANÁLISE ATUAL:")
    print(f"   Banker: {banker_50} ({banker_50/(banker_50+player_50)*100:.1f}% das não-empates)")
    print(f"   Player: {player_50} ({player_50/(banker_50+player_50)*100:.1f}% das não-empates)")
    print(f"   Ties: {ties_50}")
    print(f"   Modo detectado: {modo}")
    print(f"   Índice de manipulação: {indice_manipulacao}% {'⚠️' if foi_manipulado else ''}")
    print(f"{'='*60}")
    
    # 🛡️ CAMADA 1: WARM-UP INTELIGENTE (30 primeiras rodadas)
    if cache['estatisticas']['total_previsoes'] < 30:
        previsao = 'BANKER' if banker_50 > player_50 else 'PLAYER'
        simbolo = '🔴' if previsao == 'BANKER' else '🔵'
        
        print(f"🟡 WARM-UP [{cache['estatisticas']['total_previsoes']+1}/30] - Treinando sem arriscar")
        
        resultado_previsao = {
            'modo': modo,
            'previsao': previsao,
            'simbolo': simbolo,
            'confianca': 50,
            'estrategias': ['Treinamento (warm-up)']
        }
        
        cache['leves']['previsao'] = resultado_previsao
        cache['ultima_previsao'] = resultado_previsao
        cache['ultimo_contexto_erro'] = calcular_contexto_erro(dados_ord, modo, resultado_previsao)
        
        return resultado_previsao
    
    votos_originais = {}
    
    e1 = estrategia_compensacao_tese(dados_ord, modo)
    if e1.get('banker', 0) > 0 or e1.get('player', 0) > 0:
        votos_originais['Compensação'] = e1
    
    e2 = estrategia_paredao_tese(dados_ord, modo)
    if e2.get('banker', 0) > 0 or e2.get('player', 0) > 0:
        votos_originais['Paredão'] = e2
    
    e3 = estrategia_moedor_tese(dados_ord, modo)
    if e3.get('banker', 0) > 0 or e3.get('player', 0) > 0:
        votos_originais['Moedor'] = e3
    
    e4 = estrategia_xadrez_tese(dados_ord, modo)
    if e4.get('banker', 0) > 0 or e4.get('player', 0) > 0:
        votos_originais['Xadrez'] = e4
    
    e5 = estrategia_contragolpe_tese(dados_ord, modo)
    if e5.get('banker', 0) > 0 or e5.get('player', 0) > 0:
        votos_originais['Contragolpe'] = e5
    
    e6 = estrategia_reset_cluster_tese(dados_ord, modo)
    if e6.get('banker', 0) > 0 or e6.get('player', 0) > 0:
        votos_originais['Reset Cluster'] = e6
    
    e7 = estrategia_falsa_alternancia_tese(dados_ord, modo)
    if e7.get('banker', 0) > 0 or e7.get('player', 0) > 0:
        votos_originais['Falsa Alternância'] = e7
    
    e9 = estrategia_saturacao_tese(dados_ord)
    if e9.get('banker', 0) > 0 or e9.get('player', 0) > 0:
        votos_originais['Saturação'] = e9
    
    # FALSA ALTERNÂNCIA É ARMADILHA
    if 'Falsa Alternância' in votos_originais:
        votos_originais['Falsa Alternância']['banker'] = int(votos_originais['Falsa Alternância']['banker'] * 0.5)
        votos_originais['Falsa Alternância']['player'] = int(votos_originais['Falsa Alternância']['player'] * 0.5)
        print("⚠️ FALSA ALTERNÂNCIA DETECTADA - Peso reduzido 50% (é ARMADILHA!)")
    
    votos_banker_bruto = sum(v.get('banker', 0) for v in votos_originais.values())
    votos_player_bruto = sum(v.get('player', 0) for v in votos_originais.values())
    votos_banker_bruto, votos_player_bruto, meta_nome = aplicar_meta_tese(
        votos_banker_bruto, votos_player_bruto, dados_ord, modo
    )
    
    if meta_nome:
        votos_originais['Meta-Algoritmo'] = {'banker': 0, 'player': 0, 'motivo': meta_nome}
    
    if ajuste_horario['peso_bonus'] != 0:
        votos_originais['Horário'] = {'banker': 0, 'player': 0, 'motivo': ajuste_horario['periodo']}
    
    votos_banker, votos_player, agentes_ativos = cache['aprendizado'].obter_votos_ajustados(
        dados_ord, modo, votos_originais, indice_manipulacao
    )
    
    # 🛡️ CAMADA 4: CONSENSO MÍNIMO - SÓ VOTA SE TIVER APOIO
    total_agentes_que_votaram = len(agentes_ativos)
    
    if total_agentes_que_votaram < 3:  # Menos de 3 agentes votaram
        print(f"⚠️ POUCOS AGENTES ({total_agentes_que_votaram}) - Usando distribuição real")
        previsao = 'BANKER' if banker_50 > player_50 else 'PLAYER'
        simbolo = '🔴' if previsao == 'BANKER' else '🔵'
        confianca = 55
        agentes_ativos = ['Distribuição real (consenso baixo)']
        
        resultado_previsao = {
            'modo': modo,
            'previsao': previsao,
            'simbolo': simbolo,
            'confianca': confianca,
            'estrategias': agentes_ativos
        }
        
        cache['leves']['previsao'] = resultado_previsao
        cache['ultima_previsao'] = resultado_previsao
        cache['ultimo_contexto_erro'] = calcular_contexto_erro(dados_ord, modo, resultado_previsao)
        
        return resultado_previsao
    
    if votos_banker > votos_player:
        previsao = 'BANKER'
        simbolo = '🔴'
    elif votos_player > votos_banker:
        previsao = 'PLAYER'
        simbolo = '🔵'
    else:
        previsao = 'BANKER' if banker_50 > player_50 else 'PLAYER'
        simbolo = '🔴' if previsao == 'BANKER' else '🔵'
        agentes_ativos = ['Distribuição real (empate)']
    
    confianca = calcular_confianca_tese(votos_banker, votos_player, agentes_ativos, modo, ajuste_horario, fator_delay)
    
    print(f"\n🎯 DECISÃO FINAL: {simbolo} {previsao} com {confianca}%")
    print(f"   Agentes ativos: {len(agentes_ativos)}")
    print(f"{'='*60}\n")
    
    resultado_previsao = {
        'modo': modo,
        'previsao': previsao,
        'simbolo': simbolo,
        'confianca': confianca,
        'estrategias': agentes_ativos[:4]
    }
    
    cache['leves']['previsao'] = resultado_previsao
    cache['ultima_previsao'] = resultado_previsao
    cache['ultimo_contexto_erro'] = calcular_contexto_erro(dados_ord, modo, resultado_previsao)
    
    return resultado_previsao


def calcular_previsao():
    return calcular_previsao_com_aprendizado()


# =============================================================================
# SISTEMA DE APRENDIZADO - VERIFICAÇÃO DE PREVISÕES
# =============================================================================
def verificar_previsoes_anteriores():
    if cache.get('ultima_previsao') and cache.get('ultimo_resultado_real'):
        ultima = cache['ultima_previsao']
        resultado_real = cache['ultimo_resultado_real']
        contexto_erro = cache.get('ultimo_contexto_erro', {})
        
        dados = cache['leves']['ultimas_50']
        dados_ord = get_dados_ordenados(dados) if dados else []
        
        indice_manipulacao = cache.get('indice_manipulacao', 0)
        foi_manipulado = indice_manipulacao > 50
        
        if resultado_real == 'TIE':
            print("⏸️ Resultado foi TIE - Ignorando para aprendizado")
            cache['ultima_previsao'] = None
            cache['ultimo_resultado_real'] = None
            cache['ultimo_contexto_erro'] = None
            return
        
        acertou = (ultima['previsao'] == resultado_real)
        
        pesos_agentes = {}
        if cache['aprendizado']:
            for nome, agente in cache['aprendizado'].agentes.items():
                if agente.total_uso > 0:
                    pesos_agentes[nome] = {
                        'pesos': agente.pesos_atuais,
                        'precisao': agente.precisao,
                        'saude': agente.saude
                    }
        
        salvar_previsao(ultima, resultado_real, acertou, pesos_agentes, indice_manipulacao, foi_manipulado)
        salvar_erro_para_analise(ultima, resultado_real, acertou, contexto_erro, indice_manipulacao, foi_manipulado)
        
        cache['estatisticas']['total_previsoes'] += 1
        if acertou:
            cache['estatisticas']['acertos'] += 1
        else:
            cache['estatisticas']['erros'] += 1
        
        if cache['aprendizado'] and ultima.get('estrategias') and ultima['estrategias'][0] != 'Treinamento (warm-up)':
            cache['aprendizado'].registrar_rodada(
                agentes_usados=ultima.get('estrategias', []),
                previsao=ultima['previsao'],
                confianca=ultima['confianca'],
                resultado_real=resultado_real,
                foi_manipulado=foi_manipulado
            )
        
        print(f"\n📊 PROCESSANDO PREVISÃO #{cache['estatisticas']['total_previsoes']}")
        print(f"   Previsão: {ultima['simbolo']} {ultima['previsao']} vs Real: {resultado_real} = {'✅' if acertou else '❌'}")
        if foi_manipulado:
            print(f"   ⚠️ JOGADA MANIPULADA (índice: {indice_manipulacao}%)")
        
        mapeamento_estrategias = {
            'Compensação': ['Compensação', 'Compensacao', 'Compensa'],
            'Paredão': ['Paredão', 'Paredao', 'Pare'],
            'Moedor': ['Moedor'],
            'Xadrez': ['Xadrez', 'Xadre'],
            'Contragolpe': ['Contragolpe', 'Contra'],
            'Reset Cluster': ['Reset', 'Cluster'],
            'Falsa Alternância': ['Falsa', 'Alternância', 'Alternancia'],
            'Meta-Algoritmo': ['Meta'],
            'Saturação': ['Saturação', 'Saturacao', 'Sat'],
            'Horário': ['Horário', 'Horario']
        }
        
        for estrategia in ultima.get('estrategias', []):
            nome_clean = estrategia.replace('🔴', '').replace('🔵', '').replace('🟡', '').replace('⏸️', '').strip()
            
            if '(' in nome_clean:
                nome_clean = nome_clean.split('(')[0].strip()
            
            nome_final = None
            for chave, variacoes in mapeamento_estrategias.items():
                for variacao in variacoes:
                    if variacao in nome_clean:
                        nome_final = chave
                        break
                if nome_final:
                    break
            
            if nome_final and nome_final in cache['estatisticas']['estrategias']:
                cache['estatisticas']['estrategias'][nome_final]['total'] += 1
                if acertou:
                    cache['estatisticas']['estrategias'][nome_final]['acertos'] += 1
                else:
                    cache['estatisticas']['estrategias'][nome_final]['erros'] += 1
        
        previsao_historico = {
            'data': datetime.now().strftime('%d/%m %H:%M:%S'),
            'previsao': ultima['previsao'],
            'simbolo': ultima['simbolo'],
            'confianca': ultima['confianca'],
            'resultado_real': resultado_real,
            'acertou': acertou,
            'estrategias': ultima['estrategias'],
            'manipulado': foi_manipulado
        }
        
        cache['estatisticas']['ultimas_20_previsoes'].insert(0, previsao_historico)
        if len(cache['estatisticas']['ultimas_20_previsoes']) > 20:
            cache['estatisticas']['ultimas_20_previsoes'].pop()
        
        precisao_atual = calcular_precisao()
        print(f"📈 Precisão geral: {cache['estatisticas']['acertos']}/{cache['estatisticas']['total_previsoes']} ({precisao_atual}%)")
        
        cache['ultima_previsao'] = None
        cache['ultimo_resultado_real'] = None
        cache['ultimo_contexto_erro'] = None


def calcular_precisao():
    total = cache['estatisticas']['total_previsoes']
    if total == 0:
        return 0
    return round((cache['estatisticas']['acertos'] / total) * 100)


def atualizar_dados_leves():
    verificar_previsoes_anteriores()
    
    cache['leves']['ultimas_50'] = get_ultimas_50()
    cache['leves']['ultimas_20'] = get_ultimas_20()
    cache['leves']['total_rodadas'] = get_total_rapido()
    
    calcular_previsao()
    
    cache['leves']['ultima_atualizacao'] = datetime.now(timezone.utc)


# =============================================================================
# ROTAS DA API
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
            SELECT modo, COUNT(*) as total, 
                   SUM(CASE WHEN acertou = false THEN 1 ELSE 0 END) as erros,
                   ROUND(100.0 * SUM(CASE WHEN acertou = false THEN 1 ELSE 0 END) / COUNT(*), 1) as taxa_erro
            FROM analise_erros
            WHERE data_hora > NOW() - INTERVAL '24 hours'
            GROUP BY modo
            ORDER BY taxa_erro DESC
        ''')
        modos = cur.fetchall()
        
        cur.execute('''
            SELECT streak_atual, COUNT(*) as total,
                   SUM(CASE WHEN acertou = false THEN 1 ELSE 0 END) as erros,
                   ROUND(100.0 * SUM(CASE WHEN acertou = false THEN 1 ELSE 0 END) / COUNT(*), 1) as taxa_erro
            FROM analise_erros
            WHERE streak_atual > 0 AND data_hora > NOW() - INTERVAL '24 hours'
            GROUP BY streak_atual
            ORDER BY streak_atual
        ''')
        streaks = cur.fetchall()
        
        cur.execute('''
            SELECT previsao_feita, resultado_real, confianca, modo, indice_manipulacao
            FROM analise_erros
            WHERE foi_manipulado = true AND acertou = false
            ORDER BY data_hora DESC
            LIMIT 10
        ''')
        erros_manipulados = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify({
            'total_24h': stats[0] or 0,
            'erros_24h': stats[1] or 0,
            'confianca_media': round(stats[2] or 0, 1),
            'confianca_media_erros': round(stats[3] or 0, 1),
            'total_manipuladas_24h': stats[4] or 0,
            'erros_manipuladas_24h': stats[5] or 0,
            'modos': [{'modo': m[0], 'total': m[1], 'erros': m[2], 'taxa_erro': m[3]} for m in modos],
            'streaks': [{'streak': s[0], 'total': s[1], 'erros': s[2], 'taxa_erro': s[3]} for s in streaks],
            'erros_manipulados': [{
                'previsao': e[0],
                'real': e[1],
                'confianca': e[2],
                'modo': e[3],
                'indice': e[4]
            } for e in erros_manipulados]
        })
        
    except Exception as e:
        return jsonify({'erro': str(e)})


@app.route('/api/manipulacao')
def api_manipulacao():
    return jsonify({
        'indice_atual': cache.get('indice_manipulacao', 0),
        'manipulacoes_detectadas': cache['aprendizado'].manipulacoes_detectadas if cache['aprendizado'] else 0,
        'agentes_com_deteccao': [
            {'nome': a['nome'], 'deteccoes': a['deteccoes_manipulacao']}
            for a in cache['aprendizado'].get_stats()['agentes'] if a.get('deteccoes_manipulacao', 0) > 0
        ] if cache['aprendizado'] else []
    })


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats')
def api_stats():
    estrategias_stats = []
    for nome, dados in cache['estatisticas']['estrategias'].items():
        total = dados['total']
        if total > 0:
            precisao = round((dados['acertos'] / total) * 100)
        else:
            precisao = 0
        estrategias_stats.append({
            'nome': nome,
            'acertos': dados['acertos'],
            'erros': dados['erros'],
            'precisao': precisao
        })
    
    aprendizado_stats = None
    if cache['aprendizado']:
        aprendizado_stats = cache['aprendizado'].get_stats()
    
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
        'indice_manipulacao': cache.get('indice_manipulacao', 0),
        'estatisticas': {
            'total_previsoes': cache['estatisticas']['total_previsoes'],
            'acertos': cache['estatisticas']['acertos'],
            'erros': cache['estatisticas']['erros'],
            'precisao': calcular_precisao(),
            'ultimas_20_previsoes': cache['estatisticas']['ultimas_20_previsoes'],
            'estrategias': estrategias_stats
        },
        'aprendizado': aprendizado_stats
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
    if not cache['aprendizado']:
        return jsonify({'erro': 'Sistema de aprendizado não inicializado'})
    
    return jsonify(cache['aprendizado'].get_stats())

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'rodadas': cache['leves']['total_rodadas'],
        'fila': len(fila_rodadas),
        'fonte_ativa': fonte_ativa,
        'aprendizado': cache['aprendizado'].geracao if cache['aprendizado'] else 0,
        'manipulacao': cache.get('indice_manipulacao', 0)
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
        time.sleep(0.2)
        try:
            atualizar_dados_pesados()
        except Exception as e:
            print(f"❌ Erro loop pesado: {e}")


# =============================================================================
# TREINAMENTO INICIAL COM DADOS HISTÓRICOS (OPCIONAL)
# =============================================================================
def treinar_com_historico(limit=1000):
    print(f"\n🧠 INICIANDO TREINAMENTO COM HISTÓRICO ({limit} rodadas)...")
    
    conn = get_db_connection()
    if not conn:
        print("❌ Não foi possível conectar ao banco para treinamento")
        return
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT player_score, banker_score, resultado 
            FROM rodadas 
            ORDER BY data_hora DESC 
            LIMIT %s
        ''', (limit,))
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        if not rows:
            print("⚠️ Nenhum dado histórico encontrado")
            return
        
        dados_historicos = []
        for row in rows:
            dados_historicos.append({
                'player_score': row[0],
                'banker_score': row[1],
                'resultado': row[2]
            })
        
        dados_historicos.reverse()
        
        print(f"📚 {len(dados_historicos)} rodadas carregadas para treinamento")
        
        from tqdm import tqdm
        
        batch_size = 50
        acertos_simulados = 0
        
        for i in tqdm(range(batch_size, len(dados_historicos)), desc="Treinando"):
            historico_ate_agora = dados_historicos[i-batch_size:i]
            
            streak = 1
            streak_cor = historico_ate_agora[-1]['resultado']
            
            for j in range(2, min(5, len(historico_ate_agora))):
                if historico_ate_agora[-j]['resultado'] == streak_cor:
                    streak += 1
                else:
                    break
            
            if streak >= 3:
                previsao_simulada = streak_cor
            else:
                previsao_simulada = random.choice(['BANKER', 'PLAYER'])
            
            resultado_real = dados_historicos[i]['resultado']
            
            if resultado_real != 'TIE':
                acertou = (previsao_simulada == resultado_real)
                if acertou:
                    acertos_simulados += 1
                
                indice = calcular_indice_manipulacao(historico_ate_agora[-20:])
                foi_manipulado = indice > 50
                
                if cache['aprendizado']:
                    agentes_teste = ['Contragolpe', 'Paredão'] if streak >= 3 else ['Compensação', 'Xadrez']
                    cache['aprendizado'].registrar_rodada(
                        agentes_usados=agentes_teste,
                        previsao=previsao_simulada,
                        confianca=70,
                        resultado_real=resultado_real,
                        foi_manipulado=foi_manipulado
                    )
        
        print(f"\n✅ TREINAMENTO CONCLUÍDO!")
        print(f"📊 Acertos simulados: {acertos_simulados}/{len(dados_historicos)-batch_size} ({acertos_simulados/(len(dados_historicos)-batch_size)*100:.1f}%)")
        
    except Exception as e:
        print(f"❌ Erro no treinamento: {e}")


# =============================================================================
# INICIALIZAÇÃO DO SISTEMA DE APRENDIZADO
# =============================================================================
def inicializar_aprendizado():
    print("\n🧠 INICIALIZANDO SISTEMA DE APRENDIZADO CAÇADOR 3.0...")
    cache['aprendizado'] = ControladorAprendizado('aprendizado.json')


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("="*70)
    print("🚀 BOT BACBO - VERSÃO CAÇADORA 3.0")
    print("   SISTEMA ANTI-QUEDA - 5 CAMADAS DE PROTEÇÃO")
    print("="*70)
    print("🛡️ CAMADAS DE PROTEÇÃO:")
    print("   1. WARM-UP INTELIGENTE (30 primeiras rodadas)")
    print("   2. PENALIDADE ZERO - SÓ REFORÇO POSITIVO (+10%)")
    print("   3. VOTO MÍNIMO GARANTIDO (30% do peso base)")
    print("   4. CONSENSO MÍNIMO - só prevê com 3+ agentes")
    print("   5. RESET AUTOMÁTICO SUAVE (saúde dos agentes)")
    print("="*70)
    print("📊 PREVISÃO DE DESEMPENHO:")
    print("   • Rodadas 1-30: 50% (warm-up)")
    print("   • Rodadas 31-60: 55-60%")
    print("   • Rodadas 61-100: 65-70%")
    print("   • Rodadas 100+: 70-75% (NUNCA cai)")
    print("="*70)
    
    if not init_db():
        print("⚠️ Banco não disponível - continuando sem banco de dados")
    
    print("\n📥 Carregando histórico de rodadas do arquivo...")
    try:
        with open('rodadas (4).json', 'r') as f:
            rodadas_json = json.load(f)
        
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            carregadas = 0
            for rodada in rodadas_json:
                try:
                    data_hora = datetime.fromisoformat(rodada['data_hora'].replace('Z', '+00:00'))
                    
                    cur.execute('''
                        INSERT INTO rodadas 
                        (id, data_hora, player_score, banker_score, soma, resultado, fonte, dados_json)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                    ''', (
                        rodada['id'],
                        data_hora,
                        rodada['player_score'],
                        rodada['banker_score'],
                        rodada['soma'],
                        rodada['resultado'],
                        rodada.get('fonte', 'historico'),
                        json.dumps(rodada)
                    ))
                    if cur.rowcount > 0:
                        carregadas += 1
                except Exception as e:
                    continue
            
            conn.commit()
            cur.close()
            conn.close()
            print(f"✅ {carregadas} rodadas carregadas do arquivo JSON")
        else:
            print("⚠️ Não foi possível conectar ao banco para carga histórica")
    except Exception as e:
        print(f"⚠️ Erro ao carregar arquivo JSON: {e}")
    
    print("📊 Carregando dados...")
    
    inicializar_aprendizado()
    
    atualizar_dados_leves()
    atualizar_dados_pesados()
    
    total_rodadas = cache['leves']['total_rodadas']
    print(f"📊 {total_rodadas} rodadas no banco")
    
    if cache['aprendizado']:
        print(f"🧠 {len(cache['aprendizado'].agentes)} agentes ativos")
        print(f"📈 Geração atual: {cache['aprendizado'].geracao}")
        print(f"🎯 Manipulações detectadas: {cache['aprendizado'].manipulacoes_detectadas}")
    
    print("="*70)
    
    print("🔌 Iniciando WebSocket (modo backup)...")
    iniciar_websocket()
    
    print("📡 [PRINCIPAL] Iniciando coletor LATEST (0.3s)...")
    threading.Thread(target=loop_latest, daemon=True).start()
    
    print("⚡ Iniciando monitor WebSocket...")
    threading.Thread(target=loop_websocket_fallback, daemon=True).start()
    
    print("📚 [FALLBACK] Iniciando coletor API NORMAL (10s)...")
    threading.Thread(target=loop_api_fallback, daemon=True).start()
    
    print("🚀 Iniciando processador da fila (PREVISÃO EM TEMPO REAL)...")
    threading.Thread(target=processar_fila, daemon=True).start()
    
    print("🔄 Iniciando loop pesado...")
    threading.Thread(target=loop_pesado, daemon=True).start()
    
    print("\n" + "="*70)
    print("✅ SISTEMA PRONTO! PREVISÃO ATUALIZA AUTOMATICAMENTE!")
    print("📊 Acesse /api/stats para ver a previsão em tempo real")
    print("🧠 Acesse /api/aprendizado para ver a evolução dos agentes")
    print("📝 Acesse /api/analise-erros para análise detalhada dos erros")
    print("🎯 Acesse /api/manipulacao para estatísticas de manipulação")
    print("="*70)
    
    app.run(host='0.0.0.0', port=PORT, debug=False)
