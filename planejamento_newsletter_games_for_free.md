# Especificação Técnica de Software: Newsletter do Monitor de Jogos Grátis

**Data**: 01/10/2026
**Contexto**: YLuna85 LABs
**Projeto**: `monitor-jogos-gratis` (repositório `yuriluna85/games-for-free`, publicado em `https://yuriluna85.github.io/games-for-free/`)
**Versão da especificação**: 1.0.0
**Status**: aguardando revisão de Yuri Luna antes de qualquer código

---

## 1. Visão Geral e Problema Solucionado

- **Objetivo central**: permitir que visitantes do site se inscrevam com o e-mail e recebam uma newsletter sempre que o monitor encontrar um jogo grátis novo. O site continua estático no GitHub Pages. A lista de inscritos e o envio ficam com a Brevo, e o disparo parte do GitHub Actions que já roda o `monitor.py` todos os dias.
- **Público-alvo**: visitantes do site que querem ser avisados de jogos grátis sem precisar abrir a página todo dia.
- **Fora do escopo desta versão**: preferências por plataforma (só Epic, só Steam etc.), envio em tempo real (o envio acompanha a execução diária), painel de estatísticas próprio (as métricas ficam no painel da Brevo).

## 2. Arquitetura

```
Visitante -> formulário no site -> Brevo (lista, double opt-in, descadastro)
GitHub Actions (13:02) -> monitor.py -> jogos novos? -> API da Brevo -> campanha enviada à lista
```

- **GitHub Pages**: hospeda o formulário. Nenhum e-mail passa pelo repositório.
- **Brevo**: guarda os contatos, envia o e-mail de confirmação, gerencia o descadastro e envia as campanhas.
- **GitHub Actions**: roda o `monitor.py`, que compara os jogos atuais com os já anunciados e, havendo novidade, cria e dispara uma campanha pela API da Brevo.

## 3. Requisitos Funcionais (RF)

| ID | Descrição | Prioridade |
| :--- | :--- | :--- |
| **RF01** | Bloco de inscrição na página com campo de e-mail, caixa de consentimento obrigatória (LGPD) e botão "Quero receber". | Alta |
| **RF02** | O formulário envia o e-mail para a lista da Brevo usando o formulário incorporável da própria Brevo, sem chave de API exposta no navegador. | Alta |
| **RF03** | Confirmação dupla (double opt-in): o contato só entra na lista de envio depois de clicar no link de confirmação. | Alta |
| **RF04** | Mensagens na página para sucesso ("Confira seu e-mail para confirmar") e erro, anunciadas a leitores de tela (`aria-live`). | Alta |
| **RF05** | Arquivo `notificados.json` no repositório com a chave de cada oferta já anunciada e a data do anúncio. | Alta |
| **RF06** | Função no `monitor.py` que separa as ofertas novas comparando a lista atual com o `notificados.json`. | Alta |
| **RF07** | Na primeira execução (sem `notificados.json`), o script registra todas as ofertas atuais como anunciadas e não envia nada. | Alta |
| **RF08** | Havendo ofertas novas, o script cria uma campanha na Brevo com um único e-mail reunindo todas as novidades do dia e dispara o envio. | Alta |
| **RF09** | Sem ofertas novas, nenhum e-mail é enviado. | Alta |
| **RF10** | Cada item do e-mail traz título, plataforma, data de término (quando houver), imagem e link de resgate. | Média |
| **RF11** | Todo e-mail tem link de descadastro (gerado pela Brevo) e link para a Política de Privacidade. | Alta |
| **RF12** | Modo de teste (`--dry-run-newsletter`) que gera o HTML do e-mail em arquivo local sem chamar a Brevo e sem alterar o `notificados.json`. | Média |
| **RF13** | Entradas com mais de 90 dias são removidas do `notificados.json` para o arquivo não crescer sem limite. | Baixa |

### Regra de chave única da oferta (RF05 e RF06)

A chave é `plataforma + título normalizado + data de término`. Incluir a data permite anunciar de novo um jogo que volta a ficar grátis em outra promoção, sem repetir o anúncio de uma mesma promoção em dias seguidos.

### Decisões que dependem de Yuri

| ID | Decisão | Proposta padrão |
| :--- | :--- | :--- |
| **D1** | Quais ofertas entram na newsletter | Só o tipo "Jogo". Ficam de fora DLCs, emblemas, códigos e itens de jogo (a maior parte do GamerPower), que transformariam a newsletter em spam. |
| **D2** | Jogos do Prime Gaming | Entram, com aviso de que exigem assinatura Amazon Prime. |
| **D3** | Jogos futuros da Epic ("em breve") | Não entram. A newsletter só anuncia o que já pode ser resgatado. |
| **D4** | Remetente | Ver Riscos, item R1. Exige um e-mail ou domínio verificado na Brevo. |
| **D5** | Nome da lista e do remetente | Lista "Monitor de Jogos Grátis"; remetente "Monitor de Jogos Grátis (YLuna85 LABs)". |
| **D6** | Assunto do e-mail | "Jogo grátis novo: [título]" quando houver um item; "[N] jogos grátis novos hoje" quando houver mais de um. |

## 4. Requisitos Não-Funcionais (RNF)

