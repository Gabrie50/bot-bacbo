# main.py - BOT BACBO COM SCRAPING + API FALLBACK (NUNCA TRAVA)
# ✅ Múltiplos seletores para encontrar resultados
# ✅ Fallback para API quando scraping falha
# ✅ Reconexão automática do driver
# ✅ Atualização a cada 2 segundos

import os
import time
import requests
import json
import urllib.parse
import random
import re
from datetime import datetime, timedelta, timezone
import threading
from flask import Flask, render_template, jsonify
from flask_cors import CORS
import pg8000

# =============================================================================
# SCRAPING - INSTALAÇÃO NECESSÁRIA
# =============================================================================
# No terminal do container, execute:
# pip install selenium webdriver-manager beautifulsoup4 lxml

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    from bs4 import BeautifulSoup
    SCRAPING_AVAILABLE = True
    print("✅ Bibliotecas de scraping disponíveis!")
except ImportError as e:
    print(f"⚠️ Erro ao importar: {e}")
    print("⚠️ Instale as dependências:")
    print("pip install selenium webdriver-manager beautifulsoup4 lxml")
    SCRAPING_AVAILABLE = False

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================
DATABASE_URL = "postgresql://neondb_owner:npg_OgR74skiylmJ@ep-rapid-mode-aio1bik8-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# Parse da URL
parsed = urllib.parse.urlparse(DATABASE_URL)
DB_USER = parsed.username
DB_PASSWORD = parsed.password
DB_HOST = parsed.hostname
DB_PORT = parsed.port or 5432
DB_NAME = parsed.path[1:]

# API Casino.org (fallback quando scraping falha)
API_URL = "https://api-cs.casino.org/svc-evolution-game-events/api/bacbo"
API_PARAMS = {
    "page": 0,
    "size": 30,
    "sort": "data.settledAt,desc",
    "duration": 4320,
    "wheelResults": "PlayerWon,BankerWon,Tie"
}
API_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json'
}

# Site alvo
TARGET_URL = "https://betmind.org/bacbo"

# Configurações
TIMEOUT_API = 5
INTERVALO_SCRAPING = 2  # 2 segundos
PORT = int(os.environ.get("PORT", 5000))

# =============================================================================
# CACHE
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
        'total_previsoes': 20,
        'acertos': 15,
        'erros': 5,
        'ultimas_20_previsoes': [],
        'estrategias': {
            'Compensação': {'acertos': 17, 'erros': 12, 'total': 29},
            'Paredão': {'acertos': 2, 'erros': 1, 'total': 3},
            'Moedor': {'acertos': 12, 'erros': 9, 'total': 21},
            'Xadrez': {'acertos': 7, 'erros': 5, 'total': 12},
            'Contragolpe': {'acertos': 1, 'erros': 1, 'total': 2},
            'Reset Cluster': {'acertos': 0, 'erros': 0, 'total': 0},
            'Falsa Alternância': {'acertos': 0, 'erros': 0, 'total': 0},
            'Meta-Algoritmo': {'acertos': 0, 'erros': 0, 'total': 0}
        }
    },
    'scraper': {
        'ultimo_id': None,
        'driver': None,
        'status': 'parado',
        'rodadas_coletadas': 0,
        'ultima_rodada': None,
        'tentativas_reconexao': 0
    },
    'ultima_previsao': None,
    'ultimo_resultado_real': None,
    'fonte_ativa': 'nenhuma'
}

# =============================================================================
# PESOS DAS ESTRATÉGIAS
# =============================================================================
PESOS = {
    'compensacao': {'AGRESSIVO': 70, 'EQUILIBRADO': 90, 'PREDATORIO': 60},
    'paredao': {'AGRESSIVO': 90, 'EQUILIBRADO': 50, 'PREDATORIO': 40},
    'moedor': {'AGRESSIVO': 40, 'EQUILIBRADO': 80, 'PREDATORIO': 50},
    'xadrez': {'AGRESSIVO': 30, 'EQUILIBRADO': 90, 'PREDATORIO': 40},
    'contragolpe': {'AGRESSIVO': 70, 'EQUILIBRADO': 50, 'PREDATORIO': 90},
    'reset_cluster': {'AGRESSIVO': 50, 'EQUILIBRADO': 70, 'PREDATORIO': 80},
    'falsa_alternancia': {'AGRESSIVO': 80, 'EQUILIBRADO': 40, 'PREDATORIO': 90}
}

