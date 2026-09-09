# sddm-forge

App GTK4/libadwaita para configurar o **SDDM** e o tema de login ("Maia Theme"),
sem editar QML na mão. Uso pessoal, Fedora.

## O que dá pra mexer

- **Prévia** — render do tema **ao vivo dentro do app**, atualiza sozinho a cada
  ajuste. Botão "tela cheia" abre o greeter real (com vídeo) por cima.
- **Aparência** — fundo (vídeo / imagem / cor), blur, escurecimento, paleta de
  cores, fonte e tamanhos.
- **Layout** — editor de árvore: cria **painéis** (contêineres) e escolhe o que
  vai em cada um. Por painel: posição, direção (coluna/linha), largura (auto /
  % da tela / tela inteira), alinhamento, espaçamento, recuo, **blur do fundo
  atrás do painel**, escurecimento, canto arredondado. Adicionar / remover /
  reordenar painéis, sub-painéis e elementos. Peças:
  `clock, date, usernameRow, userHandle, password, loginButton, sessionButton,
  rebootButton, powerButton, errorMessage, text` (livre) e `spacer`.
  A visibilidade de cada peça = estar (ou não) num painel — ex.: relógio sem o
  dia da semana é um painel só com `clock`. Reordena por **arrastar** (ou ↑↓).
  Peças: clock, date, usernameRow, userHandle, **avatar**, password,
  **passwordToggle** (mostrar senha), loginButton, sessionButton,
  **sessionName**, rebootButton, powerButton, **suspendButton**, errorMessage,
  text (livre), **separator**, spacer. Cada peça de texto aceita **cor /
  tamanho / negrito** próprios.
- **Aparência → Estilo dos widgets** — presets: campo de senha
  (sublinhado / caixa / pílula / barra segmentada), botão LOGIN
  (contorno / preenchido / pílula), botões de sessão-energia
  (texto / contorno / pílula) e **ícones** neles (sem / só ícone / ícone+texto).
- **Elementos** — quais botões e textos aparecem (sessão, reiniciar, desligar,
  carrossel de usuário, `@usuario`, boas-vindas).
- **Relógio** — formato da hora e da data, locale.
- **SDDM** — Numlock, tema de cursor, fonte do greeter, HiDPI.
- **Autologin** — usuário e sessão.
- **Usuários** — faixa de UID, `HideUsers`, `HideShells`.
- **Temas** — trocar o `[Theme] Current`, (re)instalar o tema embutido, habilitar
  o serviço no boot.
- **Backup** — snapshot automático antes de cada "Aplicar"; restaurar qualquer um.

## Como funciona

- A GUI roda como usuário normal e edita uma **cópia de trabalho** do tema em
  `~/.local/share/sddm-forge/work/maia-theme/` (semeada do tema embutido).
- A aba **Prévia** roda um renderizador QML offscreen (PySide6) num processo
  separado, que observa o `theme.conf` da cópia de trabalho e regrava um PNG a
  cada mudança. O vídeo de fundo não roda offscreen: em modo "vídeo" a prévia
  mostra o **primeiro frame** do arquivo (extraído com ffmpeg). Usuários são
  fictícios. Para o render fiel, o botão **tela cheia** abre
  `sddm-greeter-qt6 --test-mode`.
- **Aplicar** chama **um** `pkexec` que, como root: faz backup, copia o tema para
  `/usr/share/sddm/themes/maia-theme/` e escreve
  `/etc/sddm.conf.d/10-maia.conf` (drop-in próprio — não toca nos defaults da
  distro).
- Nunca reinicia o `sddm.service` (isso derruba a sessão). Para ver o resultado:
  logout, ou `systemctl restart sddm` de um TTY.

## Dependências

```
sudo dnf install gtk4 libadwaita python3-gobject python3-pyside6 sddm polkit ffmpeg
```

`python3-pyside6` e `ffmpeg` são só para a **prévia embutida**; sem eles o app
funciona e a prévia cai para o botão "tela cheia".

## Rodar

```
./bin/sddm-forge            # direto do repo
```

## Instalar (usuário, sem root)

```
./install.sh                # ~/.local/bin/sddm-forge + lançador no menu
```

## Assets

Os vídeos de fundo em `theme/maia-theme/assets/` são grandes (~70 MB). Se for
versionar, considere `git lfs track '*.mp4'` antes do primeiro commit, ou
ignore-os e mantenha localmente.
