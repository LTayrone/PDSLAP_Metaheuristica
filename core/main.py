# Universidade Federal de Ouro Preto
# Mestrado em Engenharia de Produção
# Professor: Dr. Aloisio de Castro e Dr. Marcone Jamilson
# Aluno: Lucas Tayrone Moreira Ribeiro

from utils.calcular_custo_total import calcular_custo_total
from utils.carregar_parametros_otimizacao import carregar_parametros_otimizacao
from utils.gerar_solucao_inicial_hc1_atualizada import gerar_solucao_inicial_hc1_atualizada
from utils.operacoes_vizinhanca import trocar_ordem_producao_2_itens, alterar_periodo_atendimento_pedido # Adicione a nova função

import numpy as np
import random
import time
from copy import deepcopy # Importar deepcopy para garantir cópias independentes

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
    # A heurística gerar_solucao_inicial_hc1_atualizada já deve retornar uma solução factível e completa.
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

    # Sequencias de Produção por Período
    print("\n--- Sequência de Produção por Período ---")
    for t in range(parametros["num_periodos"]):
        if solucao_inicial["sequencias_producao"][t]:
            print(f"Período {t}: {solucao_inicial['sequencias_producao'][t]}")
        else:
            print(f"Período {t}: Nenhuma produção ou sequência definida.")
    print("-" * 30)

    # 3. Calcular o custo total da solução inicial
    valor_fo_inicial = calcular_custo_total(solucao_inicial, parametros)
    print(f"\nValor da Função Objetivo da Solução Inicial: {valor_fo_inicial}")
    print("-" * 30)

print("\n--- TESTANDO MOVIMENTO DE VIZINHANÇA: Trocar Ordem de Produção ---")
nova_solucao_swap, delta_swap = trocar_ordem_producao_2_itens(solucao_inicial, parametros)

if nova_solucao_swap:
    print("\nMovimento SWAP RESULTADO: Solução melhor encontrada!")
    print(f"Delta de Lucro: {delta_swap}")
    solucao_atual = nova_solucao_swap # Atualiza a solução para continuar testando
else:
    print("\nMovimento SWAP RESULTADO: Nenhuma melhoria encontrada ou movimento inválido.")
    solucao_atual = solucao_inicial # Mantém a original se não houver melhora
print("-" * 30)

print("\n--- TESTANDO MOVIMENTO DE VIZINHANÇA: Alterar Período de Atendimento ---")

nova_solucao_move_order, delta_move_order = alterar_periodo_atendimento_pedido(solucao_atual, parametros) # Use a solução atualizada

if nova_solucao_move_order:
    print("\nMovimento MOVER PEDIDO RESULTADO: Solução melhor encontrada!")
    print(f"Delta de Lucro: {delta_move_order}")
    # solucao_atual = nova_solucao_move_order # Pode atualizar novamente se quiser encadear
else:
    print("\nMovimento MOVER PEDIDO RESULTADO: Nenhuma melhoria encontrada ou movimento inválido.")
print("-" * 30)