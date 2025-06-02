import math
import numpy as np

def gerar_solucao_inicial_hc1(parametros):
    """
    Gera uma solução inicial heurística para o problema de produção com shelf-life,
    implementando a Heurística Construtiva 1 (HC1) que prioriza pedidos com maior receita.
    A lógica agora é: decidir pedidos -> produzir -> sequenciar.

    Args:
        parametros (dict): Dicionário com os parâmetros do problema.

    Returns:
        dict: Dicionário contendo as variáveis de decisão x, I, Q, gamma, y, z.
    """
    # Extrair parâmetros
    num_pedidos = parametros["num_pedidos"]
    num_periodos = parametros["num_periodos"]
    num_itens = parametros["num_itens"]
    demanda_pedidos = parametros["demanda_pedidos"]
    capacidade_periodo = parametros["capacidade_periodo"].copy() # Copia para poder modificar
    tempo_producao = parametros["tempo_producao"]
    tempo_setup = parametros["tempo_setup"]
    periodo_inicial_entrega = parametros["periodo_inicial_entrega"]
    periodo_final_entrega = parametros["periodo_final_entrega"]
    receita_pedido = parametros["receita_pedido"]
    vida_util = parametros["vida_util"]

    # Inicializa as variáveis de decisão
    x = {j: {t: 0 for t in range(num_periodos)} for j in range(num_itens)}
    I = {j: {t: {k: 0 for k in range(max(vida_util) + 1)} for t in range(num_periodos)} for j in range(num_itens)}
    Q = {j: {n: {t: {k: 0 for k in range(max(vida_util) + 1)} for t in range(num_periodos)} for n in range(num_pedidos)} for j in range(num_itens)}
    gamma = {n: {t: 0 for t in range(num_periodos)} for n in range(num_pedidos)}
    y = {j: {t: 0 for t in range(num_periodos)} for j in range(num_itens)}
    z = {i: {j: {t: 0 for t in range(num_periodos)} for j in range(num_itens)} for i in range(num_itens)}

    # Variáveis auxiliares para a heurística
    estoque_fifo = {j: [] for j in range(num_itens)} # [(periodo_producao, quantidade_atual, periodo_vencimento), ...]
    # last_item_produced_per_period rastreia o último item produzido em CADA período
    last_item_produced_per_period = {t: None for t in range(num_periodos)}

    # --- ETAPA 1: Priorizar pedidos por receita ---
    # Calcula a receita total de cada pedido (usando o primeiro período de entrega como base)
    receita_total_por_pedido = {n: receita_pedido[n][periodo_inicial_entrega[n]] for n in range(num_pedidos)}

    # Ordena pedidos em ordem decrescente de receita
    pedidos_ordenados_por_prioridade = sorted(
        range(num_pedidos),
        key=lambda n: receita_total_por_pedido[n],
        reverse=True
    )

    # --- ETAPA 2: Tentar aceitar cada pedido e planejar produção/entrega ---
    for n in pedidos_ordenados_por_prioridade:
        # Tenta encontrar o melhor período de entrega para o pedido n
        best_delivery_period = -1
        best_production_plan = None # (producoes_necessarias_por_item_periodo, temp_estoque_fifo, temp_capacidade_restante)
        
        # Iterar sobre os períodos dentro da janela de entrega do pedido (F_n a L_n)
        # para encontrar o período que pode atender o pedido. Prioriza os períodos mais cedo
        # na janela para tentar liberar capacidade para pedidos futuros, mas isso pode ser ajustado.
        for t_entrega in range(periodo_inicial_entrega[n], periodo_final_entrega[n] + 1):
            if t_entrega >= num_periodos: # Garante que t_entrega está dentro do horizonte
                continue

            # Simulações para verificar se o pedido pode ser atendido
            temp_x = {j: {t: x[j][t] for t in range(num_periodos)} for j in range(num_itens)}
            temp_I = {j: {t: {k: I[j][t][k] for k in range(max(vida_util) + 1)} for t in range(num_periodos)} for j in range(num_itens)}
            temp_Q = {j: {n_q: {t_q: {k_q: Q[j][n_q][t_q][k_q] for k_q in range(max(vida_util) + 1)} for t_q in range(num_periodos)} for n_q in range(num_pedidos)} for j in range(num_itens)}
            temp_gamma_n_t_entrega = 0 # Para este pedido n no t_entrega
            temp_y = {j: {t: y[j][t] for t in range(num_periodos)} for j in range(num_itens)}
            temp_z = {i: {j: {t: z[i][j][t] for t in range(num_periodos)} for j in range(num_itens)} for i in range(num_itens)}
            temp_capacidade_restante_periodo = capacidade_periodo.copy() # Cópia da capacidade atual
            
            # Copia o estado atual do estoque FIFO
            temp_estoque_fifo = {j: [(p_t, q, v_t) for p_t, q, v_t in estoque_fifo[j]] for j in range(num_itens)}

            can_attend_this_pedido_at_t_entrega = True
            itens_demandados_neste_pedido = {j: demanda_pedidos[n][j] for j in range(num_itens) if demanda_pedidos[n][j] > 0}
            
            production_needed_by_item = {j: 0 for j in range(num_itens)}

            # 1. Tentar atender com estoque existente
            for j, required_qty in itens_demandados_neste_pedido.items():
                qty_needed_for_item = required_qty
                # Simular consumo do estoque FIFO para este item
                for idx, (prod_t, qty_in_stk, valid_until_t) in enumerate(temp_estoque_fifo[j]):
                    if qty_needed_for_item <= 0:
                        break

                    # Verifica se o estoque é válido para t_entrega
                    if t_entrega - prod_t <= vida_util[j]: # idade é menor ou igual ao shelf-life
                        qty_to_take = min(qty_needed_for_item, qty_in_stk)
                        temp_estoque_fifo[j][idx] = (prod_t, qty_in_stk - qty_to_take, valid_until_t)
                        qty_needed_for_item -= qty_to_take
                
                # Se ainda precisar de mais, marca a necessidade de produção
                if qty_needed_for_item > 0:
                    production_needed_by_item[j] = qty_needed_for_item
            
            # 2. Planejar produção se necessário para o período t_entrega ou anterior
            # A produção para o pedido n deve ocorrer em um período p tal que:
            # p <= t_entrega
            # (t_entrega - p) <= vida_util[j]
            # E respeitar a capacidade de produção.
            
            # Primeiro, determina quais períodos de produção são válidos para atender o pedido no t_entrega
            # e ordena por prioridade (ex: mais cedo para itens perecíveis, ou mais tarde para estoque).
            # Vamos usar uma estratégia de "produção just-in-time" o mais tarde possível, mas garantindo shelf-life.
            # Para simplificar a heurística, vamos considerar que a produção ocorre no período t_entrega,
            # ou no período imediatamente anterior que permita o atendimento.

            # Lista de (item, quantidade_necessaria) para itens que precisam ser produzidos
            items_to_produce_current_pedido = [(j, qty) for j, qty in production_needed_by_item.items() if qty > 0]
            
            # Isso é uma simplificação. Em um cenário real de MILP, o solver decidiria o período de produção.
            # Para a heurística, vamos tentar produzir no período de entrega se houver capacidade, ou o mais próximo possível.
            # Se a demanda é para t_entrega, tentamos produzir em t_entrega.
            # Se for muito antes, isso pode complicar. Por enquanto, a produção é focada em t_entrega-idade.
            
            # Para cada item que precisa ser produzido, verifique a capacidade em t_entrega.
            # Esta parte da heurística é a mais complexa e crucial.
            # Precisa alocar produção e setups.

            # Simula a alocação de produção para os itens restantes que não foram atendidos pelo estoque
            simul_capacidade_restante_per_period = {p: capacidade_periodo[p] for p in range(num_periodos)}
            simul_last_item_produced_per_period = {p: last_item_produced_per_period[p] for p in range(num_periodos)}
            simul_x = {j: {t: x[j][t] for t in range(num_periodos)} for j in range(num_itens)}
            simul_y = {j: {t: y[j][t] for t in range(num_periodos)} for j in range(num_itens)}
            simul_z = {i: {j: {t: z[i][j][t] for t in range(num_periodos)} for j in range(num_itens)} for i in range(num_itens)}
            
            # Armazena as produções simuladas que seriam adicionadas
            simul_producoes_adicionais = {j: {t: 0 for t in range(num_periodos)} for j in range(num_itens)}

            # Itens a serem produzidos neste pedido, ordenados pela quantidade necessária (maior primeiro)
            items_to_produce_current_pedido.sort(key=lambda item: item[1], reverse=True)

            current_production_possible = True
            for j, required_qty_prod in items_to_produce_current_pedido:
                qty_to_produce = required_qty_prod
                # Encontra o período mais "tardio" de produção que ainda permita o atendimento
                # mas respeitando o shelf-life e a janela de entrega (até t_entrega)
                
                # Tentativa de produção no período t_entrega
                t_prod_candidate = t_entrega
                
                # Recalcula a capacidade disponível
                cap_disp = simul_capacidade_restante_per_period[t_prod_candidate]
                
                # Tempo de setup para este item neste período
                setup_time_cost = 0
                prev_item = simul_last_item_produced_per_period[t_prod_candidate-1] if t_prod_candidate > 0 else None
                
                # Se não tem produção simulada ainda para este período,
                # e o item é diferente do último produzido no período anterior,
                # então há um setup do período anterior para o atual.
                if prev_item is not None and prev_item != j:
                    setup_time_cost = tempo_setup[prev_item][j]
                
                # Verifica se há capacidade suficiente para produzir
                if (tempo_producao[j] > 0 and cap_disp >= (qty_to_produce * tempo_producao[j] + setup_time_cost)):
                    # Produz
                    simul_producoes_adicionais[j][t_prod_candidate] += qty_to_produce
                    simul_capacidade_restante_per_period[t_prod_candidate] -= (qty_to_produce * tempo_producao[j] + setup_time_cost)
                    simul_y[j][t_prod_candidate] = 1 # Máquina preparada
                    if prev_item is not None and prev_item != j:
                        simul_z[prev_item][j][t_prod_candidate] = 1 # Troca
                    simul_last_item_produced_per_period[t_prod_candidate] = j # Atualiza ultimo item produzido no periodo
                else: # Não foi possível produzir tudo necessário no t_entrega
                    current_production_possible = False
                    break
            
            if current_production_possible:
                best_delivery_period = t_entrega
                # Armazenar o plano de produção simulado para este pedido se aceito
                best_production_plan = {
                    'x': simul_producoes_adicionais,
                    'I': temp_I, # I pode ser atualizado com as produções simuladas depois
                    'Q': temp_Q,
                    'gamma_n_t': t_entrega,
                    'y': simul_y,
                    'z': simul_z,
                    'estoque_fifo': temp_estoque_fifo,
                    'capacidade_restante_periodo': simul_capacidade_restante_per_period,
                    'last_item_produced_per_period': simul_last_item_produced_per_period
                }
                break # Encontrou um período viável, tenta o próximo pedido prioritário

        # Se encontrou um plano de produção viável para o pedido n
        if best_delivery_period != -1:
            gamma[n][best_delivery_period] = 1 # Aceita o pedido
            
            # Atualiza o estado global com as produções e estoques do plano aceito
            for j in range(num_itens):
                for t in range(num_periodos):
                    x[j][t] += best_production_plan['x'][j][t] # Adiciona a produção simulada

            # Atualiza Q para o pedido aceito no t_entrega (consumo do estoque existente)
            for j, required_qty in itens_demandados_neste_pedido.items():
                qty_to_consume_from_real_stock = required_qty
                # Consome do estoque principal (FIFO)
                for idx in range(len(estoque_fifo[j])):
                    if qty_to_consume_from_real_stock <= 0:
                        break

                    prod_t, qty_in_stk, valid_until_t = estoque_fifo[j][idx]
                    
                    if best_delivery_period - prod_t <= vida_util[j]: # Validade para o período de entrega
                        qty_taken = min(qty_to_consume_from_real_stock, qty_in_stk)
                        k_idade = best_delivery_period - prod_t
                        if k_idade >= 0 and k_idade <= vida_util[j]:
                            Q[j][n][best_delivery_period][k_idade] += qty_taken
                            I[j][best_delivery_period][k_idade] -= qty_taken # Atualiza I aqui
                            estoque_fifo[j][idx] = (prod_t, qty_in_stk - qty_taken, valid_until_t)
                            qty_to_consume_from_real_stock -= qty_taken

            # Adiciona a nova produção ao estoque_fifo e atualiza a variável I_jt^0 para o período de produção
            for j in range(num_itens):
                for t_prod in range(num_periodos):
                    if best_production_plan['x'][j][t_prod] > 0:
                        estoque_fifo[j].append((t_prod, best_production_plan['x'][j][t_prod], t_prod + vida_util[j]))
                        I[j][t_prod][0] += best_production_plan['x'][j][t_prod]

            # Atualiza as capacidades restantes e os setups
            for p in range(num_periodos):
                capacidade_periodo[p] = best_production_plan['capacidade_restante_periodo'][p]
                
                # Mescla as variáveis de setup e máquina preparada
                # Esta parte pode ser mais complexa se houver sobreposição de produção de múltiplos pedidos no mesmo período
                # Para simplificar na heurística, vamos sobrescrever se um pedido de alta prioridade usa um slot
                for j_item in range(num_itens):
                    if best_production_plan['y'][j_item][p] == 1:
                        y[j_item][p] = 1
                    for i_prev_item in range(num_itens):
                        if best_production_plan['z'][i_prev_item][j_item][p] == 1:
                            z[i_prev_item][j_item][p] = 1
                
                last_item_produced_per_period[p] = best_production_plan['last_item_produced_per_period'][p] if best_production_plan['last_item_produced_per_period'][p] is not None else last_item_produced_per_period[p]


            # Limpa o estoque_fifo removendo entradas com quantidade zero
            for j in range(num_itens):
                estoque_fifo[j] = [(p_t, q, v_t) for p_t, q, v_t in estoque_fifo[j] if q > 0]
    
    # Após aceitar todos os pedidos possíveis, precisamos garantir que as variáveis I estejam consistentes
    # com o estoque_fifo final, especialmente para idades > 0
    # Iteramos novamente sobre todos os períodos e itens para preencher I
    for t in range(num_periodos):
        for j in range(num_itens):
            # Reset I[j][t][k] para o período atual (pois já foi atualizado com produções)
            for k_reset in range(max(vida_util) + 1):
                I[j][t][k_reset] = 0
            
            # Recalcula I[j][t][k] baseado no estoque_fifo final
            # Filtra o estoque_fifo para o período t, considerando apenas itens produzidos até t
            # E calcula sua idade no final de t
            for prod_t, qty, valid_until_t in estoque_fifo[j]:
                if prod_t <= t and t <= valid_until_t: # Item produzido até t e ainda válido no final de t
                    k_idade = t - prod_t
                    if k_idade >= 0 and k_idade <= vida_util[j]:
                        I[j][t][k_idade] += qty
            # A variável I[j][t][0] já foi atualizada nas etapas de produção
            # mas o restante das idades precisa ser recalculado com o estado final do estoque.
            # Esta parte é complexa em uma heurística, pois o FIFO é um estado dinâmico.
            # A forma mais robusta seria recalcular I a cada passo de tempo (o que já fazemos no começo do loop t).
            # Para a etapa de pós-processamento, podemos garantir a consistência final.

            # Reconstruir I[j][t][k] baseado em estoque_fifo para consistência final
            # para o período 't', I[j][t][k] representa o estoque no FINAL do período 't'
            # então, um item produzido em 't_producao' tem idade 't - t_producao' no final de 't'.
            for k in range(max(vida_util) + 1):
                current_stock_at_age_k = 0
                for prod_t, qty, valid_until_t in estoque_fifo[j]:
                    if (t - prod_t) == k and t <= valid_until_t: # Verifica idade e validade no final de 't'
                        current_stock_at_age_k += qty
                I[j][t][k] = current_stock_at_age_k


    return {"x": x, "I": I, "Q": Q, "gamma": gamma, "y": y, "z": z}