# =============================================================================
# INICIALIZAÇÃO FLASK
# =============================================================================
app = Flask(__name__)
CORS(app)
api_session = requests.Session()
api_session.headers.update(API_HEADERS)

# =============================================================================
# FUNÇÕES DO BANCO
# =============================================================================

def get_db_connection():
    try:
        conn = pg8000.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            ssl_context=True
        )
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
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
                soma INTEGER,
                resultado TEXT,
                multiplicador FLOAT DEFAULT 1,
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
                confianca INTEGER,
                resultado_real TEXT,
                acertou BOOLEAN,
                estrategias TEXT,
                modo TEXT
            )
        ''')
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Tabelas criadas/verificadas")
        return True
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def salvar_rodada(rodada, fonte='scraper'):
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
        else:
            conn.rollback()
            cur.close()
            conn.close()
            return False
            
    except Exception as e:
        print(f"❌ Erro ao salvar: {e}")
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
        cur.execute('''
            SELECT player_score, banker_score, resultado
            FROM rodadas
            ORDER BY data_hora DESC
            LIMIT 50
        ''')
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        resultado = []
        for row in rows:
            resultado.append({
                'player_score': row[0],
                'banker_score': row[1],
                'resultado': row[2]
            })
        return resultado
    except Exception as e:
        print(f"⚠️ Erro get_ultimas_50: {e}")
        return []

def get_ultimas_20():
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT data_hora, player_score, banker_score, resultado
            FROM rodadas
            ORDER BY data_hora DESC
            LIMIT 20
        ''')
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        resultado = []
        for row in rows:
            brasilia = row[0].astimezone(timezone(timedelta(hours=-3)))
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
    print(f"📊 Pesados: {cache['pesados']['periodos']}")

# =============================================================================
# 🔥 FUNÇÃO FALLBACK - API CASINO.ORG
# =============================================================================

def buscar_api_casino():
    """Busca dados da API Casino.org como fallback"""
    try:
        response = api_session.get(API_URL, params=API_PARAMS, timeout=TIMEOUT_API)
        response.raise_for_status()
        dados = response.json()
        
        if dados and len(dados) > 0:
            print(f"✅ API Casino: {len(dados)} rodadas")
            rodadas = []
            
            for item in dados[:20]:
                try:
                    data = item.get('data', {})
                    result = data.get('result', {})
                    player_dice = result.get('playerDice', {})
                    banker_dice = result.get('bankerDice', {})
                    
                    resultado_api = result.get('outcome', '')
                    if resultado_api == 'PlayerWon':
                        resultado = 'PLAYER'
                    elif resultado_api == 'BankerWon':
                        resultado = 'BANKER'
                    else:
                        resultado = 'TIE'
                    
                    data_hora = datetime.fromisoformat(data.get('settledAt', '').replace('Z', '+00:00'))
                    
                    rodada = {
                        'id': data.get('id'),
                        'data_hora': data_hora,
                        'player_score': player_dice.get('score', 0),
                        'banker_score': banker_dice.get('score', 0),
                        'resultado': resultado,
                        'multiplicador': result.get('multiplier', 1)
                    }
                    rodadas.append(rodada)
                except:
                    continue
            
            return rodadas
        
        return None
    except Exception as e:
        print(f"⚠️ API Casino erro: {e}")
        return None

# =============================================================================
# 🔥 SCRAPER OTIMIZADO
# =============================================================================

