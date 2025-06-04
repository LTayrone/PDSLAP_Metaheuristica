# core.zip/utils/gerar_solucao_inicial_hc1_atualizada.py

import math
import numpy as np


def gerar_solucao_inicial_hc1_atualizada(parametros):
    # --- EXTRAÇÃO DOS PARÂMETROS ---
    quantidade_pedidos = parametros["num_pedidos"]
    quantidade_periodos = parametros["num_periodos"]
    quantidade_itens = parametros["num_itens"]
    demanda_pedidos = parametros["demanda_pedidos"]
    capacidade_periodo_original = parametros["capacidade_periodo"].copy()
    tempo_producao = parametros["tempo_producao"]
    tempo_setup = parametros["tempo_setup"]  # Matriz de tempos de setup
    periodo_inicial_entrega = parametros["periodo_inicial_entrega"]
    periodo_final_entrega = parametros["periodo_final_entrega"]
    receita_pedido = parametros["receita_pedido"]
    vida_util = parametros["vida_util"]  # shelf-life
    custo_estoque = parametros["custo_estoque"]
    custo_setup = parametros["custo_setup"]

    # --- INICIALIZAÇÃO DAS VARIÁVEIS DE DECISÃO FINAIS ---
    '''
    Lembrando a estrutura das variáveis de decisão, porem foram refatoradas como "Dicionário aninhado com comprehension"
    producao = {}
    for j in range(quantidade_itens):
        producao[j] = {}  # Cria um dicionário vazio para o item j
        for t in range(quantidade_periodos):
            producao[j][t] = 0  # Inicializa cada período com 0
    '''
    # x: produção do item j no período t
    producao = {j: {t: 0 for t in range(quantidade_periodos)} for j in range(quantidade_itens)}
    # I: estoque do item j com idade k ao final do período t
    estoque = {j: {t: {k: 0 for k in range(max(vida_util) + 1)} for t in range(quantidade_periodos)} for j in range(quantidade_itens)}
    # Q: quantidade de itens j com idade k utilizados para atender o pedido n ao final do período t
    quantidade_atendida_por_pedido = {j: {n: {t: {k: 0 for k in range(max(vida_util) + 1)} for t in range(quantidade_periodos)} for n in range(quantidade_pedidos)} for j in range(quantidade_itens)}
    # gamma: 1 se o pedido n vai ser atendido no período t
    pedido_atendido = {n: {t: 0 for t in range(quantidade_periodos)} for n in range(quantidade_pedidos)}
    # y: 1 se a máquina está preparada para a produção do item j no início do período t
    maquina_preparada = {j: {t: 0 for t in range(quantidade_periodos)} for j in range(quantidade_itens)}
    # z: 1 se ocorre troca da produção do item i para o item j durante o período t
    troca_producao = {i: {j: {t: 0 for t in range(quantidade_periodos)} for j in range(quantidade_itens)} for i in range(quantidade_itens)}

    # --- VARIÁVEIS DE ESTADO PERSISTENTES ---
    # estoque_detalhado: [(periodo_producao, quantidade_atual, periodo_vencimento), ...] para cada item
    lotes_em_estoque = {j: [] for j in range(quantidade_itens)}
    capacidade_restante_por_periodo = {t: capacidade_periodo_original[t] for t in range(quantidade_periodos)}
    ultimo_item_produzido_no_periodo = {t: None for t in range(quantidade_periodos)}

    # NOVA VARIÁVEL PARA ARMAZENAR AS SEQUÊNCIAS
    sequencias_por_periodo = {t: [] for t in range(quantidade_periodos)} # Inicializa com listas vazias

    # --- ETAPA 1: ORDENAR PEDIDOS POR RECEITA ---
    receita_total_por_pedido = {}
    for n in range(quantidade_pedidos):
        periodo_valido_proxy = periodo_inicial_entrega[n]
        if periodo_valido_proxy < quantidade_periodos:
            receita_total_por_pedido[n] = receita_pedido[n][periodo_valido_proxy]
        else:
            receita_total_por_pedido[n] = -math.inf

    pedidos_priorizados = sorted(
        [n for n in range(quantidade_pedidos) if receita_total_por_pedido[n] > -math.inf],
        key=lambda n: receita_total_por_pedido[n],
        reverse=True
    )

    # --- ETAPA 2: TENTAR ACEITAR CADA PEDIDO ---
    for n_pedido in pedidos_priorizados:
        # Se o pedido já foi atendido em alguma iteração anterior, pula.
        if any(pedido_atendido[n_pedido][t] == 1 for t in range(quantidade_periodos)):
            continue

        melhor_periodo_entrega_para_pedido = -1
        # producao_temporaria_para_pedido_n: acumula a produção deste pedido distribuída nos períodos
        producao_temporaria_para_pedido_n = {j: {t: 0 for t in range(quantidade_periodos)} for j in range(quantidade_itens)}
        # quantidade_atendida_temporaria_para_pedido_n: armazena o consumo simulado para este pedido
        quantidade_atendida_temporaria_para_pedido_n = {j: {t: {k: 0 for k in range(max(vida_util) + 1)} for t in range(quantidade_periodos)} for j in range(quantidade_itens)}

        # Tenta atender o pedido no último período de sua janela de entrega possível (para adiar produção)
        for candidato_periodo_entrega in reversed(range(periodo_inicial_entrega[n_pedido], periodo_final_entrega[n_pedido] + 1)):
            if candidato_periodo_entrega >= quantidade_periodos:
                continue

            eh_viavel_para_este_periodo_entrega = True
            # Copiar o estado atual do estoque para simulação
            lotes_em_estoque_simulacao_atual = {j: [(p_t, q, v_t) for p_t, q, v_t in lotes_em_estoque[j]] for j in range(quantidade_itens)}
            producao_necessaria_apos_consumo = {j: 0 for j in range(quantidade_itens)}

            # Zerar as produções simuladas para este candidato_periodo_entrega,
            # pois será preenchido novamente para cada tentativa de período de entrega
            producao_simulada_atual = {j: {t: 0 for t in range(quantidade_periodos)} for j in range(quantidade_itens)}

            # CONSUMO DE ESTOQUE EXISTENTE (SIMULAÇÃO)
            for j_item in range(quantidade_itens):
                demanda_item_para_pedido = demanda_pedidos[n_pedido][j_item]
                if demanda_item_para_pedido == 0:
                    continue

                quantidade_restante_para_atender = demanda_item_para_pedido
                novos_lotes_em_estoque_simulacao_j = []

                # Consumir do estoque simulado (FIFO)
                lotes_em_estoque_simulacao_atual[j_item].sort(key=lambda x: x[0])

                for periodo_producao_lote, quantidade_lote_em_estoque, vencimento_lote in lotes_em_estoque_simulacao_atual[j_item]:
                    if quantidade_restante_para_atender <= 0:
                        novos_lotes_em_estoque_simulacao_j.append((periodo_producao_lote, quantidade_lote_em_estoque, vencimento_lote))
                        continue

                    # Idade do item no candidato_periodo_entrega
                    idade_no_momento_entrega = candidato_periodo_entrega - periodo_producao_lote

                    if idade_no_momento_entrega >= 0 and idade_no_momento_entrega <= vida_util[j_item]:
                        quantidade_a_usar_do_estoque = min(quantidade_restante_para_atender, quantidade_lote_em_estoque)

                        quantidade_restante_para_atender -= quantidade_a_usar_do_estoque

                        quantidade_atendida_temporaria_para_pedido_n[j_item][candidato_periodo_entrega][idade_no_momento_entrega] += quantidade_a_usar_do_estoque

                        quantidade_restante_no_lote = quantidade_lote_em_estoque - quantidade_a_usar_do_estoque
                        if quantidade_restante_no_lote > 0:
                            novos_lotes_em_estoque_simulacao_j.append((periodo_producao_lote, quantidade_restante_no_lote, vencimento_lote))
                    else:
                        # Lote vencido ou não utilizável para esta entrega, ou idade inválida
                        novos_lotes_em_estoque_simulacao_j.append((periodo_producao_lote, quantidade_lote_em_estoque, vencimento_lote))
                lotes_em_estoque_simulacao_atual[j_item] = novos_lotes_em_estoque_simulacao_j

                if quantidade_restante_para_atender > 0:
                    producao_necessaria_apos_consumo[j_item] = quantidade_restante_para_atender

            if all(qty == 0 for qty in producao_necessaria_apos_consumo.values()):
                melhor_periodo_entrega_para_pedido = candidato_periodo_entrega
                break

            # PRODUÇÃO E CAPACIDADE PARA NOVOS ITENS (AGORA DISTRIBUÍDA NA SIMULAÇÃO)
            capacidade_restante_simulacao_por_periodo = {t: capacidade_restante_por_periodo[t] for t in range(quantidade_periodos)}
            ultimo_item_produzido_simulacao_no_periodo = {t: ultimo_item_produzido_no_periodo[t] for t in range(quantidade_periodos)}

            # Copia as produções já existentes (de pedidos aceitos anteriormente) para a simulação
            # O cálculo de setup e capacidade considera todas as produções em um período.
            producao_existente_simulacao = {j: {t: producao[j][t] for t in range(quantidade_periodos)} for j in range(quantidade_itens)}

            itens_para_produzir_simulacao_ordenados = sorted(
                [j for j, qty in producao_necessaria_apos_consumo.items() if qty > 0],
                key=lambda j_item: tempo_producao[j_item] * producao_necessaria_apos_consumo[j_item],
                reverse=True
            )

            alocacao_producao_bem_sucedida = True
            for j_prod_sim in itens_para_produzir_simulacao_ordenados:
                quantidade_a_produzir_item_restante = producao_necessaria_apos_consumo[j_prod_sim]
                item_produzido_completamente = False

                # Tenta produzir o item j_prod_sim em múltiplos períodos, do mais tardio para o mais cedo,
                # respeitando o shelf-life e a janela de entrega.
                for candidato_periodo_producao in reversed(range(max(0, candidato_periodo_entrega - vida_util[j_prod_sim]), candidato_periodo_entrega + 1)):
                    if candidato_periodo_producao >= quantidade_periodos:
                        continue

                    if quantidade_a_produzir_item_restante <= 0:
                        item_produzido_completamente = True
                        break

                    # Itens já existentes + itens que serão adicionados para este pedido N, neste período candidato_periodo_producao
                    # para o cálculo do setup e capacidade.
                    itens_no_periodo_para_sequenciamento_simulacao = []
                    for idx_item in range(quantidade_itens):
                        if producao_existente_simulacao[idx_item][candidato_periodo_producao] > 0:
                            itens_no_periodo_para_sequenciamento_simulacao.append(idx_item)
                        if producao_simulada_atual[idx_item][candidato_periodo_producao] > 0 and idx_item not in itens_no_periodo_para_sequenciamento_simulacao:
                            itens_no_periodo_para_sequenciamento_simulacao.append(idx_item)

                    # Adicionar o item j_prod_sim que estamos tentando alocar AGORA
                    if j_prod_sim not in itens_no_periodo_para_sequenciamento_simulacao:
                        itens_no_periodo_para_sequenciamento_simulacao.append(j_prod_sim)

                    # Calcula o tempo de setup com a função auxiliar para a sequência TOTAL de itens nesse período
                    item_anterior_para_seq_simulacao = ultimo_item_produzido_simulacao_no_periodo[candidato_periodo_producao - 1] if candidato_periodo_producao > 0 else None

                    # Simular a sequência e o tempo de setup para *todos* os itens no período candidato_periodo_producao
                    sequencia_simulada_no_periodo, tempo_setup_simulado_no_periodo = obter_sequencia_producao(itens_no_periodo_para_sequenciamento_simulacao, tempo_setup, item_anterior_para_seq_simulacao)

                    # Recalcular o tempo total necessário para o período candidato_periodo_producao com as produções existentes
                    # E considerar a produção do item j_prod_sim
                    tempo_total_necessario_para_periodo = 0
                    for item_na_seq_simulada in sequencia_simulada_no_periodo:
                        if item_na_seq_simulada == j_prod_sim:
                            tempo_total_necessario_para_periodo += tempo_producao[item_na_seq_simulada] * (producao_existente_simulacao[item_na_seq_simulada][candidato_periodo_producao] + producao_simulada_atual[item_na_seq_simulada][candidato_periodo_producao] + quantidade_a_produzir_item_restante)
                        else:
                            tempo_total_necessario_para_periodo += tempo_producao[item_na_seq_simulada] * (producao_existente_simulacao[item_na_seq_simulada][candidato_periodo_producao] + producao_simulada_atual[item_na_seq_simulada][candidato_periodo_producao])

                    tempo_total_necessario_para_periodo += tempo_setup_simulado_no_periodo

                    # Se a capacidade for suficiente para o total de itens naquele período
                    if tempo_total_necessario_para_periodo <= capacidade_periodo_original[candidato_periodo_producao]:
                        # Produzir a quantidade restante para este item
                        producao_simulada_atual[j_prod_sim][candidato_periodo_producao] += quantidade_a_produzir_item_restante
                        # Note: O cálculo de capacidade_restante_simulacao_por_periodo é feito no COMMIT.
                        # Aqui apenas verificamos a factibilidade com a capacidade original.

                        item_produzido_completamente = True
                        quantidade_a_produzir_item_restante = 0  # Toda a demanda do item foi alocada
                        break  # Sai do loop de candidato_periodo_producao para este item j_prod_sim
                    else:
                        # Se não couber a demanda restante, tenta alocar o máximo possível
                        # Calcula a quantidade que caberia:
                        tempo_producao_atual_sem_item_novo = sum(
                            tempo_producao[item_na_seq_simulada] * (producao_existente_simulacao[item_na_seq_simulada][candidato_periodo_producao] + producao_simulada_atual[item_na_seq_simulada][candidato_periodo_producao])
                            for item_na_seq_simulada in itens_no_periodo_para_sequenciamento_simulacao if item_na_seq_simulada != j_prod_sim
                        )

                        # Tempo restante de capacidade APÓS setups e outras produções
                        capacidade_para_item_novo = capacidade_periodo_original[candidato_periodo_producao] - (tempo_producao_atual_sem_item_novo + tempo_setup_simulado_no_periodo)

                        if capacidade_para_item_novo > 0 and tempo_producao[j_prod_sim] > 0:
                            quantidade_pode_ser_produzida_aqui = math.floor(capacidade_para_item_novo / tempo_producao[j_prod_sim])
                            quantidade_a_produzir_neste_slot = min(quantidade_a_produzir_item_restante, quantidade_pode_ser_produzida_aqui)

                            if quantidade_a_produzir_neste_slot > 0:
                                producao_simulada_atual[j_prod_sim][candidato_periodo_producao] += quantidade_a_produzir_neste_slot
                                quantidade_a_produzir_item_restante -= quantidade_a_produzir_neste_slot
                                # A capacidade restante real será atualizada no COMMIT

            if quantidade_a_produzir_item_restante > 0:  # Se ainda sobrou demanda para j_prod_sim
                alocacao_producao_bem_sucedida = False
                break  # Não foi possível produzir tudo necessário para este item

            if not alocacao_producao_bem_sucedida:
                eh_viavel_para_este_periodo_entrega = False
                break

            if eh_viavel_para_este_periodo_entrega:
                melhor_periodo_entrega_para_pedido = candidato_periodo_entrega
                # Copia as produções simuladas para o plano de produção temporário do pedido
                for j_copia in range(quantidade_itens):
                    for t_copia in range(quantidade_periodos):
                        producao_temporaria_para_pedido_n[j_copia][t_copia] = producao_simulada_atual[j_copia][t_copia]

                break  # Encontrou um período de entrega viável, tenta o próximo pedido

        # --- ETAPA 3: SE PEDIDO ACEITO, COMPROMETER AS VARIÁVEIS DE DECISÃO FINAIS ---
        if melhor_periodo_entrega_para_pedido != -1:
            pedido_atendido[n_pedido][melhor_periodo_entrega_para_pedido] = 1

            # 1. Atualizar produções (x)
            for j_prod_commit in range(quantidade_itens):
                for t_prod_commit in range(quantidade_periodos):
                    if producao_temporaria_para_pedido_n[j_prod_commit][t_prod_commit] > 0:
                        producao[j_prod_commit][t_prod_commit] += producao_temporaria_para_pedido_n[j_prod_commit][t_prod_commit]
                        # Adicionar a nova produção ao estoque detalhado, como um novo lote
                        lotes_em_estoque[j_prod_commit].append((t_prod_commit, producao_temporaria_para_pedido_n[j_prod_commit][t_prod_commit], t_prod_commit + vida_util[j_prod_commit]))

            # 2. Atualizar consumo (Q) e ajustar estoque detalhado
            for j_consume_commit in range(quantidade_itens):
                if demanda_pedidos[n_pedido][j_consume_commit] == 0:
                    continue

                quantidade_restante_para_atender_commit = demanda_pedidos[n_pedido][j_consume_commit]

                novos_lotes_em_estoque_j_commit = []
                # Ordena para garantir FIFO
                lotes_em_estoque[j_consume_commit].sort(key=lambda x: x[0])

                for periodo_producao_lote_commit, quantidade_lote_em_estoque_commit, vencimento_lote_commit in lotes_em_estoque[j_consume_commit]:
                    if quantidade_restante_para_atender_commit <= 0:
                        novos_lotes_em_estoque_j_commit.append((periodo_producao_lote_commit, quantidade_lote_em_estoque_commit, vencimento_lote_commit))
                        continue

                    idade_no_momento_entrega_commit = melhor_periodo_entrega_para_pedido - periodo_producao_lote_commit
                    if idade_no_momento_entrega_commit >= 0 and idade_no_momento_entrega_commit <= vida_util[j_consume_commit]:
                        quantidade_a_usar_do_estoque_commit = min(quantidade_restante_para_atender_commit, quantidade_lote_em_estoque_commit)

                        quantidade_restante_para_atender_commit -= quantidade_a_usar_do_estoque_commit

                        quantidade_atendida_por_pedido[j_consume_commit][n_pedido][melhor_periodo_entrega_para_pedido][idade_no_momento_entrega_commit] += quantidade_a_usar_do_estoque_commit

                        quantidade_restante_no_lote_commit = quantidade_lote_em_estoque_commit - quantidade_a_usar_do_estoque_commit
                        if quantidade_restante_no_lote_commit > 0:
                            novos_lotes_em_estoque_j_commit.append((periodo_producao_lote_commit, quantidade_restante_no_lote_commit, vencimento_lote_commit))
                    else:
                        novos_lotes_em_estoque_j_commit.append((periodo_producao_lote_commit, quantidade_lote_em_estoque_commit, vencimento_lote_commit))
                lotes_em_estoque[j_consume_commit] = novos_lotes_em_estoque_j_commit

            # 3. Reconstruir `maquina_preparada`, `troca_producao`, `capacidade_restante_por_periodo`, `ultimo_item_produzido_no_periodo`
            # Esta parte é crucial para garantir que as próximas decisões usem um estado consistente.
            maquina_preparada = {j: {t: 0 for t in range(quantidade_periodos)} for j in range(quantidade_itens)}
            troca_producao = {i: {j: {t: 0 for t in range(quantidade_periodos)} for j in range(quantidade_itens)} for i in range(quantidade_itens)}
            capacidade_restante_por_periodo = {t: capacidade_periodo_original[t] for t in range(quantidade_periodos)}
            ultimo_item_produzido_no_periodo = {t: None for t in range(quantidade_periodos)}

            # Armazena as sequências reais para retorno
            temp_sequencias_por_periodo = {t: [] for t in range(quantidade_periodos)}

            for t_reconstrucao in range(quantidade_periodos):
                itens_a_produzir_no_periodo_reconstrucao = []
                for j_reconstrucao in range(quantidade_itens):
                    if producao[j_reconstrucao][t_reconstrucao] > 0:
                        itens_a_produzir_no_periodo_reconstrucao.append(j_reconstrucao)

                if itens_a_produzir_no_periodo_reconstrucao:
                    item_anterior_para_seq_reconstrucao = ultimo_item_produzido_no_periodo[t_reconstrucao - 1] if t_reconstrucao > 0 else None

                    seq_real_periodo_reconstrucao, tempo_setup_real_periodo_reconstrucao = obter_sequencia_producao(itens_a_produzir_no_periodo_reconstrucao, tempo_setup, item_anterior_para_seq_reconstrucao)

                    # Armazena a sequência para retorno
                    temp_sequencias_por_periodo[t_reconstrucao] = seq_real_periodo_reconstrucao

                    tempo_total_producao_real_periodo_reconstrucao = sum(tempo_producao[j_prod_na_seq] * producao[j_prod_na_seq][t_reconstrucao] for j_prod_na_seq in seq_real_periodo_reconstrucao)
                    tempo_total_gasto_no_periodo_reconstrucao = tempo_total_producao_real_periodo_reconstrucao + tempo_setup_real_periodo_reconstrucao

                    if tempo_total_gasto_no_periodo_reconstrucao > capacidade_periodo_original[t_reconstrucao]:
                        # print(f"ATENÇÃO CRÍTICA: Capacidade excedida no período {t_reconstrucao} durante reconstrução. Heurística falhou em manter factibilidade! Total gasto: {tempo_total_gasto_no_periodo_reconstrucao}, Capacidade: {capacidade_periodo_original[t_reconstrucao]}")
                        pass # Manter a lógica original de passar, mas é um ponto de atenção.

                    capacidade_restante_por_periodo[t_reconstrucao] = capacidade_periodo_original[t_reconstrucao] - tempo_total_gasto_no_periodo_reconstrucao

                    # Atualizar y e z
                    if seq_real_periodo_reconstrucao:
                        # APENAS O PRIMEIRO ITEM DA SEQUÊNCIA TEM maquina_preparada = 1.
                        maquina_preparada[seq_real_periodo_reconstrucao[0]][t_reconstrucao] = 1

                        soma_y_periodo_t = sum(maquina_preparada[j][t_reconstrucao] for j in range(quantidade_itens))
                        if soma_y_periodo_t > 1:
                            print(f"ERRO: Sum de y para o período {t_reconstrucao} é {soma_y_periodo_t}, deveria ser 1 ou 0.")
                        # -----------------------------

                        if item_anterior_para_seq_reconstrucao is not None and item_anterior_para_seq_reconstrucao != seq_real_periodo_reconstrucao[0]:
                            troca_producao[item_anterior_para_seq_reconstrucao][seq_real_periodo_reconstrucao[0]][t_reconstrucao] = 1

                        for idx_seq in range(len(seq_real_periodo_reconstrucao) - 1):
                            item_origem = seq_real_periodo_reconstrucao[idx_seq]
                            item_destino = seq_real_periodo_reconstrucao[idx_seq + 1]
                            if item_origem != item_destino:
                                troca_producao[item_origem][item_destino][t_reconstrucao] = 1

                        ultimo_item_produzido_no_periodo[t_reconstrucao] = seq_real_periodo_reconstrucao[-1]
                else:
                    ultimo_item_produzido_no_periodo[t_reconstrucao] = None

            # 4. Reconstruir a variável de estoque I[j][t][k] para todo o horizonte.
            for j_reconstrucao in range(quantidade_itens):
                for t_reconstrucao in range(quantidade_periodos):
                    for k_reconstrucao in range(max(vida_util) + 1):
                        estoque[j_reconstrucao][t_reconstrucao][k_reconstrucao] = 0

            # Reconstroi estoque com base em producao e quantidade_atendida_por_pedido (que são as variáveis finais e comprometidas)
            for periodo_atual in range(quantidade_periodos):
                for j_item_atual in range(quantidade_itens):
                    # a) Estoque com idade 0 (produção no periodo_atual)
                    consumo_idade_0_no_periodo = sum(quantidade_atendida_por_pedido[j_item_atual][n_temp][periodo_atual][0] for n_temp in range(quantidade_pedidos))
                    estoque[j_item_atual][periodo_atual][0] = producao[j_item_atual][periodo_atual] - consumo_idade_0_no_periodo
                    estoque[j_item_atual][periodo_atual][0] = max(0, estoque[j_item_atual][periodo_atual][0])

                    # b) Estoque com idade k > 0 (itens do período anterior que envelheceram)
                    if periodo_atual > 0:
                        for idade_anterior_k in range(max(vida_util)):
                            nova_idade = idade_anterior_k + 1

                            if nova_idade <= vida_util[j_item_atual]:
                                estoque_base_anterior = estoque[j_item_atual][periodo_atual - 1][idade_anterior_k]
                                consumo_desta_idade_no_periodo = sum(quantidade_atendida_por_pedido[j_item_atual][n_temp][periodo_atual][nova_idade] for n_temp in range(quantidade_pedidos))

                                estoque[j_item_atual][periodo_atual][nova_idade] = estoque_base_anterior - consumo_desta_idade_no_periodo
                                estoque[j_item_atual][periodo_atual][nova_idade] = max(0, estoque[j_item_atual][periodo_atual][nova_idade])
                            else:
                                estoque[j_item_atual][periodo_atual][nova_idade] = 0

    return {
        "x": producao,
        "I": estoque,
        "Q": quantidade_atendida_por_pedido,
        "gamma": pedido_atendido,
        "y": maquina_preparada,
        "z": troca_producao,
        "sequencias_producao": temp_sequencias_por_periodo
    }

