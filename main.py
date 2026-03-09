# =============================================================================
# main.py - VERSÃO COMPLETA COM RL + NEUROEVOLUTION + ANÁLISE DE ERROS
# =============================================================================
# ✅ SISTEMA DE APRENDIZADO: Cada estratégia é um agente que aprende
# ✅ NEUROEVOLUÇÃO: Mutações, crossover e seleção natural
# ✅ 10 ESTRATÉGIAS TRANSFORMADAS EM AGENTES
# ✅ MEMÓRIA PERSISTENTE: Salva em JSON e nunca reseta
# ✅ TABELA DE ANÁLISE DE ERROS: Cada erro é registrado com contexto completo
# ✅ ADAPTAÇÃO CONTÍNUA: Acompanha as mudanças do algoritmo
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
    'aprendizado': None,  # Será preenchido com o controlador
    'ultimo_contexto_erro': None  # Contexto para análise de erros
}

# =============================================================================
# INICIALIZAÇÃO FLASK
# =============================================================================
app = Flask(__name__)
CORS(app)
session = requests.Session()
session.headers.update(HEADERS)

# =============================================================================
# 🧠 SISTEMA DE APRENDIZADO: RL + NEUROEVOLUTION
# =============================================================================

class AgenteEstrategia:
    """
    Cada estratégia vira um agente que aprende com seus erros/acertos
    """
    def __init__(self, nome, pesos_base, taxa_mutacao=0.15):
        self.nome = nome
        self.pesos_base = pesos_base.copy()  # {'banker': X, 'player': Y}
        self.pesos_atuais = pesos_base.copy()
        self.acertos = 0
        self.erros = 0
        self.total_uso = 0
        self.taxa_mutacao = taxa_mutacao
        self.ultima_atuacao = datetime.now()
        self.historico_precisao = deque(maxlen=50)
        self.idade_geracoes = 0
        
    @property
    def precisao(self):
        if self.total_uso == 0:
            return 0
        return (self.acertos / self.total_uso) * 100
    
    @property
    def forca(self):
        """Quão forte o agente está baseado em precisão e uso"""
        if self.total_uso == 0:
            return 0.5
        return (self.precisao / 100) * min(1.0, self.total_uso / 50)
    
    def atuar(self, dados, modo, votos_originais):
        """
        Recebe os votos da estratégia original e aplica os pesos aprendidos
        """
        banker = votos_originais.get('banker', 0)
        player = votos_originais.get('player', 0)
        
        # Aplica pesos evolutivos
        banker_ajustado = int(banker * self.pesos_atuais.get('banker', 1.0))
        player_ajustado = int(player * self.pesos_atuais.get('player', 1.0))
        
        return {
            'banker': banker_ajustado,
            'player': player_ajustado,
            'motivo': votos_originais.get('motivo', '')
        }
    
    def registrar_resultado(self, acertou, confianca=0):
        """
        Registra se a estratégia acertou ou errou
        """
        self.total_uso += 1
        if acertou:
            self.acertos += 1
        else:
            self.erros += 1
        
        self.historico_precisao.append(1 if acertou else 0)
        self.ultima_atuacao = datetime.now()
        
        # Recompensa/penalidade nos pesos baseado no resultado
        self._aplicar_reforco(acertou, confianca)
    
    def _aplicar_reforco(self, acertou, confianca):
        """
        Aplica aprendizado por reforço nos pesos
        """
        if acertou:
            # Reforço positivo: aumenta os pesos (aprendeu)
            fator_reforco = 1.0 + (confianca / 100) * 0.1
            self.pesos_atuais['banker'] *= fator_reforco
            self.pesos_atuais['player'] *= fator_reforco
        else:
            # Penalidade: reduz os pesos (errou)
            fator_penalidade = 0.95
            self.pesos_atuais['banker'] *= fator_penalidade
            self.pesos_atuais['player'] *= fator_penalidade
        
        # Mantém os pesos dentro de limites razoáveis
        self.pesos_atuais['banker'] = max(0.1, min(3.0, self.pesos_atuais['banker']))
        self.pesos_atuais['player'] = max(0.1, min(3.0, self.pesos_atuais['player']))
    
    def mutar(self):
        """
        Neuroevolução: mutação aleatória nos pesos
        """
        if random.random() < self.taxa_mutacao:
            gene = random.choice(['banker', 'player'])
            # Mutação mais forte se estiver velho sem uso
            fator_idade = min(2.0, 1.0 + (self.idade_geracoes / 20))
            delta = random.uniform(-0.15, 0.25) * fator_idade
            
            self.pesos_atuais[gene] += delta
            self.pesos_atuais[gene] = max(0.1, min(3.0, self.pesos_atuais[gene]))
            
            print(f"🧬 MUTAÇÃO em {self.nome}: {gene} → {self.pesos_atuais[gene]:.2f} (idade: {self.idade_geracoes})")
            return True
        return False
    
    def resetar_para_base(self):
        """Reseta para os pesos base (quando está muito ruim)"""
        self.pesos_atuais = self.pesos_base.copy()
        self.acertos = int(self.acertos * 0.5)  # Preserva metade do histórico
        self.erros = int(self.erros * 0.5)
        print(f"🔄 RESET {self.nome} para pesos base")
    
    def para_dict(self):
        """Serializa o agente para salvar"""
        return {
            'nome': self.nome,
            'pesos_base': self.pesos_base,
            'pesos_atuais': self.pesos_atuais,
            'acertos': self.acertos,
            'erros': self.erros,
            'total_uso': self.total_uso,
            'taxa_mutacao': self.taxa_mutacao,
            'idade_geracoes': self.idade_geracoes,
            'historico_precisao': list(self.historico_precisao)
        }
    
    @classmethod
    def de_dict(cls, dados):
        """Recria agente a partir de dicionário"""
        agente = cls(dados['nome'], dados['pesos_base'])
        agente.pesos_atuais = dados['pesos_atuais']
        agente.acertos = dados['acertos']
        agente.erros = dados['erros']
        agente.total_uso = dados['total_uso']
        agente.taxa_mutacao = dados['taxa_mutacao']
        agente.idade_geracoes = dados['idade_geracoes']
        agente.historico_precisao = deque(dados['historico_precisao'], maxlen=50)
        return agente


