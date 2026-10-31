# Thonny RFC2217

Versão independente do Thonny com conexão nativa RFC 2217 para MicroPython. Permite usar um console serial remoto por TCP/IP, sem criar portas COM virtuais. O SimNodus é o dispositivo de referência dos testes; o transporte funciona por meio do cliente genérico do PySerial.

**Projeto não oficial / Unofficial distribution.** Esta distribuição é baseada no **Thonny 6.0.0.dev1** e no **Minny 0.0.1a2**, com alterações locais descritas em [PROVENANCE.md](PROVENANCE.md). Não é uma release oficial dos mantenedores do Thonny. A versão `0.1.0` identifica esta distribuição e é destinada a testes.

## Windows

Baixe a [release 0.1.0](https://github.com/RicardoKers/Thonny-RFC2217/releases/tag/v0.1.0):

- [Instalador Windows x64 (.exe)](https://github.com/RicardoKers/Thonny-RFC2217/releases/download/v0.1.0/Thonny-RFC2217-0.1.0-windows-x64-setup.exe): instale e abra **Thonny RFC2217** pelo menu Iniciar.
- [Versão portátil (.zip)](https://github.com/RicardoKers/Thonny-RFC2217/releases/download/v0.1.0/Thonny-RFC2217-0.1.0-windows-x64-portable.zip): extraia a pasta completa e abra **ThonnyRFC2217.exe**. Mantenha `portable.ini` para guardar a configuração em `user_data` nessa pasta.

Python, Tcl/Tk, Node e dependências estão incluídos. Não é necessário instalar Python separadamente. Requisitos: Windows 10/11 x64 e .NET Framework 4.x. O instalador usa identidade própria e o perfil fica em `%LOCALAPPDATA%/ThonnyRFC2217`; a versão portátil usa `user_data`. Os executáveis são não assinados digitalmente. Consulte [RELEASE_TEST_REPORT.md](RELEASE_TEST_REPORT.md) e os checksums da release.

Depois de abrir a aplicação:

1. Abra **Tools → Options → Interpreter**.
2. Selecione **MicroPython (ESP32)**.
3. Em **Connection**, selecione **RFC 2217 (TCP/IP)**.
4. Informe, por exemplo, `rfc2217://127.0.0.1:4000` e confirme.
5. Abra `examples/blink_gpio4.py`, pressione **F5** e acompanhe o Shell. **Ctrl+C** interrompe o programa.

O servidor RFC 2217 e o firmware MicroPython devem estar em execução externamente. O transporte no computador não depende de Wi-Fi no dispositivo emulado. Endpoints remotos também são aceitos, como `rfc2217://192.168.1.100:4000`.

## Executar pelos fontes

Requisitos: Windows, Python 3.11 ou superior com Tkinter e acesso ao PyPI para instalar dependências. Na raiz deste repositório:

```powershell
.\scripts\setup_windows.ps1
.\scripts\run_thonny.ps1
```

Os scripts criam uma `.venv` local e instalam `minny/` e `thonny/` em modo editável. O perfil de desenvolvimento fica em `.thonny-user/`, separado de outras instalações do Thonny. As duas pastas de fontes fazem parte deste repositório; não é necessário cloná-las à parte.

## Alterações principais

- Transporte RFC 2217 no Minny, reutilizando `SerialConnection` e o suporte do PySerial.
- Campo próprio de conexão RFC 2217, validação e persistência na configuração do interpretador.
- REPL, execução do editor e transferência de arquivos usando o backend MicroPython existente.
- Encerramento de leitura, tratamento de desconexão e preservação de bytes binários/UTF-8 fragmentado.
- Correções na integração de I/O e no diálogo de configuração do Thonny de desenvolvimento.
- Encerramento correto do servidor de linguagem, evitando acumular processos Node após F5; análise limitada à pasta do arquivo avulso quando não há projeto selecionado.

## Testes e limites

Os fontes foram validados com **36 testes de transporte Minny**, **38 testes Thonny** e **14 verificações reais do backend contra SimNodus**, além de ensaios manuais de F5, GPIO4/LED e Ctrl+C. Os resultados e suas condições estão em [TEST_REPORT.md](TEST_REPORT.md). A validação dos binários de uma release deve ser consultada no relatório dessa release.

Portas COM físicas e um servidor WebREPL real não estavam disponíveis para testes de integração; seus fluxos foram cobertos por testes automatizados. A suíte ampla de pacotes Minny apresentou 35 falhas que também foram reproduzidas no código original. No SimNodus de referência, retenção após desligamento, Wi-Fi e Bluetooth ainda não estavam implementados.

## Documentação e licenças

- [DEVELOPMENT.md](DEVELOPMENT.md): preparar o ambiente, testar e atualizar os fontes.
- [docs/RFC2217.md](docs/RFC2217.md): configurar e usar o transporte.
- [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md): decisões de arquitetura.
- [PROVENANCE.md](PROVENANCE.md): revisões e origem do código.
- [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md): avisos de componentes e licenças.

O núcleo Thonny e o Minny são MIT. Componentes de terceiros conservam suas próprias licenças e avisos, incluindo os ícones e stubs distribuídos com o Thonny. Consulte [LICENSE](LICENSE), [thonny/LICENSE.txt](thonny/LICENSE.txt) e [minny/LICENSE](minny/LICENSE).

