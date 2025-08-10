import numpy as np
import math
import random
import copy

def calcular_FO(solucao, parametros):
    """
    Calcula o FO.
    """
    receita_total = np.sum(parametros['receita_pedido'] * solucao['gamma'])
    # Custo total de setups: sum(sc_ij * z_ijt) para todos i, j, t
    custo_setup_total = 0.0
    for t in range(parametros['num_periodos']):
        # Multiplicar matriz de custos com z para o período t, e somar
        custo_setup_total += np.sum(parametros['custo_setup'] * solucao['z'][:, :, t])
    objetivo = receita_total - custo_setup_total
    print(f"Lucro Bruto: {receita_total:.2f}")
    print(f"Custo Setup: {custo_setup_total:.2f}")
    print(f"Objetivo: {objetivo:.2f}")
    return objetivo

def validar_restricoes(solucao, parametros):
    """
    Valida restrições principais (aproximada para heurística).
    Retorna True se viável, False caso contrário.
    """
    N, J, T = parametros['num_pedidos'], parametros['num_itens'], parametros['num_periodos']
    gamma, y, z, V = solucao['gamma'], solucao['y'], solucao['z'], solucao['V']

    # Eq. 6: Max 1 por pedido (se for maior que 1, violamos)
    if np.any(np.sum(gamma, axis=1) > 1):
        return False
    
    # Eq. 3: Exatamente 1 y_jt por t
    if np.any(np.sum(y, axis=0) != 1):
        return False
    
    # Eq. 2: Capacidade por periodo (calcular exatamente)
    for t in range(T):
        prod_tempo = np.sum(parametros['tempo_producao'] * np.sum(parametros['demanda_pedidos'] * gamma[:, t][:, np.newaxis], axis=0))
        setup_tempo = np.sum(parametros['tempo_setup'] * z[:, :, t])  # Corrigido: removido np.newaxis desnecessário (assumindo shapes corretos)
        if prod_tempo + setup_tempo > parametros['capacidade_periodo'][t]:
            return False
        
    # Eq. 5: Ordem (checar se V_jt >= V_it +1 quando z_ijt=1)
    for t in range(T):
        for i in range(J):
            for j in range(J):
                if i != j and z[i, j, t] == 1:
                    if V[j, t] < V[i, t] + 1:
                        return False
                             
    # Checagem de fluxo (Eq. 4)
    for t in range(T-1):
        for j in range(J):
            left = y[j, t] + np.sum(z[:, j, t])
            right = np.sum(z[j, :, t]) + y[j, t+1]
            if left != right:
                return False
    return True

