# Histórico de validação dos fontes

Este relatório registra ensaios locais anteriores ao empacotamento. Os logs brutos, os perfis locais e os resultados que podem conter caminhos pessoais não são publicados. A validação dos executáveis da release é documentada separadamente em `RELEASE_TEST_REPORT.md`.

# Relatório de testes — 30/10/2026

## Ambiente

Windows, Python 3.11.9, Tk 8.6, PySerial 3.5. Thonny `6.0.0.dev1` e Minny `0.0.1a2`, fontes oficiais editáveis e branches locais `feature/rfc2217`; commits originais em DEVELOPMENT.md. SimNodus em execução externa, endpoint `rfc2217://127.0.0.1:4000`, firmware identificado: **MicroPython v1.29.0 on 2026-08-24; ESP32C3 module with ESP32-C3**. Nenhum fonte, firmware ou circuito do SimNodus foi alterado.

## Automação e integração real

- Transporte Minny: **36 testes aprovados**, incluindo negociação real por `serial.rfc2217.PortManager`, bytes 0–255, múltiplas escritas, timeout ocioso, recusa, negociação incompleta, erro de host, desconexão/reconexão, DTR/RTS, encerramento com leitura ativa e ordem de fechamento da serial local. Incluem UTF-8 fragmentado com intervalo ocioso em modos texto/binário e preservação de bytes inválidos.
- Thonny: inicialmente 24 testes aprovados; após a correção de CPU/servidor de linguagem, **38 testes aprovados**. Incluem os 21 RFC/específicos de integração e quatro que exercitam o diálogo completo: edição apenas da URL, troca COM→RFC, URL inválida/cancelamento e OK sem alteração.
- Script real `tests/integration_simnodus.py`: **14 verificações aprovadas**; protocolo de mensagens e backend ESP32 reais do Thonny, sem substituir Minny ou firmware. Transcrição e resultados em `test-results/integration.json`.
- Dependências: `pip check` sem inconsistências. Scripts PowerShell parseados e `-CheckOnly` aprovado no PowerShell atual e Windows PowerShell 5.1. Ruff do Minny e verificação de whitespace dos dois clones aprovados. Formatação Thonny segue Black/isort, 100 colunas.

Na interface real, foi aberto `examples/blink_gpio4.py`, pressionado **F5**, observadas mensagens `LED LIGADO`/`LED DESLIGADO` no Shell e estados distintos do LED no circuito do SimNodus. **Ctrl+C** produziu `KeyboardInterrupt` e retorno ao prompt `>>>`. A aba **Interpreter** exibiu **MicroPython (ESP32) → RFC 2217 (TCP/IP)** com campo de URL dedicado. O ensaio manual de persistência revelou uma falha upstream no botão OK, corrigida com validação do diálogo completo e novo ensaio manual.

| Critério | Resultado e evidência |
|---|---|
| T01 selecionar RFC 2217 | Aprovado: formulário Tk automatizado e opção observada na IDE real. |
| T02 persistir host/porta | Aprovado: URL alterada manualmente para `rfc2217://localhost:4000`, OK reconectou; arquivo de configuração gravou port e rfc2217_url com o novo destino. |
| T03 conectar SimNodus | Aprovado: negociação PySerial e backend ESP32 real. |
| T04 REPL | Aprovado: boas-vindas e prompt na IDE. |
| T05 print | Aprovado: texto Unicode `RFC2217 olá ✓` via protocolo do Shell. |
| T06 F5 | Aprovado: tecla F5 real no editor e comando Run automatizado. |
| T07 interrupção | Aprovado: Ctrl+C real na IDE e ImmediateCommand interrupt automatizado; prompt retornou. |
| T08 raw REPL | Aprovado: bootstrap e operações Minny reais usando raw paste/REPL; entrada/saída também verificadas pelo fluxo inicial. |
| T09 soft reset | Aprovado: `MPY: soft reboot` e variável global removida no comando Run. |
| T10 listar arquivos | Aprovado: comando Thonny `get_dirs_children_info` no dispositivo. |
| T11 enviar/baixar | Aprovado: 774 bytes, incluindo NUL, 0xFF e controles, comparados byte a byte. |
| T12 main.py | Aprovado: main.py em diretório exclusivo executado; boot.py salvo e baixado. Inicialização automática dos arquivos da raiz não testada, para preservar boot.py existente. |
| T13 servidor desconectado | Aprovado apenas no servidor automatizado RFC com queda real do socket. Encerrar o processo SimNodus durante execução não foi realizado. |
| T14 reconectar | Aprovado: fechar backend e iniciar outro no mesmo SimNodus; `RECONNECTED_OK`. |
| T15 reiniciar IDE | Aprovado no ensaio de fechar normalmente e reabrir a IDE com a configuração gravada. |
| T16 COM convencional | Fluxo e parâmetros cobertos por fakes, incluindo leitura ativa. Hardware físico não disponível; teste real não executado. |
| T17 WebREPL | Roteamento/preservação de configuração cobertos por teste. Servidor WebREPL real não disponível; teste real não executado. |

