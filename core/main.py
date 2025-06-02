# Universidade Federal de Ouro Preto
# Mestrado em Engenharia de Produção
# Professor: Dr. Aloisio de Castro e Dr. Marcone Jamilson
# Aluno: Lucas Tayrone Moreira Ribeiro

from utils.calcular_custo_total import calcular_custo_total
# from utils.gerar_solucao_inicial import gerar_solucao_inicial # Não usada
# from utils.gerar_solucao_inicial_hc1 import gerar_solucao_inicial_hc1 # Não usada
from utils.carregar_parametros_otimizacao import carregar_parametros_otimizacao
from utils.gerar_solucao_inicial_hc1_atualizada import gerar_solucao_inicial_hc1_atualizada

import numpy as np

if __name__ == "__main__":
    caminho_arquivo_dados = (r"C:\Users\User\Downloads\aplicacaoMestrado\PDSLAP_Metaheuristica\core\inst0_5.txt")

    # 1. Carregar os parâmetros
    parametros = carregar_parametros_otimizacao(caminho_arquivo_dados)
    print("--- Parâmetros Carregados ---")
    for k, v in parametros.items():
        if isinstance(v, np.ndarray):
            print(f"{k}: \n{v}")
        else:
            print(f"{k}: {v}")
    print("-" * 30)

    # 2. Gerar a solução inicial
    solucao_inicial = gerar_solucao_inicial_hc1_atualizada(parametros)
    print("\n--- Solução Inicial Gerada ---")

    # Imprimir Variável x (Produção do item j no período t)
    print("\nVariável x (Produção do item j no período t):")
    for j in range(parametros["num_itens"]):
        for t in range(parametros["num_periodos"]):
            if solucao_inicial["x"][j][t] > 0:
                print(f"x[{j}][{t}]: {solucao_inicial['x'][j][t]}")

    # Imprimir Variável I (Estoque do item j com idade k ao final do período t)
    print("\nVariável I (Estoque de item j no final do período t com idade k ):")
    for j in range(parametros["num_itens"]):
        for t in range(parametros["num_periodos"]):
            for k in range(max(parametros["vida_util"]) + 1):
                if solucao_inicial["I"][j][t][k] > 0:
                    print(f"I[{j}][{t}][{k}]: {solucao_inicial['I'][j][t][k]}")

    # Imprimir Variável Q (Quantidade de itens j com idade k utilizados para atender pedido n no período t)
    print("\nVariável Q (Itens j para pedido n no período t de idade k):")
    for j in range(parametros["num_itens"]):
        for n in range(parametros["num_pedidos"]):
            for t in range(parametros["num_periodos"]):
                for k in range(max(parametros["vida_util"]) + 1):
                    if solucao_inicial["Q"][j][n][t][k] > 0:
                        print(f"Q[{j}][{n}][{t}][{k}]: {solucao_inicial['Q'][j][n][t][k]}")

    print("\nVariável gamma (Pedido n atendido no instante t):")
    for n in range(parametros["num_pedidos"]):
        for t in range(parametros["num_periodos"]):
            if solucao_inicial["gamma"][n][t] == 1:
                print(f"gamma[{n}][{t}]: {solucao_inicial['gamma'][n][t]}")

    print("\nVariável y (Máquina Preparada para o item j no instante t (t = 0 não há setup definido)):")
    for j in range(parametros["num_itens"]):
        for t in range(parametros["num_periodos"]):
            if solucao_inicial["y"][j][t] == 1:
                print(f"y[{j}][{t}]: {solucao_inicial['y'][j][t]}")

    print("\nVariável z (Troca da produção do item i para o item j no período t (z[i][j][t] == 1)):")
    for i in range(parametros["num_itens"]):
        for j in range(parametros["num_itens"]):
            for t in range(parametros["num_periodos"]):
                if solucao_inicial["z"][i][j][t] == 1:
                    print(f"z[{i}][{j}][{t}]: {solucao_inicial['z'][i][j][t]}")

    # NOVO BLOCO PARA IMPRIMIR A SEQUÊNCIA DE PRODUÇÃO
    print("\n--- Sequência de Produção por Período ---")
    for t in range(parametros["num_periodos"]):
        if solucao_inicial["sequencias_producao"][t]:
            print(f"Período {t}: {solucao_inicial['sequencias_producao'][t]}")
        else:
            print(f"Período {t}: Nenhuma produção ou sequência definida.")
    print("-" * 30)

    # 3. Calcular o custo total da solução inicial
    valor_fo = calcular_custo_total(solucao_inicial, parametros)
    print(f"\nValor da Função Objetivo da Solução Inicial: {valor_fo}")
    print("-" * 30)