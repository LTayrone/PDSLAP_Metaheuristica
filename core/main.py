# Universidade Federal de Ouro Preto
# Mestrado em Engenharia de Produção
# Professor: Dr. Aloisio de Castro e Dr. Marcone Jamilson
# Aluno: Lucas Tayrone Moreira Ribeiro

from utils.calcular_custo_total import calcular_custo_total
from utils.carregar_parametros_otimizacao import carregar_parametros_otimizacao
from utils.gerar_solucao_inicial_hc1_atualizada import gerar_solucao_inicial_hc1_atualizada
from utils.operacoes_vizinhanca import realizar_movimento, recalcular_variaveis_dependentes, validar_todas_restricoes # Importar recalcular_variaveis_dependentes e validar_todas_restricoes ainda é útil para depuração ou uso futuro, mas não na validação inicial aqui.

import numpy as np
import random
import time
from copy import deepcopy # Importar deepcopy para garantir cópias independentes

if __name__ == "__main__":
    caminho_arquivo_dados = (r"C:\Users\User\Downloads\aplicacaoMestrado\PDSLAP_Metaheuristica\core\inst0_2.txt")

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
    
    # REMOVIDA A VALIDAÇÃO EXTRA DA SOLUÇÃO INICIAL AQUI
    # solucao_inicial_parcial = gerar_solucao_inicial_hc1_atualizada(parametros)
    # solucao_inicial = recalcular_variaveis_dependentes(solucao_inicial_parcial, parametros)
    # if solucao_inicial is None or not validar_todas_restricoes(solucao_inicial, parametros):
    #     print("ERRO: A solução inicial gerada é infactível. Não é possível iniciar a busca local.")
    #     exit()

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
    valor_fo_inicial = calcular_custo_total(solucao_inicial, parametros)
    print(f"\nValor da Função Objetivo da Solução Inicial: {valor_fo_inicial}")
    print("-" * 30)

    # 4. Seção de Busca Local (Hill Climbing - Best Improvement)
    print("\n--- Iniciando Busca Local (Hill Climbing - Best Improvement) ---")
    
    melhor_solucao_global = deepcopy(solucao_inicial)
    melhor_valor_fo_global = valor_fo_inicial
    
    iteracoes_max = 500 # Número máximo de iterações para a busca local
    iteracao = 0
    
    start_time = time.time()
    time_limit_seconds = 60 # Limite de tempo para a busca local (ex: 60 segundos)

    while iteracao < iteracoes_max and (time.time() - start_time) < time_limit_seconds:
        iteracao += 1
        
        melhor_solucao_nesta_iteracao = None
        melhor_delta_nesta_iteracao = 0.0 # Procuramos o maior delta_custo (> 0)
        
        # Testar movimentos na vizinhança
        tipos_de_movimento = ['troca_intra_periodo', 'realocar_producao']
        
        # Para Best Improvement, precisamos explorar um número significativo de vizinhos
        # ou todos eles, se o tamanho da vizinhança for controlável.
        # Aqui, vamos tentar 'num_vizinhos_a_explorar_por_tipo' vizinhos aleatórios para cada tipo de movimento.
        num_vizinhos_a_explorar_por_tipo = 500 # Um número maior para explorar mais a vizinhança

        # Explorar vizinhos para 'troca_intra_periodo'
        for _ in range(num_vizinhos_a_explorar_por_tipo):
            # Selecionar um período aleatório para a troca
            periodos_com_producao = [t for t in range(parametros["num_periodos"]) if melhor_solucao_global['sequencias_producao'][t]]
            if not periodos_com_producao: continue 
            periodo_aleatorio = random.choice(periodos_com_producao)
            #print(f"Explorando vizinhos para troca intra-período no período {periodo_aleatorio}")
            
            num_itens_para_trocar = 2 
            if len(melhor_solucao_global['sequencias_producao'][periodo_aleatorio]) < num_itens_para_trocar:
                continue 
            
            nova_solucao_candidata, delta_custo = realizar_movimento(
                melhor_solucao_global, 
                parametros, 
                'troca_intra_periodo', 
                periodo=periodo_aleatorio, 
                num_itens_a_trocar=num_itens_para_trocar
            )
            
            if nova_solucao_candidata and delta_custo > melhor_delta_nesta_iteracao:
                melhor_solucao_nesta_iteracao = nova_solucao_candidata
                melhor_delta_nesta_iteracao = delta_custo

        # Explorar vizinhos para 'realocar_producao'
        for _ in range(num_vizinhos_a_explorar_por_tipo):
            # Selecionar um item e período de origem aleatoriamente
            itens_com_producao = []
            for j in range(parametros['num_itens']):
                for t in range(parametros['num_periodos']):
                    if melhor_solucao_global['x'][j][t] > 0:
                        itens_com_producao.append((j, t))
            
            if not itens_com_producao: continue 
            
            item_id_aleatorio, periodo_origem_aleatorio = random.choice(itens_com_producao)
            
            quantidade_a_mover = random.randint(1, melhor_solucao_global['x'][item_id_aleatorio][periodo_origem_aleatorio])
            
            nova_solucao_candidata, delta_custo = realizar_movimento(
                melhor_solucao_global, 
                parametros, 
                'realocar_producao', 
                item_id=item_id_aleatorio, 
                periodo_origem=periodo_origem_aleatorio, 
                quantidade_a_mover=quantidade_a_mover
            )

            if nova_solucao_candidata and delta_custo > melhor_delta_nesta_iteracao:
                melhor_solucao_nesta_iteracao = nova_solucao_candidata
                melhor_delta_nesta_iteracao = delta_cust
        
        # Fim da exploração da vizinhança para esta iteração
        if melhor_solucao_nesta_iteracao: # Se uma melhoria foi encontrada nesta iteração
            melhor_solucao_global = melhor_solucao_nesta_iteracao
            melhor_valor_fo_global += melhor_delta_nesta_iteracao
            print(f"Iteração {iteracao}: Melhoria encontrada. Novo FO: {melhor_valor_fo_global:.2f} (Delta: {melhor_delta_nesta_iteracao:.2f})")
        else: # Se nenhuma melhoria foi encontrada na vizinhança
            print(f"Iteração {iteracao}: Nenhuma melhoria encontrada. Parando busca local.")
            break # Sair do loop principal

    print("\n--- Busca Local Finalizada ---")
    print(f"Melhor Valor da Função Objetivo Encontrado: {melhor_valor_fo_global:.2f}")
    print(f"Valor da FO Inicial: {valor_fo_inicial:.2f}")
    print(f"Total de iterações: {iteracao}")
    print(f"Tempo de execução da busca local: {time.time() - start_time:.2f} segundos")