Além desses critérios, passaram criação de diretório, renomeação, exclusão e execução de arquivos pelo backend Thonny. O diretório remoto exclusivo foi removido. Os arquivos `main.py`/`boot.py` da raiz não foram sobrescritos. O Minny pode criar sua pasta usual `.minny` como parte do fluxo existente.

Commits locais da primeira entrega: Minny `ebc4192` e Thonny `e2ec2d5f`. Nova execução real com esses códigos repetiu as 14 verificações, todas aprovadas. A IDE foi reaberta usando o destino persistido; `localhost:4000` e `127.0.0.1:4000` apontam para o mesmo servidor neste ambiente. O commit adicional `5781c463` corrige o consumo de CPU/servidor de linguagem, conforme o ensaio ao final deste relatório.

## Arquivos da entrega

- Minny: `src/minny/serial_connection.py`, `src/minny/connection.py`, `tests/test_serial_connection.py`.
- Thonny: `thonny/plugins/micropython/mp_front.py`, `thonny/plugins/micropython/mp_back.py`, `thonny/config_ui.py`, `thonny/test/plugins/test_rfc2217.py`.
- Workspace: `README.md`, `DEVELOPMENT.md`, `TEST_REPORT.md`, `docs/IMPLEMENTATION_PLAN.md`, `docs/RFC2217.md`, três scripts em `scripts/`, `requirements-dev.txt`, `requirements-tested.txt`, `examples/blink_gpio4.py`, `tests/integration_simnodus.py` e documentação técnica em `docs/`.
- Resultados de execução e logs da IDE de entrega em `test-results/`; perfil isolado em `.thonny-user/`. Estes são dados locais e não fazem parte dos commits dos projetos oficiais.

## Suíte ampla upstream

Foi executada a suíte Minny `-m "not slow"`: **35 falhas, 185 aprovados, 3 ignorados, 6 desmarcados** naquele ponto. Reexecutados os 35 testes com falha usando **somente o código original do commit upstream** via PYTHONPATH: **as mesmas 35 falhas**, sem mudanças do projeto. São problemas de expectativas/caminhos e snapshots no Windows, ferramentas de compilação/dependências e respostas de serviços externos, incluindo HTTP 404. Não foram ocultados nem corrigidos por refatoração fora do escopo. Os logs completos de comparação foram mantidos localmente e não integram o repositório público. A primeira tentativa dentro do sandbox teve uma falha adicional de rede/cache, por isso o ensaio comparável foi repetido fora dele.

Pyrefly no Minny apresenta três erros já existentes: import opcional de ptyprocess ausente no Windows, sinal SIGKILL indisponível e override de retorno em target.py. Nenhum nos arquivos alterados. Lint de correção Thonny comparado com upstream não acrescentou ocorrências; o mp_front já contém 15 alertas fora do escopo. Os testes lentos de instalação/pacotes não foram executados.

## Correções encontradas durante a validação

