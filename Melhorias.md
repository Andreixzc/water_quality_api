# Features  

1. Vincular a porcentagem de cobertura de nuvens a cada análise, permitindo que o front-end filtre imagens com visibilidade aceitável.  
2. Implementar a funcionalidade de empilhar múltiplas imagens processadas em camadas no mesmo mapa.  
3. Padronizar um esquema de cores distinto para cada parâmetro ao gerar mapas de intensidade.  
4. Adicionar a opção de cancelar a análise em andamento. Isso exige rastrear o status atual da análise e garantir que o cancelamento seja tratado corretamente em qualquer etapa do processo.  
5. Melhorar a visualização dos mapas, possivelmente aplicando um filtro para normalizar os valores e torná-los mais uniformes.  

## Estudo de viabilidade  

- Investigar a possibilidade de baixar as imagens em tiles localmente para evitar downloads redundantes.  

## Machine Learning  

- Iniciar a funcionalidade de análise temporal:  
  - Avaliar a melhor abordagem: considerar todos os pixels de água (excluindo nuvens) de cada imagem ou calcular a média dos valores?  

## Documentação e Modularização  

1. Melhorar o código no geral, adicionando comentários e descrições nas funções.  
2. Modularizar a porra toda, reduzindo o tamanho das funções.  
3. Escrever documentação básica para facilitar a integração com o front-end.  
4. Especificar como autenticar no EE e como pegar a chave da api do google.