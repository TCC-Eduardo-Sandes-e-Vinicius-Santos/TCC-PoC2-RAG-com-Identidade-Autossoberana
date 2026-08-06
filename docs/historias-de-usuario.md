# Histórias de Usuário (US's)

## Introdução

<div align="justify">&emsp;&emsp;
As histórias de usuário são utilizadas para descrever de forma simples e objetiva as necessidades dos usuários dentro do sistema. Elas têm como foco apresentar o ponto de vista do usuário final, permitindo que a equipe de desenvolvimento compreenda claramente quais funcionalidades devem ser implementadas e qual valor será entregue. Esse método facilita a comunicação entre os envolvidos no projeto e garante que os requisitos estejam alinhados com as expectativas reais.
</div>

## Objetivo

<div align="justify">&emsp;&emsp;
O objetivo principal das histórias de usuário é registrar e organizar as funcionalidades do sistema a partir da perspectiva do usuário, promovendo clareza e priorização das entregas. Dessa forma, é possível assegurar que cada funcionalidade agregue valor, mantenha o foco no usuário final e apoie o desenvolvimento incremental e iterativo do software.
</div>

## Metodologia

<div align="justify">&emsp;&emsp;
A metodologia adotada segue o padrão ágil, onde as histórias de usuário são escritas no formato: "Como [tipo de usuário], eu quero [funcionalidade] para [benefício esperado]". Cada história é complementada por critérios de aceitação, que especificam as condições necessárias para que a entrega seja considerada concluída.
</div>

---

## Histórias

---

### US01 - Autoemitir Identidade

**Como** usuário, **quero** gerar minha própria identidade digital de forma autônoma na minha máquina **para que** eu não dependa de servidores de terceiros ou formulários web para me identificar.

#### Critérios de Aceitação

[ ] O sistema deve gerar um par de chaves criptográficas (pública e privada) localmente utilizando bibliotecas nativas.
[ ] O sistema não deve exigir o preenchimento de dados de contato (como e-mail ou telefone) nem a criação de senhas tradicionais.
[ ] O identificador descentralizado (DID) gerado deve ser salvo de forma temporária ou persistente estritamente na máquina do usuário.

---

### US02 - Verificação Biométrica Etária

**Como** usuário, **quero** comprovar minha faixa etária através da câmera do meu dispositivo **para que** eu possa acessar o assistente sem precisar compartilhar imagens de documentos oficiais de identificação.

#### Critérios de Aceitação

[ ] O sistema não deve ser acessível a menores de 18 anos.
[ ] O sistema deve ser capaz de capturar uma imagem via webcam na interface do usuário.
[ ] O sistema deve realizar a estimativa da idade rodando o modelo de visão computacional 100% localmente.
[ ] A imagem capturada deve ser descartada da memória imediatamente após a extração da alegação "maior de idade".
[ ] O sistema deve atestar o resultado associando a alegação etária ao DID gerado.

---

### US03 - Permissões do Sistema

**Como** usuário, **quero** escolher como o sistema lida com meus dados e estipular permissões **para que** se cumpra o princípio de consentimento em relação ao uso da minha identidade.

#### Critérios de Aceitação

[ ] Durante a criação da conta, o sistema deve prover um modal/tela com um formulário mostrando opções de como os dados do usuário podem ser usados.
[ ] O consentimento deve ser transformado em um documento digital e assinado criptograficamente usando a chave privada do usuário.
[ ] O sistema deve bloquear estritamente as ações da IA caso a assinatura criptográfica não seja gerada ou validada, respeitando as permissões estabelecidas.
[ ] O sistema deve respeitar as permissões estabelecidas pelo usuário.

---

### US04 - Rodar Aplicação Localmente

**Como** usuário focado em privacidade, **quero** executar toda a aplicação e os modelos de Inteligência Artificial no meu próprio computador **para que** meus dados sensíveis nunca trafeguem pela internet.

#### Critérios de Aceitação

[ ] A interface da aplicação deve ser hospedada em `localhost`.
[ ] O processamento do modelo de linguagem (LLM) deve ocorrer localmente.
[ ] Nenhuma chamada de API externa deve ser realizada para processar textos ou imagens.

---

### US05 - Assistente de IA

**Como** usuário, **quero** interagir com um assistente de IA via chat e fazer perguntas sobre meus arquivos pessoais **para que** eu obtenha respostas precisas e contextualizadas.

#### Critérios de Aceitação

[ ] O sistema deve ler e vetorizar automaticamente os documentos locais de texto apontados e armazená-los no banco vetorial local.
[ ] O fluxo de recuperação de informações (*retrieval*) só pode ser ativado caso a permissão (US03) tenha sido criptograficamente validada como "verdadeira".
[ ] O LLM local deve construir a resposta final baseando-se estritamente no conteúdo extraído do banco vetorial.

---

### US06 - Exportar Identidade

**Como** usuário, **quero** exportar minha ficha de identidade estruturada **para que** eu possa realizar o backup dos meus dados ou portar minhas permissões e comprovações etárias de forma interoperável.

#### Critérios de Aceitação

[ ] O sistema deve consolidar o DID do usuário, o termo de permissões e a alegação de maioridade em um único arquivo de texto estruturado.
[ ] O arquivo deve seguir a notação `.json` (idealmente assemelhando-se à estrutura de *Verifiable Credentials*).
[ ] A interface deve disponibilizar um botão para realizar o download direto e imediato do arquivo gerado para a máquina do usuário.

---

### US07 - Transparência do Processamento

**Como** usuário, **quero** receber avisos e explicações claras sobre como o sistema opera por baixo dos panos **para que** eu tenha transparência e segurança de que meus dados não estão sendo roubados ou armazenados indevidamente.

#### Critérios de Aceitação

[ ] A interface deve apresentar um texto explicativo claro afirmando que a imagem da webcam não será salva em disco ou enviada para a nuvem, bem como outras informações relevantes.