class ControladorAprendizado:
    """
    Controlador principal do sistema RL + Neuroevolução
    """
    def __init__(self, arquivo_estado='aprendizado.json'):
        self.arquivo_estado = arquivo_estado
        self.agentes = {}
        self.geracao = 0
        self.melhor_precisao_global = 0
        self.historico_evolucao = []
        self.total_rodadas_processadas = 0
        
        # Pesos base iniciais para cada estratégia (da sua tese)
        self.pesos_iniciais = {
            'Compensação': {'banker': 0.7, 'player': 0.7},      # Reduzido (confiabilidade média)
            'Paredão': {'banker': 1.2, 'player': 1.2},          # Aumentado (boa para streaks)
            'Moedor': {'banker': 1.0, 'player': 1.0},           # Neutro
            'Xadrez': {'banker': 0.6, 'player': 0.6},           # Reduzido (menos confiável)
            'Contragolpe': {'banker': 1.5, 'player': 1.5},      # Muito reforçado (85% acerto)
            'Reset Cluster': {'banker': 1.2, 'player': 1.2},    # Bom pós-empate
            'Falsa Alternância': {'banker': 1.1, 'player': 1.1}, # Médio
            'Saturação': {'banker': 1.3, 'player': 1.3},        # Forte (ponto de virada)
            'Meta-Algoritmo': {'banker': 1.4, 'player': 1.4},   # Muito forte (modo detector)
            'Horário': {'banker': 1.0, 'player': 1.0}           # Neutro (fator externo)
        }
        
        # Tenta carregar estado anterior
        self.carregar_estado()
        
        # Se não carregou nada, inicializa agentes
        if not self.agentes:
            self._inicializar_agentes()
    
    def _inicializar_agentes(self):
        """Cria os agentes iniciais"""
        for nome, pesos in self.pesos_iniciais.items():
            self.agentes[nome] = AgenteEstrategia(nome, pesos)
        print(f"✅ {len(self.agentes)} agentes inicializados")
    
    def obter_votos_ajustados(self, dados, modo, votos_por_estrategia):
        """
        Recebe votos originais de cada estratégia e aplica os pesos aprendidos
        Retorna: votos_banker, votos_player, agentes_ativos
        """
        votos_banker_total = 0
        votos_player_total = 0
        agentes_ativos = []
        detalhes = []
        
        for nome_estrategia, votos_originais in votos_por_estrategia.items():
            if nome_estrategia in self.agentes:
                agente = self.agentes[nome_estrategia]
                
                # Pula se a estratégia não votou
                if votos_originais.get('banker', 0) == 0 and votos_originais.get('player', 0) == 0:
                    continue
                
                # Agente atua nos votos
                votos_ajustados = agente.atuar(dados, modo, votos_originais)
                
                if votos_ajustados['banker'] > 0 or votos_ajustados['player'] > 0:
                    votos_banker_total += votos_ajustados['banker']
                    votos_player_total += votos_ajustados['player']
                    agentes_ativos.append(nome_estrategia)
                    
                    detalhes.append(
                        f"{nome_estrategia}: B{votos_ajustados['banker']} P{votos_ajustados['player']} "
                        f"(pesos: {agente.pesos_atuais['banker']:.2f}/{agente.pesos_atuais['player']:.2f})"
                    )
        
        if detalhes:
            print("\n📊 VOTOS COM APRENDIZADO:")
            for d in detalhes:
                print(f"   {d}")
        
        return votos_banker_total, votos_player_total, agentes_ativos
    
    def registrar_rodada(self, agentes_usados, previsao, confianca, resultado_real):
        """
        Registra o resultado para cada agente usado e aplica aprendizado
        """
        if resultado_real == 'TIE':
            return  # Ignora empates
        
        for nome_agente in agentes_usados:
            if nome_agente in self.agentes:
                agente = self.agentes[nome_agente]
                acertou = (previsao == resultado_real)
                agente.registrar_resultado(acertou, confianca)
        
        self.total_rodadas_processadas += 1
        
        # A cada 25 rodadas, executa neuroevolução
        if self.total_rodadas_processadas % 25 == 0:
            self.evoluir()
        
        # A cada 100 rodadas, salva estado
        if self.total_rodadas_processadas % 100 == 0:
            self.salvar_estado()
    
    def evoluir(self):
        """
        Processo de neuroevolução: mutações e seleção natural
        """
        self.geracao += 1
        print(f"\n🧬 EVOLUÇÃO GERAL #{self.geracao}")
        
        # Aumenta idade de todos os agentes
        for agente in self.agentes.values():
            agente.idade_geracoes += 1
        
        # Calcula precisão média e ranking
        ranking = []
        for nome, agente in self.agentes.items():
            if agente.total_uso > 0:
                forca = agente.forca
                ranking.append((nome, agente.precisao, forca, agente.total_uso))
        
        ranking.sort(key=lambda x: x[1], reverse=True)
        
        if ranking:
            precisao_media = np.mean([r[1] for r in ranking])
            print(f"📊 Precisão média: {precisao_media:.1f}%")
            
            # Mostra top 3 e bottom 3
            print("\n🏆 TOP 3 AGENTES:")
            for i, (nome, prec, forca, uso) in enumerate(ranking[:3]):
                print(f"   {i+1}. {nome}: {prec:.1f}% ({uso} usos) força: {forca:.2f}")
            
            if len(ranking) > 3:
                print("\n💀 BOTTOM 3:")
                for i, (nome, prec, forca, uso) in enumerate(ranking[-3:]):
                    print(f"   {len(ranking)-2+i}. {nome}: {prec:.1f}% ({uso} usos)")
            
            # Melhor precisão global
            melhor_atual = ranking[0][1]
            if melhor_atual > self.melhor_precisao_global:
                self.melhor_precisao_global = melhor_atual
                print(f"\n🏆 NOVA MELHOR PRECISÃO GLOBAL: {melhor_atual:.1f}%")
                self.salvar_estado()  # Salva imediatamente ao bater recorde
        
        # Aplica mutações em todos os agentes (neuroevolução)
        mutacoes = 0
        for agente in self.agentes.values():
            if agente.mutar():
                mutacoes += 1
        
        print(f"\n🧬 {mutacoes} mutações aplicadas")
        
        # Reseta agentes muito ruins
        for nome, agente in self.agentes.items():
            if agente.total_uso > 30 and agente.precisao < 30:
                print(f"⚠️ Agente {nome} com precisão {agente.precisao:.1f}% - resetando")
                agente.resetar_para_base()
        
        self.historico_evolucao.append({
            'geracao': self.geracao,
            'data': datetime.now().isoformat(),
            'precisao_media': precisao_media if ranking else 0,
            'melhor': ranking[0][0] if ranking else '',
            'melhor_precisao': ranking[0][1] if ranking else 0
        })
    
    def salvar_estado(self):
        """Salva o estado atual do aprendizado"""
        try:
            estado = {
                'geracao': self.geracao,
                'melhor_precisao_global': self.melhor_precisao_global,
                'total_rodadas_processadas': self.total_rodadas_processadas,
                'historico_evolucao': self.historico_evolucao[-50:],  # Últimas 50
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
        """Carrega estado anterior se existir"""
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
            self.historico_evolucao = estado.get('historico_evolucao', [])
            
            # Recria agentes
            for nome, dados_agente in estado.get('agentes', {}).items():
                self.agentes[nome] = AgenteEstrategia.de_dict(dados_agente)
            
            print(f"✅ Aprendizado carregado: {self.geracao} gerações, {self.total_rodadas_processadas} rodadas processadas")
            print(f"🏆 Melhor precisão global: {self.melhor_precisao_global:.1f}%")
            return True
        except Exception as e:
            print(f"⚠️ Erro ao carregar estado: {e}")
            return False
    
    def get_stats(self):
        """Retorna estatísticas do aprendizado"""
        stats = {
            'geracao': self.geracao,
            'total_rodadas': self.total_rodadas_processadas,
            'melhor_precisao_global': round(self.melhor_precisao_global, 1),
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
                'idade': agente.idade_geracoes
            })
        
        # Ordena por precisão
        stats['agentes'].sort(key=lambda x: x['precisao'], reverse=True)
        
        return stats


