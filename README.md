
# Otimização de Dimensionamento e Sequenciamento de Lotes com Aceitação de Pedidos e Shelf-Life

Este projeto implementa um modelo e heurísticas para resolver o problema de Dimensionamento e Sequenciamento de Lotes (Lot Sizing and Scheduling Problem - LSSP) integrado com o problema de Aceitação de Pedidos e a consideração da idade dos produtos em estoque (shelf-life). O objetivo principal é maximizar o lucro total, considerando custos de estoque e de preparação de máquina, além das restrições de perecibilidade e janelas de entrega.

## Problema Abordado

O problema central abordado neste projeto envolve:

* **Aceitação de Pedidos**: Clientes agregam demandas em pedidos, que podem ser aceitos ou rejeitados para maximizar o lucro.
* **Janelas de Entrega**: Pedidos aceitos devem ser entregues dentro de janelas de tempo específicas.
* **Produtos Perecíveis (Shelf-Life)**: Itens possuem um tempo máximo de vida em estoque.
* **Custos de Setup e Estoque**: A função objetivo considera a receita dos pedidos aceitos, descontando os custos de estoque e os custos de setup da máquina.
* **Dependência de Sequência**: Os custos e tempos de setup dependem da sequência de produção dos itens.
* **Entrega Não Parcial**: Pedidos não podem ser entregues parcialmente.

O modelo matemático baseia-se na formulação de programação inteira mista.

## Estrutura do Projeto

O projeto está organizado na seguinte estrutura de diretórios:
```
.
├── main.py
├── utils/
│   ├── calcular_custo_total.py
│   ├── carregar_parametros_otimizacao.py
│   ├── gerar_solucao_inicial.py
│   ├── gerar_solucao_inicial_hc1.py
│   ├── gerar_solucao_inicial_hc1_atualizada.py
│   └── operacoes_vizinhanca.py
├── inst0_1.txt
├── inst0_2.txt
├── inst0_3.txt
├── inst0_4.txt
└── inst0_5.txt
```
### Principais Componentes e Arquivos

* **`main.py`**: Ponto de entrada principal do programa. Carrega os parâmetros, gera uma solução inicial heurística e pode ser usado para testar movimentos de vizinhança.
* **`utils/carregar_parametros_otimizacao.py`**: Função para carregar os dados do problema a partir de arquivos de texto (`.txt`) estruturados.
* **`utils/calcular_custo_total.py`**: Calcula o valor da função objetivo (lucro líquido) para uma dada solução, somando receitas e subtraindo custos de estoque e setup.
* **`utils/gerar_solucao_inicial_hc1_atualizada.py`**: Implementa uma Heurística Construtiva 1 (HC1) atualizada para gerar uma solução inicial. Esta heurística prioriza pedidos com maior receita e tenta alocar produção e gerenciar estoque (FIFO) e `shelf-life`. Inclui uma função auxiliar `obter_sequencia_producao` para determinar sequências e tempos de setup.
* **`utils/operacoes_vizinhanca.py`**: Contém funções para realizar movimentos de vizinhança, essenciais para algoritmos de busca local (meta-heurísticas).
    * `trocar_ordem_producao_2_itens()`: Troca a ordem de produção de dois itens dentro do mesmo período.
    * `alterar_periodo_atendimento_pedido()`: Tenta mover um pedido aceito para outro período dentro de sua janela de entrega.
* **Arquivos de Instância (`inst0_1.txt`, `inst0_2.txt`, etc.)**: Contêm os dados de entrada para o problema (número de itens, períodos, pedidos, demandas, custos, tempos de setup, janelas de entrega, capacidades, etc.).

## Instalação e Execução

### Pré-requisitos

* Python 3.x
* `numpy`

Você pode instalar a dependência `numpy` usando pip:

```bash
pip install numpy

# Heurísticas e Metodologia

O projeto utiliza e desenvolve:

- **Heurística Construtiva (HC1):** Baseada na priorização de pedidos com maior receita, seguida de um planejamento de produção, sequenciamento e gestão de estoque FIFO (*First-In, First-Out*).

- **Movimentos de Vizinhança:** Operações para explorar o espaço de soluções e refinar a qualidade das soluções encontradas pela heurística construtiva. Os movimentos implementados incluem:
  - Troca de ordem de produção de itens;
  - Alteração do período de atendimento de pedidos.

## Futuras Melhorias

- Implementação de uma função robusta de **"reconstrução da solução"** para garantir a factibilidade de todas as variáveis (`x`, `I`, `Q`, `y`, `z`, `sequencias_producao`) após movimentos de vizinhança que alterem `gamma` (aceitação/período do pedido). Isso é crucial para o correto cálculo da FO e validação de restrições como *shelf-life*.

- Desenvolvimento de **meta-heurísticas** (e.g., *Simulated Annealing*, *Busca Tabu*, *GRASP*) que utilizem os movimentos de vizinhança para explorar de forma mais eficiente o espaço de soluções.

- Implementação do **terceiro movimento de vizinhança**: `trocar_status_aceitacao_pedido` (aceitar/rejeitar).

- **Testes computacionais extensivos** com diferentes classes de instâncias para avaliar o desempenho das heurísticas.

## Autores

[TBD]

## Referências

Este projeto é inspirado em trabalhos da literatura de Pesquisa Operacional, como os apresentados no LI Simpósio Brasileiro de Pesquisa Operacional (SBPO) e em artigos relacionados ao dimensionamento e sequenciamento de lotes com aceitação de pedidos e gestão de *shelf-life*.

- Barbosa, R. P., Oliveira, W. A., & Santos, M. O. (2019). *Um modelo para o problema de dimensionamento e sequenciamento de lotes com aceitação de pedidos*. LI Simpósio Brasileiro de Pesquisa Operacional.

- Teixeira, V., Oliveira, W., & Santos, M. (2017). *Um problema de dimensionamento e sequenciamento de lotes de produção com gerenciamento da demanda via pedidos e com tempos/custos de preparação dependentes da sequência*. Simpósio Brasileiro de Pesquisa Operacional.

- Li, Y., Chu, F., Yang, Z., & Calvo, R. (2016). *A production inventory routing planning for perishable food with quality consideration*. IFAC-PapersOnLine, 49(3), 407-412.