def gerar_solucao_heuristica_original(parametros):
    """
    Heurística greedy + local search.
    """
    N, J, T = parametros['num_pedidos'], parametros['num_itens'], parametros['num_periodos']
    demanda, receita, custo_setup, tempo_setup = parametros['demanda_pedidos'], parametros['receita_pedido'], parametros['custo_setup'], parametros['tempo_setup']
    capacidade_periodo, tempo_prod = parametros['capacidade_periodo'], parametros['tempo_producao']
    
    gamma = np.zeros((N, T), dtype=int)
    y = np.zeros((J, T), dtype=int)
    z = np.zeros((J, J, T), dtype=int)
    V = np.zeros((J, T), dtype=int)
    
    # Fase 1: Greedy - Alocar pedidos
    prioridades = [(np.max(receita[n]), n) for n in range(N)]  # Priorizar por receita max
    prioridades.sort(reverse=True)
    
    for _, n in prioridades:
        best_t, best_obj = -1, -np.inf
        for t in range(T):
            if np.sum(gamma[n]) > 0:  # Simples: evitar múltiplos, mas ajustar
                continue
            # Itens demandados pelo novo pedido + existentes em t
            gamma_temp = gamma.copy()
            gamma_temp[n, t] = 1
            q_t = np.sum(demanda * gamma_temp[:, t][:, np.newaxis], axis=0)
            itens_t = np.where(q_t > 0)[0]
            if len(itens_t) == 0:
                continue
            
            # Otimizar sequência simples (nearest neighbor para minimizar custo setup)
            seq = [itens_t[0]]  # Começar com primeiro
            remaining = set(itens_t[1:])
            while remaining:
                last = seq[-1]
                next_item = min(remaining, key=lambda j: custo_setup[last, j])
                seq.append(next_item)
                remaining.remove(next_item)
            
            # Calcular tempo setup para sequência
            setup_tempo = sum(tempo_setup[seq[i], seq[i+1]] for i in range(len(seq)-1))
            prod_tempo = sum(tempo_prod[j] * q_t[j] for j in itens_t)
            if prod_tempo + setup_tempo > capacidade_periodo[t]:
                continue
            
            # Estimar obj
            obj_est = receita[n, t] - sum(custo_setup[seq[i], seq[i+1]] for i in range(len(seq)-1))
            if obj_est > best_obj:
                best_obj = obj_est
                best_t = t
                best_seq = seq
        
        if best_t != -1:
            gamma[n, best_t] = 1
            # Aplicar sequência
            y[:, best_t] = 0
            y[best_seq[0], best_t] = 1
            for i in range(len(best_seq)-1):
                z[best_seq[i], best_seq[i+1], best_t] = 1
            for ord_, j in enumerate(best_seq):
                V[j, best_t] = ord_ + 1
    
    # Propagar y e z para fluxo (Eq. 4 - versão corrigida e robusta)
    for t in range(T-1):
        # Encontre o último item produzido em t (maior V entre itens com V > 0)
        itens_produzidos_t = np.where(V[:, t] > 0)[0]
        if len(itens_produzidos_t) == 0:
            print(f"Debug: Período {t} vazio, nada a propagar.")
            continue
        
        last_j = itens_produzidos_t[np.argmax(V[itens_produzidos_t, t])]
        print(f"Debug: Último item em t={t}: {last_j}")
        
        # Verifique t+1
        itens_produzidos_t1 = np.where(V[:, t+1] > 0)[0]
        if len(itens_produzidos_t1) == 0:
            # t+1 vazio: Continue do last_j sem troca
            y[last_j, t+1] = 1
            V[last_j, t+1] = 1
            print(f"Debug: Setado y[{last_j}, {t+1}] = 1 (período vazio).")
            continue
        
        # t+1 não vazio: Pegue inicial atual
        initial_t1_indices = np.where(y[:, t+1] == 1)[0]
        if len(initial_t1_indices) != 1:
            print(f"Aviso: Múltiplos y=1 em t={t+1}, pulando propagação.")
            continue
        
        initial_j = initial_t1_indices[0]
        if last_j == initial_j:
            print(f"Debug: Match perfeito em t={t+1}, sem troca necessária.")
            continue  # Já compatível, sem custo extra
        
        # Mismatch: Tente evitar troca mudando y para last_j (se custo zero ou baixo)
        if custo_setup[last_j, initial_j] == 0 or tempo_setup[last_j, initial_j] == 0:
            # Mude inicial para last_j sem adicionar z (economiza)
            y[:, t+1] = 0
            y[last_j, t+1] = 1
            # Ajuste V: Defina V[last_j, t+1] = 1, e o antigo initial vira 2 (com z implícito se custo zero)
            V[last_j, t+1] = 1
            V[initial_j, t+1] = 2  # Assuma transição simples
            print(f"Debug: Mudado inicial de t={t+1} para {last_j} sem custo.")
            continue
        
        # Senão, adicione z[last_j, initial_j, t+1], mas cheque capacidade
        tempo_extra = tempo_setup[last_j, initial_j]
        # Calcule capacidade atual em t+1 (semelhante à validação)
        prod_tempo_t1 = np.sum(tempo_prod * np.sum(demanda * gamma[:, t+1][:, np.newaxis], axis=0))
        setup_tempo_t1_atual = np.sum(tempo_setup * z[:, :, t+1])
        if prod_tempo_t1 + setup_tempo_t1_atual + tempo_extra > capacidade_periodo[t+1]:
            print(f"Aviso: Adicionar troca em t={t+1} viola capacidade; pulando.")
            continue  # Não adicione para evitar inviabilidade
        
        # Adicione a troca
        z[last_j, initial_j, t+1] = 1
        # Ajuste V apenas para itens afetados: Defina V[last_j] = max(V em t+1) + 1? Não, para inserir no início:
        max_v_t1 = np.max(V[:, t+1])
        V[itens_produzidos_t1, t+1] += 1  # Shift só itens produzidos
        V[last_j, t+1] = 1  # last_j como novo primeiro
        # Atualize y para novo inicial
        y[:, t+1] = 0
        y[last_j, t+1] = 1
        print(f"Debug: Adicionada troca z[{last_j}, {initial_j}, {t+1}] com custo {custo_setup[last_j, initial_j]}.")
    
    # Fase 2: Local Search - Realocar pedidos (ativado para teste)
    solucao_atual = {'gamma': gamma, 'y': y, 'z': z, 'V': V}
    obj_atual = calcular_FO(solucao_atual, parametros)
    
    for iter_ in range(0):  # Ativado com 10 iterações para refinamento (ajuste)
        for n in range(N):
            curr_t = np.argmax(gamma[n])
            if gamma[n, curr_t] == 0:
                continue
            for new_t in range(T):
                if new_t == curr_t:
                    continue
                gamma_temp = gamma.copy()
                gamma_temp[n, curr_t] = 0
                gamma_temp[n, new_t] = 1
                # TODO: Reotimizar sequência em curr_t e new_t (repita lógica de greedy aqui para atualizar y/z/V localmente)
                # Por agora, use aproximado; adicione full reotimização para precisão
                obj_novo = calcular_FO({'gamma': gamma_temp, 'y': y, 'z': z, 'V': V}, parametros)  # Aproximado
                if obj_novo > obj_atual:
                    gamma = gamma_temp
                    obj_atual = obj_novo
                    break
    
    solucao = {'gamma': gamma, 'y': y, 'z': z, 'V': V}
    if validar_restricoes(solucao, parametros):
        print("Solução viável!")
    else:
        print("Solução aproximada - algumas restrições podem precisar ajuste.")
    return solucao
