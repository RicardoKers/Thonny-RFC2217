# Validação da release 0.1.0 — Windows x64

Data: 31/10/2026. Distribuição não oficial de testes, baseada no Thonny 6.0.0.dev1 e Minny 0.0.1a2. Runtime privado: CPython 3.11.9 x64, Tk 8.6, PySerial 3.5, Basedpyright 1.40.2 e Node.js 24.19.0. A lista completa está em `requirements-bundled.txt` e no diretório `licenses` da aplicação.

## Artefatos

- `Thonny-RFC2217-0.1.0-windows-x64-setup.exe`: instalador por usuário, com nome, AppId, atalhos e perfil próprios.
- `Thonny-RFC2217-0.1.0-windows-x64-portable.zip`: extração e execução de `ThonnyRFC2217.exe`; perfil em `user_data` dentro da pasta extraída.
- `SHA256SUMS.txt`: integridade dos arquivos publicados.

Os executáveis desta distribuição não possuem assinatura digital comercial. Os arquivos vêm do repositório RicardoKers/Thonny-RFC2217, não dos mantenedores oficiais do Thonny. O compilador Inno Setup usado na construção foi verificado pela assinatura do fornecedor e checksum fixado no script.

## Testes efetivamente executados

| Ensaio | Resultado |
|---|---|
| Importação com runtime privado e dependências | Aprovado; módulos Thonny e Minny carregados do bundle, sem instalação global ou `.venv`. |
| Tk e launcher GUI `.exe` | Aprovado; teste de abertura Tk e execução via launcher compilado. |
| Dependências | `pip check` aprovado; 47 distribuições instaladas, 214 avisos de licença coletados, mais licenças dos componentes principais. |
| Módulos Minny instalados no pacote | 36 testes de transporte aprovados, incluindo negociação RFC 2217 real no servidor de teste. |
| Módulos Thonny instalados no pacote | 38 testes aprovados. |
| Integridade ZIP | Aprovada pela verificação CRC de todos os arquivos. |
| Portabilidade | ZIP extraído para outro diretório com espaços; `.exe` aberto a partir de um diretório de trabalho externo; Python, Tk e Node locais confirmados. |
| Ferramentas de console relocáveis | `Scripts/pip.cmd --version` apontou para o Python do diretório extraído. |
| Instalação | Instalador completo executado silenciosamente em diretório de teste separado. |
| Executável instalado | `ThonnyRFC2217.exe --smoke-test` aprovado após instalação, confirmando o runtime local. |
| Desinstalação | Desinstalador removeu a aplicação de teste; nenhuma instalação oficial foi utilizada. |
| Backend real do pacote contra SimNodus | 14 verificações aprovadas, conforme detalhado abaixo. |
| Interface portátil | REPL conectado, F5 executou o exemplo GPIO4 e mostrou mensagens no Shell; Ctrl+C produziu KeyboardInterrupt e retornou a `>>>`. |
| CPU do servidor de linguagem portátil | Um Node; 129,1 MB; 0,0% de um núcleo na amostra ociosa de 3,06 s após F5. |
| Encerramento da interface portátil | Zero Nodes dessa cópia após fechar normalmente a IDE. |

O backend foi executado com o `python.exe` do bundle e o lançador `esp32_back.py` instalado no próprio pacote. Servidor externo `rfc2217://127.0.0.1:4000`, firmware identificado como MicroPython v1.29.0, ESP32-C3. As verificações cobriram inicialização/raw REPL, saída Unicode, Run/F5, GPIO4 em 0/1, interrupção, retorno ao prompt, soft reset, listagem, criação de diretório, upload/download binário de 774 bytes, renomeação, `main.py`/`boot.py` em diretório de teste, exclusão e reconexão. Os arquivos da raiz do dispositivo não foram sobrescritos. A primeira tentativa foi recusada porque o servidor estava parado; o ensaio foi repetido após ele ser iniciado externamente e todos os 14 itens passaram.

## Limites

Validação realizada no Windows 11 deste ambiente, sem máquina virtual Windows limpa. O launcher requer .NET Framework 4.x, presente neste Windows; não foi testado em sistemas sem esse componente. O instalador exige Windows 10 ou superior com capacidade x64. ARM64 nativo, Linux e macOS não fazem parte destes binários. O pacote inclui seu próprio Python, Tcl/Tk, Node e dependências; não depende do Python global.

COM físico e servidor WebREPL real não estavam disponíveis; testes automatizados preservam esses caminhos, mas não substituem validação em hardware. Retenção de memória, Wi-Fi e Bluetooth do simulador estão fora do escopo. A medição de CPU é uma amostra ociosa e não promete consumo zero durante análise de código. Histórico e falhas preexistentes da suíte ampla Minny permanecem em [TEST_REPORT.md](TEST_REPORT.md).

## Reproduzir o build

Use CPython 3.11.9 x64 completo, com Tcl/Tk, e um ambiente de desenvolvimento preparado. Execute:

```powershell
.\scripts\setup_windows.ps1
.\scripts\build_windows.ps1
```

O processo copia somente o runtime base, instala dependências em uma pasta privada, constrói wheels dos fontes incluídos, compila o launcher C#, reúne licenças e gera instalador e ZIP em `dist/`. O compilador Inno Setup é preparado em `build-tools/` sem instalação global. A pasta de saída precisa estar ausente no primeiro build; `-Reuse` permite reutilizar o runtime durante desenvolvimento. `-BundleOnly` omite a compactação final. Código, avisos e versões estão disponíveis neste repositório; não se reivindica reprodução byte a byte de timestamps e metadados das ferramentas.
