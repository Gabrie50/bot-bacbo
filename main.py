# main.py - Bot BacBo PROFISSIONAL - MULTI-FONTE (Scraping + Supabase + API)
# ✅ SCRAPING DIRETO DO BETMIND.ORG
# ✅ SUPABASE COMO BACKUP
# ✅ API CASINO.ORG COMO TERCEIRA OPÇÃO
# ✅ SEM TRAVAMENTOS - RODA 24/7

import os
import time
import requests
import json
import urllib.parse
import random
from datetime import datetime, timedelta, timezone
import threading
from flask import Flask, render_template, jsonify
from flask_cors import CORS
import pg8000

# =============================================================================
# IMPORTAÇÕES PARA SCRAPING
# =============================================================================
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    print("⚠️ Selenium não instalado. Instale com: pip install selenium webdriver-manager")
    SELENIUM_AVAILABLE = False

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

# API Casino.org (fallback)
API_URL = "https://api-cs.casino.org/svc-evolution-game-events/api/bacbo"
PARAMS = {
    "page": 0,
    "size": 50,
    "sort": "data.settledAt,desc",
    "duration": 4320,
    "wheelResults": "PlayerWon,BankerWon,Tie"
}
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json'
}

# 🔥 SUPABASE (fonte principal)
SUPABASE_URL = "https://tahubjfdprwwwcqghcec.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRhaHViamZkcHJ3d3djcWdoY2VjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzMwOTQ3NTAsImV4cCI6MjA0ODY3MDc1MH0.3Np1QQR8hNwQ2XQx9Lm8Y5k7kR8z2X9Lm8Y5k7kR8z2X9Lm8Y5k7kR8"

SUPABASE_HEADERS = {
    'apikey': SUPABASE_ANON_KEY,
    'Authorization': f'Bearer {SUPABASE_ANON_KEY}',
    'Content-Type': 'application/json'
}

# Betmind URLs
BETMIND_URL = "https://betmind.org/bacbo"

# Configurações
TIMEOUT_API = 5
MAX_RETRIES = 3
RETRY_DELAY = 1
INTERVALO_COLETA = 3
PORT = int(os.environ.get("PORT", 5000))

