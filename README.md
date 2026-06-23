# 🎮 Monitor e Indexador de Jogos Grátis

Este repositório contém uma aplicação automatizada para monitorar, buscar e indexar ofertas de jogos gratuitos em lojas como **Steam, Epic Games Store, GOG** e outros portais da internet. A página principal é gerada estaticamente e foi projetada para ser hospedada diretamente no **GitHub Pages**.

---

## 📂 Estrutura do Repositório (Esqueleto GitHub)

O projeto segue a estrutura padrão de repositórios do GitHub com automação via GitHub Actions:

```
├── .github/
│   └── workflows/
│       └── scrape.yml      # Workflow que roda o script diariamente às 13:01
├── .gitignore              # Arquivos ignorados pelo Git (caches e arquivos de SO)
├── README.md               # Documentação do projeto (este arquivo)
├── requirements.txt        # Dependências de bibliotecas Python
├── monitor.py              # Script principal do scraper e indexador
├── games.json              # Banco de dados JSON com histórico dos links indexados
├── index.html              # Dashboard estático gerado automaticamente
└── agendar_tarefa.ps1      # Script PowerShell para agendar execução local no Windows
```

---

## ⚡ Como Funciona a Indexação Diária

A indexação dos portais de jogos gratuitos é realizada de duas formas complementares:

### 1. APIs e Scraping Direto (Lojas Oficiais)
* O script consome a API da **Epic Games Store** para recuperar jogos gratuitos ativos e futuros.
* Consome a API do **GamerPower** para filtrar e obter ofertas ativas da Steam, GOG, Itch.io e Ubisoft Store.

### 2. Busca e Indexação na Web (Google, Bing e Fallbacks)
* Diariamente, o script realiza buscas utilizando os índices de busca do Google e Bing (via requisições web seguras de Yahoo e DuckDuckGo) com queries especializadas para identificar portais, novos artigos e links promocionais ativos.
* Novos links descobertos são comparados e adicionados de forma incremental ao arquivo `games.json`, mantendo um histórico atualizado das últimas 50 ofertas e portais válidos da internet.

---

## 🤖 Automação no GitHub Pages e GitHub Actions

Como a aplicação será publicada no **GitHub Pages**, o fluxo de atualização é 100% automatizado através do arquivo `.github/workflows/scrape.yml`:

1. **Agendamento (Cron):** O workflow está programado para disparar todos os dias às **13:01 no horário de Brasília** (`16:01 UTC`).
2. **Execução:** O GitHub Actions ativa uma máquina virtual temporária, instala o Python, instala as dependências do `requirements.txt` e roda o script `monitor.py`.
3. **Indexação e Geração:** O script busca as ofertas, atualiza o arquivo de histórico `games.json` e gera o novo painel `index.html`.
4. **Deploy Automático:** O bot do GitHub faz o commit e push das alterações diretamente de volta para o repositório. O GitHub Pages atualiza o site estático instantaneamente!

---

## 💻 Execução Local (Windows)

Você também pode rodar e agendar a execução do script localmente no seu computador.

### Instalação de Dependências
Abra o terminal na pasta do projeto e instale as bibliotecas necessárias:
```bash
pip install -r requirements.txt
```

### Rodar Manualmente
```bash
python monitor.py
```

### Agendador Local (Windows Task Scheduler)
Para configurar seu computador para rodar o indexador automaticamente todos os dias às **13:01** (localmente), clique com o botão direito no arquivo `agendar_tarefa.ps1` e selecione **"Executar com o PowerShell"** (ou execute via terminal PowerShell do Administrador).

---

## 🎨 Recursos Visuais do Dashboard
O arquivo `index.html` gerado de forma estática conta com:
* **Dark Mode** nativo com gradientes vibrantes em tons de roxo e ciano.
* **Glassmorphism** nos cartões de jogos e painel de controle.
* **Filtros Dinâmicos** por plataforma (Steam, Epic, GOG) e caixa de pesquisa por título de jogo em tempo real.
* **Seção de Links Indexados**: Exibe os links dinâmicos e artigos de ofertas encontrados pelas buscas web do Google e Bing.