# =============================================================================
# FUNÇÕES DO BANCO CORRIGIDAS - PG8000 COM SSL + NOVA TABELA DE ERROS
# =============================================================================

def get_db_connection():
    """Cria conexão com o banco usando pg8000 com SSL"""
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
    """Inicializa as tabelas no banco - AGORA COM TABELA DE ANÁLISE DE ERROS"""
    conn = get_db_connection()
    if not conn:
        print("⚠️ Banco não disponível - continuando sem banco")
        return False
    
    try:
        cur = conn.cursor()
        
        # Tabela de rodadas
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
        
        # Índices
        cur.execute('CREATE INDEX IF NOT EXISTS idx_data_hora ON rodadas(data_hora DESC)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_resultado ON rodadas(resultado)')
        
        # Tabela de previsões
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
        
        # ===== NOVA TABELA: ANÁLISE DE ERROS =====
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
                acertou BOOLEAN,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # Índices para consultas rápidas
        cur.execute('CREATE INDEX IF NOT EXISTS idx_erros_data ON analise_erros(data_hora DESC)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_erros_acertou ON analise_erros(acertou)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_erros_modo ON analise_erros(modo)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_erros_streak ON analise_erros(streak_atual)')
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Tabelas criadas/verificadas com sucesso (incluindo análise de erros)")
        return True
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        return False

