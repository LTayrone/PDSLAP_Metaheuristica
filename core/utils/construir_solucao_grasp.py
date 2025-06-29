import random
import math
from copy import deepcopy
from .gerar_solucao_inicial_hc1_atualizada import gerar_solucao_inicial_hc1_atualizada, obter_sequencia_producao

def construir_solucao_grasp(parametros, alpha):
    """
    Executa a fase de construção do GRASP para o problema de PDSLAP-AP.
    Esta função primeiro determina uma ordem de prioridade de pedidos usando um
    processo guloso randomizado e, em seguida, chama uma função construtiva
    para gerar a solução completa.

    Args:
        parametros (dict): Dicionário com os parâmetros do problema.
        alpha (float): Parâmetro do GRASP (0 <= alpha <= 1) que controla a
                       aleatoriedade. alpha=0 é puramente guloso.

    Returns:
        dict: Dicionário contendo a solução construída (x, I, Q, gamma, y, z).
    """
    print(f"--- Iniciando Fase de Construção GRASP (alpha = {alpha}) ---")

    # --- 1. Avaliação Gulosa dos Candidatos ---
    pedidos_candidatos = []
    for n in range(parametros["num_pedidos"]):
        # A métrica gulosa é a "Receita Pura".
        # Usamos a receita no primeiro dia da janela como referência.
        periodo_ref = parametros["periodo_inicial_entrega"][n] # Nota: Usar periodo_final_entrega é uma opção
        if periodo_ref < parametros["num_periodos"]:
            receita = parametros["receita_pedido"][n][periodo_ref]
            pedidos_candidatos.append({'pedido_id': n, 'receita': receita})

    # Ordena para identificar o melhor e o pior valor
    pedidos_candidatos.sort(key=lambda x: x['receita'], reverse=True)
    
    # Se não houver candidatos com receita, não é possível construir.
    if not pedidos_candidatos:
        # Retorna uma solução vazia e válida
        return construir_com_ordem_definida(parametros, [])


    # --- 2. Construção da Lista de Candidatos Restrita (RCL) ---
    pedidos_priorizados_grasp = []
    
    # Cria uma cópia para poder modificar
    candidatos_restantes = list(pedidos_candidatos)

    while candidatos_restantes:
        receita_max = candidatos_restantes[0]['receita']
        receita_min = candidatos_restantes[-1]['receita']

        # Calcula o limiar de corte para a RCL
        limiar = receita_max - alpha * (receita_max - receita_min)

        # Filtra os candidatos que atendem ao limiar
        rcl = [c for c in candidatos_restantes if c['receita'] >= limiar]

        if not rcl:
            # Fallback: se a RCL estiver vazia, adiciona o melhor candidato
            rcl.append(candidatos_restantes[0])

        # --- 3. Seleção Aleatória e Atualização ---
        pedido_selecionado = random.choice(rcl)
        pedidos_priorizados_grasp.append(pedido_selecionado['pedido_id'])

        # Remove o pedido selecionado da lista de candidatos para a próxima iteração
        candidatos_restantes = [c for c in candidatos_restantes if c['pedido_id'] != pedido_selecionado['pedido_id']]


    print(f"Ordem de prioridade definida pelo GRASP: {pedidos_priorizados_grasp}")

    # --- 4. Construção da Solução Final ---
    solucao_final = construir_com_ordem_definida(parametros, pedidos_priorizados_grasp)

    return solucao_final


