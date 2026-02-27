# web_interface.py - Interface Web para o Bot BacBo

from flask import Flask, render_template, jsonify
from datetime import datetime
import psycopg2
import os
import json

app = Flask(__name__)

# Importar cache do main.py
import main
cache = main.cache_estatisticas
conn = None

def get_db_connection():
    """Obtém conexão com o banco de dados."""
    global conn
    if conn is None or conn.closed:
        conn = main.conectar_banco()
    return conn

@app.route('/')
def index():
    """Página principal com dashboard."""
    return render_template('index.html')

@app.route('/api/stats')
def api_stats():
    """API que retorna estatísticas em JSON."""
    try:
        # Tentar usar cache primeiro
        if cache['ultima_atualizacao']:
            ultima_atual = cache['ultima_atualizacao'].strftime('%d/%m/%Y %H:%M:%S')
        else:
            ultima_atual = 'Aguardando dados...'
        
        # Últimas 20 rodadas para o gráfico
        ultimas_20 = []
        for r in cache['ultimas_100'][:20]:
            cor = '🔴' if r['resultado'] == 'PLAYER' else '⚫' if r['resultado'] == 'BANKER' else '🟡'
            ultimas_20.append({
                'hora': r['data_hora'].strftime('%H:%M') if hasattr(r['data_hora'], 'strftime') else str(r['data_hora']),
                'resultado': r['resultado'],
                'cor': cor,
                'player': r['player_score'],
                'banker': r['banker_score']
            })
        
        # Última previsão (simulada - você pode querer calcular de verdade)
        conn = get_db_connection()
        previsao = main.prever_proxima_cor(conn) if conn else None
        
        response = {
            'ultima_atualizacao': ultima_atual,
            'total_rodadas': len(cache['ultimas_72h']),
            'resumo': cache['resumo'],
            'ultimas_20': ultimas_20,
            'previsao': {
                'cor': previsao['previsao'] if previsao else 'N/A',
                'confianca': f"{previsao['confianca']:.1f}%" if previsao else 'N/A',
                'modo': previsao['modo'] if previsao else 'N/A',
                'delay': previsao['delay_ativo'] if previsao else False
            } if previsao else None
        }
        return jsonify(response)
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/tabela/<int:horas>')
def api_tabela(horas):
    """API que retorna a tabela de rodadas para um período."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'erro': 'Sem conexão com banco'}), 500
        
        # Usar cache para 72h, buscar do banco para outros períodos
        if horas == 72:
            rodadas = cache['ultimas_72h']
        else:
            rodadas = main.buscar_rodadas_periodo(conn, horas)
        
        # Formatar para JSON
        tabela = []
        for r in rodadas:
            cor = '🔴' if r['resultado'] == 'PLAYER' else '⚫' if r['resultado'] == 'BANKER' else '🟡'
            tabela.append({
                'data': r['data_formatada'] if 'data_formatada' in r else r['data_hora'].strftime('%d/%m %H:%M'),
                'player': r['player_score'],
                'banker': r['banker_score'],
                'resultado': r['resultado'],
                'cor': cor,
                'mult': f"{r['multiplicador']}x" if 'multiplicador' in r else '1x',
                'winners': r['total_winners'] if 'total_winners' in r else 0,
                'premio': f"€{r['total_amount']:,.0f}" if 'total_amount' in r and r['total_amount'] else '€0'
            })
        
        return jsonify(tabela)
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
