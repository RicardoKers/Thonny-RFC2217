# Validação da release 0.1.1 — Windows x64

Data: 31/10/2026. Distribuição não oficial de testes, baseada no Thonny 6.0.0.dev1 e Minny 0.0.1a2. Runtime privado: CPython 3.11.9 x64, Tk 8.6, PySerial 3.5, Basedpyright 1.40.2 e Node.js 24.19.0. As 46 distribuições Python estão registradas em `requirements-bundled.txt`; os avisos de licença acompanham a aplicação.

## Tamanho comparado à 0.1.0

Os valores abaixo comparam os artefatos publicados, antes de executar a aplicação. MB significa 1.000.000 bytes; a contagem de arquivos corresponde ao conteúdo do ZIP, sem entradas de diretório.

| Medida | 0.1.0 | 0.1.1 | Redução |
|---|---:|---:|---:|
| Instalador | 73.204.279 bytes (73,2 MB) | 58.915.912 bytes (58,9 MB) | 19,5% |
| ZIP portátil | 117.878.336 bytes (117,9 MB) | 96.587.589 bytes (96,6 MB) | 18,1% |
| Conteúdo descompactado | 362.654.245 bytes (362,7 MB) | 279.849.144 bytes (279,8 MB) | 22,8% |
| Arquivos no ZIP | 23.595 | 14.419 | 9.176 arquivos (38,9%) |

Foram removidos `Lib/test` do Python, npm/Corepack, sourcemaps JavaScript do Basedpyright e Jedi, que não é usado pelo Thonny atual. Permanecem Node, Basedpyright, seus stubs/typeshed, Parso, Tcl/Tk, suporte a portas seriais e os recursos da IDE. A compactação do instalador usa LZMA2/ultra64; a do ZIP usa DEFLATE nível 9. Nenhuma mudança no transporte RFC 2217 ou no núcleo Thonny/Minny foi necessária nesta release.

O instalador remove os auxiliares antigos ao atualizar uma instalação identificada como Thonny RFC2217. Feche a aplicação antes de atualizar. O perfil é preservado. Para a versão portátil, extraia em pasta nova; copiar o ZIP por cima da 0.1.0 deixa os arquivos antigos no disco. Copie `user_data` para a nova pasta se desejar manter as configurações.

## Testes executados nesta release

| Ensaio | Resultado |
|---|---|
| Dependências do runtime privado | `pip check` aprovado, sem Jedi. |
| Minny instalado no pacote enxuto | 36 testes de transporte aprovados. |
| Thonny instalado no pacote enxuto | 38 testes aprovados. |
| Rotina de redução | 6 testes aprovados; 1 teste com symlink real ignorado por falta de permissão do Windows. A recusa de reparse points também foi verificada com teste independente. |
| Backend do pacote contra SimNodus em `127.0.0.1:4000` | 14 verificações aprovadas. |
| Autocompletação, hover e diagnósticos reais | Basedpyright iniciou com Node local; 84 sugestões, incluindo `sqrt`; ajuda de tipos presente; diagnóstico `reportAssignmentType`; encerramento com código 0. |
| Integridade ZIP final | CRC de todos os arquivos aprovado. |
| Portabilidade do ZIP final | Extraído em outro diretório com espaços; launcher executado de diretório de trabalho externo; Python, Thonny, Minny, Tk e Node locais confirmados. Versão do `.exe`: 0.1.1.0. |
| Servidor de linguagem após extração final | Repetida a prova completa de autocompletação, hover, diagnóstico e encerramento; aprovada. |
| Interface do ZIP final | Conectou ao REPL do SimNodus; F5 executou `blink_gpio4.py`, com mensagens LED LIGADO/DESLIGADO; Ctrl+C produziu KeyboardInterrupt e retornou ao prompt. |
| Atualização de 0.1.0 | Código do instalador exercitado em cópia extraída da 0.1.0, com AppId de validação e payload mínimo: removeu os auxiliares selecionados, preservou `user_data/keep.txt`; launcher e runtime resultantes passaram no smoke test. |
| Proteção de outro Python | Mesmo instalador de validação recusou pasta contendo Python sem a identificação desta distribuição; saída 7, executável original intacto. |
| Compilação do instalador completo final | Inno Setup concluiu a geração sem erros. |

Os testes reais do backend cobriram inicialização/raw REPL, saída Unicode, Run/F5, GPIO4 em 0/1, interrupção, retorno ao prompt, soft reset, listagem, criação de diretório, upload/download binário de 774 bytes, renomeação, `main.py`/`boot.py` em diretório de teste, limpeza e reconexão. Os arquivos da raiz do dispositivo não foram sobrescritos. O firmware de referência identificou MicroPython v1.29.0 em ESP32-C3.

## Limites

Validação no Windows 11 deste ambiente, sem máquina virtual Windows limpa. O instalador completo 0.1.0 já havia passado por instalação, execução e desinstalação; nesta versão, a lógica alterada de atualização foi exercitada sob identidade isolada para preservar a instalação em uso. Não foi feita uma instalação completa do executável final 0.1.1 neste computador. O runtime final foi validado pelo ZIP, construído a partir do mesmo bundle do instalador.

O launcher requer .NET Framework 4.x. Os binários se destinam a Windows 10/11 x64. COM físico e servidor WebREPL real não estavam disponíveis; os testes automatizados não substituem validação em hardware. Retenção de memória, Wi-Fi e Bluetooth do simulador estão fora do escopo. As falhas preexistentes da suíte ampla Minny permanecem documentadas em [TEST_REPORT.md](TEST_REPORT.md).

Os executáveis desta distribuição não possuem assinatura digital comercial. O compilador Inno Setup foi obtido do fornecedor, com assinatura e checksum verificados pelo script. As licenças dos componentes distribuídos estão incluídas, inclusive Node e PySerial.

## Reproduzir o build

Prepare CPython 3.11.9 x64 com Tcl/Tk e execute na raiz dos fontes:

```powershell
.\scripts\setup_windows.ps1
.\scripts\build_windows.ps1
```

O build instala dependências no runtime privado, constrói wheels dos fontes, compila o launcher C#, coleta licenças, remove somente os auxiliares definidos em `prune_bundle.py` e gera os artefatos em `dist/`. `-Reuse` permite reutilizar o bundle; `-BundleOnly` omite a compactação. O relatório de redução fica em `build/pruning-0.1.1.json`. A rotina recusa destinos externos e links/reparse points antes da remoção. Não se reivindica reprodução byte a byte de timestamps e metadados das ferramentas.

O teste `tests/probe_language_server_features.py` deve ser executado pelo `python.exe -I` do bundle, com `--runtime <bundle> --output-json <resultado.json>`. Os testes de redução estão em `tests/test_bundle_pruning.py`.
