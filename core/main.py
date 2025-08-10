# Universidade Federal de Ouro Preto
# Mestrado em Engenharia de Produção
# Professor: Dr. Aloisio de Castro e Dr. Marcone Jamilson
# Aluno: Lucas Tayrone Moreira Ribeiro

from utils.calcular_custo_total import calcular_custo_total
from utils.carregar_parametros_otimizacao import carregar_parametros_otimizacao
from utils.gerar_solucao_inicial_hc1_atualizada import gerar_solucao_inicial_hc1_atualizada
from utils.operacoes_vizinhanca import *
from utils.construir_solucao_grasp import construir_solucao_grasp
from utils.heuristicaInteiros import *

import numpy as np
import random
import time
from copy import deepcopy # Importar deepcopy para garantir cópias independentes

def imprimir_solucao(solucao, parametros):
    """
    Função auxiliar para imprimir os detalhes de uma solução de forma organizada.
    """
    if not solucao:
        print("A solução é nula ou não foi gerada.")
        return

    print("\n--- Detalhes da Solução ---")

    # Imprimir Variável x (Produção)
    print("\nVariável x (Produção do item j no período t):")
    producao_encontrada = False
    for j in range(parametros["num_itens"]):
        for t in range(parametros["num_periodos"]):
            if solucao.get("x", {}).get(j, {}).get(t, 0) > 0:
                print(f"x[{j}][{t}]: {solucao['x'][j][t]}")
                producao_encontrada = True
    if not producao_encontrada:
        print("Nenhuma produção planejada.")

    # Imprimir Variável gamma (Pedidos Atendidos)
    print("\nVariável gamma (Pedido n atendido no instante t):")
    pedidos_atendidos = False
    for n in range(parametros["num_pedidos"]):
        for t in range(parametros["num_periodos"]):
            if solucao.get("gamma", {}).get(n, {}).get(t, 0) == 1:
                print(f"gamma[{n}][{t}]: {solucao['gamma'][n][t]}")
                pedidos_atendidos = True
    if not pedidos_atendidos:
        print("Nenhum pedido foi atendido.")
    
    # Imprimir Sequências de Produção
    print("\n--- Sequência de Produção por Período ---")
    sequencia_encontrada = False
    for t in range(parametros["num_periodos"]):
        if solucao.get("sequencias_producao", {}).get(t):
            print(f"Período {t}: {solucao['sequencias_producao'][t]}")
            sequencia_encontrada = True
    if not sequencia_encontrada:
        print("Nenhuma sequência de produção definida.")
    print("-" * 30)


if __name__ == "__main__":
    caminho_arquivo_dados = (r"C:\Users\User\Downloads\aplicacaoMestrado\PDSLAP_Metaheuristica\core\inst0_1.txt")

    # 1. Carregar os parâmetros
    parametros = carregar_parametros_otimizacao(caminho_arquivo_dados)
    print("--- Parâmetros Carregados ---")
    for k, v in parametros.items():
        if isinstance(v, np.ndarray):
            print(f"{k}: \n{v}")
        else:
            print(f"{k}: {v}")
    print("-" * 30)

#     # 2. Gerar a solução inicial
#     # A heurística gerar_solucao_inicial_hc1_atualizada já deve retornar uma solução factível e completa.
#     solucao_inicial = gerar_solucao_inicial_hc1_atualizada(parametros)
    

#     print("\n--- Solução Inicial Gerada ---")

#     # Imprimir Variável x (Produção do item j no período t)
#     print("\nVariável x (Produção do item j no período t):")
#     for j in range(parametros["num_itens"]):
#         for t in range(parametros["num_periodos"]):
#             if solucao_inicial["x"][j][t] > 0:
#                 print(f"x[{j}][{t}]: {solucao_inicial['x'][j][t]}")

#     # Imprimir Variável I (Estoque do item j com idade k ao final do período t)
#     print("\nVariável I (Estoque de item j no final do período t com idade k ):")
#     for j in range(parametros["num_itens"]):
#         for t in range(parametros["num_periodos"]):
#             for k in range(max(parametros["vida_util"]) + 1):
#                 if solucao_inicial["I"][j][t][k] > 0:
#                     print(f"I[{j}][{t}][{k}]: {solucao_inicial['I'][j][t][k]}")

#     # Imprimir Variável Q (Quantidade de itens j com idade k utilizados para atender pedido n no período t)
#     print("\nVariável Q (Itens j para pedido n no período t de idade k):")
#     for j in range(parametros["num_itens"]):
#         for n in range(parametros["num_pedidos"]):
#             for t in range(parametros["num_periodos"]):
#                 for k in range(max(parametros["vida_util"]) + 1):
#                     if solucao_inicial["Q"][j][n][t][k] > 0:
#                         print(f"Q[{j}][{n}][{t}][{k}]: {solucao_inicial['Q'][j][n][t][k]}")

#     print("\nVariável gamma (Pedido n atendido no instante t):")
#     for n in range(parametros["num_pedidos"]):
#         for t in range(parametros["num_periodos"]):
#             if solucao_inicial["gamma"][n][t] == 1:
#                 print(f"gamma[{n}][{t}]: {solucao_inicial['gamma'][n][t]}")

