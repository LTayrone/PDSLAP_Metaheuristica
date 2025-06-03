import random
from copy import deepcopy
import math
import numpy as np

# Importar a função de cálculo de custo
from .calcular_custo_total import calcular_custo_total

# Importar a função auxiliar para obter sequência de produção
# Esta é a mesma lógica usada em gerar_solucao_inicial_hc1_atualizada
from .gerar_solucao_inicial_hc1_atualizada import obter_sequencia_producao

def recalcular_variaveis_dependentes(solucao_parcial, parametros_problema):
    """
    Recalcula as variáveis de decisão dependentes (I, Q, y, z) e as sequências de produção
    com base nas variáveis x (produção) e gamma (pedidos atendidos) fornecidas.
    Esta função espelha a lógica de reconstrução da heurística construtiva.

    Args:
        solucao_parcial (dict): Um dicionário de solução contendo pelo menos 'x' e 'gamma'.
        parametros_problema (dict): Dicionário com todos os parâmetros do problema.

    Returns:
        dict: A solução completa com todas as variáveis recalculadas (x, I, Q, gamma, y, z, sequencias_producao).
              Retorna None se a reconstrução resultar em infactibilidade (ex: capacidade excedida).
    """
    num_itens = parametros_problema["num_itens"]
    num_periodos = parametros_problema["num_periodos"]
    num_pedidos = parametros_problema["num_pedidos"]
    capacidade_periodo_original = parametros_problema["capacidade_periodo"].copy()
    tempo_producao = parametros_problema["tempo_producao"]
    tempo_setup = parametros_problema["tempo_setup"]
    vida_util = parametros_problema["vida_util"]
    demanda_pedidos = parametros_problema["demanda_pedidos"]

    # Copiar as variáveis de entrada que não serão reconstruídas diretamente, mas são necessárias
    producao = solucao_parcial["x"]
    pedido_atendido = solucao_parcial["gamma"]

    # Inicializar variáveis que serão recalculadas
    estoque = {j: {t: {k: 0 for k in range(max(vida_util) + 1)} for t in range(num_periodos)} for j in range(num_itens)}
    quantidade_atendida_por_pedido = {j: {n: {t: {k: 0 for k in range(max(vida_util) + 1)} for t in range(num_periodos)} for n in range(num_pedidos)} for j in range(num_itens)}
    maquina_preparada = {j: {t: 0 for t in range(num_periodos)} for j in range(num_itens)}
    troca_producao = {i: {j: {t: 0 for t in range(num_periodos)} for j in range(num_itens)} for i in range(num_itens)}
    sequencias_por_periodo = {t: [] for t in range(num_periodos)}
    
    # Rastreia o último item produzido no período anterior para cálculo de setup
    ultimo_item_produzido_no_periodo_anterior = {t: None for t in range(num_periodos)}

    # Reconstruir `maquina_preparada`, `troca_producao`, `capacidade_restante_por_periodo`, `ultimo_item_produzido_no_periodo`
    # E calcular sequências de produção
    for t_reconstrucao in range(num_periodos):
        itens_a_produzir_no_periodo_reconstrucao = []
        for j_reconstrucao in range(num_itens):
            if producao[j_reconstrucao][t_reconstrucao] > 0:
                itens_a_produzir_no_periodo_reconstrucao.append(j_reconstrucao)
        
        # Obter o último item produzido no período ANTERIOR, para o setup inicial do período atual
        item_anterior_para_seq_reconstrucao = None
        if t_reconstrucao > 0:
            # Encontrar o último item produzido no período anterior
            # Isso requer uma lógica para determinar qual foi o *último* item produzido.
            # Se a solucao_parcial ainda não tem sequencias_producao, precisamos de uma forma de saber.
            # Vamos usar a info de y[j][t-1] que indica o item que iniciou a produção, mas não o último
            # Melhor seria passar o ultimo_item_produzido_no_periodo como parte do estado/solução.
            # Por enquanto, vamos assumir que obtemos o ultimo item produzido no periodo anterior
            # de uma forma genérica ou que a função obter_sequencia_producao lida com 'None'.
            # A heurística inicial usa `ultimo_item_produzido_no_periodo[t_reconstrucao - 1]`.
            # Então, vamos precisar manter esse estado ou reconstruí-lo.

            # Para simplificar e refatorar, vamos assumir que `ultimo_item_produzido_no_periodo_anterior`
            # é preenchido de forma iterativa ao longo do loop de períodos.
            item_anterior_para_seq_reconstrucao = ultimo_item_produzido_no_periodo_anterior.get(t_reconstrucao - 1, None)
        
        # Usa a mesma lógica de sequenciamento da heurística construtiva
        seq_real_periodo_reconstrucao, tempo_setup_real_periodo_reconstrucao = \
            obter_sequencia_producao(itens_a_produzir_no_periodo_reconstrucao, tempo_setup, item_anterior_para_seq_reconstrucao)

        sequencias_por_periodo[t_reconstrucao] = seq_real_periodo_reconstrucao

        tempo_total_producao_real_periodo_reconstrucao = sum(tempo_producao[j_prod_na_seq] * producao[j_prod_na_seq][t_reconstrucao] for j_prod_na_seq in seq_real_periodo_reconstrucao)
        tempo_total_gasto_no_periodo_reconstrucao = tempo_total_producao_real_periodo_reconstrucao + tempo_setup_real_periodo_reconstrucao

        if tempo_total_gasto_no_periodo_reconstrucao > capacidade_periodo_original[t_reconstrucao]:
            # Se a capacidade for excedida, esta solução é infactível
            #print(f"DEBUG: Capacidade excedida no período {t_reconstrucao} durante recalculo. Total gasto: {tempo_total_gasto_no_periodo_reconstrucao}, Capacidade: {capacidade_periodo_original[t_reconstrucao]}")
            return None # Retorna None para indicar infactibilidade

        # Atualizar y e z
        if seq_real_periodo_reconstrucao:
            maquina_preparada[seq_real_periodo_reconstrucao[0]][t_reconstrucao] = 1
            if item_anterior_para_seq_reconstrucao is not None and item_anterior_para_seq_reconstrucao != seq_real_periodo_reconstrucao[0]:
                troca_producao[item_anterior_para_seq_reconstrucao][seq_real_periodo_reconstrucao[0]][t_reconstrucao] = 1

            for idx_seq in range(len(seq_real_periodo_reconstrucao) - 1):
                item_origem = seq_real_periodo_reconstrucao[idx_seq]
                item_destino = seq_real_periodo_reconstrucao[idx_seq + 1]
                if item_origem != item_destino: # Evita setup de item para ele mesmo
                    troca_producao[item_origem][item_destino][t_reconstrucao] = 1
            ultimo_item_produzido_no_periodo_anterior[t_reconstrucao] = seq_real_periodo_reconstrucao[-1]
        else:
            ultimo_item_produzido_no_periodo_anterior[t_reconstrucao] = None # Nenhum item produzido, nenhum último item

    # Reconstruir as variáveis de estoque I[j][t][k] e Q[j][n][t][k]
    # Este é um passo complexo que simula o fluxo de estoque e atendimento de pedidos
    # É fundamental que reflita as restrições (2) a (6) do modelo.
    # Vamos usar uma lógica similar à HC1-atualizada para garantir a consistência
    
    # Estoque detalhado para FIFO (para simular corretamente o I e Q)
    lotes_em_estoque_simulacao = {j: [] for j in range(num_itens)} # [(periodo_producao, quantidade_atual, periodo_vencimento), ...]

    for t_reconstrucao in range(num_periodos):
        # 1. Adicionar produção do período atual como lotes de idade 0
        for j_reconstrucao in range(num_itens):
            if producao[j_reconstrucao][t_reconstrucao] > 0:
                lotes_em_estoque_simulacao[j_reconstrucao].append((t_reconstrucao, producao[j_reconstrucao][t_reconstrucao], t_reconstrucao + vida_util[j_reconstrucao]))

        # 2. Atender pedidos no período t_reconstrucao
        for n_reconstrucao in range(num_pedidos):
            # Apenas se o pedido n_reconstrucao foi aceito para entrega neste período t_reconstrucao
            if pedido_atendido[n_reconstrucao][t_reconstrucao] == 1:
                for j_item in range(num_itens):
                    demanda_item_para_pedido = demanda_pedidos[n_reconstrucao][j_item]
                    if demanda_item_para_pedido == 0:
                        continue

                    quantidade_restante_para_atender = demanda_item_para_pedido
                    
                    # Ordena lotes por período de produção para garantir FIFO
                    lotes_em_estoque_simulacao[j_item].sort(key=lambda x: x[0])
                    
                    novos_lotes_em_estoque_j = []
                    
                    for periodo_producao_lote, quantidade_lote_em_estoque, vencimento_lote in lotes_em_estoque_simulacao[j_item]:
                        if quantidade_restante_para_atender <= 0:
                            novos_lotes_em_estoque_j.append((periodo_producao_lote, quantidade_lote_em_estoque, vencimento_lote))
                            continue

                        idade_no_momento_entrega = t_reconstrucao - periodo_producao_lote
                        
                        # Verifica validade do lote para a entrega
                        if idade_no_momento_entrega >= 0 and idade_no_momento_entrega <= vida_util[j_item]:
                            quantidade_a_usar_do_estoque = min(quantidade_restante_para_atender, quantidade_lote_em_estoque)
                            
                            quantidade_atendida_por_pedido[j_item][n_reconstrucao][t_reconstrucao][idade_no_momento_entrega] += quantidade_a_usar_do_estoque
                            quantidade_restante_para_atender -= quantidade_a_usar_do_estoque
                            
                            quantidade_restante_no_lote = quantidade_lote_em_estoque - quantidade_a_usar_do_estoque
                            if quantidade_restante_no_lote > 0:
                                novos_lotes_em_estoque_j.append((periodo_producao_lote, quantidade_restante_no_lote, vencimento_lote))
                        else:
                            # Lote vencido ou não utilizável para esta entrega (idade inválida)
                            novos_lotes_em_estoque_j.append((periodo_producao_lote, quantidade_lote_em_estoque, vencimento_lote))
                    
                    lotes_em_estoque_simulacao[j_item] = novos_lotes_em_estoque_j
                    
                    # Se após consumir todo o estoque, ainda houver demanda não atendida, a solução é infactível
                    if quantidade_restante_para_atender > 0:
                        #print(f"DEBUG: Pedido {n_reconstrucao} não pode ser totalmente atendido no período {t_reconstrucao} para item {j_item}. Faltou: {quantidade_restante_para_atender}")
                        return None # Retorna None se o pedido não pode ser atendido

        # 3. Atualizar I (estoque) no final do período t_reconstrucao
        for j_reconstrucao in range(num_itens):
            # Limpar o estoque I para este período antes de preencher
            for k in range(max(vida_util) + 1):
                estoque[j_reconstrucao][t_reconstrucao][k] = 0

            # Preencher I[j][t][k] com base nos lotes remanescentes
            for periodo_producao_lote, quantidade_lote_em_estoque, vencimento_lote in lotes_em_estoque_simulacao[j_reconstrucao]:
                if t_reconstrucao <= vencimento_lote: # Apenas lotes válidos no final do período
                    k_idade = t_reconstrucao - periodo_producao_lote
                    if k_idade >= 0 and k_idade <= vida_util[j_reconstrucao]:
                        estoque[j_reconstrucao][t_reconstrucao][k_idade] += quantidade_lote_em_estoque
                    # else: lote com idade calculada fora da faixa (possível erro lógico ou vencido mas não filtrado)

    # Verifica Restrição (6): I_jt^sl_j = 0 para garantir que não há estoque vencido no final do período
    for j in range(num_itens):
        for t in range(num_periodos):
            if estoque[j][t][vida_util[j]] > 0:
                # Se há estoque com idade máxima e não deveria haver, é infactível
                #print(f"DEBUG: Estoque de item {j} com idade {vida_util[j]} > 0 no período {t}. Infactível.")
                return None


    return {
        "x": producao,
        "I": estoque,
        "Q": quantidade_atendida_por_pedido,
        "gamma": pedido_atendido,
        "y": maquina_preparada,
        "z": troca_producao,
        "sequencias_producao": sequencias_por_periodo
    }