- **Interface**: o bloco de inscrição reaproveita os tokens de cor e a tipografia já existentes no `index.html` (Dark Mode, `Outfit`). O formulário incorporável da Brevo terá o CSS padrão dela substituído pelo estilo do site. Sem sidestripe e sem emojis (Protocolos 30 e 35).
- **Responsividade**: o bloco funciona de 360px a 4K sem rolagem horizontal.
- **Acessibilidade**: `label` visível no campo de e-mail, foco visível, mensagens com `aria-live="polite"`, contraste mínimo de 7:1 no texto (Protocolo 27). Os botões A+/A- e Alto Contraste também valem para o bloco.
- **E-mail**: HTML simples em tabelas, com estilos inline, legível sem imagens e com versão em texto puro. Conteúdo em pt-BR com acentuação completa.
- **Segurança**: a chave da API da Brevo fica só no secret `BREVO_API_KEY` do GitHub e no `.env` local, que já está no `.gitignore`. O navegador nunca recebe a chave.
- **Privacidade (LGPD)**: nenhum e-mail é gravado no repositório, em logs do Actions ou no `notificados.json`.
- **Resiliência**: falha na Brevo não pode derrubar a atualização do site. O script registra o erro, não marca as ofertas como anunciadas (para tentar de novo no dia seguinte) e segue gerando o `index.html`.
- **Separação de dados (Protocolo 20)**: o `notificados.json` é dado gerado pela automação. Só o GitHub Actions o grava e o commita; testes locais usam `--dry-run-newsletter`.

## 5. Arquitetura Técnica

- **Stack**: Python 3.10 (o mesmo do workflow), `urllib` da biblioteca padrão para a API da Brevo (sem dependência nova), HTML/CSS/JS do `index.html` gerado pelo `monitor.py`.
- **API da Brevo (v3)**: criação de campanha de e-mail e disparo imediato, autenticados pelo cabeçalho `api-key`. Os endpoints e campos exatos serão conferidos na documentação oficial no momento da implementação.
- **Estrutura de arquivos afetados**:

```
monitor-jogos-gratis/
├── monitor.py                  Modificado: detecção de novidades, montagem e envio da newsletter, bloco de inscrição no HTML
├── newsletter.py               Novo: funções da Brevo e do modelo do e-mail, separadas do monitor.py
├── notificados.json            Novo (gerado pelo Actions): ofertas já anunciadas
├── privacidade.html            Modificado: coleta de e-mail, finalidade, Brevo como operadora, exclusão
├── termos.html                 Modificado: cláusula sobre a newsletter
├── .github/workflows/scrape.yml Modificado: secret BREVO_API_KEY e notificados.json no git add
├── .env                         Modificado localmente: BREVO_API_KEY (não versionado)
└── README.md                    Modificado: seção da newsletter e changelog
```

- **Novos secrets e variáveis**:
  - `BREVO_API_KEY`: chave da API da Brevo.
  - `BREVO_LIST_ID`: número da lista de contatos na Brevo.
  - `BREVO_SENDER_EMAIL` e `BREVO_SENDER_NAME`: remetente verificado.

## 6. Riscos

| ID | Risco | Tratamento |
| :--- | :--- | :--- |
| **R1** | O site não tem domínio próprio. Usar um Gmail como remetente pela Brevo tende a falhar na verificação de autenticidade (DMARC) dos provedores, e os e-mails podem cair no spam. | Opção A: usar o remetente que a Brevo oferece no plano gratuito, se houver, e testar a entrega. Opção B: registrar um domínio e autenticá-lo na Brevo. Decidir após o primeiro teste de entrega (DoD 7). |
| **R2** | Limites do plano gratuito da Brevo (envios por dia e marca da Brevo no rodapé). | Conferir os limites atuais no painel ao criar a conta. Um e-mail por dia por inscrito cabe em planos pequenos. |
| **R3** | O GitHub atrasa o agendamento de 3 a 5 horas. | A newsletter chega no mesmo dia, só que mais tarde. O disparo externo, já sugerido, resolve os dois problemas. |
| **R4** | Oferta vencida anunciada. | Depende do filtro de vencidos de 01/10/2026 estar publicado antes desta funcionalidade. |
| **R5** | Bots inscrevendo e-mails de terceiros. | O double opt-in impede envio a quem não confirmou. Se houver abuso, ativar o captcha do formulário da Brevo. |

## 7. Ordem de Implementação

1. Publicar no GitHub o filtro de vencidos e o agendamento de 13:02 (pré-requisito).
2. Configurar a conta da Brevo: lista, formulário com double opt-in, remetente e chave da API (Yuri).
3. Criar o `newsletter.py` e a detecção de novidades no `monitor.py`, com `--dry-run-newsletter`.
4. Inserir o bloco de inscrição no HTML gerado.
5. Atualizar `privacidade.html`, `termos.html`, `scrape.yml` e `README.md`.
6. Testar localmente em cópia isolada e depois com um envio real só para o e-mail de Yuri.
7. Publicar e acompanhar a primeira execução real.

## 8. Critérios de Aceite (DoD)

- [ ] 1. Inscrição pelo site gera o e-mail de confirmação, e o contato só aparece como ativo na lista depois do clique.
- [ ] 2. A primeira execução cria o `notificados.json` sem enviar e-mail.
- [ ] 3. Uma execução com oferta nova envia um único e-mail com todas as novidades; uma execução sem novidade não envia nada.
- [ ] 4. A mesma oferta não é anunciada duas vezes em dias seguidos.
- [ ] 5. Falha simulada na Brevo não impede a geração do `index.html` e não marca as ofertas como anunciadas.
- [ ] 6. O link de descadastro funciona e remove o contato da lista.
- [ ] 7. O e-mail de teste chega na caixa de entrada do Gmail de Yuri, e não no spam.
- [ ] 8. O bloco de inscrição passa em 360px, 768px e 1440px, com A+/A-, Alto Contraste e navegação por teclado.
- [ ] 9. Política de Privacidade e Termos de Uso atualizados.
- [ ] 10. Nenhum e-mail de inscrito aparece no repositório, no `notificados.json` ou nos logs do Actions.
- [ ] 11. `README.md` com a seção da newsletter, os novos secrets e o changelog.

---

Especificação elaborada por Jarbas para YLuna85 LABs.