1. PySerial RFC 2217 não aceita write_timeout, cancel_read ou out_waiting como a serial local; adaptação explícita, leitura finita e sem promessa de drenagem remota.
2. Espera em fila de leitura podia atrasar a percepção da falha até o prazo total: rechecagem periódica do erro, conservando o timeout.
3. Cancelamento serial Windows precisa finalizar a leitura antes de fechar handles: ordem original preservada para COM.
4. Fragmentação TCP podia publicar UTF-8 incompleto quando o primeiro byte chegava sozinho: buffer retido até completar.
5. Backend Thonny upstream não encaminhava I/O Minny ao Shell: ligação do IOHandler restaurada e testada.
6. Diálogo Thonny ignorava alterações diferidas quando nenhuma opção já havia mudado: aplicar/validar páginas também nesse caso.
7. GUI atual requer basedpyright-langserver: dependência instalada apenas na venv e PATH temporário no launcher.

## Limites

Sem validação de retenção após desligamento, Wi-Fi ou Bluetooth (não implementados no simulador). Sem hardware COM ou servidor WebREPL reais. Sem provocar encerramento/reinício externo do SimNodus, testar perda de rede longa ou certificação contra diversos servidores físicos RFC 2217. Não há repetição automática de transferências interrompidas. DTR/RTS/BREAK dependem do servidor; o transporte não introduz reset extra. Não foi produzida distribuição portátil; entrega executável pelo código-fonte. Nenhum branch remoto ou PR publicado.

## Correção posterior: CPU alta e vários Nodes

O usuário forneceu imagem com quatro Nodes consumindo aproximadamente 12% de CPU cada e log de sucessivos reinícios. A inspeção do código confirmou que `LanguageServerProxy.shut_down()` encerrava somente o launcher Python de Basedpyright, que criava Node como processo filho. Enquanto a IDE permanecia aberta, o Node anterior podia continuar vivo junto com o novo. Ao inspecionar depois do fechamento normal da IDE, não havia Nodes deste projeto restantes; não foi necessário encerrar processos de outros aplicativos.

Também foi confirmado que o workspace enviado ao servidor era `<user-home>`: `run.working_directory` não estava definido e o Thonny usava a pasta pessoal. `openFilesOnly` não evita toda a enumeração de arquivos. Cada novo servidor repetia esse trabalho. As correções são:

- `lsp_proxy.py`: restaurar shutdown/resposta/exit, aguardar saída e coletar o processo; readers param em EOF em vez de repetir leitura vazia.
- `plugins/basedpyright.py`: controlar diretamente o Node do pacote pip Windows, mantendo fallback para servidor externo.
- `workbench.py`: escolher projeto explícito ou pasta do arquivo local aberto; manter rootUri e workspaceFolders consistentes.
- `scripts/run_thonny.ps1`: inicializar apenas diretório de trabalho ausente com `examples`, preservando escolhas existentes.
- Testes novos: `test_lsp_lifecycle.py` (5), `test_language_server_workspace.py` (6), `plugins/test_basedpyright_process.py` (3).

Validação real de quatro servidores Basedpyright consecutivos: todos inicializaram e saíram com código 0; cada saída levou 0,031–0,032 s; aproximadamente 128,8–129,5 MB e nenhuma CPU detectada nas amostras ociosas de três segundos. Resultado em `test-results/language-server.json`.

Na IDE, três ciclos reais de **F5 → Ctrl+C** contra SimNodus mantiveram **um único Node** após cada execução, com 128,8 MB, 127,8 MB e 131,9 MB. As amostras de três segundos mediram 0,0% de um núcleo nesses três intervalos. Isso é uma medição ociosa após inicialização; não promete CPU zero durante análise/edição. Logs em `test-results/gui-cpu-restarts.jsonl`. As mensagens do programa e KeyboardInterrupt continuaram normais. O launcher passou `-CheckOnly` também no Windows PowerShell 5.1.

Esta correção não desativa o servidor de linguagem nem remove recursos de edição.

Ao fechar normalmente a IDE corrigida, a contagem medida caiu para **zero Nodes deste workspace**. A instância de teste foi encerrada e o programa ficou interrompido no simulador. Commit local da correção: **`5781c463`**; fontes Thonny e Minny sem alterações pendentes. Os servidores de outros aplicativos não foram encerrados.
