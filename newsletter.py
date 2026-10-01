# -*- coding: utf-8 -*-
"""
newsletter.py - Newsletter de jogos gratis novos do Monitor de Jogos Gratis (via Brevo).
Autor: Yuri Luna (YLuna85 LABs)

Fluxo: o monitor.py entrega a lista de ofertas ativas; este modulo separa os jogos
completos ainda nao anunciados (comparando com notificados.json), monta um unico
e-mail com as novidades do dia e dispara uma campanha para a lista da Brevo.
Fora do GitHub Actions o envio fica desligado e so a previa em HTML e gerada.
"""

from __future__ import annotations

import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_NOTIFICADOS = os.path.join(BASE_DIR, "notificados.json")
ARQUIVO_PREVIA = os.path.join(BASE_DIR, "newsletter_previa.html")

BREVO_API_URL = "https://api.brevo.com/v3"
# O Cloudflare da Brevo bloqueia o User-Agent padrao do urllib (erro 1010)
USER_AGENT = "MonitorJogosGratis/1.0 (YLuna85 LABs)"
SITE_URL = "https://yuriluna85.github.io/games-for-free/"
LISTA_PADRAO = 3
REMETENTE_NOME_PADRAO = "Monitor de Jogos Grátis (YLuna85 LABs)"
DIAS_RETENCAO = 90
IMAGEM_PADRAO = "https://images.unsplash.com/photo-1550745165-9bc0b252726f?q=80&w=600&auto=format&fit=crop"


class ErroBrevo(Exception):
    """Falha de configuracao ou de resposta da API da Brevo."""


# ---------------------------------------------------------------------------
# Selecao das ofertas
# ---------------------------------------------------------------------------

def chave_oferta(jogo: Dict[str, Any]) -> str:
    """Identifica uma promocao: plataforma + titulo normalizado + data de termino."""
    titulo = re.sub(r"\s+", " ", str(jogo.get("title", ""))).strip().lower()
    plataforma = str(jogo.get("platform", "")).strip().lower()
    termino = str(jogo.get("end_date", "")).strip()
    return f"{plataforma}|{titulo}|{termino}"


def eh_elegivel(jogo: Dict[str, Any]) -> bool:
    """Decisao D1: so jogos completos; DLCs, codigos e itens ficam de fora."""
    return str(jogo.get("type", "")).strip().lower() == "jogo"


def eh_prime(jogo: Dict[str, Any]) -> bool:
    """Decisao D2: jogos do Prime Gaming entram com aviso de assinatura."""
    return str(jogo.get("platform", "")).strip().lower().startswith("prime gaming")