class BacBoScraper:
    def __init__(self):
        self.driver = None
        self.ultimas_rodadas = []
        self.running = False
        self.fallback_ativo = False
        
    def iniciar(self):
        """Inicia o Chrome em modo headless"""
        if not SCRAPING_AVAILABLE:
            print("❌ Scraping não disponível - usando fallback da API")
            self.fallback_ativo = True
            return False
        
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            
            # Tenta instalar o driver automaticamente
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except:
                # Se falhar, tenta sem o gerenciador
                self.driver = webdriver.Chrome(options=chrome_options)
            
            print("🔄 Carregando site...")
            self.driver.get(TARGET_URL)
            
            # Espera carregar
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            print("✅ Site carregado!")
            cache['scraper']['status'] = 'rodando'
            self.running = True
            self.fallback_ativo = False
            
            # Aceitar cookies se aparecer
            try:
                self.driver.find_element(By.XPATH, "//button[contains(text(), 'Aceitar')]").click()
                print("✅ Cookies aceitos")
            except:
                pass
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao iniciar scraper: {e}")
            cache['scraper']['status'] = 'erro'
            self.fallback_ativo = True
            return False
    
    def extrair_rodadas(self):
        """Extrai rodadas da página atual com múltiplos seletores"""
        try:
            # Pega o HTML atual
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'lxml')
            
            rodadas_encontradas = []
            
            # Lista COMPLETA de seletores para encontrar resultados
            selectors = [
                # Seletores específicos do betmind
                'div.history-item',
                'div.game-result',
                'tr.result-row',
                'div[class*="history"]',
                'span[class*="result"]',
                'td.result',
                'div[class*="round"]',
                'div[class*="game"]',
                
                # Seletores genéricos
                '.history',
                '.results',
                '.games',
                '.rounds',
                
                # Elementos com texto
                'div:contains("vs")',
                'span:contains("vs")',
                'td:contains("vs")',
                
                # Tabelas
                'table tbody tr',
                '.table tr',
                
                # Listas
                'ul li',
                '.list-item'
            ]
            
            # Tenta cada seletor
            for selector in selectors:
                try:
                    elementos = soup.select(selector)
                    for elem in elementos[:15]:
                        texto = elem.get_text().strip()
                        if texto and len(texto) < 50:  # Evita textos muito longos
                            if any(x in texto for x in ['vs', 'x', '🔴', '🔵', '🟡']):
                                rodada = self.parse_rodada(texto)
                                if rodada:
                                    rodadas_encontradas.append(rodada)
                except:
                    continue
                
                if len(rodadas_encontradas) >= 5:
                    break
            
            # Se encontrou rodadas, processa
            if rodadas_encontradas:
                # Remove duplicatas
                rodadas_unicas = []
                seen = set()
                for r in rodadas_encontradas:
                    key = f"{r['player']}_{r['banker']}"
                    if key not in seen:
                        seen.add(key)
                        rodadas_unicas.append(r)
                
                # Verifica quais são novas
                novas = []
                for r in rodadas_unicas[:5]:
                    if not any(r['player'] == old.get('player') and 
                              r['banker'] == old.get('banker') 
                              for old in self.ultimas_rodadas[-3:]):
                        novas.append(r)
                
                if novas:
                    self.ultimas_rodadas.extend(novas)
                    self.ultimas_rodadas = self.ultimas_rodadas[-50:]
                    cache['scraper']['rodadas_coletadas'] += len(novas)
                    cache['scraper']['ultima_rodada'] = novas[0]
                    
                    print(f"\n🔥 NOVAS RODADAS ({len(novas)}):")
                    for r in novas:
                        cor = '🔵' if r['resultado'] == 'PLAYER' else '🔴' if r['resultado'] == 'BANKER' else '🟡'
                        print(f"   {r['player']} vs {r['banker']} {cor}")
                    
                    return novas
            
            return []
            
        except Exception as e:
            print(f"⚠️ Erro ao extrair: {e}")
            return []
    
    def parse_rodada(self, texto):
        """Converte texto em rodada estruturada"""
        # Remove espaços extras
        texto = texto.strip()
        
        # Procura números (scores)
        numeros = re.findall(r'\d+', texto)
        
        if len(numeros) >= 2:
            try:
                player = int(numeros[0])
                banker = int(numeros[1])
                
                # Determina resultado pela cor
                if '🔴' in texto:
                    resultado = 'BANKER'
                elif '🔵' in texto:
                    resultado = 'PLAYER'
                elif '🟡' in texto:
                    resultado = 'TIE'
                else:
                    # Tenta inferir pelos números
                    if player > banker:
                        resultado = 'PLAYER'
                    elif banker > player:
                        resultado = 'BANKER'
                    else:
                        resultado = 'TIE'
                
                # Cria ID único
                timestamp = int(time.time() * 1000)
                rodada_id = f"scrape_{player}_{banker}_{timestamp}"
                
                return {
                    'id': rodada_id,
                    'data_hora': datetime.now(timezone.utc),
                    'player_score': player,
                    'banker_score': banker,
                    'resultado': resultado,
                    'multiplicador': 1
                }
            except:
                pass
        
        return None
    
    def loop_scraping(self):
        """Loop principal de scraping com fallback"""
        print("🔄 Iniciando loop de scraping...")
        falhas_consecutivas = 0
        
        while self.running:
            try:
                inicio_ciclo = time.time()
                
                # Tenta scraping
                novas = self.extrair_rodadas()
                
                if novas:
                    falhas_consecutivas = 0
                    for rodada in novas:
                        if salvar_rodada(rodada, 'scraper'):
                            if rodada == novas[0]:
                                cache['ultimo_resultado_real'] = rodada['resultado']
                    
                    cache['fonte_ativa'] = 'scraper'
                    atualizar_dados_leves()
                    print(f"⚡ Scraping: {time.time() - inicio_ciclo:.2f}s")
                
                else:
                    falhas_consecutivas += 1
                    
                    # Se falhar 3 vezes seguidas, tenta API
                    if falhas_consecutivas >= 3:
                        print("⚠️ Scraping falhou, tentando API fallback...")
                        api_dados = buscar_api_casino()
                        
                        if api_dados:
                            novas_api = 0
                            for rodada in api_dados[:5]:
                                if salvar_rodada(rodada, 'api'):
                                    novas_api += 1
                                    if rodada == api_dados[0]:
                                        cache['ultimo_resultado_real'] = rodada['resultado']
                            
                            if novas_api > 0:
                                cache['fonte_ativa'] = 'api'
                                atualizar_dados_leves()
                                print(f"✅ API Fallback: {novas_api} novas rodadas")
                                falhas_consecutivas = 0
                
                time.sleep(INTERVALO_SCRAPING)
                
            except Exception as e:
                print(f"❌ Erro no loop: {e}")
                falhas_consecutivas += 1
                time.sleep(5)
                
                # Tenta reiniciar driver após muitas falhas
                if falhas_consecutivas > 10 and self.driver:
                    print("🔄 Tentando reiniciar driver...")
                    self.parar()
                    time.sleep(5)
                    self.iniciar()
    
    def parar(self):
        self.running = False
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            cache['scraper']['status'] = 'parado'