def construir_com_ordem_definida(parametros, ordem_pedidos):
    """
    Função adaptada e corrigida para construir uma solução FACTÍVEL a partir 
    de uma lista de prioridade de pedidos já definida.
    A lógica interna agora garante que a restrição de capacidade nunca seja violada.
    """
    # --- EXTRAÇÃO DOS PARÂMETROS ---
    quantidade_pedidos = parametros["num_pedidos"]
    quantidade_periodos = parametros["num_periodos"]
    quantidade_itens = parametros["num_itens"]
    demanda_pedidos = parametros["demanda_pedidos"]
    capacidade_periodo_original = parametros["capacidade_periodo"].copy()
    tempo_producao = parametros["tempo_producao"]
    tempo_setup = parametros["tempo_setup"]
    periodo_inicial_entrega = parametros["periodo_inicial_entrega"]
    periodo_final_entrega = parametros["periodo_final_entrega"]
    vida_util = parametros["vida_util"]

    # --- INICIALIZAÇÃO DAS VARIÁVEIS DE DECISÃO FINAIS ---
    producao = {j: {t: 0 for t in range(quantidade_periodos)} for j in range(quantidade_itens)}
    estoque = {j: {t: {k: 0 for k in range(max(vida_util) + 1)} for t in range(quantidade_periodos)} for j in range(quantidade_itens)}
    quantidade_atendida_por_pedido = {j: {n: {t: {k: 0 for k in range(max(vida_util) + 1)} for t in range(quantidade_periodos)} for n in range(quantidade_pedidos)} for j in range(quantidade_itens)}
    pedido_atendido = {n: {t: 0 for t in range(quantidade_periodos)} for n in range(quantidade_pedidos)}
    maquina_preparada = {j: {t: 0 for t in range(quantidade_periodos)} for j in range(quantidade_itens)}
    troca_producao = {i: {j: {t: 0 for t in range(quantidade_periodos)} for j in range(quantidade_itens)} for i in range(quantidade_itens)}
    sequencias_por_periodo = {t: [] for t in range(quantidade_periodos)}

    # --- VARIÁVEIS DE ESTADO PERSISTENTES ---
    lotes_em_estoque = {j: [] for j in range(quantidade_itens)}
    ultimo_item_produzido_no_periodo = {t: None for t in range(-1, quantidade_periodos)}

    # --- LOOP PRINCIPAL COM ORDEM DO GRASP ---
    for n_pedido in ordem_pedidos:
        if any(pedido_atendido[n_pedido].values()):
            continue

        melhor_periodo_entrega_para_pedido = -1
        plano_de_producao_viavel = {}
        
        for candidato_periodo_entrega in reversed(range(periodo_inicial_entrega[n_pedido], periodo_final_entrega[n_pedido] + 1)):
            if candidato_periodo_entrega >= quantidade_periodos:
                continue

            # --- Início da Simulação para o candidato_periodo_entrega ---
            producao_necessaria_apos_consumo = {j: 0 for j in range(quantidade_itens)}
            producao_simulada_para_pedido_atual = {j: {t: 0 for t in range(quantidade_periodos)} for j in range(quantidade_itens)}
            
            # _CORREÇÃO_: Criar uma cópia do estado do último item para uso exclusivo nesta simulação.
            # Isso evita que a simulação use dados inconsistentes do estado global.
            ultimo_item_simulado = deepcopy(ultimo_item_produzido_no_periodo)

            # 1. CONSUMO DE ESTOQUE EXISTENTE (SIMULAÇÃO)
            for j_item in range(quantidade_itens):
                demanda_item_para_pedido = demanda_pedidos[n_pedido][j_item]
                if demanda_item_para_pedido == 0: continue
                
                estoque_disponivel_item = sum(q for p, q, v in lotes_em_estoque[j_item] if candidato_periodo_entrega - p <= vida_util[j_item])
                producao_necessaria_apos_consumo[j_item] = max(0, demanda_item_para_pedido - estoque_disponivel_item)
            
            # 2. ALOCAÇÃO DE PRODUÇÃO (SIMULAÇÃO)
            alocacao_producao_viavel = True
            itens_a_produzir = [j for j, q in producao_necessaria_apos_consumo.items() if q > 0]
            
            if itens_a_produzir:
                for j_prod in sorted(itens_a_produzir, key=lambda j: producao_necessaria_apos_consumo[j], reverse=True):
                    demanda_restante_item = producao_necessaria_apos_consumo[j_prod]
                    item_alocado = False
                    
                    for t_prod in reversed(range(max(0, candidato_periodo_entrega - vida_util[j_prod]), candidato_periodo_entrega + 1)):
                        producao_total_no_periodo_sim = {item: (producao[item][t_prod] + producao_simulada_para_pedido_atual[item][t_prod]) for item in range(quantidade_itens)}
                        producao_total_no_periodo_sim[j_prod] += demanda_restante_item
                        itens_no_periodo_sim = [item for item, qtd in producao_total_no_periodo_sim.items() if qtd > 0]
                        
                        # _CORREÇÃO_: Utiliza o estado SIMULADO (`ultimo_item_simulado`) para obter o item anterior.
                        # Esta é a correção principal para garantir o cálculo de setup correto.
                        ultimo_item_ant_sim = ultimo_item_simulado.get(t_prod - 1)
                        
                        seq_sim, setup_time_sim = obter_sequencia_producao(itens_no_periodo_sim, tempo_setup, ultimo_item_ant_sim)
                        prod_time_sim = sum(tempo_producao[item] * producao_total_no_periodo_sim[item] for item in seq_sim)
                        
                        if prod_time_sim + setup_time_sim <= capacidade_periodo_original[t_prod] + 1e-6:
                            producao_simulada_para_pedido_atual[j_prod][t_prod] += demanda_restante_item
                            
                            # _CORREÇÃO_: Atualiza o estado simulado com o último item da nova sequência.
                            if seq_sim:
                                ultimo_item_simulado[t_prod] = seq_sim[-1]
                                # Propaga essa informação para períodos futuros que estejam vazios na simulação,
                                # garantindo consistência para alocações futuras dentro do mesmo pedido.
                                for t_seguinte in range(t_prod + 1, quantidade_periodos):
                                    if sum(producao[j][t_seguinte] + producao_simulada_para_pedido_atual[j][t_seguinte] for j in range(quantidade_itens)) < 1e-6:
                                        ultimo_item_simulado[t_seguinte] = ultimo_item_simulado[t_prod]
                                    else:
                                        break
                            item_alocado = True
                            break
                    
                    if not item_alocado:
                        alocacao_producao_viavel = False
                        break

            if alocacao_producao_viavel:
                melhor_periodo_entrega_para_pedido = candidato_periodo_entrega
                plano_de_producao_viavel = producao_simulada_para_pedido_atual
                break
        
        # --- ETAPA 3: COMMIT - SE A SIMULAÇÃO FOI BEM SUCEDIDA ---
        if melhor_periodo_entrega_para_pedido != -1:
            pedido_atendido[n_pedido][melhor_periodo_entrega_para_pedido] = 1

            # Atualiza produção e lotes em estoque
            for j in range(quantidade_itens):
                for t in range(quantidade_periodos):
                    if plano_de_producao_viavel[j][t] > 0:
                        producao[j][t] += plano_de_producao_viavel[j][t]
                        lotes_em_estoque[j].append((t, plano_de_producao_viavel[j][t], t + vida_util[j]))

            # Atualiza consumo (Q) e debita dos lotes de estoque
            temp_lotes_para_consumo = deepcopy(lotes_em_estoque)
            for j_item in range(quantidade_itens):
                demanda = demanda_pedidos[n_pedido][j_item]
                if demanda <= 0: continue
                
                temp_lotes_para_consumo[j_item].sort(key=lambda x: x[0]) # FIFO
                for i in range(len(temp_lotes_para_consumo[j_item])):
                    p_t, q_lote, v_t = temp_lotes_para_consumo[j_item][i]
                    idade = melhor_periodo_entrega_para_pedido - p_t
                    if idade >= 0 and idade <= vida_util[j_item]:
                        consumo = min(demanda, q_lote)
                        if consumo > 0:
                            quantidade_atendida_por_pedido[j_item][n_pedido][melhor_periodo_entrega_para_pedido][idade] += consumo
                            temp_lotes_para_consumo[j_item][i] = (p_t, q_lote - consumo, v_t)
                            demanda -= consumo
                    if demanda < 1e-6: break
            
            lotes_em_estoque = {j: [lote for lote in temp_lotes_para_consumo[j] if lote[1] > 1e-6] for j in range(quantidade_itens)}
            
            # _CORREÇÃO_: A reconstrução do último item agora acontece após cada commit,
            # garantindo que o próximo pedido a ser avaliado parta de um estado global consistente.
            for t in range(quantidade_periodos):
                itens_a_produzir_no_periodo = [j for j in range(quantidade_itens) if producao[j][t] > 0]
                if itens_a_produzir_no_periodo:
                    item_anterior = ultimo_item_produzido_no_periodo.get(t - 1)
                    seq, _ = obter_sequencia_producao(itens_a_produzir_no_periodo, tempo_setup, item_anterior)
                    if seq:
                        ultimo_item_produzido_no_periodo[t] = seq[-1]
                else:
                    ultimo_item_produzido_no_periodo[t] = ultimo_item_produzido_no_periodo.get(t - 1)

    # --- ETAPA FINAL: RECONSTRUÇÃO DAS VARIÁVEIS DE ESTOQUE (I) e SEQUENCIAMENTO (y, z) ---
    # Esta parte final é executada uma vez após todos os pedidos serem processados.
    
    # Recalcula as sequências finais e as variáveis y e z
    ultimo_item_final = {}
    for t in range(quantidade_periodos):
        itens_a_produzir_no_periodo = [j for j in range(quantidade_itens) if producao[j][t] > 0]
        
        # Zera as variáveis de setup para o período
        for j in range(quantidade_itens):
            maquina_preparada[j][t] = 0
            for i in range(quantidade_itens):
                troca_producao[i][j][t] = 0
        
        if not itens_a_produzir_no_periodo:
            sequencias_por_periodo[t] = []
            ultimo_item_final[t] = ultimo_item_final.get(t - 1)
            continue

        item_anterior = ultimo_item_final.get(t - 1)
        seq, _ = obter_sequencia_producao(itens_a_produzir_no_periodo, tempo_setup, item_anterior)
        
        sequencias_por_periodo[t] = seq
        
        if seq:
            maquina_preparada[seq[0]][t] = 1
            if item_anterior is not None and item_anterior != seq[0]:
                troca_producao[item_anterior][seq[0]][t] = 1
            
            for i in range(len(seq) - 1):
                if seq[i] != seq[i+1]:
                   troca_producao[seq[i]][seq[i+1]][t] = 1
            
            ultimo_item_final[t] = seq[-1]
        else:
            ultimo_item_final[t] = item_anterior

    # Reconstrói a variável de estoque I com base na produção e consumo finais
    for j in range(quantidade_itens):
        estoque_temp = {t: {k: 0 for k in range(max(vida_util) + 1)} for t in range(-1, quantidade_periodos)}
        for t in range(quantidade_periodos):
            # 1. Estoque que envelheceu do período anterior
            for k in range(1, vida_util[j] + 1):
                estoque_temp[t][k] = estoque_temp[t-1][k-1]
            
            # 2. Adiciona produção do período atual (idade 0)
            estoque_temp[t][0] += producao[j][t]
            
            # 3. Subtrai o consumo do período atual
            for n in range(quantidade_pedidos):
                if pedido_atendido[n][t] == 1:
                    for k in range(vida_util[j] + 1):
                        consumo = quantidade_atendida_por_pedido[j][n][t].get(k, 0)
                        estoque_temp[t][k] -= consumo
            
            # Garante que o estoque não seja negativo
            for k in range(vida_util[j] + 1):
                estoque[j][t][k] = max(0, estoque_temp[t][k])


    # Retorno da solução completa
    return {
        "x": producao,
        "I": estoque,
        "Q": quantidade_atendida_por_pedido,
        "gamma": pedido_atendido,
        "y": maquina_preparada,
        "z": troca_producao,
        "sequencias_producao": sequencias_por_periodo
    }