import random
from copy import deepcopy
# Supondo que calcular_custo_total.py contenha a função para calcular o custo total
from .calcular_custo_total import calcular_custo_total
# Importa a função de sequenciamento que já existe na sua hc1_atualizada
from .gerar_solucao_inicial_hc1_atualizada import obter_sequencia_producao
import math
import numpy as np


def trocar_ordem_producao_2_itens(solucao_atual, parametros_problema):
    """
    Realiza o movimento de vizinhança: Troca a ordem de produção entre dois itens
    dentro de um mesmo período.
    Inclui agora a reavaliação dos setups do período seguinte se o último item do período atual muda.

    Args:
        solucao_atual (dict): Dicionário representando a solução atual, com as variáveis de decisão.
        parametros_problema (dict): Dicionário com os parâmetros do problema (custos, capacidades, etc.).

    Returns:
        tuple: (nova_solucao, delta_custo) se o movimento for válido e melhorar a FO,
               (None, None) caso contrário ou se não houver melhora.
    """
    print("\n--- INICIANDO MOVIMENTO: Trocar Ordem de Produção de 2 Itens ---")
    nova_solucao = deepcopy(solucao_atual)
    custo_original = calcular_custo_total(solucao_atual, parametros_problema)
    print(f"Custo Original da Solução: {custo_original}")

    num_periodos = parametros_problema["num_periodos"]
    num_itens = parametros_problema["num_itens"]
    tempo_producao = parametros_problema["tempo_producao"]
    tempo_setup = parametros_problema["tempo_setup"]
    capacidade_periodo_original = parametros_problema["capacidade_periodo"]

    periodos_com_producao = [t for t in range(num_periodos) if nova_solucao['sequencias_producao'][t]]
    
    if not periodos_com_producao:
        print("DEBUG: Nenhum período com produção para aplicar o movimento.")
        return None, None

    periodo_selecionado = random.choice(periodos_com_producao)
    print(f"DEBUG: Período selecionado para troca: {periodo_selecionado}")

    seq_periodo_original = list(nova_solucao['sequencias_producao'][periodo_selecionado]) # Usar uma cópia para o original
    
    if len(seq_periodo_original) < 2:
        print(f"DEBUG: Período {periodo_selecionado} tem menos de 2 itens na sequência. Pulando.")
        return None, None

    idx1, idx2 = random.sample(range(len(seq_periodo_original)), 2)
    
    item1 = seq_periodo_original[idx1]
    item2 = seq_periodo_original[idx2]

    print(f"DEBUG: Itens selecionados para troca no período {periodo_selecionado}: {item1} (idx {idx1}) e {item2} (idx {idx2})")

    nova_seq_periodo = list(seq_periodo_original)
    nova_seq_periodo[idx1], nova_seq_periodo[idx2] = nova_seq_periodo[idx2], nova_seq_periodo[idx1]
    nova_solucao['sequencias_producao'][periodo_selecionado] = nova_seq_periodo

    print(f"DEBUG: Sequência original do período {periodo_selecionado}: {seq_periodo_original}")
    print(f"DEBUG: Nova sequência do período {periodo_selecionado}: {nova_seq_periodo}")

    # --- Atualização de y e z para o período selecionado ---
    ultimo_item_periodo_anterior = None
    if periodo_selecionado > 0:
        if solucao_atual['sequencias_producao'][periodo_selecionado - 1]:
            ultimo_item_periodo_anterior = solucao_atual['sequencias_producao'][periodo_selecionado - 1][-1]
    
    print(f"DEBUG: Último item do período anterior ({periodo_selecionado-1}): {ultimo_item_periodo_anterior}")

    # Zera as variáveis y e z para o período selecionado antes de preencher com a nova sequência
    for j_item in range(num_itens):
        nova_solucao['y'][j_item][periodo_selecionado] = 0
        for i_item in range(num_itens):
            nova_solucao['z'][i_item][j_item][periodo_selecionado] = 0

    if nova_seq_periodo:
        nova_solucao['y'][nova_seq_periodo[0]][periodo_selecionado] = 1
        
        if ultimo_item_periodo_anterior is not None and ultimo_item_periodo_anterior != nova_seq_periodo[0]:
            nova_solucao['z'][ultimo_item_periodo_anterior][nova_seq_periodo[0]][periodo_selecionado] = 1
        
        for idx in range(len(nova_seq_periodo) - 1):
            item_origem = nova_seq_periodo[idx]
            item_destino = nova_seq_periodo[idx+1]
            if item_origem != item_destino:
                nova_solucao['z'][item_origem][item_destino][periodo_selecionado] = 1
    
    # Recalcula o tempo gasto no período selecionado com a nova sequência para checar capacidade
    tempo_total_producao_periodo = sum(tempo_producao[j] * nova_solucao['x'][j][periodo_selecionado] for j in nova_seq_periodo)
    
    tempo_setup_periodo = 0
    if ultimo_item_periodo_anterior is not None and nova_seq_periodo and ultimo_item_periodo_anterior != nova_seq_periodo[0]:
        tempo_setup_periodo += tempo_setup[ultimo_item_periodo_anterior][nova_seq_periodo[0]]
    
    for idx in range(len(nova_seq_periodo) - 1):
        item_origem = nova_seq_periodo[idx]
        item_destino = nova_seq_periodo[idx+1]
        if item_origem != item_destino:
            tempo_setup_periodo += tempo_setup[item_origem][item_destino]

    tempo_total_gasto_no_periodo = tempo_total_producao_periodo + tempo_setup_periodo
    
    print(f"DEBUG: Tempo de produção da nova sequência no período {periodo_selecionado}: {tempo_total_producao_periodo}")
    print(f"DEBUG: Tempo de setup da nova sequência no período {periodo_selecionado}: {tempo_setup_periodo}")
    print(f"DEBUG: Tempo total gasto no período {periodo_selecionado} com a nova sequência: {tempo_total_gasto_no_periodo}")
    print(f"DEBUG: Capacidade original do período {periodo_selecionado}: {capacidade_periodo_original[periodo_selecionado]}")

    if tempo_total_gasto_no_periodo > capacidade_periodo_original[periodo_selecionado]:
        print(f"DEBUG: Nova sequência excede a capacidade no período {periodo_selecionado}. Movimento inválido.")
        return None, None
    
    # --- Propagação do impacto para o próximo período (T+1) ---
    old_last_item_current_period = seq_periodo_original[-1] if seq_periodo_original else None
    new_last_item_current_period = nova_seq_periodo[-1] if nova_seq_periodo else None

    if new_last_item_current_period != old_last_item_current_period:
        next_period = periodo_selecionado + 1
        if next_period < num_periodos:
            print(f"DEBUG: Último item do período {periodo_selecionado} mudou. Reavaliando setups no período {next_period}.")
            
            # Pega os itens que *já estão* produzidos no próximo período (não mudam com este movimento)
            items_in_next_period = [j for j in range(num_itens) if nova_solucao['x'][j][next_period] > 0]
            
            # Se houver itens no próximo período, recalcular sua sequência e setups
            if items_in_next_period:
                # Reconstruir a sequência para o próximo período com o *novo* último item do período atual
                recalculated_seq_next_period, recalculated_setup_time_next_period = obter_sequencia_producao(
                    items_in_next_period, 
                    tempo_setup, 
                    new_last_item_current_period # O novo item anterior para o próximo período
                )

                # Atualizar y e z para o próximo período baseado nesta sequência recalculada
                # Zera y e z existentes para next_period primeiro
                for j_next in range(num_itens):
                    nova_solucao['y'][j_next][next_period] = 0
                    for i_next in range(num_itens):
                        nova_solucao['z'][i_next][j_next][next_period] = 0

                if recalculated_seq_next_period:
                    nova_solucao['y'][recalculated_seq_next_period[0]][next_period] = 1
                    if new_last_item_current_period is not None and new_last_item_current_period != recalculated_seq_next_period[0]:
                        nova_solucao['z'][new_last_item_current_period][recalculated_seq_next_period[0]][next_period] = 1
                    
                    for idx_next in range(len(recalculated_seq_next_period) - 1):
                        item_origem_next = recalculated_seq_next_period[idx_next]
                        item_destino_next = recalculated_seq_next_period[idx_next + 1]
                        if item_origem_next != item_destino_next:
                            nova_solucao['z'][item_origem_next][item_destino_next][next_period] = 1
                
                # Atualizar a sequência armazenada na solução para o próximo período
                nova_solucao['sequencias_producao'][next_period] = recalculated_seq_next_period
                
                # Re-checar a capacidade para o próximo período, pois o custo de setup pode ter mudado
                tempo_total_producao_next_period = sum(tempo_producao[j] * nova_solucao['x'][j][next_period] for j in items_in_next_period)
                new_total_gasto_next_period = tempo_total_producao_next_period + recalculated_setup_time_next_period
                
                if new_total_gasto_next_period > capacidade_periodo_original[next_period]:
                    print(f"DEBUG: Movimento inviabiliza período {next_period} devido à capacidade. Rejeitando.")
                    return None, None
            else:
                # Se não houver produção no próximo período, mas o item anterior mudou
                # e não há um primeiro item no próximo período para setup, apenas garante consistência
                nova_solucao['sequencias_producao'][next_period] = [] # Garante que está vazio se não houver produção
                # Os setups y e z para next_period já foram zerados acima, o que é o correto para período sem produção.

    custo_novo = calcular_custo_total(nova_solucao, parametros_problema)
    print(f"Custo da Nova Solução: {custo_novo}")

    delta_custo = custo_novo - custo_original
    print(f"DEBUG: Delta de Custo (Novo - Original): {delta_custo}")

    if delta_custo > 0:
        print("DEBUG: Movimento gerou uma MELHORIA na função objetivo. Aceitando a nova solução.")
        return nova_solucao, delta_custo
    else:
        print("DEBUG: Movimento não gerou melhoria na função objetivo. Rejeitando a nova solução.")
        return None, None