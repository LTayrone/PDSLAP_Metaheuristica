import numpy as np

def carregar_parametros_otimizacao(caminho_arquivo):
    """
    Carrega todos os parâmetros do problema de otimização de produção a partir de um arquivo estruturado.
    """
    with open(caminho_arquivo) as arquivo:
        num_itens, num_periodos, num_pedidos = map(int, arquivo.readline().split())

        demanda_pedidos = np.fromfile(arquivo, dtype=int, count=num_pedidos*num_itens, sep=" ")
        demanda_pedidos = demanda_pedidos.reshape((num_pedidos, num_itens))

        dados_setup = np.fromfile(arquivo, dtype=int, count=num_itens*num_itens*2, sep=" ")
        dados_setup = dados_setup.reshape((num_itens, num_itens, 2))
        custo_setup = dados_setup[:, :, 0]
        tempo_setup = dados_setup[:, :, 1]

        janelas_entrega = np.fromfile(arquivo, dtype=int, count=num_pedidos*2, sep=" ")
        janelas_entrega = janelas_entrega.reshape((num_pedidos, 2))
        periodo_inicial_entrega = janelas_entrega[:, 0]
        periodo_final_entrega = janelas_entrega[:, 1]

        capacidade_periodo = np.fromfile(arquivo, dtype=int, count=num_periodos, sep=" ")

        tempo_producao = np.fromfile(arquivo, dtype=int, count=num_itens, sep=" ")
        custo_estoque = np.fromfile(arquivo, dtype=int, count=num_itens, sep=" ")

        receita_pedido = np.fromfile(arquivo, dtype=int, count=num_pedidos*num_periodos, sep=" ")
        receita_pedido = receita_pedido.reshape((num_pedidos, num_periodos))

        vida_util = np.fromfile(arquivo, dtype=int, count=num_itens, sep=" ")

    parametros = {
        'num_itens': num_itens,
        'num_periodos': num_periodos,
        'num_pedidos': num_pedidos,
        'demanda_pedidos': demanda_pedidos,
        'custo_setup': custo_setup,
        'tempo_setup': tempo_setup,
        'periodo_inicial_entrega': periodo_inicial_entrega,
        'periodo_final_entrega': periodo_final_entrega,
        'capacidade_periodo': capacidade_periodo,
        'tempo_producao': tempo_producao,
        'custo_estoque': custo_estoque,
        'receita_pedido': receita_pedido,
        'vida_util': vida_util
    }
    return parametros