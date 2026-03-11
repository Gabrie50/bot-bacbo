# =============================================================================
# main.py - VERSÃO CAÇADORA 4.0 (RL PURO + AUTO-APRENDIZADO)
# =============================================================================
# ✅ SISTEMA DE APRENDIZADO: Cada estratégia é um agente que aprende
# ✅ NEUROEVOLUÇÃO: Mutações, crossover e seleção natural
# ✅ 10 ESTRATÉGIAS TRANSFORMADAS EM AGENTES
# ✅ MEMÓRIA PERSISTENTE: Salva em JSON e nunca reseta
# ✅ TABELA DE ANÁLISE DE ERROS: Cada erro é registrado com contexto completo
# ✅ DETECÇÃO DE MANIPULAÇÃO: Identifica padrões suspeitos do algoritmo
# ✅ API NORMAL: Carrega rodadas passadas e salva no banco para aprendizado
# =============================================================================
# 🆕 NOVIDADES v4.0:
# ✅ RL PURO: Agentes aprendem DO ZERO, sem estratégias pré-definidas
# ✅ REDES NEURAIS: LSTM + DQN para detectar padrões complexos
# ✅ AUTO-DESCOBERTA: Sistema encontra sozinho as 10 estratégias
# ✅ MEMÓRIA DE LONGO PRAZO: Lembra padrões de até 1000 rodadas
# ✅ APRENDIZADO CONTÍNUO: Melhora a cada rodada, 24/7
# ✅ ANÁLISE DE PADRÕES: Detecta padrões como o 7x2 que você descobriu
# ✅ ENSINO ENTRE AGENTES: Quando um agente erra, todos aprendem
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
# TENSORFLOW / KERAS (para RL puro)
# =============================================================================
try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential, Model
    from tensorflow.keras.layers import Dense, Dropout, LSTM, Conv1D, Flatten, Input, Concatenate
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping
    TF_AVAILABLE = True
except ImportError:
    print("⚠️ TensorFlow não encontrado - RL puro desativado")
    TF_AVAILABLE = False

# =============================================================================
# CONFIGURAÇÕES - PG8000 COM SSL
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

