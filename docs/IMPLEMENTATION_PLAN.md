# Plano de implementação RFC 2217

## Base e compatibilidade

Workspace isolado, Python 3.11.9, ambiente `.venv`, instalações editáveis de dois repositórios oficiais adjacentes. Thonny `6.0.0.dev1` (`99de9cfe057a79d40da674e5c319e4b0142f9579`) já depende de Minny e declara sua origem editável `../minny`; Minny `0.0.1a2` (`4471205b1d8f905dd410a4b35c6037686d6917ab`) exige Python >=3.11. Não foi necessário recuar versões. Branch local `feature/rfc2217` em cada repositório. Nenhuma publicação remota.

## Estudo anterior à implementação

Foram examinados os metadados, README, políticas de contribuição e os pontos de conexão: `minny/src/minny/{serial_connection,connection,bare_metal_target,webrepl_connection}.py` e `thonny/thonny/plugins/micropython/{mp_front,bare_metal_backend}.py`. O Thonny delega execução e arquivos ao Minny. O lançador do backend já passa `port`, DTR e RTS para `SerialConnection`. A interface conserva WebREPL no mesmo seletor somente leitura das portas locais. A conexão serial usa leitura bloqueante, `cancel_read()` e `out_waiting`; esses recursos não são todos oferecidos pela implementação RFC 2217 do PySerial.

## Transporte

Estender `SerialConnection` de forma mínima para URLs RFC 2217, usando `serial.serial_for_url(..., do_not_open=True)`. Preservar a sequência de configuração de DTR/RTS antes da abertura. Manter parâmetros da serial local. Usar leitura finita no transporte de rede, distinguindo timeout vazio de erro e encerramento. Encerrar a thread por sinalização e cancelamento quando disponível; fechar socket e limitar espera quando necessário. Não implementar Telnet/RFC 2217 manualmente. A implementação PySerial 3.5 não aceita `write_timeout` no RFC: usar seu socket com timeout finito. Escritas são síncronas (`sendall`); `outgoing_is_empty()` verifica ausência de escrita em andamento no Minny, sem prometer drenagem do dispositivo remoto. A serial local preserva cancelamento → espera da thread → fechamento; rede fecha socket antes da espera final. Leituras em `MicroPythonConnection` passam a verificar falhas a cada 0,1 s, conservando o prazo total do chamador. UTF-8 incompleto permanece em buffer mesmo quando o primeiro byte do caractere chega isolado.

## Interface e persistência

Adicionar `RFC 2217 (TCP/IP)` ao seletor existente, rotulado Connection, com campo URL dedicado. Salvar a URL efetiva em `<backend>.port` para reutilizar o lançamento e protocolo existentes, e lembrar o último endpoint em `<backend>.rfc2217_url`. Validar esquema, host e porta. Adaptar identidade do dispositivo, disponibilidade, histórico e seleção para não buscar URLs entre portas USB. Preservar COM, detecção automática, WebREPL e Python local. Nenhum backend duplicado e nenhuma dependência do SimNodus no código central.

Dois defeitos de integração do upstream surgiram apenas na execução real: `MicroPythonBackend` não ligava o `IOHandler` do Minny ao protocolo da IDE, e `ConfigurationDialog` só aplicava páginas quando já existia mudança em uma opção vinculada diretamente, ignorando campos diferidos como seleção de conexão. Corrigir a ligação de I/O para encaminhar saída/entrada ao Shell e sempre aplicar/validar as páginas ao confirmar o diálogo. Não gravar valores inválidos antecipadamente. Ambos recebem testes de regressão; o segundo exige exercício do diálogo completo.

## Validação

Primeiro testes automatizados de transporte, bytes binários, timeout, encerramento, reconexão, sinais, serial local e configuração. Servidor de teste, se utilizado, deverá negociar RFC 2217 por infraestrutura PySerial; TCP de eco não basta. Executar a suíte rápida existente do Minny e verificações de estilo pertinentes. Depois validar o backend real do Thonny contra `127.0.0.1:4000`: REPL, execução, interrupção, soft reset, arquivos e reconexão. Validar também a interface e F5 quando o ambiente gráfico permitir. Registrar separadamente testes reais, mocks e itens não executados.

## Isolamento e limites

Dados do Thonny em `.thonny-user`, sem alterar instalação/configuração existente. SimNodus e firmware não serão modificados, reconstruídos nem iniciados pelo projeto. Não presumir retenção de arquivos após reset/desligamento; Wi-Fi e Bluetooth estão fora da validação porque o simulador ainda não os implementa. Usar arquivos de teste com nomes próprios e preservar `boot.py`/`main.py` preexistentes. Desconexão real do servidor só será declarada testada se efetivamente provocada; teste automatizado de desconexão não equivale a encerrar SimNodus. GPIO será verificado por leitura do firmware; observação visual do circuito depende do simulador.
