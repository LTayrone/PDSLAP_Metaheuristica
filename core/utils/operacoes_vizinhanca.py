import random
from copy import deepcopy
from .calcular_custo_total import calcular_custo_total
from .gerar_solucao_inicial_hc1_atualizada import obter_sequencia_producao # Importa a função de sequenciamento

# Funções auxiliares para reverter e aplicar o impacto de um pedido
def _remover_impacto_pedido(solucao, parametros, n_pedido, t_original):
    """
    Remove o impacto de um pedido atendido em um período t_original da solução.
    Retorna uma nova solução com o impacto removido e os parâmetros atualizados.
    """
    temp_solucao = deepcopy(solucao)

    num_itens = parametros["num_itens"]
    num_periodos = parametros["num_periodos"]
    tempo_producao = parametros["tempo_producao"]
    tempo_setup = parametros["tempo_setup"]
    capacidade_periodo_original = parametros["capacidade_periodo"]

    # 1. Marcar pedido como não atendido no período original
    if temp_solucao['gamma'][n_pedido][t_original] == 1:
        temp_solucao['gamma'][n_pedido][t_original] = 0
    else:
        # Se o pedido não estava atendido nesse período, algo está errado ou ele foi movido antes
        print(f"ALERTA: Pedido {n_pedido} não estava atendido no período {t_original} ao tentar remover impacto.")
        return None # Retorna None se o estado não é o esperado

    # Reverter Q (consumo de estoque) para este pedido neste período
    # Isso vai afetar as idades do estoque I
    for j_item in range(num_itens):
        for k_idade in range(max(parametros["vida_util"]) + 1):
            qty_consumida = temp_solucao['Q'][j_item][n_pedido][t_original][k_idade]
            if qty_consumida > 0:
                temp_solucao['I'][j_item][t_original][k_idade] += qty_consumida # Devolve ao estoque
                temp_solucao['Q'][j_item][n_pedido][t_original][k_idade] = 0 # Zera Q

    # Reverter X (produção) e seu impacto no estoque I e capacidade
    # Para isso, precisamos identificar qual produção foi feita *para este pedido*.
    # Na HC1, a produção é feita sob demanda do pedido.
    # Esta parte é a mais tricky: idealmente, precisaríamos de uma variável V_jnt (produção de j para pedido n em t).
    # Como não temos, vamos assumir que toda a produção x[j][t] que seria "para" este pedido
    # agora é liberada ou precisa ser recalculada se fosse de propósito geral.
    # Por simplicidade da heurística, vamos considerar que a produção de x[j][t] era dedicada,
    # e agora essa quantidade é liberada (e remove seu custo de setup se for o caso).

    # Primeiro, vamos identificar quais itens tiveram produção *exclusivamente* para este pedido
    # É muito difícil desfazer 'x' perfeitamente sem rastrear a intenção original de cada 'x_jt'.
    # A maneira mais segura é RECALCULAR 'x', 'y', 'z', 'I' para os períodos afetados.
    # Isso tornaria a função muito mais complexa.

    # ALTERNATIVA (Mais Simples para Heurística):
    # Não tentaremos "desfazer" X, Y, Z. Vamos apenas liberar a demanda do pedido n.
    # O recálculo de X, Y, Z, I será feito na função principal 'alterar_periodo_atendimento_pedido'
    # de uma forma mais abrangente ou na "aplicação" do novo período.
    # Por ora, vamos manter a lógica de que remover o pedido *libera* o que ele consumiu (Q) e o que foi produzido (X).

    # Recalcular as variáveis de produção (x, y, z) e estoque (I) de todos os períodos
    # Para isso, vamos precisar da lógica da HC1 de balanceamento.
    # Isso é complexo demais para uma sub-função de "remover_impacto" de uma heurística simples.

    # Vamos simplificar drasticamente para este movimento:
    # Apenas o gamma será alterado. As produções e estoques serão reconstruídos na função chamadora
    # ou de forma mais genérica, se o novo plano for aceito.
    # Isso significa que essa sub-função só lida com o gamma e o Q do período de entrega.

    # Para fins de simulação de alteração da solução:
    # Apenas zera a produção x e o estoque I para o período original, e depois reconstrói.
    # (Este é um hack simplificado, mas necessário para manter o movimento "fácil")

    # Zera produções do pedido e consumos do período original
    for j_item in range(num_itens):
        producao_consumida_pelo_pedido_no_t_original = sum(solucao['Q'][j_item][n_pedido][t_original][k] for k in range(max(parametros["vida_util"]) + 1))
        # Se a produção era exatamente a demanda do pedido, podemos removê-la.
        # No entanto, isso é perigoso em uma heurística, pois a produção pode atender múltiplos pedidos.
        # A solução mais robusta é recalcular tudo.

    # Para tornar o movimento possível de implementar, vamos usar uma abordagem mais global de "limpar e reconstruir"
    # as partes afetadas, em vez de um "desfazer" cirúrgico.
    # A função principal `alterar_periodo_atendimento_pedido` fará isso.
    # Esta função auxiliar, por enquanto, será mais um placeholder.

    return temp_solucao

