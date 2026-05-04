import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright
import os

class BacBoCapturer:
    def __init__(self):
        self.results = []
        self.processed_rounds = set()
        
    def process_message(self, payload):
        """Processa as mensagens do WebSocket"""
        try:
            data = json.loads(payload)
            
            # Verifica se é mensagem do Bac Bo
            if data.get("type") == "bacbo.playerState":
                game = data.get("args", {}).get("game", {})
                dice = game.get("dice", [])
                round_number = game.get("number", "")
                
                # Mostra status dos dados
                if dice:
                    status = [d.get("status") for d in dice]
                    print(f"📊 Round {round_number}: {status}")
                
                # Verifica se todos os dados foram lançados
                if len(dice) == 4 and all(d.get("status") == "Evaluated" for d in dice):
                    round_id = game.get("id", "")
                    
                    # Evita duplicatas
                    if round_id not in self.processed_rounds:
                        self.processed_rounds.add(round_id)
                        
                        # Extrai valores dos dados
                        valores = [d["value"] for d in dice]
                        player_total = valores[0] + valores[1]
                        banker_total = valores[2] + valores[3]
                        
                        # Determina vencedor
                        if player_total > banker_total:
                            winner = "Player"
                        elif banker_total > player_total:
                            winner = "Banker"
                        else:
                            winner = "Tie"
                        
                        # Formata resultado
                        result = {
                            "type": "game.result",
                            "args": {
                                "dice": valores,
                                "winner": winner,
                                "round": round_number,
                                "player_total": player_total,
                                "banker_total": banker_total,
                                "timestamp": datetime.now().isoformat()
                            }
                        }
                        
                        # Mostra no console
                        print(f"\n{'='*50}")
                        print(f"🎲 RESULTADO - Round {round_number}")
                        print(f"   Dados: {valores}")
                        print(f"   Player: {player_total} | Banker: {banker_total}")
                        print(f"   VENCEDOR: {winner}")
                        print(f"{'='*50}\n")
                        
                        # Salva resultado
                        self.results.append(result)
                        
                        # Salva em arquivo
                        with open("bacbo_results.json", "w") as f:
                            json.dump(self.results, f, indent=2)
                        
                        # Salva também em CSV
                        self.save_to_csv(result)
                        
        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"Erro: {e}")
    
    def save_to_csv(self, result):
        """Salva resultado em CSV"""
        import csv
        import os
        
        args = result['args']
        file_exists = os.path.isfile('bacbo_results.csv')
        
        with open('bacbo_results.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['timestamp', 'round', 'dice1', 'dice2', 'dice3', 'dice4', 'player_total', 'banker_total', 'winner'])
            
            writer.writerow([
                args['timestamp'],
                args['round'],
                args['dice'][0], args['dice'][1], args['dice'][2], args['dice'][3],
                args['player_total'],
                args['banker_total'],
                args['winner']
            ])
    
    async def run(self):
        """Executa o capturador"""
        print("="*60)
        print("🎰 BAC BO - CAPTURADOR AUTOMÁTICO")
        print("   Igual ao do vídeo - com navegador real")
        print("="*60)
        
        # Verifica se é modo headless
        headless = os.environ.get('HEADLESS', 'false').lower() == 'true'
        
        async with async_playwright() as p:
            # Abre navegador REAL
            browser = await p.chromium.launch(
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox'
                ]
            )
            
            # Cria contexto com fingerprint real
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            # Abre página
            page = await context.new_page()
            
            # Vai para o site
            print("\n🌐 Abrindo o site...")
            await page.goto("https://win1.casino/pt-br/game/evolution-gaming-bac-bo")
            
            # Aguarda o iframe carregar
            print("\n⏳ Aguardando o jogo carregar...")
            await page.wait_for_timeout(15000)
            
            print("\n✅ Jogo carregado! Aguardando resultados...")
            print("💡 O navegador vai ficar aberto capturando os resultados\n")
            
            # Intercepta WebSocket
            def on_websocket(ws):
                print(f"\n🔌 WebSocket conectado!")
                print(f"📡 URL: {ws.url[:100]}...")
                
                # Salva URL do WebSocket
                with open("websocket_url.txt", "w") as f:
                    f.write(ws.url)
                
                # Escuta mensagens
                ws.on("framereceived", lambda frame: self.process_message(frame.payload))
            
            page.on("websocket", on_websocket)
            
            # Mantém rodando
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\n\n🛑 Encerrando...")
                print(f"📊 Total de resultados capturados: {len(self.results)}")
            
            await browser.close()

# Executa
if __name__ == "__main__":
    capturer = BacBoCapturer()
    asyncio.run(capturer.run())
