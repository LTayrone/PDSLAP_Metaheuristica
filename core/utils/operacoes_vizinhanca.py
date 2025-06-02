# operacoes_vizinhanca.py

import copy
import random
import numpy as np

# Assumimos que a função de carregar_parametros_otimizacao.py
# e calcular_custo_total.py já estão definidas e acessíveis
# Importar os módulos do seu projeto conforme a estrutura
from utils.carregar_parametros_otimizacao import carregar_parametros_otimizacao
from utils.calcular_custo_total import calcular_custo_total
# Se 'obter_sequencia_producao' for usada aqui, também precisa ser importada ou definida
from utils.gerar_solucao_inicial_hc1_atualizada import obter_sequencia_producao # Importar a função auxiliar

class Solucao:
    """
    Representa uma solução para o problema PDSLAP.
    Os dados da solução são armazenados internamente como um dicionário.
    """
    def __init__(self, parametros_otimizacao, dados_solucao_dict):
        self.parametros = parametros_otimizacao
        # Armazena o dicionário completo de dados da solução
        self.dados = copy.deepcopy(dados_solucao_dict)
        
        # Calcula o custo inicial
        self.custo_total = self.calcular_custo()

    def calcular_custo(self):
        # Passa o dicionário de dados completo da solução diretamente
        return calcular_custo_total(self.parametros, self.dados)

    def __lt__(self, other):
        # Permite comparar soluções (útil para encontrar a melhor na vizinhança)
        return self.custo_total < other.custo_total

    def __repr__(self):
        return f"Solucao(Custo: {self.custo_total})"


def _criar_nova_solucao_copia(solucao_original):
    """Cria uma cópia profunda da solução para modificação."""
    return Solucao(solucao_original.parametros, solucao_original.dados)

def trocar_aceitacao_pedido(solucao_original):
    """
    Troca a aceitação de um pedido aleatório em um período aleatório (γnt de 0 para 1 ou vice-versa).
    """
    nova_solucao = _criar_nova_solucao_copia(solucao_original)
    parametros = nova_solucao.parametros

    n_pedidos = parametros['num_pedidos']
    n_periodos = parametros['num_periodos']

    # Escolher um pedido e um período aleatórios
    pedido_idx = random.randrange(n_pedidos)
    periodo_idx = random.randrange(n_periodos)

    # Inverte a aceitação do pedido no período
    nova_solucao.dados['gamma'][pedido_idx][periodo_idx] = 1 - nova_solucao.dados['gamma'][pedido_idx][periodo_idx]

    # Re-calcula o custo da nova solução
    nova_solucao.custo_total = nova_solucao.calcular_custo()
    return nova_solucao

def alterar_quantidade_produzida(solucao_original, max_delta_percent=0.1):
    """
    Altera a quantidade produzida de um item em um período.
    A alteração é um valor aleatório dentro de +/- max_delta_percent da quantidade atual.
    Garante que a quantidade não seja negativa.
    """
    nova_solucao = _criar_nova_solucao_copia(solucao_original)
    parametros = nova_solucao.parametros

    n_itens = parametros['num_itens']
    n_periodos = parametros['num_periodos']

    item_idx = random.randrange(n_itens)
    periodo_idx = random.randrange(n_periodos)

    quantidade_atual = nova_solucao.dados['x'][item_idx][periodo_idx]
    
    if quantidade_atual == 0:
        delta = random.randint(1, 10) # Tenta adicionar uma pequena quantidade se a produção for zero
    else:
        max_delta_valor = max(1, int(quantidade_atual * max_delta_percent))
        delta = random.randint(-max_delta_valor, max_delta_valor)

    nova_quantidade = quantidade_atual + delta

    # Garante que a quantidade não seja negativa
    nova_solucao.dados['x'][item_idx][periodo_idx] = max(0, nova_quantidade)

    nova_solucao.custo_total = nova_solucao.calcular_custo()
    return nova_solucao

def trocar_ordem_producao(solucao_original):
    """
    Troca a ordem de produção entre dois itens dentro do mesmo período.
    Escolhe um período aleatório e dois itens aleatórios para trocar a posição
    no array `sequencias_producao`.
    """
    nova_solucao = _criar_nova_solucao_copia(solucao_original)
    parametros = nova_solucao.parametros

    n_periodos = parametros['num_periodos']
    
    # Tenta encontrar um período com pelo menos 2 itens para troca
    periodos_com_producao = [t for t, seq in enumerate(nova_solucao.dados['sequencias_producao']) if len(seq) >= 2]

    if not periodos_com_producao:
        return solucao_original # Retorna a solução original se nenhuma troca for possível

    periodo_idx = random.choice(periodos_com_producao)

    sequenciamento_periodo = nova_solucao.dados['sequencias_producao'][periodo_idx]
    
    idx1, idx2 = random.sample(range(len(sequenciamento_periodo)), 2)

    # Troca os itens de posição
    sequenciamento_periodo[idx1], sequenciamento_periodo[idx2] = \
        sequenciamento_periodo[idx2], sequenciamento_periodo[idx1]

    # Re-calcula as variáveis de setup (y e z) com base na nova sequência
    _atualizar_variaveis_setup(nova_solucao)

    nova_solucao.custo_total = nova_solucao.calcular_custo()
    return nova_solucao

