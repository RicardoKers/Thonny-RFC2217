# Desenvolvimento

Este repositório contém um snapshot dos dois projetos em pastas adjacentes:

```text
thonny/       Fontes Thonny modificados e licenças originais
minny/        Fontes Minny modificados e licença original
scripts/      Preparação, execução e testes pelo código-fonte
tests/        Integração opcional com SimNodus e servidor de linguagem
examples/     Exemplo GPIO4
docs/         Arquitetura e uso do RFC 2217
```

Não existem repositórios Git internos em `thonny/` e `minny/`. As revisões originais e as revisões locais exportadas estão em [PROVENANCE.md](PROVENANCE.md).

## Preparação

Use Python 3.11 ou superior com Tkinter. Na raiz, em PowerShell:

```powershell
.\scripts\setup_windows.ps1
.\scripts\run_thonny.ps1 -CheckOnly
.\scripts\run_thonny.ps1
```

O setup cria `.venv`, instala os dois projetos em modo editável e as dependências de desenvolvimento. Nenhuma instalação global é alterada. O launcher confere os caminhos de importação e mantém os dados do perfil em `.thonny-user`. O primeiro lançamento configura ESP32/RFC 2217 em `127.0.0.1:4000`. Escolhas posteriores ficam preservadas.

Uma dependência de desenvolvimento da interface Thonny 6 é o Basedpyright. Seu Node pertence ao ambiente virtual. O launcher altera PATH somente no processo; no Windows com o pacote local, o Thonny controla diretamente o processo Node para garantir o encerramento.

Para reproduzir as versões registradas no ambiente inicial:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\requirements-tested.txt
```

## Testes

```powershell
.\scripts\run_tests.ps1
.\scripts\run_tests.ps1 -Integration
.\scripts\run_tests.ps1 -Integration -Url rfc2217://localhost:4000
.\scripts\run_tests.ps1 -FullMinny
.\.venv\Scripts\python.exe .\tests\integration_language_server.py
```

O comando padrão executa os testes de transporte Minny e a suíte Thonny. O servidor de teste usa a negociação real de `serial.rfc2217.PortManager`; não se limita a um TCP de eco. Não exige hardware nem SimNodus.

`-Integration` é opt-in e requer o servidor externo já iniciado. O teste interrompe programas, reinicia o interpretador e cria/remove um diretório remoto exclusivo. Feche a conexão da IDE antes dele para não conectar dois clientes ao mesmo console. O script não sobrescreve `boot.py` ou `main.py` da raiz do dispositivo. Os arquivos e relatórios gerados em `test-results/` são locais e ignorados pelo Git.

`-FullMinny` amplia a execução para testes upstream de pacotes/projetos. Há 35 falhas preexistentes reproduzidas neste Windows; consulte [TEST_REPORT.md](TEST_REPORT.md). A suíte lenta não foi executada. O probe de servidor de linguagem é específico do Windows e mede quatro ciclos reais de inicialização/encerramento em uma pasta pequena de exemplos.

## Atualização dos fontes

Não substitua as pastas incluídas diretamente por um clone atualizado. Faça a comparação em checkouts separados, preserve as alterações locais e reveja as mudanças de API entre Thonny e Minny antes de atualizar o snapshot. Reexecute setup, os testes e a validação dos binários. As alterações locais podem ser extraídas como patches a partir do histórico deste repositório e comparadas com os commits upstream registrados.

Para propor uma contribuição oficial, siga `thonny/CONTRIBUTING.rst`: discuta mudanças maiores em uma issue antes de enviar código. Transporte Minny, interface Thonny e correções gerais de integração podem ser apresentados separadamente.

## Distribuição Windows

Os scripts de empacotamento e o relatório de validação da release complementam este ambiente de desenvolvimento. Um binário publicado deve incluir seus runtimes e avisos de licença, usar um perfil independente e ser testado fora da `.venv` de desenvolvimento. Consulte a descrição e os arquivos da release específica antes de instalar.

A release 0.1.0 usa CPython 3.11.9 x64 completo com Tcl/Tk. Para reconstruir, prepare a `.venv` com essa versão e execute `scripts/build_windows.ps1`. O script gera um bundle privado, compila o launcher C# pelo .NET Framework, prepara o compilador Inno Setup em `build-tools/` e produz o instalador, ZIP portátil e checksums em `dist/`. Consulte [RELEASE_TEST_REPORT.md](RELEASE_TEST_REPORT.md) para comandos e testes efetivamente realizados. `requirements-bundled.txt` registra as 47 distribuições instaladas no runtime desta release; `packaging/windows/requirements-runtime.txt` contém as dependências diretas do build.