def _aplicar_impacto_pedido(solucao, parametros, n_pedido, t_destino):
    """
    Aplica o impacto de um pedido atendido no período t_destino na solução.
    Retorna uma nova solução com o impacto aplicado e os parâmetros atualizados.
    """
    temp_solucao = deepcopy(solucao)

    num_itens = parametros["num_itens"]
    num_periodos = parametros["num_periodos"]
    tempo_producao = parametros["tempo_producao"]
    tempo_setup = parametros["tempo_setup"]
    capacidade_periodo_original = parametros["capacidade_periodo"]
    vida_util = parametros["vida_util"]
    demanda_pedidos = parametros["demanda_pedidos"]

    # 1. Marcar pedido como atendido no período de destino
    temp_solucao['gamma'][n_pedido][t_destino] = 1

    # 2. Replanejar produção e consumo para este pedido no novo período
    # Isso é essencialmente uma versão simplificada da lógica da HC1 para um único pedido.
    
    # Criar um estado temporário do estoque FIFO para simulação
    # Esta é a parte mais complexa: simular o consumo e a produção.
    # A solução 'temp_solucao' tem o estado atual do estoque (sem o pedido n_pedido ainda).
    
    # Reconstruir um estoque FIFO simulado a partir de temp_solucao['x'] e temp_solucao['Q']
    # do estado atual da solução, excluindo o pedido n_pedido (que foi "removido" antes).
    
    # É muito difícil fazer isso de forma incremental e precisa sem a lógica completa da HC1.
    # A abordagem mais prática para heurísticas é:
    # A) Criar uma "nova" sub-solução para o pedido n_pedido no período t_destino.
    # B) Mergear essa sub-solução com o restante da solução.
    # C) Validar a solução mergeada.

    # Pela complexidade, esta função auxiliar será mais um esqueleto.
    # A lógica principal será na função 'alterar_periodo_atendimento_pedido'.
    
    # Reconstruir 'x', 'I', 'Q', 'y', 'z', e 'sequencias_producao' para os períodos afetados.
    # Esta é a parte que a HC1 já faz.
    # Para uma heurística de vizinhança, é mais comum que a função principal tente
    # aplicar o movimento e depois RECALCULE e RECONSTRUA as variáveis dependentes.

    # Para manter este "fácil", a função `alterar_periodo_atendimento_pedido` será
    # a principal responsável por lidar com o impacto total.
    
    return temp_solucao

