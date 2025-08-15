import numpy as np

def calcular_FO(solucao, parametros):
    """
    Calcula o valor da função objetivo:
    FO = soma(receita_pedido[n,t] * gamma[n,t]) - soma(sc[i,j] * z[i,j,t])
    """
    receita_total = np.sum(parametros['receita_pedido'] * solucao['gamma'])
    custo_setup_total = 0.0
    for t in range(parametros['num_periodos']):
        custo_setup_total += np.sum(parametros['custo_setup'] * solucao['z'][:, :, t])
    objetivo = receita_total - custo_setup_total
    print(f"Lucro Bruto: {receita_total:.2f}")
    print(f"Custo Setup: {custo_setup_total:.2f}")
    print(f"Objetivo: {objetivo:.2f}")
    return objetivo

def validar_restricoes(solucao, parametros):
    """
    Valida todas as restrições do modelo com produção distribuída até o período de entrega.
    """
    N = parametros['num_pedidos']
    J = parametros['num_itens']
    T = parametros['num_periodos']
    gamma = solucao['gamma']  # (N, T): 1 se pedido n é entregue em t
    x = solucao['x']          # (J, N, T): produção do item j do pedido n no período t
    y = solucao['y']          # (J, T)
    z = solucao['z']          # (J, J, T)
    V = solucao['V']          # (J, T)
    demanda = parametros['demanda_pedidos']  # (N, J)
    tempo_prod = parametros['tempo_producao']  # (J,)
    tempo_setup = parametros['tempo_setup']  # (J, J)
    capacidade = parametros['capacidade_periodo']  # (T,)

    # --- 1. Cada pedido entregue no máximo uma vez ---
    if np.any(np.sum(gamma, axis=1) > 1):
        print("Violado: pedido entregue mais de uma vez.")
        return False

    # --- 2. Produção acumulada até t deve atender demanda se gamma_nt = 1 ---
    for n in range(N):
        for j in range(J):
            acumulado = 0
            for t in range(T):
                acumulado += x[j, n, t]
                if gamma[n, t] == 1 and acumulado < demanda[n, j]:
                    print(f"Violado: pedido {n}, item {j} não produzido integralmente até t={t}.")
                    return False

    # --- 3. Capacidade por período ---
    for t in range(T):
        tempo_usado = 0.0
        for j in range(J):
            producao_jt = sum(x[j, n, t] for n in range(N))
            tempo_usado += tempo_prod[j] * producao_jt
        tempo_usado += np.sum(tempo_setup * z[:, :, t])
        if tempo_usado > capacidade[t]:
            print(f"Violado: capacidade excedida no período {t}. Usado: {tempo_usado:.2f}, Cap: {capacidade[t]:.2f}")
            return False

    # --- 4. Produção só se preparado ---
    for j in range(J):
        for t in range(T):
            producao_jt = sum(x[j, n, t] for n in range(N))
            if producao_jt > 0 and y[j, t] == 0:
                print(f"Violado: produção do item {j} no período {t} sem setup.")
                return False

    # --- 5. Sequenciamento: V_jt >= V_it + 1 se z_ijt = 1 ---
    for t in range(T):
        for i in range(J):
            for j in range(J):
                if i != j and z[i, j, t] == 1:
                    if V[j, t] < V[i, t] + 1:
                        print(f"Violado: ordem inválida {i}→{j} em t={t}.")
                        return False

    # --- 6. Conservação de setup (fluxo) ---
    for t in range(T - 1):
        for j in range(J):
            entrada = y[j, t] + np.sum(z[:, j, t])
            saida = np.sum(z[j, :, t]) + y[j, t + 1]
            if entrada != saida:
                print(f"Violado: fluxo de setup para item {j} entre t={t} e {t+1}.")
                return False

    return True

