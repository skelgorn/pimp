# LetrasPIP - Letras do Spotify em Picture-in-Picture

Uma aplicação para exibir letras de músicas do Spotify em uma janela flutuante (estilo Picture-in-Picture) na tela do seu computador, sincronizada com a música atual.

## Status do Projeto

**Versão Atual:** 0.2-beta

Este projeto está em desenvolvimento ativo. A versão atual é funcional e inclui um instalador para Windows, com melhorias significativas na sincronização e diagnóstico.

---

## 🆕 Novidades da Versão 0.2

### ✨ Novas Funcionalidades
- **Sistema de Logs Integrado**: Janela de logs em tempo real para diagnóstico
- **Persistência de Offset por Faixa**: Ajustes de sincronização são lembrados para cada música
- **Interface de Diagnóstico**: Menu tray com opções para visualizar logs e resetar offset
- **Logs Detalhados**: Rastreamento completo de mudanças de offset e sincronização
- **Melhor Experiência do Usuário**: Mensagens mais claras e controles intuitivos

### 🔧 Melhorias Técnicas
- Sistema robusto de cache de offsets por faixa
- Logs com timestamp para diagnóstico preciso
- Interface de logs com opções de salvar e limpar
- Código limpo e organizado

---

## Instalação (Para Usuários Windows)

1.  **Baixe o Instalador:** Vá para a [**página de Releases**](https://github.com/skelgorn/pimp/releases) do projeto.
2.  **Faça o Download:** Baixe o arquivo `LetrasPIP_setup.exe` da versão mais recente.
3.  **Execute o Instalador:** Rode o `LetrasPIP_setup.exe`. Ele irá instalar a aplicação, criar um atalho na área de trabalho e iniciar o programa.
    *   **Aviso:** O Windows SmartScreen pode exibir um alerta por ser um aplicativo não reconhecido. Clique em "Mais informações" e depois em "Executar assim mesmo".

## Como Usar

### 🎵 Uso Básico
-   Após a instalação, o LetrasPIP será iniciado.
-   Na primeira vez, você precisará autorizar o aplicativo a se conectar com sua conta do Spotify. Uma janela do navegador será aberta para você fazer o login.
-   Depois de autorizado, o aplicativo irá detectar a música que está tocando no seu Spotify e exibir as letras na janela flutuante.
-   Para mover a janela, simplesmente clique e arraste-a para qualquer lugar da tela.

### ⚙️ Ajustes de Sincronização
- **Ajuste Manual**: Use o menu do tray (clique direito no ícone) para adiantar ou atrasar a letra
- **Persistência**: Os ajustes são automaticamente salvos por faixa
- **Reset**: Use "Resetar Offset" no menu para voltar ao padrão
- **Centralizar**: Use "Centralizar letra" para reposicionar a janela

### 🔍 Diagnóstico e Logs
- **Visualizar Logs**: Clique em "Mostrar Logs" no menu do tray
- **Salvar Logs**: Use o botão "Salvar Logs" na janela de logs
- **Limpar Logs**: Use o botão "Limpar Logs" para resetar os logs

---

## Funcionalidades

### ✅ Implementadas
-   Janela flutuante que permanece sempre visível (always-on-top).
-   Busca e exibição de letras sincronizadas com a música do Spotify.
-   Login e autorização com a conta do Spotify.
-   Instalador para Windows.
-   **Sistema de logs em tempo real para diagnóstico.**
-   **Persistência de offset de sincronização por faixa.**
-   **Interface de diagnóstico integrada.**
-   **Ajuste manual de sincronização via menu tray.**
-   **Logs detalhados com timestamp.**
-   **Sistema de cache robusto.**

### 🚧 Planejadas
-   Fundo transparente e personalização da janela.
-   Rolagem automática com destaque da linha atual.
-   Estilo dinâmico (cores baseadas na capa do álbum).
-   Opções de personalização na própria interface (fonte, tamanho, etc.).

---

## 🐛 Solução de Problemas

### Problemas Comuns

1. **Letra não sincronizada**
   - Use o menu tray para ajustar a sincronização
   - Verifique os logs para diagnóstico detalhado
   - O offset será salvo automaticamente para a próxima vez

2. **Letra não encontrada**
   - Verifique se a música tem letra disponível
   - Algumas músicas instrumentais não têm letra
   - Use os logs para ver detalhes da busca

3. **Problemas de conexão**
   - Verifique sua conexão com a internet
   - Reinicie o aplicativo se necessário
   - Verifique os logs para erros específicos

### Diagnóstico Avançado
- Abra a janela de logs via menu tray
- Os logs mostram detalhes de busca, sincronização e erros
- Salve os logs para análise posterior se necessário

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

## 📁 Estrutura do Projeto

```
LetrasPIP/
├── main.py                 # Ponto de entrada da aplicação
├── lyrics_window.py        # Interface principal e sistema de logs
├── spotify_thread.py       # Thread para comunicação com Spotify
├── config.py              # Configurações e credenciais
├── requirements.txt       # Dependências Python
├── setup.iss             # Script do instalador
├── build_scripts/        # Scripts de build
│   ├── build_spec.py     # Especificação do PyInstaller
│   └── nuitka_config.py  # Configuração do Nuitka
└── installer/            # Arquivos do instalador
```

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

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

---

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

---

## 🆘 Suporte

Se você encontrar problemas ou tiver sugestões:

1. Verifique os logs da aplicação para diagnóstico
2. Abra uma issue no GitHub com detalhes do problema
3. Inclua logs salvos se disponível

**Nota:** Este é um projeto em desenvolvimento. Funcionalidades podem mudar entre versões.
