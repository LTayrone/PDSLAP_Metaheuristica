import math
import numpy as np

def gerar_solucao_inicial(parametros):
    """
    Gera uma solução inicial heurística para o problema de produção com shelf-life.
    Esta versão tenta gerenciar o estoque e o shelf-life explicitamente.

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
    capacidade_periodo = parametros["capacidade_periodo"]
    tempo_producao = parametros["tempo_producao"]
    custo_setup = parametros["custo_setup"]
    tempo_setup = parametros["tempo_setup"]
    periodo_inicial_entrega = parametros["periodo_inicial_entrega"]
    periodo_final_entrega = parametros["periodo_final_entrega"]
    vida_util = parametros["vida_util"]

    # Inicializa as variáveis de decisão
    x = {j: {t: 0 for t in range(num_periodos)} for j in range(num_itens)}
    # I[j][t][k] = estoque do item j no final do periodo t com idade k
    # k pode ir de 0 (produzido no período t) até max(vida_util)
    I = {j: {t: {k: 0 for k in range(max(vida_util) + 1)} for t in range(num_periodos)} for j in range(num_itens)}
    # Q[j][n][t][k] = quantidade do item j de idade k usada para atender pedido n no periodo t
    Q = {j: {n: {t: {k: 0 for k in range(max(vida_util) + 1)} for t in range(num_periodos)} for n in range(num_pedidos)} for j in range(num_itens)}
    gamma = {n: {t: 0 for t in range(num_periodos)} for n in range(num_pedidos)}
    y = {j: {t: 0 for t in range(num_periodos)} for j in range(num_itens)}
    z = {i: {j: {t: 0 for t in range(num_periodos)} for j in range(num_itens)} for i in range(num_itens)}

    # Variáveis auxiliares para a heurística
    # Rastreia o estoque disponível por item, e por idade de produção para FIFO
    # estoque_fifo[j] = [(periodo_producao, quantidade_atual, periodo_vencimento), ...]
    # Será uma lista de tuplas para cada item.
    estoque_fifo = {j: [] for j in range(num_itens)}

    # Rastreia o último item produzido no período anterior para calcular setups
    last_item_produced_prev_period = None

    # Status dos pedidos (True se ainda não atendido)
    pedidos_pendentes = {n: True for n in range(num_pedidos)}

    # Prioriza pedidos por prazo final (L_n) e depois por prazo inicial (F_n)
    pedidos_ordenados_por_prazo = sorted(
        range(num_pedidos),
        key=lambda n: (periodo_final_entrega[n], periodo_inicial_entrega[n])
    )

    # Loop principal: Iterar período a período
    for t in range(num_periodos):
        capacidade_restante_periodo = capacidade_periodo[t]

        # --- ETAPA 1: Gerenciamento do Estoque (Envelhecer e Remover Vencidos) ---
        for j in range(num_itens):
            # Crie uma nova lista para o estoque detalhado do próximo passo, mantendo apenas os válidos
            new_estoque_fifo_j = []
            for prod_t, qty, valid_until_t in estoque_fifo[j]:
                # Se o item foi produzido no período 'prod_t', sua idade no final de 't' é 't - prod_t'
                # e ele vence no final de 'valid_until_t'
                if t <= valid_until_t: # Se ainda não venceu até o final do período atual
                    new_estoque_fifo_j.append((prod_t, qty, valid_until_t))
                else:
                    # Item venceu no período 'valid_until_t' ou antes, não o adiciona
                    pass
            estoque_fifo[j] = new_estoque_fifo_j

            # Para a variável I_jt^k: reseta para o período atual antes de preencher
            for k_reset in range(max(vida_util) + 1):
                I[j][t][k_reset] = 0

            # Preenche I_jt^k com o estoque existente (já com idades atualizadas)
            for prod_t, qty, valid_until_t in estoque_fifo[j]:
                k_idade = t - prod_t # Idade do item no final do período t
                if k_idade >= 0 and k_idade <= vida_util[j]:
                    I[j][t][k_idade] += qty # Acumula estoque de mesma idade
                # else: a idade é inválida (item pereceu ou lógica incorreta)

        # --- ETAPA 2: Decidir a Produção (x_jt) e Definir Sequência/Setups (y_jt, z_ijt) ---
        itens_para_produzir_neste_periodo = {} # {item_id: quantidade}

        # Heurística para decidir o que produzir:
        # Tenta atender a demanda de pedidos que precisam ser atendidos no período atual
        # e talvez um pouco mais para a frente, se houver capacidade.
        # Poderíamos somar a demanda total dos pedidos pendentes que podem ser atendidos com produção em 't'
        # e que o item não pereça.

        # Calcula a demanda líquida (demanda total - estoque existente)
        demanda_liquida_por_item = {j: 0 for j in range(num_itens)}

        for n in pedidos_ordenados_por_prazo:
            if pedidos_pendentes[n]:
                # Demanda dos pedidos que podem ser atendidos neste ou futuros períodos
                # desde que a produção em 't' seja válida (shelf-life)
                if periodo_inicial_entrega[n] <= t + max(vida_util) and periodo_final_entrega[n] >= t:
                    for j in range(num_itens):
                        # Quanto do item j é demandado pelo pedido n
                        q_jn = demanda_pedidos[n][j]
                        if q_jn > 0:
                            demanda_liquida_por_item[j] += q_jn

        # Subtrair estoque existente (que pode atender demanda) para obter a demanda líquida
        for j in range(num_itens):
            for prod_t, qty, valid_until_t in estoque_fifo[j]:
                if t <= valid_until_t: # Apenas estoque válido
                    demanda_liquida_por_item[j] -= qty
            demanda_liquida_por_item[j] = max(0, demanda_liquida_por_item[j]) # Garante que não seja negativo

        # Prioriza itens a produzir com base na demanda líquida e tempo de produção
        itens_priorizados_para_producao = sorted(
            [j for j, dem in demanda_liquida_por_item.items() if dem > 0],
            key=lambda j: (demanda_liquida_por_item[j] * tempo_producao[j]), reverse=True
        )

        sequencia_producao_efetiva = [] # Para registrar a sequência real no período t
        current_setup_origin_item = last_item_produced_prev_period # Item que terminou no período t-1

        # Alocação de produção e cálculo de setup
        for j in itens_priorizados_para_producao:
            if capacidade_restante_periodo <= 0:
                break

            qty_to_produce_j = 0

            # Tentar produzir a demanda líquida, ou o que couber na capacidade
            required_time_for_unit = tempo_producao[j]

            # Calcula o tempo de setup se este for o próximo item a ser produzido
            potential_setup_time = 0
            if current_setup_origin_item is not None:
                potential_setup_time = tempo_setup[current_setup_origin_item][j]
            elif len(sequencia_producao_efetiva) == 0 and last_item_produced_prev_period is not None:
                # Este é o primeiro item do período, e houve produção no período anterior
                potential_setup_time = tempo_setup[last_item_produced_prev_period][j]

            # Capacidade disponível para produção deste item (descontando setup)
            effective_capacity_for_production = capacidade_restante_periodo - potential_setup_time

            if effective_capacity_for_production > 0 and required_time_for_unit > 0:
                max_qty_by_capacity = math.floor(effective_capacity_for_production / required_time_for_unit)
                qty_to_produce_j = min(demanda_liquida_por_item[j], max_qty_by_capacity)
            elif required_time_for_unit == 0: # Caso item nao tenha tempo de producao
                 qty_to_produce_j = demanda_liquida_por_item[j]

            if qty_to_produce_j > 0:
                x[j][t] = qty_to_produce_j

                # Consome capacidade
                capacidade_restante_periodo -= (qty_to_produce_j * required_time_for_unit + potential_setup_time)

                # Registra na sequência e nas variáveis y, z
                sequencia_producao_efetiva.append(j)

                # Define y_jt
                y[j][t] = 1 # O item j é produzido neste período (máquina preparada para j)

                # Define z_ijt (trocas)
                if current_setup_origin_item is not None and current_setup_origin_item != j:
                    z[current_setup_origin_item][j][t] = 1

                current_setup_origin_item = j # Este item se torna o 'origem' para o próximo setup no período

        # Atualiza o último item produzido no período para o próximo ciclo
        if len(sequencia_producao_efetiva) > 0:
            last_item_produced_prev_period = sequencia_producao_efetiva[-1]
        else:
            last_item_produced_prev_period = None # Nada produzido neste período

        # Adiciona a produção x_jt ao estoque FIFO (como idade 0)
        for j in range(num_itens):
            if x[j][t] > 0:
                # A produção X_jt tem idade 0 e sua validade vai até t + vida_util[j]
                estoque_fifo[j].append((t, x[j][t], t + vida_util[j]))
                I[j][t][0] += x[j][t] # Também atualiza a variável I_jt^0

        # --- ETAPA 3: Atender Pedidos com Estoque Disponível ---
        pedidos_para_atender_neste_t = sorted(
            [n for n in pedidos_ordenados_por_prazo if pedidos_pendentes[n] and periodo_inicial_entrega[n] <= t and periodo_final_entrega[n] >= t],
            key=lambda n: periodo_final_entrega[n]
        )

        for n in pedidos_para_atender_neste_t:
            can_attend_pedido = True
            itens_demandados_neste_pedido = {j: demanda_pedidos[n][j] for j in range(num_itens) if demanda_pedidos[n][j] > 0}

            # Pre-verificação: Tenta atender todos os itens do pedido com o estoque atual
            # sem realmente consumir ainda, para decidir se o pedido pode ser atendido.
            temp_estoque_para_verificacao = {j: [(p_t, q, v_t) for p_t, q, v_t in estoque_fifo[j]] for j in range(num_itens)}
            temp_Q_para_verificacao = {j: {k: 0 for k in range(max(vida_util) + 1)} for j in range(num_itens)}

            for j, required_qty in itens_demandados_neste_pedido.items():
                qty_needed_for_item = required_qty
                # Consumir do estoque temporário (FIFO)
                # Iterar em ordem para simular FIFO
                for idx, (prod_t, qty_in_stk, valid_until_t) in enumerate(temp_estoque_para_verificacao[j]):
                    if qty_needed_for_item <= 0:
                        break # Já atendeu a demanda para este item

                    if t <= valid_until_t: # Estoque válido para o período atual
                        qty_to_take = min(qty_needed_for_item, qty_in_stk)

                        k_idade = t - prod_t
                        if k_idade >= 0 and k_idade <= vida_util[j]: # Idade válida
                            temp_Q_para_verificacao[j][k_idade] += qty_to_take
                            qty_needed_for_item -= qty_to_take
                            temp_estoque_para_verificacao[j][idx] = (prod_t, qty_in_stk - qty_to_take, valid_until_t)
                        #else: Estoque com idade inválida (pereceu ou não foi produzido no período correto)
                    #else: Estoque venceu antes ou no período atual (não pode ser usado)

            if any(qty_needed_for_item > 0 for qty_needed_for_item in itens_demandados_neste_pedido.values()):
                can_attend_pedido = False # Não conseguiu atender todos os itens

            # Se o pedido pode ser atendido (pre-verificação bem sucedida)
            if can_attend_pedido:
                gamma[n][t] = 1 # Marca o pedido como atendido neste período
                pedidos_pendentes[n] = False # Pedido foi atendido, não precisa mais ser considerado

                # Agora, realmente consome do estoque principal e atualiza Q
                for j, required_qty in itens_demandados_neste_pedido.items():
                    qty_to_consume_from_real_stock = required_qty

                    # Consome do estoque principal (FIFO)
                    for idx in range(len(estoque_fifo[j])):
                        if qty_to_consume_from_real_stock <= 0:
                            break

                        prod_t, qty_in_stk, valid_until_t = estoque_fifo[j][idx]

                        if t <= valid_until_t:
                            qty_taken = min(qty_to_consume_from_real_stock, qty_in_stk)

                            k_idade = t - prod_t
                            if k_idade >= 0 and k_idade <= vida_util[j]:
                                Q[j][n][t][k_idade] += qty_taken
                                # Atualiza I[j][t][k] subtraindo o que foi consumido
                                I[j][t][k_idade] -= qty_taken

                                # Atualiza o estoque detalhado
                                estoque_fifo[j][idx] = (prod_t, qty_in_stk - qty_taken, valid_until_t)
                                qty_to_consume_from_real_stock -= qty_taken

        # Limpa o estoque_fifo removendo entradas com quantidade zero
        for j in range(num_itens):
            estoque_fifo[j] = [(p_t, q, v_t) for p_t, q, v_t in estoque_fifo[j] if q > 0]


    # A variável V_jt não é diretamente calculada por esta heurística,
    # pois é uma variável auxiliar para o solver capturar a ordem.
    # Ela será 0 em todos os lugares, a menos que uma lógica específica para ela seja adicionada,
    # o que não é o foco de uma heurística.
    # O modelo MILP usaria V_jt para as restrições 10 e 11.

    return {"x": x, "I": I, "Q": Q, "gamma": gamma, "y": y, "z": z}