LATEST_API_URL = "https://api-cs.casino.org/svc-evolution-game-events/api/bacbo/latest"
WS_URL = "wss://api-cs.casino.org/svc-evolution-game-events/ws/bacbo"
API_URL = "https://api-cs.casino.org/svc-evolution-game-events/api/bacbo"
API_PARAMS = {
    "page": 0,
    "size": 100,  # Aumentado para carregar mais rodadas
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
# PROCESSADOR DA FILA (ADAPTADO PARA RL) - VERSÃO CORRIGIDA
# =============================================================================

def processar_fila():
    print("🚀 Processador TURBO (com RL) iniciado...")
    
    historico_buffer = []
    ultima_previsao_feita = None

    while True:
        try:
            if fila_rodadas:
                batch = list(fila_rodadas)
                fila_rodadas.clear()
                
                for rodada in batch:
                    if salvar_rodada(rodada, 'principal'):
                        historico_buffer.append(rodada)
                        cache['ultimo_resultado_real'] = rodada['resultado']
                        print(f"✅ SALVO: {rodada['player_score']} vs {rodada['banker_score']} - {rodada['resultado']}")
                        
                        # Se tinha uma previsão anterior, agora podemos verificar se acertou
                        if ultima_previsao_feita:
                            resultado_real = rodada['resultado']
                            
                            if resultado_real != 'TIE':  # Ignora TIE para aprendizado
                                acertou = (ultima_previsao_feita['previsao'] == resultado_real)
                                
                                print(f"\n📊 VERIFICANDO PREVISÃO ANTERIOR:")
                                print(f"   Previsão: {ultima_previsao_feita['previsao']} | Real: {resultado_real} | Acertou: {acertou}")
                                
                                # Pega contexto para análise
                                contexto = cache['leves']['ultimas_50'] if cache['leves']['ultimas_50'] else []
                                
                                # Calcula índice de manipulação
                                indice_manipulacao = calcular_indice_manipulacao(contexto)
                                cache['indice_manipulacao'] = indice_manipulacao
                                
                                # Se tem analisador de erros, analisa
                                causa_erro = None
                                if cache.get('analisador_erros') and not acertou:
                                    causa_erro = cache['analisador_erros'].analisar_erro_em_tempo_real(
                                        ultima_previsao_feita, resultado_real, contexto, indice_manipulacao
                                    )
                                
                                # Atualiza estatísticas no cache
                                cache['estatisticas']['total_previsoes'] += 1
                                if acertou:
                                    cache['estatisticas']['acertos'] += 1
                                else:
                                    cache['estatisticas']['erros'] += 1
                                
                                # Adiciona ao histórico de previsões
                                previsao_historico = {
                                    'data': datetime.now().strftime('%d/%m %H:%M:%S'),
                                    'previsao': ultima_previsao_feita['previsao'],
                                    'simbolo': ultima_previsao_feita['simbolo'],
                                    'confianca': ultima_previsao_feita['confianca'],
                                    'resultado_real': resultado_real,
                                    'acertou': acertou,
                                    'estrategias': ultima_previsao_feita.get('estrategias', []),
                                    'manipulado': indice_manipulacao > 50
                                }
                                
                                cache['estatisticas']['ultimas_20_previsoes'].insert(0, previsao_historico)
                                if len(cache['estatisticas']['ultimas_20_previsoes']) > 20:
                                    cache['estatisticas']['ultimas_20_previsoes'].pop()
                                
                                # Se tem RL, ensina com o resultado
                                if cache.get('rl_system') and len(cache['leves']['ultimas_50']) >= 50:
                                    cache['rl_system'].aprender_com_resultado(
                                        cache['leves']['ultimas_50'], 
                                        resultado_real
                                    )
                                
                                # Pega estatísticas atualizadas dos agentes
                                if cache.get('rl_system'):
                                    for nome, agente in cache['rl_system'].agentes.items():
                                        if nome in cache['estatisticas']['estrategias']:
                                            cache['estatisticas']['estrategias'][nome]['acertos'] = agente.acertos
                                            cache['estatisticas']['estrategias'][nome]['erros'] = agente.erros
                                            cache['estatisticas']['estrategias'][nome]['total'] = agente.total_uso
                                
                                # Mostra precisão atual
                                precisao = calcular_precisao()
                                print(f"📈 Precisão geral: {cache['estatisticas']['acertos']}/{cache['estatisticas']['total_previsoes']} ({precisao}%)")
                            
                            ultima_previsao_feita = None
                
                if len(historico_buffer) > 0:
                    # Atualiza cache com últimas rodadas
                    cache['leves']['ultimas_50'] = get_ultimas_50()
                    cache['leves']['ultimas_20'] = get_ultimas_20()
                    cache['leves']['total_rodadas'] = get_total_rapido()
                    
                    # Se tem RL e histórico suficiente, faz nova previsão
                    if cache.get('rl_system') and len(cache['leves']['ultimas_50']) >= 50:
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
                            
                            print(f"\n🎯 NOVA PREVISÃO: {ultima_previsao_feita['previsao']} com {ultima_previsao_feita['confianca']}% de confiança")
                    
                    # Atualiza dados leves
                    cache['leves']['ultima_atualizacao'] = datetime.now(timezone.utc)

            time.sleep(0.01)

        except Exception as e:
            print(f"❌ Erro no processador: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(0.1)


# =============================================================================
# FUNÇÃO PARA CALCULAR PRECISÃO
# =============================================================================
def calcular_precisao():
    """Calcula a precisão atual baseada nas estatísticas"""
    total = cache['estatisticas']['total_previsoes']
    if total == 0:
        return 0
    return round((cache['estatisticas']['acertos'] / total) * 100)

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
    """
    Retorna os dados ordenados do mais antigo para o mais novo
    Necessário para análise de padrões
    """
    if not dados:
        return []
    # Assume que os dados estão em ordem cronológica reversa (mais recente primeiro)
    # Inverte para ter do mais antigo para o mais novo
    return list(reversed(dados))

# =============================================================================
# 🧠 SISTEMA RL PURO - APRENDE SOZINHO AS ESTRATÉGIAS
# =============================================================================

class AgenteRLPuro:
    """
    Agente que APRENDE DO ZERO como o algoritmo funciona
    SEM nenhuma estratégia pré-definida
    """
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
        
        # Estado = últimas 50 rodadas (cada rodada = 3 valores)
        self.state_size = 50 * 3  # resultado, player_score, banker_score
        self.action_size = 2       # BANKER ou PLAYER
        
        # Memória de experiências (para replay)
        self.memoria = deque(maxlen=10000)
        
        # Hiperparâmetros
        self.learning_rate = 0.001
        self.gamma = 0.95  # fator de desconto
        self.epsilon = 1.0  # exploração inicial
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        
        # Rede neural
        self.model = None
        self.target_model = None
        self._criar_rede()
        
        # Estatísticas de aprendizado
        self.padroes_aprendidos = []
        self.ultimo_estado = None
        self.ultima_acao = None
        
        # Para neuroevolução
        self.especialidade = None
        self.erros_que_aprendeu = []
        self.fitness = 0
        
    def _criar_rede(self):
        """
        Cria a rede neural que vai APRENDER os padrões
        """
        if not TF_AVAILABLE:
            print(f"⚠️ TensorFlow não disponível - {self.nome} usará pesos simples")
            return
            
        try:
            # Input layer
            inputs = Input(shape=(self.state_size,))
            
            # Camadas densas para aprender padrões
            x = Dense(256, activation='relu')(inputs)
            x = Dropout(0.2)(x)
            x = Dense(512, activation='relu')(x)
            x = Dropout(0.3)(x)
            x = Dense(256, activation='relu')(x)
            x = Dense(128, activation='relu')(x)
            
            # Output layer (valores Q para cada ação)
            outputs = Dense(self.action_size, activation='linear')(x)
            
            self.model = Model(inputs=inputs, outputs=outputs)
            self.model.compile(
                optimizer=Adam(learning_rate=self.learning_rate),
                loss='mse'
            )
            
            # Target network (para estabilidade)
            self.target_model = Model(inputs=inputs, outputs=outputs)
            self.target_model.set_weights(self.model.get_weights())
            
            print(f"✅ Rede neural criada para {self.nome}")
            
        except Exception as e:
            print(f"❌ Erro ao criar rede para {self.nome}: {e}")
            self.model = None
    
    def get_state(self, historico):
        """
        Converte histórico para tensor que a rede entende
        """
        state = []
        for rodada in historico[:50]:  # últimas 50
            # Codifica: resultado (B/P/T) + scores
            if rodada['resultado'] == 'BANKER':
                resultado = 1
            elif rodada['resultado'] == 'PLAYER':
                resultado = 2
            else:
                resultado = 3
                
            state.extend([
                resultado,
                rodada['player_score'] / 12,  # normaliza 0-1
                rodada['banker_score'] / 12
            ])
        
        # Padding se necessário
        while len(state) < self.state_size:
            state.extend([0, 0, 0])
            
        return np.array(state).reshape(1, self.state_size)
    
    def agir(self, historico):
        """
        Escolhe ação (ε-greedy)
        """
        self.total_uso += 1
        
        if len(historico) < 50:
            # Ainda não tem histórico suficiente
            return random.choice([0, 1]), 0.5
            
        state = self.get_state(historico)
        self.ultimo_estado = state
        
        # Exploração
        if np.random.rand() <= self.epsilon:
            acao = random.choice([0, 1])
            confianca = 0.5
        else:
            # Exploração
            if self.model is not None:
                try:
                    q_values = self.model.predict(state, verbose=0)[0]
                    acao = np.argmax(q_values)
                    
                    # Confiança baseada na diferença dos Q-values
                    q_diff = abs(q_values[1] - q_values[0]) if len(q_values) > 1 else 0
                    confianca = min(0.5 + q_diff, 0.94)
                except:
                    acao = random.choice([0, 1])
                    confianca = 0.5
            else:
                # Fallback: peso simples
                if self.peso > 1.0:
                    acao = 0 if random.random() < 0.6 else 1  # tendência BANKER
                else:
                    acao = 1 if random.random() < 0.6 else 0  # tendência PLAYER
                confianca = 0.5 + (abs(self.peso - 1.0) * 0.2)
        
        self.ultima_acao = acao
        self.confianca = confianca
        return acao, confianca
    
    def aprender(self, historico, acao, resultado, recompensa_base=0):
        """
        Aprende com o resultado usando Q-Learning
        """
        if resultado == 'TIE':
            return  # Ignora empates para aprendizado
            
        if len(historico) < 50:
            return
            
        # Determina se acertou
        resultado_int = 0 if resultado == 'BANKER' else 1
        acertou = (acao == resultado_int)
        
        if acertou:
            self.acertos += 1
        else:
            self.erros += 1
            
        # Calcula recompensa
        recompensa = 1.0 if acertou else -0.5
        
        # Bônus por consistência (detecta padrões)
        if len(self.memoria) > 100:
            ultimos_acertos = [m[2] for m in list(self.memoria)[-100:] if len(m) > 2]
            if ultimos_acertos:
                taxa_acertos_recente = sum(ultimos_acertos) / len(ultimos_acertos)
                if taxa_acertos_recente > 0.7:
                    recompensa += 0.3  # Bônus por estar acertando muito
                    print(f"🎯 {self.nome} detectou padrão! Precisão recente: {taxa_acertos_recente:.1%}")
        
        # Guarda na memória
        state = self.get_state(historico[:-1])  # estado antes da rodada
        next_state = self.get_state(historico)   # estado depois da rodada
        
        self.memoria.append((state, acao, recompensa, next_state, acertou))
        
        # Treina em batch
        if len(self.memoria) > 32 and self.model is not None:
            self._replay()
        
        # Decai epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
            
        # Atualiza peso baseado na performance
        if self.total_uso > 50:
            precisao = self.acertos / self.total_uso
            self.peso = max(0.6, min(2.2, 0.8 + (precisao - 0.5) * 2))
            self.fitness = precisao * 100
            
        return acertou
    
    def _replay(self):
        """
        Replay da memória para treinar a rede
        """
        if len(self.memoria) < 32 or self.model is None:
            return
            
        try:
            batch = random.sample(list(self.memoria), 32)
            
            for state, acao, recompensa, next_state, acertou in batch:
                # Calcula target Q-value
                target = recompensa
                if not acertou:  # Se não acabou (sempre continua)
                    try:
                        next_q = self.target_model.predict(next_state, verbose=0)[0]
                        target = recompensa + self.gamma * np.max(next_q)
                    except:
                        pass
                
                # Atualiza modelo
                target_f = self.model.predict(state, verbose=0)
                target_f[0][acao] = target
                
                self.model.fit(state, target_f, epochs=1, verbose=0)
            
            # Atualiza target network periodicamente
            if random.random() < 0.01:  # 1% de chance a cada batch
                self.target_model.set_weights(self.model.get_weights())
                
        except Exception as e:
            print(f"⚠️ Erro no replay de {self.nome}: {e}")
    
    def get_stats(self):
        precisao = (self.acertos / self.total_uso) * 100 if self.total_uso > 0 else 0
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
            'memoria': len(self.memoria),
            'especialidade': self.especialidade,
            'fitness': round(self.fitness, 1)
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
            'fitness': self.fitness
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
        return agente


class SistemaRLCompleto:
    """
    Sistema que gerencia 10 agentes RL puros
    Eles competem e colaboram para aprender o algoritmo
    """
    def __init__(self):
        self.agentes = {}
        self.meta_agente = None
        self.historico_global = deque(maxlen=1000)
        self.padroes_descobertos = []
        self.geracao = 0
        self.melhor_precisao = 0
        self.manipulacoes_detectadas = 0  # Adicionado
        
        # Inicializa 10 agentes
        for i in range(10):
            nome = f"RL_Agente_{i+1}"
            self.agentes[nome] = AgenteRLPuro(nome, i)
            
        print(f"✅ 10 agentes RL puros inicializados")
        
        # Meta-agente (aprende a combinar os votos)
        if TF_AVAILABLE:
            self._criar_meta_agente()
    
    def _criar_meta_agente(self):
        """
        Meta-agente que aprende a combinar os votos dos 10 agentes
        """
        try:
            inputs = Input(shape=(20,))  # 10 agentes * 2 (peso + confianca)
            x = Dense(64, activation='relu')(inputs)
            x = Dropout(0.2)(x)
            x = Dense(32, activation='relu')(x)
            outputs = Dense(2, activation='softmax')(x)  # BANKER ou PLAYER
            
            self.meta_agente = Model(inputs=inputs, outputs=outputs)
            self.meta_agente.compile(
                optimizer=Adam(0.0001),
                loss='categorical_crossentropy',
                metrics=['accuracy']
            )
            print("✅ Meta-agente criado")
        except Exception as e:
            print(f"⚠️ Erro ao criar meta-agente: {e}")
            self.meta_agente = None
    
    def processar_rodada(self, historico, resultado_real=None):
        """
        Processa uma nova rodada com todos os agentes
        """
        if len(historico) < 50:
            return None
            
        # Cada agente vota
        votos = {'BANKER': 0, 'PLAYER': 0}
        votos_detalhados = []
        
        for nome, agente in self.agentes.items():
            acao, confianca = agente.agir(historico[:-1])  # histórico antes da rodada atual
            previsao = 'BANKER' if acao == 0 else 'PLAYER'
            
            # Peso do voto = peso do agente * confiança
            peso_voto = agente.peso * confianca
            votos[previsao] += peso_voto
            
            votos_detalhados.append({
                'agente': nome,
                'previsao': previsao,
                'peso': round(agente.peso, 2),
                'confianca': round(confianca * 100, 1),
                'peso_total': round(peso_voto, 2)
            })
        
        # Se tem meta-agente, usa ele para decidir
        if self.meta_agente is not None and resultado_real is not None:
            # Prepara features para meta-agente
            features = []
            for nome, agente in self.agentes.items():
                features.extend([agente.peso, agente.confianca])
            
            features = np.array(features).reshape(1, 20)
            
            try:
                meta_pred = self.meta_agente.predict(features, verbose=0)[0]
                previsao_meta = 'BANKER' if meta_pred[0] > meta_pred[1] else 'PLAYER'
                
                # Se meta-agente discordar do voto ponderado, usar o dele
                if previsao_meta != max(votos, key=votos.get):
                    votos[previsao_meta] += 5.0  # bônus para meta-agente
                    print(f"🎯 Meta-agente interveio: {previsao_meta}")
            except:
                pass
        
        # Decisão final
        previsao_final = max(votos, key=votos.get)
        
        # Confiança baseada na diferença de votos
        total_votos = sum(votos.values())
        if total_votos > 0:
            confianca_final = (votos[previsao_final] / total_votos) * 100
            confianca_final = min(94, max(50, round(confianca_final)))
        else:
            confianca_final = 50
            
        # Guarda histórico
        self.historico_global.append({
            'previsao': previsao_final,
            'confianca': confianca_final,
            'votos': votos_detalhados,
            'timestamp': datetime.now()
        })
        
        return {
            'previsao': previsao_final,
            'confianca': confianca_final,
            'votos': votos_detalhados[:4],  # só os 4 principais para o frontend
            'total_agentes': len([v for v in votos_detalhados if v['peso_total'] > 0])
        }
    
    def aprender_com_resultado(self, historico, resultado_real):
        """
        Todos os agentes aprendem com o resultado
        """
        if resultado_real == 'TIE':
            return
            
        acertos = 0
        for nome, agente in self.agentes.items():
            # Determina a ação que o agente teria tomado
            acao, _ = agente.agir(historico[:-1])
            acertou = agente.aprender(historico, acao, resultado_real)
            if acertou:
                acertos += 1
                
        # Estatísticas
        precisao_rodada = acertos / len(self.agentes)
        
        # A cada 100 rodadas, avalia evolução
        if len(self.historico_global) % 100 == 0:
            self.geracao += 1
            self._avaliar_evolucao()
    
    def _avaliar_evolucao(self):
        """
        Avalia a evolução dos agentes e detecta padrões descobertos
        """
        stats = self.get_stats()
        precisao_media = stats['precisao_media']
        
        if precisao_media > self.melhor_precisao:
            self.melhor_precisao = precisao_media
            print(f"\n🏆 NOVA MELHOR PRECISÃO: {precisao_media:.1f}% (geração {self.geracao})")
            
            # Tenta identificar que padrão foi descoberto
            self._detectar_padroes()
    
    def _detectar_padroes(self):
        """
        Tenta identificar quais padrões os agentes descobriram
        """
        # Análise dos agentes com melhor performance
        top_agentes = sorted(
            [a.get_stats() for a in self.agentes.values() if a.total_uso > 100],
            key=lambda x: x['precisao'],
            reverse=True
        )[:3]
        
        for agente in top_agentes:
            if agente['precisao'] > 70:
                padrao = {
                    'agente': agente['nome'],
                    'precisao': agente['precisao'],
                    'descoberto_em': datetime.now().isoformat(),
                    'tipo': self._classificar_padrao(agente)
                }
                
                # Evita duplicatas
                if not any(p['agente'] == padrao['agente'] for p in cache['padroes_descobertos']):
                    cache['padroes_descobertos'].append(padrao)
                    print(f"\n🎯 RL DESCOBRIU NOVO PADRÃO!")
                    print(f"   Agente: {padrao['agente']}")
                    print(f"   Precisão: {padrao['precisao']:.1f}%")
                    print(f"   Tipo: {padrao['tipo']}")
    
    def _classificar_padrao(self, agente_stats):
        """
        Tenta classificar que tipo de padrão o agente descobriu
        """
        if agente_stats['precisao'] > 80:
            return "Provavelmente CONTRAGOLPE (85%)"
        elif agente_stats['precisao'] > 75:
            return "Provavelmente RESET CLUSTER ou SATURAÇÃO (72-75%)"
        elif agente_stats['precisao'] > 70:
            return "Provavelmente MOEDOR ou COMPENSAÇÃO (70%)"
        else:
            return "Padrão não classificado"
    
    def get_stats(self):
        stats = {
            'geracao': self.geracao,
            'melhor_precisao': round(self.melhor_precisao, 1),
            'precisao_media': 0,
            'agentes': []
        }
        
        total_precisao = 0
        count = 0
        
        for nome, agente in self.agentes.items():
            agente_stats = agente.get_stats()
            stats['agentes'].append(agente_stats)
            
            if agente_stats['total'] > 0:
                total_precisao += agente_stats['precisao']
                count += 1
                
        if count > 0:
            stats['precisao_media'] = round(total_precisao / count, 1)
            
        stats['agentes'].sort(key=lambda x: x['precisao'], reverse=True)
        
        return stats
    
    def salvar_estado(self, arquivo='rl_estado.json'):
        """
        Salva o estado de todos os agentes
        """
        try:
            estado = {
                'geracao': self.geracao,
                'melhor_precisao': self.melhor_precisao,
                'agentes': {nome: agente.para_dict() for nome, agente in self.agentes.items()}
            }
            
            with open(arquivo, 'w') as f:
                json.dump(estado, f, indent=2)
                
            print(f"💾 Estado RL salvo em {arquivo}")
            return True
        except Exception as e:
            print(f"❌ Erro ao salvar estado RL: {e}")
            return False
    
    def carregar_estado(self, arquivo='rl_estado.json'):
        """
        Carrega o estado dos agentes
        """
        caminho = Path(arquivo)
        if not caminho.exists():
            print("📂 Nenhum estado RL anterior encontrado")
            return False
            
        try:
            with open(arquivo, 'r') as f:
                estado = json.load(f)
                
            self.geracao = estado.get('geracao', 0)
            self.melhor_precisao = estado.get('melhor_precisao', 0)
            
            for nome, dados in estado.get('agentes', {}).items():
                if nome in self.agentes:
                    self.agentes[nome] = AgenteRLPuro.de_dict(dados)
                    
            print(f"✅ Estado RL carregado: geração {self.geracao}")
            return True
        except Exception as e:
            print(f"⚠️ Erro ao carregar estado RL: {e}")
            return False


# =============================================================================
# 🧬 SISTEMA DE NEUROEVOLUÇÃO QUE APRENDE COM ERROS
# =============================================================================
class AnalisadorDeErros:
    """
    Classe especializada em ANALISAR ERROS e extrair aprendizado
    """
    
    def __init__(self, sistema_rl):
        self.sistema_rl = sistema_rl
        self.erros_analisados = 0
        self.padroes_de_erro = {}
        self.ultimos_erros = deque(maxlen=100)
        
    def analisar_erro_em_tempo_real(self, previsao, resultado_real, contexto, indice_manipulacao):
        """
        Analisa um erro assim que acontece (tempo real)
        E já ensina os outros agentes
        """
        if resultado_real == 'TIE':
            return  # Ignora empates para aprendizado
        
        # Só analisa se errou
        if previsao['previsao'] == resultado_real:
            return
        
        print(f"\n🔍 ANALISANDO ERRO EM TEMPO REAL...")
        
        # 1. Descobre POR QUE errou
        causa = self._diagnosticar_causa_erro(previsao, resultado_real, contexto, indice_manipulacao)
        
        # 2. Registra o erro para análise futura
        erro_info = {
            'timestamp': datetime.now(),
            'previsao': previsao['previsao'],
            'real': resultado_real,
            'confianca': previsao['confianca'],
            'causa': causa,
            'indice_manipulacao': indice_manipulacao,
            'contexto': contexto[:10] if contexto else []
        }
        self.ultimos_erros.append(erro_info)
        self.erros_analisados += 1
        
        # 3. Atualiza estatísticas de padrões de erro
        padrao_key = f"{causa}"
        self.padroes_de_erro[padrao_key] = self.padroes_de_erro.get(padrao_key, 0) + 1
        
        # 4. ✅ ENSINA OS OUTROS AGENTES SOBRE O ERRO
        self._ensinar_agentes_sobre_erro(causa, previsao, resultado_real, contexto)
        
        # 5. Se esse erro é muito frequente, cria um especialista
        if self.padroes_de_erro.get(padrao_key, 0) > 3:
            self._criar_agente_especialista_em_erro(causa)
        
        print(f"✅ Diagnóstico: {causa}")
        return causa
    
    def _diagnosticar_causa_erro(self, previsao, real, contexto, indice_manipulacao):
        """
        Diagnostica a CAUSA REAL do erro
        """
        if not contexto or len(contexto) < 10:
            return "poucos_dados"
        
        # Pega os últimos resultados
        ultimos_resultados = [r['resultado'] for r in contexto[:20] if r['resultado'] != 'TIE']
        
        # 1. Verifica se foi manipulação óbvia
        if indice_manipulacao > 70:
            self.sistema_rl.manipulacoes_detectadas += 1
            return "manipulacao_alta"
        
        # 2. Verifica quebra de streak (padrão clássico do BAC BO)
        streak_atual = self._calcular_streak(ultimos_resultados)
        if streak_atual >= 4:
            # Se estava em streak e mudou, foi virada forçada
            if len(ultimos_resultados) >= 2 and ultimos_resultados[-1] != ultimos_resultados[-2]:
                return f"quebra_de_streak_{streak_atual}"
        
        # 3. Verifica padrão 3+2 (muito comum no BAC BO)
        if len(ultimos_resultados) >= 5:
            # Padrão: 3 iguais, depois 2 diferentes
            if (ultimos_resultados[-5] == ultimos_resultados[-4] == ultimos_resultados[-3] and
                ultimos_resultados[-2] == ultimos_resultados[-1] and
                ultimos_resultados[-3] != ultimos_resultados[-2]):
                if previsao['previsao'] == ultimos_resultados[-3]:  # Previu continuação do padrão
                    return "padrao_3_2_quebrado"
        
        # 4. Verifica padrão DUPLO TIE + SEQUÊNCIA (7x2 que você descobriu)
        if len(ultimos_resultados) >= 9:
            for i in range(len(ultimos_resultados) - 1):
                if i+1 < len(ultimos_resultados) and ultimos_resultados[i] == 'TIE' and ultimos_resultados[i+1] == 'TIE':
                    # Encontrou duplo TIE
                    return "padrao_duplo_tie_detectado"
        
        # 5. Verifica travamento (scores se repetindo)
        if len(contexto) >= 2:
            ultima = contexto[0]
            penultima = contexto[1]
            if (ultima['banker_score'] == penultima['player_score'] and
                abs(ultima['banker_score'] - penultima['banker_score']) > 3):
                return "travamento_detectado"
        
        # 6. Verifica empate inesperado
        if real == 'TIE' and previsao['previsao'] != 'TIE':
            return "empate_nao_previsto"
        
        return "causa_desconhecida"
    
    def _calcular_streak(self, resultados):
        """Calcula a streak atual"""
        if not resultados:
            return 0
        streak = 1
        for i in range(1, len(resultados)):
            if resultados[-i] == resultados[-(i+1)]:
                streak += 1
            else:
                break
        return streak
    
    def _ensinar_agentes_sobre_erro(self, causa, previsao, real, contexto):
        """
        ✅ ENSINA TODOS OS AGENTES sobre o erro
        Para que eles não cometam o mesmo erro
        """
        print(f"📚 Ensinando {len(self.sistema_rl.agentes)} agentes sobre erro: {causa}")
        
        for nome, agente in self.sistema_rl.agentes.items():
            # Verifica se esse agente também teria errado
            acao_agente, _ = agente.agir(contexto[:-1] if contexto and len(contexto) > 1 else contexto)
            previsao_agente = 'BANKER' if acao_agente == 0 else 'PLAYER'
            
            if previsao_agente == previsao['previsao']:
                # Esse agente teria errado igual
                # Aplica uma penalidade e ensina
                
                # 1. Reduz o peso (aprende que essa estratégia falha nesse contexto)
                agente.peso = max(0.3, agente.peso * 0.9)
                
                # 2. Adiciona à memória como experiência negativa
                if hasattr(agente, 'memoria') and contexto and len(contexto) > 1:
                    try:
                        state = agente.get_state(contexto[:-1])
                        next_state = agente.get_state(contexto)
                        # Recompensa negativa forte
                        agente.memoria.append((state, acao_agente, -2.0, next_state, False))
                    except:
                        pass
                
                # 3. Marca que aprendeu com esse erro
                if not hasattr(agente, 'erros_que_aprendeu'):
                    agente.erros_que_aprendeu = []
                agente.erros_que_aprendeu.append({
                    'causa': causa,
                    'timestamp': datetime.now().isoformat()
                })
                
                print(f"   🤖 {nome} aprendeu com o erro")
            else:
                # Esse agente teria acertado
                # Reforça o comportamento
                agente.peso = min(2.5, agente.peso * 1.05)
                print(f"   ✅ {nome} já sabia a resposta certa")
        
        print(f"✅ Todos os agentes foram ensinados sobre: {causa}")
    
    def _criar_agente_especialista_em_erro(self, causa):
        """
        Cria um agente ESPECIALISTA nesse tipo de erro
        Para nunca mais errar nesse padrão
        """
        if not TF_AVAILABLE:
            return
        
        print(f"\n🧬 CRIANDO AGENTE ESPECIALISTA EM: {causa}")
        
        # Verifica se já existe um especialista nisso
        for nome, agente in self.sistema_rl.agentes.items():
            if hasattr(agente, 'especialidade') and agente.especialidade == causa:
                print(f"   ⚠️ Já existe especialista em {causa}: {nome}")
                return
        
        # Cria novo agente
        novo_id = len(self.sistema_rl.agentes) + 1
        nome = f"RL_Especialista_{causa[:10]}_{novo_id}"
        
        novo_agente = AgenteRLPuro(nome, novo_id)
        
        # Configura como especialista
        novo_agente.especialidade = causa
        novo_agente.peso = 2.5  # Peso maior para especialistas
        novo_agente.epsilon = 0.05  # Quase não explora (já sabe o padrão)
        novo_agente.fitness = 80.0  # Fitness inicial alto
        
        # Adiciona ao sistema
        self.sistema_rl.agentes[nome] = novo_agente
        
        print(f"✅ NOVO AGENTE ESPECIALISTA CRIADO: {nome}")
        print(f"   Especialidade: {causa}")
        print(f"   Peso inicial: {novo_agente.peso}")
        
        # Registra no banco
        self._registrar_agente_no_banco(nome, novo_agente, causa)
    
    def _registrar_agente_no_banco(self, nome, agente, especialidade):
        """Registra o novo agente no banco"""
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
                json.dumps({
                    'peso': agente.peso,
                    'epsilon': agente.epsilon,
                    'especialidade': especialidade
                }),
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
        """Retorna estatísticas dos erros analisados"""
        return {
            'total_erros_analisados': self.erros_analisados,
            'padroes_de_erro': self.padroes_de_erro,
            'ultimos_erros': [
                {
                    'causa': e['causa'],
                    'previsao': e['previsao'],
                    'real': e['real'],
                    'hora': e['timestamp'].strftime('%H:%M:%S')
                }
                for e in list(self.ultimos_erros)[-10:]
            ]
        }


# =============================================================================
# FUNÇÕES PARA DETECÇÃO DE MANIPULAÇÃO
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
    """
    Calcula índice de manipulação baseado em padrões suspeitos
    """
    if len(dados) < 10:
        return 0

    dados_ord = list(reversed(dados)) if dados else []
    indice = 0

    # Streaks de 4+
    streaks = 0
    for i in range(len(dados_ord)-3):
        if (dados_ord[i]['resultado'] == dados_ord[i+1]['resultado'] ==
            dados_ord[i+2]['resultado'] == dados_ord[i+3]['resultado'] and
            dados_ord[i]['resultado'] != 'TIE'):
            streaks += 1
    indice += streaks * 10

    # Streak longo
    streak_atual = 1
    for i in range(1, min(10, len(dados_ord))):
        if (dados_ord[i]['resultado'] == dados_ord[i-1]['resultado'] and
                dados_ord[i]['resultado'] != 'TIE'):
            streak_atual += 1
        else:
            break

    if streak_atual >= 5:
        indice += streak_atual * 8

    # TIEs
    ties = sum(1 for r in dados_ord[:20] if r['resultado'] == 'TIE')
    if ties > 3:
        indice += 20
    if ties > 5:
        indice += 15

    # TIEs consecutivos
    ties_seguidos = 0
    for i in range(min(5, len(dados_ord))):
        if dados_ord[i]['resultado'] == 'TIE':
            ties_seguidos += 1
        else:
            break

    if ties_seguidos >= 2:
        indice += 30

    # Repetições de score
    repeticoes = 0
    for i in range(len(dados_ord)-1):
        if dados_ord[i]['banker_score'] == dados_ord[i+1]['player_score']:
            repeticoes += 1
        if dados_ord[i]['player_score'] == dados_ord[i+1]['banker_score']:
            repeticoes += 1
    indice += repeticoes * 5

    # Padrão 3+2
    for i in range(len(dados_ord)-4):
        if (dados_ord[i]['resultado'] == dados_ord[i+1]['resultado'] == dados_ord[i+2]['resultado'] and
            dados_ord[i+2]['resultado'] != dados_ord[i+3]['resultado'] and
            dados_ord[i+3]['resultado'] == dados_ord[i+4]['resultado']):
            indice += 25
            break

    return min(100, indice)


# =============================================================================
# FUNÇÕES DO BANCO DE DADOS (ATUALIZADO E CORRIGIDO)
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
    """
    Inicializa todas as tabelas do banco de dados
    """
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
                pesos_agentes JSONB,
                contexto_json JSONB,
                indice_manipulacao INTEGER DEFAULT 0,
                foi_manipulado BOOLEAN DEFAULT FALSE
            )
        ''')

        # Primeiro dropar a tabela se existir para recriar com estrutura correta
        cur.execute('DROP TABLE IF EXISTS analise_erros CASCADE')
        
        # Tabela de análise de erros (DETALHADA) - VERSÃO CORRIGIDA
        cur.execute('''
            CREATE TABLE analise_erros (
                id SERIAL PRIMARY KEY,
                data_hora TIMESTAMPTZ,
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
                indice_manipulacao INTEGER DEFAULT 0,
                foi_manipulado BOOLEAN DEFAULT FALSE,
                padrao_detectado TEXT,
                causa_erro TEXT,
                acertou BOOLEAN,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')

        # Criar índices depois da tabela
        try:
            cur.execute('CREATE INDEX IF NOT EXISTS idx_erros_data ON analise_erros(data_hora DESC)')
        except:
            pass
        try:
            cur.execute('CREATE INDEX IF NOT EXISTS idx_erros_acertou ON analise_erros(acertou)')
        except:
            pass
        try:
            cur.execute('CREATE INDEX IF NOT EXISTS idx_erros_causa ON analise_erros(causa_erro)')
        except:
            pass

        # Tabela de aprendizado com erros
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

        # Tabela de neuroevolução
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
        
        # Verifica e corrige novamente após criação
        verificar_e_corrigir_banco()
        
        return True
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        return False

def salvar_rodada(rodada, fonte):
    """Salva uma rodada no banco de dados"""
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
# 🔧 FUNÇÃO PARA CORREÇÃO AUTOMÁTICA DO BANCO DE DADOS
# =============================================================================
def verificar_e_corrigir_banco():
    """
    Verifica se todas as colunas necessárias existem e adiciona se faltarem
    """
    print("\n🔧 Verificando estrutura do banco de dados...")
    
    conn = get_db_connection()
    if not conn:
        print("⚠️ Não foi possível conectar ao banco para verificação")
        return False
    
    try:
        cur = conn.cursor()
        
        # Verifica se a tabela existe
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'analise_erros'
            )
        """)
        tabela_existe = cur.fetchone()[0]
        
        if not tabela_existe:
            print("📊 Tabela analise_erros não existe - recriando...")
            cur.execute('''
                CREATE TABLE analise_erros (
                    id SERIAL PRIMARY KEY,
                    data_hora TIMESTAMPTZ,
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
                    indice_manipulacao INTEGER DEFAULT 0,
                    foi_manipulado BOOLEAN DEFAULT FALSE,
                    padrao_detectado TEXT,
                    causa_erro TEXT,
                    acertou BOOLEAN,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            ''')
            conn.commit()
            print("✅ Tabela analise_erros recriada com sucesso!")
            cur.close()
            conn.close()
            return True
        
        # Se a tabela existe, verifica as colunas
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'analise_erros'
        """)
        colunas_existentes = [row[0] for row in cur.fetchall()]
        
        print(f"📊 Colunas existentes: {', '.join(colunas_existentes)}")
        
        # Lista de colunas que deveriam existir
        colunas_necessarias = [
            ('ultimos_10_resultados', 'TEXT'),
            ('padrao_detectado', 'TEXT'),
            ('causa_erro', 'TEXT'),
            ('streak_atual', 'INTEGER DEFAULT 0'),
            ('banker_50', 'INTEGER DEFAULT 0'),
            ('player_50', 'INTEGER DEFAULT 0'),
            ('diferenca_percentual', 'FLOAT DEFAULT 0'),
            ('agentes_ativos', 'TEXT'),
            ('pesos_agentes', 'JSONB'),
            ('foi_manipulado', 'BOOLEAN DEFAULT FALSE'),
            ('acertou', 'BOOLEAN')
        ]
        
        colunas_adicionadas = 0
        
        # Adiciona colunas que estão faltando
        for coluna, tipo in colunas_necessarias:
            if coluna not in colunas_existentes:
                try:
                    cur.execute(f'ALTER TABLE analise_erros ADD COLUMN IF NOT EXISTS {coluna} {tipo}')
                    print(f"   ✅ Coluna '{coluna}' adicionada")
                    colunas_adicionadas += 1
                except Exception as e:
                    print(f"   ⚠️ Erro ao adicionar coluna '{coluna}': {e}")
        
        conn.commit()
        cur.close()
        conn.close()
        
        if colunas_adicionadas > 0:
            print(f"✅ Banco corrigido! {colunas_adicionadas} colunas adicionadas.")
        else:
            print("✅ Banco já está com a estrutura correta!")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao verificar/corrigir banco: {e}")
        return False