def gerar_solucao_heuristica_original(parametros):
    """
    Heurística que permite produção distribuída no tempo, mas entrega única.
    """
    N, J, T = parametros['num_pedidos'], parametros['num_itens'], parametros['num_periodos']
    demanda = parametros['demanda_pedidos']      # (N, J)
    receita = parametros['receita_pedido']       # (N, T)
    custo_setup = parametros['custo_setup']      # (J, J)
    tempo_setup = parametros['tempo_setup']      # (J, J)
    capacidade = parametros['capacidade_periodo']  # (T,)
    tempo_prod = parametros['tempo_producao']    # (J,)

    # Inicializar variáveis
    gamma = np.zeros((N, T), dtype=int)
    x = np.zeros((J, N, T), dtype=int)  # x[j,n,t]: produção do item j do pedido n no período t
    y = np.zeros((J, T), dtype=int)
    z = np.zeros((J, J, T), dtype=int)
    V = np.zeros((J, T), dtype=int)

    # Acumular capacidade disponível ao longo do tempo
    cap_acumulada = np.cumsum([c for c in capacidade])  # cap total até t

    # Ordenar pedidos por lucro máximo
    prioridades = [(np.max(receita[n]), n) for n in range(N)]
    prioridades.sort(reverse=True)

    for _, n in prioridades:
        best_t = -1
        best_seq = None
        melhor_lucro = -np.inf

        # Tentar entregar o pedido n no período t
        for t_entrega in range(T):
            if np.sum(gamma[n]) > 0:
                continue  # já alocado

            # Verificar se é possível produzir todo o pedido n até t_entrega
            tempo_total_necessario = 0.0
            setup_tempo_potencial = 0.0
            itens_pedido = np.where(demanda[n] > 0)[0]

            # Tempo de produção
            for j in itens_pedido:
                tempo_total_necessario += tempo_prod[j] * demanda[n, j]

            # Estimar tempo de setup: sequência mínima entre itens do pedido
            if len(itens_pedido) > 1:
                seq = [itens_pedido[0]]
                rem = set(itens_pedido[1:])
                while rem:
                    last = seq[-1]
                    next_j = min(rem, key=lambda j: custo_setup[last, j])
                    seq.append(next_j)
                    rem.remove(next_j)
                setup_tempo_potencial = sum(tempo_setup[seq[i], seq[i+1]] for i in range(len(seq)-1))
            else:
                setup_tempo_potencial = 0

            tempo_total = tempo_total_necessario + setup_tempo_potencial

            # Verificar se cabe na capacidade acumulada até t_entrega
            if tempo_total > cap_acumulada[t_entrega]:
                continue

            # Simular alocação no último período de produção (pode ser antes de t_entrega)
            # Para simplificar, vamos alocar no período mais tardio possível: t = t_entrega
            # Mas a produção pode ter começado antes — aqui, alocamos tudo em t_entrega
            # (melhoria futura: distribuir produção)

            # Verificar capacidade no período t_entrega
            prod_t = sum(tempo_prod[j] * demanda[n, j] for j in itens_pedido)
            setup_t = setup_tempo_potencial
            if prod_t + setup_t > capacidade[t_entrega]:
                continue

            # Avaliar lucro
            lucro_liquido = receita[n, t_entrega] - setup_tempo_potencial * 0.1  # peso arbitrário
            if lucro_liquido > melhor_lucro:
                melhor_lucro = lucro_liquido
                best_t = t_entrega
                best_seq = seq if len(itens_pedido) > 1 else list(itens_pedido)

        if best_t != -1:
            gamma[n, best_t] = 1
            # Alocar produção total no período best_t
            for j in range(J):
                x[j, n, best_t] = demanda[n, j]

            # Atualizar setup, sequência no período best_t
            y[:, best_t] = 0
            y[best_seq[0], best_t] = 1
            for i in range(len(best_seq) - 1):
                z[best_seq[i], best_seq[i+1], best_t] = 1
            for ordem, j in enumerate(best_seq):
                V[j, best_t] = ordem + 1

    # Propagar setup entre períodos
    for t in range(T - 1):
        itens_t = np.where(V[:, t] > 0)[0]
        if len(itens_t) == 0:
            continue
        ultimo_j = itens_t[np.argmax(V[itens_t, t])]
        if y[ultimo_j, t + 1] == 0 and np.sum(y[:, t + 1]) > 0: 
            inicial_t1 = np.argmax(y[:, t + 1])
            if custo_setup[ultimo_j, inicial_t1] == 0:
                y[:, t + 1] = 0
                y[ultimo_j, t + 1] = 1

    solucao = {'gamma': gamma, 'x': x, 'y': y, 'z': z, 'V': V}
    if validar_restricoes(solucao, parametros):
        print("Solução viável gerada com produção distribuível até entrega.")
    else:
        print("Solução inviável.")
    return solucao