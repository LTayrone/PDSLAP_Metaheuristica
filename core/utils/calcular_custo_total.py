import math
import numpy as np


def calcular_custo_total(solucao, parametros):
    """
    Calcula o valor da função objetivo para uma dada solução, baseando-se na formulação.

    Args:
        solucao (dict): Dicionário contendo as variáveis de decisão x, I, Q, gamma, y, z.
        parametros (dict): Dicionário com todos os parâmetros do problema.

    Returns:
        float: O valor total da função objetivo.
    """
    # Extrai as variáveis de decisão da solução
    x = solucao["x"]
    I = solucao["I"]
    Q = solucao["Q"]
    gamma = solucao["gamma"]
    y = solucao["y"]
    z = solucao["z"]

    # Extrai os parâmetros
    num_pedidos = parametros["num_pedidos"]
    num_periodos = parametros["num_periodos"]
    num_itens = parametros["num_itens"]
    receita_pedido = parametros["receita_pedido"]
    custo_estoque = parametros["custo_estoque"]
    custo_setup = parametros["custo_setup"]
    periodo_inicial_entrega = parametros["periodo_inicial_entrega"]
    periodo_final_entrega = parametros["periodo_final_entrega"]
    vida_util = parametros["vida_util"]

    total_receita = 0
    total_custo_estoque = 0
    total_custo_setup = 0

    # 1. Calcular Receita Total (Primeiro termo da FO)
    # sum_{n=1}^{N} sum_{t=F_n}^{L_n} P_{nt} * gamma_{nt}
    for n in range(num_pedidos):
        for t in range(periodo_inicial_entrega[n], periodo_final_entrega[n] + 1):
            if t < num_periodos: # Garante que 't' esteja dentro do horizonte de planejamento
                total_receita += receita_pedido[n][t] * gamma[n][t]

    # 2. Calcular Custo de Estoque (Segundo termo da FO)
    # sum_{j=1}^{J} sum_{t=1}^{T} sum_{k=0}^{sl_j} h_j * I_{jt}^k
    for j in range(num_itens):
        for t in range(num_periodos):
            # Iterar sobre as idades válidas do item j
            for k in range(0, vida_util[j] + 1): # k vai de 0 até sl_j
                total_custo_estoque += custo_estoque[j] * I[j][t][k]

    # 3. Calcular Custo de Setup (Terceiro termo da FO)
    # sum_{t=1}^{T} sum_{i=1}^{J} sum_{j=1}^{J} sc_{ij} * z_{ijt}
    for t in range(num_periodos):
        for i in range(num_itens):
            for j in range(num_itens):
                total_custo_setup += custo_setup[i][j] * z[i][j][t]

    # A função objetivo é MAX Receita - Custo Estoque - Custo Setup
    funcao_objetivo_valor = total_receita - total_custo_estoque - total_custo_setup
    print(f"Receita: {total_receita:.2f}")
    print(f"Custo Estoque: {total_custo_estoque:.2f}")
    print(f"Custo Setup: {total_custo_setup:.2f}")
    print(f"Lucro Líquido: {funcao_objetivo_valor:.2f}")

    return funcao_objetivo_valor