def salvar_rodada(rodada, fonte):
    """Salva rodada no banco"""
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

def salvar_previsao(previsao, resultado_real, acertou, pesos_agentes=None):
    """Salva previsão no histórico"""
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

# ===== NOVA FUNÇÃO: SALVAR ERRO PARA ANÁLISE =====
def salvar_erro_para_analise(ultima, resultado_real, acertou, dados_contexto):
    """
    Salva erro com contexto completo para análise posterior
    """
    if not acertou:  # Só salva quando erra (mas podemos salvar todos se quiser)
        conn = get_db_connection()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            
            # Converte últimos 5 resultados para string
            ultimos_5 = ','.join(dados_contexto.get('ultimos_5', []))
            
            cur.execute('''
                INSERT INTO analise_erros 
                (data_hora, previsao_feita, resultado_real, confianca, modo, 
                 streak_atual, banker_50, player_50, diferenca_percentual,
                 ultimos_5_resultados, agentes_ativos, pesos_agentes, acertou)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                acertou
            ))
            conn.commit()
            cur.close()
            conn.close()
            print(f"📝 Erro registrado para análise: {ultima['previsao']} vs {resultado_real}")
        except Exception as e:
            print(f"❌ Erro ao registrar análise: {e}")


# =============================================================================
# FUNÇÕES DO BANCO (LEVES)
# =============================================================================

def get_ultimas_50():
    """Busca últimas 50 rodadas"""
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
    """Busca últimas 20 rodadas formatadas"""
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
            # Converte para string ISO e depois para datetime
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
    """Conta total de rodadas"""
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
    """Conta rodadas em um período"""
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
    """Atualiza estatísticas de períodos"""
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
    """Alterna entre fontes baseado em falhas"""
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
    """Busca rodada mais recente da API Latest"""
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
    """Processa mensagens do WebSocket"""
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
    """Callback de erro do WebSocket"""
    global falhas_websocket, fonte_ativa
    if fonte_ativa == 'websocket':
        falhas_websocket += 1
        fontes_status['websocket']['falhas'] += 1
        print(f"🔌 WS Erro: {error} - falha {falhas_websocket}/{LIMITE_FALHAS}")
        alternar_fonte()

def on_ws_close(ws, close_status_code, close_msg):
    """Callback de fechamento do WebSocket"""
    global falhas_websocket, fonte_ativa
    if fonte_ativa == 'websocket':
        falhas_websocket += 1
        fontes_status['websocket']['falhas'] += 1
        print(f"🔌 WS Fechado - falha {falhas_websocket}/{LIMITE_FALHAS}")
        alternar_fonte()
    time.sleep(5)
    iniciar_websocket()

def on_ws_open(ws):
    """Callback de abertura do WebSocket"""
    global falhas_websocket, fonte_ativa
    print("✅ WEBSOCKET CONECTADO! (modo backup)")
    if fonte_ativa == 'websocket':
        falhas_websocket = 0

def iniciar_websocket():
    """Inicia conexão WebSocket em thread separada"""
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
    """Busca rodadas da API normal"""
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
    """Carrega histórico completo da API"""
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
    """Loop principal de coleta da API Latest"""
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
    """Monitor do WebSocket"""
    print("⚡ [BACKUP] Monitor WebSocket iniciado...")
    while True:
        try:
            time.sleep(1)
        except Exception as e:
            print(f"❌ Erro no monitor WS: {e}")
            time.sleep(1)

def loop_api_fallback():
    """Loop de coleta da API Normal"""
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
    """Processa fila de rodadas e atualiza previsões"""
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
# ESTRATÉGIAS DE PREVISÃO - VERSÃO FINAL CORRIGIDA
# =============================================================================

def get_dados_ordenados(dados):
    """Retorna dados na ordem correta (mais recentes primeiro)"""
    return list(reversed(dados)) if dados else []

def verificar_delay_pos_empate(dados):
    """Verifica se rodada anterior foi TIE e retorna fator de redução"""
    if len(dados) < 2:
        return 1.0
    if dados[1]['resultado'] == 'TIE':
        print("⚠️ DELAY PÓS-EMPATE ATIVO - Rodada anterior foi TIE")
        return 0.7
    return 1.0

def detectar_modo_tese(dados):
    """Detecta o modo do algoritmo baseado nos dados"""
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


# =============================================================================
# ESTRATÉGIA 1: COMPENSAÇÃO
# =============================================================================
def estrategia_compensacao_tese(dados, modo):
    """Aposta no lado que está atrás"""
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


# =============================================================================
# ESTRATÉGIA 2: PAREDÃO
# =============================================================================
def estrategia_paredao_tese(dados, modo):
    """Aposta na continuação de sequências longas"""
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


# =============================================================================
# ESTRATÉGIA 3: MOEDOR
# =============================================================================
def estrategia_moedor_tese(dados, modo):
    """Reage a clusters de empates"""
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


# =============================================================================
# ESTRATÉGIA 4: XADREZ
# =============================================================================
def estrategia_xadrez_tese(dados, modo):
    """Aposta na continuação da alternância"""
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


# =============================================================================
# ESTRATÉGIA 5: CONTRAGOLPE
# =============================================================================
def estrategia_contragolpe_tese(dados, modo):
    """3 iguais → 1 diferente → volta ao original"""
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


# =============================================================================
# ESTRATÉGIA 6: RESET CLUSTER
# =============================================================================
def estrategia_reset_cluster_tese(dados, modo):
    """70% volta à dominante, 30% vai à oposta após cluster de empates"""
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


# =============================================================================
# ESTRATÉGIA 7: FALSA ALTERNÂNCIA
# =============================================================================
def estrategia_falsa_alternancia_tese(dados, modo):
    """Números extremos"""
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


# =============================================================================
# ESTRATÉGIA 8: META-ALGORITMO
# =============================================================================
def aplicar_meta_tese(votos_banker, votos_player, dados, modo):
    """Ajusta pesos baseado no modo e na distribuição real"""
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


# =============================================================================
# ESTRATÉGIA 9: PONTO DE SATURAÇÃO
# =============================================================================
def estrategia_saturacao_tese(dados):
    """Detecta quando o algoritmo está 'cansado' e vai mudar"""
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


# =============================================================================
# ESTRATÉGIA 10: EFEITO CALENDÁRIO
# =============================================================================
def estrategia_horario_tese():
    """Ajuste por horário"""
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
    """Calcula confiança de forma realista"""
    
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
    
    limites = {'AGRESSIVO': 92, 'PREDATORIO': 88, 'MOEDOR': 86, 'EQUILIBRADO': 90}
    max_confianca = limites.get(modo, 90) + ajuste_horario['peso_bonus']
    
    return min(max_confianca, max(50, round(confianca)))


# =============================================================================
# FUNÇÃO PARA CALCULAR CONTEXTO DE ERRO
# =============================================================================
def calcular_contexto_erro(dados_ord, modo, ultima_previsao):
    """Calcula contexto completo para análise de erros"""
    if not dados_ord or len(dados_ord) < 5:
        return {}
    
    # Calcula streak atual
    streak = 1
    streak_cor = dados_ord[0]['resultado'] if dados_ord[0]['resultado'] != 'TIE' else None
    
    if streak_cor:
        for i in range(1, min(10, len(dados_ord))):
            if dados_ord[i]['resultado'] == streak_cor:
                streak += 1
            else:
                break
    
    # Calcula distribuição
    player_50 = sum(1 for r in dados_ord[:50] if r['resultado'] == 'PLAYER')
    banker_50 = sum(1 for r in dados_ord[:50] if r['resultado'] == 'BANKER')
    
    diferenca = abs(banker_50 - player_50) / max(1, (banker_50 + player_50)) * 100
    
    # Últimos 5 resultados
    ultimos_5 = [r['resultado'] for r in dados_ord[:5] if r['resultado'] != 'TIE'][:5]
    
    # Pesos dos agentes
    pesos_agentes = {}
    if cache['aprendizado']:
        for nome, agente in cache['aprendizado'].agentes.items():
            if agente.total_uso > 0:
                pesos_agentes[nome] = {
                    'pesos': agente.pesos_atuais,
                    'precisao': agente.precisao
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
# FUNÇÃO PRINCIPAL DE PREVISÃO (COM APRENDIZADO INTEGRADO)
# =============================================================================
def calcular_previsao_com_aprendizado():
    """Versão da previsão que usa o sistema de aprendizado"""
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
    
    # Distribuição atual
    player_50 = sum(1 for r in dados_ord[:50] if r['resultado'] == 'PLAYER')
    banker_50 = sum(1 for r in dados_ord[:50] if r['resultado'] == 'BANKER')
    ties_50 = sum(1 for r in dados_ord[:50] if r['resultado'] == 'TIE')
    
    print(f"\n{'='*60}")
    print(f"📊 ANÁLISE ATUAL:")
    print(f"   Banker: {banker_50} ({banker_50/(banker_50+player_50)*100:.1f}% das não-empates)")
    print(f"   Player: {player_50} ({player_50/(banker_50+player_50)*100:.1f}% das não-empates)")
    print(f"   Ties: {ties_50}")
    print(f"   Modo detectado: {modo}")
    print(f"{'='*60}")
    
    # Coleta votos originais de cada estratégia
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
    
    # Aplica META-ALGORITMO (estratégia 8)
    votos_banker_bruto = sum(v.get('banker', 0) for v in votos_originais.values())
    votos_player_bruto = sum(v.get('player', 0) for v in votos_originais.values())
    votos_banker_bruto, votos_player_bruto, meta_nome = aplicar_meta_tese(
        votos_banker_bruto, votos_player_bruto, dados_ord, modo
    )
    
    # Adiciona o META como uma "estratégia virtual" nos votos originais
    if meta_nome:
        votos_originais['Meta-Algoritmo'] = {'banker': 0, 'player': 0, 'motivo': meta_nome}
    
    # Adiciona Horário como estratégia virtual
    if ajuste_horario['peso_bonus'] != 0:
        votos_originais['Horário'] = {'banker': 0, 'player': 0, 'motivo': ajuste_horario['periodo']}
    
    # Agora, aplica o aprendizado dos agentes aos votos
    votos_banker, votos_player, agentes_ativos = cache['aprendizado'].obter_votos_ajustados(
        dados_ord, modo, votos_originais
    )
    
    # Se não houver votos, usa a distribuição real como fallback
    if votos_banker == 0 and votos_player == 0:
        previsao = 'BANKER' if banker_50 > player_50 else 'PLAYER'
        simbolo = '🔴' if previsao == 'BANKER' else '🔵'
        confianca = 60
        estrategias_finais = ['Distribuição real (fallback)']
        
        print(f"\n⚠️ NENHUM VOTO DAS ESTRATÉGIAS - Usando distribuição real")
        
        resultado_previsao = {
            'modo': modo,
            'previsao': previsao,
            'simbolo': simbolo,
            'confianca': confianca,
            'estrategias': estrategias_finais
        }
        
        cache['leves']['previsao'] = resultado_previsao
        cache['ultima_previsao'] = resultado_previsao
        cache['ultimo_contexto_erro'] = calcular_contexto_erro(dados_ord, modo, resultado_previsao)
        
        return resultado_previsao
    
    # Decisão final baseada nos votos ajustados
    if votos_banker > votos_player:
        previsao = 'BANKER'
        simbolo = '🔴'
    elif votos_player > votos_banker:
        previsao = 'PLAYER'
        simbolo = '🔵'
    else:
        # Empate - usa distribuição real
        previsao = 'BANKER' if banker_50 > player_50 else 'PLAYER'
        simbolo = '🔴' if previsao == 'BANKER' else '🔵'
        agentes_ativos = ['Distribuição real (empate)']
    
    # Calcula confiança
    confianca = calcular_confianca_tese(votos_banker, votos_player, agentes_ativos, modo, ajuste_horario, fator_delay)
    
    print(f"\n🎯 DECISÃO FINAL: {simbolo} {previsao} com {confianca}%")
    print(f"   Agentes ativos: {len(agentes_ativos)}")
    print(f"{'='*60}\n")
    
    resultado_previsao = {
        'modo': modo,
        'previsao': previsao,
        'simbolo': simbolo,
        'confianca': confianca,
        'estrategias': agentes_ativos[:4]  # Limita a 4 para exibição
    }
    
    cache['leves']['previsao'] = resultado_previsao
    cache['ultima_previsao'] = resultado_previsao
    cache['ultimo_contexto_erro'] = calcular_contexto_erro(dados_ord, modo, resultado_previsao)
    
    return resultado_previsao


# Função de compatibilidade com o código antigo
def calcular_previsao():
    """Wrapper para manter compatibilidade"""
    return calcular_previsao_com_aprendizado()


# =============================================================================
# SISTEMA DE APRENDIZADO - VERIFICAÇÃO DE PREVISÕES (AGORA COM ANÁLISE DE ERROS)
# =============================================================================
def verificar_previsoes_anteriores():
    """Verifica acertos de previsões anteriores e alimenta o aprendizado"""
    if cache.get('ultima_previsao') and cache.get('ultimo_resultado_real'):
        ultima = cache['ultima_previsao']
        resultado_real = cache['ultimo_resultado_real']
        contexto_erro = cache.get('ultimo_contexto_erro', {})
        
        # Empates são ignorados para aprendizado
        if resultado_real == 'TIE':
            print("⏸️ Resultado foi TIE - Ignorando para aprendizado")
            cache['ultima_previsao'] = None
            cache['ultimo_resultado_real'] = None
            cache['ultimo_contexto_erro'] = None
            return
        
        acertou = (ultima['previsao'] == resultado_real)
        
        # Prepara pesos dos agentes para salvar
        pesos_agentes = {}
        if cache['aprendizado']:
            for nome, agente in cache['aprendizado'].agentes.items():
                if agente.total_uso > 0:
                    pesos_agentes[nome] = {
                        'pesos': agente.pesos_atuais,
                        'precisao': agente.precisao
                    }
        
        # Salva no banco
        salvar_previsao(ultima, resultado_real, acertou, pesos_agentes)
        
        # ===== NOVO: SALVA ERRO PARA ANÁLISE =====
        salvar_erro_para_analise(ultima, resultado_real, acertou, contexto_erro)
        
        # Atualiza estatísticas gerais
        cache['estatisticas']['total_previsoes'] += 1
        if acertou:
            cache['estatisticas']['acertos'] += 1
        else:
            cache['estatisticas']['erros'] += 1
        
        # ALIMENTA O SISTEMA DE APRENDIZADO
        if cache['aprendizado']:
            cache['aprendizado'].registrar_rodada(
                agentes_usados=ultima.get('estrategias', []),
                previsao=ultima['previsao'],
                confianca=ultima['confianca'],
                resultado_real=resultado_real
            )
        
        print(f"\n📊 PROCESSANDO PREVISÃO #{cache['estatisticas']['total_previsoes']}")
        print(f"   Previsão: {ultima['simbolo']} {ultima['previsao']} vs Real: {resultado_real} = {'✅' if acertou else '❌'}")
        
        # MAPEAMENTO PARA ESTATÍSTICAS (mantido do código original)
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
        
        # Processa cada estratégia ativa (para estatísticas)
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
        
        # Adiciona ao histórico recente
        previsao_historico = {
            'data': datetime.now().strftime('%d/%m %H:%M:%S'),
            'previsao': ultima['previsao'],
            'simbolo': ultima['simbolo'],
            'confianca': ultima['confianca'],
            'resultado_real': resultado_real,
            'acertou': acertou,
            'estrategias': ultima['estrategias']
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
    """Calcula precisão atual"""
    total = cache['estatisticas']['total_previsoes']
    if total == 0:
        return 0
    return round((cache['estatisticas']['acertos'] / total) * 100)


# =============================================================================
# ATUALIZAÇÃO DE DADOS LEVES
# =============================================================================
def atualizar_dados_leves():
    """Atualiza dados leves e previsão"""
    verificar_previsoes_anteriores()
    
    cache['leves']['ultimas_50'] = get_ultimas_50()
    cache['leves']['ultimas_20'] = get_ultimas_20()
    cache['leves']['total_rodadas'] = get_total_rapido()
    
    # Calcula nova previsão
    calcular_previsao()
    
    cache['leves']['ultima_atualizacao'] = datetime.now(timezone.utc)


# =============================================================================
# NOVAS ROTAS PARA ANÁLISE DE ERROS
# =============================================================================

@app.route('/api/analise-erros')
def api_analise_erros():
    """Endpoint para análise detalhada de erros"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'erro': 'Banco indisponível'})
    
    try:
        cur = conn.cursor()
        
        # Estatísticas gerais das últimas 24h
        cur.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN acertou = false THEN 1 ELSE 0 END) as total_erros,
                AVG(confianca) as confianca_media,
                AVG(CASE WHEN acertou = false THEN confianca ELSE NULL END) as confianca_media_erros
            FROM analise_erros
            WHERE data_hora > NOW() - INTERVAL '24 hours'
        ''')
        stats = cur.fetchone()
        
        # Quais modos mais erram
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
        
        # Em quais streaks mais erram
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
        
        # Últimos 20 erros
        cur.execute('''
            SELECT data_hora, previsao_feita, resultado_real, confianca, modo, streak_atual
            FROM analise_erros
            WHERE acertou = false
            ORDER BY data_hora DESC
            LIMIT 20
        ''')
        ultimos_erros = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify({
            'total_24h': stats[0] or 0,
            'erros_24h': stats[1] or 0,
            'confianca_media': round(stats[2] or 0, 1),
            'confianca_media_erros': round(stats[3] or 0, 1),
            'modos': [{'modo': m[0], 'total': m[1], 'erros': m[2], 'taxa_erro': m[3]} for m in modos],
            'streaks': [{'streak': s[0], 'total': s[1], 'erros': s[2], 'taxa_erro': s[3]} for s in streaks],
            'ultimos_erros': [{
                'data': e[0].strftime('%d/%m %H:%M:%S'),
                'previsao': e[1],
                'real': e[2],
                'confianca': e[3],
                'modo': e[4],
                'streak': e[5]
            } for e in ultimos_erros]
        })
        
    except Exception as e:
        return jsonify({'erro': str(e)})