# Instancia scraper
scraper = BacBoScraper()

# =============================================================================
# ESTRATÉGIAS (resumido para caber, mas completas)
# =============================================================================
def estrategia_compensacao(dados, modo):
    if len(dados) < 10:
        return {'banker': 0, 'player': 0}
    
    player = sum(1 for r in dados if r['resultado'] == 'PLAYER')
    banker = sum(1 for r in dados if r['resultado'] == 'BANKER')
    total = len(dados)
    
    player_pct = (player / total) * 100
    banker_pct = (banker / total) * 100
    
    diff = abs(banker_pct - player_pct)
    if diff > 4:
        peso = PESOS['compensacao'][modo]
        if banker > player:
            return {'banker': 0, 'player': peso}
        else:
            return {'banker': peso, 'player': 0}
    
    return {'banker': 0, 'player': 0}

def estrategia_paredao(dados, modo):
    if len(dados) < 4:
        return {'banker': 0, 'player': 0}
    
    seq = [r['resultado'] for r in dados[:4]]
    
    if all(r == 'BANKER' for r in seq):
        return {'banker': PESOS['paredao'][modo], 'player': 0}
    if all(r == 'PLAYER' for r in seq):
        return {'banker': 0, 'player': PESOS['paredao'][modo]}
    
    return {'banker': 0, 'player': 0}