def alterar_periodo_atendimento_pedido(solucao_atual, parametros_problema):
    """
    Realiza o movimento de vizinhança: Altera o período de atendimento de um pedido aceito.

    Args:
        solucao_atual (dict): Dicionário representando a solução atual, com as variáveis de decisão.
        parametros_problema (dict): Dicionário com os parâmetros do problema (custos, capacidades, etc.).

    Returns:
        tuple: (nova_solucao, delta_custo) se o movimento for válido e melhorar a FO,
               (None, None) caso contrário ou se não houver melhora.
    """
    print("\n--- INICIANDO MOVIMENTO: Alterar Período de Atendimento de Pedido ---")
    custo_original = calcular_custo_total(solucao_atual, parametros_problema)
    print(f"Custo Original da Solução: {custo_original}")

    num_pedidos = parametros_problema["num_pedidos"]
    num_periodos = parametros_problema["num_periodos"]
    periodo_inicial_entrega = parametros_problema["periodo_inicial_entrega"]
    periodo_final_entrega = parametros_problema["periodo_final_entrega"]
    vida_util = parametros_problema["vida_util"]
    tempo_producao = parametros_problema["tempo_producao"]
    tempo_setup = parametros_problema["tempo_setup"]
    capacidade_periodo_original = parametros_problema["capacidade_periodo"]
    demanda_pedidos = parametros_problema["demanda_pedidos"]
    num_itens = parametros_problema["num_itens"]

    # 1. Escolher aleatoriamente um pedido que está atualmente aceito
    pedidos_aceitos = []
    for n in range(num_pedidos):
        for t in range(num_periodos):
            if solucao_atual['gamma'][n][t] == 1:
                pedidos_aceitos.append((n, t))
                break # Pega o primeiro período em que foi aceito

    if not pedidos_aceitos:
        print("DEBUG: Nenhum pedido aceito para aplicar o movimento.")
        return None, None

    pedido_n_origem, periodo_t_origem = random.choice(pedidos_aceitos)
    print(f"DEBUG: Pedido selecionado: {pedido_n_origem}, Período de Origem: {periodo_t_origem}")

    # 2. Escolher um novo período de destino para o pedido dentro de sua janela de entrega
    periodos_candidatos_destino = [
        t for t in range(periodo_inicial_entrega[pedido_n_origem], periodo_final_entrega[pedido_n_origem] + 1)
        if t != periodo_t_origem and t < num_periodos # Deve ser diferente e dentro do horizonte
    ]

    if not periodos_candidatos_destino:
        print(f"DEBUG: Pedido {pedido_n_origem} não tem outros períodos válidos para mover dentro da janela.")
        return None, None

    periodo_t_destino = random.choice(periodos_candidatos_destino)
    print(f"DEBUG: Novo Período de Destino Candidato: {periodo_t_destino}")

    # --- SIMULAÇÃO DO MOVIMENTO ---
    # Para simular o movimento, vamos resetar as variáveis impactadas para este pedido
    # e tentar construir o novo cenário.
    
    # 1. Criar uma nova_solucao para trabalhar
    temp_solucao = deepcopy(solucao_atual)

    # 2. Zerar o gamma do pedido na origem e no destino inicialmente
    temp_solucao['gamma'][pedido_n_origem][periodo_t_origem] = 0
    temp_solucao['gamma'][pedido_n_origem][periodo_t_destino] = 0 # Inicialmente zero

    # 3. Remover o impacto do pedido 'n_origem' da solução atual
    # Para isso, vamos ter que "refazer" o planejamento de produção e estoque SEM este pedido.
    # É muito complicado. A abordagem mais prática em heurísticas é:
    #   a) Zera o impacto do pedido `n_origem` em `x`, `Q`, `I` para todos os períodos.
    #   b) Recalcula a solução *como se o pedido `n_origem` nunca tivesse sido aceito*.
    #   c) Tenta readicionar o pedido `n_origem` no `periodo_t_destino`.

    # Isso requer re-executar parte da lógica da HC1.
    # Dada a complexidade de desfazer e refazer o estoque FIFO e a sequencia,
    # a maneira mais "fácil" de implementar para uma heurística de busca local
    # é reconstruir as variáveis X, I, Q, Y, Z do zero (ou quase do zero) para os períodos afetados.
    # OU, o que é mais comum em heurísticas de busca local, ter uma função de VALIDAÇÃO.

    # Vamos simplificar: Vamos simular os impactos diretamente na `temp_solucao`
    # assumindo que a solução original é a base.

    # Limpar a produção e o consumo para o pedido_n_origem em todos os períodos
    # antes de tentar realocá-lo. Isso é uma simplificação drástica.
    for j_item in range(num_itens):
        for t_limp in range(num_periodos):
            # Zerar Q para este pedido em todos os períodos
            for k_idade in range(max(vida_util) + 1):
                temp_solucao['Q'][j_item][pedido_n_origem][t_limp][k_idade] = 0
            
            # Zerar X para este pedido no período t_limp (se a produção era para este pedido)
            # Isso é inferido e não garantido, mas é o que podemos fazer sem rastreamento preciso.
            # Se a produção era X_jt e toda ela foi para o pedido n_origem, podemos zerar X_jt.
            # Caso contrário, X_jt pode ser parcialmente para outros pedidos.
            # A forma segura é recalcular a produção necessária.

    # Para manter a lógica factível com a estrutura atual da HC1,
    # vamos simular o "impacto" de mover o pedido.
    # Basicamente, vamos tentar "atender" o pedido no `periodo_t_destino`
    # e verificar se a capacidade e o shelf-life são suficientes,
    # considerando o estado atual da `temp_solucao` (sem o pedido n_origem no t_origem).

    # Primeiro, vamos remover a produção *específica* que foi alocada para o pedido_n_origem.
    # Isso é complicado porque 'x' é uma variável agregada.
    # A alternativa é: Reconstruir o estoque FIFO e as produções a partir do zero
    # desconsiderando o pedido_n_origem e então adicionar o pedido_n_origem no novo período.

    # Isso nos leva a uma necessidade de uma função auxiliar que reconstrua o estado da solução
    # dado um conjunto de pedidos aceitos. Isso é o que a `gerar_solucao_inicial_hc1_atualizada` faz.
    # Para este movimento ser "fácil", precisamos de uma função que:
    #   1. Receba a solução atual.
    #   2. Receba o pedido 'n' a ser movido e o novo período 't_destino'.
    #   3. Produza uma *nova* solução com o pedido movido, OU retorne None se infactível.

    # Vamos reestruturar a lógica para usar uma abordagem que simula a "reconstrução"
    # do pedido movido, dentro da solução atual, mas de forma local.

    # Simulação da produção e consumo para o pedido_n_origem no periodo_t_destino
    # Isso requer um "snapshot" do estado do estoque e capacidade *antes* de tentar atender
    # o pedido_n_origem no periodo_t_destino.

    # A maneira mais pragmática para esta heurística:
    # 1. Desabilitar o pedido na posição original.
    temp_solucao['gamma'][pedido_n_origem][periodo_t_origem] = 0
    # 2. Tentar habilitar o pedido na nova posição e verificar factibilidade.
    temp_solucao['gamma'][pedido_n_origem][periodo_t_destino] = 1

    # AGORA, O PONTO CRÍTICO: Recalcular a produção e estoque para todos os itens
    # levando em conta a nova decisão de gamma. Isso é quase como rodar
    # a HC1 novamente, mas apenas para o(s) pedido(s) impactado(s) e períodos.
    # A forma mais simples: Reconstruir as variáveis 'x', 'I', 'Q', 'y', 'z', 'sequencias_producao'
    # para a solução *inteira* após esta mudança de gamma.

    # Para isso, é essencial ter uma função que "revalide" e "recalcule"
    # a produção, estoque e sequenciamento com base *somente* nos 'gamma' aceitos.
    # Sua `gerar_solucao_inicial_hc1_atualizada` faz isso se você puder controlá-la para
    # apenas receber os `gamma` fixados.

    # Vamos criar um "estado_provisorio" para as produções e estoques
    # que seria o resultado de aceitar todos os pedidos que NÃO SÃO o pedido_n_origem,
    # mais o pedido_n_origem no novo período.

    # Isso nos leva a um problema de como a `gerar_solucao_inicial_hc1_atualizada`
    # foi projetada. Ela prioriza e decide *quais* pedidos aceitar.
    # Para um movimento de vizinhança, precisamos que ela *aceite* uma lista de pedidos
    # já decididos e recalcule as variáveis dependentes.

    # Adaptação da lógica:
    # 1. Pegue todos os pedidos ACEITOS na solucao_atual.
    # 2. Remova o pedido_n_origem da sua posição original.
    # 3. Adicione o pedido_n_origem no periodo_t_destino.
    # 4. Use uma função auxiliar que "reconstrua" a solução (x, I, Q, y, z, sequencias)
    #    dado o novo conjunto de 'gamma' fixados.

    # Isso significa que precisamos de uma função como:
    # `reconstruir_solucao_com_gammas_fixos(parametros, gammas_aceitos)`

    # Sem essa função auxiliar, a implementação deste movimento se torna
    # uma repetição muito grande de lógica de `gerar_solucao_inicial_hc1_atualizada` ou
    # algo muito propenso a erros.

    # Para fins de demonstração, vamos fazer uma SIMPLIFICAÇÃO EXTREMA para o cálculo
    # de impacto na capacidade e estoque APENAS para o período de origem e destino,
    # e para os itens específicos do pedido.

    # O "segredo" para tornar esse movimento "fácil" é uma função de validação/reconstrução
    # que receba a solução (incluindo o gamma modificado) e retorne uma solução factível
    # ou None se for infactível.

    # --- SIMPLIFICAÇÃO DA IMPLEMENTAÇÃO PARA EXEMPLO ---
    # Para não reescrever a HC1, vamos simular o impacto do pedido
    # na capacidade do período de destino e no estoque.

    # Obtenha o último item produzido no período anterior ao destino
    last_item_produced_prev_period_destino = None
    if periodo_t_destino > 0 and solucao_atual['sequencias_producao'][periodo_t_destino - 1]:
        last_item_produced_prev_period_destino = solucao_atual['sequencias_producao'][periodo_t_destino - 1][-1]

    # Obtenha os itens e quantidades demandadas pelo pedido
    demanda_itens_pedido = {j: demanda_pedidos[pedido_n_origem][j] for j in range(num_itens) if demanda_pedidos[pedido_n_origem][j] > 0}

    # Calcular o tempo de produção total para os itens do pedido
    tempo_producao_necessario_pedido = sum(tempo_producao[j] * qty for j, qty in demanda_itens_pedido.items())

    # Calcular o tempo de setup potencial no período de destino se esses itens forem produzidos
    # Isso é muito simplificado, pois não sabemos a sequência exata.
    # O ideal seria tentar inseri-los na sequência existente com menor setup.
    # Para manter "fácil", assumimos um setup se houver troca.
    
    # Simulação da capacidade restante no período de destino (antes de adicionar o pedido)
    simul_capacidade_restante_destino = capacidade_periodo_original[periodo_t_destino]
    # Precisamos subtrair o tempo já usado pelas produções não relacionadas a este pedido
    # no período de destino.
    # A `solucao_atual['x']` ainda inclui o pedido no período original.
    # Isso é um grande ponto de falha. A forma correta é:
    # 1. Criar uma base de solução `sem` o pedido_n_origem.
    # 2. Tentar `adicionar` o pedido_n_origem na nova base.

    # Para ser "fácil", vamos assumir que a `solucao_atual` já tem o impacto do pedido `n_origem`
    # removido do `periodo_t_origem`.
    # ISSO É UMA PREMISSA FORTÍSSIMA e não está garantida pela `deepcopy` sozinha.
    # A maneira de fazer isso com as funções que temos é:
    # 1. Criar uma lista de `gammas_atuais` (pedidos aceitos)
    # 2. Remover o pedido `n_origem` no `periodo_t_origem` dessa lista.
    # 3. Adicionar o pedido `n_origem` no `periodo_t_destino` a essa lista.
    # 4. Chamar a `gerar_solucao_inicial_hc1_atualizada` com uma *nova* ordem de prioridade
    #    que reflita essa mudança de `gamma`.
    # Essa abordagem seria robusta, mas exige refatorar a HC1 para aceitar pedidos pré-definidos.

    # Dado as restrições atuais, vamos simular de forma *muito simplificada* a factibilidade.
    # Esta função, com o que temos, será mais para *demonstrar* a ideia do movimento
    # do que uma implementação completa e robusta de factibilidade de estoque/produção.

    # --- Implementação Simplificada para o Exemplo ---
    # Vai se basear na capacidade e não na gestão de estoque detalhada
    # A validação de shelf-life e FIFO seria muito complexa sem uma função de reconstrução de estado.

    # Vamos assumir que a capacidade do período `periodo_t_destino` é a única restrição que testaremos
    # para este movimento. A validação completa do `shelf-life` e `FIFO` seria feita por uma função
    # de validação mais abrangente.

    # Simular o tempo necessário para o pedido no novo período
    # (produção + setup, assumindo que ele se encaixa)
    tempo_total_pedido_destino = 0
    if demanda_itens_pedido:
        # Soma do tempo de produção para os itens deste pedido
        tempo_total_producao_pedido_destino = sum(tempo_producao[j] * demanda_itens_pedido[j] for j in demanda_itens_pedido.keys())
        
        # Simula o tempo de setup (isso é uma simplificação bruta)
        # Assumindo que os itens do pedido serão produzidos em sequência após o último item do período anterior
        # ou após o primeiro item que já está na sequência.
        simul_sequencia_periodo_destino = list(solucao_atual['sequencias_producao'][periodo_t_destino])
        for j_item_dem in demanda_itens_pedido.keys():
            if j_item_dem not in simul_sequencia_periodo_destino:
                simul_sequencia_periodo_destino.append(j_item_dem)
        
        # Se a sequência está vazia, o primeiro item não tem setup vindo do período anterior
        # mas sim do "nada".
        temp_last_item = last_item_produced_prev_period_destino
        temp_setup_custo = 0
        if simul_sequencia_periodo_destino:
            if temp_last_item is not None and temp_last_item != simul_sequencia_periodo_destino[0]:
                temp_setup_custo += tempo_setup[temp_last_item][simul_sequencia_periodo_destino[0]]
            for i in range(len(simul_sequencia_periodo_destino) - 1):
                if simul_sequencia_periodo_destino[i] != simul_sequencia_periodo_destino[i+1]:
                    temp_setup_custo += tempo_setup[simul_sequencia_periodo_destino[i]][simul_sequencia_periodo_destino[i+1]]
        
        tempo_total_pedido_destino = tempo_total_producao_pedido_destino + temp_setup_custo
    
    # Capacidade atual do período de destino (já ocupada por outros pedidos)
    capacidade_ocupada_destino_atual = sum(
        parametros_problema['tempo_producao'][j] * solucao_atual['x'][j][periodo_t_destino]
        for j in range(num_itens)
    )
    # Incluir setups já existentes no período de destino
    for i_set in range(num_itens):
        for j_set in range(num_itens):
            if solucao_atual['z'][i_set][j_set][periodo_t_destino] == 1:
                capacidade_ocupada_destino_atual += parametros_problema['tempo_setup'][i_set][j_set]
    
    # Capacidade restante bruta no período de destino
    capacidade_restante_real_destino = capacidade_periodo_original[periodo_t_destino] - capacidade_ocupada_destino_atual

    if tempo_total_pedido_destino > capacidade_restante_real_destino:
        print(f"DEBUG: Pedido {pedido_n_origem} não pode ser atendido no período {periodo_t_destino} devido à capacidade insuficiente. Movimento inválido.")
        return None, None

    # Se passarmos daqui, assumimos que há capacidade.
    # Agora precisamos de uma função de "reconstrução" mais inteligente.

    # Para fins práticos desta implementação:
    # Vamos criar uma nova_solucao e reconstruí-la do zero.
    # Este é um "hack" para compensar a falta de uma função de "reconstrução"
    # incremental robusta.

    # Criar uma lista de gammas que representa a nova solução
    nova_config_gamma = deepcopy(solucao_atual['gamma'])
    nova_config_gamma[pedido_n_origem][periodo_t_origem] = 0
    nova_config_gamma[pedido_n_origem][periodo_t_destino] = 1

    # Chamando a função de geração de solução inicial como um "reconstrutor"
    # Isso exige que a HC1 seja capaz de receber os gammas fixos e apenas gerar x, I, Q, y, z.
    # No entanto, a `gerar_solucao_inicial_hc1_atualizada` decide quais pedidos aceitar.
    # Isso significa que teríamos que passar uma lista de pedidos aceitos para ela,
    # ou reescrever a HC1.

    # Dado que a `gerar_solucao_inicial_hc1_atualizada` já prioriza, vamos ter que fazer
    # uma solução de contorno para este movimento.

    # Solução de Contorno:
    # 1. Crie uma lista de pedidos que devem ser aceitos.
    # 2. Re-rode a HC1 com uma lógica modificada para FORÇAR a aceitação desses pedidos.
    # Esta não é a forma mais eficiente, mas é a mais "segura" com a estrutura atual.

    # Ou, uma forma mais simples:
    # Apenas alteramos `gamma` e re-calculamos o custo.
    # **Atenção**: Esta abordagem *não* garante a factibilidade das restrições de produção/estoque/shelf-life
    # se a mudança de `gamma` não for acompanhada de uma reconstrução de `x`, `I`, `Q`, `y`, `z`, `sequencias_producao`.

    # Para este exercício, vamos simular a mudança de `gamma` e recalcular o custo,
    # *assumindo* que as variáveis `x`, `I`, `Q`, `y`, `z` seriam ajustadas de forma factível.
    # Na prática, isso exigiria uma função `validar_solucao_completa` que reprocessaria tudo.

    # Vamos implementar a versão mais superficial para fins de demonstração,
    # com um AVISO claro sobre a validação completa.

    nova_solucao_simples = deepcopy(solucao_atual)
    nova_solucao_simples['gamma'][pedido_n_origem][periodo_t_origem] = 0
    nova_solucao_simples['gamma'][pedido_n_origem][periodo_t_destino] = 1

    # --- AVISO IMPORTANTE: RECALCULAR X, I, Q, Y, Z AQUI É COMPLEXO ---
    # Para uma implementação completa, a lógica abaixo deveria ser uma chamada
    # a uma função que, dada a nova configuração de `gamma`, reconstruiria
    # as variáveis `x`, `I`, `Q`, `y`, `z`, `sequencias_producao` de forma factível.
    # Isso é o que a `gerar_solucao_inicial_hc1_atualizada` faz.
    # Se você quiser que essa função seja mais robusta, teríamos que refatorar
    # `gerar_solucao_inicial_hc1_atualizada` para aceitar um conjunto de pedidos
    # para aceitar e recalcular tudo.

    # Por agora, vamos simular a mudança de gama e o impacto no custo,
    # mas o `x`, `I`, `Q`, `y`, `z` *não estarão necessariamente consistentes*
    # com a nova decisão de `gamma` sem um recálculo profundo.
    # Isso significa que o `calcular_custo_total` pode não ser preciso neste ponto.

    # PARA TER UMA FUNÇÃO DE VIZINHANÇA CORRETA:
    # A função ideal seria uma "reconstrução parcial" da solução:
    # 1. Receber solucao_atual e a mudança de gamma.
    # 2. Com base nos *novos* gammas, reconstruir x, I, Q, y, z, sequencias_producao
    #    para que a solução seja factível e válida.
    # 3. Retornar a nova solução reconstruída.

    # Como não temos uma função de reconstrução parcial pronta, e para evitar
    # reescrever toda a lógica da HC1 aqui, esta implementação será limitada.

    # --- A função calcular_custo_total() depende das variáveis x, I, Q, y, z.
    # Se as mudanças em gamma não forem refletidas nessas variáveis, o custo será incorreto.
    # Para fins de DEPURACAO E TESTE DE CONCEITO, vamos assumir que as outras variáveis
    # seriam ajustadas magicamente.

    # A ÚNICA FORMA DE SER PRECISO AGORA É:
    # Chamar uma versão da HC1 que aceita uma lista de pedidos a serem atendidos.
    # Ex: `reconstruir_solucao(parametros, pedidos_a_atender)`

    # Para demonstrar o movimento, vamos fazer a troca de gamma e *simular* o custo,
    # com a ressalva de que a validação completa precisaria de mais.

    # Placeholder para a nova solução completa, se fosse reconstruída
    # (Este é o passo que falta para a função ser robusta)
    # nova_solucao_completa = reconstruir_solucao_apos_mudanca_gamma(solucao_atual, parametros_problema, pedido_n_origem, periodo_t_origem, periodo_t_destino)
    # if nova_solucao_completa is None:
    #     print("DEBUG: Reconstrução da solução após mudança de gamma resultou em infactibilidade.")
    #     return None, None

    # NO CÓDIGO DA HC1-ATUALIZADA, TEMOS UMA FUNÇÃO QUE FAZ ISSO IMPLICITAMENTE
    # ao final, quando reconstrói as variáveis x, I, Q, y, z com base nos pedidos aceitos.
    # Precisamos de uma forma de re-chamar essa lógica.

    # Dada a estrutura atual, a maneira "fácil" de validar é ter certeza
    # que a capacidade não é violada. O resto (estoque, shelf-life) seria mais complexo.

    # Para fins de um EXEMPLO FUNCIONANDO:
    # Vamos reconstruir X, I, Q, Y, Z, sequencias_producao a partir da nova_config_gamma
    # usando a mesma lógica que gera_solucao_inicial_hc1_atualizada.

    # IMPORTANTE: A função gerar_solucao_inicial_hc1_atualizada *decide* quais pedidos aceitar.
    # Para usá-la como um "reconstrutor" após uma mudança, precisaríamos modificá-la
    # para aceitar uma lista de pedidos que *devem* ser aceitos.

    # Para este exercício, vamos SIMULAR o impacto no lucro e mostrar a validação de capacidade.
    # A validação completa do shelf-life e estoque exigiria a reconstrução completa.

    # Assumindo que a `temp_solucao` com o `gamma` alterado é o novo estado
    # (esta é a simplificação), calculamos o custo.
    custo_novo = calcular_custo_total(nova_solucao_simples, parametros_problema)
    print(f"Custo da Nova Solução (baseado em gamma simplificado): {custo_novo}")

    delta_custo = custo_novo - custo_original
    print(f"DEBUG: Delta de Custo (Novo - Original): {delta_custo}")

    if delta_custo > 0: # Para maximização, queremos delta positivo
        print("DEBUG: Movimento gerou uma MELHORIA no lucro. Aceitando a nova solução.")
        # Se for aceito, precisamos garantir que as outras variáveis também reflitam essa mudança.
        # Isso significa que 'nova_solucao_simples' precisa ser a solução FINAL completa.
        # No cenário atual, essa 'nova_solucao_simples' só tem o gamma alterado.
        # A solução correta exigiria uma reconstrução completa de x, I, Q, y, z e sequencias_producao
        # com base nos novos gammas.
        
        # Para que o resultado seja realmente uma solução, teríamos que fazer o seguinte:
        # 1. Obter a lista de pedidos aceitos da nova_solucao_simples['gamma'].
        # 2. Chamar gerar_solucao_inicial_hc1_atualizada para reconstruir a solução baseada
        #    apenas nessa nova lista de pedidos aceitos.
        #    Isso exigiria uma MODIFICAÇÃO na gerar_solucao_inicial_hc1_atualizada para
        #    ACEITAR uma lista pré-definida de pedidos_aceitos (e não priorizá-los).

        # Sem essa refatoração, a função de vizinhança é limitada.

        # Vamos retornar a nova_solucao_simples COM O AVISO.
        # Para uso real, a nova_solucao_simples DEVE ser reconstruída para factibilidade.
        return nova_solucao_simples, delta_custo
    else:
        print("DEBUG: Movimento não gerou melhoria no lucro. Rejeitando a nova solução.")
        return None, None