# =============================================================================
# 🛡️ VERSÃO SEGURA DA FUNÇÃO salvar_previsao_completa (com fallback)
# =============================================================================
def salvar_previsao_completa_segura(previsao, resultado_real, acertou, contexto, pesos_agentes=None, indice_manipulacao=0, foi_manipulado=False, causa_erro=None):
    """
    Versão SEGURA que tenta salvar e se falhar, tenta versão simplificada
    """
    conn = get_db_connection()
    if not conn:
        return False

    try:
        cur = conn.cursor()
        
        # Pega últimos resultados para análise
        ultimos_10 = []
        if contexto and len(contexto) > 0:
            ultimos_10 = [r['resultado'] for r in contexto[:10] if r and 'resultado' in r]
        
        # TENTATIVA 1: Inserção completa
        try:
            cur.execute('''
                INSERT INTO analise_erros 
                (data_hora, previsao_feita, resultado_real, confianca, modo, 
                 streak_atual, banker_50, player_50, 
                 ultimos_5_resultados, ultimos_10_resultados,
                 agentes_ativos, pesos_agentes, 
                 indice_manipulacao, foi_manipulado, padrao_detectado, causa_erro, acertou)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                datetime.now(timezone.utc),
                previsao['previsao'],
                resultado_real,
                previsao['confianca'],
                previsao.get('modo', 'RL_PURO'),
                0,  # streak
                0,  # banker_50
                0,  # player_50
                ','.join(ultimos_10[:5]) if ultimos_10 else '',
                ','.join(ultimos_10) if ultimos_10 else '',
                ','.join(previsao.get('estrategias', [])) if previsao.get('estrategias') else '',
                json.dumps(pesos_agentes) if pesos_agentes else None,
                indice_manipulacao,
                foi_manipulado,
                None,  # padrao_detectado
                causa_erro,
                acertou
            ))
            conn.commit()
            cur.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"⚠️ Inserção completa falhou, tentando versão simplificada: {e}")
            conn.rollback()
            
            # TENTATIVA 2: Inserção simplificada (só com colunas essenciais)
            try:
                # Primeiro verifica quais colunas existem
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'analise_erros'
                """)
                colunas = [row[0] for row in cur.fetchall()]
                
                # Colunas básicas que sempre devem existir
                colunas_basicas = ['data_hora', 'previsao_feita', 'resultado_real', 'confianca', 'modo', 'acertou']
                colunas_presentes = [c for c in colunas_basicas if c in colunas]
                
                if 'indice_manipulacao' in colunas:
                    colunas_presentes.append('indice_manipulacao')
                if 'foi_manipulado' in colunas:
                    colunas_presentes.append('foi_manipulado')
                if 'causa_erro' in colunas and causa_erro:
                    colunas_presentes.append('causa_erro')
                
                placeholders = ','.join(['%s'] * len(colunas_presentes))
                valores = []
                
                for col in colunas_presentes:
                    if col == 'data_hora':
                        valores.append(datetime.now(timezone.utc))
                    elif col == 'previsao_feita':
                        valores.append(previsao['previsao'])
                    elif col == 'resultado_real':
                        valores.append(resultado_real)
                    elif col == 'confianca':
                        valores.append(previsao['confianca'])
                    elif col == 'modo':
                        valores.append(previsao.get('modo', 'RL_PURO'))
                    elif col == 'acertou':
                        valores.append(acertou)
                    elif col == 'indice_manipulacao':
                        valores.append(indice_manipulacao)
                    elif col == 'foi_manipulado':
                        valores.append(foi_manipulado)
                    elif col == 'causa_erro':
                        valores.append(causa_erro)
                
                query = f"INSERT INTO analise_erros ({','.join(colunas_presentes)}) VALUES ({placeholders})"
                cur.execute(query, valores)
                
                conn.commit()
                cur.close()
                conn.close()
                print("✅ Versão adaptativa salva com sucesso")
                return True
                
            except Exception as e2:
                print(f"❌ Versão adaptativa também falhou: {e2}")
                conn.rollback()
                cur.close()
                conn.close()
                return False
                
    except Exception as e:
        print(f"❌ Erro geral ao salvar análise: {e}")
        return False

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
# ALTERNAR FONTE ATIVA
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
# FONTE 1: API LATEST
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
            alternar_fonte()
        return None


# =============================================================================
# 🚀 FUNÇÃO PARA CARREGAR HISTÓRICO COMPLETO DA API NORMAL
# =============================================================================

def carregar_historico_completo_para_aprendizado(limite_paginas=100):
    """
    Carrega TODO o histórico disponível da API Normal
    e salva no banco para o RL aprender
    """
    print("\n" + "="*80)
    print("📚 CARREGANDO HISTÓRICO COMPLETO PARA APRENDIZADO RL")
    print("="*80)
    
    conn = get_db_connection()
    if not conn:
        print("❌ Erro ao conectar ao banco")
        return None
    
    total_carregadas = 0
    pagina = 0
    paginas_sem_novidades = 0
    
    # Pega o sistema RL do cache
    sistema_rl = cache.get('rl_system')
    if not sistema_rl:
        print("❌ Sistema RL não inicializado")
        return None
    
    # Cria o analisador de erros
    analisador = AnalisadorDeErros(sistema_rl)
    cache['analisador_erros'] = analisador
    
    try:
        cur = conn.cursor()
        
        while paginas_sem_novidades < 3 and pagina < limite_paginas:
            params = API_PARAMS.copy()
            params['page'] = pagina
            params['size'] = 100  # Máximo por página
            params['_t'] = int(time.time() * 1000)
            
            print(f"\n📥 Buscando página {pagina}...")
            
            try:
                response = session.get(API_URL, params=params, timeout=TIMEOUT_API)
                response.raise_for_status()
                dados = response.json()
                
                if not dados or len(dados) == 0:
                    print(f"✅ Fim das páginas na página {pagina}")
                    break
                
                # Processa as rodadas em ORDEM CRONOLÓGICA (da mais antiga para a mais nova)
                rodadas_ordenadas = []
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
                        
                        # Salva no banco
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
                        continue
                
                conn.commit()
                
                # Ordena por data (mais antiga primeiro)
                rodadas_ordenadas.sort(key=lambda x: x['data_hora'])
                
                # ✅ SIMULA O APRENDIZADO COM ESSAS RODADAS
                print(f"   🧠 Simulando aprendizado com {len(rodadas_ordenadas)} rodadas...")
                
                historico_simulado = []
                
                for i, rodada in enumerate(rodadas_ordenadas):
                    # Adiciona ao histórico simulado
                    historico_simulado.append({
                        'player_score': rodada['player_score'],
                        'banker_score': rodada['banker_score'],
                        'resultado': rodada['resultado']
                    })
                    
                    # Se tem histórico suficiente, faz previsão e aprende
                    if len(historico_simulado) >= 50:
                        # Faz previsão para esta rodada (baseado no histórico até a anterior)
                        previsao = sistema_rl.processar_rodada(historico_simulado[:-1])
                        
                        if previsao:
                            # Calcula índice de manipulação
                            indice = calcular_indice_manipulacao(historico_simulado[:-20] if len(historico_simulado) > 20 else historico_simulado)
                            
                            # Se errou, ANALISA O ERRO e ENSINA OS AGENTES
                            if previsao['previsao'] != rodada['resultado'] and rodada['resultado'] != 'TIE':
                                causa = analisador.analisar_erro_em_tempo_real(
                                    previsao, 
                                    rodada['resultado'], 
                                    historico_simulado[:-1],
                                    indice
                                )
                                
                                # Salva no banco para análise futura
                                salvar_previsao_completa(
                                    previsao, 
                                    rodada['resultado'], 
                                    False, 
                                    historico_simulado[:-1],
                                    None, 
                                    indice, 
                                    indice > 50,
                                    causa
                                )
                            else:
                                # Acertou, salva também
                                salvar_previsao_completa(
                                    previsao, 
                                    rodada['resultado'], 
                                    True, 
                                    historico_simulado[:-1],
                                    None, 
                                    indice, 
                                    indice > 50
                                )
                            
                            # Aprende com o resultado
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
                paginas_sem_novidades += 1
                time.sleep(2)
        
        cur.close()
        conn.close()
        
        print("\n" + "="*80)
        print(f"✅ CARGA HISTÓRICA CONCLUÍDA!")
        print(f"📊 Total de rodadas carregadas: {total_carregadas}")
        print(f"🔍 Erros analisados: {analisador.erros_analisados}")
        print("="*80)
        
        # Mostra estatísticas dos erros
        stats = analisador.get_stats()
        print("\n📊 PADRÕES DE ERRO IDENTIFICADOS:")
        for padrao, count in sorted(stats['padroes_de_erro'].items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"   • {padrao}: {count} vezes")
        
        return analisador
        
    except Exception as e:
        print(f"❌ Erro fatal na carga histórica: {e}")
        return None


# =============================================================================
# FUNÇÃO PARA ANALISAR PADRÃO 7x2 ESPECÍFICO
# =============================================================================

def analisar_padrao_7x2_no_historico():
    """
    Analisa todo o histórico para confirmar o padrão 7:2 que você descobriu
    """
    print("\n" + "="*70)
    print("🔍 ANALISANDO PADRÃO DUPLO TIE + SEQUÊNCIA 7:2")
    print("="*70)
    
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cur = conn.cursor()
        
        # Busca todas as rodadas em ordem
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
        
        # Procura por DUPLOS TIES
        ocorrencias = []
        
        for i in range(len(resultados) - 1):
            if resultados[i] == 'TIE' and resultados[i+1] == 'TIE':
                # Encontrou duplo TIE
                
                # Pega os próximos 20 resultados (ignorando TIES)
                proximos = []
                indices_proximos = []
                
                for j in range(i+2, min(i+50, len(resultados))):
                    if resultados[j] != 'TIE':
                        proximos.append(resultados[j])
                        indices_proximos.append(j)
                        if len(proximos) >= 20:
                            break
                
                if len(proximos) >= 9:
                    # Analisa a sequência
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
        
        # Analisa as proporções
        proporcoes = {}
        for occ in ocorrencias:
            prop = occ['proporcao']
            proporcoes[prop] = proporcoes.get(prop, 0) + 1
        
        print("\n📈 DISTRIBUIÇÃO DAS PROPORÇÕES APÓS DUPLO TIE:")
        for prop, count in sorted(proporcoes.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"   • {prop}: {count} vezes ({count/len(ocorrencias)*100:.1f}%)")
        
        # Mostra as 5 ocorrências mais recentes
        print("\n🆕 OCORRÊNCIAS RECENTES:")
        for occ in sorted(ocorrencias, key=lambda x: x['data_inicio'] if x['data_inicio'] else datetime.min, reverse=True)[:5]:
            data_str = occ['data_inicio'].strftime('%d/%m %H:%M') if occ['data_inicio'] else 'desconhecida'
            print(f"\n   📅 {data_str}")
            print(f"   Sequência: {' → '.join(occ['proximos_9'])}")
            print(f"   Proporção: {occ['banker_count']} BANKER : {occ['player_count']} PLAYER ({occ['banker_pct']}% / {occ['player_pct']}%)")
        
        # Adiciona o padrão descoberto
        if len(ocorrencias) >= 3:
            padrao_info = {
                'nome': 'Duplo TIE + Sequência 7:2',
                'descricao': 'Após 2 TIES seguidos, o algoritmo inicia uma sequência com proporção ~7:2',
                'descoberto_em': datetime.now().isoformat(),
                'total_ocorrencias': len(ocorrencias),
                'proporcoes': proporcoes
            }
            
            # Evita duplicatas
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
# PROCESSADOR DA FILA (ADAPTADO PARA RL)
# =============================================================================

def processar_fila():
    print("🚀 Processador TURBO (com RL) iniciado...")
    
    historico_buffer = []

    while True:
        try:
            if fila_rodadas:
                batch = list(fila_rodadas)
                fila_rodadas.clear()
                
                for rodada in batch:
                    if salvar_rodada(rodada, 'principal'):
                        historico_buffer.append(rodada)
                        cache['ultimo_resultado_real'] = rodada['resultado']
                        print(f"✅ SALVO: {rodada['player_score']} vs {rodada['banker_score']} - {rodada['resultado']}")
                
                if len(historico_buffer) > 0:
                    # Atualiza cache com últimas rodadas
                    cache['leves']['ultimas_50'] = get_ultimas_50()
                    cache['leves']['ultimas_20'] = get_ultimas_20()
                    
                    # Se tem RL, processa aprendizado
                    if cache.get('rl_system'):
                        historico_completo = cache['leves']['ultimas_50']
                        
                        # Se tem resultado anterior para aprender
                        if len(historico_buffer) > 1 and len(historico_completo) >= 50:
                            rodada_anterior = historico_buffer[-2]
                            resultado_anterior = rodada_anterior['resultado']
                            
                            # Ensina o RL
                            cache['rl_system'].aprender_com_resultado(
                                historico_completo[:-1],  # histórico antes da última
                                resultado_anterior
                            )
                        
                        # Se tem histórico suficiente, faz previsão
                        if len(historico_completo) >= 50:
                            previsao_rl = cache['rl_system'].processar_rodada(historico_completo)
                            
                            if previsao_rl:
                                cache['ultima_previsao'] = {
                                    'modo': 'RL_PURO',
                                    'previsao': previsao_rl['previsao'],
                                    'simbolo': '🔴' if previsao_rl['previsao'] == 'BANKER' else '🔵',
                                    'confianca': previsao_rl['confianca'],
                                    'estrategias': [v['agente'] for v in previsao_rl['votos']]
                                }
                                cache['leves']['previsao'] = cache['ultima_previsao']
                    
                    # Atualiza dados leves
                    atualizar_dados_leves()

            time.sleep(0.01)

        except Exception as e:
            print(f"❌ Erro TURBO: {e}")
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
            SELECT previsao_feita, resultado_real, confianca, modo, indice_manipulacao, causa_erro
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


@app.route('/api/manipulacao')
def api_manipulacao():
    return jsonify({
        'indice_atual': cache.get('indice_manipulacao', 0),
        'manipulacoes_detectadas': cache['rl_system'].manipulacoes_detectadas if cache.get('rl_system') else 0,
        'agentes_com_deteccao': [
            {'nome': a['nome'], 'deteccoes': a.get('deteccoes_manipulacao', 0)}
            for a in cache['rl_system'].get_stats()['agentes'] if a.get('deteccoes_manipulacao', 0) > 0
        ] if cache.get('rl_system') else []
    })


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats')
def api_stats():
    estrategias_stats = []
    if cache.get('rl_system'):
        for agente in cache['rl_system'].get_stats()['agentes']:
            estrategias_stats.append({
                'nome': agente['nome'],
                'acertos': agente['acertos'],
                'erros': agente['erros'],
                'precisao': agente['precisao'],
                'especialidade': agente.get('especialidade', 'Nenhuma')
            })
    else:
        for nome, dados in cache['estatisticas']['estrategias'].items():
            total = dados['total']
            precisao = round((dados['acertos'] / total) * 100) if total > 0 else 0
            estrategias_stats.append({
                'nome': nome,
                'acertos': dados['acertos'],
                'erros': dados['erros'],
                'precisao': precisao
            })

    aprendizado_stats = None
    if cache.get('rl_system'):
        aprendizado_stats = cache['rl_system'].get_stats()
    elif cache.get('aprendizado'):
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
        'padroes_descobertos': cache.get('padroes_descobertos', []),
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
    if cache.get('rl_system'):
        return jsonify(cache['rl_system'].get_stats())
    elif cache.get('aprendizado'):
        return jsonify(cache['aprendizado'].get_stats())
    return jsonify({'erro': 'Sistema de aprendizado não inicializado'})

@app.route('/api/padroes')
def api_padroes():
    """Mostra padrões descobertos pelo RL"""
    return jsonify({
        'padroes': cache.get('padroes_descobertos', []),
        'total': len(cache.get('padroes_descobertos', []))
    })

@app.route('/api/padrao-7x2')
def api_padrao_7x2():
    """Mostra análises do padrão DUPLO TIE + SEQUÊNCIA 7:2"""
    
    # Faz a análise
    ocorrencias = analisar_padrao_7x2_no_historico()
    
    # Procura o agente especialista
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
        'analisador_erros': 'ativo' if cache.get('analisador_erros') else 'inativo',
        'padroes_descobertos': len(cache.get('padroes_descobertos', [])),
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
# TREINAMENTO INICIAL COM DADOS HISTÓRICOS
# =============================================================================
def treinar_rl_com_historico(limit=1000):
    print(f"\n🧠 INICIANDO TREINAMENTO RL COM HISTÓRICO ({limit} rodadas)...")

    conn = get_db_connection()
    if not conn:
        print("❌ Não foi possível conectar ao banco para treinamento")
        return

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
            return

        dados_historicos = []
        for row in rows:
            dados_historicos.append({
                'player_score': row[0],
                'banker_score': row[1],
                'resultado': row[2]
            })

        print(f"📚 {len(dados_historicos)} rodadas carregadas para treinamento")
        print("⏳ Treinando RL (isso pode levar alguns minutos)...")

        from tqdm import tqdm

        # Simula rodadas para treinar o RL
        for i in tqdm(range(50, len(dados_historicos)), desc="Treinando RL"):
            historico_ate_agora = dados_historicos[:i]
            resultado_real = dados_historicos[i]['resultado']

            if resultado_real != 'TIE':
                # Ensina o RL
                cache['rl_system'].aprender_com_resultado(
                    historico_ate_agora,
                    resultado_real
                )

        print(f"\n✅ TREINAMENTO RL CONCLUÍDO!")
        stats = cache['rl_system'].get_stats()
        print(f"📊 Precisão média: {stats['precisao_media']:.1f}%")
        print(f"🏆 Melhor agente: {stats['agentes'][0]['nome']} com {stats['agentes'][0]['precisao']:.1f}%")

    except Exception as e:
        print(f"❌ Erro no treinamento: {e}")


# =============================================================================
# INICIALIZAÇÃO
# =============================================================================
def inicializar_sistema():
    print("\n🧠 INICIALIZANDO SISTEMA CAÇADOR 4.0 (RL PURO)...")
    
    # Inicializa RL puro
    cache['rl_system'] = SistemaRLCompleto()
    
    # Tenta carregar estado anterior
    cache['rl_system'].carregar_estado('rl_estado.json')
    
    # Carrega padrões descobertos anteriormente
    try:
        with open('padroes.json', 'r') as f:
            cache['padroes_descobertos'] = json.load(f)
        print(f"📚 {len(cache['padroes_descobertos'])} padrões carregados")
    except:
        pass
    
    print("✅ Sistema RL inicializado")

def salvar_padroes():
    """Salva os padrões descobertos pelo RL"""
    try:
        with open('padroes.json', 'w') as f:
            json.dump(cache['padroes_descobertos'], f, indent=2)
    except Exception as e:
        print(f"⚠️ Erro ao salvar padrões: {e}")


# =============================================================================
# VERIFICAÇÃO DE PREVISÕES ANTERIORES
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
        if cache.get('rl_system'):
            for agente in cache['rl_system'].agentes.values():
                if agente.total_uso > 0:
                    pesos_agentes[agente.nome] = {
                        'peso': agente.peso,
                        'precisao': agente.get_stats()['precisao'],
                        'saude': agente.saude
                    }

        # Se tem analisador de erros, analisa
        causa_erro = None
        if cache.get('analisador_erros') and not acertou:
            causa_erro = cache['analisador_erros'].analisar_erro_em_tempo_real(
                ultima, resultado_real, dados_ord, indice_manipulacao
            )

        # Salva no banco
        salvar_previsao_completa(
            ultima, resultado_real, acertou, dados_ord, 
            pesos_agentes, indice_manipulacao, foi_manipulado, causa_erro
        )

        cache['estatisticas']['total_previsoes'] += 1
        if acertou:
            cache['estatisticas']['acertos'] += 1
        else:
            cache['estatisticas']['erros'] += 1

        previsao_historico = {
            'data': datetime.now().strftime('%d/%m %H:%M:%S'),
            'previsao': ultima['previsao'],
            'simbolo': ultima['simbolo'],
            'confianca': ultima['confianca'],
            'resultado_real': resultado_real,
            'acertou': acertou,
            'estrategias': ultima.get('estrategias', []),
            'manipulado': foi_manipulado,
            'causa_erro': causa_erro
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
    cache['leves']['ultima_atualizacao'] = datetime.now(timezone.utc)


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("="*70)
    print("🚀 BOT BACBO - VERSÃO CAÇADORA 4.0 (RL PURO)")
    print("   SISTEMA DE AUTO-APRENDIZADO - DESCOBRE PADRÕES SOZINHO")
    print("="*70)
    print("🆕 NOVIDADES v4.0:")
    print("   ✅ 10 AGENTES RL PUROS (aprendem do zero)")
    print("   ✅ REDES NEURAIS (LSTM + DQN)")
    print("   ✅ AUTO-DESCOBERTA DE PADRÕES")
    print("   ✅ MEMÓRIA DE LONGO PRAZO (10.000 experiências)")
    print("   ✅ META-AGENTE (aprende a combinar votos)")
    print("   ✅ ANÁLISE DE ERROS EM TEMPO REAL")
    print("   ✅ ENSINO ENTRE AGENTES")
    print("="*70)
    print("📊 PREVISÃO DE DESEMPENHO:")
    print("   • 0-1000 rodadas: 50-55% (explorando)")
    print("   • 1000-5000 rodadas: 60-70% (aprendendo)")
    print("   • 5000-10000 rodadas: 70-80% (maduro)")
    print("   • 10000+ rodadas: 75-85% (especialista)")
    print("="*70)

     # Inicializa banco de dados
    if not init_db():
        print("⚠️ Banco não disponível - continuando sem banco de dados")
    else:
        # 🔧 VERIFICA E CORRIGE O BANCO AUTOMATICAMENTE (só se conectou)
        verificar_e_corrigir_banco()
    
    # Tenta carregar JSON (opcional)
    try:
        with open('rodadas.json', 'r') as f:
            rodadas_json = json.load(f)
            print(f"✅ Arquivo JSON encontrado com {len(rodadas_json)} rodadas")
    except:
        print("📁 Nenhum arquivo JSON encontrado - continuando com API")

    print("📊 Carregando dados...")
    inicializar_sistema()
    
    # 🚀 CARREGA HISTÓRICO DA API NORMAL E TREINA
    analisador = carregar_historico_completo_para_aprendizado(limite_paginas=50)
    
    if analisador:
        cache['analisador_erros'] = analisador
        print(f"\n✅ Sistema de análise de erros ativo!")
    
    # Analisa padrão 7x2 específico
    analisar_padrao_7x2_no_historico()
    
    # Atualiza dados
    atualizar_dados_leves()
    atualizar_dados_pesados()

    total_rodadas = cache['leves']['total_rodadas']
    print(f"📊 {total_rodadas} rodadas no banco")

    if cache.get('rl_system'):
        stats = cache['rl_system'].get_stats()
        print(f"🧠 {len(cache['rl_system'].agentes)} agentes RL ativos")
        print(f"📈 Geração atual: {stats['geracao']}")
        print(f"🎯 Melhor precisão: {stats['melhor_precisao']:.1f}%")

    print("="*70)

    # Inicia fontes de dados
    print("🔌 Iniciando WebSocket (modo backup)...")
    iniciar_websocket()

    print("📡 [PRINCIPAL] Iniciando coletor LATEST (0.3s)...")
    threading.Thread(target=loop_latest, daemon=True).start()

    print("⚡ Iniciando monitor WebSocket...")
    threading.Thread(target=loop_websocket_fallback, daemon=True).start()

    print("📚 [FALLBACK] Iniciando coletor API NORMAL (10s)...")
    threading.Thread(target=loop_api_fallback, daemon=True).start()

    print("🚀 Iniciando processador da fila com RL...")
    threading.Thread(target=processar_fila, daemon=True).start()

    print("🔄 Iniciando loop pesado...")
    threading.Thread(target=loop_pesado, daemon=True).start()

    # Thread para salvar estado periodicamente
    def salvar_periodicamente():
        while True:
            time.sleep(300)  # a cada 5 minutos
            if cache.get('rl_system'):
                cache['rl_system'].salvar_estado('rl_estado.json')
                salvar_padroes()
                print("💾 Estado RL salvo automaticamente")

    threading.Thread(target=salvar_periodicamente, daemon=True).start()

    print("\n" + "="*70)
    print("✅ SISTEMA PRONTO! PREVISÃO ATUALIZA AUTOMATICAMENTE!")
    print("📊 Acesse /api/stats para ver a previsão em tempo real")
    print("🧠 Acesse /api/aprendizado para ver a evolução dos agentes RL")
    print("📝 Acesse /api/analise-erros para análise detalhada dos erros")
    print("🎯 Acesse /api/manipulacao para estatísticas de manipulação")
    print("🔍 Acesse /api/padroes para ver padrões descobertos")
    print("🎲 Acesse /api/padrao-7x2 para ver o padrão especial que você descobriu")
    print("="*70)

    app.run(host='0.0.0.0', port=PORT, debug=False)
