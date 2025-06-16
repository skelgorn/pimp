# LetrasPIP - Letras do Spotify em Picture-in-Picture

Uma aplicação para exibir letras de músicas do Spotify em uma janela flutuante (estilo Picture-in-Picture) na tela do seu computador, sincronizada com a música atual.

## Status do Projeto

**Versão Atual:** 0.1-beta

Este projeto está em desenvolvimento ativo. A versão atual é funcional e inclui um instalador para Windows, mas pode conter bugs.

---

## Instalação (Para Usuários Windows)

1.  **Baixe o Instalador:** Vá para a [**página de Releases**](https://github.com/skelgorn/pimp/releases) do projeto.
2.  **Faça o Download:** Baixe o arquivo `LetrasPIP_setup.exe` da versão mais recente.
3.  **Execute o Instalador:** Rode o `LetrasPIP_setup.exe`. Ele irá instalar a aplicação, criar um atalho na área de trabalho e iniciar o programa.
    *   **Aviso:** O Windows SmartScreen pode exibir um alerta por ser um aplicativo não reconhecido. Clique em "Mais informações" e depois em "Executar assim mesmo".

## Como Usar

-   Após a instalação, o LetrasPIP será iniciado.
-   Na primeira vez, você precisará autorizar o aplicativo a se conectar com sua conta do Spotify. Uma janela do navegador será aberta para você fazer o login.
-   Depois de autorizado, o aplicativo irá detectar a música que está tocando no seu Spotify e exibir as letras na janela flutuante.
-   Para mover a janela, simplesmente clique e arraste-a para qualquer lugar da tela.

---

## Funcionalidades

### Implementadas
-   Janela flutuante que permanece sempre visível (always-on-top).
-   Busca e exibição de letras sincronizadas com a música do Spotify.
-   Login e autorização com a conta do Spotify.
-   Instalador para Windows.

### Planejadas
-   Fundo transparente e personalização da janela.
-   Rolagem automática com destaque da linha atual.
-   Estilo dinâmico (cores baseadas na capa do álbum).
-   Opções de personalização na própria interface (fonte, tamanho, etc.).

---

## Para Desenvolvedores

Se você deseja contribuir ou rodar o projeto a partir do código-fonte, siga os passos abaixo.

### 1. Configuração do Ambiente

-   **Clone o repositório:**
    ```bash
    git clone https://github.com/skelgorn/pimp.git
    cd pimp
    ```
-   **Crie e ative um ambiente virtual:**
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate
    
    # macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```
-   **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```
-   **Configure as chaves de API:**
    -   Copie o arquivo `.env.example` para um novo arquivo chamado `.env`.
    -   Edite o `.env` com suas credenciais do Spotify Developer Dashboard e da API do Genius.

### 2. Executando a Aplicação
```bash
python main.py
```

### 3. Compilando o Projeto

O projeto utiliza **PyInstaller** para criar o executável e **Inno Setup** para criar o instalador.

-   **Gerar o executável:**
    ```bash
    pyinstaller LetrasPIP.spec
    ```
-   **Gerar o instalador:**
    -   Abra o arquivo `setup.iss` com o Inno Setup Compiler e clique em "Compile".

---

## Tecnologias Utilizadas

-   Python 3
-   PyQt6 (para a interface gráfica)
-   Spotipy (para interação com a API do Spotify)
-   LyricsGenius (para buscar letras de músicas)
-   Pillow & Colorgram.py (para extração de cores)
-   SyncedLyrics (para letras sincronizadas)
-   python-dotenv (para variáveis de ambiente)
-   PyInstaller (para empacotamento)
-   Inno Setup (para o instalador)