# =============================================================================
# CACHE E ESTATÍSTICAS
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
        'ultimas_20_previsoes': [],
        'estrategias': {
            'Compensação': {'acertos': 0, 'erros': 0, 'total': 0},
            'Paredão': {'acertos': 0, 'erros': 0, 'total': 0},
            'Moedor': {'acertos': 0, 'erros': 0, 'total': 0},
            'Xadrez': {'acertos': 0, 'erros': 0, 'total': 0},
            'Contragolpe': {'acertos': 0, 'erros': 0, 'total': 0},
            'Reset Cluster': {'acertos': 0, 'erros': 0, 'total': 0},
            'Falsa Alternância': {'acertos': 0, 'erros': 0, 'total': 0},
            'Meta-Algoritmo': {'acertos': 0, 'erros': 0, 'total': 0}
        }
    },
    'fontes': {
        'supabase': {'sucesso': 0, 'falhas': 0},
        'scraper': {'sucesso': 0, 'falhas': 0, 'driver': None},
        'api': {'sucesso': 0, 'falhas': 0}
    },
    'ultimo_id_processado': None,
    'ultima_previsao': None,
    'ultimo_resultado_real': None
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
session = requests.Session()
session.headers.update(HEADERS)

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
                multiplicador FLOAT,
                fonte TEXT,
                dados_json JSONB
            )
        ''')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_data_hora ON rodadas(data_hora DESC)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_resultado ON rodadas(resultado)')
        
        # Tabela para histórico de previsões
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

def salvar_rodada(rodada, fonte="desconhecida"):
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        rodada['fonte'] = fonte
        cur.execute('''
            INSERT INTO rodadas 
            (id, data_hora, player_score, banker_score, soma, resultado, 
             multiplicador, fonte, dados_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        ''', (
            rodada['id'],
            rodada['data_hora'],
            rodada['player_score'],
            rodada['banker_score'],
            rodada['player_score'] + rodada['banker_score'],
            rodada['resultado'],
            rodada.get('multiplicador', 1),
            rodada.get('fonte', fonte),
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
# 🔥 FONTE 1: SUPABASE (dados reais)
# =============================================================================

def buscar_supabase():
    """Busca rodadas diretamente do Supabase"""
    try:
        # Tenta diferentes tabelas
        tabelas = ['bacbo_rodadas', 'rodadas', 'game_results', 'results', 'bacbo_games']
        
        for tabela in tabelas:
            url = f"{SUPABASE_URL}/rest/v1/{tabela}"
            params = {
                'select': '*',
                'order': 'created_at.desc',
                'limit': 30
            }
            
            response = requests.get(
                url, 
                headers=SUPABASE_HEADERS, 
                params=params, 
                timeout=5
            )
            
            if response.status_code == 200:
                dados = response.json()
                if dados and len(dados) > 0:
                    cache['fontes']['supabase']['sucesso'] += 1
                    print(f"✅ SUPABASE: {len(dados)} rodadas")
                    
                    # Converter para formato padrão
                    rodadas = []
                    for item in dados:
                        rodada = {
                            'id': str(item.get('id', time.time())),
                            'data_hora': datetime.now(timezone.utc),
                            'player_score': item.get('player_score', 0) or item.get('playerScore', 0),
                            'banker_score': item.get('banker_score', 0) or item.get('bankerScore', 0),
                            'resultado': item.get('result', '') or item.get('outcome', ''),
                            'multiplicador': item.get('multiplier', 1)
                        }
                        
                        # Normalizar resultado
                        if 'player' in str(rodada['resultado']).lower():
                            rodada['resultado'] = 'PLAYER'
                        elif 'banker' in str(rodada['resultado']).lower():
                            rodada['resultado'] = 'BANKER'
                        else:
                            rodada['resultado'] = 'TIE'
                        
                        rodadas.append(rodada)
                    
                    return rodadas
        
        cache['fontes']['supabase']['falhas'] += 1
        return None
        
    except Exception as e:
        print(f"⚠️ Supabase erro: {e}")
        cache['fontes']['supabase']['falhas'] += 1
        return None

# =============================================================================
# 🔥 FONTE 2: SCRAPING BETMIND (quando Selenium disponível)
# =============================================================================

class BetmindScraper:
    def __init__(self):
        self.driver = None
        self.ultimas_rodadas = []
        self.running = False
        
    def iniciar(self):
        """Inicia driver Chrome headless"""
        if not SELENIUM_AVAILABLE:
            print("⚠️ Selenium não disponível - scraping desativado")
            return False
        
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            
            # Usar webdriver-manager para gerenciar driver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.get(BETMIND_URL)
            
            # Esperar carregar
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Aceitar cookies se aparecer
            try:
                self.driver.find_element(By.XPATH, "//button[contains(text(), 'Aceitar')]").click()
            except:
                pass
            
            self.running = True
            print("✅ Scraper Betmind iniciado!")
            
            # Thread de scraping
            threading.Thread(target=self.scrape_loop, daemon=True).start()
            return True
            
        except Exception as e:
            print(f"❌ Erro iniciar scraper: {e}")
            return False
    
    def scrape_loop(self):
        """Loop principal de scraping"""
        while self.running:
            try:
                # Tenta encontrar elementos de histórico
                selectors = [
                    "[class*='history']",
                    "[class*='result']",
                    ".round-result",
                    "[class*='game-result']",
                    "table tr",
                    ".history-item"
                ]
                
                novas = []
                for selector in selectors:
                    elementos = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elementos[-15:]:  # Últimos 15
                        texto = elem.text.strip()
                        if texto and ('vs' in texto or 'x' in texto or '-' in texto):
                            resultado = self.parse_texto(texto)
                            if resultado:
                                resultado['timestamp'] = datetime.now().isoformat()
                                novas.append(resultado)
                    
                    if novas:
                        break
                
                # Se encontrou novas rodadas
                if novas:
                    # Evitar duplicatas
                    for nova in novas:
                        if not any(r.get('player') == nova['player'] and 
                                  r.get('banker') == nova['banker'] 
                                  for r in self.ultimas_rodadas[-5:]):
                            self.ultimas_rodadas.append(nova)
                    
                    # Manter últimas 50
                    self.ultimas_rodadas = self.ultimas_rodadas[-50:]
                    
                    print(f"🔥 SCRAPER: {len(novas)} novas rodadas")
                    cache['fontes']['scraper']['sucesso'] += 1
                
                time.sleep(2)
                
            except Exception as e:
                print(f"⚠️ Scraper loop erro: {e}")
                cache['fontes']['scraper']['falhas'] += 1
                time.sleep(5)
    
    def parse_texto(self, texto):
        """Parse texto para extrair scores"""
        import re
        
        # Remove símbolos
        texto_limpo = re.sub(r'[🔴🔵🟡🟠⭐✅❌]', '', texto).strip()
        
        # Procura padrões de números
        numeros = re.findall(r'\d+', texto_limpo)
        
        if len(numeros) >= 2:
            try:
                player = int(numeros[0])
                banker = int(numeros[1])
                
                # Determina cor
                cor = '🟡'  # padrão
                if '🔴' in texto:
                    resultado = 'BANKER'
                    cor = '🔴'
                elif '🔵' in texto:
                    resultado = 'PLAYER'
                    cor = '🔵'
                else:
                    # Tenta inferir pelo score
                    if player > banker:
                        resultado = 'PLAYER'
                        cor = '🔵'
                    elif banker > player:
                        resultado = 'BANKER'
                        cor = '🔴'
                    else:
                        resultado = 'TIE'
                        cor = '🟡'
                
                return {
                    'player': player,
                    'banker': banker,
                    'resultado': resultado,
                    'cor': cor,
                    'id': f"betmind_{player}_{banker}_{int(time.time())}"
                }
            except:
                pass
        
        return None
    
    def get_rodadas(self, n=20):
        """Retorna últimas n rodadas"""
        return self.ultimas_rodadas[-n:]
    
    def parar(self):
        """Para o scraper"""
        self.running = False
        if self.driver:
            self.driver.quit()

# Instanciar scraper
betmind_scraper = BetmindScraper()

# =============================================================================
# FONTE 3: API Casino.org (fallback)
# =============================================================================

def buscar_api_casino():
    try:
        params = PARAMS.copy()
        params['page'] = 0
        params['size'] = 30
        response = session.get(API_URL, params=params, timeout=TIMEOUT_API)
        response.raise_for_status()
        
        dados = response.json()
        if dados:
            cache['fontes']['api']['sucesso'] += 1
            print(f"✅ API Casino: {len(dados)} rodadas")
            
            # Converter formato
            rodadas = []
            for item in dados[:20]:
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

                rodada = {
                    'id': data.get('id', str(time.time())),
                    'data_hora': datetime.now(timezone.utc),
                    'player_score': player_dice.get('score', 0),
                    'banker_score': banker_dice.get('score', 0),
                    'resultado': resultado,
                    'multiplicador': result.get('multiplier', 1)
                }
                rodadas.append(rodada)
            
            return rodadas
            
    except Exception as e:
        print(f"⚠️ API Casino erro: {e}")
        cache['fontes']['api']['falhas'] += 1
    
    return None

# =============================================================================
# COLETOR MULTI-FONTE
# =============================================================================

def coletar_todas_fontes():
    """Tenta todas as fontes em ordem de prioridade"""
    
    # 1. Scraper Betmind (tempo real)
    if betmind_scraper.running:
        scraped = betmind_scraper.get_rodadas(20)
        if scraped and len(scraped) > 0:
            # Converter formato
            rodadas = []
            for item in scraped:
                rodada = {
                    'id': item.get('id', f"scrape_{int(time.time())}"),
                    'data_hora': datetime.now(timezone.utc),
                    'player_score': item['player'],
                    'banker_score': item['banker'],
                    'resultado': item['resultado'],
                    'multiplicador': 1
                }
                rodadas.append(rodada)
            
            print(f"✅ Fonte: Scraper Betmind - {len(rodadas)} rodadas")
            return rodadas, 'scraper'
    
    # 2. Supabase
    supabase_data = buscar_supabase()
    if supabase_data:
        print(f"✅ Fonte: Supabase - {len(supabase_data)} rodadas")
        return supabase_data, 'supabase'
    
    # 3. API Casino (fallback)
    api_data = buscar_api_casino()
    if api_data:
        print(f"✅ Fonte: API Casino - {len(api_data)} rodadas")
        return api_data, 'api'
    
    return None, None

# =============================================================================
# FUNÇÕES LEVES (banco local)
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
    print("📊 Atualizando dados pesados...")
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
    print(f"✅ Pesados: {cache['pesados']['periodos']}")

# =============================================================================
# SISTEMA DE APRENDIZADO
# =============================================================================

def verificar_previsoes_anteriores():
    if cache['ultima_previsao'] and cache['ultimo_resultado_real']:
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
# ESTRATÉGIAS
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
    
    print(f"⚡ Cache atualizado - Total: {cache['leves']['total_rodadas']} | Precisão: {calcular_precisao()}%")

# =============================================================================
# LOOP PRINCIPAL - MULTI-FONTE
# =============================================================================

def loop_coleta_multi():
    print("🔄 Iniciando coleta multi-fonte...")
    ultimo_id = None
    
    while True:
        try:
            inicio = time.time()
            
            # Coletar de todas as fontes
            dados, fonte = coletar_todas_fontes()
            
            if dados and len(dados) > 0:
                print(f"📥 {fonte.upper()}: {len(dados)} itens")
                
                # Pegar primeiro como referência
                primeiro = dados[0]
                novo_id = primeiro.get('id')
                
                if novo_id and novo_id != ultimo_id:
                    ultimo_id = novo_id
                    
                    novas = 0
                    for i, item in enumerate(dados[:15]):  # Processa até 15
                        if salvar_rodada(item, fonte):
                            novas += 1
                            if i == 0:
                                # Guarda resultado real para verificar previsão
                                cache['ultimo_resultado_real'] = item['resultado']
                    
                    if novas > 0:
                        print(f"✅ +{novas} novas rodadas via {fonte}")
                        atualizar_dados_leves()
                        print(f"⚡ Tempo: {time.time() - inicio:.2f}s")
            
            # Estatísticas das fontes
            print(f"📊 Fontes: SUPABASE({cache['fontes']['supabase']['sucesso']}) "
                  f"SCRAPER({cache['fontes']['scraper']['sucesso']}) "
                  f"API({cache['fontes']['api']['sucesso']})")
            
            time.sleep(INTERVALO_COLETA)
            
        except Exception as e:
            print(f"❌ Erro no loop: {e}")
            time.sleep(INTERVALO_COLETA)

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
            'fontes': cache['fontes'],
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
            SELECT data_hora, player_score, banker_score, resultado, fonte
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
                'fonte': row[4],
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
        'cache': {
            'total_rodadas': cache['leves']['total_rodadas'],
            'previsao': cache['leves']['previsao'],
            'estatisticas': {
                'total_previsoes': cache['estatisticas']['total_previsoes'],
                'acertos': cache['estatisticas']['acertos'],
                'erros': cache['estatisticas']['erros'],
                'precisao': calcular_precisao()
            }
        },
        'fontes': cache['fontes']
    })

@app.route('/forcar-scraper')
def forcar_scraper():
    """Força reinicialização do scraper"""
    if betmind_scraper.running:
        betmind_scraper.parar()
        time.sleep(2)
    
    if betmind_scraper.iniciar():
        return jsonify({'status': 'ok', 'mensagem': 'Scraper reiniciado'})
    else:
        return jsonify({'status': 'erro', 'mensagem': 'Falha ao iniciar scraper'}), 500

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("="*70)
    print("🚀 BOT BACBO - MULTI-FONTE (SCRAPING + SUPABASE + API)")
    print("="*70)
    print("✅ Fonte 1: Scraping Betmind.org (tempo real)")
    print("✅ Fonte 2: Supabase (backup)")
    print("✅ Fonte 3: API Casino.org (fallback)")
    print("✅ Sistema de aprendizado automático")
    print("="*70)
    
    # Inicializar banco
    init_db()
    
    # Iniciar scraper
    if SELENIUM_AVAILABLE:
        print("🔌 Iniciando scraper Betmind...")
        betmind_scraper.iniciar()
    else:
        print("⚠️ Selenium não disponível - Scraper desativado")
        print("   Instale com: pip install selenium webdriver-manager")
    
    # Dados iniciais
    print("📊 Carregando dados iniciais...")
    atualizar_dados_leves()
    atualizar_dados_pesados()
    
    print(f"📊 {cache['leves']['total_rodadas']} rodadas no banco")
    print("="*70)
    
    # Threads
    print("🚀 Iniciando threads...")
    threading.Thread(target=loop_coleta_multi, daemon=True).start()
    threading.Thread(target=loop_pesado, daemon=True).start()
    
    print("✅ Servidor Flask iniciando...")
    app.run(host='0.0.0.0', port=PORT, debug=False)