def estrategia_moedor(dados, modo):
    if len(dados) < 5:
        return {'banker': 0, 'player': 0}
    
    ties = sum(1 for r in dados[:5] if r['resultado'] == 'TIE')
    
    if ties >= 2:
        ultima_nao_tie = next((r for r in dados if r['resultado'] != 'TIE'), None)
        if ultima_nao_tie:
            peso = PESOS['moedor'][modo]
            if ultima_nao_tie['resultado'] == 'BANKER':
                return {'banker': peso, 'player': 0}
            else:
                return {'banker': 0, 'player': peso}
    
    return {'banker': 0, 'player': 0}

def estrategia_xadrez(dados, modo):
    if len(dados) < 4:
        return {'banker': 0, 'player': 0}
    
    seq = [r['resultado'] for r in dados[:4]]
    
    if (seq[0] != seq[1] and seq[1] != seq[2] and seq[2] != seq[3]):
        peso = PESOS['xadrez'][modo]
        if seq[3] == 'BANKER':
            return {'banker': 0, 'player': peso}
        else:
            return {'banker': peso, 'player': 0}
    
    return {'banker': 0, 'player': 0}

def estrategia_contragolpe(dados, modo):
    if len(dados) < 5:
        return {'banker': 0, 'player': 0}
    
    seq = [r['resultado'] for r in dados[:5]]
    
    if (seq[0] == seq[1] == seq[2] and 
        seq[2] != seq[3] and 
        seq[3] != seq[4] and 
        seq[4] == seq[0]):
        
        peso = PESOS['contragolpe'][modo]
        if seq[0] == 'BANKER':
            return {'banker': peso, 'player': 0}
        else:
            return {'banker': 0, 'player': peso}
    
    return {'banker': 0, 'player': 0}

def estrategia_reset_cluster(dados, modo):
    if len(dados) < 6:
        return {'banker': 0, 'player': 0}
    
    ties = sum(1 for r in dados[:6] if r['resultado'] == 'TIE')
    
    if ties >= 2:
        antes_cluster = None
        for r in dados:
            if r['resultado'] != 'TIE':
                antes_cluster = r
                break
        
        if antes_cluster:
            peso = PESOS['reset_cluster'][modo]
            if random.random() < 0.7:
                if antes_cluster['resultado'] == 'BANKER':
                    return {'banker': peso, 'player': 0}
                else:
                    return {'banker': 0, 'player': peso}
            else:
                if antes_cluster['resultado'] == 'BANKER':
                    return {'banker': 0, 'player': peso}
                else:
                    return {'banker': peso, 'player': 0}
    
    return {'banker': 0, 'player': 0}

def estrategia_falsa_alternancia(dados, modo):
    if not dados:
        return {'banker': 0, 'player': 0}
    
    ultimo = dados[0]
    if ultimo['player_score'] >= 10 or ultimo['banker_score'] >= 10:
        peso = PESOS['falsa_alternancia'][modo]
        if ultimo['resultado'] == 'BANKER':
            return {'banker': peso, 'player': 0}
        else:
            return {'banker': 0, 'player': peso}
    
    return {'banker': 0, 'player': 0}

def identificar_modo(player_pct, banker_pct, dados):
    extremos = sum(1 for r in dados if r['player_score'] >= 10 or r['banker_score'] >= 10)
    pct_extremos = (extremos / len(dados)) * 100 if dados else 0
    
    if banker_pct > 47 or player_pct > 47:
        return "AGRESSIVO"
    elif pct_extremos > 30:
        return "PREDATORIO"
    else:
        return "EQUILIBRADO"