def carregar_notificados() -> Optional[Dict[str, Dict[str, str]]]:
    """Retorna as ofertas ja anunciadas, ou None se o arquivo ainda nao existir."""
    if not os.path.exists(ARQUIVO_NOTIFICADOS):
        return None
    try:
        with open(ARQUIVO_NOTIFICADOS, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Newsletter: notificados.json ilegível ({e}); será recriado sem envio.", file=sys.stderr)
        return None
    ofertas = dados.get("ofertas", {}) if isinstance(dados, dict) else {}
    return ofertas if isinstance(ofertas, dict) else {}


def salvar_notificados(ofertas: Dict[str, Dict[str, str]]) -> None:
    """Grava notificados.json descartando anuncios com mais de DIAS_RETENCAO dias."""
    limite = (datetime.now() - timedelta(days=DIAS_RETENCAO)).strftime("%Y-%m-%d")
    mantidas = {k: v for k, v in ofertas.items() if v.get("anunciado_em", "") >= limite}
    with open(ARQUIVO_NOTIFICADOS, "w", encoding="utf-8") as f:
        json.dump({"versao": 1, "ofertas": mantidas}, f, indent=2, ensure_ascii=False)


def registrar(ofertas: Dict[str, Dict[str, str]], jogos: List[Dict[str, Any]]) -> None:
    """Marca as ofertas como anunciadas hoje."""
    hoje = datetime.now().strftime("%Y-%m-%d")
    for jogo in jogos:
        ofertas[chave_oferta(jogo)] = {
            "titulo": str(jogo.get("title", "")),
            "plataforma": str(jogo.get("platform", "")),
            "anunciado_em": hoje,
        }


def selecionar_novidades(jogos: List[Dict[str, Any]], ofertas: Dict[str, Dict[str, str]]) -> List[Dict[str, Any]]:
    """Devolve as ofertas elegiveis que ainda nao foram anunciadas, sem repeticao."""
    novos: List[Dict[str, Any]] = []
    vistos = set(ofertas)
    for jogo in jogos:
        chave = chave_oferta(jogo)
        if eh_elegivel(jogo) and chave not in vistos:
            vistos.add(chave)
            novos.append(jogo)
    return novos


# ---------------------------------------------------------------------------
# Conteudo do e-mail
# ---------------------------------------------------------------------------

def montar_assunto(novos: List[Dict[str, Any]]) -> str:
    """Decisao D6: assunto com o titulo quando ha um jogo, ou com a contagem."""
    if len(novos) == 1:
        return f"Jogo grátis novo: {novos[0].get('title', '')}"
    return f"{len(novos)} jogos grátis novos hoje"


def _bloco_jogo(jogo: Dict[str, Any]) -> str:
    titulo = html.escape(str(jogo.get("title", "")))
    plataforma = html.escape(str(jogo.get("platform", "")))
    termino = html.escape(str(jogo.get("end_date", "")))
    url = html.escape(str(jogo.get("url") or SITE_URL), quote=True)
    imagem = html.escape(str(jogo.get("image") or IMAGEM_PADRAO), quote=True)
    aviso_prime = ""
    if eh_prime(jogo):
        aviso_prime = (
            '<p style="margin:8px 0 0;padding:8px 10px;background:#fff4e5;color:#7a4100;'
            'border-radius:6px;font-size:13px;line-height:1.5;">'
            "Exige assinatura do Amazon Prime para resgatar e jogar.</p>"
        )
    return f"""
          <tr>
            <td style="padding:0 0 24px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e3e5ec;border-radius:10px;overflow:hidden;">
                <tr><td><img src="{imagem}" alt="{titulo}" width="560" style="display:block;width:100%;max-width:560px;height:auto;border:0;"></td></tr>
                <tr>
                  <td style="padding:16px 18px 18px;font-family:Arial,Helvetica,sans-serif;color:#1d2030;">
                    <p style="margin:0 0 4px;font-size:12px;letter-spacing:0.06em;text-transform:uppercase;color:#5b5f73;">{plataforma}</p>
                    <h2 style="margin:0 0 8px;font-size:20px;line-height:1.3;color:#1d2030;">{titulo}</h2>
                    <p style="margin:0;font-size:14px;color:#3b3f52;">Disponível até: {termino}</p>
                    {aviso_prime}
                    <p style="margin:16px 0 0;"><a href="{url}" style="display:inline-block;background:#5b2fd6;color:#ffffff;text-decoration:none;font-weight:bold;font-size:15px;padding:11px 20px;border-radius:8px;">Resgatar</a></p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>"""


def montar_html_email(novos: List[Dict[str, Any]]) -> str:
    """E-mail em tabelas com estilo inline, legivel tambem com imagens bloqueadas."""
    data = datetime.now().strftime("%d/%m/%Y")
    resumo = html.escape(montar_assunto(novos))
    blocos = "".join(_bloco_jogo(j) for j in novos)
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{resumo}</title></head>
<body style="margin:0;padding:0;background:#f2f3f7;">
  <span style="display:none;max-height:0;overflow:hidden;">{resumo}. Confira antes que a promoção acabe.</span>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f2f3f7;">
    <tr>
      <td align="center" style="padding:24px 12px;">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:100%;max-width:600px;background:#ffffff;border-radius:12px;">
          <tr>
            <td style="padding:28px 20px 8px;font-family:Arial,Helvetica,sans-serif;color:#1d2030;">
              <p style="margin:0 0 6px;font-size:12px;letter-spacing:0.06em;text-transform:uppercase;color:#5b5f73;">Monitor de Jogos Grátis, {data}</p>
              <h1 style="margin:0 0 8px;font-size:24px;line-height:1.3;">{resumo}</h1>
              <p style="margin:0 0 20px;font-size:15px;line-height:1.6;color:#3b3f52;">As promoções mudam sem aviso. Confirme o preço na loja antes de resgatar.</p>
            </td>
          </tr>
          <tr>
            <td style="padding:0 20px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{blocos}
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:8px 20px 28px;font-family:Arial,Helvetica,sans-serif;font-size:13px;line-height:1.6;color:#5b5f73;">
              <p style="margin:0 0 8px;">Lista completa, com DLCs e brindes, em <a href="{SITE_URL}" style="color:#5b2fd6;">yuriluna85.github.io/games-for-free</a>.</p>
              <p style="margin:0 0 8px;">Você recebe este e-mail porque confirmou a inscrição no Monitor de Jogos Grátis (YLuna85 LABs). <a href="{{{{ unsubscribe }}}}" style="color:#5b2fd6;">Cancelar inscrição</a>.</p>
              <p style="margin:0;"><a href="{SITE_URL}privacidade.html" style="color:#5b2fd6;">Política de Privacidade</a></p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Brevo
# ---------------------------------------------------------------------------

def _config_brevo() -> Dict[str, Any]:
    """Le chave, lista e remetente das variaveis de ambiente; erro se faltar algo."""
    chave = os.getenv("BREVO_API_KEY", "").strip()
    remetente = os.getenv("BREVO_SENDER_EMAIL", "").strip()
    if not chave:
        raise ErroBrevo("BREVO_API_KEY não configurada.")
    if not remetente:
        raise ErroBrevo("BREVO_SENDER_EMAIL não configurado.")
    lista_txt = os.getenv("BREVO_LIST_ID", "").strip() or str(LISTA_PADRAO)
    if not lista_txt.isdigit():
        raise ErroBrevo(f"BREVO_LIST_ID inválido: '{lista_txt}'.")
    return {
        "chave": chave,
        "lista": int(lista_txt),
        "remetente_email": remetente,
        "remetente_nome": os.getenv("BREVO_SENDER_NAME", "").strip() or REMETENTE_NOME_PADRAO,
    }


def _requisicao_brevo(metodo: str, caminho: str, chave: str, corpo: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Chama a API v3 da Brevo e devolve o JSON da resposta (vazio em 204)."""
    dados = json.dumps(corpo).encode("utf-8") if corpo is not None else None
    req = urllib.request.Request(
        BREVO_API_URL + caminho,
        data=dados,
        method=metodo,
        headers={
            "api-key": chave,
            "accept": "application/json",
            "content-type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            texto = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detalhe = e.read().decode("utf-8", "replace")[:300]
        raise ErroBrevo(f"HTTP {e.code} em {metodo} {caminho}: {detalhe}") from e
    return json.loads(texto) if texto.strip() else {}


def contar_inscritos(config: Dict[str, Any]) -> int:
    """Numero de contatos da lista; a Brevo recusa criar campanha para lista vazia."""
    lista = _requisicao_brevo("GET", f"/contacts/lists/{config['lista']}", config["chave"])
    return int(lista.get("uniqueSubscribers") or lista.get("totalSubscribers") or 0)


def criar_campanha(config: Dict[str, Any], assunto: str, html_email: str) -> int:
    """Cria a campanha (rascunho) para a lista e devolve o id."""
    resposta = _requisicao_brevo("POST", "/emailCampaigns", config["chave"], {
        "name": f"Jogos grátis novos {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "subject": assunto,
        "sender": {"name": config["remetente_nome"], "email": config["remetente_email"]},
        "htmlContent": html_email,
        "recipients": {"listIds": [config["lista"]]},
    })
    id_campanha = resposta.get("id")
    if not isinstance(id_campanha, int):
        raise ErroBrevo(f"Resposta sem id de campanha: {resposta}")
    return id_campanha


def enviar_campanha(config: Dict[str, Any], assunto: str, html_email: str) -> int:
    """Cria a campanha e dispara o envio imediato; devolve o id."""
    id_campanha = criar_campanha(config, assunto, html_email)
    _requisicao_brevo("POST", f"/emailCampaigns/{id_campanha}/sendNow", config["chave"])
    return id_campanha


# ---------------------------------------------------------------------------
# Orquestracao
# ---------------------------------------------------------------------------

def gravar_previa(html_email: str) -> None:
    with open(ARQUIVO_PREVIA, "w", encoding="utf-8") as f:
        f.write(html_email)
    print(f"Newsletter: prévia gravada em {ARQUIVO_PREVIA}")


def processar_newsletter(jogos_atuais: List[Dict[str, Any]], enviar: bool) -> None:
    """
    Separa as novidades e envia a newsletter. Com enviar=False so grava a previa e
    nao altera notificados.json. Falhas da Brevo nunca interrompem o monitor.
    """
    elegiveis = [j for j in jogos_atuais if eh_elegivel(j)]
    ofertas = carregar_notificados()

    if ofertas is None:
        # Primeira execucao: registra o que ja existe sem enviar nada (RF07)
        if enviar:
            novas_ofertas: Dict[str, Dict[str, str]] = {}
            registrar(novas_ofertas, elegiveis)
            salvar_notificados(novas_ofertas)
            print(f"Newsletter: primeira execução, {len(elegiveis)} jogos registrados como anunciados, nenhum envio.")
        else:
            print(f"Newsletter (teste): sem notificados.json; na primeira execução real {len(elegiveis)} jogos seriam só registrados.")
            if elegiveis:
                gravar_previa(montar_html_email(elegiveis))
        return

    novos = selecionar_novidades(elegiveis, ofertas)
    if not novos:
        print("Newsletter: nenhum jogo novo, nenhum envio.")
        if enviar:
            salvar_notificados(ofertas)
        return

    assunto = montar_assunto(novos)
    html_email = montar_html_email(novos)
    print(f"Newsletter: {len(novos)} jogo(s) novo(s): {', '.join(str(j.get('title')) for j in novos)}")

    if not enviar:
        print(f"Newsletter (teste): envio desligado fora do GitHub Actions. Assunto: {assunto}")
        gravar_previa(html_email)
        return

    try:
        config = _config_brevo()
        if contar_inscritos(config) == 0:
            # Sem inscritos nao ha para quem avisar; marca para nao acumular um e-mail atrasado
            registrar(ofertas, novos)
            salvar_notificados(ofertas)
            print(f"Newsletter: lista {config['lista']} sem inscritos; novidades registradas sem envio.")
            return
        id_campanha = enviar_campanha(config, assunto, html_email)
    except (ErroBrevo, urllib.error.URLError, TimeoutError) as e:
        # Nao marca como anunciado: tenta de novo na proxima execucao
        print(f"Newsletter: envio não realizado ({e}).", file=sys.stderr)
        return

    registrar(ofertas, novos)
    salvar_notificados(ofertas)
    print(f"Newsletter: campanha {id_campanha} enviada para a lista {config['lista']}.")


# ---------------------------------------------------------------------------
# Bloco de inscricao exibido no site
# ---------------------------------------------------------------------------

def montar_bloco_inscricao() -> str:
    """
    Secao de inscricao do index.html. Usa o formulario incorporavel da Brevo
    (BREVO_FORM_URL), que cuida da confirmacao dupla. Sem a URL, nada e exibido.
    """
    form_url = os.getenv("BREVO_FORM_URL", "").strip()
    if not form_url.startswith("https://"):
        return ""
    acao = html.escape(form_url, quote=True)
    return """
            <!-- NEWSLETTER -->
            <section class="newsletter-box" aria-labelledby="newsletter-titulo">
                <style>
                    .newsletter-box {
                        background: rgba(30, 33, 50, 0.55);
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        border-radius: 16px;
                        padding: 2rem;
                        margin-bottom: 4rem;
                        display: grid;
                        grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr);
                        gap: 2rem;
                        align-items: center;
                    }
                    .newsletter-box h2 { font-size: 1.6rem; font-weight: 800; margin-bottom: 0.6rem; }
                    .newsletter-box p { color: #c3c7d1; line-height: 1.6; }
                    .newsletter-form { display: grid; gap: 0.9rem; }
                    .newsletter-form label { font-weight: 600; font-size: 0.95rem; }
                    .newsletter-linha { display: flex; gap: 0.6rem; flex-wrap: wrap; }
                    .newsletter-form input[type="email"] {
                        flex: 1 1 220px;
                        min-width: 0;
                        background: #0b0d14;
                        color: #f3f4f6;
                        border: 1px solid rgba(255, 255, 255, 0.25);
                        border-radius: 8px;
                        padding: 0.8rem 1rem;
                        font: inherit;
                    }
                    .newsletter-form button {
                        background: #5b2fd6;
                        color: #ffffff;
                        border: none;
                        border-radius: 8px;
                        padding: 0.8rem 1.4rem;
                        font: inherit;
                        font-weight: 700;
                        cursor: pointer;
                    }
                    .newsletter-form button:hover { background: #4a22b8; }
                    .newsletter-form input:focus-visible,
                    .newsletter-form button:focus-visible,
                    .newsletter-consentimento input:focus-visible {
                        outline: 3px solid #00e5ff;
                        outline-offset: 2px;
                    }
                    .newsletter-consentimento { display: flex; gap: 0.6rem; align-items: flex-start; font-size: 0.85rem; color: #c3c7d1; line-height: 1.5; }
                    .newsletter-consentimento input { margin-top: 0.2rem; width: 18px; height: 18px; flex-shrink: 0; }
                    .newsletter-consentimento a { color: #00e5ff; }
                    .newsletter-status { min-height: 1.4em; font-size: 0.9rem; font-weight: 600; }
                    .newsletter-status.ok { color: #6ee7a8; }
                    .newsletter-status.erro { color: #ffb4b4; }
                    .newsletter-armadilha { position: absolute; left: -9999px; }
                    @media (max-width: 760px) {
                        .newsletter-box { grid-template-columns: 1fr; padding: 1.4rem; gap: 1.2rem; }
                    }
                </style>
                <div>
                    <h2 id="newsletter-titulo"><i class="fa-solid fa-envelope-open-text" aria-hidden="true"></i> Aviso de jogo grátis por e-mail</h2>
                    <p>Quando aparecer um jogo completo de graça, mandamos um e-mail no mesmo dia. Só jogos completos, sem DLCs nem códigos de itens, e no máximo um e-mail por dia. Para cancelar, é um clique no próprio e-mail.</p>
                </div>
                <form class="newsletter-form" id="newsletter-form" action="__ACAO__" method="POST" novalidate>
                    <label for="newsletter-email">Seu e-mail</label>
                    <div class="newsletter-linha">
                        <input type="email" id="newsletter-email" name="EMAIL" autocomplete="email" required placeholder="nome@exemplo.com">
                        <button type="submit">Quero receber</button>
                    </div>
                    <label class="newsletter-consentimento">
                        <input type="checkbox" id="newsletter-aceite" required>
                        <span>Aceito receber os avisos por e-mail e li a <a href="privacidade.html">Política de Privacidade</a>. A inscrição só vale depois que eu confirmar pelo link enviado ao meu e-mail.</span>
                    </label>
                    <input type="text" name="email_address_check" value="" class="newsletter-armadilha" tabindex="-1" autocomplete="off" aria-hidden="true">
                    <input type="hidden" name="locale" value="pt">
                    <p class="newsletter-status" id="newsletter-status" role="status" aria-live="polite"></p>
                </form>
                <script>
                    (function inicializarNewsletter() {
                        const form = document.getElementById('newsletter-form');
                        const email = document.getElementById('newsletter-email');
                        const aceite = document.getElementById('newsletter-aceite');
                        const status = document.getElementById('newsletter-status');
                        if (!form) return;
                        const mostrar = (texto, tipo) => { status.textContent = texto; status.className = 'newsletter-status ' + tipo; };
                        form.addEventListener('submit', async (evento) => {
                            evento.preventDefault();
                            if (!email.value || !email.checkValidity()) { mostrar('Digite um e-mail válido.', 'erro'); email.focus(); return; }
                            if (!aceite.checked) { mostrar('Marque a caixa de aceite para continuar.', 'erro'); aceite.focus(); return; }
                            const botao = form.querySelector('button');
                            botao.disabled = true;
                            try {
                                // O endereço da Brevo libera o domínio do site (CORS) e responde em JSON
                                const resposta = await fetch(form.action, { method: 'POST', body: new URLSearchParams(new FormData(form)) });
                                const dados = await resposta.json().catch(() => ({}));
                                if (resposta.ok && dados.success !== false) {
                                    form.reset();
                                    mostrar('Quase lá: abra seu e-mail e clique no link de confirmação. Se não achar, olhe a caixa de spam.', 'ok');
                                } else if (dados.errors && dados.errors.EMAIL) {
                                    mostrar('Esse e-mail não foi aceito. Confira se está escrito certo.', 'erro');
                                    email.focus();
                                } else {
                                    mostrar('Não foi possível concluir a inscrição agora. Tente de novo em alguns minutos.', 'erro');
                                }
                            } catch (erro) {
                                mostrar('Não foi possível enviar agora. Tente de novo em alguns minutos.', 'erro');
                            } finally {
                                botao.disabled = false;
                            }
                        });
                    })();
                </script>
            </section>
""".replace("__ACAO__", acao)