#     print("\nVariável y (Máquina Preparada para o item j no instante t (t = 0 não há setup definido)):")
#     for j in range(parametros["num_itens"]):
#         for t in range(parametros["num_periodos"]):
#             if solucao_inicial["y"][j][t] == 1:
#                 print(f"y[{j}][{t}]: {solucao_inicial['y'][j][t]}")

#     print("\nVariável z (Troca da produção do item i para o item j no período t (z[i][j][t] == 1)):")
#     for i in range(parametros["num_itens"]):
#         for j in range(parametros["num_itens"]):
#             for t in range(parametros["num_periodos"]):
#                 if solucao_inicial["z"][i][j][t] == 1:
#                     print(f"z[{i}][{j}][{t}]: {solucao_inicial['z'][i][j][t]}")

#     # Sequencias de Produção por Período
#     print("\n--- Sequência de Produção por Período ---")
#     for t in range(parametros["num_periodos"]):
#         if solucao_inicial["sequencias_producao"][t]:
#             print(f"Período {t}: {solucao_inicial['sequencias_producao'][t]}")
#         else:
#             print(f"Período {t}: Nenhuma produção ou sequência definida.")
#     print("-" * 30)

#     # 3. Calcular o custo total da solução inicial
#     valor_fo_inicial = calcular_custo_total(solucao_inicial, parametros)
#     print(f"\nValor da Função Objetivo da Solução Inicial: {valor_fo_inicial}")
#     print("-" * 30)

# print("\n--- TESTANDO MOVIMENTO DE VIZINHANÇA: Trocar Ordem de Produção ---")
# nova_solucao_swap, delta_swap = trocar_ordem_producao_2_itens(solucao_inicial, parametros)

# if nova_solucao_swap:
#     print("\nMovimento SWAP RESULTADO: Solução melhor encontrada!")
#     print(f"Delta de Lucro: {delta_swap}")
#     solucao_atual = nova_solucao_swap # Atualiza a solução para continuar testando
# else:
#     print("\nMovimento SWAP RESULTADO: Nenhuma melhoria encontrada ou movimento inválido.")
#     solucao_atual = solucao_inicial # Mantém a original se não houver melhora
# print("-" * 30)

# # 3. Gerar a solução com a Fase de Construção do GRASP
# print("\n--- EXECUTANDO FASE DE CONSTRUÇÃO GRASP ---")
# # O parâmetro alpha controla o quão gulosa ou aleatória é a construção.
# # alpha = 0.0 -> totalmente guloso (deve dar um resultado similar ao HC1)
# # alpha = 1.0 -> totalmente aleatório
# # alpha = 0.2 ou 0.3 são valores comuns para começar.
# alpha_grasp = 0.8
# solucao_grasp = construir_solucao_grasp(parametros, alpha_grasp)
# imprimir_solucao(solucao_grasp, parametros)
# valor_fo_grasp = calcular_custo_total(solucao_grasp, parametros) # 
# print(f"\nValor da Função Objetivo (GRASP, alpha={alpha_grasp}): {valor_fo_grasp}")
# print("-" * 50)



# Heurística
solucao_heur = gerar_solucao_heuristica_original(parametros)
valor_final = calcular_FO(solucao_heur, parametros)

# Verificar viabilidade
if validar_restricoes(solucao_heur, parametros):
    print("Solução viável!")
else:
    print("Solução aproximada - algumas restrições podem precisar de ajuste.")

print("\n--- Heuristica Finalizada ---")
print(f"Melhor valor de função objetivo encontrado: {valor_final:.2f}")

# Extrair e imprimir pedidos aceitos (iterando sobre o array gamma)
print("\nPedidos aceitos (pedido, período):")
gamma = solucao_heur['gamma']  # Array (N, T)
encontrou = False
for n in range(gamma.shape[0]):  # Para cada pedido n
    for t in range(gamma.shape[1]):  # Para cada período t
        if gamma[n, t] == 1:
            print(f" - Pedido {n+1} no período {t+1}")
            encontrou = True
if not encontrou:
    print(" - Nenhum pedido aceito.")

# Extrair e imprimir sequências de produção por período (derivadas de V e z)
print("\nSequências de produção por período:")
V = solucao_heur['V']  # Array (J, T)
z = solucao_heur['z']  # Array (J, J, T)
for t in range(V.shape[1]):  # Para cada período t
    # Encontrar itens produzidos (onde V[j, t] > 0 ou há setups)
    itens_t = [j for j in range(V.shape[0]) if V[j, t] > 0 or np.sum(z[:, j, t]) > 0 or np.sum(z[j, :, t]) > 0]
    if itens_t:
        # Ordenar por V[j, t] (ordem de produção)
        seq = sorted(itens_t, key=lambda j: V[j, t])
        print(f" - Período {t+1}: {seq}")
    else:
        print(f" - Período {t+1}: Nenhuma sequência (sem produção).")