def validar_todas_restricoes(solucao, parametros_problema):
    """
    Verifica se a solução completa (todas as variáveis recalculadas) satisfaz todas
    as restrições do modelo matemático (1)-(17) do Barbosa et al. (2019).
    Esta é uma verificação de "linha dura" da factibilidade.
    
    Args:
        solucao (dict): Dicionário contendo todas as variáveis de decisão x, I, Q, gamma, y, z, sequencias_producao.
        parametros_problema (dict): Dicionário com os parâmetros do problema.
        
    Returns:
        bool: True se a solução é factível, False caso contrário.
    """
    x = solucao["x"]
    I = solucao["I"]
    Q = solucao["Q"]
    gamma = solucao["gamma"]
    y = solucao["y"]
    z = solucao["z"]
    sequencias_producao = solucao["sequencias_producao"]

    num_itens = parametros_problema["num_itens"]
    num_periodos = parametros_problema["num_periodos"]
    num_pedidos = parametros_problema["num_pedidos"]
    tempo_producao = parametros_problema["tempo_producao"]
    tempo_setup = parametros_problema["tempo_setup"]
    capacidade_periodo = parametros_problema["capacidade_periodo"]
    vida_util = parametros_problema["vida_util"]
    demanda_pedidos = parametros_problema["demanda_pedidos"]
    periodo_inicial_entrega = parametros_problema["periodo_inicial_entrega"]
    periodo_final_entrega = parametros_problema["periodo_final_entrega"]

    # Rastrear o último item produzido no período anterior para validar 'y' e 'z'
    # Esta é a mesma lógica usada na reconstrução, mas agora para VALIDAÇÃO.
    ultimo_item_produzido_no_periodo_anterior_validacao = {t: None for t in range(num_periodos)}


    # --- Restrições de Balanço de Estoque e Demanda (2), (3), (4), (5), (6) ---
    # Re-simular o estoque para verificar a consistência
    lotes_em_estoque_validacao = {j: [] for j in range(num_itens)}

    for t in range(num_periodos):
        # Adicionar produção ao estoque (idade 0)
        for j in range(num_itens):
            if x[j][t] < 0: return False # Produção não pode ser negativa
            if x[j][t] > 0:
                lotes_em_estoque_validacao[j].append((t, x[j][t], t + vida_util[j]))

        # Atender demanda de pedidos
        for n in range(num_pedidos):
            if gamma[n][t] == 1: # Se o pedido n é atendido no período t
                for j in range(num_itens):
                    demanda_requerida_do_item = demanda_pedidos[n][j]

                    # Verifica se a quantidade total atendida (Q) é igual à demanda do pedido
                    total_Q_para_item_pedido = sum(Q[j][n][t][k] for k in range(max(vida_util) + 1))
                    if total_Q_para_item_pedido != demanda_requerida_do_item:
                        #print(f"DEBUG: Restrição (5) violada para pedido {n}, item {j}, período {t}. Q total ({total_Q_para_item_pedido}) != demanda ({demanda_requerida_do_item}).")
                        return False

                    # Consumir do estoque de validação (simulação FIFO)
                    # Primeiro, verificar se Q[j][n][t][k] realmente pode ser satisfeito pelo estoque_validacao
                    # e se as idades estão corretas.
                    
                    quantidade_consumida_validacao = {k: 0 for k in range(max(vida_util) + 1)}
                    
                    # Consumir dos lotes em estoque (FIFO)
                    lotes_em_estoque_validacao[j].sort(key=lambda item: item[0]) # Garante FIFO
                    
                    temp_lotes_para_proximo_passo = []
                    
                    for prod_t_lote, qty_lote, venc_t_lote in lotes_em_estoque_validacao[j]:
                        idade_do_lote_no_t = t - prod_t_lote
                        if idade_do_lote_no_t < 0 or idade_do_lote_no_t > vida_util[j] or t > venc_t_lote:
                            # Lote não é válido para consumo neste período (idade inválida ou vencido)
                            temp_lotes_para_proximo_passo.append((prod_t_lote, qty_lote, venc_t_lote))
                            continue # Passa para o próximo lote

                        # Tenta usar este lote para atender a demanda de Q[j][n][t][idade_do_lote_no_t]
                        qty_from_Q = Q[j][n][t][idade_do_lote_no_t]
                        if qty_from_Q > 0:
                            qty_to_use_from_lote = min(qty_lote, qty_from_Q)
                            
                            quantidade_consumida_validacao[idade_do_lote_no_t] += qty_to_use_from_lote
                            qty_lote -= qty_to_use_from_lote
                            
                            # Se ainda há Q para esta idade, o lote não foi suficiente. Infactível.
                            if qty_to_use_from_lote < qty_from_Q:
                                #print(f"DEBUG: Restrição (5) ou balanço de estoque (2) violada para item {j}, pedido {n}, período {t}, idade {idade_do_lote_no_t}. Q exige {qty_from_Q}, mas lote só forneceu {qty_to_use_from_lote}.")
                                return False # Não havia estoque suficiente para atender Q

                        if qty_lote > 0:
                            temp_lotes_para_proximo_passo.append((prod_t_lote, qty_lote, venc_t_lote))
                    
                    lotes_em_estoque_validacao[j] = temp_lotes_para_proximo_passo

                    # Validar se o estoque total (I) no final do período 't' corresponde ao 'lotes_em_estoque_validacao'
                    # e se não há estoque vencido.
                    
        # Verificar o estoque I no final do período t
        for j in range(num_itens):
            for k_val in range(max(vida_util) + 1):
                estoque_esperado_em_I = I[j][t][k_val]
                estoque_real_validacao = 0
                for prod_t_lote, qty_lote, venc_t_lote in lotes_em_estoque_validacao[j]:
                    if (t - prod_t_lote) == k_val and t <= venc_t_lote: # Lote válido com a idade k no final de t
                        estoque_real_validacao += qty_lote
                if estoque_esperado_em_I != estoque_real_validacao:
                    #print(f"DEBUG: Restrição (2) ou (3) ou (4) violada para item {j}, período {t}, idade {k_val}. I[{j}][{t}][{k_val}] = {estoque_esperado_em_I}, mas estoque real = {estoque_real_validacao}.")
                    return False
            
            # Restrição (6): I_jt^sl_j = 0
            # Já é verificado dentro de recalcular_variaveis_dependentes. Mas para completa validação:
            if I[j][t][vida_util[j]] > 0:
                #print(f"DEBUG: Restrição (6) violada para item {j}, período {t}. Estoque com idade máxima > 0.")
                return False


    # --- Restrição de Capacidade Produtiva (7) ---
    for t in range(num_periodos):
        tempo_total_producao = 0
        for j in range(num_itens):
            tempo_total_producao += tempo_producao[j] * x[j][t]
        
        tempo_total_setup = 0
        
        # Validar y e z junto com o cálculo do setup
        itens_produzidos_no_periodo = [j for j in range(num_itens) if x[j][t] > 0]
        
        # Obter a sequência "real" para o período para calcular setups corretamente
        # Se a sequencia_producao no solucao não for a "real" ou se foi gerada de forma errada,
        # isso pode levar a inconsistências.
        
        # A sequência_producao já é gerada em recalcular_variaveis_dependentes.
        # Precisamos usar a sequência *que está na solução* para validar o setup.
        
        seq_validacao_periodo = sequencias_producao[t]
        
        # Validação do y e z
        if seq_validacao_periodo:
            # R8: sum_{j} y_{jt} = 1 se houver produção
            if sum(y[j][t] for j in range(num_itens)) != 1:
                #print(f"DEBUG: Restrição (8) violada para período {t}. sum(y_jt) != 1. y[j][t] = { {j:y[j][t] for j in range(num_itens) if y[j][t] == 1} }")
                return False

            # Validação do primeiro item da sequência
            first_item = seq_validacao_periodo[0]
            if y[first_item][t] != 1:
                #print(f"DEBUG: Restrição (11) ou (8) violada. Primeiro item da sequência {first_item} em {t} não tem y=1.")
                return False
            
            prev_item_for_setup = ultimo_item_produzido_no_periodo_anterior_validacao.get(t-1) if t > 0 else None
            
            if prev_item_for_setup is not None and prev_item_for_setup != first_item:
                if z[prev_item_for_setup][first_item][t] != 1:
                    #print(f"DEBUG: Restrição (9) ou (11) violada. Setup de {prev_item_for_setup} para {first_item} em {t} não marcado com z=1.")
                    return False
                tempo_total_setup += tempo_setup[prev_item_for_setup][first_item]
                
            for idx in range(len(seq_validacao_periodo) - 1):
                item_origem = seq_validacao_periodo[idx]
                item_destino = seq_validacao_periodo[idx+1]
                if item_origem != item_destino:
                    if z[item_origem][item_destino][t] != 1:
                        #print(f"DEBUG: Restrição (9) ou (11) violada. Setup de {item_origem} para {item_destino} em {t} não marcado com z=1.")
                        return False
                    tempo_total_setup += tempo_setup[item_origem][item_destino]
                elif z[item_origem][item_destino][t] != 0: # Não deveria haver setup se item é o mesmo
                    #print(f"DEBUG: Restrição (9) ou (11) violada. Setup indevido de {item_origem} para {item_destino} em {t} (mesmo item).")
                    return False
            ultimo_item_produzido_no_periodo_anterior_validacao[t] = seq_validacao_periodo[-1]
        else: # Nenhum item produzido no período
            if sum(y[j][t] for j in range(num_itens)) != 0:
                #print(f"DEBUG: Restrição (8) violada para período {t}. sum(y_jt) != 0 quando não há produção.")
                return False
            # Não há setups se não há produção
            for i in range(num_itens):
                for j in range(num_itens):
                    if z[i][j][t] != 0:
                        #print(f"DEBUG: Restrição (9) violada para período {t}. Setup z[{i}][{j}][{t}] != 0 quando não há produção.")
                        return False
            ultimo_item_produzido_no_periodo_anterior_validacao[t] = None


        if (tempo_total_producao + tempo_total_setup) > capacidade_periodo[t]:
            #print(f"DEBUG: Restrição (7) de capacidade violada para período {t}. Tempo gasto: {tempo_total_producao + tempo_total_setup}, Capacidade: {capacidade_periodo[t]}.")
            return False

    # --- Restrições de Atendimento de Pedidos (12), (13) ---
    for n in range(num_pedidos):
        # Restrição (12): sum_{t=F_n}^{L_n} gamma_nt <= 1
        sum_gamma_n = sum(gamma[n][t] for t in range(num_periodos))
        if sum_gamma_n > 1:
            #print(f"DEBUG: Restrição (12) violada para pedido {n}. Atendido mais de uma vez.")
            return False

        # Se o pedido foi atendido, verificar se foi dentro da janela de tempo
        if sum_gamma_n == 1:
            atendido_em_t = -1
            for t in range(num_periodos):
                if gamma[n][t] == 1:
                    atendido_em_t = t
                    break
            
            # Restrição (13): gamma_nt = 0 para t < F_n ou t > L_n
            if not (periodo_inicial_entrega[n] <= atendido_em_t <= periodo_final_entrega[n]):
                #print(f"DEBUG: Restrição (13) violada para pedido {n}. Atendido em {atendido_em_t}, mas janela é [{periodo_inicial_entrega[n]}, {periodo_final_entrega[n]}].")
                return False

    # --- Restrições de Domínio (14), (15), (16), (17) ---
    for n in range(num_pedidos):
        for t in range(num_periodos):
            if gamma[n][t] not in [0, 1]: return False
    for j in range(num_itens):
        for t in range(num_periodos):
            if y[j][t] not in [0, 1]: return False
            if x[j][t] < 0: return False # xa_jt >=0, deve ser inteiro
            for k in range(max(vida_util) + 1):
                if I[j][t][k] < 0: return False # I_jt^k >=0
            for i in range(num_itens):
                if z[i][j][t] not in [0, 1]: return False
    for j in range(num_itens):
        for n in range(num_pedidos):
            for t in range(num_periodos):
                for k in range(max(vida_util) + 1):
                    if Q[j][n][t][k] < 0: return False # Q_jnt^k >=0
    # V_jt não é verificada aqui, pois é uma variável auxiliar do solver para a ordem.

    return True # Se todas as verificações passarem, a solução é factível