# A função obter_sequencia_producao também com variáveis
def obter_sequencia_producao(itens_a_produzir, matriz_tempo_setup, ultimo_item_anterior=None):
    """
    Heurística gulosa para determinar uma sequência de produção com base no menor tempo de setup.
    Tenta construir a sequência visitando o item que tem o menor setup do item atual.

    Args:
        itens_a_produzir (list): Lista de índices dos itens que devem ser produzidos neste período.
        matriz_tempo_setup (numpy.ndarray): Matriz de tempos de setup, matriz_tempo_setup[i][j].
        ultimo_item_anterior (int, optional): O índice do último item produzido no período anterior.
                                             Usado para calcular o primeiro setup. Defaults to None.

    Returns:
        tuple: (list: sequencia de itens, float: tempo total de setup)
    """
    if not itens_a_produzir:
        return [], 0.0

    sequencia = []
    itens_restantes_para_sequenciamento = list(set(itens_a_produzir))

    item_atual_para_sequencia = None

    # Tenta usar o ultimo_item_anterior como o primeiro item da sequência se ele estiver nos itens_a_produzir
    if ultimo_item_anterior is not None and ultimo_item_anterior in itens_restantes_para_sequenciamento:
        item_atual_para_sequencia = ultimo_item_anterior
        itens_restantes_para_sequenciamento.remove(item_atual_para_sequencia)
    elif itens_restantes_para_sequenciamento:
        # Caso contrário, escolhe o item com o menor tempo de setup a partir de um estado "neutro" (ou o primeiro da lista)
        item_atual_para_sequencia = itens_restantes_para_sequenciamento.pop(0)
    else:
        return [], 0.0

    sequencia.append(item_atual_para_sequencia)

    tempo_total_setup = 0.0

    # Calcula o setup inicial se houver troca do item anterior para o primeiro item desta sequência
    if ultimo_item_anterior is not None and ultimo_item_anterior != sequencia[0]:
        tempo_total_setup += matriz_tempo_setup[ultimo_item_anterior][sequencia[0]]

    while itens_restantes_para_sequenciamento:
        if item_atual_para_sequencia is None:
            break

        # Escolhe o próximo item que minimiza o setup do item atual
        proximo_item = min(
            itens_restantes_para_sequenciamento,
            key=lambda j: matriz_tempo_setup[item_atual_para_sequencia][j]
        )

        # Adiciona o custo de setup se houver troca entre o item atual e o próximo
        if item_atual_para_sequencia != proximo_item:
            tempo_total_setup += matriz_tempo_setup[item_atual_para_sequencia][proximo_item]

        sequencia.append(proximo_item)
        itens_restantes_para_sequenciamento.remove(proximo_item)
        item_atual_para_sequencia = proximo_item

    return sequencia, tempo_total_setup