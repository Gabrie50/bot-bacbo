import requests
import time
import json
import os
from datetime import datetime
import sys
from collections import Counter

# Configurações
API_URL = "https://api-cs.casino.org/svc-evolution-game-events/api/bacbo?page=0&size=10&sort=data.settledAt,desc&duration=30&wheelResults=PlayerWon,BankerWon,Tie"
INTERVALO = 10  # segundos
ARQUIVO_DADOS = "dados_bacbo.json"

class BotBacBo:
    def __init__(self):
        self.rodadas = []
        self.ultimo_id = None
        self.inicio = datetime.now()
        self.total_coletadas = 0
        
    def carregar_dados(self):
        """Carrega dados salvos anteriormente"""
        try:
            if os.path.exists(ARQUIVO_DADOS):
                with open(ARQUIVO_DADOS, 'r', encoding='utf-8') as f:
                    self.rodadas = json.load(f)
                print(f"📂 Dados carregados: {len(self.rodadas)} rodadas")
        except Exception as e:
            print(f"⚠️ Erro ao carregar dados: {e}")
    
    def salvar_dados(self):
        """Salva dados em arquivo"""
        try:
            # Manter apenas as últimas 10000 rodadas
            if len(self.rodadas) > 10000:
                self.rodadas = self.rodadas[-10000:]
            
            with open(ARQUIVO_DADOS, 'w', encoding='utf-8') as f:
                json.dump(self.rodadas, f, indent=2, ensure_ascii=False)
            print(f"💾 Dados salvos: {len(self.rodadas)} rodadas")
        except Exception as e:
            print(f"❌ Erro ao salvar: {e}")
    
    def buscar_novas(self):
        """Busca novas rodadas da API"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            response = requests.get(API_URL, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️ HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"⚠️ Erro na API: {e}")
            return None
    
    def processar_rodada(self, item):
        """Extrai informações da rodada"""
        try:
            data = item.get('data', {})
            result = data.get('result', {})
            
            player = result.get('playerDice', {}).get('score', 0)
            banker = result.get('bankerDice', {}).get('score', 0)
            outcome = result.get('outcome', 'Desconhecido')
            
            # Converter outcome para símbolo
            if outcome == 'PlayerWon':
                simbolo = '🔴'
                tipo = 'PLAYER'
            elif outcome == 'BankerWon':
                simbolo = '⚫'
                tipo = 'BANKER'
            elif outcome == 'Tie':
                simbolo = '🟡'
                tipo = 'TIE'
            else:
                simbolo = '⚪'
                tipo = 'DESCONHECIDO'
            
            return {
                'id': data.get('id'),
                'timestamp': data.get('settledAt'),
                'player': player,
                'banker': banker,
                'resultado': outcome,
                'simbolo': simbolo,
                'tipo': tipo,
                'hora': datetime.now().strftime('%H:%M:%S'),
                'extremo': player >= 10 or banker >= 10 or player <= 2 or banker <= 2
            }
            
        except Exception as e:
            print(f"⚠️ Erro processando: {e}")
            return None
    
    def mostrar_estatisticas(self):
        """Exibe estatísticas das rodadas"""
        if len(self.rodadas) < 10:
            return
        
        # Últimas 100 rodadas para tendência
        ultimas = self.rodadas[-100:] if len(self.rodadas) > 100 else self.rodadas
        
        players = sum(1 for r in ultimas if r['resultado'] == 'PlayerWon')
        bankers = sum(1 for r in ultimas if r['resultado'] == 'BankerWon')
        ties = sum(1 for r in ultimas if r['resultado'] == 'Tie')
        
        print("\n" + "="*50)
        print(f"📊 ESTATÍSTICAS (últimas {len(ultimas)} rodadas)")
        print(f"🔴 PLAYER: {players} ({players/len(ultimas)*100:.1f}%)")
        print(f"⚫ BANKER: {bankers} ({bankers/len(ultimas)*100:.1f}%)")
        print(f"🟡 TIE: {ties} ({ties/len(ultimas)*100:.1f}%)")
        
        # Sequências
        if len(self.rodadas) >= 5:
            ultimos_5 = self.rodadas[-5:]
            sequencia = ''.join([r['simbolo'] for r in ultimos_5])
            print(f"📈 Últimos 5: {sequencia}")
        
        # Total
        horas = (datetime.now() - self.inicio).total_seconds() / 3600
        print(f"⏱️  Rodadas: {len(self.rodadas)} | Tempo: {horas:.1f}h")
        print("="*50)
    
    def executar(self):
        """Loop principal do bot"""
        print("\n" + "="*50)
        print("🎲 BOT BAC BO - RAILWAY 24/7")
        print("="*50)
        
        # Carregar dados existentes
        self.carregar_dados()
        
        # Timer para salvamento automático
        ultimo_salvamento = time.time()
        contador_estatisticas = 0
        
        while True:
            try:
                # Buscar dados
                dados = self.buscar_novas()
                
                if dados and 'content' in dados:
                    novas_rodadas = 0
                    
                    for item in dados['content']:
                        rodada = self.processar_rodada(item)
                        
                        if rodada and rodada['id']:
                            # Verificar se é nova
                            if not any(r.get('id') == rodada['id'] for r in self.rodadas):
                                self.rodadas.append(rodada)
                                novas_rodadas += 1
                                
                                # Mostrar em tempo real
                                extremo = "⚡" if rodada['extremo'] else ""
                                print(f"[{rodada['hora']}] {rodada['simbolo']} {rodada['player']} x {rodada['banker']} {extremo}")
                    
                    if novas_rodadas > 0:
                        self.total_coletadas += novas_rodadas
                        print(f"   ➕ +{novas_rodadas} novas | Total: {len(self.rodadas)}")
                        
                        # Mostrar estatísticas a cada 10 rodadas
                        contador_estatisticas += novas_rodadas
                        if contador_estatisticas >= 10:
                            self.mostrar_estatisticas()
                            contador_estatisticas = 0
                    
                    # Salvar a cada 5 minutos
                    if time.time() - ultimo_salvamento > 300:  # 5 minutos
                        self.salvar_dados()
                        ultimo_salvamento = time.time()
                
                # Aguardar próximo ciclo
                time.sleep(INTERVALO)
                
            except KeyboardInterrupt:
                print("\n🛑 Bot parado pelo usuário")
                self.salvar_dados()
                sys.exit(0)
                
            except Exception as e:
                print(f"❌ Erro no loop: {e}")
                time.sleep(INTERVALO)

if __name__ == "__main__":
    bot = BotBacBo()
    bot.executar()