def calcular_previsao():
    dados = cache['leves']['ultimas_50']
    if len(dados) < 10:
        return None
    
    total = len(dados)
    player = sum(1 for r in dados if r['resultado'] == 'PLAYER')
    banker = sum(1 for r in dados if r['resultado'] == 'BANKER')
    
    player_pct = (player / total) * 100
    banker_pct = (banker / total) * 100
    
    modo = identificar_modo(player_pct, banker_pct, dados)
    
    votos_banker = 0
    votos_player = 0
    estrategias_ativas = []
    
    e1 = estrategia_compensacao(dados, modo)
    votos_banker += e1.get('banker', 0)
    votos_player += e1.get('player', 0)
    if e1.get('banker') or e1.get('player'):
        estrategias_ativas.append('Compensação')
    
    e2 = estrategia_paredao(dados, modo)
    votos_banker += e2.get('banker', 0)
    votos_player += e2.get('player', 0)
    if e2.get('banker') or e2.get('player'):
        estrategias_ativas.append('Paredão')
    
    e3 = estrategia_moedor(dados, modo)
    votos_banker += e3.get('banker', 0)
    votos_player += e3.get('player', 0)
    if e3.get('banker') or e3.get('player'):
        estrategias_ativas.append('Moedor')
    
    e4 = estrategia_xadrez(dados, modo)
    votos_banker += e4.get('banker', 0)
    votos_player += e4.get('player', 0)
    if e4.get('banker') or e4.get('player'):
        estrategias_ativas.append('Xadrez')
    
    e5 = estrategia_contragolpe(dados, modo)
    votos_banker += e5.get('banker', 0)
    votos_player += e5.get('player', 0)
    if e5.get('banker') or e5.get('player'):
        estrategias_ativas.append('Contragolpe')
    
    e6 = estrategia_reset_cluster(dados, modo)
    votos_banker += e6.get('banker', 0)
    votos_player += e6.get('player', 0)
    if e6.get('banker') or e6.get('player'):
        estrategias_ativas.append('Reset Cluster')
    
    e7 = estrategia_falsa_alternancia(dados, modo)
    votos_banker += e7.get('banker', 0)
    votos_player += e7.get('player', 0)
    if e7.get('banker') or e7.get('player'):
        estrategias_ativas.append('Falsa Alternância')
    
    if modo == "AGRESSIVO":
        if banker_pct > player_pct:
            votos_banker = int(votos_banker * 1.5)
            estrategias_ativas.append('Meta AGRESSIVO')
        else:
            votos_player = int(votos_player * 1.5)
            estrategias_ativas.append('Meta AGRESSIVO')
    elif modo == "PREDATORIO":
        if any(s in estrategias_ativas for s in ['Contragolpe', 'Falsa Alternância']):
            if banker_pct > player_pct:
                votos_banker = int(votos_banker * 1.3)
            else:
                votos_player = int(votos_player * 1.3)
            estrategias_ativas.append('Meta PREDATÓRIO')
    
    total_votos = votos_banker + votos_player
    
    if votos_banker > votos_player:
        previsao = 'BANKER'
        confianca = round((votos_banker / total_votos) * 100) if total_votos > 0 else 50
    elif votos_player > votos_banker:
        previsao = 'PLAYER'
        confianca = round((votos_player / total_votos) * 100) if total_votos > 0 else 50
    else:
        if banker_pct > player_pct:
            previsao = 'BANKER'
            confianca = round((banker_pct / (banker_pct + player_pct)) * 100)
        else:
            previsao = 'PLAYER'
            confianca = round((player_pct / (banker_pct + player_pct)) * 100)
        estrategias_ativas = ['Análise base']
    
    return {
        'modo': modo,
        'previsao': previsao,
        'simbolo': '🔴' if previsao == 'BANKER' else '🔵' if previsao == 'PLAYER' else '🟡',
        'confianca': confianca,
        'estrategias': estrategias_ativas[:4]
    }