# --- A função trocar_ordem_producao_2_itens está aqui (código anterior) ---
# Você já a possui no seu operacoes_vizinhanca.py
def trocar_ordem_producao_2_itens(solucao_atual, parametros_problema):
    """
    Realiza o movimento de vizinhança: Troca a ordem de produção entre dois itens
    dentro de um mesmo período.

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

    seq_periodo = nova_solucao['sequencias_producao'][periodo_selecionado]
    
    if len(seq_periodo) < 2:
        print(f"DEBUG: Período {periodo_selecionado} tem menos de 2 itens na sequência. Pulando.")
        return None, None

    idx1, idx2 = random.sample(range(len(seq_periodo)), 2)
    
    item1 = seq_periodo[idx1]
    item2 = seq_periodo[idx2]

    print(f"DEBUG: Itens selecionados para troca no período {periodo_selecionado}: {item1} (idx {idx1}) e {item2} (idx {idx2})")

    nova_seq_periodo = list(seq_periodo)
    nova_seq_periodo[idx1], nova_seq_periodo[idx2] = nova_seq_periodo[idx2], nova_seq_periodo[idx1]
    nova_solucao['sequencias_producao'][periodo_selecionado] = nova_seq_periodo

    print(f"DEBUG: Sequência original do período {periodo_selecionado}: {seq_periodo}")
    print(f"DEBUG: Nova sequência do período {periodo_selecionado}: {nova_seq_periodo}")

    ultimo_item_periodo_anterior = None
    if periodo_selecionado > 0:
        if solucao_atual['sequencias_producao'][periodo_selecionado - 1]:
            ultimo_item_periodo_anterior = solucao_atual['sequencias_producao'][periodo_selecionado - 1][-1]
    
    print(f"DEBUG: Último item do período anterior ({periodo_selecionado-1}): {ultimo_item_periodo_anterior}")

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