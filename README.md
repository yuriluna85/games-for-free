# Monitor de Jogos Grátis

Portal do YLuna85 LABs que agrega automaticamente ofertas de jogos gratuitos e com resgate temporário nas principais plataformas de distribuição digital (Epic Games, Steam, GOG, Itch.io e outras).

**Repositório**: `https://github.com/yuriluna85/games-for-free`
**Publicado em**: `https://yuriluna85.github.io/games-for-free/`
**Contexto de marca**: YLuna85 LABs
**Autor**: Yuri Almeida

---

## Estrutura de Arquivos

```
monitor-jogos-gratis/
├── index.html                 Página única, gerada automaticamente por monitor.py
├── privacidade.html            Política de Privacidade (LGPD)
├── termos.html                 Termos de Uso
├── robots.txt, sitemap.xml     Arquivos de indexação SEO
├── favicon.png                 Favicon oficial
├── monitor.py                  Script principal: coleta, traduz e monta o index.html
├── games.json                  Base de ofertas ativas (consumida/gerada por monitor.py)
├── games_data.csv               Histórico de ofertas em formato tabular
├── games_metrics.json           Métricas de execução do monitor
├── prime_games.json             Ofertas específicas do Amazon Prime Gaming
├── requirements_cache.json      Cache de traduções e metadados (evita recomputar a cada execução)
├── requirements.txt             Dependências Python
├── agendar_tarefa.ps1           Script de agendamento local (Windows Task Scheduler)
├── .github/workflows/scrape.yml Automação diária via GitHub Actions
├── .env                         Chaves de API locais (SERPER_API_KEY, SCRAPERAPI_KEY) — NUNCA versionar
└── harness.py                   Suíte de autoteste do projeto
```

**Importante**: `games.json`, `games_data.csv`, `games_metrics.json`, `prime_games.json` e `requirements_cache.json` são gerados e commitados automaticamente pelo workflow do GitHub Actions a cada execução (ver `.github/workflows/scrape.yml`). Não são resíduos: fazem parte do pipeline de dados do projeto e não devem ser removidos da raiz.

---

## Pipeline de Coleta Automatizada

O workflow `.github/workflows/scrape.yml` está agendado para 16:02 UTC (13:02 horário de Brasília) e também pode ser disparado manualmente (`workflow_dispatch`). O GitHub não garante o horário do agendamento: entre 26/09 e 30/09/2026 as execuções começaram entre 15:49 e 18:27 de Brasília.

1. Executa `python monitor.py`, que varre as plataformas de jogos, traduz descrições para pt-BR e monta o `index.html` estático.
2. Usa as chaves `SERPER_API_KEY` e `SCRAPERAPI_KEY` como *secrets* do repositório GitHub (nunca hardcoded no código).
3. Faz commit e push automático de `index.html` e dos arquivos de dados, se houver alteração.

Para rodar localmente, crie um arquivo `.env` na raiz do projeto com:
```
SERPER_API_KEY=sua_chave_aqui
SCRAPERAPI_KEY=sua_chave_aqui
```
e execute `python monitor.py`. O arquivo `.env` está listado no `.gitignore` e nunca deve ser publicado.

---

## Acessibilidade e Conformidade Legal

- Barra de acessibilidade (`A+`/`A-`/Alto Contraste) no topo da página, com persistência em `localStorage`.
- Banner de consentimento de cookies (LGPD/GDPR), informando o uso de `localStorage` e a incorporação de conteúdo de terceiros (Google Fonts, Font Awesome, imagens hospedadas pelas próprias plataformas de jogos).
- Páginas `privacidade.html` e `termos.html`, linkadas no rodapé.

---

## Execução Local

- Atalho: `EXECUTAR_MONITOR-JOGOS-GRATIS.bat` (Windows).
- Agendamento local alternativo: `agendar_tarefa.ps1` (Windows Task Scheduler).
- Suíte de autoteste: `python harness.py`.

---

## Changelog

### 01/10/2026
- **Ofertas vencidas deixam de aparecer**:
  - GamerPower: a API mantém como `Active` sorteios com data de término já vencida (ex.: 2020 e maio/2026). Agora o `monitor.py` descarta todo sorteio cujo `end_date` já passou.
  - Lista manual do Prime (`prime_games.json`): cada entrada precisa do campo `"expira_em": "AAAA-MM-DD"`. Entradas sem esse campo ou vencidas não são exibidas. As 18 entradas existentes, de junho/2026, ficaram de fora por não terem validade.
  - Links da busca web: um link some quando não reaparece na busca por mais de 7 dias (`LINK_MAX_AGE_DAYS`). O campo `last_seen` é renovado quando o link é reencontrado.
  - Página: cada card leva a data de término em `data-end`, e um script remove da tela, a cada minuto, as ofertas que venceram depois da última coleta.
- Agendamento alterado de 13:01 para 13:02 (horário de Brasília), com `cron: '2 16 * * *'`.
- A mensagem do commit automático passa a usar o horário de Brasília (antes mostrava UTC, o que dava a impressão de execução às 16h).

### 27/09/2026
- **Correção de segurança**: o arquivo `.env` (contendo `SERPER_API_KEY` e `SCRAPERAPI_KEY` reais) não estava listado no `.gitignore` deste projeto. Adicionado `.env` e `.env.*` ao `.gitignore` para impedir que as chaves sejam publicadas em um futuro commit. Nenhuma chave foi exposta ou alterada nesta correção; apenas a proteção contra versionamento futuro foi adicionada.
- Adicionadas tags de SEO (`description`, `robots`, `canonical`, Open Graph) e o favicon oficial ao `<head>` de `index.html`, que não tinha nenhum dos dois.
- Corrigidos `canonical`/`og:url` para o endereço real de publicação (`https://yuriluna85.github.io/games-for-free/`), já que o projeto não possui `CNAME` de domínio próprio.
- Criados `robots.txt` e `sitemap.xml` (o projeto não tinha nenhum dos dois).
- Adicionada barra de acessibilidade (A+/A-/Alto Contraste), que não existia em nenhuma versão anterior do site.
- Implementado banner de consentimento de cookies (LGPD/GDPR), com persistência em `localStorage` (chave `cookieConsentMonitorJogos`).
- Criadas as páginas `privacidade.html` e `termos.html`, linkadas no rodapé.
- Reescrito integralmente este `README.md`, que estava corrompido (acentuação removida em toda a extensão do arquivo).
- **Fora de escopo nesta rodada**: o `index.html` (mais de 3.300 linhas) mantém CSS e JavaScript embutidos. A extração para arquivos externos (`style.css`/`script.js`) não foi feita nesta sessão por segurança (arquivo gerado automaticamente pelo `monitor.py`; separar os arquivos exigiria também adaptar o gerador em `monitor.py`, o que fica registrado como pendência para uma rodada dedicada).