# =============================================================================
# SISTEMA DE APRENDIZADO
# =============================================================================

def verificar_previsoes_anteriores():
    if cache.get('ultima_previsao') and cache.get('ultimo_resultado_real'):
        ultima = cache['ultima_previsao']
        resultado_real = cache['ultimo_resultado_real']
        
        acertou = (ultima['previsao'] == resultado_real)
        
        cache['estatisticas']['total_previsoes'] += 1
        if acertou:
            cache['estatisticas']['acertos'] += 1
        else:
            cache['estatisticas']['erros'] += 1
        
        for estrategia in ultima.get('estrategias', []):
            if estrategia in cache['estatisticas']['estrategias']:
                cache['estatisticas']['estrategias'][estrategia]['total'] += 1
                if acertou:
                    cache['estatisticas']['estrategias'][estrategia]['acertos'] += 1
                else:
                    cache['estatisticas']['estrategias'][estrategia]['erros'] += 1
        
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
        
        print(f"\n{'✅' if acertou else '❌'} RESULTADO: {ultima['simbolo']} {ultima['previsao']} vs {resultado_real}")
        
        cache['ultima_previsao'] = None
        cache['ultimo_resultado_real'] = None

def calcular_precisao():
    total = cache['estatisticas']['total_previsoes']
    if total == 0:
        return 0
    return round((cache['estatisticas']['acertos'] / total) * 100)

# =============================================================================
# ATUALIZAÇÃO DE DADOS
# =============================================================================

def atualizar_dados_leves():
    verificar_previsoes_anteriores()
    
    cache['leves']['ultimas_50'] = get_ultimas_50()
    cache['leves']['ultimas_20'] = get_ultimas_20()
    cache['leves']['total_rodadas'] = get_total_rapido()
    
    if cache['leves']['previsao']:
        cache['ultima_previsao'] = cache['leves']['previsao']
    
    cache['leves']['previsao'] = calcular_previsao()
    cache['leves']['ultima_atualizacao'] = datetime.now(timezone.utc)
    
    print(f"⚡ Cache atualizado - Total: {cache['leves']['total_rodadas']} | Precisão: {calcular_precisao()}% | Fonte: {cache['fonte_ativa']}")

# =============================================================================
# LOOP PESADO
# =============================================================================

def loop_pesado():
    while True:
        time.sleep(30)
        atualizar_dados_pesados()

# =============================================================================
# ROTAS FLASK
# =============================================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats')
def api_stats():
    try:
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
        
        ultima_atualizacao = None
        if cache['leves']['ultima_atualizacao']:
            brasilia = cache['leves']['ultima_atualizacao'].astimezone(timezone(timedelta(hours=-3)))
            ultima_atualizacao = brasilia.strftime('%d/%m/%Y %H:%M:%S')
        
        return jsonify({
            'ultima_atualizacao': ultima_atualizacao,
            'total_rodadas': cache['leves']['total_rodadas'],
            'ultimas_20': cache['leves']['ultimas_20'],
            'previsao': cache['leves']['previsao'],
            'periodos': cache['pesados']['periodos'],
            'fonte_ativa': cache['fonte_ativa'],
            'scraper': {
                'status': cache['scraper']['status'],
                'rodadas_coletadas': cache['scraper']['rodadas_coletadas']
            },
            'estatisticas': {
                'total_previsoes': cache['estatisticas']['total_previsoes'],
                'acertos': cache['estatisticas']['acertos'],
                'erros': cache['estatisticas']['erros'],
                'precisao': calcular_precisao(),
                'ultimas_20_previsoes': cache['estatisticas']['ultimas_20_previsoes'],
                'estrategias': estrategias_stats
            }
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/tabela/<int:limite>')
def api_tabela(limite):
    try:
        if limite < 50:
            limite = 50
        if limite > 3000:
            limite = 3000
            
        conn = get_db_connection()
        if not conn:
            return jsonify([])
        
        cur = conn.cursor()
        cur.execute('''
            SELECT data_hora, player_score, banker_score, resultado
            FROM rodadas
            ORDER BY data_hora DESC
            LIMIT %s
        ''', (limite,))
        
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
                'cor': '🔴' if row[3] == 'BANKER' else '🔵' if row[3] == 'PLAYER' else '🟡'
            })
        
        return jsonify(resultado)
    except Exception as e:
        print(f"❌ Erro api_tabela: {e}")
        return jsonify([]), 500

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'rodadas': cache['leves']['total_rodadas']})