def realizar_movimento(solucao_atual, parametros_problema, tipo_movimento, **kwargs):
    """
    Função principal para coordenar a aplicação de movimentos de vizinhança.

    Args:
        solucao_atual (dict): Dicionário representando a solução atual.
        parametros_problema (dict): Dicionário com os parâmetros do problema.
        tipo_movimento (str): O nome do movimento a ser aplicado ('troca_intra_periodo', 'realocar_producao').
        **kwargs: Argumentos específicos para o tipo de movimento.

    Returns:
        tuple: (nova_solucao, delta_custo) ou (None, None) se o movimento não gerar uma solução factível.
    """
    
    # Certifique-se de que a solução inicial tem a chave 'sequencias_producao'
    if "sequencias_producao" not in solucao_atual:
        # Tenta reconstruir se faltar. Isso é importante para a primeira chamada.
        # Mas idealmente a solução_atual já deve vir completa.
        solucao_atual = recalcular_variaveis_dependentes(solucao_atual, parametros_problema)
        if solucao_atual is None:
            #print("ERRO: Solução inicial não pôde ser validada/recalculada antes de movimentos.")
            return None, None # Se a solução inicial já é infactível

    if not validar_todas_restricoes(solucao_atual, parametros_problema):
        #print("AVISO: A solução atual fornecida para 'realizar_movimento' é infactível.")
        # Retorna None, None para evitar tentar otimizar a partir de uma solução inválida.
        return None, None

    custo_original = calcular_custo_total(solucao_atual, parametros_problema)
    
    nova_solucao_tentativa = deepcopy(solucao_atual) # Cria uma cópia profunda para modificação

    movimento_valido_aplicado = False

    if tipo_movimento == 'troca_intra_periodo':
        # Requer: periodo (int), num_itens_a_trocar (int)
        periodo = kwargs.get('periodo', -1)
        num_itens_a_trocar = kwargs.get('num_itens_a_trocar', 2)

        if periodo == -1: # Se não for passado um período, escolhe um aleatoriamente que tenha produção
            periodos_com_producao = [t for t in range(parametros_problema["num_periodos"]) if nova_solucao_tentativa['sequencias_producao'][t]]
            if not periodos_com_producao:
                return None, None # Não há períodos com produção para trocar
            periodo = random.choice(periodos_com_producao)
        
        seq_periodo_atual = nova_solucao_tentativa['sequencias_producao'][periodo]
        
        if len(seq_periodo_atual) < num_itens_a_trocar:
            return None, None # Não há itens suficientes para trocar neste período
        
        # Realiza a troca na sequência
        indices_a_trocar = random.sample(range(len(seq_periodo_atual)), num_itens_a_trocar)
        
        if num_itens_a_trocar == 2:
            idx1, idx2 = indices_a_trocar
            seq_periodo_atual[idx1], seq_periodo_atual[idx2] = seq_periodo_atual[idx2], seq_periodo_atual[idx1]
        else:
            # Para N > 2, pode-se implementar uma permutação mais complexa
            # Ex: embaralhar os itens nas posições selecionadas
            elementos_selecionados = [seq_periodo_atual[i] for i in indices_a_trocar]
            random.shuffle(elementos_selecionados)
            for i, idx in enumerate(indices_a_trocar):
                seq_periodo_atual[idx] = elementos_selecionados[i]
        
        # Atualiza a sequência no dicionário da solução tentativa
        nova_solucao_tentativa['sequencias_producao'][periodo] = seq_periodo_atual
        movimento_valido_aplicado = True # O movimento foi aplicado ao x/sequenciamento
        
    elif tipo_movimento == 'realocar_producao':
        # Requer: item_id (int), periodo_origem (int), quantidade_a_mover (int)
        item_id = kwargs.get('item_id', -1)
        periodo_origem = kwargs.get('periodo_origem', -1)
        quantidade_a_mover = kwargs.get('quantidade_a_mover', 0)

        if item_id == -1 or periodo_origem == -1 or quantidade_a_mover <= 0:
            # Escolher aleatoriamente um item e período de origem com produção
            itens_com_producao = []
            for j in range(parametros_problema['num_itens']):
                for t in range(parametros_problema['num_periodos']):
                    if nova_solucao_tentativa['x'][j][t] > 0:
                        itens_com_producao.append((j, t))
            
            if not itens_com_producao:
                return None, None # Não há produção para realocar
            
            item_id, periodo_origem = random.choice(itens_com_producao)
            quantidade_a_mover = random.randint(1, nova_solucao_tentativa['x'][item_id][periodo_origem])
            if quantidade_a_mover == 0: return None, None # Não há o que mover

        max_periodos = parametros_problema['num_periodos']
        
        # Decide se move para o período anterior ou posterior
        periodo_destino = -1
        if periodo_origem == 0: # Se no primeiro período, só pode mover para frente
            periodo_destino = 1
        elif periodo_origem == max_periodos - 1: # Se no último período, só pode mover para trás
            periodo_destino = max_periodos - 2
        else: # Senão, pode ser para frente ou para trás
            periodo_destino = random.choice([periodo_origem - 1, periodo_origem + 1])
        
        # Verificar se os períodos destino e origem são válidos
        if not (0 <= periodo_destino < max_periodos and 0 <= periodo_origem < max_periodos):
            return None, None # Período inválido
            
        if nova_solucao_tentativa['x'][item_id][periodo_origem] < quantidade_a_mover:
            return None, None # Não há produção suficiente para mover

        # Aplica o movimento na produção (x)
        nova_solucao_tentativa['x'][item_id][periodo_origem] -= quantidade_a_mover
        nova_solucao_tentativa['x'][item_id][periodo_destino] += quantidade_a_mover
        movimento_valido_aplicado = True

    # Se nenhum movimento foi aplicado, ou tipo de movimento inválido, retorna None
    if not movimento_valido_aplicado:
        return None, None

    # Recalcular todas as variáveis dependentes e validar a nova solução
    nova_solucao_completa = recalcular_variaveis_dependentes(nova_solucao_tentativa, parametros_problema)
    
    if nova_solucao_completa is None:
        return None, None # O movimento gerou uma solução infactível

    # Validar todas as restrições novamente para garantir a factibilidade
    if not validar_todas_restricoes(nova_solucao_completa, parametros_problema):
        # Isso não deveria acontecer se recalcular_variaveis_dependetes já validou a capacidade
        # e o atendimento de pedidos, mas é uma camada extra de segurança.
        #print("AVISO: Solução considerada factível por recalcular_variaveis_dependentes, mas falhou na validação completa.")
        return None, None

    custo_novo = calcular_custo_total(nova_solucao_completa, parametros_problema)
    delta_custo = custo_novo - custo_original

    return nova_solucao_completa, delta_custo