# =============================================================================
# ROTAS EXISTENTES (MANTIDAS)
# =============================================================================

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
    
    # Adiciona estatísticas do aprendizado
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
    """Rota específica para estatísticas do aprendizado"""
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
        'aprendizado': cache['aprendizado'].geracao if cache['aprendizado'] else 0
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
    """Loop para atualizar dados pesados"""
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
    """
    Treina o sistema com dados históricos existentes no banco
    """
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
        
        # Converte para formato esperado
        dados_historicos = []
        for row in rows:
            dados_historicos.append({
                'player_score': row[0],
                'banker_score': row[1],
                'resultado': row[2]
            })
        
        # Inverte para ordem cronológica
        dados_historicos.reverse()
        
        print(f"📚 {len(dados_historicos)} rodadas carregadas para treinamento")
        
        # Simula o processamento em lote
        from tqdm import tqdm
        
        batch_size = 50
        acertos_simulados = 0
        
        for i in tqdm(range(batch_size, len(dados_historicos)), desc="Treinando"):
            # Pega as últimas 50 até este ponto
            historico_ate_agora = dados_historicos[i-batch_size:i]
            
            # Simula uma previsão (simplificada para treino)
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
                
                # Alimenta agentes
                if cache['aprendizado']:
                    agentes_teste = ['Contragolpe', 'Paredão'] if streak >= 3 else ['Compensação', 'Xadrez']
                    cache['aprendizado'].registrar_rodada(
                        agentes_usados=agentes_teste,
                        previsao=previsao_simulada,
                        confianca=70,
                        resultado_real=resultado_real
                    )
        
        print(f"\n✅ TREINAMENTO CONCLUÍDO!")
        print(f"📊 Acertos simulados: {acertos_simulados}/{len(dados_historicos)-batch_size} ({acertos_simulados/(len(dados_historicos)-batch_size)*100:.1f}%)")
        
    except Exception as e:
        print(f"❌ Erro no treinamento: {e}")