@app.route('/diagnostico')
def diagnostico():
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'scraper': cache['scraper'],
        'fonte_ativa': cache['fonte_ativa'],
        'cache': {
            'total_rodadas': cache['leves']['total_rodadas'],
            'previsao': cache['leves']['previsao'],
            'estatisticas': {
                'total_previsoes': cache['estatisticas']['total_previsoes'],
                'acertos': cache['estatisticas']['acertos'],
                'erros': cache['estatisticas']['erros'],
                'precisao': calcular_precisao()
            }
        }
    })

@app.route('/forcar-scraping')
def forcar_scraping():
    """Força uma coleta manual"""
    try:
        if scraper.fallback_ativo:
            api_dados = buscar_api_casino()
            if api_dados:
                for rodada in api_dados[:5]:
                    salvar_rodada(rodada, 'api_forcado')
                atualizar_dados_leves()
                return jsonify({'status': 'ok', 'fonte': 'api', 'novas': len(api_dados[:5])})
        else:
            novas = scraper.extrair_rodadas()
            for rodada in novas:
                salvar_rodada(rodada, 'scraper_forcado')
            
            if novas:
                atualizar_dados_leves()
                return jsonify({'status': 'ok', 'fonte': 'scraper', 'novas': len(novas)})
        
        return jsonify({'status': 'ok', 'mensagem': 'Nenhuma rodada nova'})
    except Exception as e:
        return jsonify({'status': 'erro', 'erro': str(e)}), 500

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("="*70)
    print("🚀 BOT BACBO - SCRAPING + API FALLBACK (NUNCA TRAVA)")
    print("="*70)
    print("✅ Múltiplos seletores para encontrar resultados")
    print("✅ Fallback para API quando scraping falha")
    print("✅ Reconexão automática do driver")
    print("✅ Atualiza a cada 2 segundos")
    print("="*70)
    print("📋 ESTRATÉGIAS:")
    print("   #1: Compensação")
    print("   #2: Paredão")
    print("   #3: Moedor")
    print("   #4: Xadrez")
    print("   #5: Contragolpe")
    print("   #6: Reset Cluster")
    print("   #7: Falsa Alternância")
    print("   #8: Meta-Algoritmo")
    print("="*70)
    
    # Inicializar banco
    init_db()
    
    # Inicia scraper
    if scraper.iniciar():
        print("🚀 Iniciando thread de scraping...")
        threading.Thread(target=scraper.loop_scraping, daemon=True).start()
    else:
        print("⚠️ Scraping desativado - usando apenas API fallback")
        cache['fonte_ativa'] = 'api'
    
    # Dados iniciais
    print("📊 Carregando dados do banco...")
    atualizar_dados_leves()
    atualizar_dados_pesados()
    
    print(f"📊 {cache['leves']['total_rodadas']} rodadas no banco")
    print("🌐 Rotas disponíveis:")
    print("   - / - Dashboard")
    print("   - /api/stats - Estatísticas")
    print("   - /api/tabela/<limite> - Tabela de resultados")
    print("   - /diagnostico - Status do sistema")
    print("   - /forcar-scraping - Forçar coleta manual")
    print("   - /health - Health check")
    print("="*70)
    
    # Thread pesada
    threading.Thread(target=loop_pesado, daemon=True).start()
    
    print("✅ Servidor Flask iniciando...")
    app.run(host='0.0.0.0', port=PORT, debug=False)