def realocar_producao_adjacente(solucao_original, max_transferencia_percent=0.2):
    """
    Realoca uma quantidade de produção de um item de um período para um período adjacente.
    Escolhe um item e um período (exceto o último) aleatoriamente,
    e tenta mover uma quantidade de produção para o período seguinte.
    """
    nova_solucao = _criar_nova_solucao_copia(solucao_original)
    parametros = nova_solucao.parametros

    n_itens = parametros['num_itens']
    n_periodos = parametros['num_periodos']

    if n_periodos < 2: # Precisa de pelo menos 2 períodos para realocação adjacente
        return solucao_original

    item_idx = random.randrange(n_itens)
    periodo_origem_idx = random.randrange(n_periodos - 1) # Não pode ser o último período

    periodo_destino_idx = periodo_origem_idx + 1

    quantidade_origem = nova_solucao.dados['x'][item_idx][periodo_origem_idx]
    
    if quantidade_origem == 0:
        return solucao_original # Nada para transferir

    # Quantidade máxima a ser transferida (mínimo entre a produção atual e % da produção)
    quantidade_transferir = random.randint(1, max(1, int(quantidade_origem * max_transferencia_percent)))

    if quantidade_transferir > 0:
        nova_solucao.dados['x'][item_idx][periodo_origem_idx] -= quantidade_transferir
        nova_solucao.dados['x'][item_idx][periodo_destino_idx] += quantidade_transferir
    else:
        return solucao_original # Retorna a solução original se nada foi realocado

    nova_solucao.custo_total = nova_solucao.calcular_custo()
    return nova_solucao

def _atualizar_variaveis_setup(solucao):
    """
    Função auxiliar para atualizar as variáveis y (setup) e z (troca de setup)
    com base na `sequencias_producao` de uma solução.
    Esta função deve ser chamada após qualquer alteração no sequenciamento.
    """
    parametros = solucao.parametros
    num_itens = parametros['num_itens']
    num_periodos = parametros['num_periodos']

    # Reinicializa y e z para a solução atual
    solucao.dados['y'] = np.zeros((num_itens, num_periodos), dtype=int)
    solucao.dados['z'] = np.zeros((num_itens, num_itens, num_periodos), dtype=int)

    for t in range(num_periodos):
        sequencia_periodo = solucao.dados['sequencias_producao'][t]
        
        if sequencia_periodo:
            # Atualiza y
            for item_id in sequencia_periodo:
                solucao.dados['y'][item_id][t] = 1
            
            # Atualiza z
            if len(sequencia_periodo) > 1:
                for i in range(len(sequencia_periodo) - 1):
                    item_prev = sequencia_periodo[i]
                    item_curr = sequencia_periodo[i+1]
                    solucao.dados['z'][item_prev][item_curr][t] = 1
            
            # Lógica para o primeiro item no período e setup inicial (se necessário pelo seu modelo)
            # Você precisaria de um 'ultimo_item_produzido_no_periodo_anterior' para este cálculo
            # e a matriz de tempo_setup. Por simplicidade, assumo que obter_sequencia_producao
            # já lida com o setup inicial para o cálculo de tempo de setup total.
            # Aqui, para a variável 'z', se o primeiro item da sequência depende do último item
            # do período anterior, uma variável auxiliar ou uma re-reconstrução de z[anterior][primeiro][t]
            # seria necessária.
            # O exemplo do gerar_solucao_inicial_hc1_atualizada.py usa `ultimo_item_produzido_no_periodo[t_reconstrucao - 1]`
            # para o `obter_sequencia_producao`, o que afeta o setup.
            # Aqui, dentro de `_atualizar_variaveis_setup`, estamos apenas reconstruindo `y` e `z` com base
            # na `sequencias_producao` atual. Se a `sequencias_producao` já foi ajustada para refletir
            # o setup inicial do período (dependendo do último item do período anterior), então está ok.
            # Se não, essa função só trata os setups *intra-período*.
            
            # Para uma atualização completa e consistente de `y` e `z` que considere o `ultimo_item_produzido_no_periodo`
            # de período a período, seria necessário que esta função recebesse essa informação
            # ou que a lógica de atualização fosse um pouco mais complexa para iterar sobre os períodos
            # e manter o estado do último item produzido.

            # Por enquanto, mantendo a consistência com o que o `trocar_ordem_producao` necessita.
            # A função `obter_sequencia_producao` (que é usada na heurística construtiva)
            # já considera o `ultimo_item_anterior` para o cálculo do tempo de setup.
            # Para a variável `z` em si, você precisa garantir que ela capture as transições corretas.

            # Adicionalmente, você pode precisar de uma variável `ultimo_item_produzido_no_periodo`
            # dentro da classe Solucao ou ser passada para _atualizar_variaveis_setup
            # para recriar o z[i][j][t] quando j é o primeiro item no período t e i é o último em t-1.
            # No entanto, a forma como o `gerar_solucao_inicial_hc1_atualizada` recalcula 'y' e 'z'
            # no final do loop principal sugere que o 'z' só é para setup intra-período.

            # A implementação atual de _atualizar_variaveis_setup é consistente com o modelo padrão
            # de z_ijt onde i é produzido *imediatamente antes* de j no período t.
            # A menos que seu modelo tenha uma variável de setup *entre* períodos que
            # também seja representada por `z`. Se for esse o caso, o `gerar_solucao_inicial_hc1_atualizada`
            # já faz essa atribuição e a lógica `_atualizar_variaveis_setup` precisaria ser mais complexa.