# =============================================================================
# INICIALIZAÇÃO DO SISTEMA DE APRENDIZADO
# =============================================================================
def inicializar_aprendizado():
    """Inicializa o sistema de aprendizado"""
    print("\n🧠 INICIALIZANDO SISTEMA DE APRENDIZADO RL + NEUROEVOLUTION...")
    cache['aprendizado'] = ControladorAprendizado('aprendizado.json')
    
    # Opcional: treinar com dados históricos (descomente se quiser)
    # treinar_com_historico(500)


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("="*70)
    print("🚀 BOT BACBO - PREVISÃO EM TEMPO REAL + RL + NEUROEVOLUTION + ANÁLISE DE ERROS")
    print("="*70)
    
    # Inicializa banco (agora com tabela de análise de erros)
    if not init_db():
        print("⚠️ Banco não disponível - continuando sem banco de dados")
    
    # CARGA HISTÓRICA - Descomente para carregar as 2500 rodadas
    print("\n📥 Carregando histórico de 2500 rodadas do arquivo...")
    try:
        with open('rodadas (3).json', 'r') as f:
            rodadas_json = json.load(f)
        
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            carregadas = 0
            for rodada in rodadas_json:
                try:
                    # Converte a data
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
    
    # CARGA HISTÓRICA DA API (opcional)
    # carregar_historico_completo()  # <--- REMOVA O # SE QUISER CARREGAR DA API
    
    print("📊 Carregando dados...")
    
    # Inicializa sistema de aprendizado
    inicializar_aprendizado()
    
    atualizar_dados_leves()
    atualizar_dados_pesados()
    
    total_rodadas = cache['leves']['total_rodadas']
    print(f"📊 {total_rodadas} rodadas no banco")
    
    if cache['aprendizado']:
        print(f"🧠 {len(cache['aprendizado'].agentes)} agentes ativos")
        print(f"📈 Geração atual: {cache['aprendizado'].geracao}")
    
    print("="*70)
    
    # Inicia todas as fontes
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
    print("="*70)
    
    app.run(host='0.0.0.0', port=PORT, debug=False)
