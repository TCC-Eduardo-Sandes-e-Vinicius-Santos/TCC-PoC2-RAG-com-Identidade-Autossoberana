# Avaliação de Acurácia do RAG e Fidelidade ao Contexto

## Documento de teste

Usamos o próprio artigo de van Bokkem et al. (2019), "Self-Sovereign Identity Solutions: The Necessity of Blockchain Technology" como insumo de teste do RAG. Critérios para essa escolha:

- **Público e citável**: disponível no arXiv, já referenciado no TCC.
- **Curto**: 8 páginas.
- **Tematicamente relevante**: é a própria base teórica da POC2 (os 11 princípios de SSI),
  o que dá uma narrativa interessante: testar se o RAG "entende" corretamente a fundamentação
  teórica do próprio sistema.
- **Cross-lingual por natureza**: o documento está em inglês e as perguntas são feitas em português sendo um teste adicional da capacidade do modelo de embeddings multilíngue de recuperar contexto em inglês a partir de uma consulta em português.

## Protocolo

`perguntas.csv` contém 24 perguntas, divididas em 4 categorias (6 cada):

| Categoria        | O que testa                                                                         | Comportamento correto                                                                |
| ---------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `factual_direta` | resposta está literalmente em um único trecho do documento                          | responder corretamente                                                               |
| `multi_hop`      | resposta exige combinar informação de ≥2 trechos (ex.: tabela + texto de discussão) | responder corretamente, testando se `k=5` é suficiente                               |
| `termo_exato`    | números, nomes próprios, datas favorece busca lexical                               | responder corretamente, testando se o componente BM25 da busca híbrida ajuda de fato |
| `fora_de_escopo` | resposta **não está** no documento                                                  | **recusar** e indicar que não há informação suficiente                               |

`fora_de_escopo` é a categoria que mede alucinação: se o modelo responder qualquer coisa
com aparência de resposta, em vez de recusar, conta como alucinação.

## Critérios de Análise


- "1 incorreto": resposta erra um fato, mesmo que o texto pareça coerente
- "2 alucinacao": só se aplica a perguntas fora_de_escopo, ou seja o modelo
  respondeu como se soubesse, em vez de recusar
- "3 recusa_indevida": só se aplica a perguntas respondíveis, ou seja o modelo
  disse "não sei" quando a resposta estava no documento
- "4 parcial_correta": resposta acerta parte da pergunta. Atente criterio_resposta_correta de forma parcial
- "5 correto": resposta corresponde ao criterio_resposta_correta da pergunta
- "6 recusa_correta": o modelo se recusou corretamente a responder uma pergunta fora de escopo