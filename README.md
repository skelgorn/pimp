# Letras PIP Spotify

Uma aplicação para exibir letras de músicas do Spotify em uma janela flutuante (estilo Picture-in-Picture) na tela do seu computador, sincronizada com a música atual.

## Funcionalidades Principais (Planejadas)

-   **Janela Flutuante Personalizável:**
    -   Fundo transparente para integração suave com qualquer tela.
    -   Pode ser movida e redimensionada facilmente pelo usuário.
    -   Permanece sempre visível (always-on-top).
-   **Sincronização de Letras com Spotify:**
    -   Exibe as letras da música que está tocando no Spotify.
    -   Destaque visual para a linha atual da música.
    -   Rolagem automática para manter a linha atual centralizada na janela (formato de 5 linhas: 2 anteriores, atual destacada, 2 próximas).
-   **Estilo Dinâmico:**
    -   Cores do texto e destaque sincronizadas com a capa do álbum da música atual.
    -   Linha atual com cor mais brilhante, outras linhas mais suaves.
    -   Borda/sombra no texto para garantir legibilidade sobre diferentes fundos.
-   **Interação Intuitiva:**
    -   Mova a janela clicando diretamente sobre a área das letras.

## Como Configurar e Usar

1.  **Crie um Ambiente Virtual (Recomendado):**
    Na pasta do projeto (`C:\Users\Leticia\CascadeProjects\LetrasPIP\`):
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # macOS/Linux
    # source venv/bin/activate
    ```

2.  **Instale as Dependências:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure as Chaves de API:**
    -   Na pasta do projeto, copie o arquivo `.env.example` para um novo arquivo chamado `.env`.
    -   Edite o arquivo `.env` com suas credenciais:
        -   `SPOTIPY_CLIENT_ID`: Seu Client ID do Spotify Developer Dashboard.
        -   `SPOTIPY_CLIENT_SECRET`: Seu Client Secret do Spotify Developer Dashboard.
        -   `SPOTIPY_REDIRECT_URI`: A URI de redirecionamento configurada no seu app Spotify (ex: `http://localhost:8888/callback`).
        -   `GENIUS_ACCESS_TOKEN`: Seu Access Token da API do Genius.

4.  **Execute a Aplicação:**
    ```bash
    python main.py
    ```

## Tecnologias Utilizadas

-   Python 3
-   PyQt6 (para a interface gráfica)
-   Spotipy (para interação com a API do Spotify)
-   LyricsGenius (para buscar letras de músicas)
-   Pillow & Colorgram.py (para extração de cores da capa do álbum)
-   SyncedLyrics (para letras sincronizadas)
-   python-dotenv (para variáveis de ambiente)

## Próximos Passos / Melhorias Futuras

-   [ ] Implementar busca e sincronização de letras (LRC e Genius).
-   [ ] Adicionar lógica de destaque e rolagem de 5 linhas.
-   [ ] Implementar extração de cor da capa do álbum.
-   [ ] Opções de personalização (fonte, tamanho, cores) via UI.
-   [ ] Empacotamento da aplicação para distribuição mais fácil.
